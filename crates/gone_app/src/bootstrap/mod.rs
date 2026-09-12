//! Bootstrap plugin for the harness lane (issue #15).
//!
//! This module is the app side of the harness protocol from [`crate::harness`]:
//! the loading presentation until the renderer has actually presented, the
//! input-adapter resource, the frame-code sprite, the report, and a clean
//! self-exit — on both lanes, the capture lane (scenario beats and reads) and
//! the perf lane (wall-clock frame-time sampling, capture-free after the
//! readiness proof). The app runs in one of two capture architectures
//! ([`state::RunMode`]): headless by default — no window, the schedule runner
//! drives updates, the offscreen Image is the only render target — or the
//! `GONE_RENDER_CHECK=1` canary, which additionally opens the real
//! (focused) window, presents the same scene through a second camera, and
//! saves one `.onscreen.png` next to the first beat's PNG.
//!
//! Design notes:
//!
//! * **Real GPU capture, offscreen.** The frame-code chip is a 24x10 [`Sprite`]
//!   rendered into the scene at the capture target's top-left pixel (top band:
//!   tick, bottom band: frame). The harness camera renders into a dedicated
//!   offscreen [`Image`] render target (`RenderTarget::Image`), and beat
//!   captures are [`Screenshot::image`] readbacks of that target handed to a
//!   [`ScreenshotCaptured`] observer, which encodes the PNG. The offscreen
//!   image is the capture source of truth because captures are exactly
//!   1920x1080 regardless of window scale or DPI overrides and their timing
//!   is decoupled from the swapchain and present. In canary mode a second
//!   camera (ordered ahead of the capture camera) presents the same world to
//!   the window, and the run's single onscreen capture is a
//!   [`Screenshot::primary_window()`] readback of the presented frame.
//!   (`Screenshot::primary_window()` works here with
//!   the correct bevy feature set: an earlier probe's all-black captures were
//!   our own feature-selection error, a missing `bevy_sprite_render`, and its
//!   textures needed `RenderAssetUsages::default()` to appear in captures at
//!   all. In headless mode nothing is presented at all because no window
//!   exists; in canary mode the window camera presents the same scene the
//!   capture camera renders.) The runner decodes the PNG's top-left
//!   chip block and asserts it equals the report entry, so the verified pixels
//!   are ones the GPU rendered.
//! * **Canary onscreen capture.** `GONE_RENDER_CHECK=1` (with harness mode)
//!   opens the real window (focused: the window must be ordered in for its
//!   surface to present, and on macOS a background-launched app only gets its
//!   window ordered in by activating) and presents the scene through a window
//!   camera. At the first
//!   beat's request the run also captures the primary window once — both
//!   requests enter the same sync point, so the onscreen readback shows the
//!   same rendered frame as the beat's PNG — and saves it as
//!   `beats/<beat>.onscreen.png` beside the beat PNG. Same save policy as
//!   beat captures: a failure is terminal, naming the beat and the error.
//!   The canary's scenario clock waits for the window's first capturable
//!   frame before it starts: a present probe (one primary-window screenshot
//!   at a time through the gate's single probe slot, the next issued only
//!   after the previous verdict lands, until one comes back rendered)
//!   proves the OS compositor is
//!   accepting the window's presents, because macOS declines a fresh
//!   unfocused window's swapchain drawable until its first composite and a
//!   capture on such a frame arrives as the zeroed readback buffer. Declined
//!   frames count against a hard budget and exhausting it fails the run by
//!   name; the probe is never a silent retry loop. Headless mode has no
//!   onscreen path at all: no window, no present gate, no capture, no file.
//! * **Readiness before the clock.** The scenario clock starts only after
//!   the first capture of the offscreen target lands. That capture is the
//!   readback of a frame the render graph actually executed into the target,
//!   so it is direct evidence the renderer built its device resources and
//!   rendered at least one full frame. On gameplay content the proof request
//!   additionally waits on the game readiness barrier (the `readiness`
//!   ledger plus the rig camera binding, see `gameplay`): the readback that
//!   opens the clock is the first fully provisioned game frame, and a
//!   required asset whose load fails fails the run by name and exits
//!   nonzero, never a placeholder render. Calibration content requests the
//!   proof immediately: the calibration scene renders through the post chain
//!   from startup, so the proof already shows the wall (the chip stays
//!   hidden). Either way, only then does the app print `GONE_READY`, record
//!   tick zero, and make the chip sprite visible (no authored content before
//!   the boundary) — and on the canary the announcement itself waits for the
//!   present gate: the window must have shown one capturable frame before
//!   the run claims readiness or advances the wake, so a locked-screen run
//!   holds at the probe instead of reporting ready with nothing presented.
//!   [`state::drive_allowed`] gates every later step on the same
//!   state, so no scenario tick or input edge is consumed before the boundary.
//! * **Simulation time is the scenario clock.** [`state::ScenarioTime`]
//!   advances by exactly `1 / ticks_per_second` seconds per driven tick,
//!   inside `drive_ticks`, and every hold of the scenario clock (loading,
//!   the canary present gate, the capture freeze) holds it too. Gameplay
//!   temporal consumers read it, never bevy's clocks: bevy's generic `Time`
//!   mirrors `Time<Virtual>` (bevy 0.19 `update_virtual_time`), and engine
//!   temporal render effects — the auto-exposure adaptation rate is
//!   `globals.delta_time`, fed from that same clock by `bevy_render`'s
//!   `prepare_globals_buffer` — keep running on it. The one exception is
//!   the capture freeze: `freeze_engine_time` pauses `Time<Virtual>` while
//!   a beat readback is in flight and unpauses on landing, so the held
//!   frame renders with a zero delta and engine temporal effects freeze
//!   instead of drifting while the readback is late.
//! * **Beats are post-tick state.** The update that captures a beat delivers
//!   the tick's input first (the drive half of the chain, inside the
//!   `ScriptedInput` set), then the game's look systems integrate it, and
//!   only then does the post-drive half run: `paint_driven_chip` repaints
//!   the chip with the just-driven (tick, frame), `request_beat_captures`
//!   pins exactly those numbers and samples the gameplay yaw from the rig's
//!   actual transform, and the screenshot request enters the render queue. A
//!   look action on a capture tick is therefore inside the PNG and inside
//!   the reported yaw sample, not one tick behind them.
//! * **Calibration lane architecture (issue #6 slice B).** The post chain is
//!   Core3d and the chip is Core2d, so the calibration scenario renders its
//!   wall/patch scene through a dedicated `Camera3d` carrying the real chain
//!   (`AgX` tonemapping, vignette, auto exposure through the selected mask)
//!   into the SAME offscreen capture target, and the chip is drawn over the
//!   scene by a plain 2d overlay camera whose final write alpha-blends
//!   (bevy's per-camera output blit replaces the target unless the camera's
//!   `output_mode` blends — see `calibration::chip_overlay_camera`) —
//!   captures stay the executed post-chain output and the chip keeps its
//!   decode contract; the chip never enters the auto-exposure
//!   histogram (it lives on a different view's LDR output). The setup
//!   evidence records the mask identity (sha256 of the loaded asset bytes)
//!   once the asset has loaded, and the beat requester refuses to pin
//!   captures before that ([`state::beat_requests_allowed`]). `calibration`
//!   owns the scene, the evidence recording, and the full reconciliation.
//! * **Beat binding and accounting.** The scenario clock holds while a beat
//!   readback is in flight (bevy captures at most one screenshot per render
//!   target per frame, so exactly one capture is in flight): no tick, no
//!   frame, no adapter step, no paint, and the renderer keeps presenting the
//!   held frame. A beat's screenshot is therefore spawned on the update that
//!   drives its scenario tick with the lane free, and the manifest entry
//!   pins exactly that scripted tick's (tick, frame, request id) at the same
//!   instant it is spawned; the pin can never land on a later tick because
//!   the clock cannot pass the beat's tick while the lane is busy. The
//!   capture therefore always shows the chip code the report claims: request,
//!   entry, and rendered pixels are one atomic step (see
//!   `state::HarnessState::pin_next_beat`), and identical scenarios pin
//!   identical (tick, frame) pairs regardless of readback latency (the
//!   observer honors `GONE_TEST_CAPTURE_DELAY_MS` so tests can prove that
//!   invariant against an artificially slow readback; the chain-level
//!   invariant test runs the real drive path with and without a landing
//!   delay). Requests and captures are separate ledgers; the run completes
//!   only when every scenario beat's PNG is on disk.
//! * **Immediate capture failures.** A failed capture convert/save records a
//!   `TimedEvent::Failure` naming the artifact and the underlying error, writes
//!   the report, and exits nonzero. There is no retry loop.
//! * **`max_frames` deadline.** The scenario's `max_frames` scenario frames
//!   (drive steps; frames the clock spends held under a readback never
//!   consume it) is the run's deadline, not extra patience: when the frame
//!   count reaches it with beats still uncaptured, [`state::fail_at_deadline`]
//!   records every uncaptured beat as missing, and `finish_scan` writes the
//!   report and exits nonzero. A beat scripted past the deadline is a failed
//!   scenario, never a hang. The all-beats-captured path is unchanged
//!   (immediate finish once the settle window after the last capture passes).
//! * **Exit.** After the last capture and a two-frame settle, the app writes
//!   `report.json`, prints `REPORT <path>`, and raises `AppExit::Success`.
//!
//! Module layout: this file owns the plugin and the scene setup; [`drive`]
//! owns the update chain (the drive half in the `ScriptedInput` set, the
//! post-drive half that captures post-tick state); [`capture`] owns the
//! capture receiver and I/O; [`calibration`] owns the calibration lane's
//! scene, evidence recording, and camera reconciliation; [`lifecycle`] owns
//! the stage-B lane's window drives and their native observations; [`state`]
//! owns the scenario run state (counters, beat ledgers, readiness, failure
//! recording, the scenario clock); [`finish`] owns the close (completion
//! scan, the `max_frames` deadline, the report); and the test modules pin the
//! accounting, readiness, and gameplay-drive regressions without needing a
//! renderer.

