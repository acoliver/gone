"""LCM scheduler for the turbo paint model.

The checkpoint ships a DDIMScheduler config, but multiview_utils swaps it for an
LCMScheduler with timestep_spacing='trailing' and calls set_turbo(True). The turbo path
then ignores the usual "N evenly spaced steps" and picks an explicit timestep list out of a
30-step DDIM grid, so that selection is reproduced here rather than approximated.

Config that matters (scheduler/scheduler_config.json):
    beta_schedule        scaled_linear, 0.00085 -> 0.012 over 1000
    prediction_type      v_prediction
    rescale_betas_zero_snr  true
    clip_sample          false
"""

from __future__ import annotations

import mlx.core as mx
import numpy as np

NUM_TRAIN_TIMESTEPS = 1000
BETA_START = 0.00085
BETA_END = 0.012
SIGMA_DATA = 0.5
TIMESTEP_SCALING = 10.0


def _rescale_zero_terminal_snr(alphas_cumprod: np.ndarray) -> np.ndarray:
    """Shift the noise schedule so the final step has exactly zero signal.

    Without this the model is asked at inference to start from pure noise while having been
    trained on a schedule whose last step still leaks a little signal, which shows up as
    washed-out, low-contrast output rather than an obvious failure.
    """
    sqrt_alphas = np.sqrt(alphas_cumprod)
    first, last = sqrt_alphas[0].copy(), sqrt_alphas[-1].copy()
    sqrt_alphas = (sqrt_alphas - last) * (first / (first - last))
    rescaled = sqrt_alphas ** 2
    alphas = rescaled[1:] / rescaled[:-1]
    alphas = np.concatenate([rescaled[:1], alphas])
    return np.cumprod(alphas)


def build_alphas_cumprod() -> np.ndarray:
    betas = np.linspace(BETA_START ** 0.5, BETA_END ** 0.5, NUM_TRAIN_TIMESTEPS,
                        dtype=np.float64) ** 2
    return _rescale_zero_terminal_snr(np.cumprod(1.0 - betas))


def turbo_timesteps(ddim_steps: int = 30, stride: int = 3) -> np.ndarray:
    """The explicit schedule the turbo pipeline uses.

    Upstream builds a 30-entry DDIM grid and then walks it backwards in strides of 3
    (torch.range(29, 0, -3), which is inclusive), giving ten steps.
    """
    step_ratio = NUM_TRAIN_TIMESTEPS // ddim_steps
    grid = (np.arange(1, ddim_steps + 1) * step_ratio).round().astype(np.int64) - 1
    index = np.arange(ddim_steps - 1, -1, -stride)
    index = index[index >= 0]
    return grid[index]


class LCMScheduler:
    def __init__(self, ddim_steps: int = 30, stride: int = 3):
        self.alphas_cumprod = build_alphas_cumprod()
        self.timesteps = turbo_timesteps(ddim_steps, stride)
        self.final_alpha_cumprod = self.alphas_cumprod[0]
        self.init_noise_sigma = 1.0

    def __len__(self) -> int:
        return len(self.timesteps)

    def _boundary_scalings(self, timestep: int) -> tuple[float, float]:
        scaled = timestep * TIMESTEP_SCALING
        denom = scaled ** 2 + SIGMA_DATA ** 2
        return SIGMA_DATA ** 2 / denom, scaled / denom ** 0.5

    def step(self, model_output: mx.array, step_index: int, sample: mx.array,
             noise: mx.array | None = None) -> tuple[mx.array, mx.array]:
        """One LCM update. Returns (prev_sample, denoised)."""
        timestep = int(self.timesteps[step_index])
        alpha_t = float(self.alphas_cumprod[timestep])
        beta_t = 1.0 - alpha_t

        if step_index + 1 < len(self.timesteps):
            prev_t = int(self.timesteps[step_index + 1])
            alpha_prev = float(self.alphas_cumprod[prev_t])
        else:
            alpha_prev = float(self.final_alpha_cumprod)
        beta_prev = 1.0 - alpha_prev

        # v-prediction: x0 = sqrt(alpha) * x_t - sqrt(beta) * v
        predicted_original = (alpha_t ** 0.5) * sample - (beta_t ** 0.5) * model_output

        c_skip, c_out = self._boundary_scalings(timestep)
        denoised = c_out * predicted_original + c_skip * sample

        if step_index == len(self.timesteps) - 1:
            return denoised, denoised
        if noise is None:
            noise = mx.random.normal(sample.shape).astype(sample.dtype)
        prev_sample = (alpha_prev ** 0.5) * denoised + (beta_prev ** 0.5) * noise
        return prev_sample, denoised

    def add_noise(self, original: mx.array, noise: mx.array, timestep: int) -> mx.array:
        alpha = float(self.alphas_cumprod[timestep])
        return (alpha ** 0.5) * original + ((1.0 - alpha) ** 0.5) * noise


