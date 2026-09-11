//! Gameplay-content harness glue (the scenario `content: "gameplay"` lane).
//!
//! The calibration lane renders its own loading scene; this module boots the
//! real game instead: the post chain, the stasis-room scene, and the player
//! rig all build exactly as the normal game builds them, and the harness
//! captures through them. Three additions keep the protocol intact:
//!
//! * **Capture plumbing.** The player rig's camera is retargeted into the
//!   same offscreen capture image the calibration lane uses, and the
//!   frame-code chip renders as a small corner overlay through a dedicated
//!   2D camera onto that same image (same lattice, same decode contract; the
//!   overlay camera never clears, it only draws the chip on top). A canary
//!   run presents the room through a second, static 3D camera into the
//!   window, with its own overlay camera carrying the chip there too.
//! * **The scripted input hop.** The adapter step recorded in the bootstrap
//!   chain's drive system is offered onto the shared gameplay input plane
//!   ([`crate::player::GameplayInput`]), which the player systems consume;
//!   the bootstrap chain sits in the `ScriptedInput` set, which the whole
//!   look chain orders after, so a scripted look offered on tick N
//!   integrates on tick N.
//! * **The room observation.** The first update counts spawned stasis-pod
//!   groups against the pod-registry count the scene is built from and
//!   records a `RoomCheck` event; a mismatch fails the scenario app-side
//!   (a broken scene cannot produce a passing run).
//!
//! * **The readiness legs.** Gameplay content extends the harness readiness
//!   barrier with two legs the calibration lane does not have: the required
//!   game assets (the crate's `readiness` ledger, polled first in the
//!   update chain) and the rig camera binding to the capture target. The
//!   readiness proof is requested only once both hold, so the readback that
//!   opens the scenario clock is a rendered game frame whose pipelines are
//!   compiled, never the chip overlay alone. A required asset whose load
//!   fails is a terminal failure naming the asset and the underlying error;
//!   the run exits nonzero instead of rendering placeholders.
//!
//! The wake override lives behind that barrier: the lane boots the scene's
//! authored `Waking` phase and drives the machine's wake-complete signal at
//! the readiness boundary ([`advance_wake_at_readiness`]), which lands the
//! machine in `AwakeInPod`, the first state whose policy allows look. When
//! the wake pass (issue #8) lands, the lane wakes naturally and the
//! override goes away; the pass's own driver must stay behind the same
//! barrier, in this lane and in the normal game alike.

use bevy::app::{App, Update};
use bevy::asset::{AssetServer, Assets, Handle};
use bevy::camera::{Camera, Camera2d, Camera3d, ClearColorConfig, RenderTarget};
use bevy::ecs::prelude::{Added, Commands, Entity, Local, Query, Res, ResMut, Resource, With};
use bevy::image::Image;
use bevy::math::Vec3;
use bevy::render::view::Msaa;
use bevy::transform::components::Transform;
use gone_sim::PhaseTransition;
use gone_sim::WakePhase;

use super::state::{HarnessState, RunMode, fail_scenario};
use super::{CaptureTarget, ChipSprite, ChipTexture, capture_target_image, spawn_chip_sprite};
use crate::harness::{Content, TimedEvent};
use crate::player::{
    GameplayInput, LookAngles, PlayerLookPlugin, PlayerMotionPlugin, PlayerPitch, ScriptedInput,
};
use crate::post::GamePostChainPlugin;
use crate::readiness::GameAssets;
use crate::scene::{
    PlayerExitPath, SimColliders, SimPodRegistry, SimWakePhase, StasisPod, StasisScenePlugin,
};

/// The canary window's static 3D camera order: the room view draws first.
const WINDOW_SPECTATOR_ORDER: isize = 0;

/// The canary window's chip overlay order: the chip draws onto the window
/// view without clearing it.
const WINDOW_OVERLAY_ORDER: isize = 1;

