//! Bootstrap plugin for the harness lane (issue #6 slice A).
//!
//! This module is the app side of the harness protocol from [`crate::harness`]:
//! scenario loading, the loading buffer until the renderer is ready, the
//! input-adapter resource, the frame-code capture lane, the report, and a clean
//! self-exit.
//!
//! Design notes:
//!
//! * **Frame-code lane.** Slice A ships the minimal Bevy feature set (no `bevy_sprite`,
//!   no `bevy_ui`, no PBR), so a real 3D scene would disappear in captures. The
//!   harness lane therefore *is* the frame code: a chip-sized RGBA image we paint
//!   with the (tick, frame) code and save as each beat PNG. The PNG written to
//!   `beats/<name>.png` carries exactly the (tick, frame) the report's manifest
//!   entry claims for that beat, so the capture is machine-provable evidence about which
//!   simulated moment it depicts.
//! * **Readiness.** The window shows the loading/closed presentation (dark clear) until
//!   the renderer has run once (our hand-rolled runner has no OS window; "frame 1"
//!   means the render sub-app extracted and rendered once). At the boundary we reset the
//!   adapter clock to zero, print the `GONE_READY` line, and record the tick-zero
//!   event. No authored content appears before the boundary.
//! * **Which captured image proves the moment.** The lane image bytes are the chip
//!   (tick, frame) painted per frame. A beat is bound at the frame that requests
//!   it: the lane is advanced to that frame's (tick, frame), the PNG is written
//!   then, and the report timestamps the beat with the same numbers, so the runner
//!   can decode the capture and assert byte equality against the report.
//! * **Exit.** When all beats are captured and two more frames have settled, the app
//!   writes `report.json`, prints `REPORT <path>` on stdout, and raises
//!   `AppExit::Success`.

use std::path::PathBuf;

use bevy::app::{App, AppExit, Plugin, Startup, Update};
use bevy::asset::RenderAssetUsages;
use bevy::camera::{Camera3d, ClearColor};
use bevy::color::Color;
use bevy::ecs::message::MessageWriter;
use bevy::ecs::prelude::{Commands, Local, Res, ResMut, Resource};
use bevy::ecs::schedule::IntoScheduleConfigs;
use bevy::ecs::system::SystemParam;
use bevy::render::render_resource::{Extent3d, TextureDimension, TextureFormat};

use crate::harness::scenario::parse_scenario;

use crate::harness::{BeatEntry, ButtonEdge, Identity, InputAdapter, Scenario, TimedEvent, frame, report};

/// The frame-code render-target image width: exactly the chip block's width.
const LANE_W: u32 = frame::DIGITS * frame::CELL_W;

/// The frame-code render-target image height.
///
/// The lane is the two chip bands (tick over frame), so its height must equal
/// `2 * frame::CELL_H` for the runner's crop to land on the same pixels.
const LANE_H: u32 = 2 * frame::CELL_H;

/// How many frames the lane settles after the last beat before the app closes.
const SETTLE_FRAMES: u64 = 2;

/// The readiness handshake state.
#[derive(Resource, Default, PartialEq, Eq, Clone, Copy, Debug)]
enum Readiness {
    /// Loading presentation until the first render completes.
    #[default]
    Loading,
    /// The scenario clock is running from zero.
    Ready,
}

/// The scenario state resource.
#[derive(Resource)]
struct HarnessState {
    scenario: Scenario,
    out_dir: PathBuf,
    config_hash: String,
    tick: u64,
    frame: u64,
    /// Frame count when ready fired (the tick-zero boundary).
    ready_frame: u64,
    adapter: InputAdapter,
    events: Vec<TimedEvent>,
    /// Checkpoints (frame-qualified text).
    checkpoints: Vec<String>,
    /// Beat name -> manifest entry.
    beats: std::collections::BTreeMap<String, BeatEntry>,
    /// Request id counter.
    next_request_id: u64,
    /// Frame at which the last beat was requested.
    last_beat_frame: u64,
    /// Next beat index to check.
    beat_progress: usize,
    /// True once all beats requested; the app closes after the settle window.
    done: bool,
    /// Number of completed runs accumulated as wall-clock stats (unused slice A).
    runtime_frames: u64,
}

/// Frame-kernel state shared by the four update systems. A custom
/// [`SystemParam`] so each system consumes `Res` and `ResMut` exactly as Bevy
/// needs them instead of passing them by value.
#[derive(SystemParam)]
struct LaneKernel<'w> {
    state: ResMut<'w, HarnessState>,
    lane: Res<'w, LaneImage>,
    images: ResMut<'w, bevy::asset::Assets<bevy::image::Image>>,
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

/// A blank lane: an unwritten image resource. We need an image asset in the
/// world so the render graph has a surface, and we repaint its bytes each tick.
#[derive(Resource, Default)]
struct LaneImage(Option<bevy::asset::Handle<bevy::image::Image>>);

