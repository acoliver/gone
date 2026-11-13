"""Native MLX geometry primitives for Era3D's Instant-NSR reconstruction stage."""

from __future__ import annotations

import math
from dataclasses import dataclass

import mlx.core as mx
import mlx.nn as nn

_HASH_FACTORS = (1, 2_654_435_761, 805_459_861)
_CORNERS = tuple((x, y, z) for x in (0, 1) for y in (0, 1) for z in (0, 1))


@dataclass(frozen=True)
class HashGridConfig:
    n_levels: int = 10
    n_features_per_level: int = 2
    log2_hashmap_size: int = 19
    base_resolution: int = 32
    per_level_scale: float = 1.3195079107728942
    start_level: int = 4
    start_step: int = 0
    update_steps: int = 1000

    def __post_init__(self) -> None:
        if self.n_levels <= 0 or self.n_features_per_level <= 0:
            raise ValueError("hash-grid levels and features must be positive")
        if self.log2_hashmap_size <= 0 or self.base_resolution <= 1:
            raise ValueError("hash-map size and base resolution must be greater than one")
        if self.per_level_scale <= 1.0:
            raise ValueError("per-level scale must be greater than one")
        if not 0 <= self.start_level <= self.n_levels:
            raise ValueError("start level must be between zero and n_levels")
        if self.update_steps <= 0:
            raise ValueError("update_steps must be positive")


@dataclass(frozen=True)
class InstantNSRGeometryConfig:
    radius: float = 1.0
    feature_dim: int = 13
    hidden_dim: int = 64
    sphere_init_radius: float = 0.5
    hash_grid: HashGridConfig = HashGridConfig()

    def __post_init__(self) -> None:
        if self.radius <= 0.0:
            raise ValueError("geometry radius must be positive")
        if self.feature_dim <= 0 or self.hidden_dim <= 0:
            raise ValueError("geometry feature and hidden dimensions must be positive")


def _round_up(value: int, multiple: int) -> int:
    return (value + multiple - 1) // multiple * multiple


def _level_shape(config: HashGridConfig, level: int) -> tuple[float, int, int]:
    scale = math.exp2(level * math.log2(config.per_level_scale)) * config.base_resolution - 1.0
    resolution = math.ceil(scale) + 1
    table_size = min(1 << config.log2_hashmap_size, _round_up(resolution**3, 8))
    return scale, resolution, table_size


class ProgressiveHashGrid(nn.Module):
    """tiny-cuda-nn-compatible 3D hash-grid encoding with progressive level masking."""

    def __init__(self, config: HashGridConfig = HashGridConfig()):
        super().__init__()
        self.config = config
        shapes = [_level_shape(config, level) for level in range(config.n_levels)]
        self.scales = tuple(shape[0] for shape in shapes)
        self.resolutions = tuple(shape[1] for shape in shapes)
        self.table_sizes = tuple(shape[2] for shape in shapes)
        offsets = [0]
        for table_size in self.table_sizes:
            offsets.append(offsets[-1] + table_size)
        self.offsets = tuple(offsets)
        self.embeddings = mx.random.uniform(
            low=-1e-4,
            high=1e-4,
            shape=(offsets[-1], config.n_features_per_level),
        )
        self.current_level = config.start_level

    @property
    def output_dim(self) -> int:
        return self.config.n_levels * self.config.n_features_per_level

    def update_step(self, global_step: int) -> None:
        config = self.config
        elapsed = max(global_step - config.start_step, 0)
        self.current_level = min(
            config.start_level + elapsed // config.update_steps,
            config.n_levels,
        )

    def _indices(self, coordinates: mx.array, level: int) -> mx.array:
        resolution = self.resolutions[level]
        table_size = self.table_sizes[level]
        dense_size = resolution**3
        if dense_size <= table_size:
            index = (
                coordinates[..., 0]
                + coordinates[..., 1] * resolution
                + coordinates[..., 2] * resolution * resolution
            )
        else:
            unsigned = coordinates.astype(mx.uint32)
            index = unsigned[..., 0] * _HASH_FACTORS[0]
            index = index ^ (unsigned[..., 1] * _HASH_FACTORS[1])
            index = index ^ (unsigned[..., 2] * _HASH_FACTORS[2])
        return (index % table_size).astype(mx.int32) + self.offsets[level]

    def _encode_level(self, points: mx.array, level: int) -> mx.array:
        position = points * self.scales[level] + 0.5
        base = mx.floor(position).astype(mx.int32)
        fraction = position - base
        encoded = mx.zeros((*points.shape[:-1], self.config.n_features_per_level))
        for corner in _CORNERS:
            corner_array = mx.array(corner, dtype=mx.int32)
            corner_position = base + corner_array
            corner_fraction = mx.array(corner, dtype=points.dtype)
            weights = mx.prod(mx.where(corner_fraction == 1, fraction, 1.0 - fraction), axis=-1)
            encoded = encoded + self.embeddings[self._indices(corner_position, level)] * weights[..., None]
        return encoded

    def __call__(self, points: mx.array) -> mx.array:
        if points.ndim < 1 or points.shape[-1] != 3:
            raise ValueError(f"hash-grid points must end in three coordinates, got {points.shape}")
        levels = []
        for level in range(self.config.n_levels):
            if level < self.current_level:
                levels.append(self._encode_level(points, level))
            else:
                levels.append(
                    mx.zeros((*points.shape[:-1], self.config.n_features_per_level), points.dtype)
                )
        return mx.concatenate(levels, axis=-1)


