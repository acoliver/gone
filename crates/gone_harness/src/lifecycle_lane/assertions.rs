//! The lifecycle lane's predeclared assertions over one finished run's
//! report: the native observations the stage-B spec pins (focus loss clears
//! the held key, reacquisition leaves no input stream, the resize records
//! both extents with the timeline unbroken, the run closes cleanly). Each
//! assertion names what it expects and what the report measured, and both
//! travel into the failure line and the evidence artifact. A live run that
//! contradicts a predeclared assertion is a FINDING, never a reason to edit
//! the assertion: the lane fails naming it.

use serde::Serialize;

use crate::onscreen::ONSCREEN_SIZE;
use crate::report::{Report, TimedEvent};
use crate::{Key, Scenario};

/// The key the lane's scenario holds across the focus loss, in adapter
/// terms: pressed at the first driven tick, never scripted a release — held
/// input the loss must clear (the run's analog of a real device's stuck
/// key).
pub(super) const HELD_KEY: Key = Key::Forward;

/// The held key's spelling in the report's button strings (`Button`'s
/// `Display` form), as the assertions expect it inside `InputCleared.
/// released` and the delivered input stream.
pub(super) const HELD_KEY_LABEL: &str = "Key(Forward)";

/// One predeclared assertion's outcome: expected vs measured, both carried
/// into the failure line and the evidence artifact. The same shape the
/// calibration lane's evidence artifact records.
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct AssertionOutcome {
    /// The assertion's stable name.
    pub name: &'static str,
    /// Whether the run satisfied the assertion.
    pub passed: bool,
    /// What the lane expects.
    pub expected: String,
    /// What the run's report measured.
    pub measured: String,
}

/// Evaluate every predeclared assertion against one finished run's report,
/// in lane order. Total: a report missing the evidence an assertion reads
/// fails that assertion by name instead of erroring the evaluation.
pub(super) fn evaluate_lifecycle(scenario: &Scenario, report: &Report) -> Vec<AssertionOutcome> {
    vec![
        focus_loss_observed(report),
        held_input_cleared_at_the_loss(report),
        held_key_releases_exactly_once(report),
        reacquisition_observed(report),
        no_input_after_reacquisition(report),
        resize_recorded(scenario, report),
        timeline_keeps_running(report),
        clean_close(report),
    ]
}

/// Verify one finished lifecycle run's report against the predeclared
/// assertions: `Ok` when every assertion held, otherwise a message naming
/// the first contradicted assertion with its expected-vs-measured numbers.
///
/// # Errors
/// The first failed assertion's verdict line.
pub fn verify_lifecycle(scenario: &Scenario, report: &Report) -> Result<(), String> {
    evaluate_lifecycle(scenario, report)
        .into_iter()
        .find(|outcome| !outcome.passed)
        .map_or(Ok(()), |outcome| {
            Err(format!(
                "lifecycle assertion `{}` failed: expected {}; measured {}",
                outcome.name, outcome.expected, outcome.measured
            ))
        })
}

/// The run observed a real focus loss: the OS resigned the window's key
/// status and the app recorded the native observation after the readiness
/// boundary (the window's creation transitions are never recorded).
fn focus_loss_observed(report: &Report) -> AssertionOutcome {
    let (passed, measured) = match first_loss(report) {
        Some((_, tick)) => (true, format!("first loss observed at tick {tick}")),
        None => (
            false,
            "no focused=false observation in the report".to_owned(),
        ),
    };
    AssertionOutcome {
        name: "focus-loss-observed",
        passed,
        expected: "at least one native WindowFocus observation with focused=false, \
                   recorded after the readiness boundary"
            .to_owned(),
        measured,
    }
}

