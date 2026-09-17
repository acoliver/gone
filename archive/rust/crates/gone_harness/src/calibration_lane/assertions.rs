//! The predeclared assertions: named bounds whose doc comments state the
//! physical reason for each, evaluated over the measured `(tick, frame,
//! mean)` sequence.

use serde::Serialize;

use super::Sample;
use super::matrix::{PERTURB_TICK, PLACEMENT_WINDOW};

/// Flatness bound for the pre-perturbation window and the settled checks,
/// in linear-light mean luminance. After settling, exposure is stationary
/// and consecutive frames are the same render, so means differ only by
/// quantization and dither (well under 0.1% of this lane's ~0.3-0.6 means);
/// 0.01 is ~2% of a mean, far above that noise and far below the +1 f-stop
/// step signal (~x2 radiance) and the placement difference (~14%).
pub const PRE_FLAT_EPSILON: f64 = 0.01;

/// Minimum rise of the first post-step mean over the last pre-step mean, in
/// linear-light mean luminance. A +1 f-stop raw step doubles scene radiance;
/// with exposure adapted for at most a frame or two, the post-tonemap mean
/// rises by roughly a third of its own value (`AgX` compresses the shoulder)
/// — an order of magnitude above this floor. The floor exists to make the
/// direction unmistakable: adaptation must not move the mean DOWN at the
/// step.
pub const STEP_JUMP_MIN_LINEAR: f64 = 0.05;

/// Bound on `|last post-step mean − first pre-step mean|` in cell A, in
/// linear-light mean luminance. With AE on, the converged exposure
/// compensates the doubled radiance exactly, so the settled frame renders
/// the same output as the pre-step frame; the residual adaptation error at
/// the sampled horizon is under 0.2% of a mean and 0.01 is ~2%.
pub const CONVERGENCE_EPSILON: f64 = 0.01;

/// Bound on every post-step mean's distance from the FIRST post-step mean in
/// cell B, in linear-light mean luminance. With AE off there is no exposure
/// to adapt: every post-step frame is the same render at the stepped level,
/// so any drift is a finding by construction.
pub const NO_ADAPTATION_EPSILON: f64 = 0.01;

/// Minimum rise of the last post-step mean over the first pre-step mean in
/// cell B, in linear-light mean luminance: the control that proves the mean
/// KEPT the step instead of adapting back. The physics matches
/// [`STEP_JUMP_MIN_LINEAR`]; the separate constant keeps the two claims
/// independently readable in the artifact.
pub const TRACKS_STEP_MIN_LINEAR: f64 = 0.05;

/// Minimum `edge-window mean − center-window mean` in cell C, in linear-light
/// mean luminance. The center-weighted mask gives the centered patch several
/// times the metering weight of the edge patch, so converged exposure
/// differs by ~0.2 f-stops between placements and the edge placement (lower
/// metered luminance, higher exposure) renders BRIGHTER: the difference must
/// exist and must point that way.
pub const PLACEMENT_DIFFERENCE_MIN_LINEAR: f64 = 0.02;

/// Bound on `|edge-window mean − center-window mean|` in cell D, in
/// linear-light mean luminance. The uniform mask weights both slots
/// identically, so metering, exposure, and output are the same either way;
/// the only positional residue is the vignette's mild darkening at the edge
/// slot on a 0.5%-area patch, well under half a percent of a mean — far
/// inside 0.01.
pub const DIFFERENCE_REMOVED_EPSILON: f64 = 0.01;

/// Bound on the change between the last two edge-window samples in C/D, in
/// linear-light mean luminance: the darken-side adaptation tail must be this
/// small before the placement windows compare converged states (at the
/// sampled horizon the residual drift is under 0.7% of a mean).
pub const EDGE_SETTLED_EPSILON: f64 = 0.01;

/// One predeclared assertion's outcome: expected vs measured, both carried
/// into the failure line and the evidence artifact.
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct AssertionOutcome {
    /// Stable assertion name (the failure line and artifact key by it).
    pub name: &'static str,
    /// Whether the measured sequence satisfied the predeclared bound.
    pub passed: bool,
    /// The predeclared bound, with the physical reason and the reference
    /// numbers it compares against.
    pub expected: String,
    /// The measured numbers, with the tick ranges they came from.
    pub measured: String,
}

