//! Bootstrap plugin for the harness lane (issue #15).
//!
//! This module is the app side of the harness protocol from [`crate::harness`]:
//! scenario loading, the loading presentation until the renderer has actually
//! presented, the input-adapter resource, the frame-code sprite, the report, and
//! a clean self-exit. The app runs as the normal winit app — a real OS window is
//! open for the whole run.
//!
//! Design notes:
//!
//! * **Real GPU capture, offscreen.** The frame-code chip is a 24x10 [`Sprite`]
//!   rendered into the scene at the capture target's top-left pixel (top band:
//!   tick, bottom band: frame). The harness camera renders into a dedicated
//!   offscreen [`Image`] render target (`RenderTarget::Image`), and beat
//!   captures are [`Screenshot::image`] readbacks of that target handed to a
//!   [`ScreenshotCaptured`] observer, which encodes the PNG. The winit window
//!   stays open for presentation only; the offscreen image is the capture
//!   source of truth, because `Screenshot::primary_window()` returns a fully
//!   black image on this platform config (M4 Max / Bevy 0.19.1 / Metal — proven
//!   by a minimal probe), so the harness never captures from the swapchain. The
//!   runner decodes the PNG's top-left chip block and asserts it equals the
//!   report entry, so the verified pixels are ones the GPU rendered.
//! * **Readiness before the clock.** The scenario clock starts only after the
//!   first capture of the offscreen target lands. That capture is the readback
//!   of a frame the render graph actually executed into the target, so it is
//!   direct evidence the renderer built its device resources and rendered at
//!   least one full frame. Only then does the app print `GONE_READY`, record
//!   tick zero, and make the chip sprite visible (no authored content before
//!   the boundary); [`state::drive_allowed`] gates every later step on the same
//!   state, so no scenario tick or input edge is consumed before the boundary.
//! * **Beat binding and accounting.** A beat's screenshot is spawned on the first
//!   frame at or after its scenario tick where the capture lane is free (bevy
//!   captures at most one screenshot per render target per frame, so exactly one
//!   capture is in flight), and the manifest entry pins *that* frame's
//!   (tick, frame, request id) at the same instant it is spawned. The capture
//!   therefore always shows the chip code the report claims: request, entry, and
//!   rendered pixels are one atomic step (see
//!   `state::HarnessState::pin_next_beat`). Requests and captures are separate
//!   ledgers; the run completes only when every scenario beat's PNG is on disk.
//!   One ordering detail keeps the pin honest: the beat request runs *before*
//!   `drive_ticks` pins the pre-drive counters, because a texture repaint
//!   reaches the GPU one update after its paint — pinning anything later would
//!   name numbers the render does not show yet.
//! * **Immediate capture failures.** A failed capture convert/save records a
//!   `TimedEvent::Failure` naming the artifact and the underlying error, writes
//!   the report, and exits nonzero. There is no retry loop.
//! * **`max_frames` deadline.** The scenario's `max_frames` rendered frames is
//!   the run's deadline, not extra patience: when the frame count reaches it
//!   with beats still uncaptured, [`state::fail_at_deadline`] records every
//!   uncaptured beat as missing, and `finish_scan` writes the report and exits
//!   nonzero. A beat scripted past the deadline is a failed scenario, never a
//!   hang. The all-beats-captured path is unchanged (immediate finish once the
//!   settle window after the last capture passes).
//! * **Exit.** After the last capture and a two-frame settle, the app writes
//!   `report.json`, prints `REPORT <path>`, and raises `AppExit::Success`.
//!
//! Module layout: this file owns the plugin, the ECS systems, and the capture
//! I/O; [`state`] owns the scenario run state (counters, beat ledgers,
//! readiness, failure recording), and `tests` pins the accounting and readiness
//! regressions without needing a renderer.

mod state;

#[cfg(test)]
mod tests;

use std::num::NonZeroU8;
use std::path::{Path, PathBuf};