class EulerAncestralDiscreteScheduler:
    """Scheduler for the delight (InstructPix2Pix) model.

    Its checkpoint ships a DDIMScheduler config which the code then replaces with this,
    keeping the config values. Note the differences from the paint scheduler above:
    rescale_betas_zero_snr is FALSE here, and timestep_spacing is 'leading'.
    """

    def __init__(self, num_train_timesteps: int = NUM_TRAIN_TIMESTEPS,
                 steps_offset: int = 1):
        betas = np.linspace(BETA_START ** 0.5, BETA_END ** 0.5, num_train_timesteps,
                            dtype=np.float64) ** 2
        self.alphas_cumprod = np.cumprod(1.0 - betas)
        self.num_train_timesteps = num_train_timesteps
        self.steps_offset = steps_offset
        self.timesteps = np.array([], dtype=np.float64)
        self.sigmas = np.array([], dtype=np.float64)

    def set_timesteps(self, num_inference_steps: int):
        step_ratio = self.num_train_timesteps // num_inference_steps
        timesteps = (np.arange(0, num_inference_steps) * step_ratio).round()[::-1]
        timesteps = timesteps.astype(np.float64) + self.steps_offset

        sigmas = np.sqrt((1.0 - self.alphas_cumprod) / self.alphas_cumprod)
        sigmas = np.interp(timesteps, np.arange(len(sigmas)), sigmas)
        self.sigmas = np.concatenate([sigmas, [0.0]])
        self.timesteps = timesteps
        return timesteps

    @property
    def init_noise_sigma(self) -> float:
        return float(self.sigmas.max())

    def scale_model_input(self, sample: mx.array, step_index: int) -> mx.array:
        sigma = float(self.sigmas[step_index])
        return sample / ((sigma ** 2 + 1) ** 0.5)

    def step(self, model_output: mx.array, step_index: int, sample: mx.array,
             noise: mx.array | None = None) -> mx.array:
        sigma = float(self.sigmas[step_index])
        # v_prediction
        predicted_original = (
            model_output * (-sigma / (sigma ** 2 + 1) ** 0.5) + sample / (sigma ** 2 + 1)
        )
        sigma_from, sigma_to = sigma, float(self.sigmas[step_index + 1])
        sigma_up = min(
            sigma_to,
            (sigma_to ** 2 * (sigma_from ** 2 - sigma_to ** 2) / max(sigma_from ** 2, 1e-12))
            ** 0.5,
        )
        sigma_down = max(sigma_to ** 2 - sigma_up ** 2, 0.0) ** 0.5

        derivative = (sample - predicted_original) / max(sigma, 1e-12)
        prev_sample = sample + derivative * (sigma_down - sigma)
        if sigma_up > 0:
            if noise is None:
                noise = mx.random.normal(sample.shape).astype(sample.dtype)
            prev_sample = prev_sample + noise * sigma_up
        return prev_sample
