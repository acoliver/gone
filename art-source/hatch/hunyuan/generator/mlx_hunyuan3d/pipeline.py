"""End-to-end MLX pipeline: multi-view images -> latents -> occupancy grid -> mesh."""

from __future__ import annotations

import os
import time
from typing import Dict, Optional

import mlx.core as mx
import numpy as np
import yaml

from .dinov2 import SingleImageEncoder
from .dit import Hunyuan3DDiT
from .preprocess import build_image_processor, resize_for_encoder
from .schedulers import build_scheduler
from .vae import ShapeVAE, marching_cubes
from .weights import (
    astype_all,
    filter_vae_decoder_keys,
    randn,
    split_checkpoint,
    verify_loaded,
)

DTYPES = {"float16": mx.float16, "bfloat16": mx.bfloat16, "float32": mx.float32}


def _conditioner_kwargs(config: dict) -> dict:
    enc = config["conditioner"]["params"]["main_image_encoder"]
    if enc["type"] != "DinoImageEncoderMV":
        raise ValueError(f"Unsupported image encoder type {enc['type']}")
    cfg = enc["kwargs"]["config"]
    return {
        "image_size": enc["kwargs"]["image_size"],
        "hidden_size": cfg["hidden_size"],
        "num_hidden_layers": cfg["num_hidden_layers"],
        "num_attention_heads": cfg["num_attention_heads"],
        "mlp_ratio": cfg["mlp_ratio"],
        "patch_size": cfg["patch_size"],
        "num_channels": cfg["num_channels"],
        "layer_norm_eps": float(cfg["layer_norm_eps"]),
        "qkv_bias": cfg["qkv_bias"],
    }