use bevy::app::{App, AppExit, Plugin, Startup, Update};
use bevy::asset::{Assets, Handle, RenderAssetUsages};
use bevy::camera::visibility::Visibility;
use bevy::camera::{Camera2d, ClearColor, RenderTarget};
use bevy::color::Color;
use bevy::ecs::message::MessageWriter;
use bevy::ecs::prelude::{Commands, Entity, On, Query, Res, ResMut, Resource};
use bevy::ecs::schedule::IntoScheduleConfigs;
use bevy::ecs::system::SystemParam;
use bevy::image::Image;
use bevy::math::{UVec2, Vec2};
use bevy::render::render_resource::{Extent3d, TextureDimension, TextureFormat, TextureUsages};
use bevy::render::view::screenshot::{Screenshot, ScreenshotCaptured};
// `Msaa` lives on the view module in bevy 0.19 (it is a property of the render
// target view, not of a render-resource pipeline object).
use bevy::render::view::Msaa;
use bevy::sprite::{Anchor, Sprite};
use bevy::transform::components::Transform;

use crate::capture::capture_to_png;
use crate::harness::scenario::parse_scenario;
use crate::harness::{Identity, InputAdapter, Scenario, TimedEvent, frame, report};

use state::{
    BeatCapture, CaptureRequest, HarnessState, Readiness, drive_allowed, fail_at_deadline,
    fail_scenario,
};

/// The frame-code chip texture width: exactly the chip block's width.
const LANE_W: u32 = frame::DIGITS * frame::CELL_W;

/// The frame-code chip texture height: the two chip bands (tick over frame).
const LANE_H: u32 = 2 * frame::CELL_H;

/// The offscreen capture target's width in pixels (matches the window's
/// logical resolution so captures are full-frame at scale factor 1.0).
const CAPTURE_W: u32 = 1920;

/// The offscreen capture target's height in pixels.
const CAPTURE_H: u32 = 1080;

/// How many frames the run settles after the last beat capture before closing.
const SETTLE_FRAMES: u64 = 2;

/// Where the loading-frame capture is written inside the run directory. The
/// proof is the rendered loading presentation (dark clear, no authored content).
const READINESS_PROOF_FILE: &str = "readiness-proof.png";

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

/// Frame-kernel state shared by the driving systems. A custom [`SystemParam`]
/// keeps the parameter count per system small and the access exact.
#[derive(SystemParam)]
struct Kernel<'w> {
    state: ResMut<'w, HarnessState>,
    readiness: Res<'w, Readiness>,
    chip: Res<'w, ChipTexture>,
    images: ResMut<'w, Assets<Image>>,
}

/// Construct the harness plugin from the harness-mode environment.
pub struct BootstrapPlugin {
    scenario: Scenario,
    out_dir: PathBuf,
    config_hash: String,
}

impl BootstrapPlugin {
    /// Build the plugin from the runner's env.
    pub fn new(
        scenario_path: Option<PathBuf>,
        out_dir: Option<PathBuf>,
        config_hash: String,
    ) -> Self {
        let scenario = match scenario_path {
            Some(path) => {
                let text = std::fs::read_to_string(&path)
                    .unwrap_or_else(|e| panic!("cannot read scenario {}: {e}", path.display()));
                parse_scenario(&text).unwrap_or_else(|e| panic!("bad scenario: {e}"))
            }
            None => panic!("GONE_HARNESS requires GONE_SCENARIO (the runner always sets it)"),
        };
        let out_dir = out_dir.expect("GONE_HARNESS requires GONE_OUT_DIR");
        Self {
            scenario,
            out_dir,
            config_hash,
        }
    }
}

impl Plugin for BootstrapPlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<Readiness>();
        app.init_resource::<ChipTexture>();
        app.init_resource::<ChipSprite>();
        app.init_resource::<CaptureTarget>();
        let adapter = InputAdapter::with_actions(self.scenario.actions.clone());
        app.insert_resource(HarnessState::new(
            self.scenario.clone(),
            self.out_dir.clone(),
            self.config_hash.clone(),
            adapter,
        ));
        app.add_observer(on_screenshot_captured);
        app.add_systems(Startup, setup_harness_scene);
        app.add_systems(
            Update,
            (
                request_readiness_proof,
                readiness_boundary,
                request_beat_captures,
                drive_ticks,
                finish_scan,
            )
                .chain(),
        );
    }
}