mod calibration;
mod capture;
mod drive;
mod finish;
mod gameplay;
mod lifecycle;
mod state;

#[cfg(test)]
mod gameplay_tests;
#[cfg(test)]
mod tests;

// The run mode is lib-facing: `run` selects it from the environment and the
// harness plugin inserts it as a resource for the window-only systems.
pub use state::{RunMode, select_run_mode};

use std::path::PathBuf;

use bevy::app::{App, Plugin, Startup, Update};
use bevy::asset::{Assets, Handle, RenderAssetUsages};
use bevy::camera::visibility::Visibility;
use bevy::camera::{Camera, Camera2d, ClearColor, RenderTarget};
use bevy::color::Color;
use bevy::ecs::prelude::{Commands, Entity, Res, ResMut, Resource};
use bevy::ecs::schedule::IntoScheduleConfigs;
use bevy::ecs::system::SystemParam;
use bevy::image::Image;
use bevy::math::{UVec2, Vec2};
use bevy::render::render_resource::{Extent3d, TextureDimension, TextureFormat, TextureUsages};
// `Msaa` lives on the view module in bevy 0.19 (it is a property of the render
// target view, not of a render-resource pipeline object).
use bevy::render::view::Msaa;
use bevy::sprite::{Anchor, Sprite};
use bevy::transform::components::Transform;

