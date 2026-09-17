//! The calibration-evidence lane's app side (issue #6 slice B).
//!
//! The scenario (`harness::calibration`) predeclares the run: one luminance
//! step, an equal-area bright-patch placement plan (including a
//! center-then-edge move at a pinned tick), a metering-mask selection, and
//! the auto-exposure on/off arm. This module renders exactly that scene
//! through the REAL post chain and records the run's setup identity as the
//! report's [`TimedEvent::Calibration`] evidence. It never measures
//! luminance; the runner measures the capture PNGs against this setup.
//!
//! # Camera / capture / post reconciliation
//!
//! The post chain is Core3d: `auto_exposure` and the effect stack run before
//! `tonemapping` in bevy's `Core3d` schedule (`post.rs` documents the pass
//! order), and a `Camera2d` renders the Core2d graph, where none of those
//! passes exist. The existing capture lane's camera is a `Camera2d`, so on
//! this lane the scene renders through a dedicated `Camera3d` that carries
//! the full post chain (`camera_post_components`: `AgX` tonemapping, vignette,
//! auto exposure through the selected mask) and writes into the SAME offscreen
//! capture target the capture lane already reads back. One camera renders the
//! calibration scene, and it is the camera the capture lane feeds on: beat
//! captures are the executed post-chain output, not a side render.
//!
//! The frame-code chip stays Core2d (a sprite; sprites never render in a 3d
//! view, and the runner decodes it from every beat PNG). A second camera —
//! the chip overlay — draws the chip OVER the 3d output into the same target
//! by alpha-blending its final write (`chip_overlay_camera` documents why
//! blending is the only correct overlay mechanism: bevy's per-camera output
//! blit replaces the target unless the camera's `output_mode` blends, so a
//! plain `ClearColorConfig::None` camera would paint its whole intermediate
//! over the scene every frame). The calibration lane's cameras are exactly
//! this pair per target; the capture lane's plain 2d camera does not exist
//! here, because its opaque write would replace the scene camera's output.
//! This composite is honest to the protocol: the scene pixels in a capture
//! are the executed post chain's output, and the chip is the capture lane's
//! frame-code machinery drawn after the chain. It also protects both
//! measurements: the chip lives on the tonemapped LDR output of a different
//! view, so its fixed palette survives every exposure the auto-exposure arm
//! adapts to, and the histogram pass reads the 3d view's HDR main texture,
//! which the chip never enters — metering sees only the wall and the patch.
//!
//! Canary runs (`GONE_RENDER_CHECK=1`) mirror the same pair onto the window:
//! a window `Camera3d` with the same post chain presents the scene, and a
//! window 2d overlay draws the chip, so the one onscreen capture decodes.
//!
//! # Evidence, not measurements
//!
//! [`record_calibration_evidence`] fires once the selected metering-mask
//! asset has actually loaded (the sha256 names the loaded `Image` pixel bytes
//! the GPU histogram samples, not the file path) and the readiness boundary
//! has passed. It records the mask identity, the auto-exposure settings as
//! bound on the camera, the authored exposure, the patch plan, the light
//! levels, and the pinned sample ticks (the scenario's beat ticks). The beat
//! requester refuses to pin a capture before the flag
//! (`state::beat_requests_allowed`) is set, so every capture the runner
//! measures postdates the setup event.
//!
//! # Scene geometry
//!
//! The camera sits at the origin looking down -Z at a wall plane
//! [`WALL_DISTANCE`] away, pinned vertical field of view
//! [`CALIBRATION_FOV`]. The wall's linear radiance is the scenario's light
//! level (`StandardMaterial` emissive; `base_color` is black and the scene
//! has no lights, so emissive is the whole signal). The bright patch is a
//! square quad at the wall plane whose side is
//! `sqrt(patch_area_fraction · frame_width · frame_height)` — the same area
//! in both slots. [`PatchSlot::Center`] is the optical axis; [`PatchSlot::
//! Edge`] sits at [`EDGE_SLOT_FRACTION`] of the half-extents toward the
//! upper right, the lane's fixed edge position, and
//! [`harness::calibration::PATCH_AREA_FRACTION_MAX`] is the parse-time cap
//! that keeps the patch on screen there. The patch radiates a fixed multiple
//! ([`PATCH_LEVEL_MULTIPLE`]) of the current wall level, so the patch is a
//! positive luminance outlier at every level. Dynamics apply per logical
//! tick in the same update the chip is painted for that tick, so a capture
//! pinned at tick T shows tick T's level, patch slot, and chip code together.

use bevy::asset::{AssetServer, Assets, Handle, LoadState, RenderAssetUsages};
use bevy::camera::PerspectiveProjection;
use bevy::camera::{
    Camera, Camera2d, Camera3d, CameraOutputMode, ClearColorConfig, Exposure, Hdr, Projection,
    RenderTarget,
};
use bevy::color::{Color, LinearRgba};
use bevy::core_pipeline::tonemapping::Tonemapping;
use bevy::ecs::prelude::{Commands, Component, Query, Res, ResMut, Resource, With};
use bevy::ecs::system::SystemParam;
use bevy::image::Image;
use bevy::math::{UVec2, Vec3};
use bevy::mesh::{Indices, Mesh, Mesh3d};
use bevy::pbr::{MeshMaterial3d, StandardMaterial};
use bevy::post_process::auto_exposure::AutoExposure;
use bevy::post_process::effect_stack::Vignette;
use bevy::render::render_resource::BlendState;
use bevy::render::render_resource::PrimitiveTopology;
use bevy::render::view::Msaa;
use bevy::transform::components::Transform;
use sha2::{Digest as _, Sha256};
use std::fmt::Write as _;

