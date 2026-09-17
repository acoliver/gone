//! Coverage of the steadying walk: the frozen ramp curve (exact start,
//! one time constant, settled full speed), yaw-framed direction control,
//! wall slide and head-on stop semantics through the landed resolver,
//! the once-per-tick intent rule, the temporal-not-directional ramp, and
//! every fail-fast input rejection.

use std::f32::consts::{FRAC_PI_2, PI};

use glam::Vec3;

use super::{IntentAxis, MoveIntent, WalkContact, WalkError, WalkState};
use crate::colliders::{Aabb, ColliderSet};
use crate::controller::{
    CAPSULE_RADIUS, CAPSULE_STANDING_HEIGHT, MAX_INPUT_LENGTH, PENETRATION_TOLERANCE,
    STEADY_INITIAL_SPEED_FACTOR, STEADYING_TIME_CONSTANT, SURVIVAL_WALK_SPEED,
};
use crate::phase::WakePhase;
use crate::resolve::{Capsule, ResolveError};

/// Displacement epsilon for free-flight expectations (pure products of
/// the frozen constants, exact to a few ulps).
const FLIGHT_EPSILON: f32 = 1e-5;

/// Displacement epsilon for resolved stops (the resolver's own house
/// tolerance for swept contact expectations).
const STOP_EPSILON: f32 = 1e-3;

/// Speed epsilon for the ramp's closed-form expectations.
const SPEED_EPSILON: f32 = 1e-5;

/// A standing capsule whose foot sphere rests at height `foot_y`.
fn standing(x: f32, foot_y: f32, z: f32) -> Capsule {
    let segment = CAPSULE_STANDING_HEIGHT - 2.0 * CAPSULE_RADIUS;
    Capsule {
        foot: Vec3::new(x, foot_y + CAPSULE_RADIUS, z),
        head: Vec3::new(x, foot_y + CAPSULE_RADIUS + segment, z),
    }
}

/// A walk state standing at the room origin, ready to step.
fn started() -> WalkState {
    WalkState::start(&WakePhase::Standing, standing(0.0, 0.0, 0.0))
        .expect("standing start is legal")
}

/// A box spanning the given min and max corners.
fn box_between(min: (f32, f32, f32), max: (f32, f32, f32)) -> Aabb {
    Aabb::from_min_max(Vec3::from(min), Vec3::from(max)).expect("test box is valid")
}

/// A scene: a floor slab topping out at y = 0 plus the given boxes.
fn scene(extra: &[Aabb]) -> ColliderSet {
    let mut set = ColliderSet::new();
    set.insert(box_between((-10.0, -1.0, -10.0), (10.0, 0.0, 10.0)));
    for aabb in extra {
        set.insert(*aabb);
    }
    set
}

/// The empty scene: no colliders at all.
fn empty_scene() -> ColliderSet {
    ColliderSet::new()
}

/// A look-frame intent at `yaw`; test axes are finite by construction.
fn intent(yaw: f32, forward: f32, strafe: f32) -> MoveIntent {
    MoveIntent::new(yaw, forward, strafe).expect("test intent is finite")
}

/// Asserts per-component displacement closeness.
fn assert_close(actual: Vec3, expected: Vec3, epsilon: f32, label: &str) {
    let drift = (actual - expected).abs();
    assert!(
        drift.x < epsilon && drift.y < epsilon && drift.z < epsilon,
        "{label}: expected {expected:?}, walked {actual:?}"
    );
}

/// The ramp starts bitwise on the exact frozen initial product.
#[test]
fn speed_at_a_full_stop_is_exactly_the_frozen_initial_product() {
    let state = started();
    assert_eq!(
        state.speed().to_bits(),
        (STEADY_INITIAL_SPEED_FACTOR * SURVIVAL_WALK_SPEED).to_bits(),
        "the first step must move at exactly the frozen factor times full speed"
    );
}

