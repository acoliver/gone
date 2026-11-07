"""One-tensor-at-a-time safetensors loading for Era3D MLX components."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from pathlib import Path
import re
from typing import Callable

import mlx.core as mx
import mlx.utils
import numpy as np
from safetensors import safe_open


@dataclass(frozen=True)
class TensorLoadRecord:
    source_name: str
    destination_name: str
    source_shape: tuple[int, ...]
    destination_shape: tuple[int, ...]
    source_dtype: str
    destination_dtype: str


@dataclass(frozen=True)
class ComponentLoadReport:
    source_path: str
    source_sha256: str
    tensors: tuple[TensorLoadRecord, ...]

    def to_dict(self) -> dict:
        return {
            "source_path": self.source_path,
            "source_sha256": self.source_sha256,
            "tensors": [asdict(record) for record in self.tensors],
        }


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


_SPECIAL_ATTENTION = re.compile(r"(^|\.)(attn1|attn_mv)(\.)")


def translate_unet_key(source_name: str) -> str:
    """Translate only Era3D wrapper paths that differ from the upstream module tree."""
    return _SPECIAL_ATTENTION.sub(r"\1\2.attention\3", source_name)


def _assign(module, dotted: str, value: mx.array) -> None:
    target = module
    parts = dotted.split(".")
    for part in parts[:-1]:
        target = target[int(part)] if part.isdigit() else getattr(target, part)
    final = parts[-1]
    if final.isdigit():
        target[int(final)] = value
    else:
        setattr(target, final, value)


def _source_metadata(path: Path) -> dict[str, tuple[tuple[int, ...], str]]:
    metadata = {}
    with safe_open(str(path), framework="np") as handle:
        for name in handle.keys():
            tensor = handle.get_slice(name)
            metadata[name] = (tuple(tensor.get_shape()), str(tensor.get_dtype()))
    return metadata


def load_component_streaming(
    module,
    path: str | Path,
    *,
    translate_key: Callable[[str], str] = lambda name: name,
    strict: bool = True,
    source_sha256: str | None = None,
) -> ComponentLoadReport:
    """Validate names/shapes, then assign one safetensor at a time.

    Validation uses only safetensors slice metadata and the MLX parameter tree. Payloads are
    fetched individually, transformed, evaluated, and released before the next key. This
    avoids the duplicate checkpoint-sized dictionary used by the older Paint loader.
    """
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)

    source_metadata = _source_metadata(source)
    destination_parameters = dict(mlx.utils.tree_flatten(module.parameters()))
    destination_names = {name: translate_key(name) for name in source_metadata}
    translated = list(destination_names.values())
    if len(translated) != len(set(translated)):
        raise ValueError("Era3D checkpoint key translation produced duplicate destinations")

    source_destinations = set(translated)
    model_destinations = set(destination_parameters)
    missing = source_destinations - model_destinations
    extra = model_destinations - source_destinations if strict else set()
    if missing or extra:
        raise ValueError(
            f"Era3D parameter mismatch: {len(missing)} missing destinations "
            f"(e.g. {sorted(missing)[:3]}), {len(extra)} model-only parameters "
            f"(e.g. {sorted(extra)[:3]})"
        )

    for source_name, (source_shape, _) in source_metadata.items():
        destination_name = destination_names[source_name]
        destination_shape = tuple(destination_parameters[destination_name].shape)
        transformed_shape = ((source_shape[0], source_shape[2], source_shape[3], source_shape[1])
                             if len(source_shape) == 4 else source_shape)
        if transformed_shape != destination_shape:
            raise ValueError(
                f"Era3D shape mismatch {source_name} -> {destination_name}: "
                f"{source_shape} transforms to {transformed_shape}, expected {destination_shape}"
            )

    # Do not retain references to every initialized destination array while replacing them.
    # Once validation is complete, dropping this flat tree lets each old parameter be released
    # as its checkpoint tensor is assigned instead of holding two full models until return.
    del destination_parameters

    records = []
    with safe_open(str(source), framework="np") as handle:
        for source_name in handle.keys():
            destination_name = destination_names[source_name]
            array = handle.get_tensor(source_name)
            source_shape = tuple(array.shape)
            source_dtype = str(array.dtype)
            if array.ndim == 4:
                array = np.transpose(array, (0, 2, 3, 1))
            value = mx.array(array)
            mx.eval(value)
            _assign(module, destination_name, value)
            records.append(TensorLoadRecord(
                source_name=source_name,
                destination_name=destination_name,
                source_shape=source_shape,
                destination_shape=tuple(value.shape),
                source_dtype=source_dtype,
                destination_dtype=str(value.dtype),
            ))

    return ComponentLoadReport(
        source_path=str(source),
        source_sha256=source_sha256 or sha256_file(source),
        tensors=tuple(records),
    )
