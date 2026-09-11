//! The four matrix cells and the predeclared scene constants they are built
//! from.
//!
//! # Wall-clock budgeting of the sample ticks
//!
//! Headless frames are paced by the render pipeline (no vsync) and one
//! logical tick runs per rendered frame, so tick counts convert to wall time
//! through the measured frame cadence. The perf lane measured the bootstrap
//! scene at 0.83 ms/frame (1210 fps) on this host; the calibration lane
//! renders the real post chain and is slower per frame, which only makes the
//! same tick counts cover MORE wall time (the app's adaptation runs on
//! wall-clock deltas, so extra wall time per tick means more settling, never
//! less). Every window below is sized at the fast measured cadence, and the
//! lane's child timeout is far above the slowest plausible cadence.
//!
//! # Adaptation model the bounds rely on
//!
//! Bevy 0.19 `AutoExposure` meters the masked histogram toward a fixed
//! target, moving exposure at the documented defaults the app binds
//! unchanged: `speed_brighten` 3 f-stops/s and `speed_darken` 1 f-stop/s,
//! linear for moves larger than 1.5 f-stops and exponential with time
//! constant 1.5/speed seconds below that. At [`INITIAL_LEVEL`] the
//! mask-metered luminance is ~0.65, so the readiness exposure gap is ~0.6
//! f-stops (exponential, 1.5 s time constant); the cells' step is +1 f-stop
//! on the brighten side (0.5 s time constant) and the patch move is ~0.2
//! f-stops on the darken side (1.5 s time constant). The sample windows give
//! each perturbation several multiples of its time constant at the fast
//! cadence before the assertions read the sequence.

use crate::calibration::{CalibrationParams, LuminanceStep, MaskSelection, PatchPlan};
use crate::{Beat, Content, Scenario, ScenarioMode};

/// The wall's linear radiance before the step in every cell. With the
/// centered patch it meters to ~0.65 (mask-weighted wall ~0.98·0.28·L plus
/// patch ~0.005·0.97·10·L), so the readiness exposure gap is ~0.6 f-stops:
/// small enough to settle inside the pre-step window, large enough that the
/// run exercises adaptation before the first sample.
const INITIAL_LEVEL: f32 = 2.0;

/// The wall's linear radiance from the step tick on in cells A and B: a
/// +1 f-stop raw step, large enough that the post-tonemap mean move is
/// unmistakable, small enough that adaptation converges well inside the
/// post window.
const STEP_LEVEL: f32 = 4.0;

/// The bright patch's area fraction in every cell: 0.5% of the frame, equal
/// in both placements. Small enough that the patch move's metering change
/// (~0.2 f-stops under the center-weighted mask) settles quickly, large
/// enough that the placement difference stays far above the assertion
/// floors.
const PATCH_AREA_FRACTION: f32 = 0.005;

/// First pre-perturbation sample: ~8.5 s at the measured fast cadence
/// (0.83 ms/frame), by which the readiness adaptation (~0.6 f-stops, 1.5 s
/// time constant) has decayed below 0.005 f-stops.
const PRE_EARLY_TICK: u64 = 10_200;

/// Second pre-perturbation sample: ~9.5 s, one settled interval after
/// [`PRE_EARLY_TICK`]; the pair must read flat.
const PRE_LATE_TICK: u64 = 11_400;

/// The pinned perturbation tick in every cell: the luminance step in A/B,
/// the patch's center-to-edge move in C/D. ~10.5 s, after the settled
/// pre-perturbation window.
pub(super) const PERTURB_TICK: u64 = 12_600;

/// The step tick for cells C and D: beyond `max_frames`, so the step never
/// lands and the run isolates the patch move; the level equals the initial
/// level, making the declared step a no-op by construction.
const NOOP_STEP_TICK: u64 = 24_600;

/// The scenario deadline in rendered frames: past the last sample plus the
/// capture settle window.
const MAX_FRAMES: u64 = 24_000;

/// Cells A/B: the first post-step sample, one tick after the step, while
/// exposure has adapted for at most a frame or two (well under 0.05 f-stops
/// at either cadence): the sample must show the raw step, not the
/// adaptation.
const POST_JUMP_TICK: u64 = 12_601;

/// Cells A/B: post-step sample offsets from the step, in ticks, chosen so
/// the last one sits ~4.5 s after the step — nine 0.5 s time constants of
/// the 3 f-stops/s brighten-side adaptation for the 1 f-stop step (residual
/// below 0.002 f-stops).
const POST_STEP_TICKS: [u64; 4] = [13_200, 14_400, 15_600, 18_000];

/// Cells C/D: post-move sample offsets from the move, in ticks. The darken
/// side adapts at 1 f-stop/s (1.5 s time constant); the ~0.2 f-stop move
/// decays to ~0.014 f-stops by the +4 s sample and ~0.004 by the +6 s one,
/// so the final pair reads settled and the windows on them compare
/// placements.
const EDGE_MOVE_TICKS: [u64; 4] = [15_000, 17_400, 19_800, 22_200];

/// Samples averaged into each placement window of cells C/D: the first two
/// samples (both pre-move) against the last two (both post-move).
pub(super) const PLACEMENT_WINDOW: usize = 2;

/// The four matrix cells.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum CellId {
    /// Luminance step, center mask, AE ON.
    A,
    /// Luminance step, center mask, AE OFF (control).
    B,
    /// Patch metering center-to-edge, center mask, AE ON.
    C,
    /// Patch metering center-to-edge, uniform mask, AE ON (control).
    D,
}

