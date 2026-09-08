//! The `gone` harness protocol (issue #5 / slice A).
//!
//! This module is the single home of every protocol type shared between the
//! app and the runner: the scenario format, the input adapter, the frame-code
//! pixel encoding, the report schema, and beat expectations. The direction is
//! fixed: the app (`gone_app`) owns this surface and serializes/writes it, the
//! runner (`gone_harness`) is the consumer. `gone_harness` re-exports these
//! types and never defines them itself, so there is exactly one truth for the JSON
//! on the wire and for the pixel encoding the runner decodes from captured PNGs.
//!
//! The whole module is dependency-free (std + `serde` only), so `gone_harness`
//! can re-export it without pulling any render code into the runner.

pub mod beat;
pub mod frame;
pub mod input;
pub mod report;
pub mod scenario;

pub use beat::*;
pub use frame::*;
pub use input::*;
pub use report::*;
pub use scenario::*;

/// Shared protocol version. The app and the runner both embed this and refuse to
/// pair across a mismatch, so a stale binary and a stale runner fail loudly
/// instead of misreading each other's JSON.
pub const PROTOCOL_VERSION: u32 = 1;
