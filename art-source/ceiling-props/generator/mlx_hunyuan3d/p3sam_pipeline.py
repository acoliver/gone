"""Production P3-SAM automatic mesh-part segmentation pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fpsample
import mlx.core as mx
import numba
import numpy as np
import trimesh

from mlx_hunyuan3d.p3sam_data import prepare_mesh_points
from mlx_hunyuan3d.p3sam_model import P3SAM
from mlx_hunyuan3d.p3sam_weights import load_p3sam_weights


@dataclass(frozen=True)
class P3SAMConfig:
    point_count: int = 100_000
    prompt_count: int = 400
    prompt_batch_size: int = 32
    seed: int = 42
    nms_iou: float = 0.9
    cluster_minimum: int = 3
    bbox_iou: float = 0.5
    uncovered_ratio: float = 0.7
    component_area_ratio: float = 0.001
    post_process: bool = True
    post_process_threshold: float = 0.95

    def __post_init__(self) -> None:
        if self.point_count <= 0 or self.prompt_count <= 0:
            raise ValueError("P3-SAM point and prompt counts must be positive")
        if self.prompt_count > self.point_count:
            raise ValueError("P3-SAM prompt count cannot exceed sampled point count")
        if self.prompt_batch_size <= 0:
            raise ValueError("P3-SAM prompt batch size must be positive")
        for name, value in (
            ("nms_iou", self.nms_iou),
            ("bbox_iou", self.bbox_iou),
            ("uncovered_ratio", self.uncovered_ratio),
            ("component_area_ratio", self.component_area_ratio),
            ("post_process_threshold", self.post_process_threshold),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"P3-SAM {name} must be between zero and one")
        if self.cluster_minimum <= 0:
            raise ValueError("P3-SAM cluster minimum must be positive")


@dataclass(frozen=True)
class P3SAMResult:
    mesh: trimesh.Trimesh
    face_ids: np.ndarray
    aabbs: np.ndarray
    prompt_iou: np.ndarray
    mask_count: int


@numba.njit(cache=True)
def _adjacent_faces(face_adjacency: np.ndarray, face_count: int) -> np.ndarray:
    degrees = np.zeros(face_count, dtype=np.int32)
    for edge in range(face_adjacency.shape[0]):
        first, second = face_adjacency[edge]
        degrees[first] += 1
        degrees[second] += 1
    max_degree = max(1, int(np.max(degrees)))
    adjacent = np.full((face_count, max_degree), -1, dtype=np.int32)
    counts = np.zeros(face_count, dtype=np.int32)
    for edge in range(face_adjacency.shape[0]):
        first, second = face_adjacency[edge]
        adjacent[first, counts[first]] = second
        counts[first] += 1
        adjacent[second, counts[second]] = first
        counts[second] += 1
    return adjacent


def _mask_iou(first: np.ndarray, second: np.ndarray) -> float:
    union = np.count_nonzero(first | second)
    return float(np.count_nonzero(first & second) / union) if union else 0.0


def _single_iou(first: np.ndarray, second: np.ndarray) -> float:
    area = np.count_nonzero(first)
    return float(np.count_nonzero(first & second) / area) if area else 0.0


def _bbox(points: np.ndarray, mask: np.ndarray) -> np.ndarray:
    selected = points[mask]
    return np.stack([selected.min(axis=0), selected.max(axis=0)])


def _bbox_iou(first: np.ndarray, second: np.ndarray) -> float:
    lower = np.maximum(first[0], second[0])
    upper = np.minimum(first[1], second[1])
    intersection = np.prod(np.maximum(upper - lower, 0.0))
    first_volume = np.prod(first[1] - first[0])
    second_volume = np.prod(second[1] - second[0])
    union = first_volume + second_volume - intersection
    return float(intersection / union) if union > 0 else 0.0


def _fix_labels(face_ids: np.ndarray, adjacent: np.ndarray) -> np.ndarray:
    result = face_ids.copy()
    missing = np.flatnonzero(result < 0).tolist()
    for _ in range(50):
        if not missing:
            break
        remaining = []
        changed = False
        for face in missing:
            neighbors = adjacent[face]
            labels = result[neighbors[neighbors >= 0]]
            labels = labels[labels >= 0]
            if labels.size == 0:
                remaining.append(face)
                continue
            result[face] = np.argmax(np.bincount(labels))
            changed = True
        missing = remaining
        if not changed:
            break
    return result


def _connected_regions(face_ids: np.ndarray, adjacent: np.ndarray) -> list[np.ndarray]:
    visited = np.zeros(face_ids.size, dtype=np.bool_)
    regions: list[np.ndarray] = []
    for start in range(face_ids.size):
        if visited[start]:
            continue
        label = face_ids[start]
        stack = [start]
        region = []
        while stack:
            face = stack.pop()
            if visited[face]:
                continue
            visited[face] = True
            region.append(face)
            for neighbor in adjacent[face]:
                if (
                    neighbor >= 0
                    and not visited[neighbor]
                    and face_ids[neighbor] == label
                ):
                    stack.append(int(neighbor))
        regions.append(np.asarray(region, dtype=np.int64))
    return regions


def _region_neighbors(
    regions: list[np.ndarray], adjacent: np.ndarray
) -> list[list[int]]:
    face_region = np.full(adjacent.shape[0], -1, dtype=np.int64)
    for index, region in enumerate(regions):
        face_region[region] = index
    result: list[list[int]] = []
    for index, region in enumerate(regions):
        neighbors: set[int] = set()
        for face in region:
            for adjacent_face in adjacent[face]:
                if adjacent_face >= 0:
                    target = int(face_region[adjacent_face])
                    if target >= 0 and target != index:
                        neighbors.add(target)
        result.append(sorted(neighbors))
    return result


def _aabbs(mesh: trimesh.Trimesh, face_ids: np.ndarray) -> np.ndarray:
    boxes = []
    for label in np.unique(face_ids):
        if label < 0:
            continue
        vertices = mesh.vertices[mesh.faces[face_ids == label].reshape(-1)]
        boxes.append(np.stack([vertices.min(axis=0), vertices.max(axis=0)]))
    return np.asarray(boxes)


def _project_point_labels(
    face_count: int,
    face_indices: np.ndarray,
    point_labels: np.ndarray,
) -> np.ndarray:
    labels = np.full(face_count, -2, dtype=np.int64)
    sorting = np.argsort(face_indices, kind="stable")
    sorted_faces = face_indices[sorting]
    starts = np.flatnonzero(np.r_[True, sorted_faces[1:] != sorted_faces[:-1]])
    ends = np.r_[starts[1:], sorting.size]
    for start, end in zip(starts, ends, strict=True):
        face = int(sorted_faces[start])
        values = point_labels[sorting[start:end]]
        labels[face] = np.argmax(np.bincount(values + 2)) - 2
    return labels


def _model_masks(
    model: P3SAM,
    features: mx.array,
    points: np.ndarray,
    prompts: np.ndarray,
    batch_size: int,
) -> tuple[np.ndarray, np.ndarray]:
    masks = []
    scores = []
    for start in range(0, prompts.shape[0], batch_size):
        current = prompts[start : start + batch_size]
        probabilities, iou = model.masks(features, points, current)
        mx.eval(probabilities, iou)
        probabilities_np = np.asarray(probabilities)
        iou_np = np.asarray(iou)
        head = np.argmax(iou_np, axis=-1)
        for prompt_index, selected_head in enumerate(head):
            masks.append(probabilities_np[:, prompt_index, selected_head] > 0.5)
            scores.append(iou_np[prompt_index, selected_head])
    return np.stack(masks, axis=1), np.asarray(scores, dtype=np.float32)


def _select_masks(
    points: np.ndarray,
    masks: np.ndarray,
    scores: np.ndarray,
    config: P3SAMConfig,
) -> list[np.ndarray]:
    sorting = np.argsort(-scores, kind="stable")
    sorted_masks = [masks[:, index] for index in sorting]
    clusters: dict[int, list[int]] = {}
    for index, mask in enumerate(sorted_masks):
        for representative, members in clusters.items():
            if _mask_iou(mask, sorted_masks[representative]) > config.nms_iou:
                members.append(index)
                break
        else:
            clusters[index] = [index]

    filtered = [
        index
        for index, members in clusters.items()
        if len(members) >= config.cluster_minimum
    ]
    merged: dict[int, list[int]] = {}
    consumed: set[int] = set()
    boxes = {index: _bbox(points, sorted_masks[index]) for index in filtered}
    for offset, current in enumerate(filtered):
        if current in consumed:
            continue
        merged[current] = [current]
        for target in filtered[offset + 1 :]:
            if (
                target not in consumed
                and _bbox_iou(boxes[target], boxes[current]) > config.bbox_iou
            ):
                merged[current].append(target)
                consumed.add(target)

    uncovered = np.ones(points.shape[0], dtype=np.bool_)
    for representative in merged:
        uncovered[sorted_masks[representative]] = False
    for index, mask in enumerate(sorted_masks):
        if (
            index not in merged
            and _single_iou(mask, uncovered) > config.uncovered_ratio
        ):
            merged[index] = [index]
            uncovered[mask] = False
    representatives = sorted(
        merged, key=lambda index: np.count_nonzero(sorted_masks[index]), reverse=True
    )
    return [sorted_masks[index] for index in representatives]


def _clean_face_labels(
    mesh: trimesh.Trimesh,
    face_ids: np.ndarray,
    adjacent: np.ndarray,
    config: P3SAMConfig,
) -> np.ndarray:
    labels = _fix_labels(face_ids + 1, adjacent) - 1
    areas = np.asarray(mesh.area_faces)
    total_area = float(areas.sum())
    shell_regions = _connected_regions(np.ones_like(labels), adjacent)
    shell_id = np.empty(labels.size, dtype=np.int64)
    shell_areas = np.empty(len(shell_regions), dtype=np.float64)
    for index, region in enumerate(shell_regions):
        shell_id[region] = index
        shell_areas[index] = areas[region].sum()

    regions = _connected_regions(labels, adjacent)
    for region in regions:
        if (
            areas[region].sum() / (shell_areas[shell_id[region[0]]] + 1e-7)
            <= config.component_area_ratio
        ):
            labels[region] = -1
    labels = _fix_labels(labels, adjacent)

    regions = _connected_regions(labels, adjacent)
    next_label = max(0, int(labels.max()) + 1)
    for region in regions:
        if (
            labels[region[0]] < 0
            and areas[region].sum() / total_area > config.component_area_ratio
        ):
            labels[region] = next_label
            next_label += 1

    regions = _connected_regions(labels, adjacent)
    region_boxes = []
    region_labels = []
    for region in regions:
        vertices = mesh.vertices[mesh.faces[region].reshape(-1)]
        region_boxes.append(np.stack([vertices.min(axis=0), vertices.max(axis=0)]))
        region_labels.append(int(labels[region[0]]))
    neighbors = _region_neighbors(regions, adjacent)
    for index, region in enumerate(regions):
        if region_labels[index] >= 0:
            continue
        candidates = [
            candidate for candidate in neighbors[index] if region_labels[candidate] >= 0
        ]
        if not candidates:
            candidates = [
                candidate
                for candidate in range(len(regions))
                if region_labels[candidate] >= 0
            ]
        if not candidates:
            continue
        current = region_boxes[index]
        best = min(
            candidates,
            key=lambda candidate: np.max(
                np.abs(
                    np.concatenate(
                        [
                            np.minimum(region_boxes[candidate][0], current[0])
                            - region_boxes[candidate][0],
                            np.maximum(region_boxes[candidate][1], current[1])
                            - region_boxes[candidate][1],
                        ]
                    )
                )
            ),
        )
        labels[region] = region_labels[best]

    if config.post_process:
        regions = _connected_regions(labels, adjacent)
        region_areas = np.asarray(
            [areas[region].sum() / total_area for region in regions]
        )
        order = np.argsort(-region_areas)
        regions = [regions[index] for index in order]
        region_areas = region_areas[order]
        cumulative = np.cumsum(region_areas)
        neighbors = _region_neighbors(regions, adjacent)
        for index, region in enumerate(regions):
            if (
                cumulative[index] <= config.post_process_threshold
                or region_areas[index] >= 0.01
            ):
                continue
            candidates = [
                candidate
                for candidate in neighbors[index]
                if cumulative[candidate] <= config.post_process_threshold
            ]
            if candidates:
                target = max(candidates, key=lambda candidate: region_areas[candidate])
                labels[region] = labels[regions[target][0]]
    return labels


def colored_part_mesh(
    mesh: trimesh.Trimesh, face_ids: np.ndarray, seed: int = 42
) -> trimesh.Trimesh:
    rng = np.random.RandomState(seed)
    unique = [int(label) for label in np.unique(face_ids) if label >= 0]
    colors = {
        label: np.r_[rng.randint(40, 256, 3), 255].astype(np.uint8) for label in unique
    }
    face_colors = np.asarray(
        [
            colors.get(int(label), np.asarray([255, 0, 0, 255], np.uint8))
            for label in face_ids
        ]
    )
    result = mesh.copy()
    result.visual.face_colors = face_colors
    return result


class P3SAMSegmenter:
    def __init__(self, checkpoint_path: str | Path):
        self.model = P3SAM()
        load_p3sam_weights(self.model, checkpoint_path)
        self.model.eval()

    def segment(
        self,
        mesh_or_path: trimesh.Trimesh | str | Path,
        config: P3SAMConfig | None = None,
    ) -> P3SAMResult:
        config = config or P3SAMConfig()
        np.random.seed(config.seed)
        mesh, data = prepare_mesh_points(
            mesh_or_path, point_count=config.point_count, seed=config.seed
        )
        features = self.model.features(
            data.features,
            data.sampled_points,
            data.grid_coord,
            data.batch,
            data.inverse,
            seed=config.seed,
        )
        mx.eval(features)
        prompt_indices = fpsample.fps_sampling(data.points, config.prompt_count)
        prompts = data.points[prompt_indices]
        masks, scores = _model_masks(
            self.model,
            features,
            data.points,
            prompts,
            config.prompt_batch_size,
        )
        selected_masks = _select_masks(data.points, masks, scores, config)
        point_labels = np.full(config.point_count, -1, dtype=np.int64)
        for label, mask in enumerate(selected_masks):
            point_labels[mask] = label
        face_ids = _project_point_labels(
            len(mesh.faces), data.face_indices, point_labels
        )
        adjacent = _adjacent_faces(np.asarray(mesh.face_adjacency), len(mesh.faces))
        face_ids = _clean_face_labels(mesh, face_ids, adjacent, config)
        return P3SAMResult(
            mesh=mesh,
            face_ids=face_ids,
            aabbs=_aabbs(mesh, face_ids),
            prompt_iou=scores,
            mask_count=len(selected_masks),
        )

    @staticmethod
    def save(result: P3SAMResult, output_directory: str | Path, seed: int = 42) -> None:
        output = Path(output_directory)
        output.mkdir(parents=True, exist_ok=True)
        colored_part_mesh(result.mesh, result.face_ids, seed).export(
            output / "parts.glb"
        )
        np.save(output / "aabb.npy", result.aabbs)
        np.save(output / "face_ids.npy", result.face_ids)
        np.save(output / "prompt_iou.npy", result.prompt_iou)