use super::state::{HarnessState, PresentGate, Readiness, RunMode, drive_allowed, fail_scenario};
use super::{CAPTURE_H, CAPTURE_W};
use crate::harness::calibration::{
    AutoExposureEvidence, AutoExposureSettings, CalibrationEvidence, CalibrationParams,
    MaskSelection, PatchPlan, PatchSlot,
};
use crate::harness::{Beat, ScenarioMode, TimedEvent, patch_placements};
use crate::post::{PostChainAssets, camera_post_components, mask_asset_path};

/// The calibration scene camera's pinned vertical field of view (45 degrees).
/// The lane's geometry (frame extents at the wall, patch placement, the area
/// cap's fit) is derived from this value; changing it changes the lane.
const CALIBRATION_FOV: f32 = core::f32::consts::FRAC_PI_4;

/// Distance from the camera to the wall plane, in world units.
const WALL_DISTANCE: f32 = 5.0;

/// How far the patch sits toward the camera from the wall plane, in world
/// units: enough separation that depth ordering is unambiguous at the lane's
/// near plane, far less than any distance a capture pixel could resolve.
const PATCH_FORWARD: f32 = 0.01;

/// The edge slot's center, as a fraction of the half-extents toward the
/// upper right. 0.75 keeps the largest capped patch fully on screen at the
/// wall plane while clearly leaving the mask's center-weighted core.
const EDGE_SLOT_FRACTION: f32 = 0.75;

/// The bright patch's radiance as a fixed multiple of the current wall
/// level: one knob (`initial_level`/`step.level`) moves wall and patch
/// together, and the patch stays a positive luminance outlier at every
/// level. The level cap (`harness::calibration::LEVEL_MAX`) keeps the
/// multiple finite.
const PATCH_LEVEL_MULTIPLE: f32 = 10.0;

/// The authored exposure in force on the calibration camera
/// (`Exposure::ev100`). Governs the captured brightness on the
/// auto-exposure-off arm; near zero maps the level range directly through
/// the tonemapper.
const AUTHORED_EV100: f32 = 0.0;

/// The wall quad's size, as a multiple of the frame extents at the wall
/// plane: generous overscan so no wall edge can ever enter the frame.
const WALL_OVERSCAN: f32 = 3.0;

/// Camera orders on the calibration lane. All four are distinct because
/// camera order is global; the chip overlay of each target must sort after
/// that target's scene camera so the chip draws over the post-chain output.
const WINDOW_SCENE_ORDER: isize = 0;
const WINDOW_CHIP_ORDER: isize = 1;
const TARGET_SCENE_ORDER: isize = 2;
const TARGET_CHIP_ORDER: isize = 3;

/// Marks the calibration lane's scene cameras (one per target in flight:
/// the offscreen capture target, plus the window on canary runs).
#[derive(Component)]
pub(super) struct CalibrationCamera;

/// Marks the bright-patch entity (the one entity whose transform moves when
/// the plan changes slots).
#[derive(Component)]
pub(super) struct CalibrationPatch;

/// The calibration scene's material handles (spawned at Startup; the
/// per-tick driver repaints the wall level through them).
#[derive(Resource, Default)]
pub(super) struct CalibrationScene {
    wall_material: Option<Handle<StandardMaterial>>,
    patch_material: Option<Handle<StandardMaterial>>,
}

/// Everything [`spawn_calibration_scene`] needs, gathered as one system
/// parameter so the system call stays a single argument. Only meaningful on
/// the calibration lane; the system gates on the scenario mode first.
#[derive(SystemParam)]
pub(super) struct SceneSpawnContext<'w, 's> {
    commands: Commands<'w, 's>,
    mode: Res<'w, RunMode>,
    state: Res<'w, HarnessState>,
    capture: Res<'w, super::CaptureTarget>,
    /// Present exactly on the calibration lane (`GamePostChainPlugin` is
    /// added there and nowhere else); `None` makes the spawn system a no-op
    /// on the other lanes instead of failing param validation and panicking
    /// the run.
    masks: Option<Res<'w, PostChainAssets>>,
    meshes: ResMut<'w, Assets<Mesh>>,
    materials: ResMut<'w, Assets<StandardMaterial>>,
}

/// Spawn the calibration lane's world content: cameras (scene + chip overlay
/// per target), wall, bright patch, and the material-handle resource. A
/// no-op on every other lane, which never build the post-chain plugins this
/// scene's cameras require.
pub(super) fn setup_calibration_scene(mut ctx: SceneSpawnContext) {
    let Some(masks) = ctx.masks.as_ref() else {
        return;
    };
    if ctx.state.scenario.mode != ScenarioMode::Calibration {
        return;
    }
    let params = ctx
        .state
        .scenario
        .calibration
        .expect("calibration mode carries its params (parse_scenario enforces the section)");
    let mask = selected_mask(masks, params.mask);
    let target = ctx
        .capture
        .0
        .clone()
        .expect("capture target exists (setup_harness_scene ran before this system)");
    spawn_cameras(&mut ctx, mask, target, params.auto_exposure);
    spawn_wall_and_patch(&mut ctx, params);
}

