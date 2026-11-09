"""End-to-end Hunyuan3D-Paint: mesh + reference image -> textured mesh.

Assembles the verified pieces:

    paint_conditioning  normal and position maps rendered with our rasteriser
    paint_vae           encodes those maps, decodes the generated views
    paint_unet          SD 2.1 UNet with multi-view and reference attention
    paint_scheduler     LCM with the turbo timestep selection
    texture_bake        projects the generated views onto a UV atlas

The UNet consumes 12 latent channels, cat[noisy(4), normal(4), position(4)], and reads
reference features that the dual stream writes in a separate pass at timestep 0.

NOT IMPLEMENTED: upstream first runs the input image through hunyuan3d-delight-v2-0 to
strip baked lighting. That is a separate checkpoint and is skipped here, so lighting in
the reference image is carried into the texture. This is a quality limitation, and it is
called out rather than hidden because the output looks plausible either way.
"""

from __future__ import annotations

import numpy as np

from .paint_conditioning import (
    CANDIDATE_AZIMUTHS,
    CANDIDATE_ELEVATIONS,
    CANDIDATE_VIEW_WEIGHTS,
    camera_labels,
    normalize_for_paint,
    render_normal_maps,
    render_position_maps,
)
from .paint_scheduler import LCMScheduler
from .paint_unet import UNet2DConditionModel
from .paint_vae import AutoencoderKL
from .paint_weights import load_unet, load_vae, verify_loaded, verify_unet_loaded
from .texture_bake import bake, inpaint, unwrap

VIEW_SIZE = 512