/// At one time constant the speed is the frozen exponential-approach
/// value, and the tick that consumed the constant moved at the start
/// speed: the clock advances after the sweep.
#[test]
fn speed_at_one_time_constant_is_the_exponential_approach_value() {
    let mut state = started();
    let stepped = state
        .step(
            intent(0.0, 1.0, 0.0),
            STEADYING_TIME_CONSTANT,
            &empty_scene(),
        )
        .expect("free step resolves");
    let start_speed = STEADY_INITIAL_SPEED_FACTOR * SURVIVAL_WALK_SPEED;
    assert_close(
        stepped.displacement,
        Vec3::new(0.0, 0.0, start_speed * STEADYING_TIME_CONSTANT),
        FLIGHT_EPSILON,
        "the tick moves at the start speed",
    );
    let expected =
        SURVIVAL_WALK_SPEED * (1.0 - (1.0 - STEADY_INITIAL_SPEED_FACTOR) * (-1.0f32).exp());
    assert!(
        (state.speed() - expected).abs() < SPEED_EPSILON,
        "speed at one time constant: got {}, expected {expected}",
        state.speed()
    );
}

/// After many time constants the speed is within epsilon of full
/// survival pace and the approach never overshoots it.
#[test]
fn speed_settles_within_epsilon_of_full_speed() {
    let mut state = started();
    for _ in 0..20 {
        state
            .step(
                intent(0.0, 1.0, 0.0),
                STEADYING_TIME_CONSTANT,
                &empty_scene(),
            )
            .expect("free steps resolve");
        state.end_tick();
        assert!(
            state.speed() <= SURVIVAL_WALK_SPEED,
            "the exponential approach never overshoots full speed"
        );
    }
    assert!(
        (SURVIVAL_WALK_SPEED - state.speed()).abs() < 1e-6,
        "speed after twenty time constants: got {}",
        state.speed()
    );
}

/// Direction control through yaw: forward in a turned frame moves the
/// capsule along that frame's world direction, strafe along its right,
/// back opposite the look axis; a free tick reads Free and ungrounded
/// in the empty scene.
#[test]
fn yaw_frames_steer_the_capsule_across_the_world() {
    let dt = 0.1;
    let speed = STEADY_INITIAL_SPEED_FACTOR * SURVIVAL_WALK_SPEED;
    let cases = [
        (
            0.0,
            1.0,
            0.0,
            Vec3::new(0.0, 0.0, speed * dt),
            "forward at yaw 0",
        ),
        (
            FRAC_PI_2,
            1.0,
            0.0,
            Vec3::new(speed * dt, 0.0, 0.0),
            "forward at yaw pi/2",
        ),
        (
            FRAC_PI_2,
            0.0,
            1.0,
            Vec3::new(0.0, 0.0, -speed * dt),
            "strafe right at yaw pi/2",
        ),
        (
            FRAC_PI_2,
            -1.0,
            0.0,
            Vec3::new(-speed * dt, 0.0, 0.0),
            "back at yaw pi/2",
        ),
    ];
    for (yaw, forward, strafe, expected, label) in cases {
        let mut state = started();
        let stepped = state
            .step(intent(yaw, forward, strafe), dt, &empty_scene())
            .expect("free step resolves");
        assert_close(stepped.displacement, expected, FLIGHT_EPSILON, label);
        assert_eq!(stepped.contact, WalkContact::Free, "{label}");
        assert!(stepped.contact_normals.is_empty(), "{label}");
        assert!(!stepped.grounded, "{label}: no floor in the empty scene");
    }
}

/// A diagonal move into a wall slides: tangential progress survives,
/// the into-face axis stops one tolerance short of the face, the face's
/// normal is reported, and the floor reads grounded.
#[test]
fn wall_contact_slides_tangentially_and_stops_into_the_face() {
    let wall = box_between((-4.0, 0.0, 0.0), (4.0, 3.2, 0.2));
    let set = scene(&[wall]);
    let mut state = WalkState::start(&WakePhase::Standing, standing(0.0, 0.0, -1.0))
        .expect("standing start is legal");
    let stepped = state
        .step(intent(0.0, 1.0, 1.0), 4.0, &set)
        .expect("slide resolves");
    // Full tangential run into +X, into-face travel stopped at the wall
    // face minus the tolerance (the capsule face starts 0.7 m away).
    let tangential = STEADY_INITIAL_SPEED_FACTOR * SURVIVAL_WALK_SPEED * 4.0 / 2f32.sqrt();
    let into_face = 0.7 - PENETRATION_TOLERANCE;
    assert_close(
        stepped.displacement,
        Vec3::new(tangential, 0.0, into_face),
        STOP_EPSILON,
        "wall slide",
    );
    assert_eq!(stepped.contact, WalkContact::Sliding);
    assert_eq!(stepped.contact_normals, vec![Vec3::new(0.0, 0.0, -1.0)]);
    assert!(stepped.grounded, "walking the floor reads grounded");
}

