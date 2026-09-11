//! The harness update chain: the drive half and the post-drive half.
//!
//! The drive half sits in the `ScriptedInput` set: the readiness proof
//! request, the readiness boundary (present-gated on the canary), the
//! canary's present probe, and the adapter step that advances the scenario
//! clock and offers the scripted input onto the shared gameplay plane. The
//! post-drive half runs after `ScriptedInput` and after [`LookApplied`] —
//! the player systems have integrated the tick's input, so everything it
//! does reads post-tick state: the chip repaint, the beat pin and capture
//! request, the bevy virtual-clock freeze under a readback, the perf sample,
//! and (via [`super::finish`]) the close scan. Captures are therefore
//! post-tick by construction, and the look action on a capture tick is
//! inside both the PNG and the reported yaw sample.

use bevy::app::{App, Update};
use bevy::asset::Assets;
use bevy::camera::visibility::Visibility;
use bevy::ecs::prelude::{Commands, Res, ResMut, Single, With};
use bevy::ecs::schedule::IntoScheduleConfigs;
use bevy::ecs::system::SystemParam;
use bevy::image::Image;
use bevy::math::Vec3;
use bevy::render::view::screenshot::Screenshot;
use bevy::time::{Time, Virtual};
use bevy::transform::components::Transform;

use super::RunMode;
use super::gameplay::{GameCameraBound, proof_gate};
use super::state::{
    BeatCapture, CaptureRequest, HarnessState, OnscreenCapture, PresentGate, PresentProbe,
    Readiness, ScenarioTime, drive_allowed, onscreen_capture_due,
};
use super::{CaptureTarget, ChipSprite, ChipTexture};
use crate::harness::{Content, ScenarioMode, TimedEvent, frame};
use crate::player::{GameplayInput, LookApplied, PlayerYaw, ScriptedInput};
use crate::readiness::GameAssets;

/// Frame-kernel state shared by the driving systems. A custom [`SystemParam`]
/// keeps the parameter count per system small and the access exact.
#[derive(SystemParam)]
pub(super) struct Kernel<'w> {
    state: ResMut<'w, HarnessState>,
    readiness: Res<'w, Readiness>,
    present: Res<'w, PresentGate>,
    scenario_time: ResMut<'w, ScenarioTime>,
    chip: Res<'w, ChipTexture>,
    images: ResMut<'w, Assets<Image>>,
}

/// The post-drive half of the harness update chain, identical on both lanes:
/// repaint the chip with the just-driven numbers, pin and request due beat
/// captures from the post-tick state, freeze bevy's virtual clock for the
/// duration of a capture hold, sample the perf lane, and close the run. The
/// half runs after the scripted-input set (the drive half) and, when the
/// game's look chain is present, after look application ([`LookApplied`]), so
/// a beat's observation samples the pose the tick's input actually produced —
/// captures are post-tick state. On calibration content the look set is empty
/// and that constraint is vacuous.
pub(super) fn register_post_drive_systems(app: &mut App) {
    app.add_systems(
        Update,
        (
            paint_driven_chip,
            request_beat_captures,
            freeze_engine_time,
            perf_sample,
            super::finish::finish_scan,
        )
            .chain()
            .after(ScriptedInput)
            .after(LookApplied),
    );
}