/// The gameplay capture view (the retargeted rig camera) into the offscreen
/// target. Distinct from the canary window's orders so both targets' camera
/// chains stay unambiguous when both exist.
const GAMEPLAY_SCENE_ORDER: isize = 2;

/// The offscreen chip overlay onto the gameplay capture view.
const GAMEPLAY_OVERLAY_ORDER: isize = 3;

/// Where the canary spectator camera sits: above and behind the room's
/// center, looking down into it (the onscreen check needs a lit, non-black
/// view of the room; it is a canary, not an authored shot).
const SPECTATOR_EYE: Vec3 = Vec3::new(0.0, 2.6, 7.5);

/// What the canary spectator camera aims at: the room's occupied center.
const SPECTATOR_FOCUS: Vec3 = Vec3::new(0.0, 0.8, 0.0);

/// Build the real game into a harness app: post chain, stasis scene, and
/// player look and body motion, in the same order the normal game adds them
/// (each plugin's build provides the resource the next consumes). Fails
/// loudly at boot if the wiring came out wrong. Installs the readiness
/// barrier's resources: the required-asset ledger over the handles the post
/// chain just loaded, and the game-camera binding flag the retarget sets.
/// The scene plugin's authored `Waking` spawn state stands; the wake
/// override advances at the readiness boundary
/// (`advance_wake_at_readiness`), never before it.
pub(super) fn wire(app: &mut App) {
    app.add_plugins((
        GamePostChainPlugin,
        StasisScenePlugin,
        PlayerLookPlugin,
        PlayerMotionPlugin,
    ));
    assert!(
        app.world()
            .get_resource::<crate::post::PostChainAssets>()
            .is_some(),
        "gameplay content requires PostChainAssets (GamePostChainPlugin provides it)"
    );
    assert!(
        app.world().get_resource::<SimPodRegistry>().is_some(),
        "gameplay content requires SimPodRegistry (StasisScenePlugin provides it)"
    );
    assert!(
        app.world().get_resource::<SimColliders>().is_some(),
        "gameplay content requires SimColliders (StasisScenePlugin provides it)"
    );
    assert!(
        app.world().get_resource::<PlayerExitPath>().is_some(),
        "gameplay content requires PlayerExitPath (StasisScenePlugin provides it)"
    );
    assert!(
        app.world().get_resource::<GameplayInput>().is_some(),
        "gameplay content requires GameplayInput (PlayerLookPlugin provides it)"
    );
    assert!(
        app.world().get_resource::<LookAngles>().is_some(),
        "gameplay content requires LookAngles (PlayerLookPlugin provides it)"
    );
    let ledger = {
        let masks = app.world().resource::<crate::post::PostChainAssets>();
        GameAssets::game_required_assets(masks)
    };
    app.insert_resource(ledger);
    app.insert_resource(GameCameraBound::default());
}

/// The gameplay content scene: the offscreen capture target and the corner
/// chip sprite (hidden until the readiness boundary, exactly as in
/// calibration), the chip overlay camera onto the capture target, and, in
/// canary mode, the static room view plus chip overlay into the window.
/// The rig camera itself is retargeted into the capture target by
/// [`retarget_gameplay_camera`] once the player plugin spawns it. No clear
/// color is authored here: the game's own cameras clear.
pub(super) fn setup_gameplay_scene(
    mut commands: Commands,
    mode: Res<RunMode>,
    mut chip: ResMut<ChipTexture>,
    mut sprite: ResMut<ChipSprite>,
    mut capture: ResMut<CaptureTarget>,
    mut images: ResMut<Assets<Image>>,
) {
    let handle = capture_target_image(&mut images);
    spawn_overlay_camera(&mut commands, handle.clone());
    if *mode.into_inner() == RunMode::Canary {
        spawn_window_spectator_camera(&mut commands);
        spawn_window_overlay_camera(&mut commands);
    }
    capture.0 = Some(handle);
    let (handle, entity) = spawn_chip_sprite(&mut commands, &mut images);
    chip.0 = Some(handle);
    sprite.0 = Some(entity);
}