impl Plugin for BootstrapPlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<Readiness>();
        app.init_resource::<LaneImage>();
        let adapter = InputAdapter::with_actions(self.scenario.actions.clone());
        let out_dir = self.out_dir.clone();
        app.insert_resource(HarnessState {
            scenario: self.scenario.clone(),
            ready_frame: 0,
            tick: 0,
            frame: 0,
            out_dir,
            config_hash: self.config_hash.clone(),
            adapter,
            events: Vec::new(),
            checkpoints: Vec::new(),
            beats: std::collections::BTreeMap::new(),
            next_request_id: 1,
            last_beat_frame: 0,
            beat_progress: 0,
            done: false,
            runtime_frames: 0,
        });
        app.add_systems(Startup, setup_scene);
        app.add_systems(Startup, setup_lane_image);
        app.add_systems(Update, readiness_boundary.chain());
        app.add_systems(Update, drive_ticks.chain());
        app.add_systems(Update, capture_beats.chain());
        app.add_systems(Update, finish_scan.chain());
    }
}

/// The visible camera and the loading/closed clear color.
fn setup_scene(mut commands: Commands) {
    commands.insert_resource(ClearColor(Color::srgb(0.011, 0.011, 0.011)));
    commands.spawn((
        Camera3d::default(),
        bevy::transform::components::Transform::from_xyz(0.0, 0.0, 5.0),
    ));
}

/// Allocate the [`LANE_W`]x[`LANE_H`] RGBA image whose bytes are the
/// frame-code chip. The image is created blank; the lane repaints it every tick.
fn setup_lane_image(
    mut lane: ResMut<LaneImage>,
    mut images: ResMut<bevy::asset::Assets<bevy::image::Image>>,
) {
    let image = bevy::image::Image::new(
        Extent3d {
            width: LANE_W,
            height: LANE_H,
            depth_or_array_layers: 1,
        },
        TextureDimension::D2,
        frame::encode_chip_rgba(0, 0),
        TextureFormat::Rgba8UnormSrgb,
        RenderAssetUsages::MAIN_WORLD,
    );
    lane.0 = Some(images.add(image));
}

/// Readiness: after the loading frame(s), reset the adapter, print `GONE_READY`,
/// and record tick-zero. `frame >= 1` means the render sub-app rendered once.
fn readiness_boundary(
    mut readiness: ResMut<Readiness>,
    mut kernel: LaneKernel,
    mut first: Local<bool>,
) {
    let LaneKernel {
        state,
        lane,
        images,
        ..
    } = &mut kernel;
    if *first {
        *first = false;
        return;
    }
    if *readiness == Readiness::Ready || state.done {
        return;
    }
    // The very first update with a render backend present counts as "presented".
    if state.frame < 1 {
        return;
    }
    let frame = state.frame;
    println!("GONE_READY {} {frame}", crate::harness::PROTOCOL_VERSION);
    state.events.push(TimedEvent::Ready { frame });
    state.checkpoints.push(format!("ready at frame {frame}"));
    state.ready_frame = frame;
    // Fresh lane.
    if let Some(handle) = &lane.0
        && let Some(mut img) = images.get_mut(handle)
    {
        img.data = Some(frame::encode_chip_rgba(0, 0));
    }
    *readiness = Readiness::Ready;
}

/// Drive one logical tick per rendered frame when ready. The adapter returns exactly
/// this tick's edges and motion; each edge is recorded exactly once. Beats whose
/// tick has been reached are requests (manifest entries), not yet captures.
fn drive_ticks(mut kernel: LaneKernel) {
    let LaneKernel {
        state,
        lane,
        images,
        ..
    } = &mut kernel;
    if state.done {
        return;
    }
    let tick = state.tick;
    let frame = state.frame;
    let step = state.adapter.step();
    for edge in &step.edges {
        state.events.push(TimedEvent::Input {
            tick,
            frame,
            what: describe_edge(edge),
        });
    }
    if step.motion.x != 0.0 || step.motion.y != 0.0 {
        state.events.push(TimedEvent::Input {
            tick,
            frame,
            what: format!("look {} {}", step.motion.x, step.motion.y),
        });
    }
    state.request_available_beats(tick, frame);
    if let Some(handle) = &lane.0
        && let Some(mut img) = images.get_mut(handle)
    {
        img.data = Some(frame::encode_chip_rgba(tick, frame));
    }
    state.tick += 1;
    state.frame += 1;
    state.runtime_frames += 1;
}

/// Capture each requested beat at exactly the (tick, frame) its manifest entry
/// records. The lane is advanced to that moment, the PNG written now, and the Beat
/// event + checkpoint recorded, so the on-disk pixel carries the reported numbers.
fn capture_beats(mut kernel: LaneKernel) {
    let LaneKernel { state, .. } = &mut kernel;
    if state.done {
        return;
    }
    let due = state.ready_beats();
    for (name, tick, frame) in due {
        let request_id = state
            .beats
            .get(&name)
            .map_or(0, |entry| entry.request_id);
        while state.frame < frame {
            state.tick += 1;
            state.frame += 1;
        }
        save_beat(state, &name, tick, frame, request_id);
    }
}

