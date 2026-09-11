//! The gameplay-full lane's runner side: the built-in scenario that plays the
//! whole opening beat and the machine verification over its report.
//!
//! The smoke lane proves the rig exists and scripted look turns it; this lane
//! proves the wake progression drives in order and the body carries the
//! player out of the pod and across the room toward the jammed hatch. Every
//! expectation is derived from the frozen simulation truth the app itself
//! builds from (the authored exit path and standing eye height via
//! `gone_app::placement_truth`, the controller constants and hatch placement
//! via the app's `gone_sim` re-export), never from literals and never from
//! the report under test.
//!
//! Three assertions sit beyond the smoke lane's checks:
//!
//! * **The phase sequence.** The report's wake-phase observations must read
//!   exactly the wake progression, in order: the authored `Waking` opening,
//!   the readiness override into `AwakeInPod`, the get-up's `ExitingPod`,
//!   and `Standing` at the exit waypoint.
//! * **The standing beat at the exit waypoint.** The beat's eye-point sample
//!   must equal the standing eye the authored exit path's waypoint pose
//!   projects to, within the sim's own pose arrival tolerance plus
//!   projection noise.
//! * **The door beat near the hatch.** The beat's eye must sit inside the
//!   room envelope at the standing eye height, its toward-the-hatch
//!   displacement must match the frozen steadying ramp consumed exactly as
//!   the sim consumes it, and its distance to the frozen hatch placement
//!   must be bounded by that same walk model.

use std::collections::BTreeMap;

use gone_app::gone_sim::PodRegistry;
use gone_app::gone_sim::controller::{
    CAPSULE_RADIUS, MAX_INPUT_LENGTH, PENETRATION_TOLERANCE, STEADY_INITIAL_SPEED_FACTOR,
    STEADYING_TIME_CONSTANT, SURVIVAL_WALK_SPEED,
};
use gone_app::gone_sim::exit::{EXIT_POSE_COUNT, POSE_TOLERANCE};
use gone_app::gone_sim::pods::{ROOM_CEILING_HEIGHT, ROOM_LENGTH, ROOM_WIDTH};
use gone_app::harness::report::{Report, TimedEvent};
use gone_app::harness::scenario::TICKS_PER_SECOND;
use gone_app::harness::{
    Action, Beat, Button, Content, Key, Scenario, ScenarioMode, ScriptedAction,
};
use gone_app::placement_truth::{STANDING_EYE_HEIGHT, player_exit_path};

use super::{AnchoredBeat, verify_room, verify_yaw_replay};

/// The built-in scenario's name: the artifact directory name and the
/// runner's dispatch key.
pub const GAMEPLAY_FULL_SCENARIO_NAME: &str = "gameplay-full";

/// The beat the lane pins once the get-up lands at the exit waypoint.
const STANDING_BEAT: &str = "standing";

/// The beat the lane pins after the walk, near the hatch.
const DOOR_BEAT: &str = "door";

/// The tick the activate press lands on: the readiness override has landed
/// the machine in `AwakeInPod` on tick 0, the first phase whose policy
/// accepts the exit intent, and two quiet ticks leave the boundary's own
/// events room.
const GET_UP_PRESS_TICK: u64 = 2;

/// The standing beat: the get-up drives one authored segment per tick from
/// the press (the controller is built on the press tick), so the waypoint
/// lands on press + 4 segments, and the beat pins two quiet ticks later on
/// the settled standing pose.
const STANDING_BEAT_TICK: u64 = GET_UP_PRESS_TICK + EXIT_POSE_COUNT as u64 + 1;

/// The scripted turn: the spawn yaw continues the pod's opening (facing the
/// central aisle), so a -90 degree look aims the walk straight down +X, the
/// hatch wall's direction, along an obstacle-free line the whole way.
const TURN_TICK: u64 = 12;
const TURN_DEG: f32 = -90.0;

/// The walk: forward intent on `WALK_TICKS` consecutive ticks. The frozen
/// ramp covers about 9.3 m over that many ticks at 60 ticks per second,
/// which stops the player more than a meter short of the +X wall (the
/// full-speed bound over the same ticks stays short of it too), so the sweep
/// is never clamped and the expected displacement is the ramp's exact sum.
const WALK_FIRST_TICK: u64 = 20;
const WALK_TICKS: u64 = 660;

