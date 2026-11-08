"""Perspective six-view Era3D UNet in MLX.

The decoder camera embedding is inferred after the mid block, so down/mid blocks use the
ordinary time-plus-image-class embedding while every up block uses time-plus-image-class
plus the predicted elevation/focal embedding.
"""

from __future__ import annotations

from typing import Any

import mlx.core as mx
import mlx.nn as nn

from mlx_hunyuan3d.era3d import EraBasicMVTransformerBlock
from mlx_hunyuan3d.paint_unet import (
    DownBlock2D,
    Downsample2D,
    ResnetBlock2D,
    TimestepEmbedding,
    UpBlock2D,
    Upsample2D,
    _silu,
    timestep_embedding,
)


class EraTransformer2DModel(nn.Module):
    def __init__(self, channels: int, heads: int, context_dim: int, num_views: int = 6):
        super().__init__()
        dim_head = channels // heads
        self.norm = nn.GroupNorm(32, channels, eps=1e-6, pytorch_compatible=True)
        self.proj_in = nn.Linear(channels, channels)
        self.transformer_blocks = [
            EraBasicMVTransformerBlock(channels, heads, dim_head, context_dim, num_views)
        ]
        self.proj_out = nn.Linear(channels, channels)

    def __call__(self, hidden: mx.array, context: mx.array) -> mx.array:
        batch, height, width, channels = hidden.shape
        residual = hidden
        hidden = self.norm(hidden).reshape(batch, height * width, channels)
        hidden = self.proj_in(hidden)
        for block in self.transformer_blocks:
            hidden = block(hidden, context)
        hidden = self.proj_out(hidden).reshape(batch, height, width, channels)
        return hidden + residual


class EraCrossAttnDownBlock2D(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, time_dim: int, layers: int,
                 heads: int, context_dim: int, add_downsample: bool, num_views: int):
        super().__init__()
        self.resnets = []
        self.attentions = []
        for index in range(layers):
            self.resnets.append(ResnetBlock2D(
                in_channels if index == 0 else out_channels, out_channels, time_dim
            ))
            self.attentions.append(EraTransformer2DModel(
                out_channels, heads, context_dim, num_views
            ))
        self.downsamplers = [Downsample2D(out_channels)] if add_downsample else []

    def __call__(self, hidden: mx.array, temb: mx.array,
                 context: mx.array) -> tuple[mx.array, list[mx.array]]:
        states = []
        for resnet, attention in zip(self.resnets, self.attentions):
            hidden = attention(resnet(hidden, temb), context)
            states.append(hidden)
        for downsampler in self.downsamplers:
            hidden = downsampler(hidden)
            states.append(hidden)
        return hidden, states


class EraCrossAttnUpBlock2D(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, prev_channels: int,
                 time_dim: int, layers: int, heads: int, context_dim: int,
                 add_upsample: bool, num_views: int):
        super().__init__()
        self.resnets = []
        self.attentions = []
        for index in range(layers):
            skip_channels = in_channels if index == layers - 1 else out_channels
            previous_channels = prev_channels if index == 0 else out_channels
            self.resnets.append(ResnetBlock2D(
                previous_channels + skip_channels, out_channels, time_dim
            ))
            self.attentions.append(EraTransformer2DModel(
                out_channels, heads, context_dim, num_views
            ))
        self.upsamplers = [Upsample2D(out_channels)] if add_upsample else []

    def __call__(self, hidden: mx.array, states: list[mx.array], temb: mx.array,
                 context: mx.array) -> mx.array:
        for resnet, attention in zip(self.resnets, self.attentions):
            hidden = mx.concatenate([hidden, states.pop()], axis=-1)
            hidden = attention(resnet(hidden, temb), context)
        for upsampler in self.upsamplers:
            hidden = upsampler(hidden)
        return hidden


