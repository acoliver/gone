"""Correctness-first fixed-step NeuS rendering for the native MLX Instant-NSR port."""

from __future__ import annotations

import math
from dataclasses import dataclass

import mlx.core as mx
import mlx.nn as nn

from .instant_nsr import InstantNSRGeometry
from .instant_nsr_occupancy import NeuSOccupancyGrid


@dataclass(frozen=True)
class NeuSRenderConfig:
    radius: float = 1.0
    num_samples_per_ray: int = 1024
    cos_anneal_end: int = 20_000
    background_color: tuple[float, float, float] = (1.0, 1.0, 1.0)

    def __post_init__(self) -> None:
        if self.radius <= 0.0:
            raise ValueError("render radius must be positive")
        if self.num_samples_per_ray <= 0:
            raise ValueError("samples per ray must be positive")
        if self.cos_anneal_end < 0:
            raise ValueError("cosine anneal end must be non-negative")
        if len(self.background_color) != 3:
            raise ValueError("background color must have three channels")


class VarianceNetwork(nn.Module):
    def __init__(self, initial_value: float = 0.3):
        super().__init__()
        self.variance = mx.array(initial_value, dtype=mx.float32)

    @property
    def inverse_variance(self) -> mx.array:
        return mx.exp(self.variance * 10.0)

    def __call__(self, count: int) -> mx.array:
        return mx.broadcast_to(self.inverse_variance, (count, 1))


class ReLULinear(nn.Module):
    def __init__(self, input_dim: int, output_dim: int):
        super().__init__()
        bound = math.sqrt(6.0 / input_dim)
        self.weight = mx.random.uniform(
            low=-bound,
            high=bound,
            shape=(output_dim, input_dim),
        )
        self.bias = mx.zeros((output_dim,))

    def __call__(self, x: mx.array) -> mx.array:
        return x @ self.weight.T + self.bias


class RadianceMLP(nn.Module):
    """View-independent 16→64→64→3 color network from Era3D's NSR config."""

    def __init__(self, feature_dim: int = 13, hidden_dim: int = 64):
        super().__init__()
        self.first = ReLULinear(feature_dim + 3, hidden_dim)
        self.hidden = ReLULinear(hidden_dim, hidden_dim)
        self.final = ReLULinear(hidden_dim, 3)

    def __call__(self, feature: mx.array, normal: mx.array) -> mx.array:
        x = mx.concatenate((feature, normal), axis=-1).astype(mx.float32)
        x = nn.relu(self.first(x))
        x = nn.relu(self.hidden(x))
        return mx.sigmoid(self.final(x))


def _normalize(vector: mx.array, epsilon: float = 1e-8) -> mx.array:
    return vector / mx.maximum(mx.linalg.norm(vector, axis=-1, keepdims=True), epsilon)


def ray_aabb_intersection(
    origins: mx.array,
    directions: mx.array,
    radius: float,
) -> tuple[mx.array, mx.array, mx.array]:
    if origins.shape != directions.shape or origins.ndim != 2 or origins.shape[-1] != 3:
        raise ValueError(
            f"ray origins and directions must both be [N,3], got {origins.shape}/{directions.shape}"
        )
    parallel = mx.abs(directions) < 1e-9
    inside = mx.abs(origins) <= radius
    safe_directions = mx.where(parallel, 1.0, directions)
    t0 = (-radius - origins) / safe_directions
    t1 = (radius - origins) / safe_directions
    axis_near = mx.minimum(t0, t1)
    axis_far = mx.maximum(t0, t1)
    axis_near = mx.where(parallel & inside, -mx.inf, axis_near)
    axis_far = mx.where(parallel & inside, mx.inf, axis_far)
    axis_near = mx.where(parallel & ~inside, mx.inf, axis_near)
    axis_far = mx.where(parallel & ~inside, -mx.inf, axis_far)
    near = mx.maximum(mx.max(axis_near, axis=-1), 0.0)
    far = mx.min(axis_far, axis=-1)
    hit = far > near
    return near, far, hit


def neus_alpha(
    sdf: mx.array,
    normal: mx.array,
    directions: mx.array,
    distances: mx.array,
    inverse_variance: mx.array,
    cosine_anneal_ratio: float,
) -> mx.array:
    true_cosine = mx.sum(directions * normal, axis=-1)
    iter_cosine = -(
        nn.relu(-true_cosine * 0.5 + 0.5) * (1.0 - cosine_anneal_ratio)
        + nn.relu(-true_cosine) * cosine_anneal_ratio
    )
    estimated_next_sdf = sdf + iter_cosine * distances * 0.5
    estimated_previous_sdf = sdf - iter_cosine * distances * 0.5
    previous_cdf = mx.sigmoid(estimated_previous_sdf * inverse_variance)
    next_cdf = mx.sigmoid(estimated_next_sdf * inverse_variance)
    return mx.clip((previous_cdf - next_cdf + 1e-5) / (previous_cdf + 1e-5), 0.0, 1.0)


def alpha_weights(alpha: mx.array) -> mx.array:
    transmittance = mx.cumprod(
        mx.concatenate((mx.ones_like(alpha[..., :1]), 1.0 - alpha + 1e-10), axis=-1),
        axis=-1,
    )[..., :-1]
    return alpha * transmittance