/// The door beat: the last movement tick plus a few quiet ones, so the
/// pinned sample is the settled post-walk pose.
const DOOR_BEAT_TICK: u64 = WALK_FIRST_TICK + WALK_TICKS + 5;

/// The clean-close deadline: the last beat lands inside 690 driven frames;
/// the deadline adds headroom and never binds on the happy path.
const MAX_FRAMES: u64 = 900;

/// The door beat lands inside the deadline: a scenario whose beat outruns
/// its own clean-close budget is an authoring bug, failed at compile time.
const _: () = assert!(DOOR_BEAT_TICK < MAX_FRAMES);

/// The built-in gameplay-full scenario: activate press to start the authored
/// get-up, a 90 degree turn once standing, then eleven scripted seconds of
/// forward walking toward the hatch wall, with beats pinned at the exit
/// waypoint and near the hatch.
#[must_use]
pub fn gameplay_full_scenario() -> Scenario {
    let mut actions = vec![
        ScriptedAction::press(GET_UP_PRESS_TICK, Key::Activate),
        ScriptedAction::release(GET_UP_PRESS_TICK, Key::Activate),
        ScriptedAction::look(TURN_TICK, TURN_DEG, 0.0),
    ];
    for tick in WALK_FIRST_TICK..WALK_FIRST_TICK + WALK_TICKS {
        actions.push(ScriptedAction::move_delta(tick, 1.0, 0.0));
    }
    Scenario {
        name: GAMEPLAY_FULL_SCENARIO_NAME.to_owned(),
        seed: 1234,
        ticks_per_second: TICKS_PER_SECOND,
        actions,
        beats: vec![
            Beat::new(STANDING_BEAT, STANDING_BEAT_TICK),
            Beat::new(DOOR_BEAT, DOOR_BEAT_TICK),
        ],
        pacing: None,
        max_frames: MAX_FRAMES,
        mode: ScenarioMode::Capture,
        warmup_frames: 0,
        sample_frames: 0,
        content: Content::Gameplay,
    }
}

/// Tolerance for one position-axis comparison, in meters: the sim's own pose
/// arrival tolerance (a sweep stopping this close counts as reaching the
/// pose) plus slack for the eye projection's f32 rounding, orders below
/// anything a wrong pose could produce.
const EYE_TOLERANCE_METERS: f32 = POSE_TOLERANCE + 1e-3;

/// Tolerance for the walk displacement comparison, in meters: the per-tick
/// f32 sum over hundreds of steps accumulates well under a millimeter, so
/// this sits orders above the noise and far below any real ramp or wiring
/// difference.
const WALK_TOLERANCE_METERS: f32 = 0.05;

/// The protocol names of the wake phases in progression order (the app
/// records `snake_case` strings; the app-side `phase_name` is their single
/// home, and a drift fails this assertion loudly).
const WAKE_PROGRESSION: [&str; 4] = ["waking", "awake_in_pod", "exiting_pod", "standing"];

/// Verify a gameplay-full run's report: the shared gameplay checks (room
/// presence, the scripted-look replay over the beat-pinned samples), then
/// the lane's own wake progression, waypoint, and door assertions.
///
/// # Errors
/// A message naming the first failed check, in order: the room observation,
/// the wake phase sequence, a beat missing its pinned samples, the yaw
/// replay, the exit waypoint, or the door beat's bounds and walk.
pub fn verify_gameplay_full(scenario: &Scenario, report: &Report) -> Result<(), String> {
    verify_room(report)?;
    verify_wake_phase_sequence(report)?;
    let anchored = super::beat_anchored_samples(report)?;
    let yaw_samples: Vec<(u64, f32)> = anchored.iter().map(|beat| (beat.tick, beat.yaw)).collect();
    verify_yaw_replay(scenario, &yaw_samples)?;
    let standing = anchored_beat(&anchored, STANDING_BEAT)?;
    let door = anchored_beat(&anchored, DOOR_BEAT)?;
    verify_standing_at_waypoint(standing)?;
    verify_door_beat(scenario, beat_eye(standing)?, door)
}

