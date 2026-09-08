//! Run report schema for the harness (issue #5 / slice A).
//!
//! The app writes one `report.json` per run. It carries tick-stamped events,
//! phase checkpoints, frame-time statistics, and the beat manifest: beat name ->
//! PNG file, tick, rendered frame, request id. Run identity is content hashes
//! (sha2) of the app binary, the scenario file, and the harness config, so a stale
//! binary or edited scenario cannot masquerade as the tested build.

use std::collections::BTreeMap;

/// One timestamped event on the timeline.
#[derive(Clone, Debug, PartialEq, serde::Serialize, serde::Deserialize)]
#[serde(tag = "kind", content = "at")]
pub enum TimedEvent {
    /// The renderer has presented a frame (the app's first primary-window
    /// screenshot landed); this is the tick-zero boundary: no scenario tick ran
    /// and no input was consumed before it.
    Ready {
        /// Rendered frame number at the boundary.
        frame: u64,
    },
    /// The app recorded an input consumption on a tick.
    Input {
        /// Logical tick the input was consumed on.
        tick: u64,
        /// Rendered frame during which it was consumed.
        frame: u64,
        /// Human-readable description of the edge or motion; button edges are
        /// self-describing (`Key(Forward) press` / `Key(Forward) release`).
        what: String,
    },
    /// A beat's window screenshot was captured and written to disk; the
    /// tick/frame are the rendered moment the PNG shows (the runner decodes the
    /// capture's frame code and asserts it equals these).
    Beat {
        /// Beat name.
        name: String,
        /// Rendered tick the capture shows.
        tick: u64,
        /// Rendered frame the capture shows.
        frame: u64,
        /// Unique request id bound to this capture.
        request_id: u64,
    },
    /// The app finished writing the report and will exit cleanly.
    Complete {
        /// Rendered frame at completion.
        frame: u64,
    },
    /// The app hit an unrecoverable error (a failed beat capture, for example);
    /// it records the failure and exits nonzero. The scenario does not retry.
    Failure {
        /// Scenario frame at which the failure was recorded.
        frame: u64,
        /// The failing step and underlying error, naming the beat or artifact.
        what: String,
    },
}

impl TimedEvent {
    /// Sort key for the report's canonical event order: the class rank first
    /// (the ready boundary sorts before the run's events, terminal events
    /// after them), then tick, then frame. Equal keys keep append order
    /// through the stable sort in [`sort_events`], which preserves each
    /// tick's buffered-edge order for inputs (press before release).
    fn order_key(&self) -> (u8, u64, u64) {
        match self {
            Self::Ready { frame } => (0, 0, *frame),
            Self::Input { tick, frame, .. } | Self::Beat { tick, frame, .. } => (1, *tick, *frame),
            Self::Complete { frame } | Self::Failure { frame, .. } => (2, u64::MAX, *frame),
        }
    }
}

/// Frame-time statistics over the run (from present timestamps).
#[derive(Clone, Debug, Default, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct FrameStats {
    /// Rendered frames measured.
    pub frames: u64,
    /// Mean frame duration in microseconds.
    pub mean_us: f64,
    /// Sample 95th-percentile duration in microseconds.
    pub p95_us: f64,
    /// Median duration in microseconds.
    pub median_us: f64,
}

/// One entry in the capture manifest.
#[derive(Clone, Debug, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct BeatEntry {
    /// Capture file, relative forward-slash from the run directory.
    pub file: String,
    /// Tick the capture was requested at.
    pub tick: u64,
    /// Rendered frame the capture was requested at.
    pub frame: u64,
    /// Request id bound to this capture.
    pub request_id: u64,
}

/// Content-hash run identity.
#[derive(Clone, Debug, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct Identity {
    /// sha2-256 of the app binary bytes.
    pub app_hash: String,
    /// sha2-256 of the scenario file bytes.
    pub scenario_hash: String,
    /// sha2-256 of the harness config bytes (the runner defines this; the app
    /// echoes it back).
    pub config_hash: String,
}