class Hunyuan3DDiTFlowMatchingPipeline:
    def __init__(self, conditioner, model, vae, scheduler, image_processor, config, dtype):
        self.conditioner = conditioner
        self.model = model
        self.vae = vae
        self.scheduler = scheduler
        self.image_processor = image_processor
        self.config = config
        self.dtype = dtype

    @classmethod
    def from_pretrained(
        cls,
        model_path: str,
        subfolder: str = "hunyuan3d-dit-v2-mv-turbo",
        dtype: str = "float16",
        verbose: bool = True,
    ) -> "Hunyuan3DDiTFlowMatchingPipeline":
        folder = os.path.join(model_path, subfolder)
        config_path = os.path.join(folder, "config.yaml")
        ckpt_path = os.path.join(folder, "model.fp16.safetensors")
        for path in (config_path, ckpt_path):
            if not os.path.exists(path):
                raise FileNotFoundError(path)

        with open(config_path, "r") as handle:
            config = yaml.safe_load(handle)
        if dtype not in DTYPES:
            raise ValueError(f"dtype must be one of {sorted(DTYPES)}")
        mx_dtype = DTYPES[dtype]

        started = time.time()
        state = mx.load(ckpt_path)
        groups = split_checkpoint(state)

        conditioner = SingleImageEncoder(**_conditioner_kwargs(config))
        cond_items = astype_all(groups["conditioner"], mx_dtype)
        verify_loaded(conditioner, cond_items, "conditioner")
        conditioner.load_weights(cond_items)
        conditioner.eval()

        model = Hunyuan3DDiT(**config["model"]["params"])
        model_items = astype_all(groups["model"], mx_dtype)
        verify_loaded(model, model_items, "denoiser")
        model.load_weights(model_items)
        model.eval()

        vae = ShapeVAE(**config["vae"]["params"])
        vae_items = astype_all(filter_vae_decoder_keys(groups["vae"]), mx_dtype)
        verify_loaded(vae, vae_items, "vae")
        vae.load_weights(vae_items)
        vae.eval()

        mx.eval(conditioner.parameters(), model.parameters(), vae.parameters())

        scheduler = build_scheduler(
            config["scheduler"]["target"], config["scheduler"].get("params", {})
        )
        image_processor = build_image_processor(
            config["image_processor"]["target"], config["image_processor"].get("params", {})
        )

        if verbose:
            print(
                f"Loaded {subfolder} in {time.time() - started:.1f}s "
                f"({dtype}, guidance_embed={model.guidance_embed})"
            )
        return cls(conditioner, model, vae, scheduler, image_processor, config, mx_dtype)

    def encode_cond(self, images: np.ndarray, view_idxs, do_cfg: bool) -> Dict[str, mx.array]:
        resized = resize_for_encoder(images, self.conditioner.main_image_encoder.image_size)
        image = mx.array(resized).astype(self.dtype)
        cond = self.conditioner(image, view_idxs=view_idxs)
        if do_cfg:
            uncond = self.conditioner.unconditional_embedding(
                image.shape[0], view_idxs=view_idxs, dtype=self.dtype
            )
            cond = {k: mx.concatenate([cond[k], uncond[k]], axis=0) for k in cond}
        mx.eval(cond)
        return cond

    def __call__(
        self,
        image,
        num_inference_steps: int = 5,
        guidance_scale: float = 5.0,
        seed: int = 0,
        box_v: float = 1.01,
        octree_resolution: int = 256,
        mc_level: float = 0.0,
        num_chunks: int = 20000,
        latents: Optional[np.ndarray] = None,
        remove_bg: bool = False,
        verbose: bool = True,
    ):
        cond_inputs = self.image_processor(image, remove_bg=remove_bg)
        images = cond_inputs["image"]
        view_idxs = cond_inputs.get("view_idxs")
        batch_size = images.shape[0]

        # Guidance-distilled checkpoints bake the scale into a conditioning embedding
        # instead of running a second, unconditional forward pass.
        do_cfg = guidance_scale >= 0 and not self.model.guidance_embed

        t0 = time.time()
        cond = self.encode_cond(images, view_idxs, do_cfg)
        if verbose:
            print(f"  conditioning: {time.time() - t0:.2f}s  {cond['main'].shape}")

        sigmas = np.linspace(0, 1, num_inference_steps)
        timesteps = self.scheduler.set_timesteps(sigmas=sigmas)

        if latents is None:
            latents = randn((batch_size, *self.vae.latent_shape), seed=seed)
        latents = mx.array(np.asarray(latents, dtype=np.float32)).astype(self.dtype)

        guidance = None
        if self.model.guidance_embed:
            guidance = mx.full((batch_size,), guidance_scale, dtype=mx.float32)

        t0 = time.time()
        for i, t in enumerate(timesteps):
            latent_input = mx.concatenate([latents] * 2) if do_cfg else latents
            timestep = mx.full(
                (latent_input.shape[0],), float(t) / self.scheduler.num_train_timesteps,
                dtype=mx.float32,
            )
            noise_pred = self.model(latent_input, timestep, cond, guidance=guidance)
            if do_cfg:
                pred_cond, pred_uncond = mx.split(noise_pred, 2, axis=0)
                noise_pred = pred_uncond + guidance_scale * (pred_cond - pred_uncond)

            latents = self.scheduler.step(
                noise_pred.astype(mx.float32), t, latents.astype(mx.float32)
            ).astype(self.dtype)
            mx.eval(latents)
            if verbose:
                print(f"  step {i + 1}/{len(timesteps)}  ({time.time() - t0:.1f}s)", end="\r")
        if verbose:
            print(f"\n  sampling: {time.time() - t0:.2f}s")

        return self.export(
            latents,
            box_v=box_v,
            octree_resolution=octree_resolution,
            mc_level=mc_level,
            num_chunks=num_chunks,
            verbose=verbose,
        )

    def export(self, latents, box_v=1.01, octree_resolution=256, mc_level=0.0,
               num_chunks=20000, verbose=True):
        import trimesh

        t0 = time.time()
        latents = latents.astype(self.dtype) * (1.0 / self.vae.scale_factor)
        decoded = self.vae.decode(latents)
        mx.eval(decoded)
        if verbose:
            print(f"  vae decode: {time.time() - t0:.2f}s")

        def report(done, total):
            if verbose:
                print(f"  volume decoding: {done}/{total}", end="\r")

        t0 = time.time()
        grid_logits = self.vae.decode_volume(
            decoded, bounds=box_v, octree_resolution=octree_resolution,
            num_chunks=num_chunks, progress=report,
        )
        if verbose:
            print(f"\n  volume decoding: {time.time() - t0:.2f}s  grid={grid_logits.shape}")

        t0 = time.time()
        meshes = []
        for vertices, faces in marching_cubes(grid_logits, mc_level, box_v, octree_resolution):
            # The reference flips winding order on export.
            meshes.append(trimesh.Trimesh(vertices, faces[:, ::-1]))
        if verbose:
            print(f"  marching cubes: {time.time() - t0:.2f}s")
        return meshes