/// The wake progression assertion: the report's wake-phase observations, in
/// report order, must be exactly the progression, each phase once.
fn verify_wake_phase_sequence(report: &Report) -> Result<(), String> {
    let observed: Vec<&str> = report
        .events
        .iter()
        .filter_map(|event| match event {
            TimedEvent::WakePhase { phase, .. } => Some(phase.as_str()),
            _ => None,
        })
        .collect();
    if observed == WAKE_PROGRESSION {
        return Ok(());
    }
    Err(format!(
        "the run's wake phases were {observed:?}, expected the progression \
         {WAKE_PROGRESSION:?} in order"
    ))
}

/// The anchored beat named `name`, or an error naming the gap.
fn anchored_beat<'a>(anchored: &'a [AnchoredBeat], name: &str) -> Result<&'a AnchoredBeat, String> {
    anchored
        .iter()
        .find(|beat| beat.name == name)
        .ok_or_else(|| format!("the report has no `{name}` beat sample: the lane pins one"))
}

/// The beat's eye-point sample, or an error naming the missing sample.
fn beat_eye(beat: &AnchoredBeat) -> Result<[f32; 3], String> {
    beat.eye.ok_or_else(|| {
        format!(
            "beat `{}` has no player-position sample at its pinned (tick {}): \
             the gameplay lane samples the rig's eye at every pin",
            beat.name, beat.tick
        )
    })
}

/// The exit waypoint assertion: the standing beat's eye must equal the
/// standing eye point the authored exit path's waypoint pose projects to
/// (the foot sphere carried up to the standing eye height), per axis within
/// [`EYE_TOLERANCE_METERS`].
fn verify_standing_at_waypoint(beat: &AnchoredBeat) -> Result<(), String> {
    let eye = beat_eye(beat)?;
    let foot = player_exit_path().waypoint().foot();
    let expected = [
        foot.x,
        foot.y - CAPSULE_RADIUS + STANDING_EYE_HEIGHT,
        foot.z,
    ];
    for (axis, (measured, expected)) in eye.iter().zip(expected).enumerate() {
        if (measured - expected).abs() > EYE_TOLERANCE_METERS {
            return Err(format!(
                "the `{}` beat's eye is not at the exit waypoint: {} measured \
                 {measured:.4} m, expected {expected:.4} m (tolerance \
                 {EYE_TOLERANCE_METERS} m)",
                beat.name, AXIS_NAMES[axis],
            ));
        }
    }
    Ok(())
}

/// Axis names for position error messages.
const AXIS_NAMES: [&str; 3] = ["x", "y", "z"];

/// The door beat's assertions: inside the room envelope, at the standing eye
/// height, displaced from the standing beat by the scripted walk's frozen
/// ramp amount, and near the hatch.
fn verify_door_beat(
    scenario: &Scenario,
    standing_eye: [f32; 3],
    door: &AnchoredBeat,
) -> Result<(), String> {
    let eye = beat_eye(door)?;
    verify_room_bounds(&eye)?;
    verify_standing_eye_height(&eye)?;
    let expected = expected_walk_displacement(scenario)?;
    verify_walk_displacement(standing_eye, &eye, expected)?;
    verify_near_the_hatch(standing_eye, &eye, expected)
}

/// The room envelope the resolver keeps the capsule inside, with the
/// resolver's own penetration tolerance as the touching allowance.
fn verify_room_bounds(eye: &[f32; 3]) -> Result<(), String> {
    let half_length = ROOM_LENGTH / 2.0 + PENETRATION_TOLERANCE;
    let half_width = ROOM_WIDTH / 2.0 + PENETRATION_TOLERANCE;
    let inside = eye[0].abs() <= half_length
        && eye[2].abs() <= half_width
        && eye[1] >= 0.0
        && eye[1] <= ROOM_CEILING_HEIGHT;
    if inside {
        return Ok(());
    }
    Err(format!(
        "the `{DOOR_BEAT}` beat's eye is outside the room: ({:.3}, {:.3}, {:.3}), \
         bounds x +/-{half_length:.3}, z +/-{half_width:.3}, y 0..{ROOM_CEILING_HEIGHT:.3}",
        eye[0], eye[1], eye[2]
    ))
}

