//! The production wake driver (issue #8, normal-mode wiring).
//!
//! This is the app integration the sim slice left deliberately open: the
//! authored eyelid timeline ([`gone_sim::WakeState`] over
//! [`gone_sim::WakeTimeline::authored`]) drives the real opening beat of the
//! windowed game, behind the same readiness barrier every lane obeys.
//!
//! * **The effect exists from the camera's first frame.** A Startup system
//!   ordered after the rig spawn attaches
//!   [`WakeEyelidMaterial::CLOSED`] to the player camera itself, so no
//!   rendered frame ever shows the room through an unliddered camera. There
//!   is no Update race and no un-covered frame.
//! * **The loading cover is readiness-driven, not frame-counted.** Until the
//!   eyelid pass can actually composite — the required-asset ledger
//!   ([`GameAssets::ready`]) and the render-world pipeline bridge
//!   ([`WakeEyelidPipelineReadiness`], real pipeline-cache state) both agree
//!   — an opaque dark 2D camera over the game view keeps the window on the
//!   loading presentation. During those updates the wake machine is
//!   untouched: the phase holds at `Waking`, the sample holds fully closed.
//!   The cover lifts exactly when the machine starts, whose first sample is
//!   logical tick zero — bitwise the closed rest state — so the lift is
//!   seamless against the closed eyelids beneath.
//! * **The windowed game additionally waits for the window itself.** A
//!   compiled pipeline is not a drawable: issue #27 showed the whole wake
//!   playing invisibly while the primary window's surface acquire failed
//!   every frame. The render world therefore records a closed-frame fact
//!   after every render frame and the next extraction publishes it
//!   ([`present`], reading bevy's own `ExtractedWindows` — never the
//!   surface; `MainWorld` exists on the render world only during
//!   `ExtractSchedule`), and the windowed gate
//!   holds the machine — no start, no tick, no accumulated seconds — until
//!   a frame has closed over the primary window's drawable. That first
//!   acknowledged frame starts the timeline once at tick zero and spends no
//!   wake delta doing it, and later updates that follow a frame without a
//!   drawable bank no time, so the timeline can never catch up on seconds
//!   the window never presented. The harness lanes take no presentation
//!   pacing ([`PresentationPacedWake`], the normal game's opt-in): the
//!   headless lane has no window, and the canary's scenario clock is
//!   already held by its screenshot-proven present gate, so their 1:1
//!   clock contracts are byte-identical to the driver's own.
//! * **The timeline runs on the lane's own clock, one shared machine.** The
//!   driver accumulates the update's seconds and consumes whole logical
//!   ticks of [`gone_sim::LOGICAL_TICK_SECS`] (1/60 s at
//!   [`gone_sim::LOGICAL_TICKS_PER_SECOND`]); the authored milliseconds
//!   encode through the sim's own conversion, and the completion tick is
//!   [`gone_sim::WakeTimeline::complete_tick`], never a hand-counted frame
//!   number. The normal game feeds bevy's virtual delta; the gameplay
//!   harness pins bevy's virtual clock to its deterministic scenario clock
//!   (one fixed step per driven tick, zero on held updates), so the same
//!   driver plays the same authored samples per driven tick on every lane.
//!   Because every sample is a pure function of the logical tick, batching
//!   ticks differently can change only how many were consumed, never what
//!   any tick samples.
//! * **Sway composes without drift.** While the effect is attached, the rig's
//!   two transforms are a pure projection of `(LookAngles + the current
//!   sample's sway offset)` — the same yaw-parent/pitch-child layering the
//!   look integrator writes, never an accumulation into the pose. The same
//!   tick always lands on the same pose bits regardless of the updates that
//!   reached it.
//! * **Completion hands off once.** At the authored completion tick the
//!   driver projects the neutral authored pose (sway zero), delivers
//!   [`SimWakePhase::wake_complete`] exactly once (the machine's `Waking ->
//!   AwakeInPod` boundary; any other outcome is a loud wiring failure), and
//!   removes the effect from every wake camera. The look gate unlocks with
//!   the phase; the next look write projects the plain angles.
//!
//! # What is not here
//!
//! * **No GPU frame has validated the composited content.** The driver's
//!   evidence is typed: the pipeline bridge (compile state — never drawable
//!   proof) and, in the windowed game, the closed-frame acknowledgement
//!   (frame scheduling evidence from bevy's own loop). What nothing here
//!   proves is pixel content: no gate or test reads presented frames. The
//!   fixture tests below drive controlled bridge and acknowledgement states
//!   — that is fixture behavior, not native presentation evidence; the
//!   harness lanes' screenshot gates remain the pixel evidence for their
//!   own lanes.
//! * The calibration, smoke, and perf lanes build none of this module: they
//!   never run [`crate::bootstrap::gameplay::wire`], so they never acquire
//!   the game wake.