/// The input layer cleared at the focus-loss boundary: exactly one
/// `InputCleared` at the first loss's tick, releasing the held key and
/// dropping no buffered edges (the scenario leaves nothing buffered).
fn held_input_cleared_at_the_loss(report: &Report) -> AssertionOutcome {
    let expected = format!(
        "exactly one InputCleared at the first loss tick, releasing \
         [\"{HELD_KEY_LABEL}\"] and dropping no buffered edges"
    );
    let Some((_, loss_tick)) = first_loss(report) else {
        return AssertionOutcome {
            name: "held-input-cleared-at-the-loss",
            passed: false,
            expected,
            measured: "no focus loss observed (the clear triggers on it)".to_owned(),
        };
    };
    let (passed, measured) = match clear_events(report).as_slice() {
        [(tick, dropped, released)]
            if *tick == loss_tick
                && *dropped == 0
                && released.len() == 1
                && released[0] == HELD_KEY_LABEL =>
        {
            (
                true,
                format!("cleared at tick {tick}, released {released:?}, dropped {dropped} edges"),
            )
        }
        [(tick, dropped, released)] => (
            false,
            format!(
                "one clear at tick {tick} (loss tick {loss_tick}), released {released:?}, \
                 dropped {dropped} edges"
            ),
        ),
        [] => (false, "no InputCleared event in the report".to_owned()),
        many => (
            false,
            format!("{} InputCleared events, expected exactly one", many.len()),
        ),
    };
    AssertionOutcome {
        name: "held-input-cleared-at-the-loss",
        passed,
        expected,
        measured,
    }
}

/// The held key's synthetic release delivered exactly once through the
/// ordinary input stream after the clear, and nothing pressed the key
/// again: the release stream is the observable form of the stuck key going
/// up at the boundary.
fn held_key_releases_exactly_once(report: &Report) -> AssertionOutcome {
    let expected = format!(
        "exactly one `{HELD_KEY_LABEL} release` input after the clear and no \
         later `{HELD_KEY_LABEL} press` (the synthetic release delivers exactly once)"
    );
    let Some((_, loss_tick)) = first_loss(report) else {
        return AssertionOutcome {
            name: "held-key-releases-exactly-once",
            passed: false,
            expected,
            measured: "no focus loss observed (the release follows the clear)".to_owned(),
        };
    };
    let release_word = format!("{HELD_KEY_LABEL} release");
    let press_word = format!("{HELD_KEY_LABEL} press");
    let after = |what: &str| {
        input_events(report)
            .into_iter()
            .filter(|(tick, event)| *tick > loss_tick && *event == what)
            .map(|(tick, _)| tick)
            .collect::<Vec<u64>>()
    };
    let releases = after(&release_word);
    let presses = after(&press_word);
    let (passed, measured) = match releases.as_slice() {
        [tick] if presses.is_empty() => {
            (true, format!("one release at tick {tick}, no later press"))
        }
        [tick] => (
            false,
            format!(
                "one release at tick {tick} but {} later presses",
                presses.len()
            ),
        ),
        [] => (false, "no release delivered after the clear".to_owned()),
        ticks => (
            false,
            format!("{} releases at ticks {ticks:?}", ticks.len()),
        ),
    };
    AssertionOutcome {
        name: "held-key-releases-exactly-once",
        passed,
        expected,
        measured,
    }
}

/// The run observed the reacquisition: the OS made the window key again and
/// the app recorded the native focused=true observation after the loss.
fn reacquisition_observed(report: &Report) -> AssertionOutcome {
    let observed = first_loss(report).and_then(|(index, _)| reacquisition_after(report, index));
    let (passed, measured) = match observed {
        Some(tick) => (true, format!("reacquired at tick {tick}")),
        None => (
            false,
            "no focused=true observation after the loss in the report".to_owned(),
        ),
    };
    AssertionOutcome {
        name: "reacquisition-observed",
        passed,
        expected: "a native WindowFocus observation with focused=true, recorded after \
                   the focus loss"
            .to_owned(),
        measured,
    }
}

