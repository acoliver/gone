//! The `gone` game executable (issue #6 slice A).
//!
//! Thin shim over `gone_app::run` so the harness runner spawns
//! `target/debug/gone_app`. `AppExit` maps to `std::process::ExitCode` via
//! Bevy's `Termination` impl, so the runner sees the same 0 / non-zero split.

fn main() -> bevy::app::AppExit {
    gone_app::run()
}
