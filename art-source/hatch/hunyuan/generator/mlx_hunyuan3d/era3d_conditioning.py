"""Era3D Stable-unCLIP image embedding normalization and explicit noising."""

from __future__ import annotations

import math

import mlx.core as mx
import mlx.nn as nn
import numpy as np

from mlx_hunyuan3d.era3d_io import cfg_task_layout


class EraImageNormalizer(nn.Module):
    def __init__(self, embedding_dim: int):
        super().__init__()
        self.mean = mx.zeros((1, embedding_dim))
        self.std = mx.ones((1, embedding_dim))

    def scale(self, embeddings: mx.array) -> mx.array:
        return (embeddings - self.mean) / self.std

    def unscale(self, embeddings: mx.array) -> mx.array:
        return embeddings * self.std + self.mean


def squared_cosine_alphas_cumprod(num_train_timesteps: int = 1000) -> mx.array:
    """Construct Diffusers' `squaredcos_cap_v2` schedule in its float32 order."""
    def alpha_bar(time: float) -> float:
        return math.cos((time + 0.008) / 1.008 * math.pi / 2) ** 2

    betas = []
    for index in range(num_train_timesteps):
        start = index / num_train_timesteps
        end = (index + 1) / num_train_timesteps
        betas.append(min(1 - alpha_bar(end) / alpha_bar(start), 0.999))
    betas = mx.array(np.asarray(betas, dtype=np.float32))
    return mx.cumprod(1.0 - betas)


def timestep_embedding(timesteps: mx.array, embedding_dim: int) -> mx.array:
    """Diffusers embedding with `flip_sin_to_cos=True` and frequency shift zero."""
    if timesteps.ndim != 1:
        raise ValueError(f"timesteps must be rank one, got {timesteps.shape}")
    half = embedding_dim // 2
    exponent = -math.log(10_000) * mx.arange(half, dtype=mx.float32) / half
    phases = timesteps.astype(mx.float32)[:, None] * mx.exp(exponent)[None]
    embedding = mx.concatenate([mx.cos(phases), mx.sin(phases)], axis=-1)
    if embedding_dim % 2:
        embedding = mx.pad(embedding, [(0, 0), (0, 1)])
    return embedding


def noise_image_embeddings(
    embeddings: mx.array,
    noise: mx.array,
    normalizer: EraImageNormalizer,
    *,
    noise_level: int = 0,
    alphas_cumprod: mx.array | None = None,
) -> mx.array:
    """Return explicit-noise Stable-unCLIP conditioning with appended level embedding."""
    if embeddings.shape != noise.shape:
        raise ValueError(f"image embedding/noise shape mismatch: {embeddings.shape} vs {noise.shape}")
    if noise_level < 0 or noise_level >= 1000:
        raise ValueError(f"noise level must be in [0,999], got {noise_level}")
    alphas = squared_cosine_alphas_cumprod() if alphas_cumprod is None else alphas_cumprod
    alpha = alphas[noise_level].astype(embeddings.dtype)
    scaled = normalizer.scale(embeddings)
    noised = mx.sqrt(alpha) * scaled + mx.sqrt(1 - alpha) * noise
    unscaled = normalizer.unscale(noised)
    levels = mx.full((embeddings.shape[0],), noise_level, dtype=mx.int32)
    level_embedding = timestep_embedding(levels, embeddings.shape[-1]).astype(embeddings.dtype)
    return mx.concatenate([unscaled, level_embedding], axis=-1)


def encode_clip_condition(
    clip_model,
    pixels: mx.array,
    noise: mx.array,
    normalizer: EraImageNormalizer,
    *,
    noise_level: int = 0,
) -> tuple[mx.array, mx.array]:
    """Encode/cache the 12 base images, returning base and 24-sample CFG conditioning."""
    embeddings = clip_model(pixels)
    if embeddings.shape[0] != 12:
        raise ValueError(f"Era3D CLIP base batch must be 12, got {embeddings.shape}")
    conditioned = noise_image_embeddings(
        embeddings, noise, normalizer, noise_level=noise_level
    )
    return conditioned, cfg_task_layout(conditioned, zero_unconditional=True)


def encode_vae_condition(vae, pixels: mx.array) -> tuple[mx.array, mx.array]:
    """Encode posterior modes and return scaled 12-base/24-CFG NHWC latents."""
    if pixels.shape[0] != 12:
        raise ValueError(f"Era3D VAE base batch must be 12, got {pixels.shape}")
    latents = vae.encode(pixels)
    if latents.shape[0] != 12 or latents.shape[-1] != 4:
        raise ValueError(f"Era3D VAE produced inconsistent latents {latents.shape}")
    return latents, cfg_task_layout(latents, zero_unconditional=True)