/// The loading scene: dark clear, one Camera2d rendering into the offscreen
/// capture target (MSAA off so the chip lattice stays pixel-crisp in captures),
/// and the chip sprite spawned hidden at the target's top-left — it becomes
/// visible only at the readiness boundary. The target image gets
/// `RENDER_ATTACHMENT` (the camera renders into it) plus `TEXTURE_BINDING` (the
/// screenshot pass samples/blits it).
fn setup_harness_scene(
    mut commands: Commands,
    mut chip: ResMut<ChipTexture>,
    mut sprite: ResMut<ChipSprite>,
    mut capture: ResMut<CaptureTarget>,
    mut images: ResMut<Assets<Image>>,
) {
    commands.insert_resource(ClearColor(Color::srgb(0.011, 0.011, 0.011)));
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
    let handle = images.add(image);
    commands.spawn((
        Camera2d,
        RenderTarget::Image(handle.clone().into()),
        Msaa::Off,
    ));
    capture.0 = Some(handle);
    let image = Image::new(
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
    );
    let handle = images.add(image);
    // The camera centers the target, so its top-left pixel sits at minus half
    // the extent; pinning the chip there puts it at the capture's corner.
    let chip_origin = UVec2::new(CAPTURE_W, CAPTURE_H).as_vec2() * Vec2::new(-0.5, 0.5);
    let entity = commands
        .spawn((
            Sprite::from_image(handle.clone()),
            Anchor::TOP_LEFT,
            Visibility::Hidden,
            Transform::from_translation(chip_origin.extend(0.0)),
        ))
        .id();
    chip.0 = Some(handle);
    sprite.0 = Some(entity);
}

/// While loading, request a screenshot of the offscreen capture target every
/// update until one lands. The target image exists from startup, but the
/// camera and render resources need a rendered frame before a readback can
/// produce content; the first capture to arrive is the proof.
fn request_readiness_proof(
    readiness: Res<Readiness>,
    capture: Res<CaptureTarget>,
    state: Res<HarnessState>,
    mut commands: Commands,
) {
    if *readiness.into_inner() != Readiness::Loading || state.into_inner().done {
        return;
    }
    let handle = capture
        .into_inner()
        .0
        .clone()
        .expect("capture target exists (created in Startup, before any Update)");
    commands.spawn(Screenshot::image(handle));
}

/// The readiness boundary: print `GONE_READY`, record the tick-zero event, and
/// make the chip sprite visible. Runs exactly once, the first update after the
/// readiness proof landed. The adapter was never stepped before this point, so
/// the clock starts at zero with no input consumed.
fn readiness_boundary(
    readiness: Res<Readiness>,
    mut state: ResMut<HarnessState>,
    sprite: Res<ChipSprite>,
    mut commands: Commands,
) {
    if *readiness.into_inner() != Readiness::Ready || state.announced {
        return;
    }
    state.announced = true;
    let frame = state.frame;
    println!("GONE_READY {} {frame}", crate::harness::PROTOCOL_VERSION);
    state.events.push(TimedEvent::Ready { frame });
    state.checkpoints.push(format!("ready at frame {frame}"));
    if let Some(entity) = sprite.into_inner().0 {
        commands.entity(entity).insert(Visibility::Visible);
    }
}

/// Drive one logical tick per rendered frame once ready. The adapter returns
/// exactly this tick's edges and motion; each edge is recorded once, with its
/// press/release state in words. Runs after [`request_beat_captures`], so the
/// beat pins name the pre-drive counters this update renders.
fn drive_ticks(mut kernel: Kernel) {
    if !drive_allowed(*kernel.readiness, &kernel.state) {
        return;
    }
    let tick = kernel.state.tick;
    let frame = kernel.state.frame;
    let step = kernel.state.adapter.step();
    for edge in &step.edges {
        kernel.state.events.push(TimedEvent::Input {
            tick,
            frame,
            what: edge.to_string(),
        });
    }
    if step.motion.x != 0.0 || step.motion.y != 0.0 {
        kernel.state.events.push(TimedEvent::Input {
            tick,
            frame,
            what: format!("look {} {}", step.motion.x, step.motion.y),
        });
    }
    paint_chip(&mut kernel, tick, frame);
    kernel.state.tick += 1;
    kernel.state.frame += 1;
}

