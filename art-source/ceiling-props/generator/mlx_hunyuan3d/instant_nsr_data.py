"""Orthographic six-view inputs for native MLX Instant-NSR training."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import mlx.core as mx
import numpy as np
from PIL import Image

VIEW_NAMES = ("front", "front_right", "right", "back", "left", "front_left")


@dataclass(frozen=True)
class OrthographicDataConfig:
    image_size: tuple[int, int] = (1024, 1024)
    view_names: tuple[str, ...] = VIEW_NAMES
    view_weights: tuple[float, ...] = (1.0, 0.7, 0.4, 1.0, 0.7, 0.4)
    apply_mask: bool = True


DEFAULT_DATA_CONFIG = OrthographicDataConfig()


def _opengl_to_opencv_rt(rt: np.ndarray) -> np.ndarray:
    basis = np.diag(np.asarray((1.0, -1.0, -1.0), dtype=np.float32))
    return np.concatenate((basis @ rt[:3, :3], (basis @ rt[:3, 3])[:, None]), axis=1)


def _invert_rt(rt: np.ndarray) -> np.ndarray:
    homogeneous = np.concatenate((rt, np.asarray(((0.0, 0.0, 0.0, 1.0),))), axis=0)
    return np.linalg.inv(homogeneous)[:3].astype(np.float32)


def _rgba_image(path: Path, image_size: tuple[int, int]) -> np.ndarray:
    image = Image.open(path)
    if image.mode == "RGB":
        from rembg import remove

        image = remove(image)
    return np.asarray(image.resize(image_size), dtype=np.uint8)


def _prediction_path(root: Path, kind: str, view: str, index: int) -> Path:
    numbered_kind = "normal" if kind == "normals" else kind
    candidates = (
        root / f"{kind}_{view}_masked.png",
        root / f"{numbered_kind}_{index}.png",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    names = ", ".join(str(path) for path in candidates)
    raise FileNotFoundError(f"missing Era3D {kind} view; expected one of: {names}")


def _ortho_camera_grid(width: int, height: int) -> tuple[np.ndarray, np.ndarray]:
    x, y = np.meshgrid(
        np.arange(width, dtype=np.float32) + 0.5,
        np.arange(height, dtype=np.float32) + 0.5,
        indexing="xy",
    )
    origins = np.stack(
        ((x / width - 0.5) * 2.0, (y / height - 0.5) * 2.0, np.zeros_like(x)), axis=-1
    )
    directions = np.stack(
        (np.zeros_like(x), np.zeros_like(y), np.ones_like(x)), axis=-1
    )
    return origins.astype(np.float32), directions.astype(np.float32)


class OrthographicViewDataset:
    def __init__(
        self,
        *,
        images: np.ndarray,
        foreground_masks: np.ndarray,
        rgb_masks: np.ndarray,
        world_normals: np.ndarray,
        camera_to_world: np.ndarray,
        view_weights: Sequence[float],
        apply_mask: bool,
        color_alpha: np.ndarray | None = None,
    ):
        views, height, width, channels = images.shape
        expected_vector_shape = (views, height, width, 3)
        expected_mask_shape = (views, height, width)
        if channels != 3 or world_normals.shape != expected_vector_shape:
            raise ValueError(
                "images and world normals must have shape (views, height, width, 3)"
            )
        if (
            foreground_masks.shape != expected_mask_shape
            or rgb_masks.shape != expected_mask_shape
        ):
            raise ValueError(
                "orthographic masks must have shape (views, height, width)"
            )
        if color_alpha is not None and color_alpha.shape != expected_mask_shape:
            raise ValueError("color alpha must have shape (views, height, width)")
        if camera_to_world.shape != (views, 3, 4):
            raise ValueError(f"camera_to_world must have shape ({views}, 3, 4)")
        if len(view_weights) != views:
            raise ValueError(f"expected {views} view weights, got {len(view_weights)}")

        self.images = np.asarray(images, dtype=np.float32)
        self.foreground_masks = np.asarray(foreground_masks, dtype=np.bool_)
        self.rgb_masks = np.asarray(rgb_masks, dtype=np.bool_)
        if color_alpha is None:
            color_alpha = foreground_masks.astype(np.float32)
        self.color_alpha = np.asarray(color_alpha, dtype=np.float32)
        self.world_normals = np.asarray(world_normals, dtype=np.float32)
        self.camera_to_world = np.asarray(camera_to_world, dtype=np.float32)
        self.view_weights = np.asarray(view_weights, dtype=np.float32)
        self.apply_mask = apply_mask
        self.height = height
        self.width = width
        self.origins, self.directions = _ortho_camera_grid(width, height)

    @property
    def num_views(self) -> int:
        return self.images.shape[0]

    @property
    def refinement_images(self) -> np.ndarray:
        alpha = self.color_alpha[..., None]
        return self.images * alpha + (1.0 - alpha)

    def sample(self, count: int, rng: np.random.Generator) -> dict[str, mx.array]:
        if count <= 0:
            raise ValueError(f"ray count must be positive, got {count}")
        selected_view = int(rng.integers(0, self.num_views))
        view = np.full((count,), selected_view, dtype=np.int64)
        x = rng.integers(0, self.width, size=count)
        y = rng.integers(0, self.height, size=count)

        c2w = self.camera_to_world[view]
        local_origins = self.origins[y, x]
        local_directions = self.directions[y, x]
        ray_origins = (
            np.einsum("nij,nj->ni", c2w[:, :3, :3], local_origins) + c2w[:, :3, 3]
        )
        ray_directions = np.einsum("nij,nj->ni", c2w[:, :3, :3], local_directions)
        ray_directions /= np.linalg.norm(ray_directions, axis=-1, keepdims=True)

        foreground = self.foreground_masks[view, y, x]
        rgb = self.images[view, y, x].copy()
        if self.apply_mask:
            rgb = rgb * foreground[:, None] + (1.0 - foreground[:, None])
        return {
            "ray_origins": mx.array(ray_origins),
            "ray_directions": mx.array(ray_directions),
            "rgb": mx.array(rgb),
            "normal": mx.array(self.world_normals[view, y, x]),
            "foreground_mask": mx.array(foreground),
            "rgb_mask": mx.array(self.rgb_masks[view, y, x]),
            "view_weights": mx.array(self.view_weights[view]),
            "view_index": mx.array(view),
            "x": mx.array(x),
            "y": mx.array(y),
        }


def load_era3d_orthographic_views(
    prediction_dir: str | Path,
    camera_pose_dir: str | Path,
    config: OrthographicDataConfig = DEFAULT_DATA_CONFIG,
) -> OrthographicViewDataset:
    if len(config.view_names) != len(config.view_weights):
        raise ValueError("view_names and view_weights must have equal lengths")
    prediction_root = Path(prediction_dir)
    pose_root = Path(camera_pose_dir)

    front_rt = np.loadtxt(pose_root / "000_front_RT.txt", dtype=np.float32)
    front_c2w = _invert_rt(_opengl_to_opencv_rt(front_rt))
    images = []
    foreground_masks = []
    rgb_masks = []
    color_alpha = []
    world_normals = []
    camera_to_world = []

    for index, view in enumerate(config.view_names):
        normal_rgba = _rgba_image(
            _prediction_path(prediction_root, "normals", view, index),
            config.image_size,
        )
        color_rgba = _rgba_image(
            _prediction_path(prediction_root, "color", view, index),
            config.image_size,
        )
        if normal_rgba.shape[-1] != 4 or color_rgba.shape[-1] != 4:
            raise ValueError("background removal must produce RGBA Era3D views")

        color_alpha_view = color_rgba[..., 3].astype(np.float32) / 255.0
        foreground = color_alpha_view > 0.5
        normal = normal_rgba[..., :3].astype(np.float32) / 255.0 * 2.0 - 1.0
        # Normal-map matting can fill enclosed negative space; the color matte preserves it.
        normal[~foreground] = 0.0
        normal_opencv = normal * np.asarray((1.0, -1.0, -1.0), dtype=np.float32)
        world_normal = np.einsum("ij,hwj->hwi", front_c2w[:3, :3], normal_opencv)

        color = color_rgba[..., :3].astype(np.float32) / 255.0
        invalid_color = color_rgba[..., 3] < 127.5
        invalid_white = np.all(color_rgba[..., :3] > 250, axis=-1)
        rgb_mask = ~(invalid_color & invalid_white)

        rt = np.loadtxt(pose_root / f"000_{view}_RT.txt", dtype=np.float32)
        c2w = _invert_rt(_opengl_to_opencv_rt(rt))
        images.append(color)
        foreground_masks.append(foreground)
        rgb_masks.append(rgb_mask)
        color_alpha.append(color_alpha_view)
        world_normals.append(world_normal)
        camera_to_world.append(c2w)

    return OrthographicViewDataset(
        images=np.stack(images),
        foreground_masks=np.stack(foreground_masks),
        rgb_masks=np.stack(rgb_masks),
        world_normals=np.stack(world_normals),
        camera_to_world=np.stack(camera_to_world),
        view_weights=config.view_weights,
        apply_mask=config.apply_mask,
        color_alpha=np.stack(color_alpha),
    )
