"""Native-MLX P3-SAM model and Sonata PointTransformerV3 encoder."""

from __future__ import annotations

from dataclasses import dataclass

import mlx.core as mx
import numpy as np
from mlx import nn

from mlx_hunyuan3d.p3sam_serialization import SERIALIZATION_ORDERS, serialize

ENC_DEPTHS = (3, 3, 3, 12, 3)
ENC_CHANNELS = (48, 96, 192, 384, 512)
ENC_HEADS = (3, 6, 12, 24, 32)
PATCH_SIZE = 1024


@dataclass
class PointState:
    feat: mx.array
    coord: np.ndarray
    grid_coord: np.ndarray
    batch: np.ndarray
    serialized_order: np.ndarray
    serialized_inverse: np.ndarray
    neighbor_indices: mx.array
    parent: PointState | None = None
    pooling_inverse: np.ndarray | None = None


def _neighbor_indices(grid_coord: np.ndarray) -> np.ndarray:
    coord = np.asarray(grid_coord, dtype=np.int64)
    maximum = coord.max(axis=0) + 3
    strides = np.asarray([maximum[1] * maximum[2], maximum[2], 1], dtype=np.int64)
    keys = coord @ strides
    sorting = np.argsort(keys)
    sorted_keys = keys[sorting]
    missing = coord.shape[0]
    neighbors = np.full((coord.shape[0], 27), missing, dtype=np.int64)
    column = 0
    for x_offset in (-1, 0, 1):
        for y_offset in (-1, 0, 1):
            for z_offset in (-1, 0, 1):
                candidate = coord + np.asarray([x_offset, y_offset, z_offset])
                valid = np.all(candidate >= 0, axis=1) & np.all(
                    candidate < maximum, axis=1
                )
                candidate_keys = candidate @ strides
                positions = np.searchsorted(sorted_keys, candidate_keys)
                clipped = np.minimum(positions, sorted_keys.size - 1)
                found = (
                    valid
                    & (positions < sorted_keys.size)
                    & (sorted_keys[clipped] == candidate_keys)
                )
                neighbors[found, column] = sorting[clipped[found]]
                column += 1
    return neighbors


class _OrderRng:
    def __init__(self, seed: int):
        self._generator = np.random.RandomState(seed & 0xFFFFFFFF)

    def permutation(self, count: int) -> np.ndarray:
        result = np.arange(count, dtype=np.int64)
        for index in range(count - 1):
            random = int(self._generator.randint(0, 2**32, dtype=np.uint32))
            target = index + random % (count - index)
            result[index], result[target] = result[target], result[index]
        return result


def _serialized_arrays(
    grid_coord: np.ndarray,
    batch: np.ndarray,
    rng: _OrderRng,
) -> tuple[np.ndarray, np.ndarray]:
    permutation = rng.permutation(len(SERIALIZATION_ORDERS))
    _, order, inverse, _ = serialize(
        grid_coord,
        batch,
        order_permutation=permutation,
    )
    return order, inverse


class SparseSubmanifoldConv(nn.Module):
    def __init__(self, channels: int):
        super().__init__()
        self.weight = mx.zeros((channels, 3, 3, 3, channels))
        self.bias = mx.zeros((channels,))

    def __call__(self, feat: mx.array, neighbors: mx.array) -> mx.array:
        padded = mx.concatenate(
            [feat, mx.zeros((1, feat.shape[1]), dtype=feat.dtype)], axis=0
        )
        gathered = padded[neighbors].reshape(feat.shape[0], -1)
        weight = self.weight.reshape(self.weight.shape[0], -1).T
        return gathered @ weight + self.bias


class PointMLP(nn.Module):
    def __init__(self, channels: int):
        super().__init__()
        self.fc1 = nn.Linear(channels, channels * 4)
        self.fc2 = nn.Linear(channels * 4, channels)

    def __call__(self, x: mx.array) -> mx.array:
        return self.fc2(nn.gelu(self.fc1(x)))