use crate::harness::{Content, InputAdapter, Scenario, ScenarioMode, frame};
use crate::player::{LookInputMode, ScriptedInput};
use crate::post::GamePostChainPlugin;

use calibration::{
    CalibrationScene, drive_calibration, record_calibration_evidence, setup_calibration_scene,
};
use capture::{CaptureDelay, on_screenshot_captured};
use drive::{
    drive_ticks, readiness_boundary, register_post_drive_systems, request_present_probe,
    request_readiness_proof,
};
use state::{HarnessState, PresentGate, Readiness};

/// The landed scenario clock, consumed beyond the bootstrap by the player
/// motion slice (the walk's fixed dt source).
pub(crate) use state::ScenarioTime;

/// The frame-code chip texture width: exactly the chip block's width.
const LANE_W: u32 = frame::DIGITS * frame::CELL_W;

/// The frame-code chip texture height: the two chip bands (tick over frame).
const LANE_H: u32 = 2 * frame::CELL_H;

/// The offscreen capture target's width in pixels (matches the window's
/// logical resolution so captures are full-frame at scale factor 1.0).
pub(super) const CAPTURE_W: u32 = 1920;

/// The offscreen capture target's height in pixels.
pub(super) const CAPTURE_H: u32 = 1080;

/// The canary window camera's render order: the presented view draws first.
const WINDOW_CAMERA_ORDER: isize = 0;