/// Paint the chip texture with this frame's (tick, frame) code.
fn paint_chip(kernel: &mut Kernel, tick: u64, frame_num: u64) {
    if let Some(handle) = &kernel.chip.0
        && let Some(mut image) = kernel.images.get_mut(handle)
    {
        image.data = Some(frame::encode_chip_rgba(tick, frame_num));
    }
}

/// Spawn the next due beat's screenshot while at most one is in flight, pinning
/// its manifest entry to the (tick, frame) the capture is about to render. One
/// atomic step pins request, entry, and pixels: this runs *before*
/// [`drive_ticks`], so the pinned numbers are the pre-drive counters — exactly
/// what the chip texture shows in this update's render. (A texture repaint
/// reaches the GPU one update after its paint, so pinning the pre-drive
/// counters is what makes the PNG decode to the entry's numbers.) bevy
/// captures at most one screenshot per render target per frame, and the
/// capture's observer binds it back to the entry by request id.
fn request_beat_captures(
    readiness: Res<Readiness>,
    capture: Res<CaptureTarget>,
    mut state: ResMut<HarnessState>,
    mut commands: Commands,
) {
    if !drive_allowed(*readiness.into_inner(), &state) || state.capture_in_flight.is_some() {
        return;
    }
    if state.next_due_beat().is_none() {
        return;
    }
    let handle = capture
        .into_inner()
        .0
        .clone()
        .expect("capture target exists (created in Startup, before any Update)");
    let (tick, frame) = (state.tick, state.frame);
    let (name, entry) = state.pin_next_beat(tick, frame);
    commands.spawn((
        Screenshot::image(handle),
        BeatCapture {
            name: name.clone(),
            tick,
            frame,
            request_id: entry.request_id,
        },
    ));
    state.capture_in_flight = Some(CaptureRequest {
        name,
        tick,
        frame,
        request_id: entry.request_id,
    });
}

/// The receiver for every bevy screenshot of this run. A capture carrying a
/// [`BeatCapture`] is that beat's rendered frame: convert and write it now, no
/// retry. Any other capture is a readiness proof.
fn on_screenshot_captured(
    mut captured: On<ScreenshotCaptured>,
    mut readiness: ResMut<Readiness>,
    mut state: ResMut<HarnessState>,
    beats: Query<&BeatCapture>,
) {
    let captured = captured.event_mut();
    if let Ok(beat) = beats.get(captured.entity) {
        capture_beat(&mut state, beat, &captured.image);
        return;
    }
    if *readiness == Readiness::Ready {
        return; // a duplicate proof landing after the boundary
    }
    match save_capture(&state.out_dir, READINESS_PROOF_FILE, &captured.image) {
        Ok(()) => {
            bevy::log::info!(
                "harness: readiness proof captured ({}x{} screenshot of the offscreen target)",
                captured.image.width(),
                captured.image.height()
            );
            state
                .checkpoints
                .push("readiness proof captured".to_owned());
            *readiness = Readiness::Ready;
        }
        Err(err) => fail_scenario(&mut state, format!("readiness proof capture failed: {err}")),
    }
}