class SerializedAttention(nn.Module):
    def __init__(self, channels: int, heads: int, order_index: int):
        super().__init__()
        self.channels = channels
        self.heads = heads
        self.order_index = order_index
        self.qkv = nn.Linear(channels, channels * 3)
        self.proj = nn.Linear(channels, channels)

    def __call__(self, point: PointState) -> mx.array:
        count = point.feat.shape[0]
        patch = min(count, PATCH_SIZE)
        if count > patch:
            padded_count = ((count + patch - 1) // patch) * patch
            pad = np.arange(padded_count, dtype=np.int64)
            remainder = count % patch
            if remainder:
                pad[padded_count - patch + remainder :] = pad[
                    padded_count - 2 * patch + remainder : padded_count - patch
                ]
        else:
            pad = np.arange(count, dtype=np.int64)
        order = point.serialized_order[self.order_index][pad]
        qkv = self.qkv(point.feat)[mx.array(order)]
        head_dim = self.channels // self.heads
        windows = qkv.reshape(-1, patch, 3, self.heads, head_dim)
        q = mx.transpose(windows[:, :, 0], (0, 2, 1, 3))
        k = mx.transpose(windows[:, :, 1], (0, 2, 1, 3))
        v = mx.transpose(windows[:, :, 2], (0, 2, 1, 3))
        scores = (q * (head_dim**-0.5)) @ mx.swapaxes(k, -1, -2)
        attended = mx.softmax(scores, axis=-1) @ v
        attended = mx.transpose(attended, (0, 2, 1, 3)).reshape(-1, self.channels)
        restored = attended[mx.array(point.serialized_inverse[self.order_index])]
        return self.proj(restored)


class SonataBlock(nn.Module):
    def __init__(self, channels: int, heads: int, order_index: int):
        super().__init__()
        self.cpe = [
            SparseSubmanifoldConv(channels),
            nn.Linear(channels, channels),
            nn.LayerNorm(channels),
        ]
        self.norm1 = [nn.LayerNorm(channels)]
        self.attn = SerializedAttention(channels, heads, order_index)
        self.norm2 = [nn.LayerNorm(channels)]
        self.mlp = [PointMLP(channels)]

    def __call__(self, point: PointState) -> PointState:
        cpe = self.cpe[0](point.feat, point.neighbor_indices)
        cpe = self.cpe[2](self.cpe[1](cpe))
        point.feat = point.feat + cpe
        point.feat = point.feat + self.attn(
            self._with_feat(point, self.norm1[0](point.feat))
        )
        point.feat = point.feat + self.mlp[0](self.norm2[0](point.feat))
        return point

    @staticmethod
    def _with_feat(point: PointState, feat: mx.array) -> PointState:
        return PointState(
            feat=feat,
            coord=point.coord,
            grid_coord=point.grid_coord,
            batch=point.batch,
            serialized_order=point.serialized_order,
            serialized_inverse=point.serialized_inverse,
            neighbor_indices=point.neighbor_indices,
            parent=point.parent,
            pooling_inverse=point.pooling_inverse,
        )


class GridPooling(nn.Module):
    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()
        self.proj = nn.Linear(in_channels, out_channels)
        self.norm = [nn.LayerNorm(out_channels)]

    def __call__(self, point: PointState, rng: _OrderRng) -> PointState:
        pooled_grid = point.grid_coord // 2
        packed = pooled_grid | (point.batch[:, None] << 48)
        unique, cluster, counts = np.unique(
            packed, axis=0, return_inverse=True, return_counts=True
        )
        pooled_grid = unique & ((1 << 48) - 1)
        cluster_mx = mx.array(cluster.astype(np.int32))
        projected = self.proj(point.feat)
        pooled_feat = mx.full((unique.shape[0], projected.shape[1]), -mx.inf)
        pooled_feat = pooled_feat.at[cluster_mx].maximum(projected)
        pooled_feat = nn.gelu(self.norm[0](pooled_feat))
        sums = np.zeros((unique.shape[0], 3), dtype=np.float64)
        np.add.at(sums, cluster, point.coord)
        pooled_coord = (sums / counts[:, None]).astype(np.float32)
        sorting = np.argsort(cluster, kind="stable")
        starts = np.cumsum(np.insert(counts, 0, 0)[:-1])
        heads = sorting[starts]
        pooled_batch = point.batch[heads]
        order, inverse = _serialized_arrays(pooled_grid, pooled_batch, rng)
        return PointState(
            feat=pooled_feat,
            coord=pooled_coord,
            grid_coord=pooled_grid.astype(np.int64),
            batch=pooled_batch,
            serialized_order=order,
            serialized_inverse=inverse,
            neighbor_indices=mx.array(_neighbor_indices(pooled_grid).astype(np.int32)),
            parent=point,
            pooling_inverse=cluster.astype(np.int64),
        )


class SonataStage(nn.Module):
    def __init__(self, stage: int):
        super().__init__()
        if stage > 0:
            self.down = GridPooling(ENC_CHANNELS[stage - 1], ENC_CHANNELS[stage])
        for block in range(ENC_DEPTHS[stage]):
            setattr(
                self,
                f"block{block}",
                SonataBlock(
                    ENC_CHANNELS[stage],
                    ENC_HEADS[stage],
                    block % len(SERIALIZATION_ORDERS),
                ),
            )
        self.stage = stage

    def __call__(self, point: PointState, rng: _OrderRng) -> PointState:
        if self.stage > 0:
            point = self.down(point, rng)
        for block in range(ENC_DEPTHS[self.stage]):
            point = getattr(self, f"block{block}")(point)
        return point


class SonataEncoder(nn.Module):
    def __init__(self):
        super().__init__()
        for stage in range(len(ENC_DEPTHS)):
            setattr(self, f"enc{stage}", SonataStage(stage))

    def __call__(self, point: PointState, rng: _OrderRng) -> PointState:
        for stage in range(len(ENC_DEPTHS)):
            point = getattr(self, f"enc{stage}")(point, rng)
        return point


class SonataStem(nn.Module):
    def __init__(self):
        super().__init__()
        self.linear = nn.Linear(9, ENC_CHANNELS[0])
        self.norm = nn.LayerNorm(ENC_CHANNELS[0])

    def __call__(self, feat: mx.array) -> mx.array:
        return nn.gelu(self.norm(self.linear(feat)))


class SonataEmbedding(nn.Module):
    def __init__(self):
        super().__init__()
        self.stem = SonataStem()
        self.mask_token = mx.zeros((1, ENC_CHANNELS[0]))


class Sonata(nn.Module):
    def __init__(self):
        super().__init__()
        self.embedding = SonataEmbedding()
        self.enc = SonataEncoder()

    def __call__(
        self,
        features: mx.array,
        coord: np.ndarray,
        grid_coord: np.ndarray,
        batch: np.ndarray,
        rng: _OrderRng,
    ) -> PointState:
        order, inverse = _serialized_arrays(grid_coord, batch, rng)
        point = PointState(
            feat=self.embedding.stem(features),
            coord=coord,
            grid_coord=grid_coord,
            batch=batch,
            serialized_order=order,
            serialized_inverse=inverse,
            neighbor_indices=mx.array(_neighbor_indices(grid_coord).astype(np.int32)),
        )
        return self.enc(point, rng)


class P3SAM(nn.Module):
    def __init__(self):
        super().__init__()
        self.sonata = Sonata()
        self.mlp = nn.Sequential(
            nn.Linear(1232, 512),
            nn.GELU(),
            nn.Linear(512, 512),
            nn.GELU(),
            nn.Linear(512, 512),
        )
        self.seg_mlp_1 = self._mlp(518, 512, 1)
        self.seg_mlp_2 = self._mlp(518, 512, 1)
        self.seg_mlp_3 = self._mlp(518, 512, 1)
        self.seg_s2_mlp_g = self._mlp(521, 256, 256)
        self.seg_s2_mlp_1 = self._mlp(777, 256, 1)
        self.seg_s2_mlp_2 = self._mlp(777, 256, 1)
        self.seg_s2_mlp_3 = self._mlp(777, 256, 1)
        self.iou_mlp = self._mlp(777, 256, 256)
        self.iou_mlp_out = self._mlp(256, 256, 3)

    @staticmethod
    def _mlp(in_dim: int, hidden_dim: int, out_dim: int) -> nn.Sequential:
        return nn.Sequential(
            nn.Linear(in_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, out_dim),
        )

    def features(
        self,
        features: np.ndarray,
        coord: np.ndarray,
        grid_coord: np.ndarray,
        batch: np.ndarray,
        inverse: np.ndarray,
        *,
        seed: int = 42,
    ) -> mx.array:
        point = self.sonata(
            mx.array(features), coord, grid_coord, batch, _OrderRng(seed)
        )
        while point.parent is not None:
            parent = point.parent
            parent.feat = mx.concatenate(
                [parent.feat, point.feat[mx.array(point.pooling_inverse)]], axis=-1
            )
            point = parent
        encoded = self.mlp(point.feat)
        return encoded[mx.array(inverse)]

    def masks(
        self,
        features: mx.array,
        points: np.ndarray,
        prompts: np.ndarray,
    ) -> tuple[mx.array, mx.array]:
        point_array = mx.array(points)
        prompt_array = mx.array(prompts)
        count, prompt_count = points.shape[0], prompts.shape[0]
        feat = mx.broadcast_to(features[:, None, :], (count, prompt_count, 512))
        point = mx.broadcast_to(point_array[:, None, :], (count, prompt_count, 3))
        prompt = mx.broadcast_to(prompt_array[None, :, :], (count, prompt_count, 3))
        stage1_input = mx.concatenate([feat, point, prompt], axis=-1)
        logits = mx.stack(
            [
                self.seg_mlp_1(stage1_input)[..., 0],
                self.seg_mlp_2(stage1_input)[..., 0],
                self.seg_mlp_3(stage1_input)[..., 0],
            ],
            axis=-1,
        )
        stage2_input = mx.concatenate([stage1_input, logits], axis=-1)
        global_feature = mx.max(self.seg_s2_mlp_g(stage2_input), axis=0)
        global_feature = mx.broadcast_to(
            global_feature[None], (count, prompt_count, 256)
        )
        combined = mx.concatenate([global_feature, stage2_input], axis=-1)
        logits = mx.stack(
            [
                self.seg_s2_mlp_1(combined)[..., 0],
                self.seg_s2_mlp_2(combined)[..., 0],
                self.seg_s2_mlp_3(combined)[..., 0],
            ],
            axis=-1,
        )
        iou_input = mx.concatenate([global_feature, stage1_input, logits], axis=-1)
        iou = mx.sigmoid(self.iou_mlp_out(mx.max(self.iou_mlp(iou_input), axis=0)))
        return mx.sigmoid(logits), iou
