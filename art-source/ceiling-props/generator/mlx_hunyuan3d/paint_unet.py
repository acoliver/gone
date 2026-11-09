"""MLX port of the SD 2.1 UNet used by Hunyuan3D-Paint, including its 2.5D attention.

Two models are built from one checkpoint:

    unet       12-channel input, carries the multi-view and reference attention
    unet_dual  4-channel input, a plain copy that runs the reference image once at
               timestep 0 to populate the reference embeddings the main model reads

The 12 input channels are cat[noisy_latent(4), normal_latent(4), position_latent(4)]: the
normal and position maps are renders of the mesh pushed through the VAE, which is why the
rasteriser feeds this model directly.

Ordering detail that is easy to get wrong: attn_refview and attn_multiview are both applied
to the OUTPUT OF norm1, not to the running hidden state, and each adds its result back into
hidden separately. Feeding them the updated hidden instead still runs and still produces an
image - just a worse one - so it will not announce itself.

Conventions, as in paint_vae: MLX is NHWC with conv weights (out, kH, kW, in), and every
GroupNorm is pytorch_compatible.
"""

from __future__ import annotations

import math

import mlx.core as mx
import mlx.nn as nn


def _silu(x: mx.array) -> mx.array:
    return x * mx.sigmoid(x)


def timestep_embedding(timesteps: mx.array, dim: int, max_period: int = 10000,
                       flip_sin_to_cos: bool = True, downscale_freq_shift: float = 0.0):
    """Diffusers' Timesteps. SD flips the halves so cosine comes first."""
    half = dim // 2
    exponent = -math.log(max_period) * mx.arange(half, dtype=mx.float32)
    exponent = exponent / (half - downscale_freq_shift)
    emb = timesteps.astype(mx.float32)[:, None] * mx.exp(exponent)[None, :]
    if flip_sin_to_cos:
        return mx.concatenate([mx.cos(emb), mx.sin(emb)], axis=-1)
    return mx.concatenate([mx.sin(emb), mx.cos(emb)], axis=-1)


class TimestepEmbedding(nn.Module):
    def __init__(self, in_dim: int, time_dim: int):
        super().__init__()
        self.linear_1 = nn.Linear(in_dim, time_dim)
        self.linear_2 = nn.Linear(time_dim, time_dim)

    def __call__(self, x: mx.array) -> mx.array:
        return self.linear_2(_silu(self.linear_1(x)))


class ResnetBlock2D(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, time_dim: int, groups: int = 32):
        super().__init__()
        self.norm1 = nn.GroupNorm(groups, in_channels, eps=1e-5, pytorch_compatible=True)
        self.conv1 = nn.Conv2d(in_channels, out_channels, 3, padding=1)
        self.time_emb_proj = nn.Linear(time_dim, out_channels)
        self.norm2 = nn.GroupNorm(groups, out_channels, eps=1e-5, pytorch_compatible=True)
        self.conv2 = nn.Conv2d(out_channels, out_channels, 3, padding=1)
        self.conv_shortcut = (
            nn.Conv2d(in_channels, out_channels, 1) if in_channels != out_channels else None
        )

    def __call__(self, x: mx.array, temb: mx.array) -> mx.array:
        residual = x
        h = self.conv1(_silu(self.norm1(x)))
        h = h + self.time_emb_proj(_silu(temb))[:, None, None, :]
        h = self.conv2(_silu(self.norm2(h)))
        if self.conv_shortcut is not None:
            residual = self.conv_shortcut(residual)
        return h + residual