class EraUNetMidBlock2DCrossAttn(nn.Module):
    def __init__(self, channels: int, time_dim: int, heads: int,
                 context_dim: int, num_views: int):
        super().__init__()
        self.resnets = [
            ResnetBlock2D(channels, channels, time_dim),
            ResnetBlock2D(channels, channels, time_dim),
        ]
        self.attentions = [EraTransformer2DModel(channels, heads, context_dim, num_views)]

    def __call__(self, hidden: mx.array, temb: mx.array, context: mx.array) -> mx.array:
        hidden = self.resnets[0](hidden, temb)
        hidden = self.attentions[0](hidden, context)
        return self.resnets[1](hidden, temb)


class ResidualBlock(nn.Module):
    def __init__(self, dim: int):
        super().__init__()
        self.linear1 = nn.Linear(dim, dim)
        self.linear2 = nn.Linear(dim, dim)

    def __call__(self, hidden: mx.array) -> mx.array:
        return _silu(self.linear2(_silu(self.linear1(hidden))) + hidden)


class ResidualLiner(nn.Module):
    """Checkpoint-compatible spelling and tree for Era3D's pose regressors."""

    def __init__(self, in_features: int, out_features: int, dim: int,
                 num_blocks: int):
        super().__init__()
        self.linear_in = [nn.Linear(in_features, dim)]
        self.blocks = [ResidualBlock(dim) for _ in range(num_blocks)]
        self.linear_out = nn.Linear(dim, out_features)

    def __call__(self, hidden: mx.array) -> mx.array:
        hidden = _silu(self.linear_in[0](hidden))
        for block in self.blocks:
            hidden = block(hidden)
        return self.linear_out(hidden)


