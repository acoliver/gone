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
//! One deliberate sim override: the wake pass (issue #8) does not exist yet,
//! so the scene boots in `Waking`, where look is disallowed. A gameplay run
//! starts the phase machine at `AwakeInPod` instead, which is the first
//! state whose policy allows look; when the wake pass lands, the lane wakes
//! naturally and this override goes away.

use bevy::app::{App, Update};
use bevy::asset::{Assets, Handle};
use bevy::camera::{Camera, Camera2d, Camera3d, ClearColorConfig, RenderTarget};
use bevy::ecs::prelude::{Added, Commands, Entity, Local, Query, Res, ResMut, With};
use bevy::image::Image;
use bevy::math::Vec3;
use bevy::render::view::Msaa;
use bevy::transform::components::Transform;
use gone_sim::WakePhase;

use super::state::{HarnessState, RunMode, fail_scenario};
use super::{
    CaptureTarget, ChipSprite, ChipTexture, TimedEvent, capture_target_image, spawn_chip_sprite,
};
use crate::player::{GameplayInput, LookAngles, PlayerLookPlugin, PlayerPitch, ScriptedInput};
use crate::post::GamePostChainPlugin;
use crate::scene::{SimPodRegistry, SimWakePhase, StasisPod, StasisScenePlugin};

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
/// player look, in the same order the normal game adds them (each plugin's
/// build provides the resource the next consumes). Fails loudly at boot if
/// the wiring came out wrong, and starts the wake machine at `AwakeInPod`
/// (see the module docs for why).
pub(super) fn wire(app: &mut App) {
    app.add_plugins((GamePostChainPlugin, StasisScenePlugin, PlayerLookPlugin));
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
        app.world().get_resource::<GameplayInput>().is_some(),
        "gameplay content requires GameplayInput (PlayerLookPlugin provides it)"
    );
    assert!(
        app.world().get_resource::<LookAngles>().is_some(),
        "gameplay content requires LookAngles (PlayerLookPlugin provides it)"
    );
    app.insert_resource(SimWakePhase::new(WakePhase::AwakeInPod));
}

/// The gameplay content scene: the offscreen capture target and the corner
/// chip sprite (hidden until the readiness boundary, exactly as in
/// calibration), the chip overlay camera onto the capture target, and — in
/// canary mode — the static room view plus chip overlay into the window.
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
/// after the gameplay view, that never clears — its only content is the chip
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

/// The player rig's camera lookup: the entity owning the just-added 3D camera
/// tagged `PlayerPitch` (which marks the rig camera and nothing else), with
/// mutable access to its camera settings.
type RigCameraQuery<'w, 's> =
    Query<'w, 's, (Entity, &'static mut Camera), (Added<Camera3d>, With<PlayerPitch>)>;

/// Retarget the player rig's camera into the offscreen capture target on the
/// first update after the player plugin spawns it (`Added` fires exactly
/// once per rig), before this update renders. Also drops MSAA on the capture
/// view so the chip lattice stays pixel-crisp, matching the calibration
/// camera. `PlayerPitch` marks the rig camera and nothing else: the canary
/// spectator (also a 3D camera) never matches.
fn retarget_gameplay_camera(
    capture: Res<CaptureTarget>,
    mut commands: Commands,
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

/// The gameplay update registration: the same chain the calibration lane
/// runs, plus the first-update room observation, all inside the
/// `ScriptedInput` set so the player look chain orders after the adapter
/// step that feeds it. The rig-camera retarget runs outside the set: it only
/// touches the camera once, before the first render.
pub(super) fn register_update_systems(app: &mut App) {
    use super::{
        drive_ticks, finish_scan, perf_sample, readiness_boundary, request_beat_captures,
        request_present_probe, request_readiness_proof,
    };
    use bevy::ecs::schedule::IntoScheduleConfigs;
    app.add_systems(Update, retarget_gameplay_camera);
    app.add_systems(
        Update,
        (
            request_readiness_proof,
            readiness_boundary,
            request_present_probe,
            observe_room,
            request_beat_captures,
            drive_ticks,
            perf_sample,
            finish_scan,
        )
            .chain()
            .in_set(ScriptedInput),
    );
}

#[cfg(test)]
mod tests {
    use bevy::app::TaskPoolPlugin;
    use bevy::asset::{AssetApp, AssetPlugin};
    use bevy::ecs::prelude::{Entity, With};

    use super::super::state::HarnessState;
    use super::{StasisPod, TimedEvent, observe_room, record_room_check};
    use crate::harness::{Content, InputAdapter, Scenario};

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
            InputAdapter::new(),
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
        // observation's first run — the world shape a broken or omitted scene
        // build produces — must fail the run app-side with a report failure.
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
}
