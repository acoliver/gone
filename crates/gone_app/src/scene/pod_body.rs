//! Pure stasis pod construction (issue #7 stage A cavity rebuild).
//!
//! Every pod is an open-topped tray instead of a solid block: a base slab,
//! four walls with a real cavity between them, and a dark floor plate
//! inside. The state's top finishes the silhouette: sealed pods close with
//! a flat lid over the whole footprint, empty-open pods keep the angled
//! open lid and the hanging blanket, and the player pod stands its lid up
//! as a canopy over the head end so the lying view of the ceiling stays
//! clear.
//!
//! [`pod_solids`] is the one construction path: the scene spawns its boxes
//! verbatim (`geometry::fill_pod`), and the pure tests in this module
//! assert the cavity, eye, ray, and aperture guarantees against the same
//! data, so the rendered geometry and the guarantees cannot drift apart.
//! The module is renderer-free apart from `bevy_math` vectors: no ECS, no
//! meshes, no materials.
//!
//! All numbers are pod-local, in meters: local +Z is the pod's opening
//! (its foot), local -Z the head, up is +Y. The pod group's transform (the
//! registry placement) carries this frame into the world.

use bevy::math::Vec3;
use gone_sim::PodState;
use gone_sim::controller::POD_EXIT_CLEARANCE;
use gone_sim::pods::{POD_HEIGHT, POD_LENGTH, POD_WIDTH};

/// Cavity wall thickness, in meters. Thin shell walls leave a 0.78 m
/// interior between them: the 0.60 m lying capsule with 0.09 m of side
/// margin on each side.
const CAVITY_WALL: f32 = 0.06;

/// Base slab thickness, in meters: the cavity floor the lying capsule
/// rests on, under the dark floor plate. `exit_path` reads it to place the
/// lying capsule on the plate top.
pub(crate) const CAVITY_BASE: f32 = 0.1;

/// Dark cavity floor plate thickness, in meters: a thin dark floor inside
/// the tray so the open interior reads as a cavity from across the aisle.
/// `exit_path` reads it for the plate top the lying capsule rests on.
pub(crate) const CAVITY_PLATE_THICKNESS: f32 = 0.012;

/// Pod lid slab thickness, in meters (closed lid, open lid, and canopy
/// alike).
const LID_THICKNESS: f32 = 0.06;

/// How much shorter than the body the open lid slab is.
const LID_SETBACK: f32 = 0.1;

/// The empty-open lid's tilt from horizontal, in radians: propped up over
/// the head end so the opening reads as open from across the aisle.
const LID_OPEN_TILT: f32 = 60.0_f32.to_radians();

/// The player pod's canopy length along the pod, in meters. It stands
/// vertical over the head wall, inside the footprint: the pod backs flush
/// against its wall, so a lid leaning past vertical would clip the wall,
/// and anything short of vertical crosses the straight-up ray from the
/// lying eye. At this length the canopy top (`POD_HEIGHT +
/// CANOPY_LENGTH` = 2.1 m) stays under the roughly 2.45 m height where
/// the worst 15 degree cone ray crosses the canopy's inner face; the ray
/// tests below pin that clearance with margin.
const CANOPY_LENGTH: f32 = 1.3;

/// The occupancy blanket's silhouette, in meters: a thin slab draped over
/// one rim of an empty-open pod.
const BLANKET_THICKNESS: f32 = 0.05;
const BLANKET_DROP: f32 = 0.56;
const BLANKET_WIDTH: f32 = 0.7;

/// How far above the pod top the blanket's upper edge sits (it drapes over
/// the rim).
const BLANKET_OVERHANG: f32 = 0.02;

/// Distance from the pod's foot end to the hanging blanket, in meters.
const BLANKET_FROM_FOOT: f32 = 0.15;

/// Which greybox material one solid renders with.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum SolidKind {
    /// Structural pod mass: base slab and walls.
    Body,
    /// The dark cavity floor plate inside the tray.
    Cavity,
    /// Lid slabs: closed, angled open, and the player canopy.
    Lid,
    /// The empty-open pod's occupancy blanket.
    Blanket,
}

