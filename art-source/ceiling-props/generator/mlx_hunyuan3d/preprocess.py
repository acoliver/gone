"""Image preprocessing for Hunyuan3D-2mv, ported from ``hy3dgen.shapegen.preprocessors``.

Produces the (B, V, H, W, C) channels-last float array the MLX conditioner expects.
"""

from __future__ import annotations

from typing import Dict, Tuple

import cv2
import numpy as np
from PIL import Image

# View order the model was trained with.
VIEW_TO_IDX = {"front": 0, "left": 1, "back": 2, "right": 3}


def recenter(image: np.ndarray, border_ratio: float = 0.2) -> Tuple[np.ndarray, np.ndarray]:
    """Crop to the alpha bounding box and re-pad so the subject fills 1-border_ratio."""
    if image.shape[-1] == 4:
        mask = image[..., 3]
    else:
        alpha = np.ones_like(image[..., 0:1]) * 255
        image = np.concatenate([image, alpha], axis=-1)
        mask = alpha[..., 0]

    h_in, w_in, channels = image.shape
    size = max(h_in, w_in)
    result = np.zeros((size, size, channels), dtype=np.uint8)

    coords = np.nonzero(mask)
    if coords[0].size == 0:
        raise ValueError("input image is empty (fully transparent alpha channel)")
    x_min, x_max = coords[0].min(), coords[0].max()
    y_min, y_max = coords[1].min(), coords[1].max()
    h, w = x_max - x_min, y_max - y_min
    if h == 0 or w == 0:
        raise ValueError("input image is empty")

    desired_size = int(size * (1 - border_ratio))
    scale = desired_size / max(h, w)
    h2, w2 = int(h * scale), int(w * scale)
    x2_min = (size - h2) // 2
    y2_min = (size - w2) // 2
    result[x2_min : x2_min + h2, y2_min : y2_min + w2] = cv2.resize(
        image[x_min:x_max, y_min:y_max], (w2, h2), interpolation=cv2.INTER_AREA
    )

    bg = np.ones((size, size, 3), dtype=np.uint8) * 255
    alpha = result[..., 3:].astype(np.float32) / 255
    rgb = result[..., :3] * alpha + bg * (1 - alpha)
    return rgb.clip(0, 255).astype(np.uint8), (alpha * 255).clip(0, 255).astype(np.uint8)


def bilinear_resize(x: np.ndarray, out_h: int, out_w: int) -> np.ndarray:
    """Bilinear resize matching ``torch.nn.functional.interpolate(align_corners=False)``.

    Operates on float arrays shaped (..., H, W, C). Antialiasing is a no-op for the
    upscaling case used here (512 -> 518), so it is intentionally not implemented.

    Sampling coordinates and the lerp are evaluated in float64. That reproduces the
    reference to ~5e-8 when torch is also run in float64; torch's own float32 kernel
    deviates from that by ~3e-5, so this path is the more accurate of the two.
    """
    in_h, in_w = x.shape[-3], x.shape[-2]
    if (in_h, in_w) == (out_h, out_w):
        return x

    def axis_weights(in_size: int, out_size: int):
        src = (np.arange(out_size, dtype=np.float64) + 0.5) * in_size / out_size - 0.5
        src = np.clip(src, 0, None)
        lo = np.floor(src).astype(np.int64)
        hi = np.minimum(lo + 1, in_size - 1)
        return lo, hi, src - lo

    y_lo, y_hi, y_frac = axis_weights(in_h, out_h)
    x_lo, x_hi, x_frac = axis_weights(in_w, out_w)

    work = x.astype(np.float64, copy=False)
    rows_lo = work[..., y_lo, :, :]
    rows_hi = work[..., y_hi, :, :]
    rows = rows_lo + (rows_hi - rows_lo) * y_frac[:, None, None]
    cols_lo = rows[..., :, x_lo, :]
    cols_hi = rows[..., :, x_hi, :]
    out = cols_lo + (cols_hi - cols_lo) * x_frac[:, None]
    return out.astype(x.dtype, copy=False)