/// Convert and write one beat's captured target frame to its manifest file,
/// then record the capture. Failures name the beat and underlying error and are
/// terminal.
fn capture_beat(state: &mut HarnessState, request: &BeatCapture, image: &Image) {
    let Some(in_flight) = state.capture_in_flight.take() else {
        fail_scenario(
            state,
            format!(
                "beat `{}` capture arrived with none in flight",
                request.name
            ),
        );
        return;
    };
    if in_flight.request_id != request.request_id {
        fail_scenario(
            state,
            format!(
                "beat `{}` capture does not match the in-flight request",
                request.name
            ),
        );
        return;
    }
    let Some(entry) = state.beats.get(&request.name) else {
        fail_scenario(
            state,
            format!("beat `{}` has no manifest entry", request.name),
        );
        return;
    };
    let file = entry.file.clone();
    match save_capture(&state.out_dir, &file, image) {
        Ok(()) => {
            bevy::log::info!(
                "harness: beat `{}` captured from the offscreen target at tick {}, frame {}, \
                 request {} ({})",
                request.name,
                request.tick,
                request.frame,
                request.request_id,
                file
            );
            state.mark_captured(
                &request.name,
                request.tick,
                request.frame,
                request.request_id,
            );
        }
        Err(err) => fail_scenario(
            state,
            format!("beat `{}` capture failed: {err}", request.name),
        ),
    }
}

/// Convert a captured frame image to PNG bytes and write it under the run
/// directory at `rel`.
///
/// # Errors
/// A message naming `rel` and the underlying error; the caller fails the run.
fn save_capture(out_dir: &Path, rel: &str, image: &Image) -> Result<(), String> {
    let path = out_dir.join(rel);
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("capture `{rel}` mkdir: {e}"))?;
    }
    let png = capture_to_png(image)?;
    std::fs::write(&path, png).map_err(|e| format!("capture `{rel}` save: {e}"))?;
    Ok(())
}

/// Close the run: a recorded failure exits nonzero immediately (no settle
/// window); the `max_frames` deadline with beats still uncaptured records that
/// failure and exits nonzero in the same pass; otherwise every beat must be
/// captured to disk and the settle window must pass before the report is
/// written and `AppExit::Success` requested.
fn finish_scan(mut state: ResMut<HarnessState>, mut exits: MessageWriter<AppExit>) {
    if state.done {
        return;
    }
    fail_at_deadline(&mut state);
    let failed = state.failed.clone();
    if failed.is_none()
        && !(state.all_beats_captured() && state.frame >= state.last_beat_frame + SETTLE_FRAMES)
    {
        return;
    }
    if failed.is_none() {
        let frame = state.frame;
        state.events.push(TimedEvent::Complete { frame });
    }
    let path = write_report(&state);
    println!("REPORT {}", path.display());
    exits.write(if failed.is_some() {
        exit_failure()
    } else {
        AppExit::Success
    });
    state.done = true;
}

/// Serialize and write `report.json` into the run directory; returns its path.
/// Panics when the report cannot be written: the runner treats a missing or
/// unparsable report as a failed run either way.
fn write_report(state: &HarnessState) -> PathBuf {
    if let Err(err) = std::fs::create_dir_all(&state.out_dir) {
        panic!("cannot create run dir {}: {err}", state.out_dir.display());
    }
    let identity = Identity {
        app_hash: app_hash(),
        scenario_hash: scenario_hash(),
        config_hash: state.config_hash.clone(),
    };
    // Capture completion is asynchronous (a beat's readback lands one or more
    // frames after the frame it captured), so `state.events` is in wall-clock
    // completion order, which two identical runs can differ in. The report is
    // written in the protocol's canonical order instead.
    let mut events = state.events.clone();
    report::sort_events(&mut events);
    let report = report::Report {
        protocol_version: crate::harness::PROTOCOL_VERSION,
        scenario: state.scenario.name.clone(),
        seed: state.scenario.seed,
        events,
        checkpoints: state.checkpoints.clone(),
        frame_stats: crate::harness::FrameStats::default(),
        beats: state.beats.clone(),
        identity,
    };
    let text = report::report_to_json(&report).expect("report json");
    let path = state.out_dir.join("report.json");
    std::fs::write(&path, text).expect("write report");
    path
}

/// The nonzero `AppExit` used when the scenario failed.
fn exit_failure() -> AppExit {
    AppExit::Error(NonZeroU8::new(1).expect("one is nonzero"))
}

fn app_hash() -> String {
    std::env::var("GONE_APP_HASH").unwrap_or_default()
}

fn scenario_hash() -> String {
    std::env::var("GONE_SCENARIO_HASH").unwrap_or_default()
}
