"""MLX port of the DINOv2 (giant) multi-view image conditioner used by Hunyuan3D-2mv.

Mirrors ``transformers.Dinov2Model`` (SwiGLU FFN + LayerScale variant) plus the
``DinoImageEncoderMV`` wrapper from ``hy3dgen.shapegen.models.conditioner``.
"""

from __future__ import annotations


import mlx.core as mx
import mlx.nn as nn
import numpy as np

# ImageNet statistics used by the reference DINOv2 transform.
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


class Dinov2PatchEmbeddings(nn.Module):
    def __init__(self, hidden_size: int, patch_size: int, num_channels: int):
        super().__init__()
        self.projection = nn.Conv2d(
            num_channels, hidden_size, kernel_size=patch_size, stride=patch_size
        )

    def __call__(self, pixel_values: mx.array) -> mx.array:
        """pixel_values: (B, H, W, C) in MLX's channels-last convention."""
        x = self.projection(pixel_values)
        b, h, w, c = x.shape
        return x.reshape(b, h * w, c)


class Dinov2Embeddings(nn.Module):
    def __init__(self, hidden_size: int, patch_size: int, num_channels: int, num_positions: int):
        super().__init__()
        self.cls_token = mx.zeros((1, 1, hidden_size))
        self.mask_token = mx.zeros((1, hidden_size))
        self.position_embeddings = mx.zeros((1, num_positions, hidden_size))
        self.patch_embeddings = Dinov2PatchEmbeddings(hidden_size, patch_size, num_channels)

    def __call__(self, pixel_values: mx.array) -> mx.array:
        embeddings = self.patch_embeddings(pixel_values)
        b = embeddings.shape[0]
        cls = mx.broadcast_to(self.cls_token, (b, 1, self.cls_token.shape[-1]))
        embeddings = mx.concatenate([cls.astype(embeddings.dtype), embeddings], axis=1)
        if embeddings.shape[1] != self.position_embeddings.shape[1]:
            raise ValueError(
                f"Expected {self.position_embeddings.shape[1]} tokens for the stored positional "
                f"embeddings but got {embeddings.shape[1]}; positional interpolation is not "
                "supported (inputs must be 518x518)."
            )
        return embeddings + self.position_embeddings.astype(embeddings.dtype)


class Dinov2SelfAttention(nn.Module):
    def __init__(self, hidden_size: int, num_heads: int, qkv_bias: bool):
        super().__init__()
        if hidden_size % num_heads != 0:
            raise ValueError(f"hidden_size {hidden_size} not divisible by num_heads {num_heads}")
        self.num_heads = num_heads
        self.head_dim = hidden_size // num_heads
        self.scale = self.head_dim**-0.5
        self.query = nn.Linear(hidden_size, hidden_size, bias=qkv_bias)
        self.key = nn.Linear(hidden_size, hidden_size, bias=qkv_bias)
        self.value = nn.Linear(hidden_size, hidden_size, bias=qkv_bias)

    def __call__(self, x: mx.array) -> mx.array:
        b, n, _ = x.shape
        shape = (b, n, self.num_heads, self.head_dim)
        q = self.query(x).reshape(shape).transpose(0, 2, 1, 3)
        k = self.key(x).reshape(shape).transpose(0, 2, 1, 3)
        v = self.value(x).reshape(shape).transpose(0, 2, 1, 3)
        out = mx.fast.scaled_dot_product_attention(q, k, v, scale=self.scale)
        return out.transpose(0, 2, 1, 3).reshape(b, n, -1)


class Dinov2SelfOutput(nn.Module):
    def __init__(self, hidden_size: int):
        super().__init__()
        self.dense = nn.Linear(hidden_size, hidden_size)

    def __call__(self, x: mx.array) -> mx.array:
        return self.dense(x)


class Dinov2Attention(nn.Module):
    def __init__(self, hidden_size: int, num_heads: int, qkv_bias: bool):
        super().__init__()
        self.attention = Dinov2SelfAttention(hidden_size, num_heads, qkv_bias)
        self.output = Dinov2SelfOutput(hidden_size)

    def __call__(self, x: mx.array) -> mx.array:
        return self.output(self.attention(x))


class Dinov2LayerScale(nn.Module):
    def __init__(self, hidden_size: int):
        super().__init__()
        self.lambda1 = mx.ones((hidden_size,))

    def __call__(self, x: mx.array) -> mx.array:
        return x * self.lambda1.astype(x.dtype)


class Dinov2SwiGLUFFN(nn.Module):
    """SwiGLU feed-forward as used by DINOv2-giant."""

    def __init__(self, hidden_size: int, mlp_ratio: int):
        super().__init__()
        hidden_features = int(hidden_size * mlp_ratio)
        hidden_features = int(hidden_features * 2 / 3)
        hidden_features = (hidden_features + 7) // 8 * 8
        self.weights_in = nn.Linear(hidden_size, 2 * hidden_features)
        self.weights_out = nn.Linear(hidden_features, hidden_size)

    def __call__(self, x: mx.array) -> mx.array:
        h = self.weights_in(x)
        x1, x2 = mx.split(h, 2, axis=-1)
        return self.weights_out(nn.silu(x1) * x2)


