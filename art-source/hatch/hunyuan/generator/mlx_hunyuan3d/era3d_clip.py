"""MLX CLIP vision encoder used by Era3D image conditioning."""

from __future__ import annotations

from typing import Any

import mlx.core as mx
import mlx.nn as nn


def _quick_gelu(x: mx.array) -> mx.array:
    return x * mx.sigmoid(1.702 * x)


def _layer_norm_fp32(layer: nn.LayerNorm, hidden: mx.array) -> mx.array:
    dtype = hidden.dtype
    hidden = hidden.astype(mx.float32)
    mean = mx.mean(hidden, axis=-1, keepdims=True)
    variance = mx.mean((hidden - mean) ** 2, axis=-1, keepdims=True)
    hidden = (hidden - mean) * mx.rsqrt(variance + layer.eps)
    hidden = hidden * layer.weight.astype(mx.float32) + layer.bias.astype(mx.float32)
    return hidden.astype(dtype)


class CLIPVisionEmbeddings(nn.Module):
    def __init__(self, config: dict[str, Any]):
        super().__init__()
        hidden = config["hidden_size"]
        image_size = config["image_size"]
        patch_size = config["patch_size"]
        patches = (image_size // patch_size) ** 2
        self.class_embedding = mx.zeros((hidden,))
        self.patch_embedding = nn.Conv2d(
            config["num_channels"], hidden, patch_size, stride=patch_size, bias=False
        )
        self.position_embedding = nn.Embedding(patches + 1, hidden)

    def __call__(self, pixels: mx.array) -> mx.array:
        patches = self.patch_embedding(pixels)
        patches = patches.reshape(patches.shape[0], -1, patches.shape[-1])
        class_embedding = mx.broadcast_to(
            self.class_embedding[None, None], (pixels.shape[0], 1, self.class_embedding.shape[0])
        )
        hidden = mx.concatenate([class_embedding, patches], axis=1)
        position_ids = mx.arange(self.position_embedding.weight.shape[0])
        return hidden + self.position_embedding(position_ids)[None]


class CLIPAttention(nn.Module):
    def __init__(self, config: dict[str, Any]):
        super().__init__()
        hidden = config["hidden_size"]
        self.num_heads = config["num_attention_heads"]
        self.head_dim = hidden // self.num_heads
        self.scale = self.head_dim ** -0.5
        self.k_proj = nn.Linear(hidden, hidden)
        self.v_proj = nn.Linear(hidden, hidden)
        self.q_proj = nn.Linear(hidden, hidden)
        self.out_proj = nn.Linear(hidden, hidden)

    def __call__(self, hidden: mx.array) -> mx.array:
        batch, length, width = hidden.shape
        shape = (batch, length, self.num_heads, self.head_dim)
        query = self.q_proj(hidden).reshape(shape).transpose(0, 2, 1, 3)
        key = self.k_proj(hidden).reshape(shape).transpose(0, 2, 1, 3)
        value = self.v_proj(hidden).reshape(shape).transpose(0, 2, 1, 3)
        attended = mx.fast.scaled_dot_product_attention(query, key, value, scale=self.scale)
        attended = attended.transpose(0, 2, 1, 3).reshape(batch, length, width)
        return self.out_proj(attended)


class CLIPMLP(nn.Module):
    def __init__(self, config: dict[str, Any]):
        super().__init__()
        self.fc1 = nn.Linear(config["hidden_size"], config["intermediate_size"])
        self.fc2 = nn.Linear(config["intermediate_size"], config["hidden_size"])
        self.hidden_act = config["hidden_act"]
        if self.hidden_act not in {"gelu", "quick_gelu"}:
            raise ValueError(f"unsupported Era3D CLIP activation {self.hidden_act!r}")

    def __call__(self, hidden: mx.array) -> mx.array:
        hidden = self.fc1(hidden)
        hidden = nn.gelu(hidden) if self.hidden_act == "gelu" else _quick_gelu(hidden)
        return self.fc2(hidden)


class CLIPEncoderLayer(nn.Module):
    def __init__(self, config: dict[str, Any]):
        super().__init__()
        hidden = config["hidden_size"]
        eps = config["layer_norm_eps"]
        self.self_attn = CLIPAttention(config)
        self.layer_norm1 = nn.LayerNorm(hidden, eps=eps)
        self.mlp = CLIPMLP(config)
        self.layer_norm2 = nn.LayerNorm(hidden, eps=eps)

    def __call__(self, hidden: mx.array) -> mx.array:
        hidden = hidden + self.self_attn(self.layer_norm1(hidden))
        return hidden + self.mlp(self.layer_norm2(hidden))


class CLIPEncoder(nn.Module):
    def __init__(self, config: dict[str, Any]):
        super().__init__()
        self.layers = [CLIPEncoderLayer(config) for _ in range(config["num_hidden_layers"])]

    def __call__(self, hidden: mx.array) -> mx.array:
        for layer in self.layers:
            hidden = layer(hidden)
            mx.eval(hidden)
        return hidden


class CLIPVisionTransformer(nn.Module):
    def __init__(self, config: dict[str, Any]):
        super().__init__()
        hidden = config["hidden_size"]
        eps = config["layer_norm_eps"]
        self.embeddings = CLIPVisionEmbeddings(config)
        # Hugging Face's checkpoint intentionally spells this path `pre_layrnorm`.
        self.pre_layrnorm = nn.LayerNorm(hidden, eps=eps)
        self.encoder = CLIPEncoder(config)
        self.post_layernorm = nn.LayerNorm(hidden, eps=eps)

    def __call__(self, pixels: mx.array) -> mx.array:
        hidden = _layer_norm_fp32(self.pre_layrnorm, self.embeddings(pixels))
        hidden = self.encoder(hidden)
        return _layer_norm_fp32(self.post_layernorm, hidden[:, 0])


class EraCLIPVisionModelWithProjection(nn.Module):
    """Checkpoint-compatible CLIP-ViT-H/14 projection model.

    Input is NHWC because MLX convolutions are channels-last. The returned image embeddings
    are unnormalized, matching `CLIPVisionModelWithProjection(...).image_embeds`.
    """

    def __init__(self, config: dict[str, Any]):
        super().__init__()
        self.vision_model = CLIPVisionTransformer(config)
        self.visual_projection = nn.Linear(
            config["hidden_size"], config["projection_dim"], bias=False
        )

    def __call__(self, pixels: mx.array) -> mx.array:
        return self.visual_projection(self.vision_model(pixels))