use std::num::NonZeroU8;

use bevy::app::{App, AppExit, Plugin, Startup, Update};
use bevy::camera::{Camera, Camera2d, ClearColorConfig};
use bevy::ecs::message::MessageWriter;
use bevy::ecs::prelude::{Commands, Entity, Local, Query, Res, ResMut, Resource, Single, With};
use bevy::ecs::schedule::IntoScheduleConfigs;
use bevy::ecs::system::SystemParam;
use bevy::math::{Quat, Vec2};
use bevy::prelude::Camera3d;
use bevy::render::view::Msaa;
use bevy::time::{Time, Virtual};
use bevy::window::{PrimaryWindow, Window};
use gone_sim::{
    LOGICAL_TICK_SECS, PhaseTransition, WakePhase, WakeSample, WakeStart, WakeState, WakeTimeline,
};

use crate::player::{
    GAME_CLEAR_COLOR, LookAngles, LookApplied, PlayerPitch, RigTransforms, ScriptedInput,
};
use crate::readiness::{GameAssets, poll_required_assets_or_exit};
use crate::scene::SimWakePhase;
use crate::wake_pass::{
    WakeEyelidMaterial, WakeEyelidPipelineFailure, WakeEyelidPipelineReadiness, WakeEyelidPlugin,
};

/// The primary window's closed-frame acknowledgement (the gate's
/// presentation leg): the render/main mirror and the normal game's
/// presentation pacing.
mod present;

pub(crate) use present::PresentationPacedWake;
use present::{WakePresentProbePlugin, WakePresentReadiness};

/// The loading cover's render order, above every game camera (the rig camera
/// keeps its default order), so the cover's opaque frame is the one the
/// window presents until the wake gate opens.
const LOADING_COVER_ORDER: isize = 100;

/// The game's opaque loading cover: a spawned fullscreen 2D camera over the
/// game view, present from Startup until the wake gate opens. `None` after
/// the lift; the despawn is exactly once because the gate opens exactly once.
#[derive(Resource, Default)]
pub(crate) struct LoadingCover(Option<Entity>);

/// The app's resource over the `gone_sim` wake machine, the same boundary
/// [`crate::scene::SimWakePhase`] draws over the sim's phase machine: the
/// sim type is plain data with no Bevy in it, only this wrapper is a
/// resource, and every method delegates to it unchanged.
#[derive(Resource)]
pub(crate) struct SimWakeState(WakeState);

impl SimWakeState {
    /// A machine over `timeline`, holding fully closed until readiness is
    /// marked.
    pub(crate) fn new(timeline: WakeTimeline) -> Self {
        Self(WakeState::new(timeline))
    }

    /// Whether the timeline has started.
    pub(crate) fn is_started(&self) -> bool {
        self.0.is_started()
    }

    /// Mark the readiness barrier open (start-once, exactly the machine's
    /// own contract).
    pub(crate) fn mark_ready(&mut self) -> WakeStart {
        self.0.mark_ready()
    }

    /// The sample at the current logical tick, without advancing.
    pub(crate) fn sample(&self) -> WakeSample {
        self.0.sample()
    }

    /// Consume one logical tick, returning the new tick's sample.
    pub(crate) fn tick(&mut self) -> WakeSample {
        self.0.tick()
    }

    /// Whether the timeline has reached its completion tick.
    pub(crate) fn is_complete(&self) -> bool {
        self.0.is_complete()
    }

    /// The machine's current logical tick: zero until the gate starts the
    /// timeline, one per consumed tick after. The harness tests read it to
    /// pin the 1:1 mapping between driven scenario ticks and logical ticks.
    #[cfg(test)]
    pub(crate) fn current_tick(&self) -> u64 {
        self.0.current_tick()
    }
}

/// The normal game's wake wiring: the render primitive
/// ([`WakeEyelidPlugin`]), the closed eyelid on the player camera from the
/// rig's first frame, the opaque loading cover, the primary window's
/// closed-frame probe ([`WakePresentProbePlugin`], the gate's presentation
/// leg), and the tick driver that starts the authored timeline behind the
/// readiness barrier and hands off to [`SimWakePhase::wake_complete`] at
/// the authored completion tick.
///
/// Requires the normal game's plugin set around it: the look plugin (the rig
/// and [`LookAngles`]) and the ledger ([`GameAssets`], which `run` inserts).
/// Their absence is a wiring error the systems name loudly, never a degraded
/// mode.
pub(crate) struct GameWakePlugin;