class Dinov2Layer(nn.Module):
    def __init__(self, hidden_size: int, num_heads: int, mlp_ratio: int, qkv_bias: bool, eps: float):
        super().__init__()
        self.norm1 = nn.LayerNorm(hidden_size, eps=eps)
        self.attention = Dinov2Attention(hidden_size, num_heads, qkv_bias)
        self.layer_scale1 = Dinov2LayerScale(hidden_size)
        self.norm2 = nn.LayerNorm(hidden_size, eps=eps)
        self.mlp = Dinov2SwiGLUFFN(hidden_size, mlp_ratio)
        self.layer_scale2 = Dinov2LayerScale(hidden_size)

    def __call__(self, x: mx.array) -> mx.array:
        x = x + self.layer_scale1(self.attention(self.norm1(x)))
        x = x + self.layer_scale2(self.mlp(self.norm2(x)))
        return x


class Dinov2Encoder(nn.Module):
    def __init__(self, num_layers: int, **layer_kwargs):
        super().__init__()
        self.layer = [Dinov2Layer(**layer_kwargs) for _ in range(num_layers)]

    def __call__(self, x: mx.array) -> mx.array:
        for layer in self.layer:
            x = layer(x)
        return x


class Dinov2Model(nn.Module):
    def __init__(
        self,
        hidden_size: int = 1536,
        num_hidden_layers: int = 40,
        num_attention_heads: int = 24,
        mlp_ratio: int = 4,
        patch_size: int = 14,
        num_channels: int = 3,
        image_size: int = 518,
        layer_norm_eps: float = 1e-6,
        qkv_bias: bool = True,
    ):
        super().__init__()
        self.hidden_size = hidden_size
        self.patch_size = patch_size
        self.image_size = image_size
        num_positions = (image_size // patch_size) ** 2 + 1
        self.embeddings = Dinov2Embeddings(hidden_size, patch_size, num_channels, num_positions)
        self.encoder = Dinov2Encoder(
            num_hidden_layers,
            hidden_size=hidden_size,
            num_heads=num_attention_heads,
            mlp_ratio=mlp_ratio,
            qkv_bias=qkv_bias,
            eps=layer_norm_eps,
        )
        self.layernorm = nn.LayerNorm(hidden_size, eps=layer_norm_eps)

    def __call__(self, pixel_values: mx.array) -> mx.array:
        x = self.embeddings(pixel_values)
        x = self.encoder(x)
        return self.layernorm(x)


def get_1d_sincos_pos_embed_from_grid(embed_dim: int, pos: np.ndarray) -> np.ndarray:
    """1D sin/cos positional embedding (identical to the reference implementation)."""
    if embed_dim % 2 != 0:
        raise ValueError("embed_dim must be even")
    omega = np.arange(embed_dim // 2, dtype=np.float64)
    omega /= embed_dim / 2.0
    omega = 1.0 / 10000**omega
    pos = pos.reshape(-1)
    out = np.einsum("m,d->md", pos, omega)
    return np.concatenate([np.sin(out), np.cos(out)], axis=1)


class DinoImageEncoderMV(nn.Module):
    """Multi-view DINOv2 conditioner: per-view features plus a learned-free view embedding."""

    def __init__(self, image_size: int = 518, view_num: int = 4, **model_kwargs):
        super().__init__()
        self.model = Dinov2Model(image_size=image_size, **model_kwargs)
        self.view_num = view_num
        self.image_size = image_size
        self.num_patches = (image_size // self.model.patch_size) ** 2 + 1
        view_embed = get_1d_sincos_pos_embed_from_grid(
            self.model.hidden_size, np.arange(view_num, dtype=np.float32)
        ).astype(np.float32)
        # (1, view_num, num_patches, hidden) -- underscore keeps it out of the parameter tree.
        self._view_embed = mx.array(
            np.tile(view_embed[:, None, :], (1, self.num_patches, 1))[None]
        )

    def __call__(self, image: mx.array, view_idxs=None, value_range=(-1, 1)) -> mx.array:
        """image: (B, V, H, W, C) already resized to ``image_size`` and in ``value_range``."""
        if value_range is not None:
            low, high = value_range
            image = (image - low) / (high - low)

        mean = mx.array(IMAGENET_MEAN, dtype=image.dtype)
        std = mx.array(IMAGENET_STD, dtype=image.dtype)
        image = (image - mean) / std

        bs, num_views = image.shape[0], image.shape[1]
        flat = image.reshape(bs * num_views, *image.shape[2:])
        hidden = self.model(flat)
        hidden = hidden.reshape(bs, num_views, hidden.shape[-2], hidden.shape[-1])

        if view_idxs is not None:
            if len(view_idxs) != bs:
                raise ValueError("view_idxs must contain one index list per batch element")
            view_embedding = mx.concatenate(
                [self._view_embed[:, [int(i) for i in idx], ...] for idx in view_idxs], axis=0
            )
        else:
            view_embedding = self._view_embed[:, :num_views, ...]

        hidden = hidden + view_embedding.astype(hidden.dtype)
        return hidden.reshape(bs, num_views * hidden.shape[-2], hidden.shape[-1])

    def unconditional_embedding(self, batch_size: int, view_idxs=None, dtype=mx.float32) -> mx.array:
        num_views = len(view_idxs[0]) if view_idxs is not None else self.view_num
        return mx.zeros(
            (batch_size, self.num_patches * num_views, self.model.hidden_size), dtype=dtype
        )


class SingleImageEncoder(nn.Module):
    """Wrapper matching the checkpoint layout ``conditioner.main_image_encoder.*``."""

    def __init__(self, **kwargs):
        super().__init__()
        self.main_image_encoder = DinoImageEncoderMV(**kwargs)

    def __call__(self, image: mx.array, **kwargs) -> dict:
        return {"main": self.main_image_encoder(image, **kwargs)}

    def unconditional_embedding(self, batch_size: int, **kwargs) -> dict:
        return {"main": self.main_image_encoder.unconditional_embedding(batch_size, **kwargs)}