/// The report.
#[derive(Clone, Debug, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct Report {
    /// Protocol version this report conforms to.
    pub protocol_version: u32,
    /// Scenario name.
    pub scenario: String,
    /// Seed used for the scenario RNG stream.
    pub seed: u64,
    /// Tick-stamped events in order.
    pub events: Vec<TimedEvent>,
    /// Phase checkpoints with wall offsets.
    pub checkpoints: Vec<String>,
    /// Frame-time statistics.
    pub frame_stats: FrameStats,
    /// Beat name -> capture entry.
    pub beats: BTreeMap<String, BeatEntry>,
    /// Run identity: content hashes.
    pub identity: Identity,
}

/// Write a report as JSON text.
///
/// # Errors
/// Returns a message when the report cannot be serialized.
pub fn report_to_json(report: &Report) -> Result<String, String> {
    serde_json::to_string_pretty(report).map_err(|e| format!("report serialize: {e}"))
}

/// Parse a report from JSON.
///
/// # Errors
/// Returns a message when the text is not a report.
pub fn parse_report(text: &str) -> Result<Report, String> {
    serde_json::from_str(text).map_err(|e| format!("report parse error: {e}"))
}

/// Sort events into the report's canonical total order: by tick, then frame,
/// with the ready boundary first and terminal events (`Complete`, `Failure`)
/// last, equal keys keeping append order. The app applies this when it
/// serializes the report because capture completion is asynchronous: a beat's
/// readback can land several ticks after the tick the capture shows, so
/// wall-clock append order is not reproducible across runs. The canonical
/// order is, and each `Beat` event keeps its captured tick/frame and request
/// id, the numbers the runner's frame-code decode proves.
pub fn sort_events(events: &mut [TimedEvent]) {
    events.sort_by_key(TimedEvent::order_key);
}

/// Thin assertion-view over a report used by the runner to answer "did the app
/// actually do the thing".
impl Report {
    /// All recorded checkpoints reference frame and tick.
    #[must_use]
    pub fn has_checkpoint(&self, snippet: &str) -> bool {
        self.checkpoints.iter().any(|c| c.contains(snippet))
    }

    /// The rendered frame at which the ready event fired, if any.
    #[must_use]
    pub fn ready_frame(&self) -> Option<u64> {
        self.events.iter().find_map(|e| match e {
            TimedEvent::Ready { frame } => Some(*frame),
            _ => None,
        })
    }

    /// The first recorded failure, if the run failed.
    #[must_use]
    pub fn first_failure(&self) -> Option<&str> {
        self.events.iter().find_map(|e| match e {
            TimedEvent::Failure { what, .. } => Some(what.as_str()),
            _ => None,
        })
    }
}

/// A report with the given identity and an empty timeline.
impl Report {
    /// Construct an empty report.
    #[must_use]
    pub fn new(protocol_version: u32, scenario: &str, seed: u64, identity: Identity) -> Self {
        Self {
            protocol_version,
            scenario: scenario.to_owned(),
            seed,
            events: Vec::new(),
            checkpoints: Vec::new(),
            frame_stats: FrameStats::default(),
            beats: BTreeMap::new(),
            identity,
        }
    }
}

#[cfg(test)]
mod tests {
    use std::collections::BTreeMap;

    use super::{BeatEntry, FrameStats, Identity, Report, TimedEvent};

    fn sample() -> Report {
        Report {
            protocol_version: 1,
            scenario: "smoke".to_owned(),
            seed: 0,
            events: vec![
                TimedEvent::Ready { frame: 3 },
                TimedEvent::Beat {
                    name: "beat-a".into(),
                    tick: 2,
                    frame: 5,
                    request_id: 1,
                },
                TimedEvent::Complete { frame: 9 },
            ],
            checkpoints: vec!["ready".into(), "beat-a captured".into()],
            frame_stats: FrameStats {
                frames: 9,
                mean_us: 16000.0,
                p95_us: 17000.0,
                median_us: 16000.0,
            },
            beats: BTreeMap::from([(
                "beat-a".into(),
                BeatEntry {
                    file: "beats/beat-a.png".into(),
                    tick: 2,
                    frame: 5,
                    request_id: 1,
                },
            )]),
            identity: Identity {
                app_hash: "a".into(),
                scenario_hash: "s".into(),
                config_hash: "c".into(),
            },
        }
    }

