//! Scenario define format for the harness (issue #5 / slice A).
//!
//! A scenario is a JSON file the runner hands the app via `GONE_SCENARIO`. The
//! scenario is the reproducible instruction: same file + same seed + same build should
//! play the same ticks in sequence against the fixed logical clock.

use crate::harness::input::ScriptedAction;

/// Fixed logical tick rate the app simulates at after the readiness handshake,
/// used when the scenario does not override it.
pub const TICKS_PER_SECOND: u64 = 60;

/// Pacing variation used only by `harness compare`.
#[derive(Clone, Copy, Debug, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub enum Pacing {
    /// Run with vsync presentation (the default).
    FixedVsync,
    /// Run with an uncapped present (present immediately), the pacing-variation
    /// probe for compare mode.
    Uncapped,
}

/// One scenario definition.
#[derive(Clone, Debug, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct Scenario {
    /// Scenario name (also used for the artifact directory name by the runner).
    pub name: String,
    /// Seed for the scenario's RNG stream, used to key run-id and reproducibility.
    pub seed: u64,
    /// Logical ticks per second for the fixed timeline.
    #[serde(default = "default_tps")]
    pub ticks_per_second: u64,
    /// Scripted inputs, executed on their tick schedule.
    pub actions: Vec<ScriptedAction>,
    /// Named beats to capture (in tick order).
    pub beats: Vec<crate::harness::Beat>,
    /// Optional pacing variation for the determinism compare mode.
    #[serde(default)]
    pub pacing: Option<Pacing>,
    /// Optional wait: if present the app may run this many *rendered frames* after
    /// the last action at most before clean-closing.
    #[serde(default = "default_max_frames")]
    pub max_frames: u64,
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
        }
    }
}

/// Parse a scenario from JSON text.
///
/// # Errors
/// Returns a message when the JSON is invalid or is not a scenario.
pub fn parse_scenario(text: &str) -> Result<Scenario, String> {
    serde_json::from_str(text).map_err(|e| format!("scenario parse error: {e}"))
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
    use super::{Scenario, parse_scenario, scenario_to_json};

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
    fn serialized_scenario_roundtrips() {
        let a = parse_scenario(GOOD).expect("a");
        let b: Scenario = parse_scenario(&scenario_to_json(&a).expect("json")).expect("b");
        assert_eq!(a, b);
    }
}