class Era3DUNet(nn.Module):
    def __init__(self, config: dict[str, Any], *, regressor_dim: int = 1280):
        super().__init__()
        channels = tuple(config["block_out_channels"])
        heads = tuple(config["attention_head_dim"])
        layers = int(config["layers_per_block"])
        context_dim = int(config["cross_attention_dim"])
        num_views = int(config["num_views"])
        time_dim = channels[0] * 4
        if config["selfattn_block"] != "self_rowwise" or num_views != 6:
            raise ValueError("Era3DUNet only implements the released six-view self_rowwise model")
        if config["use_dino"] or config["addition_downsample"]:
            raise ValueError("released Era3D checkpoint must not enable DINO/additional-downsample paths")

        self.num_views = num_views
        self.block_out_channels = channels
        self.time_embedding = TimestepEmbedding(channels[0], time_dim)
        self.class_embedding = TimestepEmbedding(
            int(config["projection_class_embeddings_input_dim"]), time_dim
        )
        self.conv_in = nn.Conv2d(config["in_channels"], channels[0], 3, padding=1)

        self.down_blocks = []
        previous = channels[0]
        for index, out_channels in enumerate(channels):
            last = index == len(channels) - 1
            if last:
                block = DownBlock2D(previous, out_channels, time_dim, layers, False)
            else:
                block = EraCrossAttnDownBlock2D(
                    previous, out_channels, time_dim, layers, heads[index], context_dim,
                    True, num_views,
                )
            self.down_blocks.append(block)
            previous = out_channels

        self.mid_block = EraUNetMidBlock2DCrossAttn(
            previous, time_dim, heads[-1], context_dim, num_views
        )
        pose_input = channels[-1] * 2
        regress_blocks = int(config["num_regress_blocks"])
        self.elevation_regressor = ResidualLiner(pose_input, 1, regressor_dim, regress_blocks)
        self.focal_regressor = ResidualLiner(pose_input, 1, regressor_dim, regress_blocks)
        self.camera_embedding = TimestepEmbedding(
            int(config["projection_camera_embeddings_input_dim"]), time_dim
        )

        self.up_blocks = []
        reversed_channels = tuple(reversed(channels))
        reversed_heads = tuple(reversed(heads))
        previous = reversed_channels[0]
        for index, out_channels in enumerate(reversed_channels):
            skip_channels = reversed_channels[min(index + 1, len(reversed_channels) - 1)]
            if index == 0:
                block = UpBlock2D(
                    skip_channels, out_channels, previous, time_dim, layers + 1, True
                )
            else:
                block = EraCrossAttnUpBlock2D(
                    skip_channels, out_channels, previous, time_dim, layers + 1,
                    reversed_heads[index], context_dim,
                    index < len(reversed_channels) - 1, num_views,
                )
            self.up_blocks.append(block)
            previous = out_channels

        self.conv_norm_out = nn.GroupNorm(
            32, channels[0], eps=config["norm_eps"], pytorch_compatible=True
        )
        self.conv_out = nn.Conv2d(channels[0], config["out_channels"], 3, padding=1)

    def _time_and_class_embedding(self, sample: mx.array, timestep,
                                  class_labels: mx.array) -> mx.array:
        if class_labels is None:
            raise ValueError("Era3D UNet requires 2048-dimensional image class labels")
        if not isinstance(timestep, mx.array):
            timestep = mx.array([timestep])
        if timestep.size == 1:
            timestep = mx.broadcast_to(timestep, (sample.shape[0],))
        if timestep.shape != (sample.shape[0],):
            raise ValueError(f"inconsistent Era3D timestep batch {timestep.shape}")
        weight_dtype = self.conv_in.weight.dtype
        sinusoid = timestep_embedding(timestep, self.block_out_channels[0])
        time = self.time_embedding(sinusoid.astype(weight_dtype))
        return time + self.class_embedding(class_labels).astype(weight_dtype)

    def _camera_condition(self, hidden: mx.array) -> tuple[mx.array, mx.array]:
        pooled = mx.mean(hidden, axis=(1, 2))
        if pooled.shape[0] % 2:
            raise ValueError(f"Era3D camera regression requires paired domains, got {pooled.shape}")
        normal, color = mx.split(pooled, 2, axis=0)
        paired = mx.concatenate([normal, color], axis=-1)
        if paired.shape[0] % self.num_views:
            raise ValueError(f"Era3D camera batch is not six-view grouped: {paired.shape}")

        elevation = self.elevation_regressor(paired)
        focal = self.focal_regressor(paired)
        groups = paired.shape[0] // self.num_views
        elevation = mx.mean(elevation.reshape(groups, self.num_views, 1), axis=1)
        focal = mx.mean(focal.reshape(groups, self.num_views, 1), axis=1)
        pose = mx.concatenate([elevation, focal], axis=-1)
        pose_features = mx.concatenate([mx.sin(pose), mx.cos(pose)], axis=-1)
        camera = self.camera_embedding(pose_features)
        camera = mx.repeat(camera, self.num_views, axis=0)
        camera = mx.concatenate([camera, camera], axis=0)
        return camera, pose

    def __call__(self, sample: mx.array, timestep, encoder_hidden_states: mx.array,
                 class_labels: mx.array) -> tuple[mx.array, mx.array]:
        if sample.shape[0] != 24 or sample.shape[-1] != 8:
            raise ValueError(f"Era3D UNet requires [24,H,W,8], got {sample.shape}")
        if encoder_hidden_states.shape != (24, 77, 1024):
            raise ValueError(
                f"Era3D UNet requires fixed context [24,77,1024], got {encoder_hidden_states.shape}"
            )
        if class_labels.shape != (24, 2048):
            raise ValueError(f"Era3D UNet requires class labels [24,2048], got {class_labels.shape}")

        embedding = self._time_and_class_embedding(sample, timestep, class_labels)
        hidden = self.conv_in(sample)
        states = [hidden]
        for block in self.down_blocks:
            if isinstance(block, DownBlock2D):
                hidden, new_states = block(hidden, embedding)
            else:
                hidden, new_states = block(hidden, embedding, encoder_hidden_states)
            states.extend(new_states)
            mx.eval(hidden, *new_states)

        hidden = self.mid_block(hidden, embedding, encoder_hidden_states)
        mx.eval(hidden)
        camera, pose = self._camera_condition(hidden)
        decoder_embedding = embedding + camera.astype(embedding.dtype)

        for block in self.up_blocks:
            if isinstance(block, UpBlock2D):
                hidden = block(hidden, states, decoder_embedding)
            else:
                hidden = block(
                    hidden, states, decoder_embedding, encoder_hidden_states
                )
            mx.eval(hidden)
        output = self.conv_out(_silu(self.conv_norm_out(hidden)))
        return output, pose
