//! The `gone` harness protocol (issue #5 / slice A).
//!
//! This module is the single home of every protocol type shared between the
//! app and the runner: the scenario format, the input adapter, the frame-code
//! pixel encoding, the report schema, the beat expectations, and the
//! performance-lane policy and statistics. The direction is fixed: the app
//! (`gone_app`) owns this surface and serializes/writes it, the runner
//! (`gone_harness`) is the consumer. `gone_harness` re-exports these types and
//! never defines them itself, so there is exactly one truth for the JSON
//! on the wire and for the pixel encoding the runner decodes from captured PNGs.
//!
//! The whole module is dependency-free (std + `serde` only), so `gone_harness`
//! can re-export it without pulling any render code into the runner.

pub mod beat;
pub mod calibration;
pub mod frame;
pub mod input;
pub mod perf;
pub mod report;
pub mod scenario;

pub use beat::*;
pub use calibration::*;
pub use frame::*;
pub use input::*;
pub use perf::*;
pub use report::*;
pub use scenario::*;

/// Shared protocol version. The app and the runner both embed this and refuse to
/// pair across a mismatch, so a stale binary and a stale runner fail loudly
/// instead of misreading each other's JSON.
///
/// Version 2: captures are real rendered-window screenshots (the frame-code chip
/// is a scene sprite), input events carry their edge (`Key(Forward) press`), and
/// a `Failure` event records capture/report errors in the report itself.
///
/// Version 3: the performance lane — scenarios gain a `mode` (capture or perf)
/// with warmup/sample window counts, reports gain the optional `perf` section
/// (raw wall-clock samples plus statistics), and the scenario `pacing` field is
/// consumed at window creation (Uncapped lifts vsync for the run).
///
/// Version 4: the calibration-evidence lane — scenarios gain the `calibration`
/// mode plus a required `calibration` section (one luminance step, an
/// equal-area bright-patch placement plan, a metering-mask selection, and the
/// auto-exposure arm), and reports gain the `Calibration` event, recorded once
/// before any calibration dynamics with the setup evidence (mask selection plus
/// the sha256 of the loaded mask asset's pixel bytes, the auto-exposure settings
/// in force, the authored exposure, the patch area and placements, the light
/// levels and step tick, and the pinned sample ticks). The capture and perf
/// surfaces are unchanged.
pub const PROTOCOL_VERSION: u32 = 4;