/// Nothing was stuck after the reacquisition: no input event of any kind
/// (edge, look motion, movement) carries a tick past the reacquisition's.
/// A stuck motion or mouse jump can only reach the report through this
/// stream, so an empty stream after the reacquisition is the lane's whole
/// claim.
fn no_input_after_reacquisition(report: &Report) -> AssertionOutcome {
    let expected = "no input events after the reacquisition observation: no stuck \
                    motion, no mouse jump, no re-delivered edges"
        .to_owned();
    let reacquire = first_loss(report).and_then(|(index, _)| reacquisition_after(report, index));
    let Some(reacquire_tick) = reacquire else {
        return AssertionOutcome {
            name: "no-input-after-reacquisition",
            passed: false,
            expected,
            measured: "no reacquisition observed (the quiet window follows it)".to_owned(),
        };
    };
    let stray: Vec<(u64, &str)> = input_events(report)
        .into_iter()
        .filter(|(tick, _)| *tick > reacquire_tick)
        .collect();
    let (passed, measured) = if stray.is_empty() {
        (
            true,
            format!("no input after the reacquisition at tick {reacquire_tick}"),
        )
    } else {
        (
            false,
            format!(
                "{} input events after the reacquisition at tick {reacquire_tick}: {stray:?}",
                stray.len()
            ),
        )
    };
    AssertionOutcome {
        name: "no-input-after-reacquisition",
        passed,
        expected,
        measured,
    }
}

/// The resize was observed natively with both extents recorded: the window
/// at the scenario's new physical size (logical matches at the lane's
/// forced scale factor of 1.0) and the capture target unchanged at the
/// lane's fixed extent.
fn resize_recorded(scenario: &Scenario, report: &Report) -> AssertionOutcome {
    let (capture_width, capture_height) = ONSCREEN_SIZE;
    let Some(params) = scenario.lifecycle.as_ref() else {
        return AssertionOutcome {
            name: "resize-recorded",
            passed: false,
            expected: "the scenario carries a lifecycle section".to_owned(),
            measured: "the scenario has no lifecycle section (authoring error)".to_owned(),
        };
    };
    let (width, height) = (params.resize.width, params.resize.height);
    let expected = format!(
        "a native WindowResized observation of {width}x{height} with the capture target \
         unchanged at {capture_width}x{capture_height} (physical and capture dims recorded)"
    );
    let observed = resize_observations(report);
    let matching = observed.iter().find(|observation| {
        resize_names_drive(observation, width, height, capture_width, capture_height)
    });
    let (passed, measured) = match matching {
        Some(&(tick, ..)) => (
            true,
            format!(
                "resized at tick {tick}: {width}x{height}, capture {capture_width}x{capture_height}"
            ),
        ),
        None if observed.is_empty() => (
            false,
            "no WindowResized observation in the report".to_owned(),
        ),
        None => (
            false,
            format!(
                "{} resize observations, none at {width}x{height} with capture \
                 {capture_width}x{capture_height}: {observed:?}",
                observed.len()
            ),
        ),
    };
    AssertionOutcome {
        name: "resize-recorded",
        passed,
        expected,
        measured,
    }
}

/// The report's resize observations as (tick, width, height, capture width,
/// capture height) tuples, in recorded order.
fn resize_observations(report: &Report) -> Vec<(u64, f32, f32, u32, u32)> {
    report
        .events
        .iter()
        .filter_map(|event| match event {
            TimedEvent::WindowResized {
                tick,
                width,
                height,
                capture_width,
                capture_height,
                ..
            } => Some((*tick, *width, *height, *capture_width, *capture_height)),
            _ => None,
        })
        .collect()
}

/// True when one resize observation names the scenario's driven extent with
/// the capture target unchanged. The extents compare through a margin far
/// above the conversion rounding (zero at these magnitudes: the recorded
/// width is the scenario's integer extent rendered at the lane's scale
/// factor of 1.0) and far below any real extent difference (1 pixel).
fn resize_names_drive(
    (_, event_width, event_height, event_capture_width, event_capture_height): &(
        u64,
        f32,
        f32,
        u32,
        u32,
    ),
    width: u32,
    height: u32,
    capture_width: u32,
    capture_height: u32,
) -> bool {
    const EXTENT_EPSILON: f64 = 1e-3;
    let extent_matches = |recorded: f32, driven: u32| {
        (f64::from(recorded) - f64::from(driven)).abs() < EXTENT_EPSILON
    };
    extent_matches(*event_width, width)
        && extent_matches(*event_height, height)
        && *event_capture_width == capture_width
        && *event_capture_height == capture_height
}

