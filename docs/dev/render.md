# gone render notes: game post chain and pass order (issue #6 slice B)

This records the game camera's post-processing chain and the render-pass order
it depends on, so the eyelid pass (#8) lands in the right slot without
re-deriving the graph. The code home for the chain is
`crates/gone_app/src/post.rs`; the camera rig is
`crates/gone_app/src/player.rs`. The chain exists on the game camera only:
the harness lanes (`GONE_HARNESS=1`, with or without `GONE_RENDER_CHECK=1`)
never add these plugins or components.

## What the game camera carries

- `AutoExposurePlugin`, added explicitly (`bevy_post_process::auto_exposure`).
  DefaultPlugins adds `PostProcessPlugin` (bloom, depth of field, motion
  blur, the effect stack) but not auto exposure, so the game adds it by name.
- `Tonemapping::AgX` on the camera. AgX requires the `tonemapping_luts`
  feature (the LUT ktx2 textures) and the `zstd_rust` decoder; specializing
  an AgX pipeline without them panics.
- `Vignette` (intensity 0.35, radius 0.85, smoothness 5.0, center and
  roundness at the neutral defaults): a gentle lens fall-off, not a tunnel.
- `AutoExposure` with a center-weighted metering mask: a checked-in 64x64
  `R8Unorm` asset (`assets/post/metering_mask.png`), a radial falloff with
  weight `w = (1 - r²)²` quantized to the shader's 16 levels. The shader
  samples the red channel and multiplies it by 16 for its histogram weight,
  so the asset stores exactly the weights the GPU applies. The construction
  is executable in `post.rs`, and the checked-in asset is generated from it
  by the ignored test `generate_metering_mask_asset`, which fails if the
  file ever drifts from the construction. The uniform white default mask is
  not used.

## Pass order (bevy 0.19)

`Core3d` chains the sets `Prepass → MainPass → EarlyPostProcess →
PostProcess` (`bevy_core_pipeline::schedule::Core3dSystems`). Within
`PostProcess`, the edges bevy declares are:

- `auto_exposure.before(tonemapping)` (`bevy_post_process::auto_exposure`)
- effect stack `post_processing.after(depth_of_field).before(tonemapping)`
  (`bevy_post_process::effect_stack`)
- `tonemapping.in_set(Core3dSystems::PostProcess)` (`bevy_core_pipeline`)
- `upscaling.after(Core3dSystems::PostProcess)` (`bevy_core_pipeline`)

The order the game relies on:

    MainPass (HDR) → [auto exposure, effect stack (vignette)] → tonemapping → upscaling

Auto exposure and the effect stack each pin only their edge to tonemapping;
their order relative to each other is unspecified by bevy, and nothing in the
game depends on it.

## Where the eyelid pass (#8) goes

The eyelid pass installs after tonemapping: `.after(Core3dSystems::PostProcess)`
in `Core3d`, compositing over the finished LDR image. It must also declare its
order against upscaling explicitly (before `Node3d::Upscaling`), because
upscaling carries the same `after(PostProcess)` edge and bevy would otherwise
leave the two unordered.

It must not run before tonemapping and must not write the HDR main texture:

- Auto exposure reads the HDR main texture (`ViewTarget::main_texture_view()`)
  in its histogram compute pass. A pass that darkens the frame before or in
  place of tonemapping would show up in the histogram, drive the exposure
  compensation up, and un-darken the image over a few frames. A pass that
  runs after tonemapping never touches that texture, so metering never sees
  the eyelid at all.
- The near-zero corner weight of the metering mask additionally decouples
  metering from the vignette, whose darkening is confined to corners; corner
  pixels carry almost no histogram weight either way.

With the eyelid after tonemapping, exposure keeps converging on the scene's
true luminance while the player sees the eyelid occlusion on top. The eyelid
is a presentation effect over the scene, and exposure must keep tracking the
scene beneath it.

## Validated on Metal vs assumed

Validated on this machine (Apple M4 Max, Metal, bevy 0.19.1):

- The game binary boots and renders with this exact chain (explicit boot
  check: no panics, no shader compilation or bind-group errors in the log).
- The metering mask asset loads through the asset server and reaches the
  camera's `AutoExposure` component (the no-GPU wiring test builds both game
  plugins and asserts the handle equality).

Assumed from bevy 0.19.1 source, not observed with a frame debugger:

- The pass edges quoted above (read from `bevy_core_pipeline` and
  `bevy_post_process` sources for this exact version).
- The histogram reading the HDR main texture (the compute pass binds
  `ViewTarget::main_texture_view()`).
- The 16-level metering-mask quantization (documented on
  `AutoExposure::metering_mask`, and visible as `u32(mask * 16.0)` in
  `auto_exposure.wgsl`).

A frame-capture check that the passes execute in the recorded order is the
follow-up when the eyelid pass lands (Metal GPU capture or RenderDoc). The
ordering contract is enforced by the render graph itself, so the capture
guards the assumption, not the mechanism.