/// The offscreen chip overlay: a 2D camera onto the capture target, ordered
/// after the gameplay view, that never clears; its only content is the chip
/// sprite, drawn on top of the frame the gameplay view rendered into the
/// target.
fn spawn_overlay_camera(commands: &mut Commands, target: Handle<Image>) {
    commands.spawn((
        Camera2d,
        Camera {
            order: GAMEPLAY_OVERLAY_ORDER,
            clear_color: ClearColorConfig::None,
            ..Camera::default()
        },
        RenderTarget::Image(target.into()),
        Msaa::Off,
    ));
}

/// The canary window's static room view: a 3D camera into the primary
/// window, so the window presents the actual scene the rig camera renders
/// for capture.
fn spawn_window_spectator_camera(commands: &mut Commands) {
    commands.spawn((
        Camera3d::default(),
        Camera {
            order: WINDOW_SPECTATOR_ORDER,
            ..Camera::default()
        },
        Transform::from_translation(SPECTATOR_EYE).looking_at(SPECTATOR_FOCUS, Vec3::Y),
    ));
}

/// The canary window's chip overlay: a 2D camera onto the primary window,
/// ordered after the spectator view, that never clears. The chip sprite is
/// shared with the offscreen overlay, so both captures decode the same code.
fn spawn_window_overlay_camera(commands: &mut Commands) {
    commands.spawn((
        Camera2d,
        Camera {
            order: WINDOW_OVERLAY_ORDER,
            clear_color: ClearColorConfig::None,
            ..Camera::default()
        },
        Msaa::Off,
    ));
}

/// Whether the rig camera is bound to the offscreen capture target yet. The
/// readiness proof for gameplay content waits on it: the readback that opens
/// the scenario clock must be a frame the game camera rendered into the
/// target, not the chip overlay alone. Set once by
/// [`retarget_gameplay_camera`], which runs on the first update after the
/// player plugin spawns the rig.
#[derive(Resource, Default)]
pub(super) struct GameCameraBound(pub(super) bool);