/// The door beat stands on the room floor: its eye height is the frozen
/// standing eye height above the floor (the capsule rest adds the resolver's
/// penetration tolerance, which the standing-eye projection consumes).
fn verify_standing_eye_height(eye: &[f32; 3]) -> Result<(), String> {
    let expected = PENETRATION_TOLERANCE + STANDING_EYE_HEIGHT;
    if (eye[1] - expected).abs() <= EYE_TOLERANCE_METERS {
        return Ok(());
    }
    Err(format!(
        "the `{DOOR_BEAT}` beat's eye is not at the standing height: y {:.4} m, \
         expected {expected:.4} m (tolerance {EYE_TOLERANCE_METERS} m)",
        eye[1]
    ))
}

/// The walk displacement assertion: the toward-the-hatch (+X) displacement
/// from the standing beat to the door beat must equal the scripted walk's
/// frozen ramp amount within [`WALK_TOLERANCE_METERS`], and the lateral
/// drift must stay inside what the yaw replay's own tolerance allows the
/// walk direction.
fn verify_walk_displacement(
    standing_eye: [f32; 3],
    door_eye: &[f32; 3],
    expected: f32,
) -> Result<(), String> {
    let measured = door_eye[0] - standing_eye[0];
    if (measured - expected).abs() > WALK_TOLERANCE_METERS {
        return Err(format!(
            "the scripted walk did not carry the player to the hatch: moved \
             {measured:.3} m along +X between the pinned beats, expected \
             {expected:.3} m (tolerance {WALK_TOLERANCE_METERS} m)"
        ));
    }
    let lateral = (door_eye[2] - standing_eye[2]).abs();
    let bound = expected * super::YAW_TOLERANCE_DEG.to_radians().tan() + WALK_TOLERANCE_METERS;
    if lateral > bound {
        return Err(format!(
            "the scripted walk drifted off the +X line: {lateral:.3} m lateral, \
             bound {bound:.3} m"
        ));
    }
    Ok(())
}

/// The near-the-hatch assertion: the door beat's planar distance to the
/// frozen hatch placement must not exceed the distance the verified walk
/// model leaves, within the walk tolerance.
fn verify_near_the_hatch(
    standing_eye: [f32; 3],
    door_eye: &[f32; 3],
    expected_displacement: f32,
) -> Result<(), String> {
    let hatch = PodRegistry::frozen().hatch().center;
    let expected_final = [standing_eye[0] + expected_displacement, standing_eye[2]];
    let expected = planar_distance(expected_final, hatch);
    let measured = planar_distance([door_eye[0], door_eye[2]], hatch);
    if measured <= expected + WALK_TOLERANCE_METERS {
        return Ok(());
    }
    Err(format!(
        "the `{DOOR_BEAT}` beat is not near the hatch: {measured:.3} m from the \
         frozen hatch placement, expected within {expected:.3} m of it"
    ))
}

/// Planar (x, z) distance between a point and the hatch center.
fn planar_distance(point: [f32; 2], hatch: (f32, f32)) -> f32 {
    ((point[0] - hatch.0).powi(2) + (point[1] - hatch.1).powi(2)).sqrt()
}

/// The expected toward-the-hatch displacement, in meters: the scripted
/// movement intents consumed exactly as the sim consumes them. The walk
/// clock starts at the first walked tick (the tick after the waypoint lands,
/// which is the press tick plus the authored segment count) and advances on
/// every walked tick, zero-intent or not; each movement tick moves its
/// clamped intent magnitude at the clock's speed. Intent offered before the
/// walk owns the body is dropped end-of-frame and contributes nothing.
///
/// # Errors
/// A message naming the missing script piece: no activate press to start the
/// get-up, or no movement intent after it.
fn expected_walk_displacement(scenario: &Scenario) -> Result<f32, String> {
    let press_tick = activate_press_tick(scenario)?;
    let intents = movement_intents(scenario);
    if intents.is_empty() {
        return Err("the scenario scripts no movement after the get-up".to_owned());
    }
    let first_walk_tick = press_tick + EXIT_POSE_COUNT as u64;
    let dt = tick_seconds(scenario.ticks_per_second);
    Ok(walk_displacement(&intents, first_walk_tick, dt))
}