class ImageProcessorV2:
    def __init__(self, size: int = 512, border_ratio: float = 0.15):
        self.size = size
        self.border_ratio = border_ratio

    def load_image(self, image, border_ratio: float = None, remove_bg: bool = False):
        border_ratio = self.border_ratio if border_ratio is None else border_ratio

        if isinstance(image, str):
            if remove_bg:
                image = Image.open(image)
            else:
                # Preserve the reference's exact BGR(A) read path when no matting is needed.
                raw = cv2.imread(image, cv2.IMREAD_UNCHANGED)
                if raw is None:
                    raise FileNotFoundError(f"Could not read image at {image}")
                rgb, mask = recenter(raw, border_ratio=border_ratio)
                rgb = cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB)
                return self._finish(rgb, mask)
        elif isinstance(image, np.ndarray) and not remove_bg:
            rgb, mask = recenter(image, border_ratio=border_ratio)
            return self._finish(rgb, mask)
        elif isinstance(image, np.ndarray):
            image = Image.fromarray(image)

        if not isinstance(image, Image.Image):
            raise TypeError(f"Unsupported image type {type(image)}")

        if remove_bg:
            from .matting import ensure_alpha

            image = ensure_alpha(image, remove_bg=True)
        rgb, mask = recenter(np.asarray(image.convert("RGBA")), border_ratio=border_ratio)
        return self._finish(rgb, mask)

    def _finish(self, rgb: np.ndarray, mask: np.ndarray):
        rgb = cv2.resize(rgb, (self.size, self.size), interpolation=cv2.INTER_CUBIC)
        mask = cv2.resize(mask, (self.size, self.size), interpolation=cv2.INTER_NEAREST)
        # Match the reference scaling: uint8 -> [-1, 1], for the mask as well as the image.
        return (
            rgb.astype(np.float32) / 255 * 2 - 1,
            mask[..., None].astype(np.float32) / 255 * 2 - 1,
        )

    def __call__(self, image, remove_bg: bool = False) -> Dict[str, np.ndarray]:
        rgb, mask = self.load_image(image, remove_bg=remove_bg)
        return {"image": rgb[None], "mask": mask[None]}


class MVImageProcessorV2(ImageProcessorV2):
    """Processes a ``{'front': img, 'left': img, ...}`` dict into a stacked multi-view array."""

    def __call__(
        self, image_dict: Dict[str, object], remove_bg: bool = False
    ) -> Dict[str, object]:
        entries = []
        for view_tag, image in image_dict.items():
            if view_tag not in VIEW_TO_IDX:
                raise ValueError(
                    f"Unknown view '{view_tag}'; expected one of {sorted(VIEW_TO_IDX)}"
                )
            rgb, mask = self.load_image(image, remove_bg=remove_bg)
            entries.append((VIEW_TO_IDX[view_tag], rgb, mask))

        entries.sort(key=lambda e: e[0])
        view_idxs = [e[0] for e in entries]
        images = np.stack([e[1] for e in entries], axis=0)[None]  # (1, V, H, W, C)
        masks = np.stack([e[2] for e in entries], axis=0)[None]
        return {"image": images, "mask": masks, "view_idxs": [view_idxs]}


def resize_for_encoder(images: np.ndarray, image_size: int = 518) -> np.ndarray:
    """Replicates torchvision Resize(image_size, bilinear) + CenterCrop(image_size)."""
    *lead, h, w, c = images.shape
    flat = images.reshape(-1, h, w, c)
    if h != w:
        # Resize shorter side to image_size, then center-crop.
        if h < w:
            new_h, new_w = image_size, int(round(image_size * w / h))
        else:
            new_h, new_w = int(round(image_size * h / w)), image_size
        flat = bilinear_resize(flat, new_h, new_w)
        top = (new_h - image_size) // 2
        left = (new_w - image_size) // 2
        flat = flat[:, top : top + image_size, left : left + image_size, :]
    else:
        flat = bilinear_resize(flat, image_size, image_size)
    return flat.reshape(*lead, image_size, image_size, c)


IMAGE_PROCESSORS = {
    "ImageProcessorV2": ImageProcessorV2,
    "MVImageProcessorV2": MVImageProcessorV2,
}


def build_image_processor(target: str, params: dict):
    name = target.rsplit(".", 1)[-1]
    if name not in IMAGE_PROCESSORS:
        raise ValueError(f"Unsupported image processor {target}")
    return IMAGE_PROCESSORS[name](**params)