/// One solid cuboid of a pod's greybox, in the pod's local frame. `center`
/// is the box center (mesh primitives are centered on their entity) and
/// `roll_radians` is a rotation about local +X applied when the box
/// spawns. Only the angled open lid rolls; every other solid is
/// axis-aligned.
#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) struct PodSolid {
    /// Box center in the pod's local frame.
    pub(crate) center: Vec3,
    /// Full box size along the local axes.
    pub(crate) size: Vec3,
    /// Rotation about local +X, in radians (0 for axis-aligned solids).
    pub(crate) roll_radians: f32,
    /// Which greybox material the box renders with.
    pub(crate) kind: SolidKind,
}

/// Build one pod's full solid set for `state`: the shared cavity tray plus
/// the state's top (and the blanket for empty-open pods). The scene spawns
/// these verbatim and the tests assert the geometric guarantees against
/// the same boxes.
#[must_use]
pub(crate) fn pod_solids(state: PodState) -> Vec<PodSolid> {
    let mut solids = cavity_solids();
    match state {
        PodState::Sealed => solids.push(sealed_lid()),
        PodState::EmptyOpen => {
            solids.push(open_lid());
            solids.push(hanging_blanket());
        }
        PodState::Player => solids.push(player_canopy()),
    }
    solids
}

/// The open cavity's interior clear box: between the four walls' inner
/// faces and above the base slab, returned as `(min, max)` corners. The
/// builder places the walls from these bounds and the tests assert the
/// cavity guarantees against them, so one function shapes the interior.
#[must_use]
pub(crate) fn cavity_interior() -> (Vec3, Vec3) {
    let half_width = POD_WIDTH / 2.0 - CAVITY_WALL;
    let half_length = POD_LENGTH / 2.0 - CAVITY_WALL;
    (
        Vec3::new(-half_width, CAVITY_BASE, -half_length),
        Vec3::new(half_width, POD_HEIGHT, half_length),
    )
}

/// Half the exit aperture's clear width: the frozen [`POD_EXIT_CLEARANCE`]
/// taken from each side of the pod's 0.9 m width, exactly as the
/// controller spec freezes it (the 0.60 m capsule plus this margin on
/// each jamb fills the opening exactly).
#[must_use]
pub(crate) fn exit_aperture_half_width() -> f32 {
    POD_WIDTH / 2.0 - POD_EXIT_CLEARANCE
}

/// An axis-aligned solid at `center` (meshes are centered on their
/// entity).
fn solid(center: Vec3, size: Vec3, kind: SolidKind) -> PodSolid {
    PodSolid {
        center,
        size,
        roll_radians: 0.0,
        kind,
    }
}

/// The cavity tray every pod is built from: base slab, dark floor plate,
/// two full-length side walls, the head wall between them, and the two
/// foot jamb pieces that leave the exit aperture open between them.
fn cavity_solids() -> Vec<PodSolid> {
    let (interior_min, interior_max) = cavity_interior();
    let aperture = exit_aperture_half_width();
    let wall_height = POD_HEIGHT - CAVITY_BASE;
    let wall_mid = CAVITY_BASE + wall_height / 2.0;
    let foot_z = (POD_LENGTH - CAVITY_WALL) / 2.0;
    let jamb_width = interior_max.x - aperture;
    let jamb_x = aperture + jamb_width / 2.0;

    let mut solids = vec![
        // Base slab, full footprint.
        solid(
            Vec3::new(0.0, CAVITY_BASE / 2.0, 0.0),
            Vec3::new(POD_WIDTH, CAVITY_BASE, POD_LENGTH),
            SolidKind::Body,
        ),
        // Dark floor plate on the base, spanning the interior.
        solid(
            Vec3::new(0.0, CAVITY_BASE + CAVITY_PLATE_THICKNESS / 2.0, 0.0),
            Vec3::new(
                interior_max.x - interior_min.x,
                CAVITY_PLATE_THICKNESS,
                interior_max.z - interior_min.z,
            ),
            SolidKind::Cavity,
        ),
        // Head wall between the side walls.
        solid(
            Vec3::new(0.0, wall_mid, -foot_z),
            Vec3::new(interior_max.x - interior_min.x, wall_height, CAVITY_WALL),
            SolidKind::Body,
        ),
    ];
    for sign in [-1.0, 1.0] {
        solids.push(solid(
            Vec3::new(sign * (interior_max.x + CAVITY_WALL / 2.0), wall_mid, 0.0),
            Vec3::new(CAVITY_WALL, wall_height, POD_LENGTH),
            SolidKind::Body,
        ));
        solids.push(solid(
            Vec3::new(sign * jamb_x, wall_mid, foot_z),
            Vec3::new(jamb_width, wall_height, CAVITY_WALL),
            SolidKind::Body,
        ));
    }
    solids
}