/// The tick of the scenario's activate press (the get-up's start intent).
fn activate_press_tick(scenario: &Scenario) -> Result<u64, String> {
    scenario
        .actions
        .iter()
        .find(|action| {
            matches!(
                action.action,
                Action::Press {
                    button: Button::Key(Key::Activate),
                }
            )
        })
        .map(|action| action.tick)
        .ok_or_else(|| "the scenario scripts no activate press to start the get-up".to_owned())
}

/// The scenario's movement intents summed per tick, as the adapter sums the
/// actions that share one.
fn movement_intents(scenario: &Scenario) -> BTreeMap<u64, (f32, f32)> {
    let mut intents: BTreeMap<u64, (f32, f32)> = BTreeMap::new();
    for action in &scenario.actions {
        if let Action::MoveDelta { forward, strafe } = action.action {
            let entry = intents.entry(action.tick).or_insert((0.0, 0.0));
            entry.0 += forward;
            entry.1 += strafe;
        }
    }
    intents
}

/// One fixed tick's sim seconds, mirroring the app's scenario clock (rates
/// above `u16::MAX` saturate there on both sides).
fn tick_seconds(ticks_per_second: u64) -> f32 {
    1.0 / f32::from(u16::try_from(ticks_per_second).unwrap_or(u16::MAX))
}

/// The frozen ramp's displacement over the intent table: the walk clock
/// starts at zero on `first_walk_tick` and advances once per walked tick
/// through the last movement tick; each movement tick adds its clamped
/// intent magnitude at the clock's current speed. Ticks before the walk owns
/// the body are outside the range, which is exactly the sim's drop.
fn walk_displacement(intents: &BTreeMap<u64, (f32, f32)>, first_walk_tick: u64, dt: f32) -> f32 {
    let last_tick = intents
        .keys()
        .last()
        .copied()
        .unwrap_or(first_walk_tick)
        .max(first_walk_tick);
    let mut displacement = 0.0;
    let mut clock = 0.0;
    for tick in first_walk_tick..=last_tick {
        if let Some(&(forward, strafe)) = intents.get(&tick) {
            let magnitude = (forward * forward + strafe * strafe).sqrt();
            displacement += magnitude.min(MAX_INPUT_LENGTH) * steadied_speed(clock) * dt;
        }
        clock += dt;
    }
    displacement
}

/// The frozen steadying ramp at `seconds` of accumulated walk time: the
/// formula documented and frozen in `gone_sim::walk` over the frozen
/// controller constants, including the bitwise initial product at zero.
fn steadied_speed(seconds: f32) -> f32 {
    if seconds == 0.0 {
        return STEADY_INITIAL_SPEED_FACTOR * SURVIVAL_WALK_SPEED;
    }
    SURVIVAL_WALK_SPEED
        * (1.0 - (1.0 - STEADY_INITIAL_SPEED_FACTOR) * (-seconds / STEADYING_TIME_CONSTANT).exp())
}

#[cfg(test)]
mod tests {
    use std::collections::BTreeMap;

    use gone_app::gone_sim::controller::{
        CAPSULE_RADIUS, STEADY_INITIAL_SPEED_FACTOR, STEADYING_TIME_CONSTANT, SURVIVAL_WALK_SPEED,
    };
    use gone_app::gone_sim::pods::ROOM_LENGTH;
    use gone_app::harness::report::{BeatEntry, Identity, Report, TimedEvent};
    use gone_app::placement_truth::{STANDING_EYE_HEIGHT, player_exit_path};

