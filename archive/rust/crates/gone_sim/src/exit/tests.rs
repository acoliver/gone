//! Coverage of the authored path and the get-up controller: the happy
//! drive visits every pose in order and lands Standing at the waypoint,
//! the waypoint follows the placement, the phase rejections are typed, a
//! shrunk aperture blocks with a typed error, resolver rejections wrap,
//! and the authored table stays internally consistent.

use super::{
    EXIT_MOUTH_WIDTH, EXIT_POSE_COUNT, ExitError, ExitPath, ExitPathError, GetUpController,
    POSE_TOLERANCE, SegmentMove, segment_move,
};
use crate::colliders::{Aabb, ColliderSet};
use crate::controller::{CAPSULE_RADIUS, PENETRATION_TOLERANCE};
use crate::phase::WakePhase;
use crate::pods::{POD_HEIGHT, POD_LENGTH, POD_WIDTH, PodPlacement, PodRegistry};
use crate::resolve::ResolveError;
use glam::Vec3;

/// Test-scene tray build mirroring the app-side pod cavity: 0.06 m
/// shell walls, a 0.1 m base slab, and a 0.012 m plate on top, so the
/// plate top — the tray floor the path is authored against — is real
/// geometry, not an assumption.
const CAVITY_WALL: f32 = 0.06;
const CAVITY_BASE: f32 = 0.1;
const CAVITY_PLATE: f32 = 0.012;
const TRAY_FLOOR: f32 = CAVITY_BASE + CAVITY_PLATE;

/// Test floor slab half-span, well past every pod placement used here.
const FLOOR_SPAN: f32 = 16.0;

/// The codebase's position tolerance for transformed expectations.
const POSITION_EPSILON: f32 = 1e-5;

/// Asserts stop precision for transformed room-frame expectations.
fn assert_close(actual: Vec3, expected: Vec3, label: &str) {
    let drift = (actual - expected).abs();
    assert!(
        drift.x < POSITION_EPSILON && drift.y < POSITION_EPSILON && drift.z < POSITION_EPSILON,
        "{label}: expected {expected:?}, got {actual:?}"
    );
}

/// A pod placement at `yaw` with floor-plan center `center`.
fn placement(yaw: f32, center: (f32, f32)) -> PodPlacement {
    PodPlacement {
        center,
        yaw_radians: yaw,
    }
}

/// The frozen player pod's registry placement: yaw pi, opening toward
/// the aisle.
fn frozen_player_placement() -> PodPlacement {
    PodRegistry::frozen().player_pod().placement()
}

/// Rotates a pod-local point into the room frame, independently of the
/// production transform, for waypoint expectations.
fn local_to_world(placement: PodPlacement, x: f32, y: f32, z: f32) -> Vec3 {
    let (sin, cos) = placement.yaw_radians.sin_cos();
    Vec3::new(
        placement.center.0 + x * cos + z * sin,
        y,
        placement.center.1 - x * sin + z * cos,
    )
}

/// The pod-local floor-plan coordinates of a room-frame point (the
/// inverse rotation; exact for the axis-aligned test yaws 0 and pi).
fn world_planar_local(placement: PodPlacement, world: Vec3) -> (f32, f32) {
    let (sin, cos) = placement.yaw_radians.sin_cos();
    let dx = world.x - placement.center.0;
    let dz = world.z - placement.center.1;
    (dx * cos - dz * sin, dx * sin + dz * cos)
}

/// One axis-aligned test box, pod-local center and size lifted into
/// the room frame. The size is a full extent, matching the app-side
/// pod builder's solid sizes; [`Aabb::try_new`] takes half extents,
/// so the builder halves it here. Valid only for yaws that keep boxes
/// axis-aligned (the tests use 0 and pi).
fn local_box(placement: PodPlacement, center: (f32, f32, f32), size: (f32, f32, f32)) -> Aabb {
    Aabb::try_new(
        local_to_world(placement, center.0, center.1, center.2),
        Vec3::from(size) * 0.5,
    )
    .expect("test box is valid")
}