/// The offscreen capture camera's render order, distinct from the window
/// camera's so both cameras stay active when both exist (canary mode).
const OFFSCREEN_CAMERA_ORDER: isize = 1;

/// Handle of the frame-code chip texture (created at startup, repainted per tick).
#[derive(Resource, Default)]
struct ChipTexture(Option<Handle<Image>>);

/// The chip sprite entity (spawned hidden at startup, shown at the boundary).
#[derive(Resource, Default)]
struct ChipSprite(Option<Entity>);

/// Handle of the offscreen render target the harness camera draws into.
/// Created once at startup; every screenshot of the run reads back from it.
#[derive(Resource, Default)]
struct CaptureTarget(Option<Handle<Image>>);

/// The capture target's extent in pixels, recorded when the target image is
/// created (`setup_harness_scene` reads it back off the created image). The
/// lifecycle lane's resize observer records it beside the window's new
/// extent; a Copy resource keeps that observer free of the asset store.
#[derive(Resource, Clone, Copy, Debug, Default)]
struct CaptureExtent {
    width: u32,
    height: u32,
}

/// Construct the harness plugin from the harness-mode environment.
pub struct BootstrapPlugin {
    scenario: Scenario,
    out_dir: PathBuf,
    config_hash: String,
    mode: RunMode,
}

impl BootstrapPlugin {
    /// Build the plugin from an already-parsed scenario and the runner's env.
    /// `mode` is the capture architecture selected in `run` (headless or
    /// canary; the normal game never builds this plugin).
    ///
    /// # Panics
    /// Panics without `GONE_OUT_DIR` (the runner always sets it), and on a
    /// perf scenario whose sample window is empty: there is no honest
    /// measurement to fall back to.
    pub fn new(
        scenario: Scenario,
        out_dir: Option<PathBuf>,
        config_hash: String,
        mode: RunMode,
    ) -> Self {
        assert!(
            scenario.mode != ScenarioMode::Perf || scenario.sample_frames != 0,
            "perf scenario `{}` needs a sample_frames window of at least 1 frame",
            scenario.name
        );
        let out_dir = out_dir.expect("GONE_HARNESS requires GONE_OUT_DIR");
        Self {
            scenario,
            out_dir,
            config_hash,
            mode,
        }
    }
}

