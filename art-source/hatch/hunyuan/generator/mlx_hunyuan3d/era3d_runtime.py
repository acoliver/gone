"""Staged Era3D inference with explicit noise and bounded model residency."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import gc
from pathlib import Path
from typing import Any

import mlx.core as mx
from PIL import Image

from mlx_hunyuan3d.era3d_conditioning import encode_clip_condition, encode_vae_condition
from mlx_hunyuan3d.era3d_io import (
    apply_cfg,
    base_prompt_layout,
    cfg_task_layout,
    clip_preprocess,
    generated_latent_cfg_layout,
    load_fixed_prompts,
    preprocess_rgba,
    quantize_task_images,
    task_images,
    vae_preprocess,
)
from mlx_hunyuan3d.era3d_scheduler import EraDDIMScheduler


@dataclass(frozen=True)
class Era3DPreparedInput:
    clip_pixels: mx.array
    vae_pixels: mx.array
    normal_prompts: mx.array
    color_prompts: mx.array


@dataclass(frozen=True)
class Era3DResult:
    normals: mx.array
    colors: mx.array
    pose: mx.array
    latents: mx.array


def prepare_era3d_input(image: Image.Image, model_dir: str | Path) -> Era3DPreparedInput:
    """Build both quantized image branches and load the audited six-view prompts."""
    rgb = preprocess_rgba(image)
    images = quantize_task_images(task_images(rgb))
    clip_pixels = mx.array(clip_preprocess(images, model_dir), dtype=mx.float16)
    vae_pixels = mx.array(vae_preprocess(images), dtype=mx.float16)
    normal_prompts, color_prompts = load_fixed_prompts(model_dir)
    return Era3DPreparedInput(
        clip_pixels=clip_pixels,
        vae_pixels=vae_pixels,
        normal_prompts=normal_prompts,
        color_prompts=color_prompts,
    )


def _clear_stage_cache() -> None:
    gc.collect()
    mx.clear_cache()


def run_staged_era3d(
    *,
    clip_stage_factory: Callable[[], tuple[Any, Any]],
    vae_factory: Callable[[], Any],
    unet_factory: Callable[[], Any],
    clip_pixels: mx.array,
    vae_pixels: mx.array,
    normal_prompts: mx.array,
    color_prompts: mx.array,
    embedding_noise: mx.array,
    initial_latents: mx.array,
    variance_noises: mx.array,
    scheduler_config: dict,
    noise_level: int = 0,
    guidance_scale: float = 3.0,
) -> Era3DResult:
    """Run CLIP → VAE encode → UNet → VAE decode without overlapping large models.

    Factories must return newly loaded components rather than retaining them in closures. The
    VAE factory is intentionally called twice so its encoder weights do not overlap the UNet.
    """
    if clip_pixels.shape != (12, 224, 224, 3):
        raise ValueError(f"Era3D CLIP pixels must be [12,224,224,3], got {clip_pixels.shape}")
    if vae_pixels.shape != (12, 512, 512, 3):
        raise ValueError(f"Era3D VAE pixels must be [12,512,512,3], got {vae_pixels.shape}")
    if embedding_noise.shape != (12, 1024):
        raise ValueError(f"Era3D embedding noise must be [12,1024], got {embedding_noise.shape}")
    if initial_latents.shape != (12, 64, 64, 4):
        raise ValueError(f"Era3D initial latents must be [12,64,64,4], got {initial_latents.shape}")
    if variance_noises.shape != (40, 12, 64, 64, 4):
        raise ValueError(
            f"Era3D variance noise must be [40,12,64,64,4], got {variance_noises.shape}"
        )

    clip, normalizer = clip_stage_factory()
    image_condition, image_cfg = encode_clip_condition(
        clip, clip_pixels, embedding_noise, normalizer, noise_level=noise_level
    )
    mx.eval(image_condition, image_cfg)
    del image_condition
    del clip, normalizer
    _clear_stage_cache()

    vae = vae_factory()
    vae_condition, vae_cfg = encode_vae_condition(vae, vae_pixels)
    mx.eval(vae_condition, vae_cfg)
    del vae_condition
    del vae
    _clear_stage_cache()

    prompts = base_prompt_layout(normal_prompts, color_prompts)
    prompt_cfg = cfg_task_layout(prompts, zero_unconditional=False)
    mx.eval(prompt_cfg)
    scheduler = EraDDIMScheduler(scheduler_config)
    latents = initial_latents
    unet = unet_factory()
    pose = None
    for index, timestep in enumerate(scheduler.timesteps):
        latent_cfg = generated_latent_cfg_layout(latents)
        model_input = mx.concatenate([latent_cfg, vae_cfg], axis=-1)
        prediction_cfg, pose = unet(model_input, int(timestep), prompt_cfg, image_cfg)
        prediction = apply_cfg(prediction_cfg, guidance_scale)
        latents = scheduler.step(
            prediction, index, latents, variance_noises[index], eta=1.0
        )
        mx.eval(latents, pose)
    del unet, vae_cfg, image_cfg, prompt_cfg
    _clear_stage_cache()

    vae = vae_factory()
    decoded = vae.decode(latents)
    images = mx.clip(decoded / 2.0 + 0.5, 0.0, 1.0)
    mx.eval(images)
    del vae, decoded
    _clear_stage_cache()
    normals, colors = mx.split(images, 2, axis=0)
    return Era3DResult(normals=normals, colors=colors, pose=pose, latents=latents)