/// The player rig's camera lookup: the entity owning the just-added 3D camera
/// tagged `PlayerPitch` (which marks the rig camera and nothing else), with
/// mutable access to its camera settings.
type RigCameraQuery<'w, 's> =
    Query<'w, 's, (Entity, &'static mut Camera), (Added<Camera3d>, With<PlayerPitch>)>;

/// Retarget the player rig's camera into the offscreen capture target on the
/// first update after the player plugin spawns it (`Added` fires exactly
/// once per rig), before this update renders, and set the game-camera
/// binding flag the readiness proof gate consumes. Also drops MSAA on the
/// capture view so the chip lattice stays pixel-crisp, matching the
/// calibration camera. `PlayerPitch` marks the rig camera and nothing else:
/// the canary spectator (also a 3D camera) never matches.
pub(super) fn retarget_gameplay_camera(
    capture: Res<CaptureTarget>,
    mut commands: Commands,
    mut bound: ResMut<GameCameraBound>,
    mut rig: RigCameraQuery,
) {
    let handle = capture
        .into_inner()
        .0
        .clone()
        .expect("capture target exists (created in Startup, before any Update)");
    for (entity, mut camera) in rig.iter_mut() {
        camera.order = GAMEPLAY_SCENE_ORDER;
        commands
            .entity(entity)
            .insert((RenderTarget::Image(handle.clone().into()), Msaa::Off));
        bound.0 = true;
    }
}

/// The gameplay run's first-update room observation: spawned stasis-pod
/// groups versus the pod-registry count the scene is built from, recorded as
/// a `RoomCheck` event at the current frame (before any tick runs). A
/// mismatch fails the scenario: the runner re-asserts the numbers, and a
/// scene that did not build cannot produce a passing run.
fn observe_room(
    mut state: ResMut<HarnessState>,
    registry: Res<SimPodRegistry>,
    pods: Query<(), With<StasisPod>>,
    mut seen: Local<bool>,
) {
    if *seen {
        return;
    }
    *seen = true;
    let pods_expected = registry.into_inner().registry().pods().len();
    let pods_present = pods.iter().count();
    record_room_check(&mut state, pods_expected, pods_present);
}

/// Record the room observation and fail the scenario on a mismatch.
fn record_room_check(state: &mut HarnessState, pods_expected: usize, pods_present: usize) {
    let frame = state.frame;
    state.events.push(TimedEvent::RoomCheck {
        frame,
        pods_expected,
        pods_present,
    });
    if pods_expected != pods_present {
        fail_scenario(
            state,
            format!(
                "stasis room mismatch: the registry builds {pods_expected} pods \
                 but {pods_present} pod groups are present in the world"
            ),
        );
    }
}

/// The gameplay lane's wake-phase observation: record the machine's phase
/// into the report once per change (the authored opening included, so the
/// run's first update records `Waking` while the lane loads), stamped with
/// the run moment whose update observed it. The stamp follows the beat-pin
/// convention (the tick and frame that just drove; zero before the first
/// tick drove), so the recorded sequence reads in the report's canonical
/// order exactly as the machine moved. The runner's gameplay-full lane
/// asserts the recorded names are the wake progression, in order. Systems
/// order after the player motion slice (which advances the machine inside
/// its controllers) via the post-drive half's `.after(PlaneCleared)` chain
/// ordering, so a transition is recorded on the update that drove it.
pub(super) fn observe_wake_phase(
    mut state: ResMut<HarnessState>,
    phase: Option<Res<SimWakePhase>>,
    mut last: Local<Option<WakePhase>>,
) {
    let Some(phase) = phase else {
        return;
    };
    let current = phase.into_inner().phase();
    if *last == Some(current) {
        return;
    }
    *last = Some(current);
    let (tick, frame) = (state.tick.saturating_sub(1), state.frame.saturating_sub(1));
    state.events.push(TimedEvent::WakePhase {
        tick,
        frame,
        phase: phase_name(current).to_owned(),
    });
}

/// The report's spelling of a wake phase: `snake_case` protocol strings, kept
/// out of the protocol module because the protocol module cannot name
/// simulation types (`xtask check architecture`).
#[must_use]
fn phase_name(phase: WakePhase) -> &'static str {
    match phase {
        WakePhase::Waking => "waking",
        WakePhase::AwakeInPod => "awake_in_pod",
        WakePhase::ExitingPod => "exiting_pod",
        WakePhase::Standing => "standing",
    }
}

/// The gameplay lane's required-asset poll: advance the readiness ledger and
/// fail the run on a required asset's load error, naming the asset and the
/// underlying error. A pending load keeps the lane loading: the proof request
/// waits on the ledger, the scenario clock stays at frame zero, and no input
/// or phase advances (the same hold the capture freeze uses). The poll runs
/// first in the update chain so a load that completes this update is visible
/// to this update's proof request.
pub(super) fn poll_required_assets(
    mut state: ResMut<HarnessState>,
    mut assets: ResMut<GameAssets>,
    server: Res<AssetServer>,
) {
    assets.poll(server.into_inner());
    if let Some(failure) = assets.failure() {
        fail_scenario(
            &mut state,
            format!(
                "required asset `{}` failed to load: {}",
                failure.asset, failure.error
            ),
        );
    }
}

/// The gameplay legs of the readiness proof gate: calibration content has
/// none (the readback of the dark loading scene is the whole proof), and
/// gameplay content requires the required-asset ledger to be fully loaded
/// and the rig camera bound to the capture target, so the proof readback is
/// a rendered game frame. The resources are present exactly when the
/// gameplay wire ran; their absence on gameplay content is a wiring error.
pub(super) fn proof_gate(
    state: &HarnessState,
    assets: Option<Res<GameAssets>>,
    bound: Option<Res<GameCameraBound>>,
) -> bool {
    if state.scenario.content != Content::Gameplay {
        return true;
    }
    let assets =
        assets.expect("gameplay content requires GameAssets (the gameplay wire inserts it)");
    let bound =
        bound.expect("gameplay content requires GameCameraBound (the gameplay wire inserts it)");
    assets.ready() && bound.0
}