/// The phase timeline never restarted: the observation ticks strictly
/// increase across loss, reacquisition, and resize, and the beat manifest
/// still pins captures past the resize — a run whose clock reset at any
/// drive would put a later observation at an earlier tick and fail here.
fn timeline_keeps_running(report: &Report) -> AssertionOutcome {
    let expected = "observation ticks strictly increase (loss < reacquire < resize) and \
                    the beat manifest still pins past the resize: the phase timeline \
                    never restarted"
        .to_owned();
    let measured = match (first_loss(report), first_resize_tick(report)) {
        (Some((loss_index, loss_tick)), Some(resize_tick)) => {
            match reacquisition_after(report, loss_index) {
                Some(reacquire_tick)
                    if loss_tick < reacquire_tick && reacquire_tick < resize_tick =>
                {
                    let last_beat_tick = report
                        .beats
                        .values()
                        .map(|entry| entry.tick)
                        .max()
                        .unwrap_or_default();
                    if last_beat_tick > resize_tick {
                        return AssertionOutcome {
                            name: "timeline-keeps-running",
                            passed: true,
                            expected,
                            measured: format!(
                                "loss {loss_tick} < reacquire {reacquire_tick} < resize \
                                 {resize_tick}; last pinned beat tick {last_beat_tick}"
                            ),
                        };
                    }
                    format!(
                        "loss {loss_tick} < reacquire {reacquire_tick} < resize {resize_tick}, \
                         but the last pinned beat tick is {last_beat_tick} (must pin past the \
                         resize)"
                    )
                }
                Some(reacquire_tick) => format!(
                    "ticks did not strictly increase: loss {loss_tick}, reacquire \
                     {reacquire_tick}, resize {resize_tick}"
                ),
                None => "no reacquisition observed".to_owned(),
            }
        }
        (Some(_), None) => "no resize observation".to_owned(),
        (None, _) => "no focus loss observed".to_owned(),
    };
    AssertionOutcome {
        name: "timeline-keeps-running",
        passed: false,
        expected,
        measured,
    }
}

/// The run closed cleanly: the report records exactly one `Complete` and no
/// `Failure`. The child's exit code 0 is the runner's own status check in
/// `run_scenario`, asserted beside this; a report that ends in `Failure`
/// fails the lane by name even when the child exits.
fn clean_close(report: &Report) -> AssertionOutcome {
    let completes = report
        .events
        .iter()
        .filter(|event| matches!(event, TimedEvent::Complete { .. }))
        .count();
    let failures = report
        .events
        .iter()
        .filter(|event| matches!(event, TimedEvent::Failure { .. }))
        .count();
    let (passed, measured) = if completes == 1 && failures == 0 {
        (true, "one Complete event, no Failure events".to_owned())
    } else {
        (
            false,
            format!("{completes} Complete events, {failures} Failure events"),
        )
    };
    AssertionOutcome {
        name: "clean-close",
        passed,
        expected: "the report records exactly one Complete and no Failure (the child \
                   also exited 0; the runner asserts the status beside this)"
            .to_owned(),
        measured,
    }
}

/// (event position, tick, focused) over the report's native focus
/// observations, in recorded order. The position orders the loss before the
/// reacquisition regardless of which ticks they stamped.
fn focus_observations(report: &Report) -> Vec<(usize, u64, bool)> {
    report
        .events
        .iter()
        .enumerate()
        .filter_map(|(index, event)| match event {
            TimedEvent::WindowFocus { tick, focused, .. } => Some((index, *tick, *focused)),
            _ => None,
        })
        .collect()
}

/// The first recorded focus loss: its event position and tick.
fn first_loss(report: &Report) -> Option<(usize, u64)> {
    focus_observations(report)
        .into_iter()
        .find(|&(_, _, focused)| !focused)
        .map(|(index, tick, _)| (index, tick))
}

/// The first reacquisition recorded after the loss at event position
/// `loss_index`.
fn reacquisition_after(report: &Report, loss_index: usize) -> Option<u64> {
    focus_observations(report)
        .into_iter()
        .find(|&(index, _, focused)| index > loss_index && focused)
        .map(|(_, tick, _)| tick)
}

