"""Checkpoint -> MLX parameter-tree mapping for Hunyuan3D-2mv.

The released ``model.fp16.safetensors`` bundles all three sub-models under the
``conditioner.``, ``model.`` and ``vae.`` prefixes. Most names map 1:1 onto the ported
modules; the exceptions are handled by the rules below.
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

import mlx.core as mx
import numpy as np

# The reference stores block MLPs as Sequential(Linear, GELU, Linear), so the second
# Linear sits at index 2; the MLX port uses a 2-element list, so index 2 becomes index 1.
_BLOCK_MLP = re.compile(r"^(double_blocks\.\d+\.(?:img|txt)_mlp)\.(\d+)\.(.*)$")
# LastLayer's adaLN_modulation is Sequential(SiLU, Linear); only index 1 holds weights.
_ADALN = re.compile(r"^final_layer\.adaLN_modulation\.1\.(.*)$")
_MLP_INDEX_REMAP = {"0": "0", "2": "1"}


def _map_dit_key(key: str) -> str:
    body = key[len("model.") :]
    match = _BLOCK_MLP.match(body)
    if match:
        prefix, index, suffix = match.groups()
        if index not in _MLP_INDEX_REMAP:
            raise KeyError(f"Unexpected Sequential index in {key}")
        return f"{prefix}.{_MLP_INDEX_REMAP[index]}.{suffix}"
    match = _ADALN.match(body)
    if match:
        return f"final_layer.adaLN_modulation.{match.group(1)}"
    return body


def _is_conv_weight(key: str) -> bool:
    return key.endswith("patch_embeddings.projection.weight")


def split_checkpoint(state: Dict[str, mx.array]) -> Dict[str, List[Tuple[str, mx.array]]]:
    """Split a flat checkpoint into per-submodel (name, array) lists with MLX-side names."""
    out: Dict[str, List[Tuple[str, mx.array]]] = {
        "conditioner": [],
        "model": [],
        "vae": [],
    }
    for key, value in state.items():
        if key.startswith("conditioner."):
            name = key[len("conditioner.") :]
            if _is_conv_weight(key):
                # torch Conv2d (O, I, kH, kW) -> MLX Conv2d (O, kH, kW, I)
                value = value.transpose(0, 2, 3, 1)
            out["conditioner"].append((name, value))
        elif key.startswith("model."):
            out["model"].append((_map_dit_key(key), value))
        elif key.startswith("vae."):
            out["vae"].append((key[len("vae.") :], value))
        else:
            raise KeyError(f"Unexpected checkpoint key prefix: {key}")
    return out


def filter_vae_decoder_keys(items: List[Tuple[str, mx.array]]) -> List[Tuple[str, mx.array]]:
    """Drop encoder-side tensors; only the decoding path is ported."""
    keep_prefixes = ("post_kl.", "transformer.", "geo_decoder.")
    return [(k, v) for k, v in items if k.startswith(keep_prefixes)]


def astype_all(items: List[Tuple[str, mx.array]], dtype) -> List[Tuple[str, mx.array]]:
    return [(k, v.astype(dtype)) for k, v in items]


def verify_loaded(module, items: List[Tuple[str, mx.array]], label: str) -> None:
    """Assert that every parameter in ``module`` was populated by ``items`` and vice versa."""
    from mlx.utils import tree_flatten

    expected = {k for k, _ in tree_flatten(module.parameters())}
    provided = {k for k, _ in items}
    missing = expected - provided
    unexpected = provided - expected
    if missing or unexpected:
        raise ValueError(
            f"{label}: weight mapping mismatch\n"
            f"  missing ({len(missing)}): {sorted(missing)[:10]}\n"
            f"  unexpected ({len(unexpected)}): {sorted(unexpected)[:10]}"
        )


def randn(shape, seed: int = 0, dtype=np.float32) -> np.ndarray:
    """Deterministic Gaussian noise (NumPy Philox) for reproducible latents."""
    rng = np.random.default_rng(seed)
    return rng.standard_normal(shape).astype(dtype)