/// While loading, request a screenshot of the offscreen capture target every
/// update until one lands. The target image exists from startup, but the
/// camera and render resources need a rendered frame before a readback can
/// produce content; the first capture to arrive is the proof. On gameplay
/// content the request additionally waits on [`proof_gate`]: the required
/// game assets must have loaded and the rig camera must be bound to the
/// target, so the readback that proves readiness is a rendered game frame.
/// Calibration content requests immediately (its dark loading scene is the
/// whole proof).
pub(super) fn request_readiness_proof(
    readiness: Res<Readiness>,
    capture: Res<CaptureTarget>,
    state: Res<HarnessState>,
    assets: Option<Res<GameAssets>>,
    bound: Option<Res<GameCameraBound>>,
    mut commands: Commands,
) {
    let state = state.into_inner();
    if *readiness.into_inner() != Readiness::Loading || state.done {
        return;
    }
    if !proof_gate(state, assets, bound) {
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
/// readiness proof landed *and* the present gate has opened: on the canary the
/// window must have shown its first capturable frame before the run claims
/// readiness, so a locked-screen run holds at the probe (inside the bounded
/// present budget, exhausting it failing the run by name as today) instead of
/// announcing ready with zero presented frames. Headless runs have no gate to
/// wait for. The adapter was never stepped before this point, so the clock
/// starts at zero with no input consumed; the wake override keys on
/// `state.announced`, so the phase advance waits behind the same gate.
pub(super) fn readiness_boundary(
    readiness: Res<Readiness>,
    present: Res<PresentGate>,
    mut state: ResMut<HarnessState>,
    sprite: Res<ChipSprite>,
    mut commands: Commands,
) {
    let present = present.into_inner();
    if *readiness.into_inner() != Readiness::Ready || !present.presenting() || state.announced {
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

/// The canary present probe: while the run waits for the window's first
/// capturable frame, request a primary-window screenshot through the gate's
/// single probe slot — one probe at a time, the next issued only after the
/// previous verdict landed, the same one-in-flight discipline the beat lane
/// enforces with its capture ledger (bevy captures at most one screenshot per
/// target per frame). The observer reads the verdict ([`super::capture`]
/// routes it); the drive stays held until one comes back rendered, so the
/// first beat pin and its same-sync-point onscreen request happen only once
/// presents have demonstrably started. Headless runs have no window and never
/// probe (the gate starts satisfied).
pub(super) fn request_present_probe(
    readiness: Res<Readiness>,
    gate: ResMut<PresentGate>,
    state: Res<HarnessState>,
    mut commands: Commands,
) {
    let gate = gate.into_inner();
    let state = state.into_inner();
    if *readiness.into_inner() != Readiness::Ready
        || !gate.awaiting_first_present()
        || gate.probe_in_flight()
        || state.done
        || state.failed.is_some()
    {
        return;
    }
    gate.request_probe();
    commands.spawn((Screenshot::primary_window(), PresentProbe));
}

/// Drive one scenario-clock tick per update once ready. This is the drive
/// half of the tick. The clock is fixed timestep: this update advances the
/// tick by one and [`ScenarioTime`] by `1 / ticks_per_second` seconds, never
/// by a wall-clock delta, and `drive_allowed` holds the whole clock (tick,
/// frame, adapter, sim time) while a beat readback is in flight, so a tick
/// always lands on the same scenario frame in every run of the same scenario.
/// The adapter returns exactly this tick's edges and motions; each edge is
/// recorded once, with its press/release state in words, and look motion and
/// movement are recorded as separate named events so the report (and compare
/// mode) can tell the two channels apart. On gameplay content the same step
/// is offered onto the shared gameplay input plane — look converted from the
/// scenario's degrees to the plane's radians, movement and edges as their
/// typed payloads — so the player systems integrate it this same update; the
/// chain sits in the `ScriptedInput` set, which the look chain orders after.
/// Calibration content has no plane: nothing is offered. The post-drive half
/// ([`paint_driven_chip`], [`request_beat_captures`]) runs after the player
/// systems, so what they capture is the integrated post-tick state.
pub(super) fn drive_ticks(mut kernel: Kernel, mut plane: Option<ResMut<GameplayInput>>) {
    if !drive_allowed(*kernel.readiness, &kernel.present, &kernel.state) {
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
    if step.movement.forward != 0.0 || step.movement.strafe != 0.0 {
        kernel.state.events.push(TimedEvent::Input {
            tick,
            frame,
            what: format!("move {} {}", step.movement.forward, step.movement.strafe),
        });
    }
    if kernel.state.scenario.content == Content::Gameplay {
        let plane = plane
            .as_mut()
            .expect("gameplay content requires GameplayInput (PlayerLookPlugin provides it)");
        plane.offer_look(step.motion.x.to_radians(), step.motion.y.to_radians());
        plane.offer_movement(step.movement);
        plane.offer_edges(step.edges);
    }
    kernel.state.tick += 1;
    kernel.state.frame += 1;
    kernel.scenario_time.advance_tick();
}

/// Paint the chip texture with the numbers of the tick this update just
/// drove. Runs in the post-drive half, after the player systems and before
/// the beat requester, so the capture requested this update decodes to the
/// numbers pinned for the post-tick state it shows. The gate is the same one
/// `drive_ticks` consulted earlier this update: a driven update repaints; a
/// held update paints nothing, so the renderer keeps presenting the pinned
/// frame unchanged while a readback is in flight.
fn paint_driven_chip(mut kernel: Kernel) {
    if !drive_allowed(*kernel.readiness, &kernel.present, &kernel.state) {
        return;
    }
    let (tick, frame_num) = (kernel.state.tick - 1, kernel.state.frame - 1);
    paint_chip(&mut kernel, tick, frame_num);
}

/// Pause bevy's virtual clock for the duration of a capture hold, unpause on
/// landing. The engine's temporal render effects run on bevy's clocks, not on
/// the scenario clock: the generic `Time` resource mirrors `Time<Virtual>`
/// (bevy 0.19 `update_virtual_time`), and `bevy_render`'s
/// `prepare_globals_buffer` feeds `globals.delta_time` — the auto-exposure
/// adaptation rate — from that same clock. Pausing virtual time while a beat
/// readback is in flight makes every held frame render with a zero delta, so
/// the pinned frame stays pixel-stable for the whole readback instead of
/// drifting while bevy's wall time runs on; the landing update unpauses and
/// wall deltas resume. Outside the freeze window (loading, the canary present
/// probe wait) bevy's clocks run untouched — documented as a residual limit,
/// not defended against.
fn freeze_engine_time(state: Res<HarnessState>, mut virtual_time: ResMut<Time<Virtual>>) {
    let state = state.into_inner();
    if state.capture_in_flight.is_some() {
        virtual_time.pause();
    } else {
        virtual_time.unpause();
    }
}

/// Record one wall-clock frame delta into the perf sampler (perf mode only).
/// Runs after `drive_ticks` so every sampled update is one full rendered frame
/// of the calibration scene, chip animation included. The delta is Bevy's real
/// `Time` delta for this frame: wall-clock, not the fixed logical tick. The
/// perf lane never has a capture in flight, so the engine-time freeze never
/// touches its samples.
fn perf_sample(mut kernel: Kernel, time: Res<Time>) {
    if !drive_allowed(*kernel.readiness, &kernel.present, &kernel.state)
        || kernel.state.scenario.mode != ScenarioMode::Perf
    {
        return;
    }
    kernel
        .state
        .sampler
        .record(time.into_inner().delta_secs_f64() * 1000.0);
}

/// Paint the chip texture with this frame's (tick, frame) code.
fn paint_chip(kernel: &mut Kernel, tick: u64, frame_num: u64) {
    if let Some(handle) = &kernel.chip.0
        && let Some(mut image) = kernel.images.get_mut(handle)
    {
        image.data = Some(frame::encode_chip_rgba(tick, frame_num));
    }
}

/// Pin and request the next due beat from the post-tick state. Runs in the
/// post-drive half of the chain: this update already delivered its tick's
/// input and the player systems have integrated it, so the pinned (tick,
/// frame) — the tick that just drove — names exactly the state this update's
/// render shows. One atomic step pins request, entry, and pixels: bevy
/// captures at most one screenshot per render target per frame, and the
/// capture's observer binds it back to the entry by request id. The same
/// drive gate that admitted this update's drive step admits the pin, so the
/// clock can never pass a beat's tick while the lane is busy and every beat
/// pins exactly its scripted tick. In canary mode the first beat's request
/// also spawns the run's single onscreen capture of the primary window. On
/// gameplay content the pinned moment also samples the player rig's yaw into
/// a `PlayerYaw` event stamped with the same (tick, frame) the PNG shows —
/// read from the rig's actual transform, the rendered pose, so the sample is
/// the post-turn angle when the beat's own tick carried a look action.
pub(super) fn request_beat_captures(
    mut kernel: Kernel,
    capture: Res<CaptureTarget>,
    mode: Res<RunMode>,
    rig: Option<Single<&Transform, With<PlayerYaw>>>,
    mut commands: Commands,
) {
    let state = &mut *kernel.state;
    if !drive_allowed(*kernel.readiness, &kernel.present, state)
        || state.capture_in_flight.is_some()
    {
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
    let (tick, frame) = (state.tick - 1, state.frame - 1);
    let first_request = state.requested_beats == 0;
    let (name, entry) = state.pin_next_beat(tick, frame);
    if state.scenario.content == Content::Gameplay {
        let rig = rig.expect(
            "gameplay content requires the player rig (PlayerLookPlugin provides PlayerYaw)",
        );
        let yaw_degrees = rig_yaw_radians(rig.into_inner()).to_degrees();
        state.events.push(TimedEvent::PlayerYaw {
            tick,
            frame,
            yaw_degrees,
        });
    }
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
        name: name.clone(),
        tick,
        frame,
        request_id: entry.request_id,
    });
    if onscreen_capture_due(*mode.into_inner(), first_request) {
        // The onscreen request enters the same sync point as the offscreen
        // beat request, so its readback shows the same rendered frame: the
        // `.onscreen.png` decodes to the chip code of the beat PNG beside it.
        commands.spawn((Screenshot::primary_window(), OnscreenCapture { beat: name }));
    }
}

/// The rig yaw parent's horizontal angle, in radians, derived from its actual
/// transform rotation — the rendered pose — rather than from the look
/// bookkeeping: the beat's yaw sample proves the rig itself turned. The
/// parent carries a pure +Y rotation (`apply_mouse_look` writes
/// `Quat::from_rotation_y(yaw)`), so the angle is where that rotation sends
/// the forward axis, and `atan2` returns it already wrapped into (-pi, pi],
/// the range the look integrator keeps.
pub(super) fn rig_yaw_radians(transform: &Transform) -> f32 {
    let forward = transform.rotation * Vec3::NEG_Z;
    (-forward.x).atan2(-forward.z)
}
