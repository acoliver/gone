//! Setup-evidence handling: extract the run's recorded `Calibration` event,
//! cross-check it against the cell's predeclared parameters, and write the
//! `calibration-evidence.json` artifact.

use std::path::{Path, PathBuf};

use serde::Serialize;

use crate::calibration::{AutoExposureEvidence, CalibrationEvidence};
use crate::patch_placements;
use crate::report::{Report, TimedEvent};

use super::assertions::AssertionOutcome;
use super::matrix::MatrixCell;
use super::measurement::Sample;

/// Extract the run's single Calibration evidence event.
///
/// # Errors
/// When the report carries none or more than one (each is a protocol
/// violation on this lane: exactly one is recorded before any sample).
pub(super) fn extract_evidence(
    report: &Report,
    cell_id: super::CellId,
) -> Result<&CalibrationEvidence, String> {
    let mut found = report.events.iter().filter_map(|event| match event {
        TimedEvent::Calibration { evidence, .. } => Some(evidence),
        _ => None,
    });
    let Some(evidence) = found.next() else {
        return Err(format!(
            "cell {}: report has no Calibration event; the app did not record the setup evidence",
            cell_id.label()
        ));
    };
    if found.next().is_some() {
        return Err(format!(
            "cell {}: report carries more than one Calibration event (exactly one is recorded)",
            cell_id.label()
        ));
    }
    Ok(evidence)
}

/// Cross-check the recorded evidence against the cell's predeclared
/// parameters: the app must report the setup the scenario declared, and the
/// pinned sample ticks must be the scenario's beats.
///
/// # Errors
/// A named mismatch (mask, AE arm, levels, step, area, plan, sample ticks,
/// or a malformed mask hash).
pub(super) fn crosscheck_evidence(
    evidence: &CalibrationEvidence,
    cell: &MatrixCell,
) -> Result<(), String> {
    let params = &cell.params;
    let label = cell.id.label();
    if evidence.mask_sha256.len() != 64 {
        return Err(format!(
            "cell {label}: evidence mask_sha256 is not a sha256 hex string ({} chars)",
            evidence.mask_sha256.len()
        ));
    }
    if evidence.mask != params.mask {
        return Err(format!(
            "cell {label}: evidence mask {:?} differs from the scenario's {:?}",
            evidence.mask, params.mask
        ));
    }
    if evidence.auto_exposure.enabled != params.auto_exposure {
        return Err(format!(
            "cell {label}: evidence auto exposure enabled={} differs from the scenario's {}",
            evidence.auto_exposure.enabled, params.auto_exposure
        ));
    }
    let close = |a: f32, b: f32| (a - b).abs() < 1e-4;
    if !close(evidence.initial_level, params.initial_level) {
        return Err(format!(
            "cell {label}: evidence initial_level {} differs from the scenario's {}",
            evidence.initial_level, params.initial_level
        ));
    }
    if evidence.step_tick != params.step.tick || !close(evidence.step_level, params.step.level) {
        return Err(format!(
            "cell {label}: evidence step ({}, {}) differs from the scenario's ({}, {})",
            evidence.step_tick, evidence.step_level, params.step.tick, params.step.level
        ));
    }
    if !close(evidence.patch_area_fraction, params.patch_area_fraction) {
        return Err(format!(
            "cell {label}: evidence patch area {} differs from the scenario's {}",
            evidence.patch_area_fraction, params.patch_area_fraction
        ));
    }
    if evidence.patch_placements != patch_placements(params.patch) {
        return Err(format!(
            "cell {label}: evidence patch placements differ from the scenario's plan {:?}",
            params.patch
        ));
    }
    let mut expected_ticks: Vec<u64> = cell.beats.iter().map(|(_, tick)| *tick).collect();
    expected_ticks.sort_unstable();
    if evidence.sample_ticks != expected_ticks {
        return Err(format!(
            "cell {label}: evidence sample_ticks {:?} differ from the scenario's beat ticks {expected_ticks:?}",
            evidence.sample_ticks
        ));
    }
    Ok(())
}

/// The evidence artifact: the run's identity, the recorded setup evidence
/// (mask sha256 and AE settings included), the full measured sequence, every
/// assertion's expected/measured outcome, and the overall verdict.
#[derive(Debug, Serialize)]
struct EvidenceArtifact<'a> {
    lane: &'static str,
    run_id: &'a str,
    cell: &'static str,
    cell_description: &'static str,
    mask_sha256: &'a str,
    auto_exposure: &'a AutoExposureEvidence,
    evidence: &'a CalibrationEvidence,
    samples: &'a [Sample],
    assertions: &'a [AssertionOutcome],
    passed: bool,
}

/// Everything the evidence artifact records about one judged run.
pub(super) struct RunEvidence<'a> {
    /// The run id this artifact belongs to.
    pub(super) run_id: &'a str,
    /// The judged matrix cell.
    pub(super) cell: &'a MatrixCell,
    /// The report's recorded setup evidence.
    pub(super) evidence: &'a CalibrationEvidence,
    /// The measured sequence.
    pub(super) samples: &'a [Sample],
    /// The assertion outcomes.
    pub(super) assertions: &'a [AssertionOutcome],
    /// Whether every assertion held.
    pub(super) passed: bool,
}

/// Write the evidence artifact into the run dir.
///
/// # Errors
/// A named error when serialization or the file write fails.
pub(super) fn write_artifact(run_dir: &Path, run: &RunEvidence<'_>) -> Result<PathBuf, String> {
    let artifact = EvidenceArtifact {
        lane: "calibration-matrix-v1",
        run_id: run.run_id,
        cell: run.cell.id.label(),
        cell_description: run.cell.id.description(),
        mask_sha256: &run.evidence.mask_sha256,
        auto_exposure: &run.evidence.auto_exposure,
        evidence: run.evidence,
        samples: run.samples,
        assertions: run.assertions,
        passed: run.passed,
    };
    let text = serde_json::to_string_pretty(&artifact).map_err(|e| {
        format!(
            "evidence artifact serialize (cell {}): {e}",
            run.cell.id.label()
        )
    })?;
    let path = run_dir.join("calibration-evidence.json");
    std::fs::write(&path, text.as_bytes())
        .map_err(|e| format!("failed to write {}: {e}", path.display()))?;
    Ok(path)
}