impl Plugin for BootstrapPlugin {
    fn build(&self, app: &mut App) {
        // The lifecycle lane drives and observes the real window surface, so
        // a headless lifecycle run is a launch misconfiguration and fails
        // here, at plugin build, before any scenario time can run.
        lifecycle::enforce_windowed(self.scenario.mode, self.mode, &self.scenario.name);
        app.insert_resource(self.mode);
        app.init_resource::<Readiness>();
        // The canary holds its scenario clock until the window presents its
        // first capturable frame; a windowless lane has nothing to wait for.
        app.insert_resource(match self.mode {
            RunMode::Canary => PresentGate::canary(),
            RunMode::Headless | RunMode::Normal => PresentGate::automatic(),
        });
        app.init_resource::<ChipTexture>();
        app.init_resource::<ChipSprite>();
        app.init_resource::<CaptureTarget>();
        app.init_resource::<CalibrationScene>();
        if self.scenario.mode == ScenarioMode::Calibration {
            // The calibration lane's cameras bind the checked-in metering
            // masks and need the auto-exposure render graph: the only
            // harness lane that builds the game's post-chain plugins here.
            app.add_plugins(GamePostChainPlugin);
        }
        // Gameplay content boots the real game into the harness app (post
        // chain, stasis scene, player look) before anything else wires
        // against it; the calibration content is the app as it has always
        // been, touched by nothing here.
        if self.scenario.content == Content::Gameplay {
            // A canary run's window never takes focus, so the device-cursor
            // policy would never arm look on an unattended run: the canary
            // arms the scripted pathway explicitly. Headless runs have no
            // cursor to gate on and keep the device default; the look
            // plugin's init_resource preserves the mode inserted here.
            if self.mode == RunMode::Canary {
                app.insert_resource(LookInputMode::Scripted);
            }
            gameplay::wire(app);
        }
        let adapter = InputAdapter::with_actions(
            self.scenario.actions.clone(),
            self.scenario.ticks_per_second,
        );
        app.insert_resource(HarnessState::new(
            self.scenario.clone(),
            self.out_dir.clone(),
            self.config_hash.clone(),
            adapter,
        ));
        app.insert_resource(ScenarioTime::new(self.scenario.ticks_per_second));
        // The latency-proof knob parses at launch: a bad value fails before
        // the app builds instead of failing the first capture mid-run.
        app.insert_resource(CaptureDelay::from_env());
        app.add_observer(on_screenshot_captured);
        if self.scenario.content == Content::Gameplay {
            app.add_systems(Startup, gameplay::setup_gameplay_scene);
            gameplay::register_update_systems(app);
        } else {
            app.add_systems(
                Startup,
                // The calibration scene spawns after the capture target
                // exists: its cameras render into that target.
                (setup_harness_scene, setup_calibration_scene).chain(),
            );
            app.add_systems(
                Update,
                (
                    request_readiness_proof,
                    readiness_boundary,
                    // Evidence precedes the beat requester: the gate
                    // (`state::beat_requests_allowed`) lifts the same update
                    // the mask identity is recorded, so no capture can
                    // precede it.
                    record_calibration_evidence,
                    request_present_probe,
                    // Calibration dynamics apply the tick about to be driven —
                    // the same tick the post-drive half paints the chip for
                    // and pins.
                    drive_calibration,
                    drive_ticks,
                )
                    .chain()
                    .in_set(ScriptedInput),
            );
            register_post_drive_systems(app);
            // The lifecycle lane's window drives and observers join the
            // shared chain: the drive before `drive_ticks` (inside the
            // scripted-input set), the observers in the post-drive half.
            if self.scenario.mode == ScenarioMode::Lifecycle {
                lifecycle::register(app);
            }
        }
    }
}

/// Everything [`setup_harness_scene`] needs, gathered as one system
/// parameter so the startup system stays a single argument (the same
/// pattern as the driving systems' [`Kernel`]).
#[derive(SystemParam)]
struct HarnessSceneContext<'w, 's> {
    commands: Commands<'w, 's>,
    mode: Res<'w, RunMode>,
    state: Res<'w, HarnessState>,
    chip: ResMut<'w, ChipTexture>,
    sprite: ResMut<'w, ChipSprite>,
    capture: ResMut<'w, CaptureTarget>,
    images: ResMut<'w, Assets<Image>>,
}

/// The loading scene: dark clear, one Camera2d rendering into the offscreen
/// capture target (MSAA off so the chip lattice stays pixel-crisp in captures),
/// a canary window camera presenting the same world when this run opens a
/// window, and the chip sprite spawned hidden at the target's top-left — it
/// becomes visible only at the readiness boundary.
///
/// The calibration lane spawns none of those cameras: its scene camera must
/// carry the Core3d post chain and its chip overlay must alpha-blend (see
/// `calibration::chip_overlay_camera`), and a second opaque camera writing
/// the same target would replace the other camera's output every frame. The
/// capture target itself is still created here — both lanes' cameras render
/// into it, and every screenshot of the run reads it back.
fn setup_harness_scene(mut ctx: HarnessSceneContext) {
    ctx.commands
        .insert_resource(ClearColor(Color::srgb(0.011, 0.011, 0.011)));
    let handle = capture_target_image(&mut ctx.images);
    if ctx.state.scenario.mode != ScenarioMode::Calibration {
        spawn_capture_camera(&mut ctx.commands, handle.clone());
        if *ctx.mode == RunMode::Canary {
            spawn_window_camera(&mut ctx.commands);
        }
    }
    // Record the extent the target was actually created at: the resize
    // observer reads this resource, not the asset store.
    let extent = ctx
        .images
        .get(&handle)
        .map_or(CaptureExtent::default(), |image| CaptureExtent {
            width: image.width(),
            height: image.height(),
        });
    ctx.commands.insert_resource(extent);
    ctx.capture.0 = Some(handle);
    let (handle, entity) = spawn_chip_sprite(&mut ctx.commands, &mut ctx.images);
    ctx.chip.0 = Some(handle);
    ctx.sprite.0 = Some(entity);
}

