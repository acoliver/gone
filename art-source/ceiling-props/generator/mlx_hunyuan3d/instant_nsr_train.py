"""Bounded native-MLX optimization loop for orthographic Instant-NSR."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim
import mlx.utils
import numpy as np

from .instant_nsr_data import OrthographicViewDataset
from .instant_nsr_loss import (
    InstantNSRLossConfig,
    geometry_regularization_samples,
    instant_nsr_losses,
)
from .instant_nsr_render import FixedStepNeuSRenderer


@dataclass(frozen=True)
class InstantNSRTrainingConfig:
    max_steps: int = 3000
    constant_steps: int = 500
    final_learning_rate_ratio: float = 0.1
    geometry_learning_rate: float = 1e-3
    texture_learning_rate: float = 1e-2
    variance_learning_rate: float = 1e-3
    betas: tuple[float, float] = (0.9, 0.99)
    epsilon: float = 1e-15
    weight_decay: float = 0.01
    initial_ray_count: int = 256
    max_ray_count: int = 8192
    regularization_sample_count: int = 2048
    regularization_perturb_std: float = 1e-2
    seed: int = 0

    def __post_init__(self) -> None:
        if self.max_steps <= 0 or not 0 <= self.constant_steps < self.max_steps:
            raise ValueError("training steps must satisfy 0 <= constant_steps < max_steps")
        if not 0.0 < self.final_learning_rate_ratio <= 1.0:
            raise ValueError("final learning-rate ratio must be in (0, 1]")
        if min(
            self.geometry_learning_rate,
            self.texture_learning_rate,
            self.variance_learning_rate,
        ) <= 0.0:
            raise ValueError("all Instant-NSR learning rates must be positive")
        if self.initial_ray_count <= 0 or self.max_ray_count < self.initial_ray_count:
            raise ValueError("ray counts must be positive and max_ray_count must not be smaller")
        if self.regularization_sample_count <= 0:
            raise ValueError("regularization sample count must be positive")


def exponential_learning_rate(
    step: mx.array | int,
    *,
    initial: float,
    constant_steps: int,
    max_steps: int,
    final_ratio: float,
) -> mx.array:
    progress = mx.clip(
        (mx.array(step, dtype=mx.float32) - constant_steps) / (max_steps - constant_steps),
        0.0,
        1.0,
    )
    return initial * mx.power(final_ratio, progress)


def _optimizer(initial: float, config: InstantNSRTrainingConfig) -> optim.AdamW:
    def schedule(step: mx.array) -> mx.array:
        return exponential_learning_rate(
            step,
            initial=initial,
            constant_steps=config.constant_steps,
            max_steps=config.max_steps,
            final_ratio=config.final_learning_rate_ratio,
        )

    return optim.AdamW(
        learning_rate=schedule,
        betas=list(config.betas),
        eps=config.epsilon,
        weight_decay=config.weight_decay,
        bias_correction=True,
    )


def _save_tree(path: Path, tree: object) -> None:
    values = dict(mlx.utils.tree_flatten(tree))
    mx.savez(str(path), **values)


def _load_tree(path: Path) -> object:
    values = mx.load(str(path))
    return mlx.utils.tree_unflatten(list(values.items()))


class InstantNSRTrainer:
    def __init__(
        self,
        renderer: FixedStepNeuSRenderer,
        dataset: OrthographicViewDataset,
        config: InstantNSRTrainingConfig = InstantNSRTrainingConfig(),
        loss_config: InstantNSRLossConfig = InstantNSRLossConfig(),
    ):
        self.renderer = renderer
        self.dataset = dataset
        self.config = config
        self.loss_config = loss_config
        self.geometry_optimizer = _optimizer(config.geometry_learning_rate, config)
        self.texture_optimizer = _optimizer(config.texture_learning_rate, config)
        self.variance_optimizer = _optimizer(config.variance_learning_rate, config)
        self.step = 0
        self.ray_count = config.initial_ray_count
        self.rng = np.random.default_rng(config.seed)
        self.random_key = mx.random.key(config.seed)

    def _objective(
        self,
        batch: dict[str, mx.array],
        regularization_key: mx.array,
        captured: dict[str, dict[str, mx.array]],
    ) -> mx.array:
        output = self.renderer(batch["ray_origins"], batch["ray_directions"])
        regularization = geometry_regularization_samples(
            self.renderer.geometry,
            count=self.config.regularization_sample_count,
            perturb_std=self.config.regularization_perturb_std,
            key=regularization_key,
        )
        losses = instant_nsr_losses(
            output,
            target_rgb=batch["rgb"],
            target_normal=batch["normal"],
            foreground_mask=batch["foreground_mask"],
            rgb_mask=batch["rgb_mask"],
            ray_directions=batch["ray_directions"],
            view_weights=batch["view_weights"],
            random_sdf=regularization["random_sdf"],
            random_sdf_gradient=regularization["random_sdf_grad"],
            perturbed_sdf_gradient=regularization["normal_perturb"],
            config=self.loss_config,
        )
        captured["output"] = output
        captured["losses"] = losses
        return losses["total"]

    def train_step(self) -> dict[str, float | int]:
        if self.step >= self.config.max_steps:
            raise RuntimeError(f"training is already complete at step {self.step}")
        self.renderer.update_step(self.step)
        if self.renderer.occupancy_grid is not None:
            self.renderer.occupancy_grid.update(
                self.renderer.geometry,
                self.renderer.variance.inverse_variance,
                self.renderer.render_step_size,
                self.step,
            )
        batch = self.dataset.sample(self.ray_count, self.rng)
        self.random_key, regularization_key = mx.random.split(self.random_key)
        captured: dict[str, dict[str, mx.array]] = {}

        def objective() -> mx.array:
            return self._objective(batch, regularization_key, captured)

        loss, gradients = nn.value_and_grad(self.renderer, objective)()
        output = captured["output"]
        losses = captured["losses"]
        mx.eval(loss, gradients, losses, output["num_samples"])
        self.geometry_optimizer.update(self.renderer.geometry, gradients["geometry"])
        self.texture_optimizer.update(self.renderer.texture, gradients["texture"])
        self.variance_optimizer.update(self.renderer.variance, gradients["variance"])
        mx.eval(
            self.renderer.parameters(),
            self.geometry_optimizer.state,
            self.texture_optimizer.state,
            self.variance_optimizer.state,
        )

        used_ray_count = self.ray_count
        sample_count = int(mx.sum(output["num_samples"]).item())
        if sample_count <= 0:
            raise RuntimeError("Instant-NSR renderer produced no valid training samples")
        target_sample_count = (
            self.config.initial_ray_count * self.renderer.config.num_samples_per_ray
        )
        proposed = int(self.ray_count * target_sample_count / sample_count)
        self.ray_count = min(
            int(self.ray_count * 0.9 + proposed * 0.1),
            self.config.max_ray_count,
        )
        self.step += 1

        metrics: dict[str, float | int] = {
            name: float(value.item()) for name, value in losses.items()
        }
        metrics.update(
            {
                "step": self.step,
                "ray_count": used_ray_count,
                "next_ray_count": self.ray_count,
                "sample_count": sample_count,
                "geometry_learning_rate": float(
                    self.geometry_optimizer.learning_rate.item()
                ),
                "texture_learning_rate": float(self.texture_optimizer.learning_rate.item()),
                "variance_learning_rate": float(
                    self.variance_optimizer.learning_rate.item()
                ),
                "inverse_variance": float(output["inv_s"].item()),
            }
        )
        return metrics

    def save_checkpoint(self, directory: str | Path) -> None:
        checkpoint = Path(directory)
        checkpoint.mkdir(parents=True, exist_ok=True)
        self.renderer.save_weights(str(checkpoint / "model.safetensors"))
        _save_tree(checkpoint / "geometry_optimizer.npz", self.geometry_optimizer.state)
        _save_tree(checkpoint / "texture_optimizer.npz", self.texture_optimizer.state)
        _save_tree(checkpoint / "variance_optimizer.npz", self.variance_optimizer.state)
        metadata = {
            "step": self.step,
            "ray_count": self.ray_count,
            "numpy_rng_state": self.rng.bit_generator.state,
            "mlx_random_key": np.asarray(self.random_key).tolist(),
        }
        if self.renderer.occupancy_grid is not None:
            np.save(checkpoint / "occupancy.npy", self.renderer.occupancy_grid.values)
            metadata["occupancy_initialized"] = self.renderer.occupancy_grid.initialized
            metadata["occupancy_last_update_step"] = self.renderer.occupancy_grid.last_update_step
            metadata["occupancy_rng_state"] = self.renderer.occupancy_grid.rng.bit_generator.state
        (checkpoint / "trainer.json").write_text(json.dumps(metadata), encoding="utf-8")

    def load_checkpoint(self, directory: str | Path) -> None:
        checkpoint = Path(directory)
        metadata = json.loads((checkpoint / "trainer.json").read_text(encoding="utf-8"))
        self.renderer.load_weights(str(checkpoint / "model.safetensors"), strict=True)
        self.geometry_optimizer.state = _load_tree(checkpoint / "geometry_optimizer.npz")
        self.texture_optimizer.state = _load_tree(checkpoint / "texture_optimizer.npz")
        self.variance_optimizer.state = _load_tree(checkpoint / "variance_optimizer.npz")
        self.step = int(metadata["step"])
        self.ray_count = int(metadata["ray_count"])
        self.rng.bit_generator.state = metadata["numpy_rng_state"]
        self.random_key = mx.array(metadata["mlx_random_key"], dtype=mx.uint32)
        if self.renderer.occupancy_grid is not None:
            occupancy = np.load(checkpoint / "occupancy.npy")
            if occupancy.shape != self.renderer.occupancy_grid.values.shape:
                raise ValueError(
                    "checkpoint occupancy shape does not match the configured grid: "
                    f"{occupancy.shape} != {self.renderer.occupancy_grid.values.shape}"
                )
            self.renderer.occupancy_grid.values = occupancy.astype(np.float32)
            threshold = min(
                self.renderer.occupancy_grid.config.threshold,
                float(np.mean(occupancy)),
            )
            self.renderer.occupancy_grid.binary = mx.array(occupancy > threshold)
            self.renderer.occupancy_grid.initialized = bool(metadata["occupancy_initialized"])
            self.renderer.occupancy_grid.last_update_step = int(
                metadata["occupancy_last_update_step"]
            )
            self.renderer.occupancy_grid.rng.bit_generator.state = metadata[
                "occupancy_rng_state"
            ]
        self.renderer.update_step(self.step)
        mx.eval(
            self.renderer.parameters(),
            self.geometry_optimizer.state,
            self.texture_optimizer.state,
            self.variance_optimizer.state,
        )