class WeightNormLinear(nn.Module):
    def __init__(self, weight: mx.array, bias: mx.array):
        super().__init__()
        self.weight_v = weight
        self.weight_g = mx.linalg.norm(weight, axis=1, keepdims=True)
        self.bias = bias

    def __call__(self, x: mx.array) -> mx.array:
        weight = self.weight_v * self.weight_g / mx.linalg.norm(
            self.weight_v, axis=1, keepdims=True
        )
        return x @ weight.T + self.bias


class SphereInitializedMLP(nn.Module):
    """Official one-hidden-layer, weight-normalized Instant-NSR SDF network."""

    def __init__(
        self,
        input_dim: int,
        output_dim: int = 13,
        hidden_dim: int = 64,
        sphere_radius: float = 0.5,
    ):
        super().__init__()
        first_weight = mx.zeros((hidden_dim, input_dim))
        xyz_weight = mx.random.normal((hidden_dim, 3)) * math.sqrt(2.0 / hidden_dim)
        first_weight = mx.concatenate((xyz_weight, first_weight[:, 3:]), axis=1)
        first_bias = mx.zeros((hidden_dim,))

        final_weight = (
            mx.random.normal((output_dim, hidden_dim)) * 1e-4
            + math.sqrt(math.pi / hidden_dim)
        )
        final_bias = mx.full((output_dim,), -sphere_radius)
        self.first = WeightNormLinear(first_weight, first_bias)
        self.final = WeightNormLinear(final_weight, final_bias)

    @staticmethod
    def _softplus(x: mx.array) -> mx.array:
        scaled = 100.0 * x
        return mx.maximum(scaled, 0.0) / 100.0 + mx.log1p(mx.exp(-mx.abs(scaled))) / 100.0

    def __call__(self, x: mx.array) -> mx.array:
        return self.final(self._softplus(self.first(x.astype(mx.float32))))


def contract_to_unisphere(points: mx.array, radius: float) -> mx.array:
    return (points + radius) / (2.0 * radius)


class InstantNSRGeometry(nn.Module):
    """Progressive hash-grid SDF and finite-difference normals from Instant-NSR."""

    def __init__(self, config: InstantNSRGeometryConfig = InstantNSRGeometryConfig()):
        super().__init__()
        self.config = config
        self.encoding = ProgressiveHashGrid(config.hash_grid)
        self.network = SphereInitializedMLP(
            input_dim=3 + self.encoding.output_dim,
            output_dim=config.feature_dim,
            hidden_dim=config.hidden_dim,
            sphere_radius=config.sphere_init_radius,
        )
        self.finite_difference_eps = 0.0
        self.update_step(0)

    def update_step(self, global_step: int) -> None:
        self.encoding.update_step(global_step)
        config = self.config.hash_grid
        grid_resolution = (
            config.base_resolution
            * config.per_level_scale ** (self.encoding.current_level - 1)
        )
        self.finite_difference_eps = 2.0 * self.config.radius / grid_resolution

    def _evaluate(self, points: mx.array) -> mx.array:
        normalized = contract_to_unisphere(points, self.config.radius)
        encoded = self.encoding(normalized)
        network_input = mx.concatenate((normalized * 2.0 - 1.0, encoded), axis=-1)
        return self.network(network_input)

    def forward_level(self, points: mx.array) -> mx.array:
        return self._evaluate(points)[..., 0]

    def __call__(
        self,
        points: mx.array,
        *,
        with_grad: bool = True,
        with_feature: bool = True,
        with_laplace: bool = False,
    ) -> mx.array | tuple[mx.array, ...]:
        output = self._evaluate(points)
        sdf = output[..., 0]
        values: list[mx.array] = [sdf]
        if with_grad or with_laplace:
            eps = self.finite_difference_eps
            offsets = mx.array(
                (
                    (eps, 0.0, 0.0),
                    (-eps, 0.0, 0.0),
                    (0.0, eps, 0.0),
                    (0.0, -eps, 0.0),
                    (0.0, 0.0, eps),
                    (0.0, 0.0, -eps),
                ),
                dtype=points.dtype,
            )
            displaced = mx.clip(
                points[..., None, :] + offsets,
                -self.config.radius,
                self.config.radius,
            )
            displaced_sdf = self._evaluate(displaced)[..., 0]
            if with_grad:
                gradient = 0.5 * (
                    displaced_sdf[..., 0::2] - displaced_sdf[..., 1::2]
                ) / eps
                values.append(gradient)
            if with_feature:
                values.append(output)
            if with_laplace:
                laplace = mx.sum(
                    displaced_sdf[..., 0::2]
                    + displaced_sdf[..., 1::2]
                    - 2.0 * sdf[..., None],
                    axis=-1,
                ) / (eps**2)
                values.append(laplace)
        elif with_feature:
            values.append(output)
        return values[0] if len(values) == 1 else tuple(values)