/// The frame-code chip sprite, spawned hidden at the capture target's
/// top-left corner; it becomes visible only at the readiness boundary. The
/// camera centers the target, so its top-left pixel sits at minus half the
/// extent; pinning the chip there puts it at the capture's corner. Shared by
/// both content lanes: calibration renders it full-frame scale (the only
/// scene content) and gameplay overlays it on the game view at the same
/// corner with the same lattice.
pub(super) fn spawn_chip_sprite(
    commands: &mut Commands,
    images: &mut Assets<Image>,
) -> (Handle<Image>, Entity) {
    let handle = images.add(chip_texture_image());
    let chip_origin = UVec2::new(CAPTURE_W, CAPTURE_H).as_vec2() * Vec2::new(-0.5, 0.5);
    let entity = commands
        .spawn((
            Sprite::from_image(handle.clone()),
            Anchor::TOP_LEFT,
            Visibility::Hidden,
            Transform::from_translation(chip_origin.extend(0.0)),
        ))
        .id();
    (handle, entity)
}

/// The offscreen capture target: `RENDER_ATTACHMENT` (the camera renders into
/// it) plus `TEXTURE_BINDING` (the screenshot pass samples/blits it), at the
/// full capture resolution.
pub(super) fn capture_target_image(images: &mut Assets<Image>) -> Handle<Image> {
    let mut image = Image::new_uninit(
        Extent3d {
            width: CAPTURE_W,
            height: CAPTURE_H,
            depth_or_array_layers: 1,
        },
        TextureDimension::D2,
        TextureFormat::Bgra8UnormSrgb,
        RenderAssetUsages::default(),
    );
    image.texture_descriptor.usage =
        TextureUsages::RENDER_ATTACHMENT | TextureUsages::TEXTURE_BINDING;
    images.add(image)
}

/// The offscreen capture camera: renders into the target image, ordered
/// behind the canary window camera (the two explicit orders keep both
/// cameras active when both exist).
fn spawn_capture_camera(commands: &mut Commands, target: Handle<Image>) {
    commands.spawn((
        Camera2d,
        Camera {
            order: OFFSCREEN_CAMERA_ORDER,
            ..Default::default()
        },
        RenderTarget::Image(target.into()),
        Msaa::Off,
    ));
}

/// The canary window camera: presents the same world to the primary window so
/// the window shows the actual scene the capture camera renders. Headless
/// mode never spawns it (no window exists).
fn spawn_window_camera(commands: &mut Commands) {
    commands.spawn((
        Camera2d,
        Camera {
            order: WINDOW_CAMERA_ORDER,
            ..Default::default()
        },
        Msaa::Off,
    ));
}

/// The frame-code chip texture, starting at (0, 0) until `paint_chip`
/// repaints the lattice per tick.
fn chip_texture_image() -> Image {
    Image::new(
        Extent3d {
            width: LANE_W,
            height: LANE_H,
            depth_or_array_layers: 1,
        },
        TextureDimension::D2,
        frame::encode_chip_rgba(0, 0),
        TextureFormat::Rgba8UnormSrgb,
        // Both usages: MAIN_WORLD keeps the bytes so `paint_chip` can repaint
        // the lattice per tick; RENDER_WORLD keeps the GPU copy the sprite
        // renders from (MAIN_WORLD alone is never uploaded to the GPU).
        RenderAssetUsages::default(),
    )
}
