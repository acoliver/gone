"""Background removal, so ordinary images without an alpha channel can be used.

The preprocessor relies on alpha to crop and centre the subject. Images that already carry
a real alpha channel are passed through untouched; everything else is matted with `rembg`
(U^2-Net), which is what the upstream Hunyuan3D demo uses.
"""

from __future__ import annotations

import numpy as np
from PIL import Image

_SESSION = None


def _get_session():
    """Lazily create and cache a single rembg session (model load is expensive)."""
    global _SESSION
    if _SESSION is None:
        try:
            from rembg import new_session
        except ImportError as exc:  # pragma: no cover - depends on optional extra
            raise ImportError(
                "Background removal needs `rembg`. Install it with "
                "`pip install rembg onnxruntime`, or supply images that already have "
                "an alpha channel."
            ) from exc
        _SESSION = new_session("u2net")
    return _SESSION


def has_usable_alpha(image: Image.Image) -> bool:
    """True if the image carries an alpha channel that actually masks something."""
    if image.mode not in ("RGBA", "LA") and "transparency" not in image.info:
        return False
    alpha = np.asarray(image.convert("RGBA"))[..., 3]
    # A channel that is entirely opaque carries no subject information.
    return bool((alpha < 255).any())


def remove_background(image: Image.Image) -> Image.Image:
    """Return an RGBA copy of ``image`` with the background made transparent."""
    from rembg import remove

    return remove(image.convert("RGB"), session=_get_session()).convert("RGBA")


def ensure_alpha(image: Image.Image, remove_bg: bool = True) -> Image.Image:
    """Guarantee the image has a meaningful alpha channel.

    Raises rather than silently producing a full-frame mask, which would make the model
    reconstruct the whole picture instead of the subject.
    """
    image = image.convert("RGBA") if image.mode != "RGBA" else image
    if has_usable_alpha(image):
        return image
    if not remove_bg:
        raise ValueError(
            "Image has no usable alpha channel. Pass remove_bg=True (or --remove-bg) to "
            "matte it automatically, or supply a cut-out RGBA image."
        )
    return remove_background(image)
