"""Released P3-SAM mesh sampling and Sonata input preprocessing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import trimesh


@dataclass(frozen=True)
class P3SAMPointData:
    original_points: np.ndarray
    points: np.ndarray
    normals: np.ndarray
    face_indices: np.ndarray
    sampled_points: np.ndarray
    sampled_normals: np.ndarray
    features: np.ndarray
    grid_coord: np.ndarray
    inverse: np.ndarray
    batch: np.ndarray


def normalize_point_cloud(points: np.ndarray) -> np.ndarray:
    points = np.asarray(points, dtype=np.float32)
    maximum = points.max(axis=0)
    minimum = points.min(axis=0)
    center = (maximum + minimum) / 2.0
    scale = np.max(np.abs((maximum - minimum) / 2.0))
    return (points - center) / (scale + 1e-10)


def fnv_hash(grid_coord: np.ndarray) -> np.ndarray:
    coord = np.asarray(grid_coord).astype(np.uint64, copy=False)
    hashed = np.full(coord.shape[0], np.uint64(14695981039346656037), dtype=np.uint64)
    with np.errstate(over="ignore"):
        for column in range(coord.shape[1]):
            hashed *= np.uint64(1099511628211)
            hashed ^= coord[:, column]
    return hashed


def sonata_transform(
    points: np.ndarray,
    normals: np.ndarray,
    *,
    grid_size: float = 0.005,
    rng: np.random.RandomState | None = None,
) -> dict[str, np.ndarray]:
    coord = np.asarray(points, dtype=np.float32).copy()
    normal = np.asarray(normals, dtype=np.float32).copy()
    if coord.shape != normal.shape or coord.ndim != 2 or coord.shape[1] != 3:
        raise ValueError(
            f"points and normals must have matching [N,3] shapes, got {coord.shape}"
        )
    x_min, y_min, z_min = coord.min(axis=0)
    x_max, y_max, _ = coord.max(axis=0)
    coord -= np.asarray([(x_min + x_max) / 2, (y_min + y_max) / 2, z_min], np.float32)

    scaled = coord / np.asarray(grid_size)
    grid_coord = np.floor(scaled).astype(np.int64)
    minimum = grid_coord.min(axis=0)
    grid_coord -= minimum
    keys = fnv_hash(grid_coord)
    sorted_indices = np.argsort(keys)
    sorted_keys = keys[sorted_indices]
    _, inverse_sorted, counts = np.unique(
        sorted_keys, return_inverse=True, return_counts=True
    )
    rng = rng or np.random.RandomState()
    starts = np.cumsum(np.insert(counts, 0, 0)[:-1])
    offsets = rng.randint(0, counts.max(), counts.size) % counts
    selected = sorted_indices[starts + offsets]
    inverse = np.empty_like(inverse_sorted)
    inverse[sorted_indices] = inverse_sorted

    sampled_coord = coord[selected]
    sampled_normal = normal[selected]
    color = np.ones_like(sampled_coord, dtype=np.float32) / 255.0
    features = np.concatenate([sampled_coord, color, sampled_normal], axis=1)
    return {
        "coord": sampled_coord,
        "normal": sampled_normal,
        "color": color,
        "feat": features,
        "grid_coord": grid_coord[selected],
        "inverse": inverse.astype(np.int64),
        "batch": np.zeros(selected.size, dtype=np.int64),
        "selected": selected.astype(np.int64),
    }


def prepare_mesh_points(
    mesh_or_path: trimesh.Trimesh | str | Path,
    *,
    point_count: int = 100_000,
    seed: int = 42,
) -> tuple[trimesh.Trimesh, P3SAMPointData]:
    if isinstance(mesh_or_path, trimesh.Trimesh):
        mesh = mesh_or_path.copy()
    else:
        loaded = trimesh.load(mesh_or_path, force="mesh")
        if not isinstance(loaded, trimesh.Trimesh):
            raise TypeError(f"P3-SAM input did not resolve to one mesh: {mesh_or_path}")
        mesh = loaded
    mesh.merge_vertices()
    mesh.process(validate=True)
    mesh = trimesh.Trimesh(vertices=mesh.vertices, faces=mesh.faces, process=False)
    original, face_indices = trimesh.sample.sample_surface(mesh, point_count, seed=seed)
    points = normalize_point_cloud(original)
    normals = np.asarray(mesh.face_normals[face_indices], dtype=np.float32)
    transformed = sonata_transform(points, normals, rng=np.random.RandomState(seed))
    return mesh, P3SAMPointData(
        original_points=np.asarray(original, dtype=np.float32),
        points=np.asarray(points, dtype=np.float32),
        normals=normals,
        face_indices=np.asarray(face_indices, dtype=np.int64),
        sampled_points=transformed["coord"],
        sampled_normals=transformed["normal"],
        features=transformed["feat"],
        grid_coord=transformed["grid_coord"],
        inverse=transformed["inverse"],
        batch=transformed["batch"],
    )