/// The gameplay lane's wake override, moved behind the readiness barrier:
/// while the lane loads, the machine sits at the scene's authored `Waking`;
/// once the boundary announces, the wake-complete signal advances it to
/// `AwakeInPod` (the first state whose policy allows look), exactly once.
/// This is the gate point for wake progression in gameplay runs: the issue
/// #8 wake pass's own driver must sit behind the same barrier and consume
/// the same signal.
pub(super) fn advance_wake_at_readiness(
    state: Res<HarnessState>,
    mut phase: ResMut<SimWakePhase>,
    mut advanced: Local<bool>,
) {
    if !state.into_inner().announced || *advanced {
        return;
    }
    let transition = phase.wake_complete();
    assert!(
        matches!(transition, PhaseTransition::Advanced { .. }),
        "the readiness wake override must advance the machine out of `Waking`, got {transition:?}"
    );
    *advanced = true;
}

/// The gameplay update registration. The drive half — the required-asset poll
/// first (the barrier's asset leg must be resolved before the same update's
/// proof request), the proof request, the boundary, the wake override, the
/// present probe, the room observation, and the adapter step — chains inside
/// the `ScriptedInput` set, so the player look chain orders after it and a
/// scripted look offered on tick N integrates on tick N. The post-drive half
/// (the shared registration in `super`) runs after `ScriptedInput` and after
/// [`LookApplied`], so the beat pin and the yaw sample read the pose this
/// tick's input produced. The rig-camera retarget runs outside both sets: it
/// only touches the camera once, before the first render.
pub(super) fn register_update_systems(app: &mut App) {
    use super::drive::{
        drive_ticks, readiness_boundary, register_post_drive_systems, request_present_probe,
        request_readiness_proof,
    };
    use bevy::ecs::schedule::IntoScheduleConfigs;
    app.add_systems(Update, retarget_gameplay_camera);
    app.add_systems(
        Update,
        (
            poll_required_assets,
            request_readiness_proof,
            readiness_boundary,
            advance_wake_at_readiness,
            request_present_probe,
            observe_room,
            drive_ticks,
        )
            .chain()
            .in_set(ScriptedInput),
    );
    register_post_drive_systems(app);
}

#[cfg(test)]
mod tests {
    use bevy::app::{App, TaskPoolPlugin, Update};
    use bevy::asset::{AssetApp, AssetPlugin, Assets};
    use bevy::camera::{Camera, Camera3d, RenderTarget};
    use bevy::ecs::prelude::{Entity, With};
    use bevy::image::Image;
    use bevy::render::view::Msaa;
    use gone_sim::{PhaseTransition, WakePhase};

    use super::super::state::HarnessState;
    use super::{
        GAMEPLAY_SCENE_ORDER, GameCameraBound, StasisPod, TimedEvent, advance_wake_at_readiness,
        observe_room, observe_wake_phase, phase_name, record_room_check, retarget_gameplay_camera,
    };
    use crate::harness::{Content, InputAdapter, Scenario, TICKS_PER_SECOND};
    use crate::player::PlayerPitch;
    use crate::scene::SimWakePhase;

    /// A fresh run state over a default gameplay scenario, in a scratch
    /// output directory (the observation never touches disk).
    fn gameplay_state() -> HarnessState {
        HarnessState::new(
            Scenario {
                content: Content::Gameplay,
                ..Scenario::default()
            },
            std::env::temp_dir(),
            String::new(),
            InputAdapter::new(TICKS_PER_SECOND),
        )
    }

