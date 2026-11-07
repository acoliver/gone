"""Strict loading for the released P3-SAM safetensors checkpoint."""

from __future__ import annotations

import hashlib
from pathlib import Path

import mlx.core as mx
from mlx.utils import tree_flatten
from safetensors import safe_open

from mlx_hunyuan3d.p3sam_model import P3SAM

EXPECTED_SHA256 = "eb76550cfbe06f154c6e9b17167ccfc28222bb4a216ec7b12ac2bf7d762de38c"
EXPECTED_TENSORS = 513
EXPECTED_PARAMETERS = 112_728_649
_SEQUENTIAL_MODULES = (
    "mlp",
    "seg_mlp_1",
    "seg_mlp_2",
    "seg_mlp_3",
    "seg_s2_mlp_g",
    "seg_s2_mlp_1",
    "seg_s2_mlp_2",
    "seg_s2_mlp_3",
    "iou_mlp",
    "iou_mlp_out",
)


def checkpoint_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as checkpoint:
        for chunk in iter(lambda: checkpoint.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _native_key(key: str) -> str:
    key = key.removeprefix("dit.")
    for module in _SEQUENTIAL_MODULES:
        prefix = f"{module}."
        if key.startswith(prefix):
            suffix = key[len(prefix) :]
            index, separator, rest = suffix.partition(".")
            if separator and index.isdigit():
                return f"{module}.layers.{index}.{rest}"
    return key


def load_p3sam_weights(
    model: P3SAM,
    checkpoint_path: str | Path,
    *,
    verify_digest: bool = True,
) -> None:
    path = Path(checkpoint_path)
    if verify_digest:
        digest = checkpoint_sha256(path)
        if digest != EXPECTED_SHA256:
            raise ValueError(f"P3-SAM checkpoint digest mismatch: {digest}")
    parameters = dict(tree_flatten(model.parameters()))
    loaded: list[tuple[str, mx.array]] = []
    total = 0
    with safe_open(path, framework="numpy") as checkpoint:
        keys = list(checkpoint.keys())
        if len(keys) != EXPECTED_TENSORS:
            raise ValueError(
                f"expected {EXPECTED_TENSORS} P3-SAM tensors, found {len(keys)}"
            )
        for source_key in keys:
            key = _native_key(source_key)
            if key not in parameters:
                raise KeyError(
                    f"unexpected P3-SAM tensor {source_key!r} mapped to {key!r}"
                )
            value = checkpoint.get_tensor(source_key)
            if tuple(value.shape) != tuple(parameters[key].shape):
                raise ValueError(
                    f"P3-SAM shape mismatch for {source_key}: "
                    f"checkpoint {value.shape}, model {parameters[key].shape}"
                )
            total += value.size
            loaded.append((key, mx.array(value)))
    if total != EXPECTED_PARAMETERS:
        raise ValueError(f"expected {EXPECTED_PARAMETERS} parameters, found {total}")
    if {key for key, _ in loaded} != set(parameters):
        missing = sorted(set(parameters) - {key for key, _ in loaded})
        raise KeyError(f"missing P3-SAM tensors: {missing}")
    model.load_weights(loaded, strict=True)
    mx.eval(model.parameters())
