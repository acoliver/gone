"""MLX primitives for Era3D's six-view RGB/normal diffusion model.

Era3D's distinguishing operation is not a CUDA kernel. It is an exact pair of tensor
layouts around ordinary scaled dot-product attention:

* joint-domain attention lets corresponding normal and color samples attend together;
* row-wise attention joins matching scanlines from six generated views.

The upstream non-xformers joint-attention fallback restores its output incorrectly. These
functions intentionally implement the released xformers processor's semantics, replacing
only the attention kernel with MLX's fused SDPA.
"""

from __future__ import annotations

import math

import mlx.core as mx
import mlx.nn as nn

from mlx_hunyuan3d.paint_unet import Attention, FeedForward

ERA3D_NUM_VIEWS = 6
ERA3D_VIEW_NAMES = ("front", "front_right", "right", "back", "left", "front_left")


def join_domains(x: mx.array) -> mx.array:
    """Join normal/color token sequences from a task-major batch.

    Input order is ``[normal batch, color batch]`` with shape ``(2*b, tokens, channels)``.
    The result has shape ``(b, 2*tokens, channels)``. Linear Q/K/V projections commute
    with this concatenation, so joining before :class:`Attention` is mathematically equal
    to the upstream processor, which projects before joining.
    """
    if x.ndim != 3 or x.shape[0] % 2:
        raise ValueError(f"joint-domain attention requires (2*b,tokens,channels), got {x.shape}")
    normal, color = mx.split(x, 2, axis=0)
    return mx.concatenate([normal, color], axis=1)


def split_domains(x: mx.array) -> mx.array:
    """Inverse of :func:`join_domains`, restoring task-major batch order."""
    if x.ndim != 3 or x.shape[1] % 2:
        raise ValueError(f"joined domain sequence must have even token count, got {x.shape}")
    normal, color = mx.split(x, 2, axis=1)
    return mx.concatenate([normal, color], axis=0)


def to_rowwise(x: mx.array, num_views: int = ERA3D_NUM_VIEWS) -> tuple[mx.array, int, int]:
    """Transform ``(b*v,h*w,c)`` into Era3D's ``(b*h,v*w,c)`` attention layout."""
    if x.ndim != 3 or x.shape[0] % num_views:
        raise ValueError(f"row-wise attention requires batch divisible by {num_views}, got {x.shape}")
    height = math.isqrt(x.shape[1])
    if height * height != x.shape[1]:
        raise ValueError(f"Era3D row-wise tokens must form a square, got {x.shape[1]}")
    groups = x.shape[0] // num_views
    channels = x.shape[2]
    rows = x.reshape(groups, num_views, height, height, channels)
    rows = rows.transpose(0, 2, 1, 3, 4)
    return rows.reshape(groups * height, num_views * height, channels), groups, height


def from_rowwise(x: mx.array, groups: int, height: int,
                 num_views: int = ERA3D_NUM_VIEWS) -> mx.array:
    """Inverse of :func:`to_rowwise`."""
    expected = (groups * height, num_views * height)
    if x.ndim != 3 or x.shape[:2] != expected:
        raise ValueError(f"expected row-wise shape {expected}xC, got {x.shape}")
    channels = x.shape[2]
    views = x.reshape(groups, height, num_views, height, channels)
    views = views.transpose(0, 2, 1, 3, 4)
    return views.reshape(groups * num_views, height * height, channels)


class EraJointAttention(nn.Module):
    """Cross-domain self-attention pairing normal and RGB samples."""

    def __init__(self, dim: int, heads: int, dim_head: int):
        super().__init__()
        self.attention = Attention(dim, heads, dim_head)

    def __call__(self, x: mx.array) -> mx.array:
        return split_domains(self.attention(join_domains(x)))


class EraRowwiseMVAttention(nn.Module):
    """Self-attention over corresponding rows of all six views."""

    def __init__(self, dim: int, heads: int, dim_head: int,
                 num_views: int = ERA3D_NUM_VIEWS):
        super().__init__()
        self.attention = Attention(dim, heads, dim_head)
        self.num_views = num_views

    def __call__(self, x: mx.array) -> mx.array:
        rows, groups, height = to_rowwise(x, self.num_views)
        rows = self.attention(rows)
        return from_rowwise(rows, groups, height, self.num_views)


class EraBasicMVTransformerBlock(nn.Module):
    """The deployed Era3D ``self_rowwise`` transformer block.

    State names deliberately mirror upstream where practical: ``norm1``, ``attn1``,
    ``norm_mv``, ``attn_mv``, ``norm2``, ``attn2``, ``norm3`` and ``ff``. The special
    attention wrappers add one internal ``attention`` path that the weight loader removes
    when translating upstream ``attn*.to_*`` keys.
    """

    def __init__(self, dim: int, heads: int, dim_head: int,
                 cross_attention_dim: int = 1024, num_views: int = ERA3D_NUM_VIEWS):
        super().__init__()
        self.norm1 = nn.LayerNorm(dim)
        self.attn1 = EraJointAttention(dim, heads, dim_head)
        self.norm_mv = nn.LayerNorm(dim)
        self.attn_mv = EraRowwiseMVAttention(dim, heads, dim_head, num_views)
        self.norm2 = nn.LayerNorm(dim)
        self.attn2 = Attention(dim, heads, dim_head, context_dim=cross_attention_dim)
        self.norm3 = nn.LayerNorm(dim)
        self.ff = FeedForward(dim)

    def __call__(self, hidden: mx.array, context: mx.array) -> mx.array:
        hidden = hidden + self.attn1(self.norm1(hidden))
        hidden = hidden + self.attn_mv(self.norm_mv(hidden))
        hidden = hidden + self.attn2(self.norm2(hidden), context)
        return hidden + self.ff(self.norm3(hidden))