    /// An app with the asset stores the scene build needs, the scene plugin
    /// itself, the run state, and the observation system. No renderer:
    /// startup spawns meshes, materials, and the pod groups.
    fn scene_app() -> bevy::app::App {
        let mut app = bevy::app::App::new();
        app.add_plugins((TaskPoolPlugin::default(), AssetPlugin::default()));
        app.init_asset::<bevy::mesh::Mesh>()
            .init_asset::<bevy::pbr::StandardMaterial>();
        app.add_plugins(crate::scene::StasisScenePlugin);
        app.insert_resource(gameplay_state());
        app.add_systems(bevy::app::Update, observe_room);
        app
    }

    #[test]
    fn the_room_observation_records_both_counts_and_fails_on_a_mismatch() {
        // The registry is the expected side; the world is the observed side.
        // A missing scene (registry says 7, world has 0 pod groups) is a
        // terminal scenario failure naming both numbers. The matching
        // observation never fails.
        let mut state = gameplay_state();
        record_room_check(&mut state, 7, 0);
        let check = state.events.iter().find_map(|event| match event {
            TimedEvent::RoomCheck {
                pods_expected,
                pods_present,
                ..
            } => Some((*pods_expected, *pods_present)),
            _ => None,
        });
        assert_eq!(check, Some((7, 0)), "the observation records both numbers");
        let what = state.failed.expect("a mismatch fails the scenario");
        assert!(what.contains("7 pods"), "both counts are named: {what}");
        assert!(what.contains("0 pod"), "both counts are named: {what}");
        let mut state = gameplay_state();
        record_room_check(&mut state, 7, 7);
        assert!(state.failed.is_none());
        assert!(
            state
                .events
                .iter()
                .any(|event| matches!(event, TimedEvent::RoomCheck { .. }))
        );
    }

    #[test]
    fn the_observation_runs_once_and_sees_every_built_pod() {
        let mut app = scene_app();
        app.update();
        app.update();
        let state = app.world().resource::<HarnessState>();
        let checks: Vec<_> = state
            .events
            .iter()
            .filter(|event| matches!(event, TimedEvent::RoomCheck { .. }))
            .collect();
        assert_eq!(checks.len(), 1, "exactly one observation per run");
        let expected = gone_sim::PodRegistry::frozen().pods().len();
        let TimedEvent::RoomCheck {
            pods_expected,
            pods_present,
            ..
        } = checks[0]
        else {
            unreachable!("filtered above")
        };
        assert_eq!(*pods_expected, expected);
        assert_eq!(*pods_present, expected, "every built pod group is found");
        assert!(state.failed.is_none());
    }

    #[test]
    fn a_broken_scene_fails_the_scenario_through_the_observation() {
        // Negative proof (scene side): pods built and then removed before the
        // observation's first run, the world shape a broken or omitted scene
        // build produces, must fail the run app-side with a report failure.
        let mut app = scene_app();
        app.update();
        let mut pods = app.world_mut().query_filtered::<Entity, With<StasisPod>>();
        let ids: Vec<_> = pods.iter(app.world()).collect();
        assert!(!ids.is_empty(), "the scene built its pods");
        for id in ids {
            app.world_mut().despawn(id);
        }
        // A fresh run state so the assertion reads this run's observation.
        app.insert_resource(gameplay_state());
        app.add_systems(bevy::app::Update, observe_room);
        app.update();
        let state = app.world().resource::<HarnessState>();
        let what = state.failed.as_deref().expect("broken scene fails the run");
        assert!(what.contains("mismatch"), "names the failure: {what}");
        assert!(
            state
                .events
                .iter()
                .any(|event| matches!(event, TimedEvent::RoomCheck { .. }))
        );
    }

