"""Flow-matching schedulers for Hunyuan3D-2mv, ported to plain NumPy.

Both schedulers use *reversed* timesteps compared to the usual diffusers convention:
sigma runs 0 -> 1 while the sample goes from noise to clean.
"""

from __future__ import annotations

from typing import Optional, Sequence

import numpy as np


class FlowMatchEulerDiscreteScheduler:
    def __init__(self, num_train_timesteps: int = 1000, shift: float = 1.0):
        self.num_train_timesteps = num_train_timesteps
        self.shift = shift
        sigmas = np.linspace(1, num_train_timesteps, num_train_timesteps, dtype=np.float32)
        sigmas = sigmas / num_train_timesteps
        sigmas = shift * sigmas / (1 + (shift - 1) * sigmas)
        self.sigmas = sigmas
        self.timesteps = sigmas * num_train_timesteps
        self._step_index: Optional[int] = None

    def set_timesteps(self, num_inference_steps: Optional[int] = None,
                      sigmas: Optional[Sequence[float]] = None):
        if sigmas is None:
            if num_inference_steps is None:
                raise ValueError("Provide either num_inference_steps or sigmas")
            timesteps = np.linspace(
                self.sigmas[0] * self.num_train_timesteps,
                self.sigmas[-1] * self.num_train_timesteps,
                num_inference_steps,
            )
            sigmas = timesteps / self.num_train_timesteps
        sigmas = np.asarray(sigmas, dtype=np.float32)
        sigmas = self.shift * sigmas / (1 + (self.shift - 1) * sigmas)
        self.timesteps = sigmas * self.num_train_timesteps
        self.sigmas = np.concatenate([sigmas, np.ones(1, dtype=np.float32)])
        self._step_index = None
        return self.timesteps

    def step(self, model_output, timestep, sample):
        if self._step_index is None:
            self._step_index = int(np.flatnonzero(self.timesteps == timestep)[0])
        sigma = self.sigmas[self._step_index]
        sigma_next = self.sigmas[self._step_index + 1]
        self._step_index += 1
        return sample + (sigma_next - sigma) * model_output


class ConsistencyFlowMatchEulerDiscreteScheduler:
    """Scheduler for the step-distilled ("turbo") checkpoints."""

    def __init__(self, num_train_timesteps: int = 1000, pcm_timesteps: int = 50):
        self.num_train_timesteps = num_train_timesteps
        self.pcm_timesteps = pcm_timesteps
        sigmas = np.linspace(0, 1, num_train_timesteps)
        step_ratio = num_train_timesteps // pcm_timesteps
        euler_timesteps = (np.arange(1, pcm_timesteps) * step_ratio).round().astype(np.int64) - 1
        euler_timesteps = np.asarray([0] + euler_timesteps.tolist())
        self.euler_timesteps = euler_timesteps
        self._base_sigmas = sigmas[euler_timesteps].astype(np.float32)
        self.sigmas = self._base_sigmas
        self.timesteps = self._base_sigmas * num_train_timesteps
        self._step_index: Optional[int] = None

    def set_timesteps(self, num_inference_steps: Optional[int] = None,
                      sigmas: Optional[Sequence[float]] = None):
        if num_inference_steps is None:
            if sigmas is None:
                raise ValueError("Provide either num_inference_steps or sigmas")
            num_inference_steps = len(sigmas)
        indices = np.floor(
            np.linspace(0, self.pcm_timesteps, num=num_inference_steps, endpoint=False)
        ).astype(np.int64)
        selected = self._base_sigmas[indices]
        self.timesteps = selected * self.num_train_timesteps
        self.sigmas = np.concatenate([selected, np.ones(1, dtype=np.float32)])
        self._step_index = None
        return self.timesteps

    def step(self, model_output, timestep, sample):
        if self._step_index is None:
            self._step_index = int(np.flatnonzero(self.timesteps == timestep)[0])
        sigma = self.sigmas[self._step_index]
        sigma_next = self.sigmas[self._step_index + 1]
        self._step_index += 1
        return sample + (sigma_next - sigma) * model_output


SCHEDULERS = {
    "FlowMatchEulerDiscreteScheduler": FlowMatchEulerDiscreteScheduler,
    "ConsistencyFlowMatchEulerDiscreteScheduler": ConsistencyFlowMatchEulerDiscreteScheduler,
}


def build_scheduler(target: str, params: dict):
    name = target.rsplit(".", 1)[-1]
    if name not in SCHEDULERS:
        raise ValueError(f"Unsupported scheduler {target}")
    return SCHEDULERS[name](**params)