/// The mask handle the scenario's selection binds on the camera.
fn selected_mask(masks: &PostChainAssets, selection: MaskSelection) -> Handle<Image> {
    match selection {
        MaskSelection::CenterWeighted => masks.metering_mask.clone(),
        MaskSelection::Uniform => masks.uniform_mask.clone(),
    }
}

/// Spawn the scene camera and chip overlay camera for the offscreen capture
/// target; canary runs mirror the same pair onto the primary window so the
/// onscreen capture shows the same post-chain output with its chip. Both
/// cameras of a pair draw the same target and sort by the global orders
/// (`TARGET_CHIP_ORDER` after `TARGET_SCENE_ORDER`, and likewise for the
/// window), so the chip draws over the post-chain output.
fn spawn_cameras(
    ctx: &mut SceneSpawnContext,
    mask: Handle<Image>,
    target: Handle<Image>,
    auto_exposure: bool,
) {
    let (tonemapping, vignette, auto) = camera_post_components(mask.clone());
    ctx.commands.spawn((
        chip_overlay_camera(TARGET_CHIP_ORDER),
        RenderTarget::Image(target.clone().into()),
    ));
    let scene = scene_camera(
        RenderTarget::Image(target.into()),
        TARGET_SCENE_ORDER,
        tonemapping,
        vignette,
    );
    spawn_scene_camera(&mut ctx.commands, scene, auto_exposure.then_some(auto));
    if *ctx.mode == RunMode::Canary {
        let (tonemapping, vignette, auto) = camera_post_components(mask);
        ctx.commands.spawn((
            chip_overlay_camera(WINDOW_CHIP_ORDER),
            RenderTarget::default(),
        ));
        let scene = scene_camera(
            RenderTarget::default(),
            WINDOW_SCENE_ORDER,
            tonemapping,
            vignette,
        );
        spawn_scene_camera(&mut ctx.commands, scene, auto_exposure.then_some(auto));
    }
}

/// Spawn one scene camera, binding the auto-exposure component exactly when
/// the scenario's arm is on: bevy's only auto-exposure switch is the
/// component's presence, so the off arm binds nothing. (`Option` is not a
/// bundle component in bevy 0.19, so the conditional is in the spawn, not in
/// the bundle.)
fn spawn_scene_camera(
    commands: &mut Commands,
    scene: impl bevy::ecs::bundle::Bundle,
    auto_exposure: Option<AutoExposure>,
) {
    match auto_exposure {
        Some(auto) => commands.spawn((scene, auto)),
        None => commands.spawn(scene),
    };
}

/// One calibration scene camera: the pinned projection, the authored
/// exposure, and the real post chain's tonemapping and vignette (the
/// auto-exposure component is bound separately, exactly when the scenario's
/// arm is on). HDR is authored in both arms so the on/off comparison changes
/// only the exposure source.
fn scene_camera(
    target: RenderTarget,
    order: isize,
    tonemapping: Tonemapping,
    vignette: Vignette,
) -> impl bevy::ecs::bundle::Bundle {
    (
        Camera {
            order,
            ..Camera::default()
        },
        Camera3d::default(),
        Hdr,
        Exposure {
            ev100: AUTHORED_EV100,
        },
        Projection::from(PerspectiveProjection {
            fov: CALIBRATION_FOV,
            ..PerspectiveProjection::default()
        }),
        Msaa::Off,
        target,
        CalibrationCamera,
        tonemapping,
        vignette,
        Transform::default(),
    )
}

/// One chip overlay camera: plain 2d, drawing over whatever the target
/// already holds, after its target's scene camera by order. The caller
/// appends the target component: the offscreen overlay binds the capture
/// target, the canary window overlay the primary window.
///
/// The overlay is carried by `output_mode`, not by `clear_color`. Bevy
/// finishes every camera with a full-frame blit of that camera's own
/// intermediate texture onto the render target, and the default write
/// (`blend_state: None`) replaces the target's content outright — a camera
/// with only `ClearColorConfig::None` still paints its whole intermediate
/// (chip plus whatever the intermediate held) over the scene camera's
/// output. Alpha blending makes that final blit composite the chip's opaque
/// pixels over the scene while the untouched (alpha-zero) rest of the
/// overlay leaves the scene exactly as the scene camera wrote it. Both
/// clear configs stay `None` so neither the overlay's intermediate nor the
/// target is ever cleared by this camera; the scene camera owns the
/// target's clear.
fn chip_overlay_camera(order: isize) -> impl bevy::ecs::bundle::Bundle {
    (chip_overlay_camera_config(order), Camera2d, Msaa::Off)
}

/// The overlay camera's [`Camera`] component: the order, no clears anywhere
/// in the view, and an alpha-blended final write. Split from
/// [`chip_overlay_camera`] so the render-critical configuration is directly
/// unit-testable.
fn chip_overlay_camera_config(order: isize) -> Camera {
    Camera {
        order,
        clear_color: ClearColorConfig::None,
        output_mode: CameraOutputMode::Write {
            blend_state: Some(BlendState::ALPHA_BLENDING),
            clear_color: ClearColorConfig::None,
        },
        ..Camera::default()
    }
}