/// A head-on move into a wall stops into the face: no tangential
/// progress survives, one normal is reported, and the capsule stays
/// grounded on the floor.
#[test]
fn head_on_contact_stops_into_the_face() {
    let wall = box_between((-4.0, 0.0, 0.0), (4.0, 3.2, 0.2));
    let set = scene(&[wall]);
    let mut state = WalkState::start(&WakePhase::Standing, standing(0.0, 0.0, -1.0))
        .expect("standing start is legal");
    let stepped = state
        .step(intent(0.0, 1.0, 0.0), 4.0, &set)
        .expect("head-on resolves");
    let into_face = 0.7 - PENETRATION_TOLERANCE;
    assert_close(
        stepped.displacement,
        Vec3::new(0.0, 0.0, into_face),
        STOP_EPSILON,
        "head-on stop",
    );
    assert_eq!(stepped.contact, WalkContact::Stopped);
    assert_eq!(stepped.contact_normals, vec![Vec3::new(0.0, 0.0, -1.0)]);
    assert!(stepped.grounded);
}

/// The tick's intent is consumed exactly once: a second step in the
/// same tick is a typed error that mutates nothing, and `end_tick` opens
/// the next one (idempotently).
#[test]
fn intent_is_consumed_exactly_once_per_tick() {
    let mut state = started();
    state
        .step(intent(0.0, 1.0, 0.0), 0.1, &empty_scene())
        .expect("first step resolves");
    let capsule_after_first = state.capsule();
    let speed_after_first = state.speed();
    let second = state.step(intent(0.0, 1.0, 0.0), 0.1, &empty_scene());
    assert_eq!(second, Err(WalkError::StepAlreadyTaken));
    assert_eq!(
        state.capsule(),
        capsule_after_first,
        "the rejected step moved nothing"
    );
    assert_eq!(
        state.speed().to_bits(),
        speed_after_first.to_bits(),
        "the rejected step advanced no ramp"
    );
    let text = second.unwrap_err().to_string();
    assert!(text.contains("tick"), "display: {text}");
    state.end_tick();
    state.end_tick();
    let third = state.step(intent(0.0, 1.0, 0.0), 0.1, &empty_scene());
    assert!(third.is_ok(), "end_tick opens the next tick, idempotently");
}

/// The ramp is temporal, not directional: turning mid-walk never resets
/// it, and the same (ticks, dt) sequence yields the same speed curve
/// regardless of the directions stepped.
#[test]
fn the_ramp_is_temporal_and_not_directional() {
    let mut turned = started();
    for yaw in [0.0, 0.0, 0.0, FRAC_PI_2, FRAC_PI_2, PI] {
        turned
            .step(intent(yaw, 1.0, 0.0), 0.5, &empty_scene())
            .expect("free step resolves");
        turned.end_tick();
    }
    let mut straight = started();
    for _ in 0..6 {
        straight
            .step(intent(0.0, 1.0, 0.0), 0.5, &empty_scene())
            .expect("free step resolves");
        straight.end_tick();
    }
    assert_eq!(
        turned.speed().to_bits(),
        straight.speed().to_bits(),
        "direction changes must not touch the steadying clock"
    );
}

/// Start consumes nothing and requires Standing: every earlier phase is
/// a typed rejection naming both phases, and Standing starts.
#[test]
fn start_requires_the_standing_phase() {
    for current in [
        WakePhase::Waking,
        WakePhase::AwakeInPod,
        WakePhase::ExitingPod,
    ] {
        assert_eq!(
            WalkState::start(&current, standing(0.0, 0.0, 0.0)),
            Err(WalkError::WrongPhase {
                expected: WakePhase::Standing,
                current,
            })
        );
    }
    assert!(
        WalkState::start(&WakePhase::Standing, standing(0.0, 0.0, 0.0)).is_ok(),
        "Standing starts the walk"
    );
}