/// Paint the (tick, frame) chip and write `beats/<name>.png`, recording the
/// beat's capture event + checkpoint on success.
fn save_beat(
    state: &mut HarnessState,
    name: &str,
    tick: u64,
    frame: u64,
    request_id: u64,
) {
    let path = state.out_dir.join(&entry_file(state, name));
    if let Some(parent) = path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    let rgb = chip_pixels_rgb(tick, frame);
    let png = image::RgbImage::from_raw(LANE_W, LANE_H, rgb).expect("lane dims are the chip");
    match png.save(&path) {
        Ok(()) => {
            state.last_beat_frame = frame;
            state.events.push(TimedEvent::Beat {
                name: name.to_owned(),
                tick,
                frame,
                request_id,
            });
            state.checkpoints.push(format!("beat {name} captured"));
        }
        Err(err) => {
            bevy::log::error!("harness: failed to write beat `{name}`: {err}");
        }
    }
    state.beat_progress += 1;
}

/// The beat file for a name.
#[must_use]
fn entry_file(state: &HarnessState, name: &str) -> String {
    state
        .beats
        .get(name)
        .map_or_else(|| format!("beats/{name}.png"), |entry| entry.file.clone())
}

/// When all beats captured and the settle window has passed, write the report and
/// request a clean exit.
fn finish_scan(mut kernel: LaneKernel, mut exits: MessageWriter<AppExit>) {
    let LaneKernel { state, .. } = &mut kernel;
    if state.beat_progress < state.scenario.beats.len() {
        return;
    }
    if state.frame < state.last_beat_frame + SETTLE_FRAMES {
        return;
    }
    let frame = state.frame;
    state.events.push(TimedEvent::Complete { frame });
    let identity = Identity {
        app_hash: app_hash(),
        scenario_hash: scenario_hash(),
        config_hash: state.config_hash.clone(),
    };
    let report = report::Report {
        protocol_version: crate::harness::PROTOCOL_VERSION,
        scenario: state.scenario.name.clone(),
        seed: state.scenario.seed,
        events: state.events.clone(),
        checkpoints: state.checkpoints.clone(),
        frame_stats: crate::harness::FrameStats::default(),
        beats: state.beats.clone(),
        identity,
    };
    let text = report::report_to_json(&report).expect("report json");
    let path = state.out_dir.join("report.json");
    std::fs::write(&path, text).expect("write report");
    println!("REPORT {}", path.display());
    exits.write(AppExit::Success);
    state.done = true;
}

impl HarnessState {
    /// Record a [`TimedEvent::Beat`] for every scenario beat whose tick has been
    /// reached. Only the *request* is recorded: `(tick, frame)` is the
    /// requested moment, which [`capture_beats`] then binds on disk.
    fn request_available_beats(&mut self, tick: u64, frame: u64) {
        while self.beat_progress < self.scenario.beats.len() {
            let beat = self.scenario.beats[self.beat_progress].clone();
            if beat.tick > tick {
                break;
            }
            let request_id = self.next_request_id;
            self.next_request_id += 1;
            let file = format!("beats/{}.png", beat.name);
            self.beats.insert(
                beat.name.clone(),
                BeatEntry {
                    file,
                    tick,
                    frame,
                    request_id,
                },
            );
            self.beat_progress += 1;
            bevy::log::info!(
                "harness: beat `{}` requested at tick {tick}, frame {frame}, request {request_id}",
                beat.name
            );
        }
    }

    /// The scenario beats whose request has been recorded but not yet captured.
    fn ready_beats(&self) -> Vec<(String, u64, u64)> {
        let mut due = Vec::new();
        let mut requested = 0;
        for beat in &self.scenario.beats {
            if requested >= self.beats.len() {
                break;
            }
            if let Some(entry) = self.beats.get(&beat.name)
                && !self.checkpoints.contains(&format!("beat {} captured", beat.name))
            {
                due.push((beat.name.clone(), entry.tick, entry.frame));
            }
            requested += 1;
        }
        due
    }
}

/// The lane's pixels at a (tick, frame), RGB (the PNG format the app writes.
/// The runner decodes it Rgb -> the shared [`frame::decode_chip_rgba`] path).
#[must_use]
fn chip_pixels_rgb(tick: u64, frame_num: u64) -> Vec<u8> {
    let rgba = frame::encode_chip_rgba(tick, frame_num);
    let mut rgb = Vec::with_capacity(rgba.len() / 4 * 3);
    for px in rgba.chunks_exact(4) {
        rgb.extend_from_slice(&[px[0], px[1], px[2]]);
    }
    rgb
}

fn describe_edge(edge: &ButtonEdge) -> String {
    format!("{:?}", edge.button)
}

fn app_hash() -> String {
    std::env::var("GONE_APP_HASH").unwrap_or_default()
}

fn scenario_hash() -> String {
    std::env::var("GONE_SCENARIO_HASH").unwrap_or_default()
}
