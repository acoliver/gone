"""MLX port of the Stable Diffusion AutoencoderKL used by Hunyuan3D-Paint.

The paint model is SD 2.1 based, so its VAE is the standard diffusers AutoencoderKL:
block_out_channels (128, 256, 512, 512), 2 layers per block, 4 latent channels.

Two conventions differ from PyTorch and account for most of the porting risk:

  * MLX convolutions are NHWC and store weights as (out, kH, kW, in), where PyTorch is
    NCHW with (out, in, kH, kW). Weights are transposed at load time and activations are
    kept in NHWC throughout, so no per-layer shuffling is needed.
  * nn.GroupNorm must be constructed with pytorch_compatible=True. MLX's default groups
    the channel axis differently from PyTorch, which silently produces plausible-looking
    but wrong output rather than an error.

The encoder's downsamplers also use asymmetric padding - PyTorch pads (0,1,0,1) before a
stride-2 convolution rather than padding symmetrically - which is reproduced here.
"""

from __future__ import annotations

import mlx.core as mx
import mlx.nn as nn

SCALING_FACTOR = 0.18215


def _silu(x: mx.array) -> mx.array:
    return x * mx.sigmoid(x)


class ResnetBlock2D(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, groups: int = 32):
        super().__init__()
        self.norm1 = nn.GroupNorm(groups, in_channels, eps=1e-6, pytorch_compatible=True)
        self.conv1 = nn.Conv2d(in_channels, out_channels, 3, padding=1)
        self.norm2 = nn.GroupNorm(groups, out_channels, eps=1e-6, pytorch_compatible=True)
        self.conv2 = nn.Conv2d(out_channels, out_channels, 3, padding=1)
        self.conv_shortcut = (
            nn.Conv2d(in_channels, out_channels, 1) if in_channels != out_channels else None
        )

    def __call__(self, x: mx.array) -> mx.array:
        residual = x
        h = self.conv1(_silu(self.norm1(x)))
        h = self.conv2(_silu(self.norm2(h)))
        if self.conv_shortcut is not None:
            residual = self.conv_shortcut(residual)
        return h + residual


class VAEAttention(nn.Module):
    """Single-head spatial self-attention used in the VAE mid block."""

    def __init__(self, channels: int, groups: int = 32):
        super().__init__()
        self.group_norm = nn.GroupNorm(groups, channels, eps=1e-6, pytorch_compatible=True)
        self.to_q = nn.Linear(channels, channels)
        self.to_k = nn.Linear(channels, channels)
        self.to_v = nn.Linear(channels, channels)
        self.to_out = [nn.Linear(channels, channels)]
        self.channels = channels

    def __call__(self, x: mx.array) -> mx.array:
        batch, height, width, channels = x.shape
        h = self.group_norm(x).reshape(batch, height * width, channels)
        q, k, v = self.to_q(h), self.to_k(h), self.to_v(h)
        scale = 1.0 / (channels ** 0.5)
        weights = mx.softmax((q * scale) @ k.transpose(0, 2, 1), axis=-1)
        h = self.to_out[0](weights @ v)
        return x + h.reshape(batch, height, width, channels)


class Downsample2D(nn.Module):
    def __init__(self, channels: int):
        super().__init__()
        self.conv = nn.Conv2d(channels, channels, 3, stride=2, padding=0)

    def __call__(self, x: mx.array) -> mx.array:
        # PyTorch pads (left, right, top, bottom) = (0, 1, 0, 1) before the strided conv.
        x = mx.pad(x, [(0, 0), (0, 1), (0, 1), (0, 0)])
        return self.conv(x)


class Upsample2D(nn.Module):
    def __init__(self, channels: int):
        super().__init__()
        self.conv = nn.Conv2d(channels, channels, 3, padding=1)

    def __call__(self, x: mx.array) -> mx.array:
        batch, height, width, channels = x.shape
        x = mx.broadcast_to(x[:, :, None, :, None, :], (batch, height, 2, width, 2, channels))
        return self.conv(x.reshape(batch, height * 2, width * 2, channels))


class DownEncoderBlock2D(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, layers: int, add_downsample: bool):
        super().__init__()
        self.resnets = [
            ResnetBlock2D(in_channels if i == 0 else out_channels, out_channels)
            for i in range(layers)
        ]
        self.downsamplers = [Downsample2D(out_channels)] if add_downsample else []

    def __call__(self, x: mx.array) -> mx.array:
        for resnet in self.resnets:
            x = resnet(x)
        for down in self.downsamplers:
            x = down(x)
        return x


