//! Runner crate for the play-test harness of `gone` (issue #5 / slice A).
//!
//! The protocol surface (scenario, report, input adapter, frame-code) is owned and
//! defined once in `gone_app::harness`; this crate re-exports that single truth
//! so the runner binary and the app always speak the same JSON and pixel encoding.
//! The crate itself contains no protocol definitions; its binary drives
//! `target/debug/gone_app` and verifies against the app's report and captures.
//! The [`onscreen`] and [`gameplay`] modules are runner tooling: the machine
//! verification of the render canary's single onscreen capture, of the
//! gameplay lane's room and yaw assertions, and of the gameplay-full lane's
//! wake progression, exit waypoint, and door walk.

pub mod gameplay;
pub mod onscreen;

pub use gone_app::harness::*;