/// Tick seconds that are NaN, infinite, or non-positive are rejected
/// and consume nothing: the tick stays open for a valid step.
#[test]
fn invalid_tick_seconds_are_rejected_without_consuming_the_tick() {
    let mut state = started();
    for got in [0.0, -0.1, f32::INFINITY] {
        assert_eq!(
            state.step(intent(0.0, 1.0, 0.0), got, &empty_scene()),
            Err(WalkError::InvalidTickSeconds { got })
        );
    }
    assert!(matches!(
        state.step(intent(0.0, 1.0, 0.0), f32::NAN, &empty_scene()),
        Err(WalkError::InvalidTickSeconds { got }) if got.is_nan()
    ));
    let stepped = state.step(intent(0.0, 1.0, 0.0), 0.1, &empty_scene());
    assert!(
        stepped.is_ok(),
        "the failed calls must not consume the tick"
    );
}

/// Non-finite intent axes and an unscalable magnitude are rejected,
/// naming the offending axis or value.
#[test]
fn non_finite_intent_inputs_are_rejected() {
    assert!(matches!(
        MoveIntent::new(0.0, f32::NAN, 0.0),
        Err(WalkError::NonFiniteIntentAxis {
            axis: IntentAxis::Forward,
            got
        }) if got.is_nan()
    ));
    assert!(matches!(
        MoveIntent::new(0.0, 0.0, f32::INFINITY),
        Err(WalkError::NonFiniteIntentAxis {
            axis: IntentAxis::Strafe,
            got
        }) if got.is_infinite()
    ));
    assert!(matches!(
        MoveIntent::new(f32::NAN, 0.0, 0.0),
        Err(WalkError::NonFiniteIntentAxis {
            axis: IntentAxis::Yaw,
            got
        }) if got.is_nan()
    ));
    assert_eq!(
        MoveIntent::new(0.0, f32::MAX, f32::MAX),
        Err(WalkError::NonFiniteIntentMagnitude { got: f32::INFINITY })
    );
}

/// Oversized intents clamp to the frozen input cap so diagonals never
/// outrun straight lines; sub-unit intents keep their magnitude.
#[test]
fn oversized_intents_clamp_and_sub_unit_intents_keep_magnitude() {
    let diagonal = intent(0.0, 1.0, 1.0);
    assert!(
        (diagonal.world_direction().length() - MAX_INPUT_LENGTH).abs() < 1e-6,
        "a clamped diagonal must resolve to unit length"
    );
    let half = intent(0.0, 0.5, 0.0);
    assert!(
        (half.world_direction().length() - 0.5).abs() < 1e-6,
        "a sub-unit intent keeps its magnitude"
    );

    let dt = 1.0;
    let speed = STEADY_INITIAL_SPEED_FACTOR * SURVIVAL_WALK_SPEED;
    let mut state = started();
    let stepped = state
        .step(diagonal, dt, &empty_scene())
        .expect("free step resolves");
    assert!(
        (stepped.displacement.length() - speed * dt).abs() < FLIGHT_EPSILON,
        "the clamped diagonal must not outrun a straight line: got {}",
        stepped.displacement.length()
    );
}

/// A capsule embedded in geometry is rejected by the resolver, the
/// failed step mutates nothing, and the tick stays open for a valid
/// step.
#[test]
fn a_resolver_rejection_mutates_nothing_and_consumes_nothing() {
    let mut set = ColliderSet::new();
    set.insert(box_between((-1.0, -1.0, -1.0), (1.0, 1.0, 1.0)));
    let embedded = Capsule {
        foot: Vec3::ZERO,
        head: Vec3::new(0.0, 1.15, 0.0),
    };
    let mut state =
        WalkState::start(&WakePhase::Standing, embedded).expect("standing start is legal");
    let before = state.capsule();
    assert_eq!(
        state.step(intent(0.0, 1.0, 0.0), 0.1, &set),
        Err(WalkError::Resolver(ResolveError::StartPenetration {
            index: 0
        }))
    );
    assert_eq!(state.capsule(), before, "the rejected step moved nothing");
    assert!(
        state
            .step(intent(0.0, 1.0, 0.0), 0.1, &empty_scene())
            .is_ok(),
        "the rejected step must not consume the tick"
    );
}

/// A starting capsule with a non-finite endpoint is rejected at start,
/// before any sweep can be poisoned.
#[test]
fn a_non_finite_starting_capsule_is_rejected() {
    let bad = Capsule {
        foot: Vec3::new(f32::NAN, CAPSULE_RADIUS, 0.0),
        head: Vec3::new(0.0, 1.45, 0.0),
    };
    assert_eq!(
        WalkState::start(&WakePhase::Standing, bad),
        Err(WalkError::NonFiniteCapsule)
    );
}