/// The test scene: a room floor slab plus the player pod's cavity
/// solids (base, plate, two side walls, head wall, canopy), then any
/// extra boxes. Insertion order matters to the resolver's index
/// reports: floor 0, base 1, plate 2, side walls 3 and 4, head wall 5,
/// canopy 6, then the extras.
/// The player pod's cavity solids in insertion order: base, plate,
/// side walls, head wall, canopy. The floor slab and any extra boxes
/// are added by `pod_scene`.
fn pod_solids(placement: PodPlacement) -> [Aabb; 6] {
    [
        local_box(
            placement,
            (0.0, CAVITY_BASE / 2.0, 0.0),
            (POD_WIDTH, CAVITY_BASE, POD_LENGTH),
        ),
        local_box(
            placement,
            (0.0, TRAY_FLOOR - CAVITY_PLATE / 2.0, 0.0),
            (
                POD_WIDTH - 2.0 * CAVITY_WALL,
                CAVITY_PLATE,
                POD_LENGTH - 2.0 * CAVITY_WALL,
            ),
        ),
        local_box(
            placement,
            (
                -(POD_WIDTH / 2.0 - CAVITY_WALL / 2.0),
                f32::midpoint(CAVITY_BASE, POD_HEIGHT),
                -CAVITY_WALL / 2.0,
            ),
            (
                CAVITY_WALL,
                POD_HEIGHT - CAVITY_BASE,
                POD_LENGTH - CAVITY_WALL,
            ),
        ),
        local_box(
            placement,
            (
                POD_WIDTH / 2.0 - CAVITY_WALL / 2.0,
                f32::midpoint(CAVITY_BASE, POD_HEIGHT),
                -CAVITY_WALL / 2.0,
            ),
            (
                CAVITY_WALL,
                POD_HEIGHT - CAVITY_BASE,
                POD_LENGTH - CAVITY_WALL,
            ),
        ),
        local_box(
            placement,
            (
                0.0,
                f32::midpoint(CAVITY_BASE, POD_HEIGHT),
                -(POD_LENGTH - CAVITY_WALL / 2.0),
            ),
            (
                POD_WIDTH - 2.0 * CAVITY_WALL,
                POD_HEIGHT - CAVITY_BASE,
                CAVITY_WALL,
            ),
        ),
        // The player pod's raised canopy over the head end.
        local_box(
            placement,
            (0.0, POD_HEIGHT + 0.65, -(POD_LENGTH - CAVITY_WALL / 2.0)),
            (POD_WIDTH, 1.3, CAVITY_WALL),
        ),
    ]
}

/// The test scene: a room floor slab plus the player pod's cavity
/// solids, then any extra boxes. Insertion order matters to the
/// resolver's index reports: floor 0, base 1, plate 2, side walls 3
/// and 4, head wall 5, canopy 6, then the extras.
fn pod_scene(placement: PodPlacement, extra: &[Aabb]) -> ColliderSet {
    let mut set = ColliderSet::new();
    set.insert(
        Aabb::from_min_max(
            Vec3::new(-FLOOR_SPAN, -1.0, -FLOOR_SPAN),
            Vec3::new(FLOOR_SPAN, 0.0, FLOOR_SPAN),
        )
        .expect("floor slab is valid"),
    );
    for solid in pod_solids(placement) {
        set.insert(solid);
    }
    for aabb in extra {
        set.insert(*aabb);
    }
    set
}

/// Drives the full get-up from `AwakeInPod` to `Standing` and returns
/// the finished controller.
fn drive_to_standing(
    path: ExitPath,
    scene: &ColliderSet,
) -> (GetUpController, WakePhase, Vec<bool>) {
    let mut phase = WakePhase::AwakeInPod;
    let mut controller =
        GetUpController::start(&mut phase, path).expect("the get-up starts from AwakeInPod");
    assert!(phase.in_phase(WakePhase::ExitingPod));
    let mut waypoints = Vec::new();
    for expected_index in 1..EXIT_POSE_COUNT {
        let progress = controller.tick(&mut phase, scene).expect("unblocked tick");
        assert_eq!(progress.pose_index, expected_index);
        waypoints.push(progress.at_waypoint);
        let pose = path.poses()[expected_index];
        assert_close(controller.capsule().foot, pose.foot(), "pose foot");
        assert_close(controller.capsule().head, pose.head(), "pose head");
    }
    (controller, phase, waypoints)
}

