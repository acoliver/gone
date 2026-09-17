//! Runner-side calibration matrix lane (issue #6): `gone-harness calibration`.
//!
//! Four fixed child-app runs, each one calibration-mode scenario (protocol v4,
//! `crates/gone_app/src/harness/calibration.rs`): the app renders the real post
//! chain into the offscreen capture target, applies the predeclared scene
//! dynamics per logical tick, and records the setup evidence (`TimedEvent::
//! Calibration`); the scenario's beats are the pinned capture sample ticks.
//! This module owns the runner's half:
//!
//! - **A** [`CellId::A`] luminance step, center mask, auto exposure ON: the
//!   wall level doubles at a pinned tick; samples straddle the step through
//!   settling.
//! - **B** [`CellId::B`] AE-off control: the same step with auto exposure OFF,
//!   so no adaptation is possible and the post-tonemap mean must jump at the
//!   step and stay there.
//! - **C** [`CellId::C`] patch metering, center mask, AE ON: an equal-area
//!   bright patch starts centered and moves to the edge slot at a pinned tick.
//! - **D** [`CellId::D`] uniform-mask control: the same patch move under the
//!   uniform mask, the arm that must remove the center-vs-edge metering
//!   difference.
//!
//! The runner measures every beat capture's mean luminance (sRGB decoded to
//! linear light through a 256-entry LUT, Rec. 709 luma weights; raw encoded
//! channel means recorded alongside), builds the `(tick, frame, mean)`
//! sequence, and checks the PREDECLARED assertions: named constants whose doc
//! comments state the physical reason for each bound. A live run that
//! contradicts a predeclared assertion is a FINDING, never a reason to edit
//! the constant: the lane fails naming the run, the assertion, and the
//! expected-vs-measured numbers, and the evidence artifact
//! (`calibration-evidence.json` in the run dir) records both.

mod assertions;
mod evidence;
mod matrix;
mod measurement;

pub use assertions::{
    AssertionOutcome, CONVERGENCE_EPSILON, DIFFERENCE_REMOVED_EPSILON, EDGE_SETTLED_EPSILON,
    NO_ADAPTATION_EPSILON, PLACEMENT_DIFFERENCE_MIN_LINEAR, PRE_FLAT_EPSILON, STEP_JUMP_MIN_LINEAR,
    TRACKS_STEP_MIN_LINEAR, evaluate_cell,
};
pub use matrix::{CellId, MatrixCell, matrix};
pub use measurement::Sample;

use std::path::{Path, PathBuf};

use crate::report;

use evidence::{RunEvidence, crosscheck_evidence, extract_evidence, write_artifact};
use measurement::measure_samples;

/// The lane's verdict over one finished run: measured samples, per-assertion
/// outcomes, and where the evidence artifact landed.
#[derive(Debug)]
pub struct CellJudgment {
    /// The cell that was judged.
    pub cell_id: CellId,
    /// Whether every predeclared assertion held.
    pub passed: bool,
    /// The measured (tick, frame, mean) sequence in tick order.
    pub samples: Vec<Sample>,
    /// Every predeclared assertion's outcome, in evaluation order.
    pub assertions: Vec<AssertionOutcome>,
    /// The evidence artifact written beside the run's report.
    pub artifact_path: PathBuf,
}

/// Judge one finished calibration run: read its report, extract and
/// cross-check the recorded setup evidence against the cell's predeclared
/// parameters, measure every beat capture, evaluate the predeclared
/// assertions, and write `calibration-evidence.json` into the run dir.
///
/// # Errors
/// A named error when the report is missing or unparseable, the Calibration
/// event is absent or duplicated, the recorded evidence disagrees with the
/// cell's parameters, a capture PNG is missing or the wrong extent, or the
/// sample sequence does not line up positionally with the cell's beats.
pub fn judge_cell(cell: &MatrixCell, run_dir: &Path, run_id: &str) -> Result<CellJudgment, String> {
    let report_path = run_dir.join("report.json");
    let report_text = std::fs::read_to_string(&report_path)
        .map_err(|e| format!("failed to read {}: {e}", report_path.display()))?;
    let report = report::parse_report(&report_text)
        .map_err(|e| format!("report parse (cell {}): {e}", cell.id.label()))?;
    let evidence = extract_evidence(&report, cell.id)?;
    crosscheck_evidence(evidence, cell)?;
    let samples = measure_samples(&report, run_dir)?;
    check_sample_layout(cell, &samples)?;
    let assertions = evaluate_cell(cell, &samples);
    let passed = assertions.iter().all(|outcome| outcome.passed);
    let artifact_path = write_artifact(
        run_dir,
        &RunEvidence {
            run_id,
            cell,
            evidence,
            samples: &samples,
            assertions: &assertions,
            passed,
        },
    )?;
    Ok(CellJudgment {
        cell_id: cell.id,
        passed,
        samples,
        assertions,
        artifact_path,
    })
}

