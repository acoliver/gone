//! Placement-derived gameplay truth shared by the game's own build and the
//! runner's machine checks.
//!
//! The gameplay-full lane's runner verifies a run against numbers it derives
//! itself from the frozen placement data (the exit waypoint, the hatch
//! placement), never from literals and never from the app's own report. That
//! derivation needs two values that live on this side of the boundary: the
//! authored exit path (built against the scene's tray floor, which is
//! crate-internal) and the standing eye height (the rig's own constant).
//! They are single-sourced here: the scene plugin and the player motion
//! slice consume the same items, so the game and its verifier cannot drift.
//!
//! The re-exported [`gone_sim`] crate rides along for the same reason: the
//! architecture gate forbids `gone_harness` declaring a direct `gone_sim`
//! dependency edge (see `xtask check architecture`), so the app in the
//! middle hands the frozen registry through. The harness protocol module
//! itself stays free of simulation references; this sibling module is the
//! one public home for shared gameplay truth.

use gone_sim::exit::ExitPath;

/// Standing eye height above the capsule foot's ground contact, in meters:
/// the controller spec's standing height "puts the eye point near 1.6 m",
/// and this is that number for the rig. The player motion slice projects
/// the standing capsule onto the rig through it, and the runner derives the
/// expected standing eye point from it.
pub const STANDING_EYE_HEIGHT: f32 = 1.6;

/// The authored get-up path out of the player pod, built exactly as the
/// scene plugin builds it at boot: the frozen player pod's placement against
/// the tray floor the cavity build actually constructs. The runner derives
/// its exit waypoint expectation from this same path.
///
/// # Panics
/// Panics when the frozen placement authors an invalid exit path (the same
/// construction the scene plugin performs and asserts at boot, so a frozen
/// edit that breaks it fails everywhere identically).
#[must_use]
pub fn player_exit_path() -> ExitPath {
    ExitPath::try_new(
        gone_sim::PodRegistry::frozen().player_pod().placement(),
        crate::scene::pod_body::TRAY_FLOOR_Y,
    )
    .expect("the frozen player pod authors a valid exit path")
}

#[cfg(test)]
mod tests {
    use gone_sim::controller::{CAPSULE_RADIUS, PENETRATION_TOLERANCE};

    use super::STANDING_EYE_HEIGHT;

    /// The path this module hands out is the scene plugin's own build: the
    /// same construction with the same inputs, so the waypoint the runner
    /// asserts against is the waypoint the get-up walks.
    #[test]
    fn the_shared_exit_path_is_the_scene_plugin_construction() {
        let shared = super::player_exit_path();
        let registry = gone_sim::PodRegistry::frozen();
        let scene_built = gone_sim::exit::ExitPath::try_new(
            registry.player_pod().placement(),
            crate::scene::pod_body::TRAY_FLOOR_Y,
        )
        .expect("the frozen player pod authors a valid exit path");
        assert_eq!(shared, scene_built);
        // The final pose stands on the room floor: its foot's height is the
        // frozen standing capsule rest, from which the standing eye height
        // derives.
        let foot = shared.waypoint().foot();
        assert!(
            (foot.y - (CAPSULE_RADIUS + PENETRATION_TOLERANCE)).abs() < f32::EPSILON,
            "the waypoint foot rests on the room floor: {foot:?}"
        );
        let expected_eye_y = foot.y - CAPSULE_RADIUS + STANDING_EYE_HEIGHT;
        assert!((expected_eye_y - (PENETRATION_TOLERANCE + STANDING_EYE_HEIGHT)).abs() < 1e-6);
    }
}