    use super::{
        DOOR_BEAT, DOOR_BEAT_TICK, STANDING_BEAT, STANDING_BEAT_TICK, WAKE_PROGRESSION,
        WALK_TOLERANCE_METERS, expected_walk_displacement, gameplay_full_scenario, tick_seconds,
        verify_gameplay_full, walk_displacement,
    };

    /// The standing eye point the waypoint pose projects to: what a correct
    /// run's standing beat samples.
    fn waypoint_eye() -> [f32; 3] {
        let foot = player_exit_path().waypoint().foot();
        [
            foot.x,
            foot.y - CAPSULE_RADIUS + STANDING_EYE_HEIGHT,
            foot.z,
        ]
    }

    /// The beat manifest of the built-in scenario, pinned at frames matching
    /// their ticks.
    fn beat_manifest() -> BTreeMap<String, BeatEntry> {
        let mut beats = BTreeMap::new();
        for (index, (name, tick)) in [
            (STANDING_BEAT, STANDING_BEAT_TICK),
            (DOOR_BEAT, DOOR_BEAT_TICK),
        ]
        .iter()
        .enumerate()
        {
            beats.insert(
                (*name).to_owned(),
                BeatEntry {
                    file: format!("beats/{name}.png"),
                    tick: *tick,
                    frame: *tick,
                    request_id: index as u64 + 1,
                },
            );
        }
        beats
    }

    /// A synthetic gameplay-full report carrying a correct run's numbers,
    /// derived the way the verifier derives them: the room check, the four
    /// wake phases in order, and both beats with yaw and eye samples at
    /// their pinned moments. The door eye defaults to the walk model's
    /// endpoint; the parameters let each negative test tamper with one
    /// number. The walk amount itself comes from the module's own model,
    /// pinned separately by the ramp tests below; the live gameplay-full run
    /// is the end-to-end oracle that the model matches the real sim.
    fn full_report(standing_eye: [f32; 3], door_eye: [f32; 3]) -> Report {
        let mut report = Report::new(
            3,
            "gameplay-full",
            1234,
            Identity {
                app_hash: "a".into(),
                scenario_hash: "s".into(),
                config_hash: "c".into(),
            },
        );
        report.beats = beat_manifest();
        report.events.push(TimedEvent::Ready { frame: 0 });
        report.events.push(TimedEvent::RoomCheck {
            frame: 0,
            pods_expected: 7,
            pods_present: 7,
        });
        for (index, phase) in WAKE_PROGRESSION.iter().enumerate() {
            report.events.push(TimedEvent::WakePhase {
                tick: index as u64 * 2,
                frame: index as u64 * 2,
                phase: (*phase).to_owned(),
            });
        }
        // The standing beat's yaw is the authored spawn yaw (the pod opens
        // along -Z, reported wrapped to the -180 side); the door beat's yaw
        // is the wrapped result of the scripted -90 look, and the raw
        // difference across the wrap measures as the scripted -90.
        for (_name, tick, yaw, eye) in [
            (STANDING_BEAT, STANDING_BEAT_TICK, -180.0_f32, standing_eye),
            (DOOR_BEAT, DOOR_BEAT_TICK, 90.0_f32, door_eye),
        ] {
            report.events.push(TimedEvent::PlayerYaw {
                tick,
                frame: tick,
                yaw_degrees: yaw,
            });
            report.events.push(TimedEvent::PlayerPosition {
                tick,
                frame: tick,
                x: eye[0],
                y: eye[1],
                z: eye[2],
            });
        }
        report.events.push(TimedEvent::Complete {
            frame: DOOR_BEAT_TICK + 2,
        });
        report
    }

    #[test]
    fn a_report_with_the_derived_numbers_verifies() {
        let scenario = gameplay_full_scenario();
        let expected = expected_walk_displacement(&scenario).expect("the scenario walks");
        let standing = waypoint_eye();
        let door = [standing[0] + expected, standing[1], standing[2]];
        assert!(verify_gameplay_full(&scenario, &full_report(standing, door)).is_ok());
    }