class PaintPipeline:
    def __init__(self, vae, main_unet, dual_unet, scheduler):
        self.vae = vae
        self.unet = main_unet
        self.unet_dual = dual_unet
        self.scheduler = scheduler

    @classmethod
    def from_pretrained(cls, model_path: str = "weights/Hunyuan3D-2",
                        subfolder: str = "hunyuan3d-paint-v2-0-turbo",
                        vae_path: str | None = None, dtype: str = "float16"):
        import os

        base = os.path.join(model_path, subfolder)
        # The turbo folder ships its VAE only as a pickled .bin, so the identical
        # non-turbo safetensors copy is used instead.
        vae_file = vae_path or os.path.join(
            model_path, "hunyuan3d-paint-v2-0", "vae", "diffusion_pytorch_model.safetensors")
        unet_file = os.path.join(base, "unet", "diffusion_pytorch_model.safetensors")

        vae = AutoencoderKL()
        load_vae(vae, vae_file)
        verify_loaded(vae, vae_file)

        main = UNet2DConditionModel(in_channels=12, use_ma=True, use_ra=True,
                                    learned_prompts=True)
        dual = UNet2DConditionModel(in_channels=4, use_ma=False, use_ra=False,
                                    learned_prompts=False, num_class_embeds=None)
        load_unet(main, dual, unet_file, dtype=dtype)
        verify_unet_loaded(main, dual, unet_file)
        return cls(vae, main, dual, LCMScheduler())

    def _encode(self, images: list[np.ndarray], chunk: int = 2):
        """VAE-encode a list of HWC images in 0..1 to scaled latents.

        Encoded in small chunks. The VAE's early layers run at FULL image resolution, so
        a 12-image batch at 1024 allocates activations of
        12 x 1024 x 1024 x 128 x 4 bytes = 6.4 GB EACH, several times over. Batching
        everything at once is what exhausted system memory; the chunk size trades a
        negligible amount of speed for a bounded peak.
        """
        import mlx.core as mx

        outputs = []
        for start in range(0, len(images), chunk):
            batch = np.stack(images[start:start + chunk]).astype(np.float32) * 2.0 - 1.0
            latent = self.vae.encode(mx.array(batch))
            mx.eval(latent)
            outputs.append(latent)
            mx.clear_cache()
        return mx.concatenate(outputs, axis=0) if len(outputs) > 1 else outputs[0]

    def _decode(self, latents, chunk: int = 2):
        """VAE-decode latents in small chunks, for the same reason as _encode."""
        import mlx.core as mx

        outputs = []
        for start in range(0, latents.shape[0], chunk):
            decoded = self.vae.decode(latents[start:start + chunk])
            mx.eval(decoded)
            outputs.append(np.array(decoded))
            del decoded
            mx.clear_cache()
        return np.concatenate(outputs, axis=0)

    def __call__(self, vertices, faces, reference_image: np.ndarray,
                 resolution: int = VIEW_SIZE, texture_size: int = 1024,
                 seed: int = 0, view_weights=None, azimuths=None, elevations=None,
                 atlas_uvs: np.ndarray | None = None,
                 bake_diagnostics: bool = False, verbose: bool = True):
        import mlx.core as mx

        mx.random.seed(seed)
        # Place the mesh in the frame the paint model expects. Skipping this leaves the
        # model outside the orthographic frustum and the conditioning maps arrive cropped.
        # normalize_for_paint mirrors and swaps axes for the paint cameras: it computes
        # new_y = old_z and new_z = -old_y. That is correct for rendering the conditioning
        # maps, but it means the paint-frame mesh is LYING ON ITS SIDE AND INVERTED
        # relative to what the caller handed us - a canopy at +y ends up at -z, i.e.
        # pointing DOWN. Exporting that frame ships an upside-down model whose canopy
        # reads as a lump hanging underneath.
        #
        # Keep the caller's vertices so the result can be returned in their orientation.
        source_vertices = np.asarray(vertices, dtype=np.float64).copy()
        vertices, faces = normalize_for_paint(vertices, faces)

        if verbose:
            print(f"  rendering conditioning maps at {resolution}px")
        # One camera set drives the conditioning maps, the class labels and the bake.
        # If these ever disagree the model is told it is looking one way while being shown
        # another, which produces plausible-but-wrong output rather than an error.
        cam_az = list(azimuths or CANDIDATE_AZIMUTHS)
        cam_el = list(elevations or CANDIDATE_ELEVATIONS)
        if len(cam_az) != len(cam_el):
            raise ValueError("azimuths and elevations must be the same length")
        normals = render_normal_maps(vertices, faces, azimuths=cam_az, elevations=cam_el,
                                     resolution=resolution)
        positions = render_position_maps(vertices, faces, azimuths=cam_az, elevations=cam_el,
                                         resolution=resolution)
        views = len(normals)

        normal_latents = self._encode(normals)
        position_latents = self._encode(positions)

        reference = np.asarray(reference_image, dtype=np.float32)
        if reference.shape[0] != resolution or reference.shape[1] != resolution:
            from PIL import Image
            reference = np.asarray(
                Image.fromarray((np.clip(reference, 0, 1) * 255).astype(np.uint8))
                .resize((resolution, resolution), Image.LANCZOS)).astype(np.float32) / 255.0
        ref_latent = self._encode([reference])

        dtype = self.unet.conv_in.weight.dtype
        normal_latents = normal_latents.astype(dtype)
        position_latents = position_latents.astype(dtype)
        ref_latent = ref_latent.astype(dtype)

        # Reference pass: the dual stream writes per-layer features at timestep 0, which
        # the main stream then attends back onto through attn_refview.
        if verbose:
            print("  reference pass (dual stream)")
        condition_embed: dict = {}
        self.unet_dual(ref_latent, 0, self.unet.learned_text_clip_ref.astype(dtype),
                       mode="w", num_in_batch=1, condition_embed=condition_embed)
        mx.eval(list(condition_embed.values()))

        latent_size = resolution // 8
        latents = mx.random.normal((views, latent_size, latent_size, 4)).astype(dtype)
        context = mx.broadcast_to(
            self.unet.learned_text_clip_gen.astype(dtype), (views, 77, 1024))
        labels = mx.array(camera_labels(cam_az, cam_el))

        for step in range(len(self.scheduler)):
            timestep = int(self.scheduler.timesteps[step])
            sample = mx.concatenate([latents, normal_latents, position_latents], axis=-1)
            noise_pred = self.unet(sample, timestep, context, class_labels=labels,
                                   mode="r", num_in_batch=views,
                                   condition_embed=condition_embed)
            latents, denoised = self.scheduler.step(noise_pred, step, latents)
            mx.eval(latents)
            if verbose:
                print(f"    step {step + 1}/{len(self.scheduler)} (t={timestep})")

        if verbose:
            print("  decoding views")
        images = np.clip((self._decode(denoised.astype(mx.float32)) + 1.0) * 0.5, 0.0, 1.0)
        mx.clear_cache()

        del normal_latents, position_latents, ref_latent, condition_embed, latents
        mx.clear_cache()
        if verbose:
            peak = mx.get_peak_memory() / 2**30
            print(f"  peak GPU memory {peak:.1f} GB")
        if atlas_uvs is None:
            if verbose:
                print("  unwrapping UV atlas")
            atlas_vertices, atlas_faces, uvs, atlas_vmap = unwrap(
                vertices, faces, return_vertex_map=True)
        else:
            if verbose:
                print("  using caller's frozen UV atlas (no xatlas)")
            uvs = np.asarray(atlas_uvs, dtype=np.float64)
            if uvs.shape != (len(vertices), 2):
                raise ValueError(
                    f"atlas_uvs must have shape ({len(vertices)}, 2), got {uvs.shape}")
            if not np.isfinite(uvs).all() or np.any(uvs < 0) or np.any(uvs > 1):
                raise ValueError("atlas_uvs must be finite and within 0..1")
            atlas_vertices = vertices
            atlas_faces = faces
            atlas_vmap = None

        weights = view_weights or CANDIDATE_VIEW_WEIGHTS
        view_specs = [
            {"image": images[i], "azimuth": cam_az[i],
             "elevation": cam_el[i], "weight": weights[i]}
            for i in range(views)
        ]
        if verbose:
            print("  baking texture")
        baked = bake(atlas_vertices, atlas_faces, uvs, view_specs,
                     texture_size=texture_size, return_diagnostics=bake_diagnostics)
        if bake_diagnostics:
            texture, filled, diagnostics = baked
            diagnostics["pre_push_pull_texture"] = texture.astype(np.float32)
        else:
            texture, filled = baked
            diagnostics = None
        texture = inpaint(texture, filled)
        if diagnostics is not None:
            diagnostics["post_push_pull_texture"] = texture.astype(np.float32)
            diagnostics["push_pull_filled"] = diagnostics["covered"] & ~filled
        result = {
            "texture": texture,
            "uvs": uvs,
            # returned in the CALLER's orientation, not the paint frame
            "vertices": source_vertices[atlas_vmap] if atlas_vmap is not None
            else atlas_vertices,
            "paint_frame_vertices": atlas_vertices,
            "faces": atlas_faces,
            "views": images,
            "normal_maps": normals,
            "position_maps": positions,
        }
        if diagnostics is not None:
            result["bake_diagnostics"] = diagnostics
        return result