/// Verify the measured sequence lines up positionally with the cell's
/// predeclared beats: same names, same ticks, same order. Every evaluator in
/// [`assertions`] indexes positionally, so this is their precondition.
///
/// # Errors
/// Naming the first position where the report's beat manifest disagrees with
/// the cell.
fn check_sample_layout(cell: &MatrixCell, samples: &[Sample]) -> Result<(), String> {
    if samples.len() != cell.beats.len() {
        return Err(format!(
            "cell {}: measured {} samples for {} predeclared beats",
            cell.id.label(),
            samples.len(),
            cell.beats.len()
        ));
    }
    for (sample, (name, tick)) in samples.iter().zip(&cell.beats) {
        if sample.name != *name || sample.tick != *tick {
            return Err(format!(
                "cell {}: sample at tick {} came from beat `{}`, expected beat `{name}` at tick {tick}",
                cell.id.label(),
                sample.tick,
                sample.name
            ));
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::{AssertionOutcome, CellId, MatrixCell, Sample, evaluate_cell, matrix};

    /// The cell of the matrix by id.
    fn cell(id: CellId) -> MatrixCell {
        matrix()
            .into_iter()
            .find(|cell| cell.id == id)
            .expect("the matrix holds every cell")
    }

    /// A synthetic sample at (tick, frame) with one mean.
    fn s(tick: u64, mean: f64) -> Sample {
        Sample {
            name: format!("t{tick}"),
            tick,
            frame: tick,
            mean_linear: mean,
            mean_linear_r: mean,
            mean_linear_g: mean,
            mean_linear_b: mean,
            mean_raw_r: mean,
            mean_raw_g: mean,
            mean_raw_b: mean,
        }
    }

    /// The step cells' layout with the given means: two pre, five post.
    fn step_sequence(means: [f64; 7]) -> Vec<Sample> {
        let ticks = [10_200, 11_400, 12_601, 13_200, 14_400, 15_600, 18_000];
        ticks
            .iter()
            .zip(means)
            .map(|(tick, mean)| s(*tick, mean))
            .collect()
    }

    /// The move cells' layout with the given means: two center, four edge.
    fn move_sequence(means: [f64; 6]) -> Vec<Sample> {
        let ticks = [10_200, 11_400, 15_000, 17_400, 19_800, 22_200];
        ticks
            .iter()
            .zip(means)
            .map(|(tick, mean)| s(*tick, mean))
            .collect()
    }

    fn by_name(outcomes: &[AssertionOutcome], name: &str) -> AssertionOutcome {
        outcomes
            .iter()
            .find(|outcome| outcome.name == name)
            .unwrap_or_else(|| panic!("assertion `{name}` is evaluated for this cell"))
            .clone()
    }

    #[test]
    fn matrix_has_the_four_cells_with_distinct_seeds() {
        let cells = matrix();
        assert_eq!(
            cells.each_ref().map(|cell| cell.id),
            [CellId::A, CellId::B, CellId::C, CellId::D]
        );
        let mut seeds: Vec<u64> = cells.iter().map(|cell| cell.seed).collect();
        seeds.sort_unstable();
        seeds.dedup();
        assert_eq!(seeds.len(), 4, "run ids stay distinct across cells");
    }

    #[test]
    fn every_cell_scenarios_as_a_calibration_scenario() {
        for cell in matrix() {
            let scenario = cell.scenario();
            assert_eq!(scenario.name, "calibration");
            assert_eq!(scenario.mode, crate::ScenarioMode::Calibration);
            assert_eq!(scenario.calibration, Some(cell.params));
            assert!(scenario.actions.is_empty(), "the lane takes no actions");
            assert_eq!(scenario.beats.len(), cell.beats.len());
            let json = crate::scenario_to_json(&scenario).expect("serializes");
            let parsed = crate::parse_scenario(&json).expect("the cell scenario is valid");
            assert_eq!(parsed, scenario);
        }
    }

    #[test]
    fn cells_a_and_b_share_the_step_timeline_c_and_d_the_move_timeline() {
        let cells = matrix();
        assert_eq!(cells[0].beats, cells[1].beats, "A/B share the beats");
        assert_eq!(cells[2].beats, cells[3].beats, "C/D share the beats");
        assert_eq!(cells[0].params.step.tick, cells[1].params.step.tick);
        assert_eq!(
            cells[2].params.patch.move_tick(),
            cells[3].params.patch.move_tick(),
            "C/D move the patch at the same pinned tick"
        );
    }

    #[test]
    fn cell_a_passes_on_a_converging_sequence() {
        let outcomes = evaluate_cell(
            &cell(CellId::A),
            &step_sequence([0.42, 0.4202, 0.84, 0.7, 0.55, 0.45, 0.4205]),
        );
        assert!(
            outcomes.iter().all(|outcome| outcome.passed),
            "{outcomes:?}"
        );
    }

    #[test]
    fn cell_a_fails_when_exposure_never_adapts() {
        // AE broken: the mean jumps at the step and stays there.
        let outcomes = evaluate_cell(
            &cell(CellId::A),
            &step_sequence([0.42, 0.42, 0.84, 0.84, 0.84, 0.84, 0.84]),
        );
        assert!(
            by_name(&outcomes, "step-moves-mean-up").passed,
            "the jump itself is fine"
        );
        let convergence = by_name(&outcomes, "converges-back");
        assert!(!convergence.passed);
        assert!(
            convergence.expected.contains("0.010"),
            "{}",
            convergence.expected
        );
        assert!(
            convergence.measured.contains("0.840000"),
            "the measured numbers are named: {}",
            convergence.measured
        );
    }

    #[test]
    fn cell_a_fails_when_the_step_moves_the_mean_down() {
        let outcomes = evaluate_cell(
            &cell(CellId::A),
            &step_sequence([0.42, 0.42, 0.2, 0.2, 0.2, 0.2, 0.42]),
        );
        assert!(!by_name(&outcomes, "step-moves-mean-up").passed);
    }

    #[test]
    fn cell_b_passes_on_a_flat_post_step_sequence() {
        let outcomes = evaluate_cell(
            &cell(CellId::B),
            &step_sequence([0.42, 0.42, 0.84, 0.8401, 0.8402, 0.84, 0.8401]),
        );
        assert!(
            outcomes.iter().all(|outcome| outcome.passed),
            "{outcomes:?}"
        );
    }

    #[test]
    fn cell_b_fails_when_the_mean_comes_back() {
        // An AE that adapted despite being off: the mean returns to baseline.
        let outcomes = evaluate_cell(
            &cell(CellId::B),
            &step_sequence([0.42, 0.42, 0.84, 0.7, 0.55, 0.45, 0.42]),
        );
        assert!(!by_name(&outcomes, "no-adaptation").passed);
        assert!(!by_name(&outcomes, "tracks-step").passed);
    }

    #[test]
    fn cell_c_passes_when_the_edge_placement_is_brighter() {
        let outcomes = evaluate_cell(
            &cell(CellId::C),
            &move_sequence([0.43, 0.43, 0.5, 0.51, 0.515, 0.515]),
        );
        assert!(
            outcomes.iter().all(|outcome| outcome.passed),
            "{outcomes:?}"
        );
    }

    #[test]
    fn cell_c_fails_when_the_placement_difference_is_inverted() {
        let outcomes = evaluate_cell(
            &cell(CellId::C),
            &move_sequence([0.43, 0.43, 0.4, 0.39, 0.38, 0.38]),
        );
        assert!(!by_name(&outcomes, "edge-brighter-than-center").passed);
    }

    #[test]
    fn cell_c_fails_when_the_placement_difference_is_missing() {
        let outcomes = evaluate_cell(
            &cell(CellId::C),
            &move_sequence([0.43, 0.43, 0.43, 0.43, 0.43, 0.43]),
        );
        assert!(!by_name(&outcomes, "edge-brighter-than-center").passed);
    }

    #[test]
    fn cell_d_passes_when_the_difference_is_removed() {
        let outcomes = evaluate_cell(
            &cell(CellId::D),
            &move_sequence([0.43, 0.43, 0.43, 0.43, 0.4301, 0.43]),
        );
        assert!(
            outcomes.iter().all(|outcome| outcome.passed),
            "{outcomes:?}"
        );
    }

    #[test]
    fn cell_d_fails_when_the_difference_is_not_removed() {
        let outcomes = evaluate_cell(
            &cell(CellId::D),
            &move_sequence([0.43, 0.43, 0.5, 0.51, 0.515, 0.515]),
        );
        assert!(!by_name(&outcomes, "difference-removed").passed);
    }

    #[test]
    fn cell_d_fails_when_the_edge_window_drifts() {
        let outcomes = evaluate_cell(
            &cell(CellId::D),
            &move_sequence([0.43, 0.43, 0.43, 0.43, 0.43, 0.5]),
        );
        assert!(!by_name(&outcomes, "edge-settled").passed);
    }
}