/// The sealed pod's closed lid: one flat slab lying over the whole
/// footprint, so the closed silhouette matches the tray's outer shell.
fn sealed_lid() -> PodSolid {
    solid(
        Vec3::new(0.0, POD_HEIGHT + LID_THICKNESS / 2.0, 0.0),
        Vec3::new(POD_WIDTH, LID_THICKNESS, POD_LENGTH),
        SolidKind::Lid,
    )
}

/// The empty-open pod's lid: hinged at the head end top edge and swung up
/// [`LID_OPEN_TILT`], propped over the head so the opening reads as open
/// from across the aisle. The slab mesh is centered on its entity, hence
/// the midpoint offset along the swung direction.
fn open_lid() -> PodSolid {
    let length = POD_LENGTH - LID_SETBACK;
    let hinge = Vec3::new(0.0, POD_HEIGHT, -POD_LENGTH / 2.0);
    let center = hinge
        + Vec3::new(
            0.0,
            f32::sin(LID_OPEN_TILT) * length / 2.0,
            f32::cos(LID_OPEN_TILT) * length / 2.0,
        );
    PodSolid {
        center,
        size: Vec3::new(POD_WIDTH, LID_THICKNESS, length),
        roll_radians: -LID_OPEN_TILT,
        kind: SolidKind::Lid,
    }
}

/// The player pod's raised canopy: the lid stood fully upright over the
/// head wall, inside the footprint (see [`CANOPY_LENGTH`]).
fn player_canopy() -> PodSolid {
    solid(
        Vec3::new(
            0.0,
            POD_HEIGHT + CANOPY_LENGTH / 2.0,
            -(POD_LENGTH - LID_THICKNESS) / 2.0,
        ),
        Vec3::new(POD_WIDTH, CANOPY_LENGTH, LID_THICKNESS),
        SolidKind::Lid,
    )
}

/// The empty-open pod's occupancy blanket: a thin slab draped over one
/// rim, hanging down the outside wall. Reads as "recently used, empty".
fn hanging_blanket() -> PodSolid {
    let over_rim = POD_WIDTH / 2.0 + BLANKET_THICKNESS / 2.0;
    let top = POD_HEIGHT - BLANKET_DROP / 2.0 + BLANKET_OVERHANG;
    let along = -POD_LENGTH / 2.0 + BLANKET_FROM_FOOT + BLANKET_WIDTH / 2.0;
    solid(
        Vec3::new(over_rim, top, along),
        Vec3::new(BLANKET_THICKNESS, BLANKET_DROP, BLANKET_WIDTH),
        SolidKind::Blanket,
    )
}

/// Pure coverage of the pod construction: the cavity, the lying eye, the
/// look cone, the exit aperture, and the per-state lids, all asserted
/// against the exact data the scene spawns.
#[cfg(test)]
mod tests {
    use super::{
        CANOPY_LENGTH, CAVITY_BASE, CAVITY_WALL, LID_OPEN_TILT, LID_THICKNESS, PodSolid, SolidKind,
        cavity_interior, exit_aperture_half_width, pod_solids,
    };
    use crate::scene::{EYE_FROM_CENTER_TO_HEAD, LYING_EYE_HEIGHT};
    use bevy::math::Vec3;
    use gone_sim::controller::{CAPSULE_RADIUS, CAPSULE_STANDING_HEIGHT, POD_EXIT_CLEARANCE};
    use gone_sim::pods::{POD_HEIGHT, POD_LENGTH, POD_WIDTH, ROOM_CEILING_HEIGHT};
    use gone_sim::{PodRegistry, PodState};

