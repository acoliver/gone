//! Beat protocol for the harness (issue #5 / slice A).
//!
//! A *beat* is a named, timestamped moment the app is asked to capture. The
//! runner asserts that every expected beat from the scenario actually happened and that
//! the capture is bound to the (tick, rendered frame) pair the report claims.

use std::fmt;

/// A named capture point in time expressed in logical ticks. Names are free-form
/// but must be unique within one scenario; the smoke scenario uses `beat-a` /
/// `beat-b`.
#[derive(Clone, Debug, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct Beat {
    /// Human/verifier-meaningful name, repeated verbatim in the report.
    pub name: String,
    /// Logical tick (after the readiness reset) at which the capture is requested.
    pub tick: u64,
}

impl Beat {
    /// A beat at `tick` named `name`.
    #[must_use]
    pub fn new(name: &str, tick: u64) -> Self {
        Self {
            name: name.to_owned(),
            tick,
        }
    }
}

/// Describe a beat for errors, always naming it.
impl fmt::Display for Beat {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "beat `{}`@{}", self.name, self.tick)
    }
}

/// Expectation lookups and verification over a list of [`Beat`]s. All logic is
/// pure so the runner's decision is unit-testable without spawning the app.
pub mod verify {
    use std::collections::BTreeSet;

    use super::Beat;

    /// Verify a list of expectations against the happenings. Every named expected
    /// beat must exist. Returns an error whose message names the first missing beat.
    ///
    /// # Errors
    /// Returns an `Err` whose message names the missing beat when any expected beat is
    /// absent from `happened`.
    pub fn verify_beats(happened: &[Beat], expected: &[Beat]) -> Result<(), String> {
        let present: BTreeSet<&str> = happened.iter().map(|b| b.name.as_str()).collect();
        for beat in expected {
            if !present.contains(beat.name.as_str()) {
                return Err(format!(
                    "missing beat `{}` (expected tick {})",
                    beat.name, beat.tick
                ));
            }
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::Beat;
    use super::verify::verify_beats;

    #[test]
    fn all_expected_beats_present_pass() {
        let happened = vec![Beat::new("b1", 3), Beat::new("b2", 4)];
        let expected = vec![Beat::new("b2", 4), Beat::new("b1", 3)];
        assert!(verify_beats(&happened, &expected).is_ok());
    }

    #[test]
    fn missing_beat_named_exactly() {
        let happened = vec![Beat::new("b1", 3)];
        let err = verify_beats(&happened, &[Beat::new("b2", 9)]).unwrap_err();
        assert!(
            err.contains("b2"),
            "error must name the missing beat: {err}"
        );
        assert!(
            err.contains('9'),
            "error must carry the expected tick: {err}"
        );
    }

    #[test]
    fn missing_beat_reported_even_with_others_present() {
        let happened = vec![Beat::new("a", 1), Beat::new("c", 3)];
        let expected = vec![Beat::new("nope", 7), Beat::new("a", 1)];
        let err = verify_beats(&happened, &expected).unwrap_err();
        assert!(err.contains("nope"));
    }
}