/// The happy path: every intermediate pose is visited in order within
/// its tolerance, only the last tick completes the waypoint, and the
/// machine lands in Standing with the capsule at the authored
/// waypoint pose.
#[test]
fn happy_path_visits_every_pose_and_completes_standing_at_the_waypoint() {
    let placement = frozen_player_placement();
    let path = ExitPath::try_new(placement, TRAY_FLOOR).expect("authored floor is valid");
    let scene = pod_scene(placement, &[]);
    let (controller, phase, waypoints) = drive_to_standing(path, &scene);
    assert_eq!(waypoints, vec![false, false, false, true]);
    assert!(phase.in_phase(WakePhase::Standing));
    assert!(phase.locomotion_allowed(), "Standing unlocks locomotion");
    let waypoint = path.waypoint();
    let capsule = controller.capsule();
    assert_close(capsule.foot, waypoint.foot(), "waypoint foot");
    assert_close(capsule.head, waypoint.head(), "waypoint head");
    // The waypoint stands on the room floor in front of the pod's
    // opening: foot sphere one tolerance above the deck, past the pod
    // face by the capsule radius.
    let (foot_x, foot_z) = world_planar_local(placement, capsule.foot);
    assert!(foot_x.abs() < POSITION_EPSILON, "centered on the pod");
    let expected_standoff = POD_LENGTH / 2.0 + CAPSULE_RADIUS + 2.0 * PENETRATION_TOLERANCE;
    assert!((foot_z - expected_standoff).abs() < POSITION_EPSILON);
    assert!((capsule.foot.y - (CAPSULE_RADIUS + PENETRATION_TOLERANCE)).abs() < 1e-6);
}

/// The waypoint's room-frame position is the placement transform of
/// the authored local waypoint, never a hard-coded room coordinate: an
/// identity-yaw placement transforms exactly, the frozen player pod's
/// yaw-pi placement transforms within float tolerance, and two
/// placements produce different waypoints.
#[test]
fn waypoint_room_position_is_the_placement_transform_not_a_hard_code() {
    let standing_y = CAPSULE_RADIUS + PENETRATION_TOLERANCE;
    let waypoint_z = POD_LENGTH / 2.0 + CAPSULE_RADIUS + 2.0 * PENETRATION_TOLERANCE;
    let row_a = placement(0.0, (-3.0, -2.9));
    let path_a = ExitPath::try_new(row_a, TRAY_FLOOR).expect("authored floor is valid");
    // Identity yaw: the transform is exact float arithmetic.
    assert_eq!(
        path_a.waypoint().foot(),
        Vec3::new(-3.0, standing_y, -2.9 + waypoint_z)
    );
    let player = frozen_player_placement();
    let path_b = ExitPath::try_new(player, TRAY_FLOOR).expect("authored floor is valid");
    assert_close(
        path_b.waypoint().foot(),
        local_to_world(player, 0.0, standing_y, waypoint_z),
        "yaw-pi waypoint",
    );
    let separation = (path_a.waypoint().foot() - path_b.waypoint().foot()).length();
    assert!(separation > 1.0, "the waypoint follows the placement");
}

/// `start` is the explicit exit command and only consumes in
/// `AwakeInPod`: every other phase rejects with `WrongPhase` naming
/// both phases, and the machine is left unchanged.
#[test]
fn start_rejects_every_phase_except_awake_in_pod() {
    let path =
        ExitPath::try_new(frozen_player_placement(), TRAY_FLOOR).expect("authored floor is valid");
    for current in [
        WakePhase::Waking,
        WakePhase::ExitingPod,
        WakePhase::Standing,
    ] {
        let mut phase = current;
        let error = GetUpController::start(&mut phase, path)
            .expect_err("only AwakeInPod starts the get-up");
        assert_eq!(
            error,
            ExitError::WrongPhase {
                expected: WakePhase::AwakeInPod,
                current,
            }
        );
        assert!(phase.in_phase(current), "the phase is unchanged");
        let text = error.to_string();
        assert!(text.contains("phase"), "display: {text}");
        assert!(text.contains(&format!("{current:?}")), "display: {text}");
    }
}