/// Spawn the wall and the bright patch (both emissive-only quads at the wall
/// plane) and record their material handles for the per-tick driver.
fn spawn_wall_and_patch(ctx: &mut SceneSpawnContext, params: CalibrationParams) {
    let (width, height) = frame_extents();
    let side = patch_side(params.patch_area_fraction, width, height);
    let wall = ctx
        .meshes
        .add(quad_mesh(width * WALL_OVERSCAN, height * WALL_OVERSCAN));
    let patch = ctx.meshes.add(quad_mesh(side, side));
    let wall_material = ctx.materials.add(level_material(params.initial_level));
    let patch_material = ctx
        .materials
        .add(level_material(params.initial_level * PATCH_LEVEL_MULTIPLE));
    ctx.commands.spawn((
        Mesh3d(wall),
        MeshMaterial3d(wall_material.clone()),
        Transform::from_xyz(0.0, 0.0, -WALL_DISTANCE),
    ));
    ctx.commands.spawn((
        CalibrationPatch,
        Mesh3d(patch),
        MeshMaterial3d(patch_material.clone()),
        Transform::from_translation(patch_translation(PatchSlot::Center)),
    ));
    ctx.commands.insert_resource(CalibrationScene {
        wall_material: Some(wall_material),
        patch_material: Some(patch_material),
    });
}

/// An emissive-only surface material: black base color (the scene has no
/// lights, so the lit contribution is zero) and the level as linear
/// radiance.
fn level_material(level: f32) -> StandardMaterial {
    StandardMaterial {
        base_color: Color::BLACK,
        emissive: level_emissive(level),
        ..StandardMaterial::default()
    }
}

/// The linear emissive one light level renders at: `level` on each color
/// channel, alpha at 1.0. The alpha matters: the pbr shader multiplies the
/// emissive term by `mix(1.0, view.exposure, emissive.a)`, so alpha 1.0
/// applies the camera's authored exposure to the level exactly as authored —
/// any other alpha would re-weight that mix and skew the luminance the lane
/// measures.
fn level_emissive(level: f32) -> LinearRgba {
    LinearRgba::rgb(level, level, level)
}

/// A quad in the XY plane facing +Z (toward the calibration camera),
/// centered on its transform, `width` x `height` world units.
fn quad_mesh(width: f32, height: f32) -> Mesh {
    let (hw, hh) = (width / 2.0, height / 2.0);
    let mut mesh = Mesh::new(
        PrimitiveTopology::TriangleList,
        RenderAssetUsages::default(),
    );
    mesh.insert_attribute(
        Mesh::ATTRIBUTE_POSITION,
        vec![
            [-hw, -hh, 0.0],
            [hw, -hh, 0.0],
            [-hw, hh, 0.0],
            [hw, hh, 0.0],
        ],
    );
    mesh.insert_attribute(Mesh::ATTRIBUTE_NORMAL, vec![[0.0, 0.0, 1.0]; 4]);
    mesh.insert_indices(Indices::U32(vec![0, 1, 2, 2, 1, 3]));
    mesh
}

/// The frame's world extent at the wall plane for the pinned camera
/// geometry (width, height).
fn frame_extents() -> (f32, f32) {
    // Through `UVec2::as_vec2` like every other dimension-to-float conversion
    // in this crate; the resolution constants are exactly representable.
    let extent = UVec2::new(CAPTURE_W, CAPTURE_H).as_vec2();
    frame_extents_at_wall(CALIBRATION_FOV, WALL_DISTANCE, extent.x / extent.y)
}

/// Pure frame-extent math: a perspective camera at `distance` from a plane,
/// vertical field of view `fov`, and the given width/height aspect, sees
/// `2·distance·tan(fov/2)` of the plane vertically.
fn frame_extents_at_wall(fov: f32, distance: f32, aspect: f32) -> (f32, f32) {
    let height = 2.0 * distance * (fov / 2.0).tan();
    (height * aspect, height)
}

/// The patch's square side that covers exactly `fraction` of the frame area
/// at the wall plane.
fn patch_side(fraction: f32, width: f32, height: f32) -> f32 {
    (fraction * width * height).sqrt()
}

/// The patch center for a slot, in the wall plane: center slot on the
/// optical axis, edge slot at [`EDGE_SLOT_FRACTION`] of the half-extents
/// toward the upper right.
fn slot_center(slot: PatchSlot, width: f32, height: f32) -> (f32, f32) {
    match slot {
        PatchSlot::Center => (0.0, 0.0),
        PatchSlot::Edge => (
            EDGE_SLOT_FRACTION * width / 2.0,
            EDGE_SLOT_FRACTION * height / 2.0,
        ),
    }
}

/// The patch's world translation for a slot (at the wall plane, just in
/// front of it).
fn patch_translation(slot: PatchSlot) -> Vec3 {
    let (width, height) = frame_extents();
    let (x, y) = slot_center(slot, width, height);
    Vec3::new(x, y, -WALL_DISTANCE + PATCH_FORWARD)
}

