"""MLX port of ``Hunyuan3DDiT`` (the flow-matching denoiser of Hunyuan3D-2mv).

Architecturally a FLUX-style double/single stream DiT. The reference passes
``pe=None`` throughout, so no rotary embedding is applied anywhere.
"""

from __future__ import annotations

import math
from typing import List, Optional

import mlx.core as mx
import mlx.nn as nn


def timestep_embedding(
    t: mx.array, dim: int, max_period: float = 10000.0, time_factor: float = 1000.0
) -> mx.array:
    """Sinusoidal timestep embedding, cos-first (matching the reference)."""
    t = time_factor * t.astype(mx.float32)
    half = dim // 2
    freqs = mx.exp(-math.log(max_period) * mx.arange(0, half, dtype=mx.float32) / half)
    args = t[:, None] * freqs[None]
    emb = mx.concatenate([mx.cos(args), mx.sin(args)], axis=-1)
    if dim % 2:
        emb = mx.concatenate([emb, mx.zeros_like(emb[:, :1])], axis=-1)
    return emb


def attention(q: mx.array, k: mx.array, v: mx.array) -> mx.array:
    """Scaled dot-product attention returning (B, L, H*D)."""
    scale = q.shape[-1] ** -0.5
    x = mx.fast.scaled_dot_product_attention(q, k, v, scale=scale)
    b, h, ln, d = x.shape
    return x.transpose(0, 2, 1, 3).reshape(b, ln, h * d)


def _split_qkv(qkv: mx.array, num_heads: int) -> tuple:
    """Split a fused projection laid out as ``B L (K H D)`` into ``K x (B, H, L, D)``."""
    b, ln, _ = qkv.shape
    head_dim = qkv.shape[-1] // (3 * num_heads)
    t = qkv.reshape(b, ln, 3, num_heads, head_dim).transpose(2, 0, 3, 1, 4)
    return t[0], t[1], t[2]


class MLPEmbedder(nn.Module):
    def __init__(self, in_dim: int, hidden_dim: int):
        super().__init__()
        self.in_layer = nn.Linear(in_dim, hidden_dim, bias=True)
        self.out_layer = nn.Linear(hidden_dim, hidden_dim, bias=True)

    def __call__(self, x: mx.array) -> mx.array:
        return self.out_layer(nn.silu(self.in_layer(x)))


class RMSNorm(nn.Module):
    """RMS norm computed in fp32, then rescaled by a learned per-channel gain."""

    def __init__(self, dim: int):
        super().__init__()
        self.scale = mx.ones((dim,))

    def __call__(self, x: mx.array) -> mx.array:
        xf = x.astype(mx.float32)
        rrms = mx.rsqrt(mx.mean(xf * xf, axis=-1, keepdims=True) + 1e-6)
        return (xf * rrms).astype(x.dtype) * self.scale.astype(x.dtype)


class QKNorm(nn.Module):
    def __init__(self, dim: int):
        super().__init__()
        self.query_norm = RMSNorm(dim)
        self.key_norm = RMSNorm(dim)

    def __call__(self, q: mx.array, k: mx.array) -> tuple:
        return self.query_norm(q), self.key_norm(k)