/// The pre-perturbation window's outcome: every sample before the
/// perturbation tick must read flat against the window's first sample.
fn pre_flat(samples: &[Sample], before_tick: u64, label: &'static str) -> AssertionOutcome {
    let window: Vec<&Sample> = samples
        .iter()
        .take_while(|sample| sample.tick < before_tick)
        .collect();
    let first = window[0].mean_linear;
    let worst = window
        .iter()
        .map(|sample| (sample.mean_linear - first).abs())
        .fold(f64::NEG_INFINITY, f64::max);
    AssertionOutcome {
        name: label,
        passed: worst <= PRE_FLAT_EPSILON,
        expected: format!(
            "every pre-perturbation mean within {PRE_FLAT_EPSILON:.3} of the first \
             ({first:.6}; exposure is settled before the perturbation)"
        ),
        measured: format!(
            "max |delta| {worst:.6} over ticks {}-{}",
            window[0].tick,
            window[window.len() - 1].tick
        ),
    }
}

/// Cells A and B: the first post-step mean must exceed the last pre-step
/// mean by at least [`STEP_JUMP_MIN_LINEAR`] — the raw step moves the frame
/// before any adaptation can.
fn step_moves_mean_up(samples: &[Sample]) -> AssertionOutcome {
    let last_pre = &samples[1];
    let first_post = &samples[2];
    let rise = first_post.mean_linear - last_pre.mean_linear;
    AssertionOutcome {
        name: "step-moves-mean-up",
        passed: rise >= STEP_JUMP_MIN_LINEAR,
        expected: format!(
            "first post-step mean - last pre-step mean >= {STEP_JUMP_MIN_LINEAR:.3} \
             (the +1 f-stop raw step doubles the radiance before adaptation)"
        ),
        measured: format!(
            "{:.6} - {:.6} = {rise:.6} (tick {} vs tick {})",
            first_post.mean_linear, last_pre.mean_linear, first_post.tick, last_pre.tick
        ),
    }
}

/// Cell A: the settled post-step mean must return to the pre-step baseline —
/// auto exposure adapts the +1 f-stop back.
fn converges_back(samples: &[Sample]) -> AssertionOutcome {
    let baseline = samples[0].mean_linear;
    let last = samples[samples.len() - 1].mean_linear;
    let delta = (last - baseline).abs();
    AssertionOutcome {
        name: "converges-back",
        passed: delta <= CONVERGENCE_EPSILON,
        expected: format!(
            "|last post-step mean - first pre-step mean| <= {CONVERGENCE_EPSILON:.3} \
             (AE ON adapts the +1 f-stop back; baseline {baseline:.6})"
        ),
        measured: format!(
            "|{last:.6} - {baseline:.6}| = {delta:.6} (last post tick {})",
            samples[samples.len() - 1].tick
        ),
    }
}

/// Cell B: every post-step mean must stay within [`NO_ADAPTATION_EPSILON`]
/// of the first post-step mean — AE off cannot adapt.
fn no_adaptation(samples: &[Sample]) -> AssertionOutcome {
    let first_post = samples[2].mean_linear;
    let worst = samples[2..]
        .iter()
        .map(|sample| (sample.mean_linear - first_post).abs())
        .fold(f64::NEG_INFINITY, f64::max);
    AssertionOutcome {
        name: "no-adaptation",
        passed: worst <= NO_ADAPTATION_EPSILON,
        expected: format!(
            "every post-step mean within {NO_ADAPTATION_EPSILON:.3} of the first \
             post-step ({first_post:.6}; AE OFF cannot adapt)"
        ),
        measured: format!(
            "max |delta| {worst:.6} over ticks {}-{}",
            samples[2].tick,
            samples[samples.len() - 1].tick
        ),
    }
}

/// Cell B: the last post-step mean must keep at least
/// [`TRACKS_STEP_MIN_LINEAR`] over the first pre-step mean — the mean kept
/// the step instead of adapting back.
fn tracks_step(samples: &[Sample]) -> AssertionOutcome {
    let baseline = samples[0].mean_linear;
    let last = samples[samples.len() - 1].mean_linear;
    let rise = last - baseline;
    AssertionOutcome {
        name: "tracks-step",
        passed: rise >= TRACKS_STEP_MIN_LINEAR,
        expected: format!(
            "last post-step mean - first pre-step mean >= {TRACKS_STEP_MIN_LINEAR:.3} \
             (AE OFF tracks the step exactly; baseline {baseline:.6})"
        ),
        measured: format!(
            "{last:.6} - {baseline:.6} = {rise:.6} (last post tick {})",
            samples[samples.len() - 1].tick
        ),
    }
}