/// The slot a plan occupies on `tick`: fixed plans never move; a move plan
/// sits at the edge from its pinned tick on.
fn patch_slot_at(plan: PatchPlan, tick: u64) -> PatchSlot {
    match plan {
        PatchPlan::FixedCenter => PatchSlot::Center,
        PatchPlan::FixedEdge => PatchSlot::Edge,
        PatchPlan::CenterThenEdge { at_tick } => {
            if tick >= at_tick {
                PatchSlot::Edge
            } else {
                PatchSlot::Center
            }
        }
    }
}

/// The wall level on `tick`: the initial level until the step tick, the
/// step level from it on.
fn wall_level(params: &CalibrationParams, tick: u64) -> f32 {
    if tick >= params.step.tick {
        params.step.level
    } else {
        params.initial_level
    }
}

/// Apply this tick's calibration dynamics: the wall level, the patch's
/// radiance and placement. Runs with the pre-drive tick — the same update
/// the chip is painted for that tick — so a capture pinned at tick T shows
/// tick T's level, slot, and chip code together. Idempotent per tick: every
/// write is the absolute state at `tick`, never a delta.
pub(super) fn drive_calibration(
    readiness: Res<Readiness>,
    present: Res<PresentGate>,
    state: Res<HarnessState>,
    scene: Res<CalibrationScene>,
    mut materials: ResMut<Assets<StandardMaterial>>,
    mut patches: Query<&mut Transform, With<CalibrationPatch>>,
) {
    let readiness = readiness.into_inner();
    let present = present.into_inner();
    let state = state.into_inner();
    let scene = scene.into_inner();
    if !drive_allowed(*readiness, present, state)
        || state.scenario.mode != ScenarioMode::Calibration
    {
        return;
    }
    let params = state
        .scenario
        .calibration
        .expect("calibration mode carries its params (parse_scenario enforces the section)");
    let tick = state.tick;
    let mut patch = patches
        .single_mut()
        .expect("the calibration scene spawned exactly one patch (Startup)");
    apply_tick_dynamics(&mut materials, scene, &mut patch, &params, tick);
}

/// The scene's state at `tick`: the wall and patch radiance and the patch's
/// slot. Split from [`drive_calibration`] so the per-tick dynamics are pure
/// and directly unit-testable.
fn apply_tick_dynamics(
    materials: &mut Assets<StandardMaterial>,
    scene: &CalibrationScene,
    patch: &mut Transform,
    params: &CalibrationParams,
    tick: u64,
) {
    let level = wall_level(params, tick);
    let wall = scene
        .wall_material
        .as_ref()
        .expect("the calibration scene spawned its wall material (Startup)");
    materials
        .get_mut(wall)
        .expect("wall material exists")
        .emissive = level_emissive(level);
    let patch_material = scene
        .patch_material
        .as_ref()
        .expect("the calibration scene spawned its patch material (Startup)");
    materials
        .get_mut(patch_material)
        .expect("patch material exists")
        .emissive = level_emissive(level * PATCH_LEVEL_MULTIPLE);
    patch.translation = patch_translation(patch_slot_at(params.patch, tick));
}

/// Everything [`record_calibration_evidence`] needs, gathered as one system
/// parameter so the system call stays a single argument. Only meaningful on
/// the calibration lane; the system gates on the scenario mode first.
#[derive(SystemParam)]
pub(super) struct EvidenceContext<'w, 's> {
    readiness: Res<'w, Readiness>,
    present: Res<'w, PresentGate>,
    state: ResMut<'w, HarnessState>,
    masks: Option<Res<'w, PostChainAssets>>,
    server: Res<'w, AssetServer>,
    images: Res<'w, Assets<Image>>,
    cameras:
        Query<'w, 's, (&'static Exposure, Option<&'static AutoExposure>), With<CalibrationCamera>>,
}

/// Record the calibration run's setup evidence exactly once: when the
/// readiness boundary has passed and the selected metering-mask asset has
/// actually loaded (a failed load fails the run; a still-loading mask keeps
/// waiting, and the `max_frames` deadline bounds that wait as for any beat).
/// Before this runs, the beat requester refuses to pin captures
/// (`state::beat_requests_allowed`), so the evidence precedes every sample.
pub(super) fn record_calibration_evidence(ctx: EvidenceContext) {
    let EvidenceContext {
        readiness,
        present,
        state,
        masks,
        server,
        images,
        cameras,
    } = ctx;
    let readiness = readiness.into_inner();
    let present = present.into_inner();
    let state = state.into_inner();
    let Some(masks) = masks else {
        return;
    };
    let masks = masks.into_inner();
    let server = server.into_inner();
    let images = images.into_inner();
    if !drive_allowed(*readiness, present, state)
        || state.scenario.mode != ScenarioMode::Calibration
        || state.calibration_evidence_recorded
    {
        return;
    }
    let params = state
        .scenario
        .calibration
        .expect("calibration mode carries its params (parse_scenario enforces the section)");
    let mask = selected_mask(masks, params.mask);
    match server.load_state(mask.id()) {
        LoadState::Failed(err) => fail_scenario(
            state,
            format!(
                "metering mask `{}` failed to load: {err}",
                mask_asset_path(params.mask)
            ),
        ),
        LoadState::Loading | LoadState::NotLoaded => {}
        LoadState::Loaded => {
            let image = images
                .get(&mask)
                .expect("a loaded mask asset is in the assets map");
            let evidence = setup_evidence(&params, &state.scenario.beats, image, &cameras);
            let tick = state.tick;
            let frame = state.frame;
            state.events.push(TimedEvent::Calibration {
                tick,
                frame,
                evidence,
            });
            state
                .checkpoints
                .push("calibration evidence recorded".to_owned());
            state.calibration_evidence_recorded = true;
        }
    }
}