impl CellId {
    /// The cell's letter, as used in run names and failure lines.
    #[must_use]
    pub const fn label(self) -> &'static str {
        match self {
            Self::A => "A",
            Self::B => "B",
            Self::C => "C",
            Self::D => "D",
        }
    }

    /// One-line description of what the cell isolates.
    #[must_use]
    pub const fn description(self) -> &'static str {
        match self {
            Self::A => "luminance step / center mask / AE on",
            Self::B => "luminance step / center mask / AE off (control)",
            Self::C => "patch center-to-edge / center mask / AE on",
            Self::D => "patch center-to-edge / uniform mask / AE on (control)",
        }
    }
}

/// One matrix cell: the predeclared scenario parameters, its pinned sample
/// ticks, and the seed that keys the run id.
#[derive(Clone, Debug, PartialEq)]
pub struct MatrixCell {
    /// Which cell of the matrix this is.
    pub id: CellId,
    /// Scenario seed (also embedded in the run id).
    pub seed: u64,
    /// The calibration parameters the scenario predeclares.
    pub params: CalibrationParams,
    /// The pinned sample ticks as (beat name, tick) pairs, in tick order.
    pub beats: Vec<(&'static str, u64)>,
}

impl MatrixCell {
    /// The cell's scenario: named `calibration` so every run dir lands under
    /// `tmp/harness/calibration/<run-id>/`, calibration mode, no scripted
    /// actions (the lane is closed), the beats as the pinned sample ticks.
    #[must_use]
    pub fn scenario(&self) -> Scenario {
        Scenario {
            name: "calibration".to_owned(),
            seed: self.seed,
            ticks_per_second: crate::TICKS_PER_SECOND,
            actions: Vec::new(),
            beats: self
                .beats
                .iter()
                .map(|(name, tick)| Beat::new(name, *tick))
                .collect(),
            pacing: None,
            max_frames: MAX_FRAMES,
            mode: ScenarioMode::Calibration,
            warmup_frames: 0,
            sample_frames: 0,
            content: Content::Calibration,
            calibration: Some(self.params),
        }
    }
}

/// The step timeline's parameters (cells A/B): luminance step under the
/// center-weighted mask, AE ON (cell B overrides the AE arm off).
fn step_params() -> CalibrationParams {
    CalibrationParams {
        initial_level: INITIAL_LEVEL,
        step: LuminanceStep {
            tick: PERTURB_TICK,
            level: STEP_LEVEL,
        },
        patch_area_fraction: PATCH_AREA_FRACTION,
        patch: PatchPlan::FixedCenter,
        mask: MaskSelection::CenterWeighted,
        auto_exposure: true,
    }
}

/// The move timeline's parameters (cells C/D): equal-area patch moving
/// center-to-edge at the pinned tick under a no-op step, AE ON (cell D
/// overrides the mask to uniform).
fn patch_params() -> CalibrationParams {
    CalibrationParams {
        initial_level: INITIAL_LEVEL,
        step: LuminanceStep {
            tick: NOOP_STEP_TICK,
            level: INITIAL_LEVEL,
        },
        patch_area_fraction: PATCH_AREA_FRACTION,
        patch: PatchPlan::CenterThenEdge {
            at_tick: PERTURB_TICK,
        },
        mask: MaskSelection::CenterWeighted,
        auto_exposure: true,
    }
}

/// The step cells' pinned sample ticks: settled pre window, jump sample,
/// settling window.
fn step_beats() -> Vec<(&'static str, u64)> {
    vec![
        ("pre-1", PRE_EARLY_TICK),
        ("pre-2", PRE_LATE_TICK),
        ("post-jump", POST_JUMP_TICK),
        ("post-1", POST_STEP_TICKS[0]),
        ("post-2", POST_STEP_TICKS[1]),
        ("post-3", POST_STEP_TICKS[2]),
        ("post-4", POST_STEP_TICKS[3]),
    ]
}

/// The move cells' pinned sample ticks: settled center window, the move,
/// four settled edge samples.
fn move_beats() -> Vec<(&'static str, u64)> {
    vec![
        ("center-1", PRE_EARLY_TICK),
        ("center-2", PRE_LATE_TICK),
        ("edge-1", EDGE_MOVE_TICKS[0]),
        ("edge-2", EDGE_MOVE_TICKS[1]),
        ("edge-3", EDGE_MOVE_TICKS[2]),
        ("edge-4", EDGE_MOVE_TICKS[3]),
    ]
}

/// The fixed 4-run matrix, in A, B, C, D order.
///
/// A and B share the step timeline (settled pre window, step, jump sample,
/// settling window) so the only difference between them is the AE arm; C and
/// D share the patch-move timeline so the only difference between them is
/// the mask.
#[must_use]
pub fn matrix() -> [MatrixCell; 4] {
    let step_params = step_params();
    let ae_off_params = CalibrationParams {
        auto_exposure: false,
        ..step_params
    };
    let patch_params = patch_params();
    let uniform_params = CalibrationParams {
        mask: MaskSelection::Uniform,
        ..patch_params
    };
    [
        MatrixCell {
            id: CellId::A,
            seed: 11,
            params: step_params,
            beats: step_beats(),
        },
        MatrixCell {
            id: CellId::B,
            seed: 12,
            params: ae_off_params,
            beats: step_beats(),
        },
        MatrixCell {
            id: CellId::C,
            seed: 13,
            params: patch_params,
            beats: move_beats(),
        },
        MatrixCell {
            id: CellId::D,
            seed: 14,
            params: uniform_params,
            beats: move_beats(),
        },
    ]
}