    /// Eye-to-solid clearance the cavity must hold at the lying eye point.
    const EYE_MARGIN: f32 = 0.05;

    /// Ray-blocking guard: every solid is grown by this before the cone
    /// test, so a pass proves at least this much true clearance along
    /// every ray.
    const RAY_GUARD: f32 = 0.05;

    /// Positive fit margin required around the lying capsule on every
    /// axis.
    const CAPSULE_FIT_MARGIN: f32 = 0.03;

    /// The look cone's half angle off vertical, in degrees: the brief's
    /// straight-up ray plus its plus and minus 15 degree boundary.
    const CONE_TILT_DEG: f32 = 15.0;

    /// The authored lying eye in pod-local space: the same point
    /// `player_spawn_pose` places in the world, expressed in the player
    /// pod's frame.
    fn lying_eye() -> Vec3 {
        Vec3::new(0.0, LYING_EYE_HEIGHT, -EYE_FROM_CENTER_TO_HEAD)
    }

    /// Axis-aligned bounds of one solid. The player pod's construction is
    /// fully axis-aligned; a rolled solid fails loudly here instead of
    /// yielding silently wrong bounds.
    fn bounds(solid: &PodSolid) -> (Vec3, Vec3) {
        assert!(
            solid.roll_radians.abs() < f32::EPSILON,
            "bounds are only asked for axis-aligned solids"
        );
        let half = solid.size / 2.0;
        (solid.center - half, solid.center + half)
    }

    /// Distance from a point to an axis-aligned box (zero inside).
    fn point_box_distance(point: Vec3, min: Vec3, max: Vec3) -> f32 {
        let dx = (min.x - point.x).max(point.x - max.x).max(0.0);
        let dy = (min.y - point.y).max(point.y - max.y).max(0.0);
        let dz = (min.z - point.z).max(point.z - max.z).max(0.0);
        f32::sqrt(dx * dx + dy * dy + dz * dz)
    }

    /// One axis's slab overlap for the ray-box test: narrows the
    /// entry/exit interval in place, returning false when the ray misses
    /// this axis's slab entirely.
    fn narrow_slab(
        origin: f32,
        dir: f32,
        lo: f32,
        hi: f32,
        entry: &mut f32,
        exit: &mut f32,
    ) -> bool {
        if dir.abs() < 1e-9 {
            origin >= lo && origin <= hi
        } else {
            let mut near = (lo - origin) / dir;
            let mut far = (hi - origin) / dir;
            if near > far {
                core::mem::swap(&mut near, &mut far);
            }
            *entry = (*entry).max(near);
            *exit = (*exit).min(far);
            true
        }
    }

    /// Nearest positive distance along the ray where it enters the box,
    /// or `None` when the ray never reaches it (slab method).
    fn ray_box_entry(origin: Vec3, dir: Vec3, min: Vec3, max: Vec3) -> Option<f32> {
        let mut entry = 0.0_f32;
        let mut exit = f32::INFINITY;
        let hit = narrow_slab(origin.x, dir.x, min.x, max.x, &mut entry, &mut exit)
            && narrow_slab(origin.y, dir.y, min.y, max.y, &mut entry, &mut exit)
            && narrow_slab(origin.z, dir.z, min.z, max.z, &mut entry, &mut exit);
        (hit && entry <= exit && exit > 0.0).then_some(entry.max(0.0))
    }

