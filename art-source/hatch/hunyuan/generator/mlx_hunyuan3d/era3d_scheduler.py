"""Exact 40-step ancestral DDIM scheduler used by released Era3D inference."""

from __future__ import annotations

import mlx.core as mx
import numpy as np


class EraDDIMScheduler:
    def __init__(self, config: dict, num_inference_steps: int = 40):
        if config["prediction_type"] != "v_prediction":
            raise ValueError("Era3D DDIM requires v_prediction")
        if config["beta_schedule"] != "linear" or config["timestep_spacing"] != "leading":
            raise ValueError("Era3D DDIM requires the released linear/leading schedule")
        if config["clip_sample"] or config["thresholding"]:
            raise ValueError("Era3D DDIM does not clip or threshold predicted samples")
        self.num_train_timesteps = int(config["num_train_timesteps"])
        self.num_inference_steps = num_inference_steps
        betas = np.linspace(
            config["beta_start"], config["beta_end"], self.num_train_timesteps,
            dtype=np.float32,
        )
        alphas = mx.cumprod(1.0 - mx.array(betas))
        mx.eval(alphas)
        self.alphas_cumprod = np.asarray(alphas)
        self.final_alpha_cumprod = (
            1.0 if config["set_alpha_to_one"] else float(self.alphas_cumprod[0])
        )
        step_ratio = self.num_train_timesteps // num_inference_steps
        timesteps = np.arange(num_inference_steps, dtype=np.float64) * step_ratio
        self.timesteps = timesteps.round().astype(np.int64)[::-1] + int(config["steps_offset"])
        self.init_noise_sigma = 1.0

    def __len__(self) -> int:
        return self.num_inference_steps

    def _variance(self, timestep: int, previous_timestep: int) -> float:
        alpha_t = float(self.alphas_cumprod[timestep])
        alpha_previous = (
            float(self.alphas_cumprod[previous_timestep])
            if previous_timestep >= 0 else self.final_alpha_cumprod
        )
        beta_t = 1.0 - alpha_t
        beta_previous = 1.0 - alpha_previous
        return (beta_previous / beta_t) * (1.0 - alpha_t / alpha_previous)

    def step(self, model_output: mx.array, step_index: int, sample: mx.array,
             variance_noise: mx.array, eta: float = 1.0) -> mx.array:
        """Perform one explicit-noise DDIM update and return the preceding latent."""
        if model_output.shape != sample.shape or variance_noise.shape != sample.shape:
            raise ValueError("DDIM model output, sample, and variance noise shapes must match")
        timestep = int(self.timesteps[step_index])
        previous_timestep = timestep - self.num_train_timesteps // self.num_inference_steps
        alpha_t = float(self.alphas_cumprod[timestep])
        alpha_previous = (
            float(self.alphas_cumprod[previous_timestep])
            if previous_timestep >= 0 else self.final_alpha_cumprod
        )
        beta_t = 1.0 - alpha_t

        predicted_original = alpha_t ** 0.5 * sample - beta_t ** 0.5 * model_output
        predicted_epsilon = alpha_t ** 0.5 * model_output + beta_t ** 0.5 * sample
        std_dev = eta * self._variance(timestep, previous_timestep) ** 0.5
        direction_scale = max(1.0 - alpha_previous - std_dev ** 2, 0.0) ** 0.5
        previous = alpha_previous ** 0.5 * predicted_original
        previous = previous + direction_scale * predicted_epsilon
        if eta > 0:
            previous = previous + std_dev * variance_noise
        return previous