impl Plugin for GameWakePlugin {
    fn build(&self, app: &mut App) {
        app.add_plugins(WakeEyelidPlugin);
        app.add_plugins(WakePresentProbePlugin);
        app.init_resource::<LoadingCover>();
        app.insert_resource(SimWakeState::new(WakeTimeline::authored()));
        app.add_systems(Startup, spawn_loading_cover);
        app.add_systems(
            Startup,
            attach_closed_eyelid_to_player_camera.after(crate::player::setup_player_rig),
        );
        // The driver runs after this update's ledger poll (the same gate
        // evidence the poll just refreshed) and before the look chain: the
        // completion handoff flips the phase and removes the effect before
        // `apply_mouse_look` can arm, so the wake's last frame and look's
        // first frame project the same plain pose. The sway projection runs
        // between them, on the ticks this update just drove. Both slots are
        // meaningful for the harness lanes too: after `ScriptedInput`'s
        // drive half, before the look application.
        app.add_systems(
            Update,
            (advance_wake, apply_wake_sway)
                .chain()
                .after(ScriptedInput)
                .before(LookApplied)
                .after(poll_required_assets_or_exit),
        );
    }
}

/// Spawn the opaque loading cover: a 2D camera over the game view (its clear
/// is the game's authored near-black, [`GAME_CLEAR_COLOR`]) that renders
/// nothing and replaces the target, so the window presents a dark loading
/// frame while the eyelid pass compiles. Lifted by the driver at wake start.
fn spawn_loading_cover(mut commands: Commands, mut cover: ResMut<LoadingCover>) {
    let camera = commands
        .spawn((
            Camera2d,
            Camera {
                order: LOADING_COVER_ORDER,
                clear_color: ClearColorConfig::Custom(GAME_CLEAR_COLOR),
                ..Camera::default()
            },
            Msaa::Off,
        ))
        .id();
    cover.0 = Some(camera);
}

/// Attach the fully closed eyelid to the player camera, inside the same
/// Startup as the rig spawn but strictly after it: the camera's very first
/// rendered frame carries the closed effect, so no frame can expose the
/// un-liddered room.
///
/// # Panics
/// Panics unless exactly one player rig camera exists: the wake plugin is a
/// game-mode feature that always builds over [`crate::player`], so a missing
/// rig is a wiring error, not a skip.
fn attach_closed_eyelid_to_player_camera(
    mut commands: Commands,
    rig: Query<Entity, (With<PlayerPitch>, With<Camera3d>)>,
) {
    let camera = rig.single().expect(
        "GameWakePlugin requires exactly one player rig camera (PlayerLookPlugin spawns it \
         at Startup)",
    );
    commands.entity(camera).insert(WakeEyelidMaterial::CLOSED);
}

/// The driver's gate and handoff resources, bundled to one system parameter:
/// the wake machine, the authoritative phase machine, the readiness legs
/// (the asset ledger, the pipeline bridge with its failure text, and the
/// primary window's closed-frame acknowledgement), the loading cover, and
/// the windowed game's presentation-pacing marker.
#[derive(SystemParam)]
struct WakeDriver<'w, 's> {
    /// The authored wake machine: holds closed until the gate opens, ticks
    /// at the logical rate, completes at the authored tick.
    state: ResMut<'w, SimWakeState>,
    /// The authoritative phase machine the completion signal goes through.
    phase: ResMut<'w, SimWakePhase>,
    /// The required-asset ledger (the barrier's asset leg).
    assets: Res<'w, GameAssets>,
    /// The eyelid pipeline bridge (the barrier's render leg; compile
    /// evidence, never drawable proof).
    readiness: Res<'w, WakeEyelidPipelineReadiness>,
    /// The bridge's error text, carried beside an `Errored` verdict.
    failure: Res<'w, WakeEyelidPipelineFailure>,
    /// The primary window's closed-frame acknowledgement, published from
    /// the render world's per-frame record at every extraction (the gate's
    /// presentation leg; see [`present`]).
    present: Res<'w, WakePresentReadiness>,
    /// The app's primary window, if the run is windowed (the normal game and
    /// the canary). The headless harness lane has none, and the empty query
    /// is what keeps its gate free of the presentation leg.
    primary_windows: Query<'w, 's, (), (With<Window>, With<PrimaryWindow>)>,
    /// Whether this run paces its wake on the window's presentation (the
    /// normal windowed game's opt-in; the harness lanes never insert it, so
    /// their scenario-clock contracts stay byte-identical).
    paced: Option<Res<'w, PresentationPacedWake>>,
    /// The loading cover, lifted at the same instant the machine starts.
    cover: ResMut<'w, LoadingCover>,
}

