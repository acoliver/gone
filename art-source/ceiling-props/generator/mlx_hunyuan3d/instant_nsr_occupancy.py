"""128³ NeuS occupancy grid compatible with the released nerfacc pruning rule."""

from __future__ import annotations

from dataclasses import dataclass

import mlx.core as mx
import numpy as np

from .instant_nsr import InstantNSRGeometry


@dataclass(frozen=True)
class OccupancyGridConfig:
    resolution: int = 128
    radius: float = 1.0
    threshold: float = 0.01
    ema_decay: float = 0.95
    update_every: int = 16
    warmup_steps: int = 256
    chunk_size: int = 262_144
    seed: int = 0

    def __post_init__(self) -> None:
        if self.resolution <= 1 or self.radius <= 0.0:
            raise ValueError("occupancy resolution must exceed one and radius must be positive")
        if self.threshold <= 0.0 or not 0.0 <= self.ema_decay < 1.0:
            raise ValueError("occupancy threshold must be positive and EMA decay must be in [0, 1)")
        if self.update_every <= 0 or self.chunk_size <= 0 or self.warmup_steps < 0:
            raise ValueError("occupancy intervals/chunks must be positive and warmup non-negative")


class NeuSOccupancyGrid:
    def __init__(self, config: OccupancyGridConfig = OccupancyGridConfig()):
        self.config = config
        shape = (config.resolution,) * 3
        self.values = np.zeros(shape, dtype=np.float32)
        self.binary = mx.zeros(shape, dtype=mx.bool_)
        self.initialized = False
        self.last_update_step = -1
        self.rng = np.random.default_rng(config.seed)

    def _points(self, flat_indices: np.ndarray) -> np.ndarray:
        resolution = self.config.resolution
        x = flat_indices // (resolution * resolution)
        y = (flat_indices // resolution) % resolution
        z = flat_indices % resolution
        coordinates = np.stack((x, y, z), axis=-1).astype(np.float32)
        coordinates += self.rng.random(coordinates.shape, dtype=np.float32)
        return (coordinates / resolution * 2.0 - 1.0) * self.config.radius

    def _update_indices(self, step: int) -> np.ndarray:
        total = self.config.resolution**3
        if step < self.config.warmup_steps or not self.initialized:
            return np.arange(total, dtype=np.int64)
        count = total // 4
        uniform = self.rng.integers(0, total, size=count, dtype=np.int64)
        occupied = np.flatnonzero(np.asarray(self.binary).reshape(-1))
        if occupied.size == 0:
            raise RuntimeError("cannot sample an empty initialized occupancy grid")
        if count < occupied.size:
            occupied = occupied[self.rng.integers(0, occupied.size, size=count)]
        return np.concatenate((uniform, occupied))

    def update(
        self,
        geometry: InstantNSRGeometry,
        inverse_variance: mx.array,
        render_step_size: float,
        step: int,
        *,
        force: bool = False,
    ) -> bool:
        if not force and step % self.config.update_every != 0:
            return False
        indices = self._update_indices(step)
        total = len(indices)
        updated = np.empty((total,), dtype=np.float32)
        scalar_inverse_variance = mx.clip(inverse_variance, 1e-6, 1e6)
        for start in range(0, total, self.config.chunk_size):
            stop = min(start + self.config.chunk_size, total)
            chunk_indices = indices[start:stop]
            sdf = geometry.forward_level(mx.array(self._points(chunk_indices)))
            previous_cdf = mx.sigmoid((sdf + render_step_size * 0.5) * scalar_inverse_variance)
            next_cdf = mx.sigmoid((sdf - render_step_size * 0.5) * scalar_inverse_variance)
            occupancy = mx.clip(
                (previous_cdf - next_cdf + 1e-5) / (previous_cdf + 1e-5),
                0.0,
                1.0,
            )
            updated[start:stop] = np.asarray(occupancy)

        flat_values = self.values.reshape(-1)
        flat_values[indices] = np.maximum(flat_values[indices] * self.config.ema_decay, updated)
        active_threshold = min(self.config.threshold, float(np.mean(self.values)))
        self.binary = mx.array(self.values > active_threshold)
        mx.eval(self.binary)
        if not bool(np.any(self.values > active_threshold)):
            raise RuntimeError("NeuS occupancy update produced an empty grid")
        self.initialized = True
        self.last_update_step = step
        return True

    def query(self, points: mx.array) -> mx.array:
        if points.shape[-1] != 3:
            raise ValueError(f"occupancy query points must end in three coordinates, got {points.shape}")
        normalized = (points / self.config.radius + 1.0) * 0.5
        coordinates = mx.floor(normalized * self.config.resolution).astype(mx.int32)
        coordinates = mx.clip(coordinates, 0, self.config.resolution - 1)
        inside = mx.all(mx.abs(points) <= self.config.radius, axis=-1)
        occupied = self.binary[
            coordinates[..., 0],
            coordinates[..., 1],
            coordinates[..., 2],
        ]
        return inside & occupied