/// A spent controller refuses every further tick — even when a caller
/// resets the machine back to `ExitingPod`, the path cannot be
/// re-walked.
#[test]
fn ticking_a_spent_controller_is_rejected_even_after_a_machine_reset() {
    let placement = frozen_player_placement();
    let path = ExitPath::try_new(placement, TRAY_FLOOR).expect("authored floor is valid");
    let scene = pod_scene(placement, &[]);
    let (mut controller, _, _) = drive_to_standing(path, &scene);
    let mut reset = WakePhase::ExitingPod;
    assert_eq!(
        controller.tick(&mut reset, &scene),
        Err(ExitError::GetUpAlreadyComplete)
    );
    assert_eq!(
        controller.tick(&mut reset, &scene).unwrap_err().to_string(),
        "the get-up already reached the waypoint"
    );
}

/// Shrinking the aperture with a jamb slab stops the get-up with a
/// typed `PathBlocked` error: the sweep stops the capsule short of the
/// mouth (rigid partial motion applied, nothing clipped), the machine
/// stays in `ExitingPod`, and a retry fails the same way.
#[test]
fn a_blocked_aperture_stops_the_get_up_with_a_typed_error() {
    let placement = frozen_player_placement();
    let path = ExitPath::try_new(placement, TRAY_FLOOR).expect("authored floor is valid");
    // A jamb filling the +x half of the exit mouth strip: the clear
    // passage drops to 0.45 m, under the 0.60 m capsule diameter.
    let jamb = local_box(
        placement,
        (
            0.25,
            f32::midpoint(CAVITY_BASE, POD_HEIGHT),
            POD_LENGTH / 2.0 - CAVITY_WALL / 2.0,
        ),
        (0.5, POD_HEIGHT - CAVITY_BASE, CAVITY_WALL),
    );
    let scene = pod_scene(placement, &[jamb]);
    let mut phase = WakePhase::AwakeInPod;
    let mut controller = GetUpController::start(&mut phase, path).expect("starts from AwakeInPod");
    controller
        .tick(&mut phase, &scene)
        .expect("the sit-up pivot clears the tray");
    let error = controller
        .tick(&mut phase, &scene)
        .expect_err("the shrunk aperture blocks the walk to the mouth");
    let ExitError::PathBlocked {
        pose_index,
        shortfall,
    } = error
    else {
        panic!("expected a blocked path, got {error:?}");
    };
    assert_eq!(pose_index, 2, "the walk to the aperture line is blocked");
    assert!(shortfall > POSE_TOLERANCE, "a real block, {shortfall} m");
    assert!(shortfall > 0.05, "stopped before the mouth: {shortfall} m");
    // The capsule kept the resolver's partial motion and never entered
    // the mouth strip: its foot sphere stayed short of the aperture
    // line, and the machine never advanced.
    let (foot_x, foot_z) = world_planar_local(placement, controller.capsule().foot);
    assert!(foot_x.abs() < POSITION_EPSILON, "still centered");
    assert!(
        foot_z + CAPSULE_RADIUS < POD_LENGTH / 2.0 - CAVITY_WALL,
        "foot sphere short of the mouth line, local z {foot_z}"
    );
    assert!(phase.in_phase(WakePhase::ExitingPod));
    let retry = controller.tick(&mut phase, &scene).unwrap_err();
    assert!(matches!(retry, ExitError::PathBlocked { .. }), "{retry:?}");
}

