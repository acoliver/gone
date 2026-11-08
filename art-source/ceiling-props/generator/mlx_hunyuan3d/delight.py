"""Light and shadow removal (hunyuan3d-delight-v2-0), ported to MLX.

Upstream runs the reference image through this before multiview generation, so baked
lighting does not end up in the albedo. It is a StableDiffusion InstructPix2Pix model:
the UNet takes 8 channels, cat[noisy_latent(4), image_latent(4)], where the image latent
is the VAE encoding of the input WITHOUT any noise.

Two observations keep this port small:

  * The UNet is architecturally IDENTICAL to the paint UNet (same SD2.1 backbone,
    cross_attention_dim 1024, attention_head_dim [5,10,20,20], use_linear_projection).
    It differs only in in_channels (8 vs 12) and having no class embedding, both of
    which UNet2DConditionModel already takes as arguments. The checkpoint keys differ
    only by the `transformer.` prefix the 2.5D wrapper introduces.
  * The prompt is hardcoded to "" and guidance_scale is 1.0, which disables classifier
    free guidance in diffusers. So there is no text encoder to port: the empty-prompt
    embedding is a 77x1024 constant, precomputed once and stored beside the weights.
    That saves porting CLIP for a value that can never change.
"""

from __future__ import annotations

import os
import re

import mlx.core as mx
import numpy as np

from .paint_scheduler import EulerAncestralDiscreteScheduler
from .paint_unet import UNet2DConditionModel
from .paint_vae import SCALING_FACTOR, AutoencoderKL
from .paint_weights import _assign, _load_raw, load_vae, verify_loaded

# Insert the wrapper prefix the shared UNet expects. The delight checkpoint is a plain SD
# UNet, so its blocks sit directly under transformer_blocks.N.
_BLOCK = re.compile(r"^(.*transformer_blocks\.\d+\.)(?!transformer\.)(.*)$")

IMAGE_GUIDANCE_SCALE = 1.5
NUM_INFERENCE_STEPS = 50


def load_delight_unet(model, path: str, dtype: str = "float16") -> int:
    target_dtype = {"float16": np.float16, "float32": np.float32}[dtype]
    raw = _load_raw(path)
    count = 0
    for key, array in raw.items():
        match = _BLOCK.match(key)
        name = f"{match.group(1)}transformer.{match.group(2)}" if match else key
        if array.ndim == 4:
            array = np.transpose(array, (0, 2, 3, 1))
        _assign(model, name, mx.array(array.astype(target_dtype)))
        count += 1
    return count


class DelightPipeline:
    def __init__(self, vae, unet, scheduler, empty_prompt):
        self.vae = vae
        self.unet = unet
        self.scheduler = scheduler
        self.empty_prompt = empty_prompt

    @classmethod
    def from_pretrained(cls, path: str = "weights/Hunyuan3D-2/hunyuan3d-delight-v2-0",
                        dtype: str = "float16"):
        vae = AutoencoderKL()
        vae_file = os.path.join(path, "vae", "diffusion_pytorch_model.safetensors")
        load_vae(vae, vae_file)
        verify_loaded(vae, vae_file)

        unet = UNet2DConditionModel(in_channels=8, use_ma=False, use_ra=False,
                                    learned_prompts=False, num_class_embeds=None)
        count = load_delight_unet(
            unet, os.path.join(path, "unet", "diffusion_pytorch_model.safetensors"), dtype)

        import mlx.utils
        expected = len({n for n, _ in mlx.utils.tree_flatten(unet.parameters())})
        if count != expected:
            raise ValueError(f"delight UNet: loaded {count} tensors, model has {expected}")

        embed_path = os.path.join(path, "empty_prompt_embed.npy")
        if not os.path.exists(embed_path):
            raise FileNotFoundError(
                f"{embed_path} missing. It is the CLIP encoding of the empty prompt and is "
                "generated once under .venv-ref; see mlx_hunyuan3d/delight.py.")
        empty_prompt = mx.array(np.load(embed_path))
        return cls(vae, unet, EulerAncestralDiscreteScheduler(), empty_prompt)

    def __call__(self, image: np.ndarray, num_inference_steps: int = NUM_INFERENCE_STEPS,
                 image_guidance_scale: float = IMAGE_GUIDANCE_SCALE, seed: int = 42,
                 verbose: bool = True) -> np.ndarray:
        """image: HWC float in [0, 1], 512x512. Returns the delit image, same shape."""
        mx.random.seed(seed)
        dtype = self.unet.conv_in.weight.dtype

        source = np.asarray(image, dtype=np.float32)[None]
        # InstructPix2Pix conditions on the UNSCALED image latent (no scaling_factor).
        posterior = self.vae.encode(mx.array(source * 2.0 - 1.0)) / SCALING_FACTOR
        image_latent = posterior.astype(dtype)
        mx.eval(image_latent)

        timesteps = self.scheduler.set_timesteps(num_inference_steps)
        latents = mx.random.normal(image_latent.shape).astype(dtype)
        latents = latents * self.scheduler.init_noise_sigma

        context = self.empty_prompt.astype(dtype)
        for step, timestep in enumerate(timesteps):
            scaled = self.scheduler.scale_model_input(latents, step)
            model_input = mx.concatenate([scaled, image_latent], axis=-1)
            noise_pred = self.unet(model_input, float(timestep), context)
            latents = self.scheduler.step(noise_pred, step, latents)
            mx.eval(latents)
            if verbose and (step + 1) % 10 == 0:
                print(f"    delight step {step + 1}/{len(timesteps)}")

        decoded = self.vae.decode(latents.astype(mx.float32))
        mx.eval(decoded)
        return np.clip((np.array(decoded)[0] + 1.0) * 0.5, 0.0, 1.0)


def recorrect_rgb(source: np.ndarray, target: np.ndarray, alpha: np.ndarray,
                  scale: float = 0.95) -> np.ndarray:
    """Match the delit image's per-channel statistics back to the original.

    The diffusion pass can shift overall colour; this pulls it back toward the input while
    keeping the relit shading. Upstream keeps whichever of the two is closer to the target,
    so a correction that makes things worse is discarded rather than trusted blindly.
    """
    mask = alpha > 0.5
    if not mask.any():
        return source
    corrected = np.zeros_like(source)
    for channel in range(3):
        src = source[..., channel][mask]
        tgt = target[..., channel][mask]
        src_std = src.std()
        if src_std < 1e-6:
            corrected[..., channel] = source[..., channel]
            continue
        corrected[..., channel] = np.clip(
            (source[..., channel] - scale * src.mean()) * (tgt.std() / src_std)
            + scale * tgt.mean(), 0.0, 1.0)

    if np.mean((source - target) ** 2) < np.mean((corrected - target) ** 2):
        return source
    return corrected