/// The first resize observation's tick, if any.
fn first_resize_tick(report: &Report) -> Option<u64> {
    report.events.iter().find_map(|event| match event {
        TimedEvent::WindowResized { tick, .. } => Some(*tick),
        _ => None,
    })
}

/// The report's input-delivery events as (tick, what) pairs.
fn input_events(report: &Report) -> Vec<(u64, &str)> {
    report
        .events
        .iter()
        .filter_map(|event| match event {
            TimedEvent::Input { tick, what, .. } => Some((*tick, what.as_str())),
            _ => None,
        })
        .collect()
}

/// The report's `InputCleared` events as (tick, dropped edges, released
/// buttons) triples.
fn clear_events(report: &Report) -> Vec<(u64, usize, &[String])> {
    report
        .events
        .iter()
        .filter_map(|event| match event {
            TimedEvent::InputCleared {
                tick,
                dropped_edges,
                released,
                ..
            } => Some((*tick, *dropped_edges, released.as_slice())),
            _ => None,
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use std::collections::BTreeMap;

    use crate::report::{BeatEntry, Identity, Report, TimedEvent};
    use crate::{LifecycleParams, LifecycleResize, LifecycleStep, PROTOCOL_VERSION, Scenario};

    use super::{HELD_KEY, HELD_KEY_LABEL, evaluate_lifecycle, verify_lifecycle};

    /// The drive pins the synthetic reports below are built around (the
    /// lane scenario's own drives; the builder test in the lane module
    /// pins the scenario to them).
    fn drives() -> LifecycleParams {
        LifecycleParams {
            focus_loss: LifecycleStep { at_tick: 40 },
            reacquire: LifecycleStep { at_tick: 90 },
            resize: LifecycleResize {
                at_tick: 140,
                width: 1280,
                height: 720,
            },
        }
    }

    /// The lane scenario shape the assertions expect: lifecycle mode, the
    /// drives above, the manifest pins below.
    fn scenario() -> Scenario {
        Scenario {
            name: "lifecycle".to_owned(),
            seed: 3407,
            mode: crate::ScenarioMode::Lifecycle,
            lifecycle: Some(drives()),
            ..Scenario::default()
        }
    }

    /// The beat manifest the good report carries: pins spanning the drives,
    /// the last past the resize.
    const BEAT_TICKS: [(&str, u64); 4] = [
        ("held", 20),
        ("cleared", 60),
        ("refocused", 110),
        ("resized", 160),
    ];

    /// The input event delivered at `tick` for `what` (the frame matches
    /// the tick, as the drive's stamps do).
    fn input(tick: u64, what: &str) -> TimedEvent {
        TimedEvent::Input {
            tick,
            frame: tick,
            what: what.to_owned(),
        }
    }

    /// The native focus observation at `tick`.
    fn focus(tick: u64, focused: bool) -> TimedEvent {
        TimedEvent::WindowFocus {
            tick,
            frame: tick,
            focused,
        }
    }

    /// The input layer's clear at the loss tick: nothing dropped, the held
    /// key released.
    fn cleared(tick: u64) -> TimedEvent {
        TimedEvent::InputCleared {
            tick,
            frame: tick,
            dropped_edges: 0,
            released: vec![HELD_KEY_LABEL.to_owned()],
        }
    }

    /// The native resize observation at `tick`: the scenario's extent, the
    /// capture target unchanged.
    fn resized(tick: u64) -> TimedEvent {
        TimedEvent::WindowResized {
            tick,
            frame: tick,
            width: 1280.0,
            height: 720.0,
            capture_width: 1920,
            capture_height: 1080,
        }
    }

    /// The beat manifest the good report carries: pins spanning the drives.
    fn beat_manifest() -> BTreeMap<String, BeatEntry> {
        BEAT_TICKS
            .iter()
            .enumerate()
            .map(|(index, (name, tick))| {
                (
                    (*name).to_owned(),
                    BeatEntry {
                        file: format!("beats/{name}.png"),
                        tick: *tick,
                        frame: *tick,
                        request_id: index as u64 + 1,
                    },
                )
            })
            .collect()
    }

    /// A report carrying every observation a correct run records, in the
    /// order a correct run records them: ready, the held press, the look,
    /// the loss and clear, the synthetic release, the reacquisition, the
    /// resize (capture target unchanged), the manifest, and the close.
    fn good_report() -> Report {
        let mut report = Report::new(
            PROTOCOL_VERSION,
            "lifecycle",
            3407,
            Identity {
                app_hash: "a".to_owned(),
                scenario_hash: "s".to_owned(),
                config_hash: "c".to_owned(),
            },
        );
        report.beats = beat_manifest();
        report.events = vec![
            TimedEvent::Ready { frame: 0 },
            input(0, &format!("{HELD_KEY_LABEL} press")),
            input(10, "look 3 0"),
            focus(43, false),
            cleared(43),
            input(44, &format!("{HELD_KEY_LABEL} release")),
            focus(92, true),
            resized(141),
            TimedEvent::Complete { frame: 162 },
        ];
        report
    }

    /// One assertion's outcome by name.
    fn by_name<'a>(
        outcomes: &'a [super::AssertionOutcome],
        name: &str,
    ) -> &'a super::AssertionOutcome {
        outcomes
            .iter()
            .find(|outcome| outcome.name == name)
            .unwrap_or_else(|| panic!("assertion `{name}` is evaluated"))
    }

    #[test]
    fn the_held_key_label_is_the_buttons_display_form() {
        assert_eq!(
            crate::Button::Key(HELD_KEY).to_string(),
            HELD_KEY_LABEL,
            "the label constant must track the report's button spelling"
        );
    }

    #[test]
    fn a_correct_run_satisfies_every_assertion() {
        let report = good_report();
        let outcomes = evaluate_lifecycle(&scenario(), &report);
        let failed: Vec<&super::AssertionOutcome> =
            outcomes.iter().filter(|outcome| !outcome.passed).collect();
        assert!(
            failed.is_empty(),
            "every assertion must hold on the good report: {failed:?}"
        );
        assert!(verify_lifecycle(&scenario(), &report).is_ok());
    }

    #[test]
    fn a_report_without_the_loss_fails_the_focus_assertions() {
        let mut report = good_report();
        report
            .events
            .retain(|event| !matches!(event, TimedEvent::WindowFocus { .. }));
        let outcomes = evaluate_lifecycle(&scenario(), &report);
        for name in [
            "focus-loss-observed",
            "held-input-cleared-at-the-loss",
            "held-key-releases-exactly-once",
            "reacquisition-observed",
            "no-input-after-reacquisition",
            "timeline-keeps-running",
        ] {
            assert!(!by_name(&outcomes, name).passed, "{name} must fail");
        }
    }

    #[test]
    fn a_clear_that_releases_the_wrong_buttons_fails() {
        let mut report = good_report();
        for event in &mut report.events {
            if let TimedEvent::InputCleared { released, .. } = event {
                *released = vec!["Key(Activate)".to_owned()];
            }
        }
        let outcomes = evaluate_lifecycle(&scenario(), &report);
        let outcome = by_name(&outcomes, "held-input-cleared-at-the-loss");
        assert!(!outcome.passed, "{outcome:?}");
        assert!(outcome.measured.contains("Key(Activate)"), "{outcome:?}");
    }

    #[test]
    fn a_clear_at_the_wrong_tick_fails() {
        let mut report = good_report();
        for event in &mut report.events {
            if let TimedEvent::InputCleared { tick, .. } = event {
                *tick = 44;
            }
        }
        assert!(
            !by_name(
                &evaluate_lifecycle(&scenario(), &report),
                "held-input-cleared-at-the-loss"
            )
            .passed
        );
    }

    #[test]
    fn a_repeated_release_fails() {
        let mut report = good_report();
        report.events.push(TimedEvent::Input {
            tick: 50,
            frame: 50,
            what: format!("{HELD_KEY_LABEL} release"),
        });
        let outcomes = evaluate_lifecycle(&scenario(), &report);
        let outcome = by_name(&outcomes, "held-key-releases-exactly-once");
        assert!(!outcome.passed, "{outcome:?}");
        assert!(outcome.measured.contains("2 releases"), "{outcome:?}");
    }

    #[test]
    fn an_input_after_the_reacquisition_fails() {
        // A re-delivered edge after the reacquisition is the stuck-input
        // shape (a stuck motion or a mouse jump arrives the same way): the
        // quiet-window assertion must reject it.
        let mut report = good_report();
        report.events.push(TimedEvent::Input {
            tick: 100,
            frame: 100,
            what: "look 5 0".to_owned(),
        });
        let outcomes = evaluate_lifecycle(&scenario(), &report);
        let outcome = by_name(&outcomes, "no-input-after-reacquisition");
        assert!(!outcome.passed, "{outcome:?}");
        assert!(outcome.measured.contains("look 5 0"), "{outcome:?}");
    }

    #[test]
    fn a_resize_at_the_wrong_extent_fails_naming_both() {
        let mut report = good_report();
        for event in &mut report.events {
            if let TimedEvent::WindowResized { width, height, .. } = event {
                *width = 800.0;
                *height = 600.0;
            }
        }
        let outcomes = evaluate_lifecycle(&scenario(), &report);
        let outcome = by_name(&outcomes, "resize-recorded");
        assert!(!outcome.passed, "{outcome:?}");
        assert!(outcome.measured.contains("1280x720"), "{outcome:?}");
    }

    #[test]
    fn a_resize_that_moved_the_capture_target_fails() {
        let mut report = good_report();
        for event in &mut report.events {
            if let TimedEvent::WindowResized {
                capture_width,
                capture_height,
                ..
            } = event
            {
                *capture_width = 1280;
                *capture_height = 720;
            }
        }
        assert!(!by_name(&evaluate_lifecycle(&scenario(), &report), "resize-recorded").passed);
    }

    #[test]
    fn a_reset_clock_fails_the_timeline_assertion() {
        // The failure shape a run produces when the phase timeline restarts
        // at the resize: the later observation lands at an earlier tick.
        let mut report = good_report();
        for event in &mut report.events {
            if let TimedEvent::WindowResized { tick, .. } = event {
                *tick = 10;
            }
        }
        let outcomes = evaluate_lifecycle(&scenario(), &report);
        let outcome = by_name(&outcomes, "timeline-keeps-running");
        assert!(!outcome.passed, "{outcome:?}");
        assert!(
            outcome.measured.contains("did not strictly increase"),
            "{outcome:?}"
        );
    }

    #[test]
    fn beats_pinned_only_before_the_resize_fail_the_timeline_assertion() {
        let mut report = good_report();
        report.beats.retain(|_, entry| entry.tick <= 141);
        let outcomes = evaluate_lifecycle(&scenario(), &report);
        let outcome = by_name(&outcomes, "timeline-keeps-running");
        assert!(!outcome.passed, "{outcome:?}");
    }

    #[test]
    fn a_failure_event_fails_the_close_assertion() {
        let mut report = good_report();
        report.events.push(TimedEvent::Failure {
            frame: 163,
            what: "beat `resized` capture save failed".to_owned(),
        });
        let outcomes = evaluate_lifecycle(&scenario(), &report);
        assert!(!by_name(&outcomes, "clean-close").passed);
    }

    #[test]
    fn a_report_without_a_complete_fails_the_close_assertion() {
        let mut report = good_report();
        report
            .events
            .retain(|event| !matches!(event, TimedEvent::Complete { .. }));
        assert!(!by_name(&evaluate_lifecycle(&scenario(), &report), "clean-close").passed);
    }

    #[test]
    fn verify_names_the_first_failed_assertion_with_both_numbers() {
        let mut report = good_report();
        report
            .events
            .retain(|event| !matches!(event, TimedEvent::InputCleared { .. }));
        let err = verify_lifecycle(&scenario(), &report).expect_err("must fail");
        assert!(err.contains("held-input-cleared-at-the-loss"), "{err}");
        assert!(err.contains("expected"), "{err}");
        assert!(err.contains("measured"), "{err}");
    }
}