class Attention(nn.Module):
    """Multi-head attention with diffusers' to_q/to_k/to_v/to_out naming."""

    def __init__(self, query_dim: int, heads: int, dim_head: int,
                 context_dim: int | None = None, bias: bool = False):
        super().__init__()
        inner = heads * dim_head
        context_dim = context_dim if context_dim is not None else query_dim
        self.heads = heads
        self.scale = dim_head ** -0.5
        self.to_q = nn.Linear(query_dim, inner, bias=bias)
        self.to_k = nn.Linear(context_dim, inner, bias=bias)
        self.to_v = nn.Linear(context_dim, inner, bias=bias)
        self.to_out = [nn.Linear(inner, query_dim)]

    def __call__(self, x: mx.array, context: mx.array | None = None) -> mx.array:
        context = x if context is None else context
        batch, length, _ = x.shape
        q = self.to_q(x).reshape(batch, length, self.heads, -1).transpose(0, 2, 1, 3)
        k = self.to_k(context).reshape(batch, context.shape[1], self.heads, -1).transpose(0, 2, 1, 3)
        v = self.to_v(context).reshape(batch, context.shape[1], self.heads, -1).transpose(0, 2, 1, 3)
        out = mx.fast.scaled_dot_product_attention(q, k, v, scale=self.scale)
        out = out.transpose(0, 2, 1, 3).reshape(batch, length, -1)
        return self.to_out[0](out)


class GEGLU(nn.Module):
    def __init__(self, dim_in: int, dim_out: int):
        super().__init__()
        self.proj = nn.Linear(dim_in, dim_out * 2)

    def __call__(self, x: mx.array) -> mx.array:
        hidden, gate = mx.split(self.proj(x), 2, axis=-1)
        return hidden * nn.gelu(gate)


class FeedForward(nn.Module):
    def __init__(self, dim: int, mult: int = 4):
        super().__init__()
        inner = dim * mult
        # net.0 is the GEGLU projection, net.1 a dropout (no params), net.2 the output.
        self.net = [GEGLU(dim, inner), None, nn.Linear(inner, dim)]

    def __call__(self, x: mx.array) -> mx.array:
        return self.net[2](self.net[0](x))


class BasicTransformerBlock(nn.Module):
    """The stock SD block. Wrapped by Basic2p5DTransformerBlock, which owns the extra
    attentions but delegates these submodules under a `transformer.` prefix."""

    def __init__(self, dim: int, heads: int, dim_head: int, context_dim: int):
        super().__init__()
        self.norm1 = nn.LayerNorm(dim)
        self.attn1 = Attention(dim, heads, dim_head)
        self.norm2 = nn.LayerNorm(dim)
        self.attn2 = Attention(dim, heads, dim_head, context_dim=context_dim)
        self.norm3 = nn.LayerNorm(dim)
        self.ff = FeedForward(dim)


