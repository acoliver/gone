//! Runner crate for the play-test harness of `gone` (issue #5 / slice A).
//!
//! The protocol surface (scenario, report, input adapter, frame-code) is owned and
//! defined once in `gone_app::harness`; this crate re-exports that single truth
//! so the runner binary and the app always speak the same JSON and pixel encoding.
//! The crate itself contains no protocol definitions; its binary drives
//! `target/debug/gone_app` and verifies against the app's report and captures.
//! The crate also carries runner-side verification lanes: [`onscreen`]
//! machine-verifies the render canary's onscreen capture, [`gameplay`] the
//! gameplay lane's room and yaw assertions and the gameplay-full lane's wake
//! progression, exit waypoint, and door walk, [`calibration_lane`] runs
//! the four-cell calibration matrix over the app's calibration-evidence lane,
//! and [`lifecycle_lane`] runs the stage-B lifecycle lane over the app's
//! native window observations (focus loss, reacquisition, resize, clean
//! close, runner timeout).

pub mod calibration_lane;
pub mod gameplay;
pub mod lifecycle_lane;
pub mod onscreen;

pub use gone_app::harness::*;