    /// The test cone: straight up plus a full ring of rays at
    /// [`CONE_TILT_DEG`] from vertical, in pod-local space.
    fn cone_rays() -> Vec<Vec3> {
        let tilt = CONE_TILT_DEG.to_radians();
        let step = core::f32::consts::TAU / 24.0;
        let mut rays = vec![Vec3::Y];
        let mut azimuth = 0.0;
        for _ in 0..24 {
            rays.push(Vec3::new(
                f32::sin(tilt) * f32::cos(azimuth),
                f32::cos(tilt),
                f32::sin(tilt) * f32::sin(azimuth),
            ));
            azimuth += step;
        }
        rays
    }

    /// The lying eye sits inside the open cavity with margin to every
    /// interior face, and no solid part of the player pod comes within
    /// [`EYE_MARGIN`] of it. Regression: pods used to be solid blocks, so
    /// the eye was buried inside the body box.
    #[test]
    fn player_pod_eye_lies_in_the_open_cavity_clear_of_every_solid() {
        let eye = lying_eye();
        let (interior_min, interior_max) = cavity_interior();
        let in_interior = eye.x >= interior_min.x + EYE_MARGIN
            && eye.x <= interior_max.x - EYE_MARGIN
            && eye.y >= interior_min.y + EYE_MARGIN
            && eye.y <= interior_max.y - EYE_MARGIN
            && eye.z >= interior_min.z + EYE_MARGIN
            && eye.z <= interior_max.z - EYE_MARGIN;
        assert!(in_interior, "eye inside the open cavity with margin");
        for solid in pod_solids(PodState::Player) {
            let (min, max) = bounds(&solid);
            let distance = point_box_distance(eye, min, max);
            assert!(
                distance >= EYE_MARGIN,
                "solid {:?} within margin of the eye: {distance}",
                solid.kind
            );
        }
    }

    /// Every ray of the straight-up-plus-15-degree look cone from the
    /// authored eye clears every player pod solid grown by [`RAY_GUARD`]
    /// and reaches the ceiling plane, so nothing of the pod blocks the
    /// lying view of the ceiling. Regression: the 60 degree propped lid
    /// crossed the vertical ray about 1.1 m from the eye.
    #[test]
    fn vertical_and_cone_rays_from_the_eye_miss_the_player_pod_and_reach_the_ceiling() {
        let eye = lying_eye();
        let solids = pod_solids(PodState::Player);
        for dir in cone_rays() {
            let t_ceiling = (ROOM_CEILING_HEIGHT - eye.y) / dir.y;
            assert!(t_ceiling > 0.0, "the ray climbs to the ceiling");
            for solid in &solids {
                let (min, max) = bounds(solid);
                let entry = ray_box_entry(
                    eye,
                    dir,
                    min - Vec3::splat(RAY_GUARD),
                    max + Vec3::splat(RAY_GUARD),
                );
                assert!(
                    entry.is_none_or(|t| t >= t_ceiling),
                    "ray {dir:?} blocked by {:?} before the ceiling (entry {entry:?})",
                    solid.kind
                );
            }
        }
    }

    /// The cavity interior fits the lying capsule (0.30 m radius, 1.75 m
    /// standing height lying along the pod) with margin on every axis.
    #[test]
    fn cavity_fits_the_lying_capsule_with_margin() {
        let (min, max) = cavity_interior();
        let diameter = 2.0 * CAPSULE_RADIUS;
        let fit = diameter + 2.0 * CAPSULE_FIT_MARGIN;
        assert!(
            max.x - min.x >= fit,
            "interior width {} fits the capsule with margin",
            max.x - min.x
        );
        assert!(
            max.z - min.z >= CAPSULE_STANDING_HEIGHT + 2.0 * CAPSULE_FIT_MARGIN,
            "interior length fits the lying capsule with margin"
        );
        assert!(
            max.y - min.y >= fit,
            "interior height fits the capsule diameter with margin"
        );
    }