/// Assemble the report's setup evidence from the runtime truth: the loaded
/// mask bytes (hashed, not path-named), the auto-exposure component as
/// bound on the camera, the authored exposure, the plan, the levels, and
/// the beat ticks as the pinned sample ticks (ascending, the order the
/// capture lane requests them in).
fn setup_evidence(
    params: &CalibrationParams,
    beats: &[Beat],
    image: &Image,
    cameras: &Query<(&Exposure, Option<&AutoExposure>), With<CalibrationCamera>>,
) -> CalibrationEvidence {
    let (exposure, auto) = cameras
        .single()
        .expect("the calibration lane spawned exactly one scene camera (Startup)");
    let mut sample_ticks: Vec<u64> = beats.iter().map(|beat| beat.tick).collect();
    sample_ticks.sort_unstable();
    CalibrationEvidence {
        mask: params.mask,
        mask_sha256: sha256_hex(image.data.as_deref().unwrap_or_default()),
        auto_exposure: AutoExposureEvidence {
            enabled: auto.is_some(),
            settings: auto.map(|auto| AutoExposureSettings {
                range_min: *auto.range.start(),
                range_max: *auto.range.end(),
                filter_min: *auto.filter.start(),
                filter_max: *auto.filter.end(),
                speed_brighten: auto.speed_brighten,
                speed_darken: auto.speed_darken,
            }),
        },
        authored_exposure_ev100: exposure.ev100,
        patch_area_fraction: params.patch_area_fraction,
        patch_placements: patch_placements(params.patch),
        initial_level: params.initial_level,
        step_tick: params.step.tick,
        step_level: params.step.level,
        sample_ticks,
    }
}

/// Lowercase-hex sha2-256 of `bytes`: the mask identity the report carries.
fn sha256_hex(bytes: &[u8]) -> String {
    let digest = Sha256::digest(bytes);
    let mut out = String::with_capacity(2 * digest.len());
    for byte in digest {
        let _ = write!(out, "{byte:02x}");
    }
    out
}

#[cfg(test)]
mod tests {
    use bevy::math::Vec2;

    use super::{
        AUTHORED_EV100, EDGE_SLOT_FRACTION, PATCH_FORWARD, PATCH_LEVEL_MULTIPLE, WALL_DISTANCE,
        apply_tick_dynamics, frame_extents, frame_extents_at_wall, level_material, patch_side,
        patch_slot_at, patch_translation, quad_mesh, sha256_hex, slot_center, wall_level,
    };
    use crate::harness::calibration::{
        LuminanceStep, PATCH_AREA_FRACTION_MAX, patch_placements as protocol_placements,
    };
    use crate::harness::{CalibrationParams, MaskSelection, PatchPlan, PatchSlot};

    /// The pinned geometry's frame extents: 45 vertical degrees at distance
    /// 5 sees `10·tan(22.5°)` vertically and 16/9 of that horizontally.
    #[test]
    fn frame_extents_match_the_pinned_camera_geometry() {
        let (width, height) = frame_extents();
        let expected_height = 2.0 * WALL_DISTANCE * (core::f32::consts::FRAC_PI_4 / 2.0).tan();
        let expected_width = expected_height * 16.0 / 9.0;
        assert!((height - expected_height).abs() < 1e-4);
        assert!((width - expected_width).abs() < 1e-4);
        // The pure function agrees with the pinned-constant wrapper.
        let (pw, ph) =
            frame_extents_at_wall(core::f32::consts::FRAC_PI_4, WALL_DISTANCE, 16.0 / 9.0);
        assert_eq!((width, height), (pw, ph));
    }

    #[test]
    fn patch_side_covers_exactly_the_authored_area_fraction() {
        let (width, height) = frame_extents();
        let side = patch_side(0.02, width, height);
        let covered = (side * side) / (width * height);
        assert!((covered - 0.02).abs() < 1e-6, "covered {covered}");
    }

    #[test]
    fn the_area_cap_keeps_the_patch_fully_on_screen_in_the_edge_slot() {
        // The cap's justification: at PATCH_AREA_FRACTION_MAX the largest
        // patch in the edge slot still fits, with margin to spare.
        let (width, height) = frame_extents();
        let side = patch_side(PATCH_AREA_FRACTION_MAX, width, height);
        let (ex, ey) = slot_center(PatchSlot::Edge, width, height);
        assert!(ex + side / 2.0 < width / 2.0, "edge slot stays inside x");
        assert!(ey + side / 2.0 < height / 2.0, "edge slot stays inside y");
        // And fractions below the cap (what scenarios may author) fit too.
        let side = patch_side(PATCH_AREA_FRACTION_MAX / 2.0, width, height);
        assert!(ex + side / 2.0 < width / 2.0);
        assert!(ey + side / 2.0 < height / 2.0);
    }