    #[test]
    fn the_room_check_event_sorts_right_after_the_ready_boundary() {
        // The observation happens before any tick runs; the report's
        // canonical order must place it immediately after the ready event
        // and before every input or beat event.
        let mut state = gameplay_state();
        state.events.push(TimedEvent::Beat {
            name: "beat-a".to_owned(),
            tick: 2,
            frame: 2,
            request_id: 1,
        });
        record_room_check(&mut state, 7, 7);
        state.events.push(TimedEvent::Ready { frame: 0 });
        crate::harness::sort_events(&mut state.events);
        let kinds: Vec<String> = state
            .events
            .iter()
            .map(|event| match event {
                TimedEvent::Ready { .. } => "ready".to_owned(),
                TimedEvent::RoomCheck { .. } => "room".to_owned(),
                TimedEvent::Beat { .. } => "beat".to_owned(),
                _ => "other".to_owned(),
            })
            .collect();
        assert_eq!(kinds, ["ready", "room", "beat"]);
    }

    #[test]
    fn the_retarget_binds_the_game_camera_and_opens_the_binding_leg() {
        // The rig camera spawns (as the player plugin's Startup would), the
        // retarget binds it into the capture target on the first update, and
        // the binding flag flips: the readiness proof's "rendered game
        // frame" leg. Without the flag the proof readback could land on a
        // frame only the chip overlay rendered.
        let mut app = App::new();
        app.add_plugins((TaskPoolPlugin::default(), AssetPlugin::default()));
        app.init_asset::<Image>();
        let handle = {
            let mut images = app.world_mut().resource_mut::<Assets<Image>>();
            images.add(Image::default())
        };
        app.insert_resource(super::CaptureTarget(Some(handle)));
        app.insert_resource(GameCameraBound::default());
        app.add_systems(Update, retarget_gameplay_camera);
        app.world_mut().spawn((Camera3d::default(), PlayerPitch));
        assert!(
            !app.world().resource::<GameCameraBound>().0,
            "nothing is bound before the first update"
        );
        app.update();
        assert!(
            app.world().resource::<GameCameraBound>().0,
            "the retarget sets the binding flag"
        );
        let mut cams = app
            .world_mut()
            .query_filtered::<(&Camera, &RenderTarget, &Msaa), With<PlayerPitch>>();
        let (camera, target, msaa) = cams.single(app.world()).expect("the rig camera exists");
        assert_eq!(camera.order, GAMEPLAY_SCENE_ORDER);
        assert!(
            matches!(target, RenderTarget::Image(_)),
            "the rig camera renders into the capture target"
        );
        assert_eq!(*msaa, Msaa::Off, "the capture view keeps the lattice crisp");
    }

    #[test]
    fn the_wake_override_advances_only_at_the_readiness_boundary() {
        // The barrier's phase leg in isolation: loading holds the authored
        // `Waking`; the announced boundary advances the machine exactly once
        // (the machine's idempotent boundary plus the once-flag).
        let mut app = App::new();
        app.insert_resource(gameplay_state());
        app.insert_resource(SimWakePhase::new(WakePhase::Waking));
        app.add_systems(Update, advance_wake_at_readiness);
        app.update();
        assert_eq!(
            app.world().resource::<SimWakePhase>().phase(),
            WakePhase::Waking,
            "loading holds the authored opening"
        );
        app.world_mut().resource_mut::<HarnessState>().announced = true;
        app.update();
        assert_eq!(
            app.world().resource::<SimWakePhase>().phase(),
            WakePhase::AwakeInPod,
            "the boundary advances the machine"
        );
        for _ in 0..2 {
            app.update();
        }
        assert_eq!(
            app.world().resource::<SimWakePhase>().phase(),
            WakePhase::AwakeInPod,
            "the override fires exactly once"
        );
    }

    /// The phase names the observation records, in report order.
    fn observed_phases(app: &App) -> Vec<&str> {
        app.world()
            .resource::<HarnessState>()
            .events
            .iter()
            .filter_map(|event| match event {
                TimedEvent::WakePhase { phase, .. } => Some(phase.as_str()),
                _ => None,
            })
            .collect()
    }