class SelfAttention(nn.Module):
    def __init__(self, dim: int, num_heads: int = 8, qkv_bias: bool = False):
        super().__init__()
        self.num_heads = num_heads
        self.qkv = nn.Linear(dim, dim * 3, bias=qkv_bias)
        self.norm = QKNorm(dim // num_heads)
        self.proj = nn.Linear(dim, dim)

    def __call__(self, x: mx.array) -> mx.array:
        q, k, v = _split_qkv(self.qkv(x), self.num_heads)
        q, k = self.norm(q, k)
        return self.proj(attention(q, k, v))


class Modulation(nn.Module):
    """Produces (shift, scale, gate) triplets from the conditioning vector."""

    def __init__(self, dim: int, double: bool):
        super().__init__()
        self.is_double = double
        self.multiplier = 6 if double else 3
        self.lin = nn.Linear(dim, self.multiplier * dim, bias=True)

    def __call__(self, vec: mx.array) -> tuple:
        out = self.lin(nn.silu(vec))[:, None, :]
        chunks = mx.split(out, self.multiplier, axis=-1)
        first = chunks[0:3]
        second = chunks[3:6] if self.is_double else None
        return first, second


class DoubleStreamBlock(nn.Module):
    def __init__(self, hidden_size: int, num_heads: int, mlp_ratio: float, qkv_bias: bool = False):
        super().__init__()
        mlp_hidden_dim = int(hidden_size * mlp_ratio)
        self.num_heads = num_heads
        self.hidden_size = hidden_size

        self.img_mod = Modulation(hidden_size, double=True)
        self.img_norm1 = nn.LayerNorm(hidden_size, eps=1e-6, affine=False)
        self.img_attn = SelfAttention(hidden_size, num_heads, qkv_bias)
        self.img_norm2 = nn.LayerNorm(hidden_size, eps=1e-6, affine=False)
        self.img_mlp = [
            nn.Linear(hidden_size, mlp_hidden_dim, bias=True),
            nn.Linear(mlp_hidden_dim, hidden_size, bias=True),
        ]

        self.txt_mod = Modulation(hidden_size, double=True)
        self.txt_norm1 = nn.LayerNorm(hidden_size, eps=1e-6, affine=False)
        self.txt_attn = SelfAttention(hidden_size, num_heads, qkv_bias)
        self.txt_norm2 = nn.LayerNorm(hidden_size, eps=1e-6, affine=False)
        self.txt_mlp = [
            nn.Linear(hidden_size, mlp_hidden_dim, bias=True),
            nn.Linear(mlp_hidden_dim, hidden_size, bias=True),
        ]

    @staticmethod
    def _mlp(layers, x: mx.array) -> mx.array:
        return layers[1](nn.gelu_approx(layers[0](x)))

    def __call__(self, img: mx.array, txt: mx.array, vec: mx.array) -> tuple:
        (img_shift1, img_scale1, img_gate1), (img_shift2, img_scale2, img_gate2) = self.img_mod(vec)
        (txt_shift1, txt_scale1, txt_gate1), (txt_shift2, txt_scale2, txt_gate2) = self.txt_mod(vec)

        img_mod = (1 + img_scale1) * self.img_norm1(img) + img_shift1
        img_q, img_k, img_v = _split_qkv(self.img_attn.qkv(img_mod), self.num_heads)
        img_q, img_k = self.img_attn.norm(img_q, img_k)

        txt_mod = (1 + txt_scale1) * self.txt_norm1(txt) + txt_shift1
        txt_q, txt_k, txt_v = _split_qkv(self.txt_attn.qkv(txt_mod), self.num_heads)
        txt_q, txt_k = self.txt_attn.norm(txt_q, txt_k)

        q = mx.concatenate([txt_q, img_q], axis=2)
        k = mx.concatenate([txt_k, img_k], axis=2)
        v = mx.concatenate([txt_v, img_v], axis=2)

        attn = attention(q, k, v)
        txt_len = txt.shape[1]
        txt_attn, img_attn = attn[:, :txt_len], attn[:, txt_len:]

        img = img + img_gate1 * self.img_attn.proj(img_attn)
        img = img + img_gate2 * self._mlp(
            self.img_mlp, (1 + img_scale2) * self.img_norm2(img) + img_shift2
        )

        txt = txt + txt_gate1 * self.txt_attn.proj(txt_attn)
        txt = txt + txt_gate2 * self._mlp(
            self.txt_mlp, (1 + txt_scale2) * self.txt_norm2(txt) + txt_shift2
        )
        return img, txt


class SingleStreamBlock(nn.Module):
    """DiT block with parallel attention/MLP linear layers (arXiv:2302.05442)."""

    def __init__(self, hidden_size: int, num_heads: int, mlp_ratio: float = 4.0):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_heads = num_heads
        self.mlp_hidden_dim = int(hidden_size * mlp_ratio)
        self.linear1 = nn.Linear(hidden_size, hidden_size * 3 + self.mlp_hidden_dim)
        self.linear2 = nn.Linear(hidden_size + self.mlp_hidden_dim, hidden_size)
        self.norm = QKNorm(hidden_size // num_heads)
        self.pre_norm = nn.LayerNorm(hidden_size, eps=1e-6, affine=False)
        self.modulation = Modulation(hidden_size, double=False)

    def __call__(self, x: mx.array, vec: mx.array) -> mx.array:
        (shift, scale, gate), _ = self.modulation(vec)
        x_mod = (1 + scale) * self.pre_norm(x) + shift
        fused = self.linear1(x_mod)
        qkv = fused[..., : 3 * self.hidden_size]
        mlp = fused[..., 3 * self.hidden_size :]

        q, k, v = _split_qkv(qkv, self.num_heads)
        q, k = self.norm(q, k)
        attn = attention(q, k, v)

        output = self.linear2(mx.concatenate([attn, nn.gelu_approx(mlp)], axis=2))
        return x + gate * output


class LastLayer(nn.Module):
    def __init__(self, hidden_size: int, patch_size: int, out_channels: int):
        super().__init__()
        self.norm_final = nn.LayerNorm(hidden_size, eps=1e-6, affine=False)
        self.linear = nn.Linear(hidden_size, patch_size * patch_size * out_channels, bias=True)
        self.adaLN_modulation = nn.Linear(hidden_size, 2 * hidden_size, bias=True)

    def __call__(self, x: mx.array, vec: mx.array) -> mx.array:
        shift, scale = mx.split(self.adaLN_modulation(nn.silu(vec)), 2, axis=1)
        x = (1 + scale[:, None, :]) * self.norm_final(x) + shift[:, None, :]
        return self.linear(x)


class Hunyuan3DDiT(nn.Module):
    def __init__(
        self,
        in_channels: int = 64,
        context_in_dim: int = 1536,
        hidden_size: int = 1024,
        mlp_ratio: float = 4.0,
        num_heads: int = 16,
        depth: int = 16,
        depth_single_blocks: int = 32,
        axes_dim: Optional[List[int]] = None,
        theta: int = 10_000,
        qkv_bias: bool = True,
        time_factor: float = 1000.0,
        guidance_embed: bool = False,
        **kwargs,
    ):
        super().__init__()
        if hidden_size % num_heads != 0:
            raise ValueError(f"hidden_size {hidden_size} must be divisible by num_heads {num_heads}")

        self.in_channels = in_channels
        self.out_channels = in_channels
        self.hidden_size = hidden_size
        self.num_heads = num_heads
        self.time_factor = time_factor
        self.guidance_embed = guidance_embed

        self.latent_in = nn.Linear(in_channels, hidden_size, bias=True)
        self.time_in = MLPEmbedder(in_dim=256, hidden_dim=hidden_size)
        self.cond_in = nn.Linear(context_in_dim, hidden_size)
        if guidance_embed:
            self.guidance_in = MLPEmbedder(in_dim=256, hidden_dim=hidden_size)

        self.double_blocks = [
            DoubleStreamBlock(hidden_size, num_heads, mlp_ratio=mlp_ratio, qkv_bias=qkv_bias)
            for _ in range(depth)
        ]
        self.single_blocks = [
            SingleStreamBlock(hidden_size, num_heads, mlp_ratio=mlp_ratio)
            for _ in range(depth_single_blocks)
        ]
        self.final_layer = LastLayer(hidden_size, 1, self.out_channels)

    def __call__(
        self,
        x: mx.array,
        t: mx.array,
        contexts: dict,
        guidance: Optional[mx.array] = None,
    ) -> mx.array:
        latent = self.latent_in(x)
        dtype = latent.dtype

        # NOTE: upstream calls `timestep_embedding(t, 256, self.time_factor)`, which binds
        # time_factor (1000) to the *max_period* positional while time_factor keeps its
        # 1000.0 default. The released weights were trained against that behaviour, so the
        # quirk is reproduced deliberately -- using max_period=10000 breaks the model.
        vec = self.time_in(
            timestep_embedding(t, 256, max_period=self.time_factor, time_factor=1000.0)
            .astype(dtype)
        )
        if self.guidance_embed:
            if guidance is None:
                raise ValueError("Guidance-distilled model requires a `guidance` value.")
            vec = vec + self.guidance_in(
                timestep_embedding(
                    guidance, 256, max_period=self.time_factor, time_factor=1000.0
                ).astype(dtype)
            )

        cond = self.cond_in(contexts["main"].astype(dtype))

        for block in self.double_blocks:
            latent, cond = block(latent, cond, vec)

        latent = mx.concatenate([cond, latent], axis=1)
        for block in self.single_blocks:
            latent = block(latent, vec)

        latent = latent[:, cond.shape[1] :, ...]
        return self.final_layer(latent, vec)