class Basic2p5DTransformerBlock(nn.Module):
    def __init__(self, dim: int, heads: int, dim_head: int, context_dim: int,
                 use_ma: bool = True, use_ra: bool = True):
        super().__init__()
        self.transformer = BasicTransformerBlock(dim, heads, dim_head, context_dim)
        self.attn_multiview = Attention(dim, heads, dim_head) if use_ma else None
        self.attn_refview = Attention(dim, heads, dim_head) if use_ra else None

    def __call__(self, hidden: mx.array, context: mx.array, mode: str,
                 num_in_batch: int, condition_embed: dict, layer_name: str) -> mx.array:
        block = self.transformer
        normed = block.norm1(hidden)
        hidden = block.attn1(normed) + hidden

        # Reference attention. 'w' captures this layer's normed activations from the
        # reference pass; 'r' cross-attends the generation pass back onto them.
        if "w" in mode:
            batch_n, length, channels = normed.shape
            condition_embed[layer_name] = normed.reshape(
                batch_n // num_in_batch, num_in_batch * length, channels)

        if "r" in mode and self.attn_refview is not None:
            stored = condition_embed[layer_name]
            batch, ref_len, channels = stored.shape
            context_ref = mx.broadcast_to(
                stored[:, None], (batch, num_in_batch, ref_len, channels)
            ).reshape(batch * num_in_batch, ref_len, channels)
            hidden = self.attn_refview(normed, context_ref) + hidden

        # Multi-view attention: all views in a group attend jointly.
        if num_in_batch > 1 and self.attn_multiview is not None:
            batch_n, length, channels = normed.shape
            joined = normed.reshape(batch_n // num_in_batch, num_in_batch * length, channels)
            attended = self.attn_multiview(joined)
            hidden = attended.reshape(batch_n, length, channels) + hidden

        hidden = block.attn2(block.norm2(hidden), context) + hidden
        return block.ff(block.norm3(hidden)) + hidden


class Transformer2DModel(nn.Module):
    def __init__(self, channels: int, heads: int, dim_head: int, context_dim: int,
                 depth: int = 1, use_ma: bool = True, use_ra: bool = True):
        super().__init__()
        self.norm = nn.GroupNorm(32, channels, eps=1e-6, pytorch_compatible=True)
        self.proj_in = nn.Linear(channels, channels)      # use_linear_projection=True
        self.transformer_blocks = [
            Basic2p5DTransformerBlock(channels, heads, dim_head, context_dim, use_ma, use_ra)
            for _ in range(depth)
        ]
        self.proj_out = nn.Linear(channels, channels)

    def __call__(self, x: mx.array, context: mx.array, mode: str, num_in_batch: int,
                 condition_embed: dict, layer_name: str) -> mx.array:
        batch, height, width, channels = x.shape
        residual = x
        h = self.norm(x).reshape(batch, height * width, channels)
        h = self.proj_in(h)
        for i, block in enumerate(self.transformer_blocks):
            h = block(h, context, mode, num_in_batch, condition_embed, f"{layer_name}_{i}")
        h = self.proj_out(h)
        return h.reshape(batch, height, width, channels) + residual


class Downsample2D(nn.Module):
    def __init__(self, channels: int):
        super().__init__()
        self.conv = nn.Conv2d(channels, channels, 3, stride=2, padding=1)

    def __call__(self, x: mx.array) -> mx.array:
        return self.conv(x)


class Upsample2D(nn.Module):
    def __init__(self, channels: int):
        super().__init__()
        self.conv = nn.Conv2d(channels, channels, 3, padding=1)

    def __call__(self, x: mx.array) -> mx.array:
        batch, height, width, channels = x.shape
        x = mx.broadcast_to(x[:, :, None, :, None, :], (batch, height, 2, width, 2, channels))
        return self.conv(x.reshape(batch, height * 2, width * 2, channels))


class CrossAttnDownBlock2D(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, time_dim: int, layers: int,
                 heads: int, context_dim: int, add_downsample: bool, name: str,
                 use_ma: bool, use_ra: bool):
        super().__init__()
        self.resnets, self.attentions = [], []
        for i in range(layers):
            self.resnets.append(
                ResnetBlock2D(in_channels if i == 0 else out_channels, out_channels, time_dim))
            self.attentions.append(Transformer2DModel(
                out_channels, heads, out_channels // heads, context_dim,
                use_ma=use_ma, use_ra=use_ra))
        self.downsamplers = [Downsample2D(out_channels)] if add_downsample else []
        self.name = name

    def __call__(self, x, temb, context, mode, num_in_batch, condition_embed):
        states = []
        for i, (resnet, attn) in enumerate(zip(self.resnets, self.attentions)):
            x = resnet(x, temb)
            x = attn(x, context, mode, num_in_batch, condition_embed, f"{self.name}_{i}")
            states.append(x)
        for down in self.downsamplers:
            x = down(x)
            states.append(x)
        return x, states


class DownBlock2D(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, time_dim: int, layers: int,
                 add_downsample: bool):
        super().__init__()
        self.resnets = [
            ResnetBlock2D(in_channels if i == 0 else out_channels, out_channels, time_dim)
            for i in range(layers)
        ]
        self.downsamplers = [Downsample2D(out_channels)] if add_downsample else []

    def __call__(self, x, temb):
        states = []
        for resnet in self.resnets:
            x = resnet(x, temb)
            states.append(x)
        for down in self.downsamplers:
            x = down(x)
            states.append(x)
        return x, states


class CrossAttnUpBlock2D(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, prev_channels: int, time_dim: int,
                 layers: int, heads: int, context_dim: int, add_upsample: bool, name: str,
                 use_ma: bool, use_ra: bool):
        super().__init__()
        self.resnets, self.attentions = [], []
        for i in range(layers):
            res_skip = in_channels if (i == layers - 1) else out_channels
            res_prev = prev_channels if i == 0 else out_channels
            self.resnets.append(ResnetBlock2D(res_prev + res_skip, out_channels, time_dim))
            self.attentions.append(Transformer2DModel(
                out_channels, heads, out_channels // heads, context_dim,
                use_ma=use_ma, use_ra=use_ra))
        self.upsamplers = [Upsample2D(out_channels)] if add_upsample else []
        self.name = name

    def __call__(self, x, states, temb, context, mode, num_in_batch, condition_embed):
        for i, (resnet, attn) in enumerate(zip(self.resnets, self.attentions)):
            x = mx.concatenate([x, states.pop()], axis=-1)
            x = resnet(x, temb)
            x = attn(x, context, mode, num_in_batch, condition_embed, f"{self.name}_{i}")
        for up in self.upsamplers:
            x = up(x)
        return x


class UpBlock2D(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, prev_channels: int, time_dim: int,
                 layers: int, add_upsample: bool):
        super().__init__()
        self.resnets = []
        for i in range(layers):
            res_skip = in_channels if (i == layers - 1) else out_channels
            res_prev = prev_channels if i == 0 else out_channels
            self.resnets.append(ResnetBlock2D(res_prev + res_skip, out_channels, time_dim))
        self.upsamplers = [Upsample2D(out_channels)] if add_upsample else []

    def __call__(self, x, states, temb):
        for resnet in self.resnets:
            x = mx.concatenate([x, states.pop()], axis=-1)
            x = resnet(x, temb)
        for up in self.upsamplers:
            x = up(x)
        return x


class UNetMidBlock2DCrossAttn(nn.Module):
    def __init__(self, channels: int, time_dim: int, heads: int, context_dim: int,
                 use_ma: bool, use_ra: bool):
        super().__init__()
        self.resnets = [ResnetBlock2D(channels, channels, time_dim),
                        ResnetBlock2D(channels, channels, time_dim)]
        self.attentions = [Transformer2DModel(
            channels, heads, channels // heads, context_dim, use_ma=use_ma, use_ra=use_ra)]

    def __call__(self, x, temb, context, mode, num_in_batch, condition_embed):
        x = self.resnets[0](x, temb)
        x = self.attentions[0](x, context, mode, num_in_batch, condition_embed, "mid_0")
        return self.resnets[1](x, temb)


class UNet2DConditionModel(nn.Module):
    """SD 2.1 UNet. `in_channels` is 12 for the main model and 4 for the dual stream."""

    def __init__(self, in_channels: int = 4, out_channels: int = 4,
                 block_out_channels: tuple[int, ...] = (320, 640, 1280, 1280),
                 layers_per_block: int = 2, attention_head_dim=(5, 10, 20, 20),
                 context_dim: int = 1024, num_class_embeds: int = 49,
                 use_ma: bool = True, use_ra: bool = True,
                 learned_prompts: bool = True):
        super().__init__()
        time_dim = block_out_channels[0] * 4
        if learned_prompts:
            # This model has no text encoder: the prompt embeddings are trained constants.
            # They live on the main UNet only, not on the dual stream.
            self.learned_text_clip_gen = mx.zeros((1, 77, context_dim))
            self.learned_text_clip_ref = mx.zeros((1, 77, context_dim))
        self.time_embed_dim = time_dim
        self.block_out_channels = block_out_channels
        self.time_embedding = TimestepEmbedding(block_out_channels[0], time_dim)
        # The dual stream is deep-copied from the base UNet BEFORE the camera embedding is
        # attached, so it has none. Upstream still passes class_labels to it; diffusers
        # ignores them when class_embedding is None, and so do we.
        self.class_embedding = (
            nn.Embedding(num_class_embeds, time_dim) if num_class_embeds else None
        )
        self.conv_in = nn.Conv2d(in_channels, block_out_channels[0], 3, padding=1)

        # Despite the name, diffusers' `attention_head_dim` in an SD 2.x config holds the
        # NUMBER OF HEADS, not the size of each. For [5,10,20,20] against channels
        # [320,640,1280,1280] the per-head width is 64. Reading it the other way round
        # gives heads=64/dim_head=5, whose inner dimension is still 320 - so every tensor
        # shape stays valid and the checkpoint loads cleanly while the attention groups
        # completely differently. It fails parity, not assertion.
        heads = list(attention_head_dim)

        self.down_blocks = []
        channels = block_out_channels[0]
        for i, out_ch in enumerate(block_out_channels):
            last = i == len(block_out_channels) - 1
            if not last:
                self.down_blocks.append(CrossAttnDownBlock2D(
                    channels, out_ch, time_dim, layers_per_block, heads[i], context_dim,
                    add_downsample=True, name=f"down_{i}", use_ma=use_ma, use_ra=use_ra))
            else:
                self.down_blocks.append(
                    DownBlock2D(channels, out_ch, time_dim, layers_per_block, False))
            channels = out_ch

        self.mid_block = UNetMidBlock2DCrossAttn(
            channels, time_dim, heads[-1], context_dim, use_ma, use_ra)

        self.up_blocks = []
        reversed_out = list(reversed(block_out_channels))
        reversed_heads = list(reversed(heads))
        prev = reversed_out[0]
        for i, out_ch in enumerate(reversed_out):
            skip = reversed_out[min(i + 1, len(reversed_out) - 1)]
            if i == 0:
                self.up_blocks.append(UpBlock2D(
                    skip, out_ch, prev, time_dim, layers_per_block + 1, True))
            else:
                self.up_blocks.append(CrossAttnUpBlock2D(
                    skip, out_ch, prev, time_dim, layers_per_block + 1, reversed_heads[i],
                    context_dim, add_upsample=i < len(reversed_out) - 1,
                    name=f"up_{i}", use_ma=use_ma, use_ra=use_ra))
            prev = out_ch

        self.conv_norm_out = nn.GroupNorm(32, block_out_channels[0], eps=1e-5,
                                          pytorch_compatible=True)
        self.conv_out = nn.Conv2d(block_out_channels[0], out_channels, 3, padding=1)

    def __call__(self, sample: mx.array, timestep, encoder_hidden_states: mx.array,
                 class_labels: mx.array | None = None, mode: str = "r",
                 num_in_batch: int = 1, condition_embed: dict | None = None) -> mx.array:
        condition_embed = {} if condition_embed is None else condition_embed

        if not isinstance(timestep, mx.array):
            timestep = mx.array([timestep] * sample.shape[0])
        if timestep.size == 1 and sample.shape[0] > 1:
            timestep = mx.broadcast_to(timestep, (sample.shape[0],))
        # The sinusoid is built in float32 for precision, then cast to the weight dtype.
        # Without the cast a float32 temb promotes every downstream activation back to
        # float32, silently undoing a float16 load.
        weight_dtype = self.conv_in.weight.dtype
        embedded = timestep_embedding(timestep, self.block_out_channels[0])
        temb = self.time_embedding(embedded.astype(weight_dtype))
        if self.class_embedding is not None and class_labels is not None:
            temb = temb + self.class_embedding(class_labels)

        x = self.conv_in(sample)
        states = [x]
        for block in self.down_blocks:
            if isinstance(block, DownBlock2D):
                x, new_states = block(x, temb)
            else:
                x, new_states = block(x, temb, encoder_hidden_states, mode, num_in_batch,
                                      condition_embed)
            states.extend(new_states)
            # Force evaluation at block boundaries. MLX is lazy, so without this the whole
            # UNet graph - every intermediate in every block - stays live until the final
            # eval. With multi-view attention concatenating N views that alone pushed peak
            # memory over 110 GB.
            mx.eval(x, *new_states)

        x = self.mid_block(x, temb, encoder_hidden_states, mode, num_in_batch, condition_embed)
        mx.eval(x)

        for block in self.up_blocks:
            if isinstance(block, UpBlock2D):
                x = block(x, states, temb)
            else:
                x = block(x, states, temb, encoder_hidden_states, mode, num_in_batch,
                          condition_embed)
            mx.eval(x)

        return self.conv_out(_silu(self.conv_norm_out(x)))