    #[test]
    fn edge_slot_sits_where_documented() {
        let (width, height) = frame_extents();
        let (ex, ey) = slot_center(PatchSlot::Edge, width, height);
        assert!((ex - EDGE_SLOT_FRACTION * width / 2.0).abs() < 1e-6);
        assert!((ey - EDGE_SLOT_FRACTION * height / 2.0).abs() < 1e-6);
        assert_eq!(slot_center(PatchSlot::Center, width, height), (0.0, 0.0));
    }

    #[test]
    fn patch_slots_follow_the_plan_per_tick() {
        let plan = PatchPlan::CenterThenEdge { at_tick: 60 };
        assert_eq!(patch_slot_at(plan, 0), PatchSlot::Center);
        assert_eq!(patch_slot_at(plan, 59), PatchSlot::Center);
        assert_eq!(patch_slot_at(plan, 60), PatchSlot::Edge, "move at the pin");
        assert_eq!(patch_slot_at(plan, 61), PatchSlot::Edge);
        assert_eq!(
            patch_slot_at(PatchPlan::FixedCenter, 120),
            PatchSlot::Center
        );
        assert_eq!(patch_slot_at(PatchPlan::FixedEdge, 0), PatchSlot::Edge);
    }

    #[test]
    fn the_patch_holds_the_same_area_in_both_slots() {
        // Equal-area placement: only the translation differs between slots.
        let center = patch_translation(PatchSlot::Center);
        let edge = patch_translation(PatchSlot::Edge);
        assert!(
            (center.z - edge.z).abs() < f32::EPSILON,
            "both slots sit at the wall plane"
        );
        assert!(
            edge.x > center.x && edge.y > center.y,
            "edge is upper right"
        );
        let step = Vec2::new(edge.x - center.x, edge.y - center.y);
        assert!(step.length() > 0.0, "the slots are distinct positions");
        assert!(
            (center.z - (-WALL_DISTANCE + PATCH_FORWARD)).abs() < 1e-6,
            "the patch floats just in front of the wall"
        );
    }

    #[test]
    fn wall_level_steps_at_the_step_tick() {
        let params = CalibrationParams {
            initial_level: 0.18,
            step: LuminanceStep {
                tick: 30,
                level: 0.36,
            },
            patch_area_fraction: 0.02,
            patch: PatchPlan::CenterThenEdge { at_tick: 60 },
            mask: MaskSelection::CenterWeighted,
            auto_exposure: true,
        };
        assert!((wall_level(&params, 0) - 0.18).abs() < 1e-6);
        assert!((wall_level(&params, 29) - 0.18).abs() < 1e-6);
        assert!(
            (wall_level(&params, 30) - 0.36).abs() < 1e-6,
            "the step lands on its tick"
        );
        assert!((wall_level(&params, 31) - 0.36).abs() < 1e-6);
    }

    #[test]
    fn level_material_renders_the_level_as_exposure_mixed_emissive() {
        // Black base (no lights, so the lit term is zero) and the level as
        // uniform linear radiance with alpha 1.0 — the shader applies the
        // view exposure to the emissive term exactly as authored.
        let material = level_material(0.25);
        assert_eq!(material.base_color, bevy::color::Color::BLACK);
        for (name, channel) in [
            ("red", material.emissive.red),
            ("green", material.emissive.green),
            ("blue", material.emissive.blue),
        ] {
            assert!((channel - 0.25).abs() < 1e-6, "{name} channel {channel}");
        }
        assert!((material.emissive.alpha - 1.0).abs() < f32::EPSILON);
    }

    #[test]
    fn dynamics_apply_the_tick_level_slot_and_patch_multiple() {
        // The per-tick scene state the driver applies, checked against the
        // scenario's parameters tick by tick: the wall level until and from
        // the step tick, the patch radiance at its fixed multiple, and the
        // patch slot until and from the move tick.
        let params = CalibrationParams {
            initial_level: 0.18,
            step: LuminanceStep {
                tick: 30,
                level: 0.36,
            },
            patch_area_fraction: 0.02,
            patch: PatchPlan::CenterThenEdge { at_tick: 60 },
            mask: MaskSelection::CenterWeighted,
            auto_exposure: true,
        };
        let mut materials = bevy::asset::Assets::<bevy::pbr::StandardMaterial>::default();
        let scene = super::CalibrationScene {
            wall_material: Some(materials.add(level_material(params.initial_level))),
            patch_material: Some(
                materials.add(level_material(params.initial_level * PATCH_LEVEL_MULTIPLE)),
            ),
        };
        let mut patch = bevy::transform::components::Transform::default();
        let wall = scene.wall_material.as_ref().expect("wall handle");
        let patch_material = scene.patch_material.as_ref().expect("patch handle");
        let wall_level_at = |materials: &bevy::asset::Assets<bevy::pbr::StandardMaterial>,
                             handle| {
            materials
                .get(handle)
                .expect("wall material exists")
                .emissive
                .red
        };
        let patch_level_at = |materials: &bevy::asset::Assets<bevy::pbr::StandardMaterial>,
                              handle| {
            materials
                .get(handle)
                .expect("patch material exists")
                .emissive
                .red
        };

        // Before both pinned ticks: initial level, its multiple, centered.
        apply_tick_dynamics(&mut materials, &scene, &mut patch, &params, 29);
        assert!((wall_level_at(&materials, wall) - 0.18).abs() < 1e-6);
        assert!((patch_level_at(&materials, patch_material) - 1.8).abs() < 1e-5);
        assert_eq!(patch.translation, patch_translation(PatchSlot::Center));

        // The step tick moves the wall to the step level (the patch tracks
        // at its multiple); the patch is still centered before its move.
        apply_tick_dynamics(&mut materials, &scene, &mut patch, &params, 30);
        assert!((wall_level_at(&materials, wall) - 0.36).abs() < 1e-6);
        assert!((patch_level_at(&materials, patch_material) - 3.6).abs() < 1e-5);
        assert_eq!(patch.translation, patch_translation(PatchSlot::Center));

        // The move tick relocates the patch to the edge slot and rescales
        // nothing; every write is the absolute tick state, so reapplying an
        // earlier tick restores that tick's placement exactly.
        apply_tick_dynamics(&mut materials, &scene, &mut patch, &params, 61);
        assert_eq!(patch.translation, patch_translation(PatchSlot::Edge));
        assert!((wall_level_at(&materials, wall) - 0.36).abs() < 1e-6);
        apply_tick_dynamics(&mut materials, &scene, &mut patch, &params, 30);
        assert_eq!(patch.translation, patch_translation(PatchSlot::Center));
    }

