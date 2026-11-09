"""MLX fixed-mesh vertex-color refinement against the six Era3D views."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import mlx.core as mx
import mlx.optimizers as optim
import numpy as np
from mlx import nn
from numba import njit

from .instant_nsr_data import VIEW_NAMES
from .instant_nsr_mesh import InstantNSRMesh


@dataclass(frozen=True)
class VertexColorRefinementConfig:
    steps: int = 200
    learning_rate: float = 2e-3
    resolution: tuple[int, int] = (1024, 1024)
    view_weights: tuple[float, ...] = (1.0, 0.2, 0.7, 1.0, 0.7, 0.2)
    orthographic_scale: float = 1.0
    antialias_supersample: int = 2

    def __post_init__(self) -> None:
        if self.steps <= 0 or self.learning_rate <= 0.0:
            raise ValueError("color refinement steps and learning rate must be positive")
        if min(self.resolution) <= 0 or self.orthographic_scale <= 0.0:
            raise ValueError("refinement resolution and orthographic scale must be positive")
        if self.antialias_supersample <= 0:
            raise ValueError("antialias supersampling must be positive")
        if len(self.view_weights) != len(VIEW_NAMES):
            raise ValueError(f"color refinement requires {len(VIEW_NAMES)} view weights")


def orthographic_projection(scale: float, near: float = 0.1, far: float = 100.0) -> np.ndarray:
    if scale <= 0.0 or near >= far:
        raise ValueError("orthographic scale must be positive and near must precede far")
    matrix = np.zeros((4, 4), dtype=np.float32)
    matrix[0, 0] = 1.0 / scale
    matrix[1, 1] = 1.0 / scale
    matrix[2, 2] = 2.0 / (far - near)
    matrix[2, 3] = -(far + near) / (far - near)
    matrix[3, 3] = 1.0
    return matrix


def refinement_camera_matrices(
    camera_pose_dir: str | Path,
    *,
    scale: float = 1.0,
) -> np.ndarray:
    root = Path(camera_pose_dir)
    projection = orthographic_projection(scale)
    opengl_to_opencv = np.diag(np.asarray((1.0, -1.0, -1.0), dtype=np.float32))
    matrices = []
    for view in VIEW_NAMES:
        rt = np.loadtxt(root / f"000_{view}_RT.txt", dtype=np.float32)
        w2c = np.eye(4, dtype=np.float32)
        w2c[:3, :3] = opengl_to_opencv @ rt[:3, :3]
        w2c[:3, 3] = opengl_to_opencv @ rt[:3, 3]
        matrices.append(projection @ w2c)
    return np.stack(matrices)


@njit(cache=True)
def _rasterize_triangles(
    screen: np.ndarray,
    faces: np.ndarray,
    width: int,
    height: int,
) -> tuple[np.ndarray, np.ndarray]:
    triangle_map = np.full((height, width), -1, dtype=np.int32)
    barycentric_map = np.zeros((height, width, 3), dtype=np.float32)
    depth = np.full((height, width), np.inf, dtype=np.float32)
    for triangle_index in range(faces.shape[0]):
        i0, i1, i2 = faces[triangle_index]
        x0, y0, z0 = screen[i0]
        x1, y1, z1 = screen[i1]
        x2, y2, z2 = screen[i2]
        denominator = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(denominator) < 1e-12:
            continue
        minimum_x = max(0, int(np.ceil(min(x0, x1, x2))))
        maximum_x = min(width - 1, int(np.floor(max(x0, x1, x2))))
        minimum_y = max(0, int(np.ceil(min(y0, y1, y2))))
        maximum_y = min(height - 1, int(np.floor(max(y0, y1, y2))))
        for y in range(minimum_y, maximum_y + 1):
            for x in range(minimum_x, maximum_x + 1):
                w0 = ((y1 - y2) * (x - x2) + (x2 - x1) * (y - y2)) / denominator
                w1 = ((y2 - y0) * (x - x2) + (x0 - x2) * (y - y2)) / denominator
                w2 = 1.0 - w0 - w1
                if w0 < -1e-6 or w1 < -1e-6 or w2 < -1e-6:
                    continue
                pixel_depth = w0 * z0 + w1 * z1 + w2 * z2
                if pixel_depth < depth[y, x]:
                    depth[y, x] = pixel_depth
                    triangle_map[y, x] = triangle_index
                    barycentric_map[y, x, 0] = w0
                    barycentric_map[y, x, 1] = w1
                    barycentric_map[y, x, 2] = w2
    return triangle_map, barycentric_map


def rasterize_fixed_mesh(
    vertices: np.ndarray,
    faces: np.ndarray,
    matrix: np.ndarray,
    resolution: tuple[int, int],
) -> tuple[np.ndarray, np.ndarray]:
    width, height = resolution
    homogeneous = np.concatenate(
        (np.asarray(vertices, dtype=np.float32), np.ones((len(vertices), 1), dtype=np.float32)),
        axis=1,
    )
    clip = homogeneous @ np.asarray(matrix, dtype=np.float32).T
    ndc = clip[:, :3] / clip[:, 3:4]
    screen = np.empty_like(ndc)
    screen[:, 0] = (ndc[:, 0] + 1.0) * width * 0.5 - 0.5
    screen[:, 1] = (ndc[:, 1] + 1.0) * height * 0.5 - 0.5
    screen[:, 2] = ndc[:, 2]
    return _rasterize_triangles(screen, np.asarray(faces, dtype=np.int32), width, height)


class _VertexColors(nn.Module):
    def __init__(self, colors: np.ndarray):
        super().__init__()
        self.colors = mx.array(colors, dtype=mx.float32)


class FixedMeshColorRefiner:
    def __init__(
        self,
        mesh: InstantNSRMesh,
        target_images: np.ndarray,
        camera_matrices: np.ndarray,
        config: VertexColorRefinementConfig | None = None,
    ):
        config = config or VertexColorRefinementConfig()
        if mesh.colors is None:
            raise ValueError("fixed-mesh refinement requires model-derived initial vertex colors")
        width, height = config.resolution
        expected_images = (len(config.view_weights), height, width, 3)
        if target_images.shape != expected_images:
            raise ValueError(f"target images must have shape {expected_images}, got {target_images.shape}")
        if camera_matrices.shape != (len(config.view_weights), 4, 4):
            raise ValueError("camera matrices must have shape (views, 4, 4)")
        self.mesh = mesh
        self.config = config
        self.model = _VertexColors(mesh.colors)
        self.optimizer = optim.Adam(
            learning_rate=config.learning_rate,
            betas=[0.9, 0.999],
            eps=1e-8,
            bias_correction=True,
        )
        self.vertex_indices = []
        self.barycentrics = []
        self.pixel_indices = []
        self.targets = []
        supersample = config.antialias_supersample
        raster_resolution = (width * supersample, height * supersample)
        for view in range(len(config.view_weights)):
            triangles, barycentrics = rasterize_fixed_mesh(
                mesh.vertices,
                mesh.faces,
                camera_matrices[view],
                raster_resolution,
            )
            y, x = np.nonzero(triangles >= 0)
            selected_triangles = triangles[y, x]
            self.vertex_indices.append(mx.array(mesh.faces[selected_triangles], dtype=mx.int32))
            self.barycentrics.append(mx.array(barycentrics[y, x], dtype=mx.float32))
            base_pixels = (y // supersample) * width + x // supersample
            self.pixel_indices.append(mx.array(base_pixels, dtype=mx.int32))
            self.targets.append(mx.array(target_images[view].reshape(-1, 3), dtype=mx.float32))
        if not any(indices.shape[0] for indices in self.vertex_indices):
            raise RuntimeError("fixed mesh is outside every refinement camera")

    def _loss(self) -> mx.array:
        width, height = self.config.resolution
        sample_weight = 1.0 / self.config.antialias_supersample**2
        total = mx.array(0.0, dtype=mx.float32)
        for view, weight in enumerate(self.config.view_weights):
            indices = self.vertex_indices[view]
            rendered = mx.ones((height * width, 3), dtype=mx.float32)
            if indices.shape[0] > 0:
                interpolated = mx.sum(
                    self.model.colors[indices] * self.barycentrics[view][..., None],
                    axis=1,
                )
                contribution = (interpolated - 1.0) * sample_weight
                rendered = rendered.at[self.pixel_indices[view]].add(contribution)
            total = total + weight * mx.sum(mx.abs(rendered - self.targets[view]))
        return total / (len(self.config.view_weights) * height * width * 3)

    def refine(self) -> list[float]:
        losses = []
        for _ in range(self.config.steps):
            loss, gradients = nn.value_and_grad(self.model, self._loss)()
            self.optimizer.update(self.model, gradients)
            mx.eval(loss, self.model.parameters(), self.optimizer.state)
            losses.append(float(loss.item()))
        self.mesh.colors = np.asarray(self.model.colors).astype(np.float32)
        return losses
