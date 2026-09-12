//! The compare lane: run one scenario twice and diff the event timelines.

use std::path::Path;

use gone_harness::report;

use crate::error::RunnerError;
use crate::paths::{load_scenario, read_or, repo_root, root_scenario};
use crate::run::run_scenario;

pub(crate) fn run_compare(args: &[String], render_check: bool) -> i32 {
    match compare_impl(args, render_check) {
        Ok(code) => code,
        Err(e) => {
            eprintln!("{e}");
            1
        }
    }
}

fn compare_impl(args: &[String], render_check: bool) -> Result<i32, RunnerError> {
    let path_arg = args.get(2).map_or("smoke", String::as_str);
    let scenario_path = root_scenario(path_arg)?;
    let scenario = load_scenario(&scenario_path)?;
    let root = repo_root()?;
    let out_root = root.join("tmp").join("harness");
    let run_a = run_scenario(&root, &scenario_path, &scenario, &out_root, render_check)?;
    let run_b = run_scenario(&root, &scenario_path, &scenario, &out_root, render_check)?;
    let (a, b) = (compare_stream(&run_a)?, compare_stream(&run_b)?);
    if a == b {
        println!("COMPARE PASS: two runs identical ({} events)", a.len());
        Ok(0)
    } else {
        let first = a.iter().zip(&b).position(|(x, y)| x != y).unwrap_or(0);
        println!("COMPARE DIVERGENCE at event {first}: {a:?} vs {b:?}");
        Ok(1)
    }
}

/// One run's compare stream: its report's events, reduced to comparable
/// lines. Fails when the report is missing or unparsable: a compare verdict
/// is a claim about two real runs, and an unreadable report is a failed run,
/// never an empty stream that would compare as "identical".
fn compare_stream(run: &Path) -> Result<Vec<String>, RunnerError> {
    let report_bytes = read_or("report", &run.join("report.json"))?;
    let parsed = report::parse_report(&String::from_utf8_lossy(&report_bytes))
        .map_err(|e| RunnerError(format!("report parse: {e}")))?;
    Ok(parsed.events.iter().map(compare_event_line).collect())
}

/// One event's compare line. The terminal `Complete` frame is normalized
/// away: under the scenario clock's capture freeze the completion frame is
/// itself deterministic, so the normalization is redundant today, and it
/// keeps the line shape stable. Every tick-scoped event (inputs, beats with
/// their pinned tick/frame) compares exactly.
fn compare_event_line(event: &report::TimedEvent) -> String {
    match event {
        report::TimedEvent::Complete { .. } => "Complete".to_owned(),
        other => format!("{other:?}"),
    }
}

#[cfg(test)]
mod tests {
    use super::compare_stream;
    use std::path::PathBuf;

    /// A scratch run directory unique to this test process (the runner's run
    /// dirs are `tmp/harness`, but a unit test needs no repo side effects).
    fn scratch_run_dir(label: &str) -> PathBuf {
        let dir = std::env::temp_dir().join(format!("gone-compare-{}-{label}", std::process::id()));
        std::fs::create_dir_all(&dir).expect("create scratch run dir");
        dir
    }

    /// A compare over a run whose report is missing must fail, not pass:
    /// the old closure `unwrap_or_default()`ed both read failures into empty
    /// streams, so two missing reports compared as "COMPARE PASS: 0 events".
    #[test]
    fn compare_stream_fails_when_the_report_is_missing() {
        let run_dir = scratch_run_dir("missing");
        let err = compare_stream(&run_dir).expect_err("missing report must fail");
        assert!(
            err.to_string().contains("failed to read report"),
            "the error names the unreadable artifact: {err}"
        );
        std::fs::remove_dir(&run_dir).expect("clean up scratch run dir");
    }

    /// A compare over a run with an unparsable report must fail with the
    /// parse error, never produce an empty stream.
    #[test]
    fn compare_stream_fails_when_the_report_is_corrupt() {
        let run_dir = scratch_run_dir("corrupt");
        let path = run_dir.join("report.json");
        std::fs::write(&path, "{ not a report").expect("write corrupt report");
        let err = compare_stream(&run_dir).expect_err("corrupt report must fail");
        assert!(
            err.to_string().contains("report parse"),
            "the error carries the parse failure: {err}"
        );
        std::fs::remove_file(&path).expect("remove corrupt report");
        std::fs::remove_dir(&run_dir).expect("clean up scratch run dir");
    }

    #[test]
    fn compare_normalizes_only_the_terminal_complete_frame() {
        // The completion frame is deterministic under the capture freeze, so
        // the normalization is redundant today and kept for line-shape
        // stability; every tick-scoped event keeps its exact Debug form.
        use gone_harness::report::TimedEvent;
        let events = [
            TimedEvent::Ready { frame: 0 },
            TimedEvent::Beat {
                name: "beat-a".to_owned(),
                tick: 2,
                frame: 2,
                request_id: 1,
            },
            TimedEvent::Complete { frame: 14 },
        ];
        let lines: Vec<String> = events.iter().map(super::compare_event_line).collect();
        assert_eq!(lines[0], "Ready { frame: 0 }");
        assert_eq!(
            lines[1],
            r#"Beat { name: "beat-a", tick: 2, frame: 2, request_id: 1 }"#
        );
        assert_eq!(
            lines[2], "Complete",
            "the terminal frame must normalize away"
        );
    }
}