/// A collider swallowing the capsule at the first pose surfaces the
/// resolver's own rejection, wrapped in the typed resolver error,
/// naming the offending collider index.
#[test]
fn resolver_rejections_surface_as_the_typed_resolver_error() {
    let placement = frozen_player_placement();
    let path = ExitPath::try_new(placement, TRAY_FLOOR).expect("authored floor is valid");
    // A slab around the lying capsule's middle, embedding it far past
    // the penetration tolerance on every axis.
    let block = local_box(
        placement,
        (0.0, TRAY_FLOOR + CAPSULE_RADIUS, 0.0),
        (0.2, 0.2, 0.4),
    );
    let scene = pod_scene(placement, &[block]);
    let mut phase = WakePhase::AwakeInPod;
    let mut controller = GetUpController::start(&mut phase, path).expect("starts from AwakeInPod");
    let error = controller
        .tick(&mut phase, &scene)
        .expect_err("an embedded capsule cannot sweep");
    assert_eq!(
        error,
        ExitError::Resolver(ResolveError::StartPenetration { index: 7 })
    );
    let text = error.to_string();
    assert!(text.contains("resolver"), "display: {text}");
    assert!(text.contains("embedded"), "display: {text}");
    assert!(phase.in_phase(WakePhase::ExitingPod));
}

/// The authored movement table matches the pose table segment for
/// segment (rigid moves and one pivot), the mouth poses stay centered
/// on the pod's lateral axis, and the frozen mouth width covers the
/// capsule with the frozen clearance per side.
#[test]
fn authored_moves_match_the_pose_table_and_mouth_poses_stay_centered() {
    let placement = frozen_player_placement();
    let path = ExitPath::try_new(placement, TRAY_FLOOR).expect("authored floor is valid");
    for index in 0..EXIT_POSE_COUNT - 1 {
        let expected = segment_move(&path.poses()[index], &path.poses()[index + 1]);
        assert_eq!(Some(path.moves[index]), expected, "segment {index}");
    }
    // The sit-up is the authored pivot; everything else is rigid.
    assert!(matches!(path.moves[0], SegmentMove::PivotAboutFoot(_)));
    for movement in &path.moves[1..] {
        assert!(matches!(movement, SegmentMove::Rigid(_)));
    }
    // Every pose from the aperture line on is centered: the mouth is
    // always crossed on the pod's lateral axis.
    for pose in &path.poses()[2..] {
        assert!(
            (pose.foot().x - placement.center.0).abs() < POSITION_EPSILON,
            "centered foot at the mouth"
        );
        assert!(
            (pose.head().x - placement.center.0).abs() < POSITION_EPSILON,
            "centered head at the mouth"
        );
    }
    const {
        assert!(EXIT_MOUTH_WIDTH >= 2.0 * CAPSULE_RADIUS + 2.0 * 0.149);
    }
}

/// Path construction validates its inputs: non-finite placements and
/// floors, floors below the room floor, and floors too high for the
/// lying capsule to fit under the tray walls are all rejected with
/// typed errors.
#[test]
fn path_construction_validates_its_inputs() {
    let player = frozen_player_placement();
    let nan = f32::NAN;
    assert_eq!(
        ExitPath::try_new(
            PodPlacement {
                center: (nan, 0.0),
                yaw_radians: 0.0,
            },
            TRAY_FLOOR,
        ),
        Err(ExitPathError::NonFinitePlacement)
    );
    assert_eq!(
        ExitPath::try_new(player, nan),
        Err(ExitPathError::NonFiniteTrayFloor)
    );
    assert_eq!(
        ExitPath::try_new(player, -0.5),
        Err(ExitPathError::TrayFloorBelowRoom { got: -0.5 })
    );
    let max = POD_HEIGHT - 2.0 * CAPSULE_RADIUS;
    assert_eq!(
        ExitPath::try_new(player, max + 0.01),
        Err(ExitPathError::TrayFloorTooHigh {
            max,
            got: max + 0.01
        })
    );
    // The authored tray floor is inside both bounds, and the boundary
    // values are accepted.
    assert!(ExitPath::try_new(player, TRAY_FLOOR).is_ok());
    assert!(ExitPath::try_new(player, 0.0).is_ok());
    assert!(ExitPath::try_new(player, max).is_ok());
}
