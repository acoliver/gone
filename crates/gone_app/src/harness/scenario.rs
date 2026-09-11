//! Scenario define format for the harness (issue #5 / slice A).
//!
//! A scenario is a JSON file the runner hands the app via `GONE_SCENARIO`. The
//! scenario is the reproducible instruction: same file + same seed + same build should
//! play the same ticks in sequence against the fixed logical clock.

use crate::harness::input::ScriptedAction;

/// Default fixed logical tick rate the app simulates at after the readiness
/// handshake: one tick per scenario frame, each worth `1/TICKS_PER_SECOND`
/// seconds of simulation time, when the scenario does not override the rate.
pub const TICKS_PER_SECOND: u64 = 60;

/// Pacing variation: the presentation mode a run uses. Parsed per scenario and
/// consumed at window creation: `Uncapped` sets the window to
/// `PresentMode::AutoNoVsync` so wall-clock frame times are not quantized by
/// vsync (the perf lane requires this; `compare` scenarios leave it unset and
/// run the default vsync presentation).
#[derive(Clone, Copy, Debug, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub enum Pacing {
    /// Run with vsync presentation (the default).
    FixedVsync,
    /// Run with an uncapped present (present immediately), the pacing-variation
    /// probe for compare mode and the perf lane's requirement.
    Uncapped,
}

/// Which world the app builds for a run. Content selection is separate from
/// the presentation mode ([`ScenarioMode`] decides what the run measures;
/// `Content` decides what the run renders): the calibration scene is the
/// default and is byte-for-byte the historical behavior, and gameplay boots
/// the real game plugins alongside the harness protocol systems.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Content {
    /// The calibration scene: dark clear plus the frame-code chip sprite,
    /// rendered by the harness camera into the offscreen capture target.
    #[default]
    Calibration,
    /// The real game content: stasis room, player rig with first-person
    /// look, and the explicit post chain. The frame-code chip renders as a
    /// small overlay in the corner of the gameplay camera's view, same
    /// lattice encoding and decode contract as calibration.
    Gameplay,
}

/// What the scenario asks the app to do.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ScenarioMode {
    /// Drive beats and captures (the default capture lane).
    #[default]
    Capture,
    /// Measure wall-clock frame times over a warmup + sample window: readiness
    /// as usual, then no beats, no captures, no decode. The perf policy that
    /// judges the window lives runner-side; the scenario carries only the
    /// window shape.
    Perf,
}

/// One scenario definition.
#[derive(Clone, Debug, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct Scenario {
    /// Scenario name (also used for the artifact directory name by the runner).
    pub name: String,
    /// Seed for the scenario's RNG stream, used to key run-id and reproducibility.
    pub seed: u64,
    /// Logical tick rate of the scenario's fixed clock (at least 1). One tick
    /// advances simulation time by `1 / ticks_per_second` seconds, and the
    /// clock advances exactly one tick per scenario frame after the readiness
    /// boundary; the headless capture lane also paces its update loop at this
    /// rate, so the simulation's wall-clock rate is the declared rate wherever
    /// the lane can pace it. Validated at parse time: a zero rate is a
    /// scenario error, never a silent fallback to the default.
    #[serde(default = "default_tps")]
    pub ticks_per_second: u64,
    /// Scripted inputs, executed on their tick schedule.
    pub actions: Vec<ScriptedAction>,
    /// Named beats to capture (in tick order).
    pub beats: Vec<crate::harness::Beat>,
    /// Optional pacing variation for the determinism compare mode.
    #[serde(default)]
    pub pacing: Option<Pacing>,
    /// Hard clean-close deadline in *scenario frames* (drive steps after the
    /// readiness boundary; frames the clock spends held under a readback
    /// never consume it): the run ends at this count at the latest. Beats
    /// still uncaptured when the count reaches it are recorded as missing and
    /// fail the run with a nonzero exit.
    #[serde(default = "default_max_frames")]
    pub max_frames: u64,
    /// Which world the app builds: the calibration scene by default, or the
    /// real gameplay plugins. The runner and the app both parse this, so a
    /// gameplay scenario always runs the gameplay lane.
    #[serde(default)]
    pub content: Content,
    /// What the scenario asks the app to do (capture lane by default).
    #[serde(default)]
    pub mode: ScenarioMode,
    /// Perf mode only: frames run after readiness before the sample window
    /// starts. Unused (zero) on the capture lane.
    #[serde(default)]
    pub warmup_frames: u64,
    /// Perf mode only: rendered frames sampled into the perf window. Must be
    /// at least 1 in perf mode; unused (zero) on the capture lane.
    #[serde(default)]
    pub sample_frames: u64,
}

impl Default for Scenario {
    fn default() -> Self {
        Self {
            name: String::new(),
            seed: 0,
            ticks_per_second: TICKS_PER_SECOND,
            actions: Vec::new(),
            beats: Vec::new(),
            pacing: None,
            max_frames: default_max_frames(),
            content: Content::default(),
            mode: ScenarioMode::default(),
            warmup_frames: 0,
            sample_frames: 0,
        }
    }
}

/// Parse a scenario from JSON text.
///
/// # Errors
/// Returns a message when the JSON is invalid, is not a scenario, or declares
/// a `ticks_per_second` below 1: the fixed clock has no meaningful step at a
/// zero rate, so a rateless scenario fails here on both sides (the app and
/// the runner share this parser) instead of failing later mid-run.
pub fn parse_scenario(text: &str) -> Result<Scenario, String> {
    let scenario: Scenario =
        serde_json::from_str(text).map_err(|e| format!("scenario parse error: {e}"))?;
    if scenario.ticks_per_second == 0 {
        return Err(format!(
            "scenario `{}` has ticks_per_second 0: the fixed clock needs a rate \
             of at least 1 tick per second",
            scenario.name
        ));
    }
    Ok(scenario)
}

