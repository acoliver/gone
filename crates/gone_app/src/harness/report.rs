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
    /// The app finished its startup presentation and the scenario clock reset;
    /// this is the tick-zero boundary.
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
        /// Human-readable description of the edge or motion.
        what: String,
    },
    /// The app requested a beat capture.
    Beat {
        /// Beat name.
        name: String,
        /// Tick when requested.
        tick: u64,
        /// Rendered frame when requested.
        frame: u64,
        /// Unique request id bound to this capture.
        request_id: u64,
    },
    /// The app finished writing the report and will exit cleanly.
    Complete {
        /// Rendered frame at completion.
        frame: u64,
    },
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
}