/// Cells C and D: the last two edge samples must read flat — the
/// darken-side adaptation tail is small enough that the placement windows
/// compare converged states.
fn edge_settled(samples: &[Sample]) -> AssertionOutcome {
    let older = samples[samples.len() - 2].mean_linear;
    let newest = samples[samples.len() - 1].mean_linear;
    let delta = (newest - older).abs();
    AssertionOutcome {
        name: "edge-settled",
        passed: delta <= EDGE_SETTLED_EPSILON,
        expected: format!(
            "|last two edge-window means| <= {EDGE_SETTLED_EPSILON:.3} (the adaptation \
             tail at the sampled horizon is under 0.7% of a mean)"
        ),
        measured: format!(
            "|{newest:.6} - {older:.6}| = {delta:.6} (ticks {} vs {})",
            samples[samples.len() - 2].tick,
            samples[samples.len() - 1].tick
        ),
    }
}

/// The placement windows for cells C/D: (center mean, edge mean, and the
/// tick ranges each window covers). Center window is the first
/// [`PLACEMENT_WINDOW`] samples (both pre-move); edge window the last
/// [`PLACEMENT_WINDOW`] (both settled post-move).
fn placement_windows(samples: &[Sample]) -> (f64, f64, u64, u64, u64, u64) {
    let edge_start = samples.len() - PLACEMENT_WINDOW;
    let mean = |slice: &[Sample]| {
        slice.iter().map(|s| s.mean_linear).sum::<f64>()
            / f64::from(
                u32::try_from(slice.len()).expect("windows hold more than u32::MAX samples"),
            )
    };
    (
        mean(&samples[..PLACEMENT_WINDOW]),
        mean(&samples[edge_start..]),
        samples[0].tick,
        samples[PLACEMENT_WINDOW - 1].tick,
        samples[edge_start].tick,
        samples[samples.len() - 1].tick,
    )
}

/// Cell C: the edge-window mean must exceed the center-window mean by at
/// least [`PLACEMENT_DIFFERENCE_MIN_LINEAR`] — the center-weighted mask
/// meters the centered patch harder, so the edge placement's exposure is
/// higher and it renders brighter.
fn edge_brighter_than_center(samples: &[Sample]) -> AssertionOutcome {
    let (center, edge, c0, c1, e0, e1) = placement_windows(samples);
    let diff = edge - center;
    AssertionOutcome {
        name: "edge-brighter-than-center",
        passed: diff >= PLACEMENT_DIFFERENCE_MIN_LINEAR,
        expected: format!(
            "edge-window mean - center-window mean >= {PLACEMENT_DIFFERENCE_MIN_LINEAR:.3} \
             (the center-weighted mask meters the centered patch harder, so the \
             edge placement's exposure is higher and it renders brighter)"
        ),
        measured: format!(
            "edge {edge:.6} (ticks {e0}-{e1}) - center {center:.6} (ticks {c0}-{c1}) = {diff:.6}"
        ),
    }
}

/// Cell D: the placement windows must agree within
/// [`DIFFERENCE_REMOVED_EPSILON`] — the uniform mask removes the
/// center-vs-edge metering difference.
fn difference_removed(samples: &[Sample]) -> AssertionOutcome {
    let (center, edge, c0, c1, e0, e1) = placement_windows(samples);
    let diff = (edge - center).abs();
    AssertionOutcome {
        name: "difference-removed",
        passed: diff <= DIFFERENCE_REMOVED_EPSILON,
        expected: format!(
            "|edge-window mean - center-window mean| <= {DIFFERENCE_REMOVED_EPSILON:.3} \
             (the uniform mask weights both slots identically)"
        ),
        measured: format!(
            "|edge {edge:.6} (ticks {e0}-{e1}) - center {center:.6} (ticks {c0}-{c1})| = {diff:.6}"
        ),
    }
}

/// Evaluate the cell's predeclared assertions over the measured sequence.
/// Positions are the cell's beat layout (verified by the runner's
/// `check_sample_layout` before this runs): samples 0-1 are the settled pre
/// window, sample 2 the first post-perturbation sample, the rest the
/// settling window.
#[must_use]
pub fn evaluate_cell(cell: &super::MatrixCell, samples: &[Sample]) -> Vec<AssertionOutcome> {
    match cell.id {
        super::CellId::A => vec![
            pre_flat(samples, PERTURB_TICK, "pre-step-flat"),
            step_moves_mean_up(samples),
            converges_back(samples),
        ],
        super::CellId::B => vec![
            pre_flat(samples, PERTURB_TICK, "pre-step-flat"),
            step_moves_mean_up(samples),
            no_adaptation(samples),
            tracks_step(samples),
        ],
        super::CellId::C => vec![
            pre_flat(samples, PERTURB_TICK, "pre-move-flat"),
            edge_settled(samples),
            edge_brighter_than_center(samples),
        ],
        super::CellId::D => vec![
            pre_flat(samples, PERTURB_TICK, "pre-move-flat"),
            edge_settled(samples),
            difference_removed(samples),
        ],
    }
}