    #[test]
    fn report_roundtrips() {
        let json = super::report_to_json(&sample()).expect("serializes");
        let parsed = super::parse_report(&json).expect("parses");
        assert_eq!(parsed, sample());
    }

    #[test]
    fn checkpoint_and_ready_frame_helpers_work() {
        let report = sample();
        assert!(report.has_checkpoint("ready"));
        assert!(!report.has_checkpoint("deferred"));
        assert_eq!(report.ready_frame(), Some(3));
    }

    #[test]
    fn parse_rejects_malformed_json() {
        assert!(super::parse_report("{ nope").is_err());
    }

    #[test]
    fn failure_event_roundtrips_and_is_findable() {
        let mut report = sample();
        report.events.push(super::TimedEvent::Failure {
            frame: 10,
            what: "beat `beat-a` capture save failed: disk full".into(),
        });
        let json = super::report_to_json(&report).expect("serializes");
        let parsed = super::parse_report(&json).expect("parses");
        assert_eq!(
            parsed.first_failure(),
            Some("beat `beat-a` capture save failed: disk full")
        );
    }

    #[test]
    fn first_failure_is_none_on_a_clean_report() {
        assert_eq!(sample().first_failure(), None);
    }

    /// A minimal report carrying exactly `events` (the sort is the thing under
    /// test; the rest of the report is scaffolding for serialization).
    fn report_with_events(events: Vec<TimedEvent>) -> Report {
        let mut report = Report::new(
            1,
            "pacing",
            1234,
            Identity {
                app_hash: "a".into(),
                scenario_hash: "s".into(),
                config_hash: "c".into(),
            },
        );
        report.events = events;
        report
    }

    #[test]
    fn async_capture_completion_cannot_reorder_the_written_events() {
        // Regression (issue #5 stage A): report events were appended in
        // wall-clock completion order, and a beat capture's readback lands
        // asynchronously (the documented one-to-two-frame readback delay), so
        // two runs with identical tick/frame data diverged at the first beat
        // whose readback landed late. The written order must be canonical:
        // tick, then frame, ready first, terminal events last, and same-key
        // ties keeping each tick's buffered-edge order (press before release).
        let input = |tick: u64, what: &str| TimedEvent::Input {
            tick,
            frame: tick,
            what: what.to_owned(),
        };
        let beat = |name: &str, tick: u64, request_id: u64| TimedEvent::Beat {
            name: name.to_owned(),
            tick,
            frame: tick,
            request_id,
        };
        // Run A: beat-a's readback landed while tick 5 was still driving.
        let mut run_a = vec![
            TimedEvent::Ready { frame: 0 },
            input(0, "look 15 0"),
            input(3, "move-delta"),
            beat("beat-a", 2, 1),
            input(5, "Key(Activate) press"),
            input(5, "Key(Activate) release"),
            beat("beat-b", 8, 2),
            TimedEvent::Complete { frame: 11 },
        ];
        // Run B: both readbacks landed after every scripted input.
        let mut run_b = vec![
            TimedEvent::Ready { frame: 0 },
            input(0, "look 15 0"),
            input(3, "move-delta"),
            input(5, "Key(Activate) press"),
            input(5, "Key(Activate) release"),
            beat("beat-a", 2, 1),
            beat("beat-b", 8, 2),
            TimedEvent::Complete { frame: 11 },
        ];
        super::sort_events(&mut run_a);
        super::sort_events(&mut run_b);
        let json_a = super::report_to_json(&report_with_events(run_a)).expect("serializes");
        let json_b = super::report_to_json(&report_with_events(run_b)).expect("serializes");
        assert_eq!(
            json_a, json_b,
            "both append orders must serialize to the same report"
        );
        // The shared sequence is the canonical one: sorted by tick, the ready
        // boundary first, completion last, and every Beat event still carrying
        // the captured tick/frame and request id.
        let expected = vec![
            TimedEvent::Ready { frame: 0 },
            input(0, "look 15 0"),
            beat("beat-a", 2, 1),
            input(3, "move-delta"),
            input(5, "Key(Activate) press"),
            input(5, "Key(Activate) release"),
            beat("beat-b", 8, 2),
            TimedEvent::Complete { frame: 11 },
        ];
        let written = super::parse_report(&json_a).expect("parses").events;
        assert_eq!(written, expected);
    }
}