    /// The exit aperture between the foot jambs takes the frozen
    /// [`POD_EXIT_CLEARANCE`] from each side of the 0.9 m width and admits
    /// the capsule. The two widths round to different ulps in f32, so both
    /// comparisons carry an ulp-scale tolerance instead of exact
    /// equality.
    #[test]
    fn exit_aperture_honors_the_frozen_clearance_against_the_pod_width() {
        let aperture_half = exit_aperture_half_width();
        let expected = POD_WIDTH / 2.0 - POD_EXIT_CLEARANCE;
        assert!(
            (aperture_half - expected).abs() < f32::EPSILON,
            "the aperture is the frozen clearance per jamb"
        );
        assert!(
            aperture_half + 1e-5 >= CAPSULE_RADIUS,
            "the capsule fits the aperture"
        );
        let foot_z = (POD_LENGTH - CAVITY_WALL) / 2.0;
        let jambs: Vec<PodSolid> = pod_solids(PodState::Player)
            .into_iter()
            .filter(|solid| solid.kind == SolidKind::Body && (solid.center.z - foot_z).abs() < 1e-6)
            .collect();
        assert_eq!(jambs.len(), 2, "two foot jamb pieces");
        for jamb in &jambs {
            let (min, max) = bounds(jamb);
            let inner = if jamb.center.x > 0.0 { min.x } else { max.x };
            assert!(
                (inner.abs() - aperture_half).abs() < 1e-5,
                "jamb inner face sits at the aperture edge"
            );
        }
    }

    /// Every frozen pod keeps the cavity tray base, and the six
    /// non-player pods still carry their states (see
    /// [`assert_state_top`]).
    #[test]
    fn every_pod_keeps_the_tray_and_non_player_pods_carry_their_states() {
        let registry = PodRegistry::frozen();
        assert_eq!(
            registry
                .pods()
                .iter()
                .filter(|p| !p.state().is_player())
                .count(),
            6,
            "six non-player pods"
        );
        for pod in registry.pods() {
            let solids = pod_solids(pod.state());
            assert!(
                solids.iter().any(|solid| {
                    solid.kind == SolidKind::Body
                        && solid.size == Vec3::new(POD_WIDTH, CAVITY_BASE, POD_LENGTH)
                }),
                "pod {} keeps the full-footprint tray base",
                pod.id().index()
            );
            assert_state_top(pod.state(), &solids);
        }
    }

    /// One pod's lid set matches its state: sealed pods close with a full
    /// flat lid over the footprint, empty-open pods keep the angled open
    /// lid and the hanging blanket, and the player pod alone stands its
    /// lid up as a canopy over the head end.
    fn assert_state_top(state: PodState, solids: &[PodSolid]) {
        let lids: Vec<&PodSolid> = solids
            .iter()
            .filter(|solid| solid.kind == SolidKind::Lid)
            .collect();
        let blankets = solids
            .iter()
            .filter(|solid| solid.kind == SolidKind::Blanket)
            .count();
        match state {
            PodState::Sealed => {
                assert_eq!(lids.len(), 1, "sealed pod has one closed lid");
                assert_eq!(
                    lids[0].center,
                    Vec3::new(0.0, POD_HEIGHT + LID_THICKNESS / 2.0, 0.0)
                );
                assert_eq!(
                    lids[0].size,
                    Vec3::new(POD_WIDTH, LID_THICKNESS, POD_LENGTH)
                );
                assert_eq!(blankets, 0, "no blanket on a sealed pod");
            }
            PodState::EmptyOpen => {
                assert_eq!(lids.len(), 1, "empty-open pod has one open lid");
                assert!(
                    (lids[0].roll_radians + LID_OPEN_TILT).abs() < f32::EPSILON,
                    "the lid is propped open, not closed or upright"
                );
                assert!(blankets >= 1, "the occupancy blanket hangs");
            }
            PodState::Player => {
                assert_eq!(lids.len(), 1, "the player pod has one canopy");
                assert_eq!(
                    lids[0].center,
                    Vec3::new(
                        0.0,
                        POD_HEIGHT + CANOPY_LENGTH / 2.0,
                        -(POD_LENGTH - LID_THICKNESS) / 2.0
                    )
                );
                assert!(
                    lids[0].size.y > lids[0].size.z,
                    "the canopy rises over the head end, it does not lie flat"
                );
                assert_eq!(blankets, 0, "no blanket on the player pod");
            }
        }
    }
}