/// Serialize a scenario to compact JSON.
///
/// # Errors
/// Returns a message when the scenario cannot be serialized.
pub fn scenario_to_json(scenario: &Scenario) -> Result<String, String> {
    serde_json::to_string(scenario).map_err(|e| format!("scenario serialize: {e}"))
}

fn default_tps() -> u64 {
    TICKS_PER_SECOND
}

fn default_max_frames() -> u64 {
    720
}

/// Key the scenario by name.
#[must_use]
pub fn index(scenarios: &[Scenario]) -> std::collections::BTreeMap<&str, &Scenario> {
    scenarios
        .iter()
        .map(|s| (s.name.as_str(), s))
        .collect::<std::collections::BTreeMap<_, _>>()
}

#[cfg(test)]
mod tests {
    use super::{Content, Pacing, Scenario, ScenarioMode, parse_scenario, scenario_to_json};

    const GOOD: &str = r#"{
        "name": "smoke",
        "seed": 7,
        "ticks_per_second": 60,
        "actions": [
            {"tick": 0, "action": {"Look": {"yaw_deg": 5.0, "pitch_deg": 0.0}}},
            {"tick": 5, "action": {"Press": {"button": {"Key": "Activate"}}}},
            {"tick": 10, "action": {"Release": {"button": {"Key": "Activate"}}}}
        ],
        "beats": [
            {"name": "beat-a", "tick": 2},
            {"name": "beat-b", "tick": 8}
        ],
        "max_frames": 240
    }"#;

    #[test]
    fn scenario_parses() {
        let scenario = parse_scenario(GOOD).expect("valid scenario");
        assert_eq!(scenario.name, "smoke");
        assert_eq!(scenario.seed, 7);
        assert_eq!(scenario.actions.len(), 3);
        assert_eq!(scenario.beats.len(), 2);
    }

    #[test]
    fn default_fields_apply() {
        let minimal = r#"{"name":"x","seed":0,"actions":[],"beats":[]}"#;
        let s: Scenario = parse_scenario(minimal).expect("parses");
        assert_eq!(s.ticks_per_second, 60);
        assert_eq!(s.pacing, None);
        assert_eq!(s.max_frames, 720);
        assert_eq!(s.content, Content::Calibration);
        assert_eq!(s.mode, ScenarioMode::Capture);
        assert_eq!(s.warmup_frames, 0);
        assert_eq!(s.sample_frames, 0);
    }

    #[test]
    fn gameplay_content_parses_and_defaults_to_calibration() {
        let gameplay = r#"{"name":"g","seed":0,"actions":[],"beats":[],"content":"gameplay"}"#;
        let s: Scenario = parse_scenario(gameplay).expect("parses");
        assert_eq!(s.content, Content::Gameplay);
        // An unknown content value is a parse error, never a silent fallback
        // to the calibration scene.
        let bad = r#"{"name":"x","seed":0,"actions":[],"beats":[],"content":"frobnicate"}"#;
        assert!(parse_scenario(bad).is_err());
    }

    #[test]
    fn perf_mode_and_window_parse() {
        let perf = r#"{
            "name": "calibration",
            "seed": 1,
            "actions": [],
            "beats": [],
            "mode": "perf",
            "pacing": "Uncapped",
            "warmup_frames": 120,
            "sample_frames": 600
        }"#;
        let s: Scenario = parse_scenario(perf).expect("parses");
        assert_eq!(s.mode, ScenarioMode::Perf);
        assert_eq!(s.pacing, Some(Pacing::Uncapped));
        assert_eq!(s.warmup_frames, 120);
        assert_eq!(s.sample_frames, 600);
    }

    #[test]
    fn unknown_mode_is_a_parse_error() {
        let bad = r#"{"name":"x","seed":0,"actions":[],"beats":[],"mode":"frobnicate"}"#;
        assert!(parse_scenario(bad).is_err());
    }

    #[test]
    fn malformed_json_errors() {
        let err = parse_scenario("{ nope").expect_err("must fail");
        assert!(err.contains("scenario parse error"));
    }

    #[test]
    fn unknown_action_variant_is_a_parse_error() {
        let bad =
            r#"{"name":"x","seed":0,"actions":[{"tick":0,"action":{"NoSuch":1}}],"beats":[]}"#;
        assert!(parse_scenario(bad).is_err());
    }

    #[test]
    fn a_zero_tick_rate_is_a_parse_error() {
        // The fixed clock consumes ticks_per_second as its simulation-time
        // step (1/tps seconds per tick); a zero rate has no meaningful step,
        // so it fails at parse time on both sides instead of mid-run.
        let bad = r#"{"name":"zero","seed":0,"ticks_per_second":0,"actions":[],"beats":[]}"#;
        let err = parse_scenario(bad).expect_err("zero tps must fail");
        assert!(err.contains("ticks_per_second"), "names the field: {err}");
        assert!(err.contains("zero"), "names the scenario: {err}");
        // A rate of 1 is the floor and parses fine.
        let floor = r#"{"name":"one","seed":0,"ticks_per_second":1,"actions":[],"beats":[]}"#;
        let parsed = parse_scenario(floor).expect("a rate of one is the floor");
        assert_eq!(parsed.ticks_per_second, 1);
    }

    #[test]
    fn serialized_scenario_roundtrips() {
        let a = parse_scenario(GOOD).expect("a");
        let b: Scenario = parse_scenario(&scenario_to_json(&a).expect("json")).expect("b");
        assert_eq!(a, b);
    }
}