    #[test]
    fn a_standing_beat_off_the_waypoint_fails() {
        let scenario = gameplay_full_scenario();
        let expected = expected_walk_displacement(&scenario).expect("the scenario walks");
        let mut standing = waypoint_eye();
        standing[1] += 0.05;
        let door = [standing[0] + expected, standing[1], standing[2]];
        let err = verify_gameplay_full(&scenario, &full_report(standing, door))
            .expect_err("a drifted waypoint must fail");
        assert!(err.contains("exit waypoint"), "names the failure: {err}");
    }

    #[test]
    fn a_phase_sequence_with_a_missing_phase_fails() {
        let scenario = gameplay_full_scenario();
        let expected = expected_walk_displacement(&scenario).expect("the scenario walks");
        let standing = waypoint_eye();
        let door = [standing[0] + expected, standing[1], standing[2]];
        let mut report = full_report(standing, door);
        report.events.retain(
            |event| !matches!(event, TimedEvent::WakePhase { phase, .. } if phase == "exiting_pod"),
        );
        let err = verify_gameplay_full(&scenario, &report).expect_err("a missing phase must fail");
        assert!(err.contains("wake phases"), "names the failure: {err}");
    }

    #[test]
    fn a_phase_sequence_out_of_order_fails() {
        let scenario = gameplay_full_scenario();
        let expected = expected_walk_displacement(&scenario).expect("the scenario walks");
        let standing = waypoint_eye();
        let door = [standing[0] + expected, standing[1], standing[2]];
        let mut report = full_report(standing, door);
        // Move the awake_in_pod observation to the end of the event list, the
        // shape a run whose override fired late would produce.
        let mut reordered = Vec::new();
        let mut moved = None;
        for event in std::mem::take(&mut report.events) {
            match event {
                TimedEvent::WakePhase { tick, frame, phase } if phase == "awake_in_pod" => {
                    moved = Some(TimedEvent::WakePhase { tick, frame, phase });
                }
                other => reordered.push(other),
            }
        }
        if let Some(moved) = moved {
            reordered.push(moved);
        }
        report.events = reordered;
        let err = verify_gameplay_full(&scenario, &report)
            .expect_err("a reordered progression must fail");
        assert!(err.contains("in order"), "names the failure: {err}");
    }

    #[test]
    fn a_door_beat_that_never_walked_fails() {
        let scenario = gameplay_full_scenario();
        let standing = waypoint_eye();
        let report = full_report(standing, standing);
        let err = verify_gameplay_full(&scenario, &report).expect_err("no walk must fail");
        assert!(err.contains("scripted walk"), "names the failure: {err}");
        assert!(err.contains("expected"), "names the scripted amount: {err}");
    }

    #[test]
    fn a_door_beat_outside_the_room_fails() {
        let scenario = gameplay_full_scenario();
        let expected = expected_walk_displacement(&scenario).expect("the scenario walks");
        let standing = waypoint_eye();
        let mut door = [standing[0] + expected, standing[1], standing[2]];
        door[0] = ROOM_LENGTH / 2.0 + 1.0;
        let err = verify_gameplay_full(&scenario, &full_report(standing, door))
            .expect_err("outside the room must fail");
        assert!(err.contains("outside the room"), "names the failure: {err}");
    }

    #[test]
    fn a_door_beat_missing_its_position_sample_fails() {
        let scenario = gameplay_full_scenario();
        let expected = expected_walk_displacement(&scenario).expect("the scenario walks");
        let standing = waypoint_eye();
        let door = [standing[0] + expected, standing[1], standing[2]];
        let mut report = full_report(standing, door);
        report
            .events
            .retain(|event| !matches!(event, TimedEvent::PlayerPosition { tick, .. } if *tick == super::DOOR_BEAT_TICK));
        let err = verify_gameplay_full(&scenario, &report).expect_err("a missing sample must fail");
        assert!(err.contains(DOOR_BEAT), "names the beat: {err}");
    }

    #[test]
    fn the_walk_model_starts_on_the_frozen_initial_product() {
        // One movement tick on the walk's first tick moves at the frozen
        // initial share of survival speed, bitwise: the ramp's documented
        // start.
        let mut intents = BTreeMap::new();
        intents.insert(0_u64, (1.0_f32, 0.0_f32));
        let dt = tick_seconds(60);
        let expected = STEADY_INITIAL_SPEED_FACTOR * SURVIVAL_WALK_SPEED * dt;
        let measured = walk_displacement(&intents, 0, dt);
        assert!((measured - expected).abs() < f32::EPSILON);
    }

