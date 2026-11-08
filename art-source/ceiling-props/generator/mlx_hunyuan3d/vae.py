"""MLX port of the Hunyuan3D ``ShapeVAE`` decoder (vecset latents -> occupancy grid).

Only the decoding half is ported: ``post_kl`` -> self-attention ``transformer`` ->
``geo_decoder`` cross-attention queried on a dense 3D grid. The point-cloud encoder is
not needed for image-to-3D inference (and requires ``torch_cluster`` FPS upstream).
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple, Union

import mlx.core as mx
import mlx.nn as nn
import numpy as np


class FourierEmbedder:
    """sin/cos positional embedding of 3D coordinates (``include_input=True``)."""

    def __init__(self, num_freqs: int = 8, logspace: bool = True, input_dim: int = 3,
                 include_input: bool = True, include_pi: bool = True):
        if logspace:
            frequencies = 2.0 ** np.arange(num_freqs, dtype=np.float32)
        else:
            frequencies = np.linspace(1.0, 2.0 ** (num_freqs - 1), num_freqs, dtype=np.float32)
        if include_pi:
            frequencies = frequencies * np.pi
        self.frequencies = mx.array(frequencies)
        self.include_input = include_input
        self.num_freqs = num_freqs
        temp = 1 if include_input or num_freqs == 0 else 0
        self.out_dim = input_dim * (num_freqs * 2 + temp)

    def __call__(self, x: mx.array) -> mx.array:
        if self.num_freqs == 0:
            return x
        embed = (x[..., None] * self.frequencies.astype(x.dtype)).reshape(*x.shape[:-1], -1)
        parts = [x] if self.include_input else []
        parts += [mx.sin(embed), mx.cos(embed)]
        return mx.concatenate(parts, axis=-1)


class MLP(nn.Module):
    def __init__(self, width: int, expand_ratio: int = 4, output_width: Optional[int] = None):
        super().__init__()
        self.c_fc = nn.Linear(width, width * expand_ratio)
        self.c_proj = nn.Linear(width * expand_ratio, output_width or width)

    def __call__(self, x: mx.array) -> mx.array:
        return self.c_proj(nn.gelu(self.c_fc(x)))


class QKVMultiheadAttention(nn.Module):
    """Self-attention over a fused ``B L (H (3 D))`` projection (head-major layout)."""

    def __init__(self, heads: int, width: int, qk_norm: bool = False):
        super().__init__()
        self.heads = heads
        self.qk_norm = qk_norm
        if qk_norm:
            self.q_norm = nn.LayerNorm(width // heads, eps=1e-6)
            self.k_norm = nn.LayerNorm(width // heads, eps=1e-6)

    def __call__(self, qkv: mx.array) -> mx.array:
        bs, n_ctx, width = qkv.shape
        attn_ch = width // self.heads // 3
        qkv = qkv.reshape(bs, n_ctx, self.heads, 3 * attn_ch)
        q = qkv[..., :attn_ch]
        k = qkv[..., attn_ch : 2 * attn_ch]
        v = qkv[..., 2 * attn_ch :]
        if self.qk_norm:
            q = self.q_norm(q)
            k = self.k_norm(k)
        q, k, v = (t.transpose(0, 2, 1, 3) for t in (q, k, v))
        out = mx.fast.scaled_dot_product_attention(q, k, v, scale=attn_ch**-0.5)
        return out.transpose(0, 2, 1, 3).reshape(bs, n_ctx, -1)


class MultiheadAttention(nn.Module):
    def __init__(self, width: int, heads: int, qkv_bias: bool, qk_norm: bool = False):
        super().__init__()
        self.c_qkv = nn.Linear(width, width * 3, bias=qkv_bias)
        self.c_proj = nn.Linear(width, width)
        self.attention = QKVMultiheadAttention(heads=heads, width=width, qk_norm=qk_norm)

    def __call__(self, x: mx.array) -> mx.array:
        return self.c_proj(self.attention(self.c_qkv(x)))


class ResidualAttentionBlock(nn.Module):
    def __init__(self, width: int, heads: int, qkv_bias: bool = True, qk_norm: bool = False):
        super().__init__()
        self.attn = MultiheadAttention(width, heads, qkv_bias, qk_norm)
        self.ln_1 = nn.LayerNorm(width, eps=1e-6)
        self.mlp = MLP(width=width)
        self.ln_2 = nn.LayerNorm(width, eps=1e-6)

    def __call__(self, x: mx.array) -> mx.array:
        x = x + self.attn(self.ln_1(x))
        x = x + self.mlp(self.ln_2(x))
        return x


class Transformer(nn.Module):
    def __init__(self, width: int, layers: int, heads: int, qkv_bias: bool = True,
                 qk_norm: bool = False):
        super().__init__()
        self.resblocks = [
            ResidualAttentionBlock(width, heads, qkv_bias, qk_norm) for _ in range(layers)
        ]

    def __call__(self, x: mx.array) -> mx.array:
        for block in self.resblocks:
            x = block(x)
        return x


class QKVMultiheadCrossAttention(nn.Module):
    def __init__(self, heads: int, width: int, qk_norm: bool = False):
        super().__init__()
        self.heads = heads
        self.qk_norm = qk_norm
        if qk_norm:
            self.q_norm = nn.LayerNorm(width // heads, eps=1e-6)
            self.k_norm = nn.LayerNorm(width // heads, eps=1e-6)

    def __call__(self, q: mx.array, kv: mx.array) -> mx.array:
        _, n_ctx, _ = q.shape
        bs, n_data, width = kv.shape
        attn_ch = width // self.heads // 2
        q = q.reshape(bs, n_ctx, self.heads, -1)
        kv = kv.reshape(bs, n_data, self.heads, -1)
        k = kv[..., :attn_ch]
        v = kv[..., attn_ch:]
        if self.qk_norm:
            q = self.q_norm(q)
            k = self.k_norm(k)
        q, k, v = (t.transpose(0, 2, 1, 3) for t in (q, k, v))
        out = mx.fast.scaled_dot_product_attention(q, k, v, scale=q.shape[-1] ** -0.5)
        return out.transpose(0, 2, 1, 3).reshape(bs, n_ctx, -1)


class MultiheadCrossAttention(nn.Module):
    def __init__(self, width: int, heads: int, qkv_bias: bool = True,
                 data_width: Optional[int] = None, qk_norm: bool = False):
        super().__init__()
        data_width = width if data_width is None else data_width
        self.c_q = nn.Linear(width, width, bias=qkv_bias)
        self.c_kv = nn.Linear(data_width, width * 2, bias=qkv_bias)
        self.c_proj = nn.Linear(width, width)
        self.attention = QKVMultiheadCrossAttention(heads=heads, width=width, qk_norm=qk_norm)

    def __call__(self, x: mx.array, data: mx.array) -> mx.array:
        return self.c_proj(self.attention(self.c_q(x), self.c_kv(data)))

    def encode_kv(self, data: mx.array) -> mx.array:
        """Precompute the key/value projection so it can be reused across query chunks."""
        return self.c_kv(data)

    def call_with_kv(self, x: mx.array, kv: mx.array) -> mx.array:
        return self.c_proj(self.attention(self.c_q(x), kv))


class ResidualCrossAttentionBlock(nn.Module):
    def __init__(self, width: int, heads: int, mlp_expand_ratio: int = 4,
                 data_width: Optional[int] = None, qkv_bias: bool = True, qk_norm: bool = False):
        super().__init__()
        data_width = width if data_width is None else data_width
        self.attn = MultiheadCrossAttention(width, heads, qkv_bias, data_width, qk_norm)
        self.ln_1 = nn.LayerNorm(width, eps=1e-6)
        self.ln_2 = nn.LayerNorm(data_width, eps=1e-6)
        self.ln_3 = nn.LayerNorm(width, eps=1e-6)
        self.mlp = MLP(width=width, expand_ratio=mlp_expand_ratio)

    def __call__(self, x: mx.array, data: mx.array) -> mx.array:
        x = x + self.attn(self.ln_1(x), self.ln_2(data))
        return x + self.mlp(self.ln_3(x))

    def call_with_kv(self, x: mx.array, kv: mx.array) -> mx.array:
        x = x + self.attn.call_with_kv(self.ln_1(x), kv)
        return x + self.mlp(self.ln_3(x))


class CrossAttentionDecoder(nn.Module):
    """Maps 3D query points + latents to an occupancy/SDF logit."""

    def __init__(self, fourier_embedder: FourierEmbedder, out_channels: int, width: int,
                 heads: int, mlp_expand_ratio: int = 4, enable_ln_post: bool = True,
                 qkv_bias: bool = True, qk_norm: bool = False):
        super().__init__()
        self.fourier_embedder = fourier_embedder
        self.enable_ln_post = enable_ln_post
        self.query_proj = nn.Linear(fourier_embedder.out_dim, width)
        if not enable_ln_post:
            qk_norm = False
        self.cross_attn_decoder = ResidualCrossAttentionBlock(
            width=width, heads=heads, mlp_expand_ratio=mlp_expand_ratio,
            qkv_bias=qkv_bias, qk_norm=qk_norm,
        )
        if enable_ln_post:
            # NOTE: the reference uses the torch default eps (1e-5) for this norm only.
            self.ln_post = nn.LayerNorm(width, eps=1e-5)
        self.output_proj = nn.Linear(width, out_channels)

    def encode_kv(self, latents: mx.array) -> mx.array:
        return self.cross_attn_decoder.attn.encode_kv(self.cross_attn_decoder.ln_2(latents))

    def __call__(self, queries: mx.array, latents: Optional[mx.array] = None,
                 kv: Optional[mx.array] = None) -> mx.array:
        dtype = latents.dtype if latents is not None else kv.dtype
        query_embeddings = self.query_proj(self.fourier_embedder(queries).astype(dtype))
        if kv is None:
            x = self.cross_attn_decoder(query_embeddings, latents)
        else:
            x = self.cross_attn_decoder.call_with_kv(query_embeddings, kv)
        if self.enable_ln_post:
            x = self.ln_post(x)
        return self.output_proj(x)


def generate_dense_grid_points(bbox_min: np.ndarray, bbox_max: np.ndarray,
                               octree_resolution: int) -> Tuple[np.ndarray, List[int]]:
    num_cells = int(octree_resolution)
    axes = [
        np.linspace(bbox_min[i], bbox_max[i], num_cells + 1, dtype=np.float32) for i in range(3)
    ]
    xs, ys, zs = np.meshgrid(*axes, indexing="ij")
    xyz = np.stack((xs, ys, zs), axis=-1)
    return xyz, [num_cells + 1] * 3


class ShapeVAE(nn.Module):
    def __init__(self, num_latents: int, embed_dim: int, width: int, heads: int,
                 num_decoder_layers: int, geo_decoder_mlp_expand_ratio: int = 4,
                 geo_decoder_ln_post: bool = True, num_freqs: int = 8, include_pi: bool = True,
                 qkv_bias: bool = True, qk_norm: bool = False, scale_factor: float = 1.0,
                 **kwargs):
        super().__init__()
        self.fourier_embedder = FourierEmbedder(num_freqs=num_freqs, include_pi=include_pi)
        self.post_kl = nn.Linear(embed_dim, width)
        self.transformer = Transformer(
            width=width, layers=num_decoder_layers, heads=heads,
            qkv_bias=qkv_bias, qk_norm=qk_norm,
        )
        self.geo_decoder = CrossAttentionDecoder(
            fourier_embedder=self.fourier_embedder, out_channels=1, width=width, heads=heads,
            mlp_expand_ratio=geo_decoder_mlp_expand_ratio, enable_ln_post=geo_decoder_ln_post,
            qkv_bias=qkv_bias, qk_norm=qk_norm,
        )
        self.scale_factor = scale_factor
        self.latent_shape = (num_latents, embed_dim)

    def decode(self, latents: mx.array) -> mx.array:
        return self.transformer(self.post_kl(latents))

    def __call__(self, latents: mx.array) -> mx.array:
        return self.decode(latents)

    def decode_volume(
        self,
        latents: mx.array,
        bounds: Union[float, Sequence[float]] = 1.01,
        octree_resolution: int = 256,
        num_chunks: int = 20000,
        progress=None,
    ) -> np.ndarray:
        """Evaluate the geometry decoder on a dense grid, returning (B, R+1, R+1, R+1) logits."""
        if isinstance(bounds, (int, float)):
            bounds = [-bounds, -bounds, -bounds, bounds, bounds, bounds]
        bbox_min, bbox_max = np.array(bounds[0:3]), np.array(bounds[3:6])
        xyz_samples, grid_size = generate_dense_grid_points(bbox_min, bbox_max, octree_resolution)
        xyz_samples = xyz_samples.reshape(-1, 3)

        batch_size = latents.shape[0]
        # The latent-side key/value projection is identical for every chunk: hoist it.
        kv = self.geo_decoder.encode_kv(latents)
        mx.eval(kv)

        total = xyz_samples.shape[0]
        out = np.empty((batch_size, total), dtype=np.float32)
        for start in range(0, total, num_chunks):
            chunk = mx.array(xyz_samples[start : start + num_chunks])
            chunk = mx.broadcast_to(chunk[None], (batch_size, chunk.shape[0], 3))
            logits = self.geo_decoder(chunk, kv=kv)
            out[:, start : start + chunk.shape[1]] = np.array(
                logits.squeeze(-1).astype(mx.float32)
            )
            if progress is not None:
                progress(min(start + num_chunks, total), total)
        return out.reshape(batch_size, *grid_size)


def marching_cubes(grid_logits: np.ndarray, mc_level: float, bounds, octree_resolution: int):
    """Extract meshes from occupancy logits (Lewiner marching cubes)."""
    from skimage import measure

    if isinstance(bounds, (int, float)):
        bounds = [-bounds, -bounds, -bounds, bounds, bounds, bounds]
    bbox_min, bbox_max = np.array(bounds[0:3]), np.array(bounds[3:6])
    bbox_size = bbox_max - bbox_min
    grid_size = np.array([int(octree_resolution) + 1] * 3)

    outputs = []
    for i in range(grid_logits.shape[0]):
        vertices, faces, _, _ = measure.marching_cubes(
            grid_logits[i], mc_level, method="lewiner"
        )
        vertices = (vertices / grid_size * bbox_size + bbox_min).astype(np.float32)
        outputs.append((vertices, np.ascontiguousarray(faces)))
    return outputs
