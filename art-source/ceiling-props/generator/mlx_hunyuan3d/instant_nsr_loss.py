"""Training objectives used by Era3D's orthographic Instant-NSR system."""

from __future__ import annotations

from dataclasses import dataclass

import mlx.core as mx

from .instant_nsr import InstantNSRGeometry


@dataclass(frozen=True)
class InstantNSRLossConfig:
    rgb_mse: float = 0.5
    rgb_l1: float = 0.0
    mask: float = 1.0
    eikonal: float = 0.2
    normal: float = 1.0
    normal_smooth: float = 1.0
    sparsity: float = 1.0
    sparsity_scale: float = 100.0
    rgb_penalize_ratio: float = 0.8
    normal_penalize_ratio: float = 0.8
    mask_penalize_ratio: float = 0.9
    geometry_aware_normals: bool = True


def _normalize(vector: mx.array, epsilon: float = 1e-6) -> mx.array:
    return vector / mx.maximum(mx.linalg.norm(vector, axis=-1, keepdims=True), epsilon)


def _mask_indices(mask: mx.array) -> mx.array:
    flat_mask = mask.reshape(-1)
    count = int(mx.sum(flat_mask).item())
    if count <= 0:
        raise ValueError("masked Instant-NSR loss has no selected samples")
    return mx.argsort(mx.where(flat_mask, 0, 1))[:count]


def released_ranking_loss(
    error: mx.array,
    penalize_ratio: float,
    *,
    extra_weights: mx.array | None = None,
    reduction: str = "mean",
) -> mx.array:
    if error.ndim != 1:
        raise ValueError(f"ranking loss expects one-dimensional errors, got {error.shape}")
    count = int(penalize_ratio * error.shape[0])
    if count <= 0:
        raise ValueError("ranking loss requires at least one selected error")
    indices = mx.argsort(error)
    sorted_error = mx.sort(error)
    selected = sorted_error[indices[:count]]
    if extra_weights is not None:
        selected = selected * extra_weights[indices[:count]]
    if reduction == "mean":
        return mx.mean(selected)
    if reduction == "sum":
        return mx.sum(selected)
    raise ValueError(f"unsupported ranking reduction {reduction!r}")


def geometry_regularization_samples(
    geometry: InstantNSRGeometry,
    *,
    count: int = 2048,
    perturb_std: float = 1e-2,
    key: mx.array | None = None,
) -> dict[str, mx.array]:
    if key is None:
        point_key = perturb_key = None
    else:
        point_key, perturb_key = mx.random.split(key)
    points = mx.random.uniform(low=-1.0, high=1.0, shape=(count, 3), key=point_key)
    random_sdf, random_gradient = geometry(
        points,
        with_grad=True,
        with_feature=False,
    )
    perturbed = points + mx.random.normal(points.shape, key=perturb_key) * perturb_std
    _, perturbed_gradient = geometry(
        perturbed,
        with_grad=True,
        with_feature=False,
    )
    return {
        "random_sdf": random_sdf,
        "random_sdf_grad": random_gradient,
        "normal_perturb": perturbed_gradient,
    }


def instant_nsr_losses(
    output: dict[str, mx.array],
    *,
    target_rgb: mx.array,
    target_normal: mx.array,
    foreground_mask: mx.array,
    rgb_mask: mx.array,
    ray_directions: mx.array,
    view_weights: mx.array,
    random_sdf: mx.array,
    random_sdf_gradient: mx.array,
    perturbed_sdf_gradient: mx.array,
    config: InstantNSRLossConfig = InstantNSRLossConfig(),
) -> dict[str, mx.array]:
    valid_rgb = output["rays_valid"] & rgb_mask.astype(mx.bool_)
    rgb_indices = _mask_indices(valid_rgb)
    selected_rgb = output["comp_rgb"][rgb_indices]
    selected_target_rgb = target_rgb[rgb_indices]
    rgb_error = mx.sum((selected_rgb - selected_target_rgb) ** 2, axis=-1)
    rgb_mse = released_ranking_loss(
        rgb_error,
        config.rgb_penalize_ratio,
        reduction="mean",
    )
    rgb_l1_error = mx.sum(
        mx.abs(selected_rgb - selected_target_rgb),
        axis=-1,
    )
    rgb_l1 = released_ranking_loss(rgb_l1_error, 0.8, reduction="mean")

    target_cosines = mx.sum(_normalize(ray_directions) * _normalize(target_normal), axis=-1)
    target_cosines = mx.where(target_cosines > -0.1, 0.0, target_cosines)
    normal_mask = foreground_mask.astype(mx.bool_) & (target_cosines < -0.1)
    normal_indices = _mask_indices(normal_mask)
    normal_error = 1.0 - mx.sum(
        _normalize(output["comp_normal"]) * _normalize(target_normal),
        axis=-1,
    )
    masked_normal_error = normal_error[normal_indices]
    masked_view_weights = view_weights[normal_indices]
    if config.geometry_aware_normals:
        geometry_weights = mx.exp(mx.abs(target_cosines))
        geometry_weights = geometry_weights / mx.sum(geometry_weights)
        masked_normal_error = masked_normal_error * geometry_weights[normal_indices]
        normal = released_ranking_loss(
            masked_normal_error,
            config.normal_penalize_ratio,
            extra_weights=masked_view_weights,
            reduction="sum",
        )
    else:
        normal = released_ranking_loss(
            masked_normal_error,
            config.normal_penalize_ratio,
            extra_weights=masked_view_weights,
            reduction="mean",
        )

    sample_mask = output["sample_mask"]
    sample_indices = _mask_indices(sample_mask)
    sampled_gradients = output["sdf_grad_samples"].reshape(-1, 3)[sample_indices]
    eikonal = mx.mean((mx.linalg.norm(sampled_gradients, axis=-1) - 1.0) ** 2)

    opacity = mx.clip(output["opacity"], 1e-3, 1.0 - 1e-3)
    target_mask = foreground_mask.astype(opacity.dtype)
    mask_error = -(
        target_mask * mx.log(opacity) + (1.0 - target_mask) * mx.log(1.0 - opacity)
    )
    mask = released_ranking_loss(
        mask_error,
        config.mask_penalize_ratio,
        extra_weights=view_weights,
        reduction="mean",
    )
    sparsity = mx.mean(mx.exp(-config.sparsity_scale * mx.abs(random_sdf)))
    normal_smooth = mx.mean(mx.abs(random_sdf_gradient - perturbed_sdf_gradient))

    losses = {
        "rgb_mse": rgb_mse,
        "rgb_l1": rgb_l1,
        "normal": normal,
        "eikonal": eikonal,
        "mask": mask,
        "sparsity": sparsity,
        "normal_smooth": normal_smooth,
    }
    losses["total"] = (
        config.rgb_mse * rgb_mse
        + config.rgb_l1 * rgb_l1
        + config.normal * normal
        + config.eikonal * eikonal
        + config.mask * mask
        + config.sparsity * sparsity
        + config.normal_smooth * normal_smooth
    )
    return losses
