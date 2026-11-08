"""Checkpoint metadata, fixed conditioning, and exact input preparation for Era3D.

No model component is instantiated here. The front end is intentionally split so the
runtime can load CLIP, cache its result, release CLIP, then load the VAE and UNet without
holding duplicate multi-gigabyte checkpoints.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

import mlx.core as mx
import numpy as np
from PIL import Image
from safetensors import safe_open

ERA3D_REPO = "pengHTYX/MacLab-Era3D-512-6view"
ERA3D_REVISION = "00732de5cb3417b2a806ced9e92879aacb67c731"
NUM_VIEWS = 6
IMAGE_SIZE = 512
OBJECT_CROP_SIZE = 420
PROMPT_SHAPE = (NUM_VIEWS, 77, 1024)

PROMPT_HASHES = {
    "normal_embeds.npy": "08f5fff902f0aa0c8a36f62d59ae7d8f3237f888860dad7b0520e7ba68123588",
    "color_embeds.npy": "be446158d33d7817f5623b51d5becdfd2cab0ae06feb59d050695856fb2204f5",
}


@dataclass(frozen=True)
class ComponentSpec:
    directory: str
    filename: str
    tensors: int
    parameters: int
    stored_dtype: str


COMPONENTS = (
    ComponentSpec("image_encoder", "model.safetensors", 520, 632_076_800, "F16"),
    ComponentSpec("image_normalizer", "diffusion_pytorch_model.safetensors", 2, 2_048, "F16"),
    ComponentSpec("vae", "diffusion_pytorch_model.safetensors", 248, 83_653_863, "F16"),
    ComponentSpec("unet", "diffusion_pytorch_model.safetensors", 838, 947_664_646, "F16"),
)

REQUIRED_CONFIGS = (
    "model_index.json",
    "feature_extractor/preprocessor_config.json",
    "image_encoder/config.json",
    "image_noising_scheduler/scheduler_config.json",
    "image_normalizer/config.json",
    "scheduler/scheduler_config.json",
    "unet/config.json",
    "vae/config.json",
)


def _read_json(path: Path) -> dict[str, Any]:
    with path.open() as handle:
        return json.load(handle)


def _assert_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise ValueError(f"Era3D {label}: expected {expected!r}, got {actual!r}")


def validate_config(model_dir: str | Path) -> dict[str, Any]:
    """Fail fast if a checkpoint directory is not the audited six-view perspective model."""
    root = Path(model_dir)
    missing = [name for name in REQUIRED_CONFIGS if not (root / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Era3D configuration is incomplete: {missing}")

    unet = _read_json(root / "unet/config.json")
    clip = _read_json(root / "image_encoder/config.json")
    vae = _read_json(root / "vae/config.json")
    scheduler = _read_json(root / "scheduler/scheduler_config.json")
    image_scheduler = _read_json(root / "image_noising_scheduler/scheduler_config.json")

    checks = (
        (unet["num_views"], 6, "UNet view count"),
        (unet["in_channels"], 8, "UNet input channels"),
        (unet["out_channels"], 4, "UNet output channels"),
        (unet["block_out_channels"], [320, 640, 1280, 1280], "UNet block widths"),
        (unet["attention_head_dim"], [5, 10, 20, 20], "UNet attention heads"),
        (unet["cross_attention_dim"], 1024, "UNet cross-attention width"),
        (unet["selfattn_block"], "self_rowwise", "UNet transformer family"),
        (unet["projection_class_embeddings_input_dim"], 2048, "image conditioning width"),
        (unet["regress_elevation"], True, "elevation regressor"),
        (unet["regress_focal_length"], True, "focal regressor"),
        (clip["image_size"], 224, "CLIP image size"),
        (clip["patch_size"], 14, "CLIP patch size"),
        (clip["hidden_size"], 1280, "CLIP width"),
        (clip["num_hidden_layers"], 32, "CLIP layers"),
        (clip["hidden_act"], "gelu", "CLIP activation"),
        (clip["projection_dim"], 1024, "CLIP projection width"),
        (vae["scaling_factor"], 0.18215, "VAE scaling factor"),
        (scheduler["prediction_type"], "v_prediction", "DDIM prediction type"),
        (scheduler["steps_offset"], 1, "DDIM step offset"),
        (image_scheduler["beta_schedule"], "squaredcos_cap_v2", "image-noise schedule"),
    )
    for actual, expected, label in checks:
        _assert_equal(actual, expected, label)

    return {
        "repo": ERA3D_REPO,
        "revision": ERA3D_REVISION,
        "num_views": NUM_VIEWS,
        "unet": unet,
        "clip": clip,
        "vae": vae,
        "scheduler": scheduler,
        "image_noising_scheduler": image_scheduler,
    }


def inspect_safetensors(path: str | Path) -> dict[str, Any]:
    """Read tensor names/shapes/dtypes without copying tensor payloads into memory."""
    tensor_count = 0
    parameter_count = 0
    dtypes: set[str] = set()
    with safe_open(str(path), framework="np") as handle:
        for key in handle.keys():
            info = handle.get_slice(key)
            shape = info.get_shape()
            tensor_count += 1
            parameter_count += int(np.prod(shape, dtype=np.int64))
            dtypes.add(str(info.get_dtype()))
    return {
        "tensors": tensor_count,
        "parameters": parameter_count,
        "dtypes": sorted(dtypes),
    }


def validate_checkpoint_files(model_dir: str | Path) -> dict[str, dict[str, Any]]:
    """Validate all active inference weights against the metadata-only audit.

    The text encoder is intentionally absent: official inference supplies fixed prompt
    tensors and never asks it to encode text.
    """
    root = Path(model_dir)
    results = {}
    for spec in COMPONENTS:
        path = root / spec.directory / spec.filename
        if not path.is_file():
            raise FileNotFoundError(f"missing Era3D component {path}")
        actual = inspect_safetensors(path)
        _assert_equal(actual["tensors"], spec.tensors, f"{spec.directory} tensor count")
        _assert_equal(actual["parameters"], spec.parameters,
                      f"{spec.directory} parameter count")
        _assert_equal(actual["dtypes"], [spec.stored_dtype], f"{spec.directory} dtypes")
        results[spec.directory] = actual
    return results


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_fixed_prompts(model_dir: str | Path) -> tuple[mx.array, mx.array]:
    """Load the two exact fixed prompt tensors without a CLIP text encoder."""
    prompt_dir = Path(model_dir) / "fixed_prompt_embeds_6view"
    arrays = []
    for filename in ("normal_embeds.npy", "color_embeds.npy"):
        path = prompt_dir / filename
        if not path.is_file():
            raise FileNotFoundError(f"missing fixed Era3D prompt {path}")
        _assert_equal(_sha256(path), PROMPT_HASHES[filename], f"{filename} SHA-256")
        array = np.load(path, allow_pickle=False)
        _assert_equal(array.shape, PROMPT_SHAPE, f"{filename} shape")
        _assert_equal(array.dtype, np.dtype(np.float16), f"{filename} dtype")
        arrays.append(mx.array(array))
    return arrays[0], arrays[1]


def base_prompt_layout(normal: mx.array, color: mx.array) -> mx.array:
    """Return official base order ``N0..N5,C0..C5``."""
    if normal.shape != PROMPT_SHAPE or color.shape != PROMPT_SHAPE:
        raise ValueError(f"prompt shapes must both be {PROMPT_SHAPE}")
    return mx.concatenate([normal, color], axis=0)


def cfg_task_layout(task_major: mx.array, *, zero_unconditional: bool) -> mx.array:
    """Convert ``[N,C]`` into official ``[N_u,N_c,C_u,C_c]`` layout.

    Prompts set ``zero_unconditional=False`` because Era3D retains fixed task/view text in
    the unconditional path. CLIP image embeddings and VAE condition latents set it true.
    """
    if task_major.shape[0] % 2:
        raise ValueError(f"task-major batch must divide into normal/color, got {task_major.shape}")
    normal, color = mx.split(task_major, 2, axis=0)
    normal_uncond = mx.zeros_like(normal) if zero_unconditional else normal
    color_uncond = mx.zeros_like(color) if zero_unconditional else color
    return mx.concatenate([normal_uncond, normal, color_uncond, color], axis=0)


def generated_latent_cfg_layout(latents: mx.array) -> mx.array:
    """Duplicate generated ``[N,C]`` latents to ``[N,N,C,C]`` for one UNet pass."""
    return cfg_task_layout(latents, zero_unconditional=False)


def apply_cfg(noise_prediction: mx.array, guidance_scale: float = 3.0) -> mx.array:
    """Guide normal and color predictions independently, restoring ``[N,C]`` order."""
    if noise_prediction.shape[0] % 4:
        raise ValueError(f"CFG prediction batch must divide into four groups, got {noise_prediction.shape}")
    normal_u, normal_c, color_u, color_c = mx.split(noise_prediction, 4, axis=0)
    normal = normal_u + guidance_scale * (normal_c - normal_u)
    color = color_u + guidance_scale * (color_c - color_u)
    return mx.concatenate([normal, color], axis=0)


def preprocess_rgba(image: Image.Image, object_crop_size: int = OBJECT_CROP_SIZE,
                    image_size: int = IMAGE_SIZE) -> np.ndarray:
    """Reproduce `SingleImageDataset.load_image` exactly through white compositing.

    The upstream crop passes inclusive alpha maxima directly to PIL's exclusive crop box,
    omitting the last occupied row and column. This apparent off-by-one is preserved for
    parity rather than corrected.
    """
    if image.mode != "RGBA":
        raise ValueError(f"Era3D preprocessing requires RGBA, got {image.mode}")
    rgba = np.asarray(image)
    coords = np.stack(np.nonzero(rgba[:, :, 3]), axis=1)[:, (1, 0)]
    if coords.size == 0:
        raise ValueError("Era3D input has no non-transparent pixels")
    min_x, min_y = coords.min(axis=0)
    max_x, max_y = coords.max(axis=0)
    cropped = image.crop((int(min_x), int(min_y), int(max_x), int(max_y)))
    scale = object_crop_size / max(cropped.height, cropped.width)
    resized = cropped.resize((int(scale * cropped.width), int(scale * cropped.height)))
    canvas = Image.new("RGBA", (image_size, image_size), 0)
    canvas.paste(resized, ((image_size - resized.width) // 2,
                           (image_size - resized.height) // 2))

    array = np.asarray(canvas).astype(np.float32) / 255.0
    alpha = array[..., 3:4]
    return array[..., :3] * alpha + (1.0 - alpha)


def task_images(rgb: np.ndarray) -> np.ndarray:
    """Repeat one 512-square conditioning image into ``N0..N5,C0..C5`` order."""
    if rgb.shape != (IMAGE_SIZE, IMAGE_SIZE, 3) or rgb.dtype != np.float32:
        raise ValueError(f"expected float32 {(IMAGE_SIZE, IMAGE_SIZE, 3)}, got {rgb.shape} {rgb.dtype}")
    views = np.repeat(rgb[None], NUM_VIEWS, axis=0)
    return np.concatenate([views, views], axis=0)


def quantize_task_images(images: np.ndarray) -> list[Image.Image]:
    """Reproduce torchvision `to_pil_image` for float `[0,1]` tensors.

    Torchvision multiplies by 255 and casts to byte, which truncates rather than rounds.
    The pipeline then feeds these PIL images to both CLIP and the VAE.
    """
    if images.shape != (2 * NUM_VIEWS, IMAGE_SIZE, IMAGE_SIZE, 3):
        raise ValueError(f"unexpected Era3D image batch {images.shape}")
    quantized = np.clip(images * 255.0, 0, 255).astype(np.uint8)
    return [Image.fromarray(image, mode="RGB") for image in quantized]


def clip_preprocess(images: list[Image.Image], model_dir: str | Path) -> np.ndarray:
    """Apply the audited CLIPImageProcessor resize/crop/rescale/normalize path.

    Returns NHWC float32 for the future MLX CLIP vision model.
    """
    config = _read_json(Path(model_dir) / "feature_extractor/preprocessor_config.json")
    shortest = int(config["size"]["shortest_edge"])
    crop_h = int(config["crop_size"]["height"])
    crop_w = int(config["crop_size"]["width"])
    mean = np.asarray(config["image_mean"], dtype=np.float32)
    std = np.asarray(config["image_std"], dtype=np.float32)

    output = []
    for image in images:
        width, height = image.size
        scale = shortest / min(width, height)
        resized = image.resize((int(round(width * scale)), int(round(height * scale))),
                               Image.Resampling.BICUBIC)
        left = (resized.width - crop_w) // 2
        top = (resized.height - crop_h) // 2
        cropped = resized.crop((left, top, left + crop_w, top + crop_h))
        pixels = np.asarray(cropped).astype(np.float32) / 255.0
        output.append((pixels - mean) / std)
    return np.stack(output, axis=0)


def vae_preprocess(images: list[Image.Image]) -> np.ndarray:
    """Reproduce torchvision `to_tensor(...)*2-1` in NHWC float32."""
    if len(images) != 2 * NUM_VIEWS:
        raise ValueError(f"Era3D VAE requires {2 * NUM_VIEWS} task/view images, got {len(images)}")
    tensors = [np.asarray(image).astype(np.float32) / 255.0 for image in images]
    return np.stack(tensors, axis=0) * 2.0 - 1.0
