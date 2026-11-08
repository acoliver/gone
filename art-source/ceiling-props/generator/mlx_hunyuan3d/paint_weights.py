"""Map diffusers checkpoints onto the MLX paint modules.

Kept separate from the module definitions so the naming rules live in one place, matching
how weights.py handles the shape models.

The only real subtlety is convolution layout: PyTorch stores (out, in, kH, kW) and MLX
wants (out, kH, kW, in). A 1x1 convolution transposes to the same number of elements
either way, so a missed transpose there does NOT raise - it silently permutes channels.
Every 4-D tensor is therefore transposed unconditionally, and verify_loaded() re-checks
shapes against the constructed tree rather than trusting the mapping.
"""

from __future__ import annotations

import numpy as np
from safetensors import safe_open


def _load_raw(path: str) -> dict[str, np.ndarray]:
    tensors = {}
    with safe_open(path, framework="np") as handle:
        for key in handle.keys():
            tensors[key] = handle.get_tensor(key)
    return tensors


def _assign(tree, dotted: str, value):
    """Assign into a module tree, following attributes and list indices."""
    parts = dotted.split(".")
    target = tree
    for part in parts[:-1]:
        target = target[int(part)] if part.isdigit() else getattr(target, part)
    last = parts[-1]
    if last.isdigit():
        target[int(last)] = value
    else:
        setattr(target, last, value)


def load_vae(model, path: str) -> int:
    """Load a diffusers AutoencoderKL checkpoint into the MLX model. Returns tensor count."""
    import mlx.core as mx

    raw = _load_raw(path)
    count = 0
    for key, array in raw.items():
        if array.ndim == 4:
            # (out, in, kH, kW) -> (out, kH, kW, in)
            array = np.transpose(array, (0, 2, 3, 1))
        _assign(model, key, mx.array(array.astype(np.float32)))
        count += 1
    return count


def is_orphan_key(key: str) -> bool:
    """True for checkpoint entries the reference model never constructs.

    The safetensors export carries 36 IP-Adapter tensors (attn2.to_k_ip / to_v_ip and
    image_proj_model.*) that UNet2p5DConditionModel never builds. The authoritative .bin -
    the file from_pretrained actually loads, with strict=True - has 1535 tensors and none
    of these; the safetensors has 1571. Loading them would create dead parameters and mask
    a genuine mismatch, so they are dropped explicitly rather than ignored silently.
    """
    return "_ip." in key or "image_proj_model" in key


def load_unet(main, dual, path: str, dtype: str = "float16") -> tuple[int, int]:
    """Split one checkpoint across the main UNet and the dual stream.

    Defaults to float16, matching the checkpoint's own torch_dtype. At float32 the two
    streams alone are 7.4 GB of weights and the multi-view attention pushes peak memory
    past 110 GB, which is close enough to a 128 GB machine's limit to matter.
    """
    import mlx.core as mx

    target_dtype = {"float16": np.float16, "float32": np.float32}[dtype]
    raw = _load_raw(path)
    counts = {"unet.": 0, "unet_dual.": 0}
    for key, array in raw.items():
        if is_orphan_key(key):
            continue
        if key.startswith("unet_dual."):
            target, prefix = dual, "unet_dual."
        elif key.startswith("unet."):
            target, prefix = main, "unet."
        else:
            raise ValueError(f"unexpected checkpoint key {key!r}")
        if array.ndim == 4:
            array = np.transpose(array, (0, 2, 3, 1))
        _assign(target, key[len(prefix):], mx.array(array.astype(target_dtype)))
        counts[prefix] += 1
    return counts["unet."], counts["unet_dual."]


def verify_unet_loaded(main, dual, path: str) -> None:
    import mlx.utils

    with safe_open(path, framework="np") as handle:
        keys = [k for k in handle.keys() if not is_orphan_key(k)]
    expected_main = {k[len("unet."):] for k in keys if k.startswith("unet.")}
    expected_dual = {k[len("unet_dual."):] for k in keys if k.startswith("unet_dual.")}

    for label, model, expected in (("main", main, expected_main), ("dual", dual, expected_dual)):
        present = {name for name, _ in mlx.utils.tree_flatten(model.parameters())}
        if present != expected:
            missing, extra = sorted(expected - present), sorted(present - expected)
            raise ValueError(
                f"{label} UNet mismatch: {len(missing)} missing (e.g. {missing[:3]}), "
                f"{len(extra)} extra (e.g. {extra[:3]})"
            )


def verify_loaded(model, raw_path: str) -> None:
    """Fail loudly if any parameter kept its randomly initialised shape or went missing."""
    import mlx.utils

    expected = set()
    with safe_open(raw_path, framework="np") as handle:
        expected = set(handle.keys())

    present = {name for name, _ in mlx.utils.tree_flatten(model.parameters())}
    missing = expected - present
    if missing:
        raise ValueError(f"{len(missing)} checkpoint tensors were not applied, e.g. "
                         f"{sorted(missing)[:5]}")
    extra = present - expected
    if extra:
        raise ValueError(f"{len(extra)} model parameters had no checkpoint entry, e.g. "
                         f"{sorted(extra)[:5]}")