class FixedStepNeuSRenderer(nn.Module):
    def __init__(
        self,
        geometry: InstantNSRGeometry,
        texture: RadianceMLP,
        config: NeuSRenderConfig = NeuSRenderConfig(),
        occupancy_grid: NeuSOccupancyGrid | None = None,
    ):
        super().__init__()
        self.geometry = geometry
        self.texture = texture
        self.config = config
        self.occupancy_grid = occupancy_grid
        self.variance = VarianceNetwork()
        self.cosine_anneal_ratio = 0.0
        self.render_step_size = 1.732 * 2.0 * config.radius / config.num_samples_per_ray
        self.max_steps = math.ceil(2.0 * math.sqrt(3.0) * config.radius / self.render_step_size)

    def update_step(self, global_step: int) -> None:
        self.geometry.update_step(global_step)
        if self.config.cos_anneal_end == 0:
            self.cosine_anneal_ratio = 1.0
        else:
            self.cosine_anneal_ratio = min(1.0, global_step / self.config.cos_anneal_end)

    def __call__(self, origins: mx.array, directions: mx.array) -> dict[str, mx.array]:
        directions = _normalize(directions)
        near, far, hit = ray_aabb_intersection(origins, directions, self.config.radius)
        steps = mx.arange(self.max_steps, dtype=origins.dtype)[None, :]
        starts = near[:, None] + steps * self.render_step_size
        ends = mx.minimum(starts + self.render_step_size, far[:, None])
        valid = hit[:, None] & (starts < far[:, None])
        distances = mx.where(valid, ends - starts, 0.0)
        midpoints = mx.where(valid, (starts + ends) * 0.5, 0.0)
        positions = origins[:, None, :] + directions[:, None, :] * midpoints[..., None]
        positions = mx.where(valid[..., None], positions, 0.0)

        if self.occupancy_grid is not None and self.occupancy_grid.initialized:
            valid = valid & self.occupancy_grid.query(positions)
            flat_valid = valid.reshape(-1)
            active_count = int(mx.sum(flat_valid).item())
            if active_count <= 0:
                raise RuntimeError("occupancy pruning removed every NeuS ray sample")
            active_indices = mx.argsort(mx.where(flat_valid, 0, 1))[:active_count]
            active_positions = positions.reshape(-1, 3)[active_indices]
            active_directions = mx.broadcast_to(directions[:, None, :], positions.shape)
            active_directions = active_directions.reshape(-1, 3)[active_indices]
            active_distances = distances.reshape(-1)[active_indices]
            active_sdf, active_gradient, active_feature = self.geometry(
                active_positions,
                with_grad=True,
                with_feature=True,
            )
            active_normal = _normalize(active_gradient)
            inverse_variance = mx.clip(self.variance.inverse_variance, 1e-6, 1e6)
            active_alpha = neus_alpha(
                active_sdf,
                active_normal,
                active_directions,
                active_distances,
                inverse_variance,
                self.cosine_anneal_ratio,
            )
            active_rgb = self.texture(active_feature, active_normal)
            flat_shape = (positions.shape[0] * positions.shape[1],)
            sdf = mx.zeros(flat_shape, dtype=active_sdf.dtype).at[active_indices].add(active_sdf)
            sdf_gradient = mx.zeros((*flat_shape, 3), dtype=active_gradient.dtype)
            sdf_gradient = sdf_gradient.at[active_indices].add(active_gradient)
            normal = mx.zeros((*flat_shape, 3), dtype=active_normal.dtype)
            normal = normal.at[active_indices].add(active_normal)
            rgb = mx.zeros((*flat_shape, 3), dtype=active_rgb.dtype)
            rgb = rgb.at[active_indices].add(active_rgb)
            alpha = mx.zeros(flat_shape, dtype=active_alpha.dtype).at[active_indices].add(active_alpha)
            matrix_shape = valid.shape
            sdf = sdf.reshape(matrix_shape)
            sdf_gradient = sdf_gradient.reshape((*matrix_shape, 3))
            normal = normal.reshape((*matrix_shape, 3))
            rgb = rgb.reshape((*matrix_shape, 3))
            alpha = alpha.reshape(matrix_shape)
        else:
            sdf, sdf_gradient, feature = self.geometry(
                positions,
                with_grad=True,
                with_feature=True,
            )
            normal = _normalize(sdf_gradient)
            inverse_variance = mx.clip(self.variance.inverse_variance, 1e-6, 1e6)
            alpha = neus_alpha(
                sdf,
                normal,
                mx.broadcast_to(directions[:, None, :], normal.shape),
                distances,
                inverse_variance,
                self.cosine_anneal_ratio,
            )
            alpha = mx.where(valid, alpha, 0.0)
            rgb = self.texture(feature, normal)
        weights = alpha_weights(alpha)

        opacity = mx.sum(weights, axis=-1)
        depth = mx.sum(weights * midpoints, axis=-1)
        composite_rgb = mx.sum(weights[..., None] * rgb, axis=-2)
        background = mx.array(self.config.background_color, dtype=composite_rgb.dtype)
        composite_rgb = composite_rgb + background * (1.0 - opacity[..., None])
        composite_normal = _normalize(mx.sum(weights[..., None] * normal, axis=-2))
        return {
            "comp_rgb": composite_rgb,
            "comp_normal": composite_normal,
            "opacity": opacity,
            "depth": depth,
            "rays_valid": opacity > 0.0,
            "num_samples": mx.sum(valid, axis=-1),
            "sdf_samples": sdf,
            "sdf_grad_samples": sdf_gradient,
            "weights": weights,
            "midpoints": midpoints,
            "intervals": distances,
            "sample_mask": valid,
            "inv_s": inverse_variance,
        }