class UpDecoderBlock2D(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, layers: int, add_upsample: bool):
        super().__init__()
        self.resnets = [
            ResnetBlock2D(in_channels if i == 0 else out_channels, out_channels)
            for i in range(layers)
        ]
        self.upsamplers = [Upsample2D(out_channels)] if add_upsample else []

    def __call__(self, x: mx.array) -> mx.array:
        for resnet in self.resnets:
            x = resnet(x)
        for up in self.upsamplers:
            x = up(x)
        return x


class UNetMidBlock2D(nn.Module):
    def __init__(self, channels: int):
        super().__init__()
        self.resnets = [ResnetBlock2D(channels, channels), ResnetBlock2D(channels, channels)]
        self.attentions = [VAEAttention(channels)]

    def __call__(self, x: mx.array) -> mx.array:
        x = self.resnets[0](x)
        x = self.attentions[0](x)
        return self.resnets[1](x)


class Encoder(nn.Module):
    def __init__(self, in_channels: int, latent_channels: int,
                 block_out_channels: tuple[int, ...], layers_per_block: int):
        super().__init__()
        self.conv_in = nn.Conv2d(in_channels, block_out_channels[0], 3, padding=1)
        blocks, channels = [], block_out_channels[0]
        for i, out_channels in enumerate(block_out_channels):
            blocks.append(DownEncoderBlock2D(
                channels, out_channels, layers_per_block,
                add_downsample=i < len(block_out_channels) - 1,
            ))
            channels = out_channels
        self.down_blocks = blocks
        self.mid_block = UNetMidBlock2D(channels)
        self.conv_norm_out = nn.GroupNorm(32, channels, eps=1e-6, pytorch_compatible=True)
        self.conv_out = nn.Conv2d(channels, 2 * latent_channels, 3, padding=1)

    def __call__(self, x: mx.array) -> mx.array:
        x = self.conv_in(x)
        for block in self.down_blocks:
            x = block(x)
            mx.eval(x)
        x = self.mid_block(x)
        mx.eval(x)
        return self.conv_out(_silu(self.conv_norm_out(x)))


class Decoder(nn.Module):
    def __init__(self, out_channels: int, latent_channels: int,
                 block_out_channels: tuple[int, ...], layers_per_block: int):
        super().__init__()
        reversed_channels = list(reversed(block_out_channels))
        self.conv_in = nn.Conv2d(latent_channels, reversed_channels[0], 3, padding=1)
        self.mid_block = UNetMidBlock2D(reversed_channels[0])
        blocks, channels = [], reversed_channels[0]
        for i, out_ch in enumerate(reversed_channels):
            blocks.append(UpDecoderBlock2D(
                channels, out_ch, layers_per_block + 1,
                add_upsample=i < len(reversed_channels) - 1,
            ))
            channels = out_ch
        self.up_blocks = blocks
        self.conv_norm_out = nn.GroupNorm(32, channels, eps=1e-6, pytorch_compatible=True)
        self.conv_out = nn.Conv2d(channels, out_channels, 3, padding=1)

    def __call__(self, x: mx.array) -> mx.array:
        x = self.mid_block(self.conv_in(x))
        mx.eval(x)
        for block in self.up_blocks:
            x = block(x)
            mx.eval(x)
        return self.conv_out(_silu(self.conv_norm_out(x)))


class AutoencoderKL(nn.Module):
    def __init__(self, in_channels: int = 3, out_channels: int = 3, latent_channels: int = 4,
                 block_out_channels: tuple[int, ...] = (128, 256, 512, 512),
                 layers_per_block: int = 2):
        super().__init__()
        self.encoder = Encoder(in_channels, latent_channels, block_out_channels, layers_per_block)
        self.decoder = Decoder(out_channels, latent_channels, block_out_channels, layers_per_block)
        self.quant_conv = nn.Conv2d(2 * latent_channels, 2 * latent_channels, 1)
        self.post_quant_conv = nn.Conv2d(latent_channels, latent_channels, 1)

    def encode_moments(self, x: mx.array) -> tuple[mx.array, mx.array]:
        """Returns (mean, logvar). Input and output are NHWC."""
        moments = self.quant_conv(self.encoder(x))
        mean, logvar = mx.split(moments, 2, axis=-1)
        return mean, mx.clip(logvar, -30.0, 20.0)

    def encode(self, x: mx.array) -> mx.array:
        """Deterministic latent (the distribution mean), already scaled."""
        mean, _ = self.encode_moments(x)
        return mean * SCALING_FACTOR

    def decode(self, latent: mx.array, scaled: bool = True) -> mx.array:
        if scaled:
            latent = latent / SCALING_FACTOR
        return self.decoder(self.post_quant_conv(latent))
