"""Fresh component factories for bounded-residency Era3D inference."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mlx_hunyuan3d.era3d_clip import EraCLIPVisionModelWithProjection
from mlx_hunyuan3d.era3d_conditioning import EraImageNormalizer
from mlx_hunyuan3d.era3d_io import validate_config
from mlx_hunyuan3d.era3d_unet import Era3DUNet
from mlx_hunyuan3d.era3d_weights import (
    ComponentLoadReport,
    load_component_streaming,
    translate_unet_key,
)
from mlx_hunyuan3d.paint_vae import AutoencoderKL


class Era3DComponentFactory:
    """Instantiate and stream-load one active model stage at a time."""

    def __init__(self, model_dir: str | Path):
        self.model_dir = Path(model_dir)
        self.config = validate_config(self.model_dir)
        self.reports: list[tuple[str, ComponentLoadReport]] = []
        self._source_hashes: dict[Path, str] = {}

    def _load(self, name: str, model: Any, relative_path: str, *, unet: bool = False) -> Any:
        path = self.model_dir / relative_path
        report = load_component_streaming(
            model,
            path,
            translate_key=translate_unet_key if unet else lambda key: key,
            source_sha256=self._source_hashes.get(path),
        )
        self._source_hashes[path] = report.source_sha256
        self.reports.append((name, report))
        return model

    def clip_stage(self) -> tuple[EraCLIPVisionModelWithProjection, EraImageNormalizer]:
        clip = EraCLIPVisionModelWithProjection(self.config["clip"])
        self._load("image_encoder", clip, "image_encoder/model.safetensors")
        normalizer = EraImageNormalizer(self.config["clip"]["projection_dim"])
        self._load(
            "image_normalizer",
            normalizer,
            "image_normalizer/diffusion_pytorch_model.safetensors",
        )
        return clip, normalizer

    def vae(self) -> AutoencoderKL:
        config = self.config["vae"]
        vae = AutoencoderKL(
            in_channels=config["in_channels"],
            out_channels=config["out_channels"],
            latent_channels=config["latent_channels"],
            block_out_channels=tuple(config["block_out_channels"]),
            layers_per_block=config["layers_per_block"],
        )
        return self._load("vae", vae, "vae/diffusion_pytorch_model.safetensors")

    def unet(self) -> Era3DUNet:
        model = Era3DUNet(self.config["unet"])
        return self._load(
            "unet", model, "unet/diffusion_pytorch_model.safetensors", unet=True
        )

    @property
    def scheduler_config(self) -> dict[str, Any]:
        with (self.model_dir / "scheduler/scheduler_config.json").open() as handle:
            return json.load(handle)