/// The driver's view resources: every camera currently carrying the eyelid
/// effect (the rig camera in the normal game; the canary spectator joins it
/// on gameplay harness runs, so every wake view renders the same authored
/// samples), the rig's transform pair, and the look angles the sway
/// projection composes against.
#[derive(SystemParam)]
struct WakeView<'w, 's> {
    /// The cameras carrying the effect, with their entities for the
    /// completion removal. Empty only before the Startup attachment and
    /// after it: the empty query is what skips this system once completion
    /// removed the effect everywhere.
    eyelids: Query<'w, 's, (Entity, &'static mut WakeEyelidMaterial)>,
    /// The rig's yaw-parent/pitch-camera transform pair.
    rig: RigTransforms<'w, 's>,
    /// The integrated look angles (constant while the wake owns the camera).
    angles: Res<'w, LookAngles>,
}

/// Advance the wake by this update's virtual delta, in whole logical ticks.
///
/// A failed pipeline exits the game naming bevy's own error text. Until the
/// readiness legs hold — the asset ledger, the pipeline bridge, and, in a
/// windowed run, the primary window's first closed frame — the machine is
/// untouched: the cover stays up, the sample holds closed, the phase holds
/// at `Waking`, and no second is banked. The gate's first open update
/// starts the machine at logical tick zero (bitwise closed) and lifts the
/// cover; a presentation-paced run spends no wake delta on that start
/// update, and banks a later update's seconds only when the frame it
/// follows had the drawable. The completion tick projects the neutral pose,
/// delivers `wake_complete` exactly once, and removes the effect.
fn advance_wake(
    mut driver: WakeDriver,
    view: WakeView,
    time: Res<Time<Virtual>>,
    mut commands: Commands,
    mut exits: MessageWriter<AppExit>,
    mut accumulator: Local<f32>,
) {
    let WakeView {
        mut eyelids,
        mut rig,
        angles,
    } = view;
    // The empty query is the post-completion shape (the Startup attachment
    // fills it from the first frame on), the same skip the removed effect
    // gave the old single-carrier filter.
    if eyelids.is_empty() {
        return;
    }
    let angles = angles.into_inner();
    let time = time.into_inner();
    if *driver.readiness == WakeEyelidPipelineReadiness::Errored {
        fail_eyelid_pipeline(&driver.failure, &mut exits);
        return;
    }
    if !driver.assets.ready() || *driver.readiness != WakeEyelidPipelineReadiness::Ready {
        return;
    }
    // The presentation leg (windowed runs): a compiled pipeline is not a
    // drawable, so the machine also holds until the render world has closed
    // a frame over the primary window's. The hold banks nothing, so the
    // whole pre-window wait can never be caught up later.
    let paced = driver.paced.is_some();
    if !driver.primary_windows.is_empty() && !driver.present.drawable_frame_seen {
        return;
    }
    if !driver.state.is_started() {
        start_wake(&mut driver, &mut commands, &mut rig, angles, &mut eyelids);
        if paced {
            // The acknowledged start spends no wake delta: the first frame
            // the window presents after the gate opens is tick zero's closed
            // rest state, not tick one.
            return;
        }
    }
    // A paced run banks this update's seconds only when the frame it follows
    // had the drawable: a no-drawable update (occlusion, surface recreation)
    // banks nothing, so the timeline can never catch up on time the window
    // never presented. Unpaced runs — the harness lanes' screenshot-paced
    // scenario clocks — bank every driven second, as before.
    if !paced || driver.present.closed_with_drawable {
        *accumulator += time.delta_secs();
    }
    while *accumulator >= LOGICAL_TICK_SECS {
        *accumulator -= LOGICAL_TICK_SECS;
        let sample = driver.state.tick();
        if driver.state.is_complete() {
            complete_wake(&mut driver, &mut commands, &mut rig, angles, &eyelids);
            return;
        }
        write_material(&mut eyelids, WakeEyelidMaterial::from_sample(sample));
    }
}

/// Write one sample's uniform onto every wake camera carrying the effect.
fn write_material(
    eyelids: &mut Query<'_, '_, (Entity, &'static mut WakeEyelidMaterial)>,
    material: WakeEyelidMaterial,
) {
    for (_, mut carrier) in &mut *eyelids {
        *carrier = material;
    }
}

/// The gate's first open update: mark the machine ready (the machine's own
/// start-once contract; later gate-open updates are its `AlreadyStarted`
/// no-op), lift the loading cover, and settle the rig and every wake camera
/// on logical tick zero's closed rest state.
fn start_wake(
    driver: &mut WakeDriver,
    commands: &mut Commands,
    rig: &mut RigTransforms,
    angles: &LookAngles,
    eyelids: &mut Query<'_, '_, (Entity, &'static mut WakeEyelidMaterial)>,
) {
    driver.state.mark_ready();
    if let Some(cover) = driver.cover.0.take() {
        commands.entity(cover).despawn();
    }
    // Tick zero's sample is the closed rest state; write it (the attachments
    // already carried it) and settle the rig at the same tick's sway (zero).
    project_rig_pose(rig, angles, driver.state.sample().sway_offset);
    write_material(
        eyelids,
        WakeEyelidMaterial::from_sample(driver.state.sample()),
    );
}

/// The authored completion tick's handoff: project the neutral authored
/// pose exactly once (the view state is neutral even if look stays unarmed
/// this frame), deliver `wake_complete` through the shared boundary — the
/// machine's `Waking -> AwakeInPod` move; any other outcome is a loud
/// wiring failure — and strip the effect from every wake camera.
fn complete_wake(
    driver: &mut WakeDriver,
    commands: &mut Commands,
    rig: &mut RigTransforms,
    angles: &LookAngles,
    eyelids: &Query<'_, '_, (Entity, &'static mut WakeEyelidMaterial)>,
) {
    project_rig_pose(rig, angles, Vec2::ZERO);
    let transition = driver.phase.wake_complete();
    assert!(
        matches!(
            transition,
            PhaseTransition::Advanced {
                from: WakePhase::Waking,
                to: WakePhase::AwakeInPod
            }
        ),
        "the wake timeline's completion must advance Waking -> AwakeInPod exactly \
         once, got {transition:?}"
    );
    for (camera, _) in eyelids.iter() {
        commands.entity(camera).remove::<WakeEyelidMaterial>();
    }
}

/// Exit the game nonzero, naming the eyelid pipeline's own failure text.
/// The bridge writes that text beside every `Errored` verdict, so the
/// missing text here would be a bridge bug, not a fallback path.
///
/// # Panics
/// Panics if the failure text is somehow absent beside an `Errored` verdict.
fn fail_eyelid_pipeline(failure: &WakeEyelidPipelineFailure, exits: &mut MessageWriter<AppExit>) {
    let error = failure
        .0
        .as_deref()
        .expect("the readiness bridge carries the error text beside an Errored verdict");
    eprintln!("gone: the wake eyelid pipeline failed: {error}");
    exits.write(AppExit::Error(NonZeroU8::new(1).expect("one is nonzero")));
}

/// Project `(look angles + sway offset)` onto the rig's two transforms: yaw
/// plus the sway's x on the yaw parent, pitch plus the sway's y on the pitch
/// camera child. A pure projection of two authoritative states, recomputed
/// from the angles every write, so no batching of ticks and no number of
/// updates can accumulate drift into the pose.
fn project_rig_pose(rig: &mut RigTransforms, angles: &LookAngles, sway: Vec2) {
    let (yaw, pitch) = angles.yaw_pitch();
    rig.yaw.rotation = Quat::from_rotation_y(yaw + sway.x);
    rig.pitch.rotation = Quat::from_rotation_x(pitch + sway.y);
}

/// Compose the current wake sample's camera sway onto the rig, every update
/// the effect is attached (the component filter skips the system the update
/// after completion removed it). Runs after the driver's tick advance, so
/// the pose reflects the ticks this update drove; during the wake the look
/// gate keeps the integrator from writing the same rotations.
fn apply_wake_sway(
    state: Res<SimWakeState>,
    angles: Res<LookAngles>,
    _effect: Single<(), (With<PlayerPitch>, With<WakeEyelidMaterial>)>,
    mut rig: RigTransforms,
) {
    project_rig_pose(
        &mut rig,
        angles.into_inner(),
        state.into_inner().sample().sway_offset,
    );
}

#[cfg(test)]
mod tests;
