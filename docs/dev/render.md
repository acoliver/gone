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
  8-bit grayscale PNG asset (`assets/post/metering_mask.png`), a radial
  falloff with weight `w = (1 - r²)²` quantized to the shader's 16 levels,
  loaded with explicit linear settings (`is_srgb: false`; the mask is a
  weight table, so its bytes must reach the shader un-decoded and the
  resolved texture format stays linear). The shader samples the red channel
  and multiplies it by 16 for its histogram weight, so the asset stores
  exactly the weights the GPU applies. The construction is executable in
  `post.rs`, the checked-in asset is generated from it by the ignored test
  `generate_metering_mask_asset`, and the normal test run reads the shipped
  PNG back (center-heaviest, monotone falloff) plus the loader settings
  (resolved format linear) without regenerating anything. The uniform white
  default mask is not used.

## Pass order (bevy 0.19)

Bevy 0.19 has no render-graph nodes for this pipeline: `Core3d` is a render
*schedule* (`impl ScheduleLabel`, `bevy_core_pipeline::schedule`), its stages
are the system sets `Prepass → MainPass → EarlyPostProcess → PostProcess`
chained by `Core3d::base_schedule()`, and passes are plain render systems
added to that schedule. The edges bevy declares (validated against the
0.19.1 sources):

- `auto_exposure.before(tonemapping).in_set(Core3dSystems::PostProcess)`
  (`bevy_post_process::auto_exposure`)
- effect stack `post_processing.after(depth_of_field).before(tonemapping)`
  (`bevy_post_process::effect_stack`, `Core3d` arm)
- `tonemapping.in_set(Core3dSystems::PostProcess)` (`bevy_core_pipeline::core_3d`)
- `upscaling.after(Core3dSystems::PostProcess)`, where `upscaling` is the
  render system `bevy_core_pipeline::upscaling::upscaling` (added by
  `bevy_core_pipeline::core_3d`). There is no `Node3d::Upscaling` in 0.19;
  that name belongs to the pre-0.19 render graph.

The order the game relies on:

    MainPass (HDR) → [auto exposure, effect stack (vignette)] → tonemapping → upscaling

Auto exposure and the effect stack each pin only their edge to tonemapping;
their order relative to each other is unspecified by bevy, and nothing in the
game depends on it.

## Where the eyelid pass (#8) goes

`Core3d` is a schedule, so the eyelid installs as a render system:

    render_app.add_systems(Core3d, eyelid.after(Core3dSystems::PostProcess).before(upscaling))

`.after(Core3dSystems::PostProcess)` puts it after the whole set, tonemapping
included, compositing over the finished LDR frame. `.before(upscaling)` must
be declared explicitly: upscaling carries the same `after(PostProcess)` edge,
so bevy would otherwise leave the two unordered. Upscaling reads the view's
current main texture (`ViewTarget::main_texture_view()`) and blits it to the
output texture, so an eyelid ordered after upscaling would render into the
ping-pong pair after the blit and never reach the screen.

If the eyelid is implemented as a `FullscreenMaterial`, the default placement
is wrong for it and must be overridden: `FullscreenMaterial::schedule_configs`
defaults to `system.in_set(Core3dSystems::PostProcess).before(tonemapping)`
(`bevy_core_pipeline::fullscreen_material`), i.e. inside the PostProcess set
and *before* tonemapping. The override moves it to the slot above, after
tonemapping and before upscaling; nothing else about the plugin changes.

The pass must continue the ViewTarget ping-pong, not write in place. Bevy's
`ViewTarget` holds two main textures; every `post_process_write()` hands the
caller `source` (the current main texture) and `destination` (the other one)
and flips which of the pair is current. Tonemapping runs exactly this way
(its render pass writes `post_process.destination`), and upscaling then reads
whichever texture is current. The eyelid does the same: bind `source`, draw
to `destination`, call `post_process_write()` first. Writing anything else
(scaling into a private texture, or drawing into `source`'s view) breaks the
chain upscaling reads.

It must not run before tonemapping, and it does not reach metering:

- Auto exposure's histogram compute reads `ViewTarget::main_texture_view()`
  at its ordered point, before tonemapping's `post_process_write()` flips the
  pair. Because every later write goes to the other texture of the pair, the
  texture the histogram read this frame is never the one the eyelid draws
  into, so the eyelid cannot show up in the histogram, drive the exposure
  compensation up, and un-darken the image over a few frames.
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

Validated by reading the vendored 0.19.1 sources, not observed with a frame
debugger:

- The pass edges quoted above (`bevy_core_pipeline::core_3d`, `upscaling`,
  `tonemapping`; `bevy_post_process::auto_exposure`, `effect_stack`), and the
  absence of any `Node3d` graph enum in this version.
- The default `FullscreenMaterial::schedule_configs` placement (inside
  `PostProcess`, before tonemapping) and the `Core3d` schedule/set model.
- The histogram binding `ViewTarget::main_texture_view()` and the
  ping-pong flip in `ViewTarget::post_process_write()` (both read directly
  in `bevy_post_process` and `bevy_render` sources for this version).
- The 16-level metering-mask quantization (`u32(mask * 16.0)` in
  `auto_exposure.wgsl`, documented on `AutoExposure::metering_mask`).

Still assumed, because only a GPU capture can show it: that the schedules
execute in the recorded order at runtime. A frame-capture check (Metal GPU
capture or RenderDoc) is the follow-up when the eyelid pass lands. The
ordering contract is enforced by the schedule's explicit edges, so the
capture guards the assumption, not the mechanism.