    #[test]
    fn the_evidence_protocol_placements_are_the_scene_placements() {
        // The report's placement list and the scene driver agree tick by
        // tick: each recorded (tick, slot) pair matches the scene slot at
        // that tick, and the placements are in tick order.
        for plan in [
            PatchPlan::FixedCenter,
            PatchPlan::FixedEdge,
            PatchPlan::CenterThenEdge { at_tick: 45 },
        ] {
            let placements = protocol_placements(plan);
            let mut last = 0;
            for placement in &placements {
                assert!(placement.tick >= last, "placements ascend");
                last = placement.tick;
                assert_eq!(
                    patch_slot_at(plan, placement.tick),
                    placement.slot,
                    "plan {plan:?} at tick {}",
                    placement.tick
                );
            }
        }
    }

    #[test]
    fn sha256_hex_known_vectors() {
        assert_eq!(
            sha256_hex(b""),
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        );
        assert_eq!(
            sha256_hex(b"abc"),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        );
    }

    #[test]
    fn quad_mesh_is_a_centered_z_facing_quad() {
        use bevy::mesh::Mesh;

        let mesh = quad_mesh(2.0, 1.0);
        let positions = mesh
            .attribute(Mesh::ATTRIBUTE_POSITION)
            .expect("positions exist")
            .as_float3()
            .expect("positions are float3");
        assert_eq!(positions.len(), 4);
        for [x, y, z] in positions {
            assert!(
                x.abs() <= 1.0 && y.abs() <= 0.5,
                "vertex ({x}, {y}) centered"
            );
            assert!(z.abs() < f32::EPSILON);
        }
        let bevy::mesh::Indices::U32(indices) = mesh.indices().expect("indices exist") else {
            panic!("indices are u32");
        };
        assert_eq!(indices.as_slice(), &[0, 1, 2, 2, 1, 3]);
        let normals = mesh
            .attribute(Mesh::ATTRIBUTE_NORMAL)
            .expect("normals exist")
            .as_float3()
            .expect("normals are float3");
        assert!(normals.iter().all(|n| {
            n[0].abs() < f32::EPSILON
                && n[1].abs() < f32::EPSILON
                && (n[2] - 1.0).abs() < f32::EPSILON
        }));
    }

    #[test]
    fn authored_exposure_constant_is_the_documented_value() {
        assert!(AUTHORED_EV100.abs() < f32::EPSILON);
    }

    #[test]
    fn the_chip_overlay_camera_blends_instead_of_replacing_the_target() {
        // The overlay composite lives in the camera's output mode: bevy
        // finishes every camera with a full-frame blit of its own
        // intermediate onto the target, and the default write (blend None)
        // replaces the target outright — which is the defect this lane
        // shipped (the overlay erased the scene every frame, leaving clear
        // color plus chip). The pinned configuration: no clear anywhere in
        // the view (the scene camera owns the target's clear), and a final
        // write that alpha-blends over the target's existing content.
        for order in [super::TARGET_CHIP_ORDER, super::WINDOW_CHIP_ORDER] {
            let camera = super::chip_overlay_camera_config(order);
            assert_eq!(camera.order, order);
            assert!(
                matches!(camera.clear_color, bevy::camera::ClearColorConfig::None),
                "expected ClearColorConfig::None, got {:?}",
                camera.clear_color
            );
            let bevy::camera::CameraOutputMode::Write {
                blend_state,
                clear_color,
            } = camera.output_mode
            else {
                panic!("the overlay must write (blend) its output, not skip it");
            };
            assert_eq!(
                blend_state,
                Some(bevy::render::render_resource::BlendState::ALPHA_BLENDING)
            );
            assert!(
                matches!(clear_color, bevy::camera::ClearColorConfig::None),
                "expected ClearColorConfig::None, got {clear_color:?}"
            );
        }
    }
}