    #[test]
    fn the_phase_observation_records_the_progression_once_per_change() {
        // The observation records the authored opening on the run's first
        // update and each machine transition exactly once, on the update it
        // happened; an update where nothing changed records nothing. The
        // full sequence is the wake progression in order.
        let mut app = App::new();
        app.insert_resource(gameplay_state());
        app.insert_resource(SimWakePhase::new(WakePhase::Waking));
        app.add_systems(Update, observe_wake_phase);
        app.update();
        app.update();
        assert_eq!(observed_phases(&app), ["waking"], "exactly the opening");

        // The wake override's transition lands on its own update.
        let transition = app
            .world_mut()
            .resource_mut::<SimWakePhase>()
            .wake_complete();
        assert!(
            matches!(transition, PhaseTransition::Advanced { .. }),
            "the override advanced the machine, got {transition:?}"
        );
        app.update();
        app.update();
        assert_eq!(observed_phases(&app), ["waking", "awake_in_pod"]);

        // The get-up's two transitions drive through the machine the same
        // way the exit controller drives them.
        let transition = {
            let mut machine = app.world_mut().resource_mut::<SimWakePhase>();
            machine
                .machine_mut()
                .request_pod_exit(gone_sim::phase::InputEdge::Rising)
        };
        assert!(
            matches!(transition, PhaseTransition::Advanced { .. }),
            "the exit command advanced the machine, got {transition:?}"
        );
        app.update();
        assert_eq!(
            observed_phases(&app),
            ["waking", "awake_in_pod", "exiting_pod"]
        );
        {
            let mut machine = app.world_mut().resource_mut::<SimWakePhase>();
            machine.machine_mut().get_up_complete().expect("legal here");
        }
        app.update();
        assert_eq!(
            observed_phases(&app),
            ["waking", "awake_in_pod", "exiting_pod", "standing"]
        );
    }

    #[test]
    fn the_phase_observation_stamps_the_just_driven_tick() {
        // The stamp follows the beat-pin convention: the tick and frame that
        // just drove, so a transition observed mid-run names its tick. Before
        // the first driven tick the run's moment is tick zero.
        let mut app = App::new();
        app.insert_resource(gameplay_state());
        app.insert_resource(SimWakePhase::new(WakePhase::Waking));
        app.add_systems(Update, observe_wake_phase);
        app.update();
        let stamps: Vec<(u64, u64)> = app
            .world()
            .resource::<HarnessState>()
            .events
            .iter()
            .filter_map(|event| match event {
                TimedEvent::WakePhase { tick, frame, .. } => Some((*tick, *frame)),
                _ => None,
            })
            .collect();
        assert_eq!(stamps, [(0, 0)], "the opening stamps the run's start");

        {
            let mut state = app.world_mut().resource_mut::<HarnessState>();
            state.tick = 31;
            state.frame = 31;
        }
        let transition = app
            .world_mut()
            .resource_mut::<SimWakePhase>()
            .wake_complete();
        assert!(
            matches!(transition, PhaseTransition::Advanced { .. }),
            "the override advanced the machine, got {transition:?}"
        );
        app.update();
        let stamps: Vec<(u64, u64)> = app
            .world()
            .resource::<HarnessState>()
            .events
            .iter()
            .filter_map(|event| match event {
                TimedEvent::WakePhase { tick, frame, .. } => Some((*tick, *frame)),
                _ => None,
            })
            .collect();
        assert_eq!(
            stamps,
            [(0, 0), (30, 30)],
            "a mid-run observation stamps the tick that just drove"
        );
    }

    #[test]
    fn every_wake_phase_has_a_protocol_name() {
        assert_eq!(phase_name(WakePhase::Waking), "waking");
        assert_eq!(phase_name(WakePhase::AwakeInPod), "awake_in_pod");
        assert_eq!(phase_name(WakePhase::ExitingPod), "exiting_pod");
        assert_eq!(phase_name(WakePhase::Standing), "standing");
    }
}
