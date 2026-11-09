"""Chunked coarse-to-fine marching cubes and vertex colors for Instant-NSR."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import mlx.core as mx
import numpy as np
from skimage.measure import marching_cubes

from .instant_nsr import InstantNSRGeometry
from .instant_nsr_render import RadianceMLP


@dataclass(frozen=True)
class MeshExtractionConfig:
    resolution: int = 256
    radius: float = 1.0
    threshold: float = 0.0
    bounds_padding: float = 0.1
    chunk_size: int = 2_097_152

    def __post_init__(self) -> None:
        if self.resolution <= 2 or self.radius <= 0.0:
            raise ValueError("mesh resolution must exceed two and radius must be positive")
        if self.bounds_padding < 0.0 or self.chunk_size <= 0:
            raise ValueError("mesh bounds padding must be non-negative and chunk size positive")


@dataclass
class InstantNSRMesh:
    vertices: np.ndarray
    faces: np.ndarray
    colors: np.ndarray | None = None


def _grid_points(
    flat_indices: np.ndarray,
    resolution: int,
    minimum: np.ndarray,
    maximum: np.ndarray,
) -> np.ndarray:
    x = flat_indices // (resolution * resolution)
    y = (flat_indices // resolution) % resolution
    z = flat_indices % resolution
    coordinates = np.stack((x, y, z), axis=-1).astype(np.float32)
    normalized = coordinates / (resolution - 1)
    return minimum + normalized * (maximum - minimum)


def evaluate_sdf_grid(
    geometry: InstantNSRGeometry,
    minimum: np.ndarray,
    maximum: np.ndarray,
    *,
    resolution: int,
    chunk_size: int,
) -> np.ndarray:
    minimum = np.asarray(minimum, dtype=np.float32)
    maximum = np.asarray(maximum, dtype=np.float32)
    if minimum.shape != (3,) or maximum.shape != (3,) or np.any(maximum <= minimum):
        raise ValueError("marching-cubes bounds must be increasing three-vectors")
    total = resolution**3
    values = np.empty((total,), dtype=np.float32)
    for start in range(0, total, chunk_size):
        stop = min(start + chunk_size, total)
        indices = np.arange(start, stop, dtype=np.int64)
        sdf = geometry.forward_level(
            mx.array(_grid_points(indices, resolution, minimum, maximum))
        )
        values[start:stop] = np.asarray(sdf)
    return values.reshape((resolution,) * 3)


def extract_isosurface(
    geometry: InstantNSRGeometry,
    minimum: np.ndarray,
    maximum: np.ndarray,
    config: MeshExtractionConfig,
) -> InstantNSRMesh:
    minimum = np.asarray(minimum, dtype=np.float32)
    maximum = np.asarray(maximum, dtype=np.float32)
    sdf = evaluate_sdf_grid(
        geometry,
        minimum,
        maximum,
        resolution=config.resolution,
        chunk_size=config.chunk_size,
    )
    if not float(np.min(sdf)) <= config.threshold <= float(np.max(sdf)):
        raise ValueError(
            f"SDF threshold {config.threshold} is outside sampled range "
            f"[{float(np.min(sdf))}, {float(np.max(sdf))}]"
        )
    spacing = tuple((maximum - minimum) / (config.resolution - 1))
    vertices, faces, _, _ = marching_cubes(
        -sdf,
        level=-config.threshold,
        spacing=spacing,
        gradient_direction="ascent",
        allow_degenerate=False,
    )
    vertices = vertices.astype(np.float32) + minimum
    return InstantNSRMesh(vertices=vertices, faces=faces.astype(np.int32))


def extract_coarse_to_fine_mesh(
    geometry: InstantNSRGeometry,
    config: MeshExtractionConfig = MeshExtractionConfig(),
) -> InstantNSRMesh:
    scene_minimum = np.full((3,), -config.radius, dtype=np.float32)
    scene_maximum = np.full((3,), config.radius, dtype=np.float32)
    coarse = extract_isosurface(geometry, scene_minimum, scene_maximum, config)
    coarse_minimum = np.min(coarse.vertices, axis=0)
    coarse_maximum = np.max(coarse.vertices, axis=0)
    extent = coarse_maximum - coarse_minimum
    fine_minimum = np.maximum(coarse_minimum - extent * config.bounds_padding, scene_minimum)
    fine_maximum = np.minimum(coarse_maximum + extent * config.bounds_padding, scene_maximum)
    return extract_isosurface(geometry, fine_minimum, fine_maximum, config)


def color_mesh_vertices(
    mesh: InstantNSRMesh,
    geometry: InstantNSRGeometry,
    texture: RadianceMLP,
    *,
    chunk_size: int = 2_097_152,
) -> InstantNSRMesh:
    if chunk_size <= 0:
        raise ValueError("vertex-color chunk size must be positive")
    colors = []
    for start in range(0, len(mesh.vertices), chunk_size):
        points = mx.array(mesh.vertices[start : start + chunk_size])
        _, gradient, feature = geometry(points, with_grad=True, with_feature=True)
        normal = gradient / mx.maximum(mx.linalg.norm(gradient, axis=-1, keepdims=True), 1e-8)
        color = texture(feature, normal)
        colors.append(np.asarray(color))
    mesh.colors = np.concatenate(colors, axis=0).astype(np.float32)
    return mesh


def export_glb(mesh: InstantNSRMesh, path: str | Path) -> None:
    import trimesh

    visual = None
    if mesh.colors is not None:
        color = np.clip(mesh.colors, 0.0, 1.0)
        alpha = np.ones((len(color), 1), dtype=np.float32)
        visual = trimesh.visual.ColorVisuals(vertex_colors=np.concatenate((color, alpha), axis=1))
    result = trimesh.Trimesh(
        vertices=mesh.vertices,
        faces=mesh.faces,
        visual=visual,
        process=False,
    )
    result.export(Path(path), file_type="glb")