    #[test]
    fn the_walk_clock_advances_on_zero_intent_ticks() {
        // The steadying clock is temporal, not directional: three idle ticks
        // between two movement ticks speed the second one up, exactly the
        // documented ramp at 3 ticks' worth of accumulated time.
        let mut intents = BTreeMap::new();
        intents.insert(0_u64, (1.0_f32, 0.0_f32));
        intents.insert(3_u64, (1.0_f32, 0.0_f32));
        let dt = tick_seconds(60);
        let measured = walk_displacement(&intents, 0, dt);
        let first = STEADY_INITIAL_SPEED_FACTOR * SURVIVAL_WALK_SPEED * dt;
        let second_speed = SURVIVAL_WALK_SPEED
            * (1.0
                - (1.0 - STEADY_INITIAL_SPEED_FACTOR)
                    * (-3.0 * dt / STEADYING_TIME_CONSTANT).exp());
        let expected = first + second_speed * dt;
        assert!(
            (measured - expected).abs() < 1e-6,
            "measured {measured}, expected {expected}"
        );
        assert!(measured > 2.0 * first, "the ramp rises across the gap");
    }

    #[test]
    fn intent_before_the_walk_owns_the_body_is_dropped() {
        // Movement on the tick before the walk starts contributes nothing:
        // the phase still owns the body, and the end-of-frame clear drops it.
        let mut intents = BTreeMap::new();
        intents.insert(0_u64, (1.0_f32, 0.0_f32));
        intents.insert(1_u64, (1.0_f32, 0.0_f32));
        let dt = tick_seconds(60);
        let measured = walk_displacement(&intents, 1, dt);
        let expected = STEADY_INITIAL_SPEED_FACTOR * SURVIVAL_WALK_SPEED * dt;
        assert!((measured - expected).abs() < f32::EPSILON);
    }

    #[test]
    fn the_built_in_scenario_walks_clear_of_the_wall_and_fits_its_deadline() {
        // The exact-sum comparison relies on the sweep never clamping: the
        // expected walk must stop short of the +X wall's capsule face, and
        // the door beat must land inside the clean-close deadline.
        let scenario = gameplay_full_scenario();
        let expected = expected_walk_displacement(&scenario).expect("the scenario walks");
        let foot = player_exit_path().waypoint().foot();
        let wall_face = ROOM_LENGTH / 2.0 - CAPSULE_RADIUS;
        assert!(
            foot.x + expected < wall_face - WALK_TOLERANCE_METERS,
            "the walk stops short of the wall: {} + {expected} vs {wall_face}",
            foot.x
        );
        // The beats are pinned in tick order, as the app's request cursor
        // requires.
        let ticks: Vec<u64> = scenario.beats.iter().map(|beat| beat.tick).collect();
        let mut sorted = ticks.clone();
        sorted.sort_unstable();
        assert_eq!(ticks, sorted);
        assert_eq!(scenario.beats[0].name, STANDING_BEAT);
        assert_eq!(scenario.beats[1].name, DOOR_BEAT);
    }

    #[test]
    fn the_scenario_scripts_the_turn_between_its_beats() {
        // The yaw replay must be satisfiable by construction: no look is
        // scripted before the standing beat, and the scripted -90 look lands
        // strictly before the door beat.
        let scenario = gameplay_full_scenario();
        let before = |tick: u64| -> f32 {
            scenario
                .actions
                .iter()
                .filter(|action| action.tick < tick)
                .filter_map(|action| match action.action {
                    gone_app::harness::Action::Look { yaw_deg, .. } => Some(yaw_deg),
                    _ => None,
                })
                .sum()
        };
        assert!((before(STANDING_BEAT_TICK) - 0.0).abs() < f32::EPSILON);
        assert!((before(DOOR_BEAT_TICK) + 90.0).abs() < f32::EPSILON);
    }
}
