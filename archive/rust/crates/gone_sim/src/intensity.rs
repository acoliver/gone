//! Deterministic fixture-intensity interpolation (issue #10 groundwork).
//!
//! The emergency bay's fixtures do not teleport between intensities: a
//! fixture driven by the power state eases from its current value toward
//! a target over an explicit settle duration. This module owns that
//! interpolation as a small, pure, tick-driven helper:
//!
//! * [`FixtureFade`] holds one fixture's intensity fade: the value the
//!   fade started from, the target it eases toward, the explicit settle
//!   duration in logical ticks, and the ticks consumed so far. Every
//!   value is a pure function of that state: no wall clock, no dt, no
//!   global mutable state — a tick is a tick, one
//!   [`LOGICAL_TICK_SECS`](crate::LOGICAL_TICK_SECS) step at a time.
//! * [`FixtureFade::retarget`] is the crossfade hook: it restarts the
//!   fade from the fixture's actual current intensity, so retargeting
//!   mid-fade never discontinuously jumps. This is the code path the
//!   first repair milestone's lighting payoff will exercise; milestone 1
//!   never triggers it in-game, but its behavior is proven here by tests.
//!
//! # Settle and boundary contract (documented and frozen)
//!
//! A fade authored from `initial` toward `target` over `settle_ticks`
//! holds `initial` before its first tick, eases linearly and
//! monotonically between the endpoints while it runs, and lands on
//! `target` at exactly the settle tick, holding it exactly from then on.
//! The progress is a single division by the settle duration, never a
//! running sum, so batching ticks differently can never change a value —
//! the same boundary rule the wake timeline samples by.
//!
//! A settle duration of zero is valid and means immediate: the fixture
//! sits at its target from construction (or from the retarget tick) with
//! no intervening values. That is the hard cut, for a fixture that dies
//! with the cells rather than fading; callers who want an eased settle
//! author a positive duration.
//!
//! Validation is fail-loud, matching the crate's authoring rule: a
//! non-finite or negative intensity constructs nothing, and a rejected
//! construction or retarget leaves no half-built state behind. Intensities
//! are otherwise unbounded — the sim does not guess a renderer's range.
//!
//! Pure: no Bevy, no clocks, no RNG.

/// A rejected fixture-fade intensity.
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum FixtureFadeError {
    /// An intensity carried a non-finite value (NaN or infinity), which
    /// would poison every interpolation downstream.
    NonFiniteIntensity {
        /// The offending value.
        got: f32,
    },
    /// An intensity sat below zero, which the field's meaning excludes:
    /// intensities count up from dark.
    NegativeIntensity {
        /// The offending value.
        got: f32,
    },
}

impl std::fmt::Display for FixtureFadeError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::NonFiniteIntensity { got } => {
                write!(f, "fixture intensity carried a non-finite value: {got}")
            }
            Self::NegativeIntensity { got } => {
                write!(
                    f,
                    "fixture intensity {got} is negative: intensities count up from dark"
                )
            }
        }
    }
}

impl std::error::Error for FixtureFadeError {}

/// Validate one authored intensity: finite, then non-negative.
fn validate_intensity(value: f32) -> Result<(), FixtureFadeError> {
    if !value.is_finite() {
        return Err(FixtureFadeError::NonFiniteIntensity { got: value });
    }
    if value < 0.0 {
        return Err(FixtureFadeError::NegativeIntensity { got: value });
    }
    Ok(())
}

/// One fixture's intensity fade: the pure, tick-driven crossfade helper
/// the render bridge drives per fixture.
///
/// Built only through [`FixtureFade::new`] and [`FixtureFade::holding`],
/// which validate their inputs. The fields are private; the fade changes
/// only through [`FixtureFade::tick`] and [`FixtureFade::retarget`], so
/// an intensity can never jump outside the documented boundary contract.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct FixtureFade {
    /// The intensity the current fade eases from.
    from: f32,
    /// The intensity the current fade eases toward.
    target: f32,
    /// The current fade's settle duration in logical ticks. Zero is the
    /// immediate hard cut.
    settle_ticks: u16,
    /// Ticks consumed by the current fade. Never exceeds `settle_ticks`:
    /// once settled the counter stops, so a forever-held fixture cannot
    /// wrap it.
    elapsed_ticks: u16,
}

impl FixtureFade {
    /// Author a fade from `initial` toward `target` over `settle_ticks`
    /// logical ticks. The fade starts holding `initial` bitwise and lands
    /// on `target` bitwise at exactly the settle tick. A zero settle is
    /// the immediate hard cut: the fade is settled at `target` from
    /// construction. Duration is an unsigned count of logical ticks,
    /// limited to `0..=u16::MAX`; negative, fractional, and larger counts
    /// must be rejected when converting external input, not clamped here.
    ///
    /// ```
    /// use gone_sim::FixtureFade;
    /// let mut fade = FixtureFade::new(0.0, 8.0, 2)?;
    /// assert_eq!(fade.tick(), 4.0);
    /// assert_eq!(fade.tick(), 8.0);
    /// assert!(fade.is_settled());
    /// # Ok::<(), gone_sim::FixtureFadeError>(())
    /// ```
    ///
    /// Negative durations cannot be authored:
    /// ```compile_fail
    /// gone_sim::FixtureFade::new(0.0, 1.0, -1);
    /// ```
    /// Counts above the duration range cannot be authored:
    /// ```compile_fail
    /// gone_sim::FixtureFade::new(0.0, 1.0, 65_536);
    /// ```
    ///
    /// # Errors
    /// [`FixtureFadeError::NonFiniteIntensity`] for a non-finite
    /// `initial` or `target`, and
    /// [`FixtureFadeError::NegativeIntensity`] for a negative one. A
    /// rejected authoring builds nothing.
    pub fn new(initial: f32, target: f32, settle_ticks: u16) -> Result<Self, FixtureFadeError> {
        validate_intensity(initial)?;
        validate_intensity(target)?;
        Ok(Self {
            from: initial,
            target,
            settle_ticks,
            elapsed_ticks: 0,
        })
    }

    /// A fixture holding `value`, settled, with no fade in flight: the
    /// state every fixture starts in before its first state-driven fade.
    ///
    /// # Errors
    /// [`FixtureFadeError::NonFiniteIntensity`] and
    /// [`FixtureFadeError::NegativeIntensity`], as in
    /// [`FixtureFade::new`].
    pub fn holding(value: f32) -> Result<Self, FixtureFadeError> {
        Self::new(value, value, 0)
    }

    /// Retarget the fade toward `target` over `settle_ticks`, starting
    /// from the fixture's actual current intensity. The value at the
    /// retarget equals the value just before it, so a mid-fade retarget
    /// never discontinuously jumps — including a retarget onto the same
    /// value, which holds it over the new settle. A zero settle cuts
    /// straight to `target`.
    ///
    /// # Errors
    /// [`FixtureFadeError::NonFiniteIntensity`] and
    /// [`FixtureFadeError::NegativeIntensity`] for a rejected `target`.
    /// A rejected retarget leaves the fade exactly as it was: same value,
    /// same target, same progress.
    pub fn retarget(&mut self, target: f32, settle_ticks: u16) -> Result<(), FixtureFadeError> {
        validate_intensity(target)?;
        self.from = self.intensity();
        self.target = target;
        self.settle_ticks = settle_ticks;
        self.elapsed_ticks = 0;
        Ok(())
    }

    /// The current intensity, without advancing. Before the first tick it
    /// is the fade's start value; from the settle tick on it is the
    /// target, returned bitwise rather than through the interpolation
    /// arithmetic.
    #[must_use]
    pub fn intensity(&self) -> f32 {
        if self.elapsed_ticks >= self.settle_ticks {
            return self.target;
        }
        if self.elapsed_ticks == 0 {
            return self.from;
        }
        let progress = f32::from(self.elapsed_ticks) / f32::from(self.settle_ticks);
        self.from + (self.target - self.from) * progress
    }

    /// The intensity the current fade eases toward.
    #[must_use]
    pub const fn target(&self) -> f32 {
        self.target
    }

    /// Whether the fade has reached its target: true from the settle tick
    /// on, and always for a zero-settle fade.
    #[must_use]
    pub const fn is_settled(&self) -> bool {
        self.elapsed_ticks >= self.settle_ticks
    }

    /// Consume one logical tick and return the intensity at the new tick.
    /// While the fade runs, each tick eases one tick further toward the
    /// target; from the settle tick on, every tick returns the target
    /// bitwise and the counter stands still.
    pub fn tick(&mut self) -> f32 {
        if self.elapsed_ticks < self.settle_ticks {
            // `elapsed < settle <= u16::MAX` bounds the increment, so it
            // can never overflow.
            self.elapsed_ticks += 1;
        }
        self.intensity()
    }
}

/// Coverage of the fade contract: endpoint exactness, monotone linear
/// intermediate values, stability after settle, the zero-settle hard cut,
/// retarget continuity and its rejection atomicity, and fail-loud input
/// validation.
#[cfg(test)]
mod tests {
    use super::{FixtureFade, FixtureFadeError};

    #[test]
    fn initial_endpoint_preserves_signed_zero() {
        let fade = FixtureFade::new(-0.0, 1.0, 1).expect("valid fade");
        assert_bits_equal(fade.intensity(), -0.0, "initial endpoint");
    }

    #[test]
    fn one_tick_settle_has_no_interior_sample() {
        let mut fade = FixtureFade::new(7.0, 2.0, 1).expect("valid fade");
        assert_bits_equal(fade.intensity(), 7.0, "initial endpoint");
        assert!(!fade.is_settled());
        assert_bits_equal(fade.tick(), 2.0, "one-tick target");
        assert!(fade.is_settled());
    }

    #[test]
    fn maximum_duration_settles_without_counter_overflow() {
        let mut fade = FixtureFade::new(0.0, 1.0, u16::MAX).expect("valid duration");
        let mut previous = fade.intensity();
        for _ in 1..u16::MAX {
            let next = fade.tick();
            assert!(next >= previous && next < 1.0);
            assert!(!fade.is_settled());
            previous = next;
        }
        assert_bits_equal(fade.tick(), 1.0, "maximum settle tick");
        assert!(fade.is_settled());
        for _ in 0..=u16::MAX {
            assert_bits_equal(fade.tick(), 1.0, "hold cannot wrap counter");
        }
    }

    #[test]
    fn zero_duration_retarget_cuts_immediately() {
        let mut fade = FixtureFade::new(0.0, 8.0, 4).expect("valid fade");
        fade.tick();
        fade.retarget(3.0, 0).expect("valid cut");
        assert_bits_equal(fade.intensity(), 3.0, "immediate target");
        assert!(fade.is_settled());
        assert_bits_equal(fade.tick(), 3.0, "cut holds");
    }

    #[test]
    fn extreme_valid_intensities_remain_finite_and_monotone() {
        for (initial, target) in [(0.0, f32::MAX), (f32::MAX, 0.0)] {
            let mut fade = FixtureFade::new(initial, target, 256).expect("valid endpoints");
            let mut previous = initial;
            for _ in 0..256 {
                let next = fade.tick();
                assert!(next.is_finite() && next >= 0.0);
                assert!(if target > initial {
                    next >= previous
                } else {
                    next <= previous
                });
                previous = next;
            }
            assert_bits_equal(fade.intensity(), target, "extreme endpoint");
        }
    }

    /// Closeness band for eased interior samples.
    const EASE_EPSILON: f32 = 1e-6;

    /// The bitwise intensity assert: boundary values must land with no
    /// interpolation error, and 0.0 against -0.0 would pass `==` while
    /// differing in bits.
    fn assert_bits_equal(actual: f32, expected: f32, label: &str) {
        assert_eq!(actual.to_bits(), expected.to_bits(), "{label}");
    }

    /// Asserts closeness for an eased interior sample.
    fn assert_close(actual: f32, expected: f32, label: &str) {
        assert!(
            (actual - expected).abs() < EASE_EPSILON,
            "{label}: expected {expected}, got {actual}"
        );
    }

    /// A fade holds its start value before the first tick, eases in
    /// linear steps, lands on the target bitwise at the settle tick, and
    /// holds it exactly forever after.
    #[test]
    fn fade_hits_exact_linear_steps_and_settles_stably() {
        let mut fade = FixtureFade::new(0.0, 8.0, 4).expect("valid fade");
        assert_bits_equal(fade.intensity(), 0.0, "pre-fade hold");
        assert!(!fade.is_settled());
        assert_bits_equal(fade.target(), 8.0, "target");
        assert_close(fade.tick(), 2.0, "step 1");
        assert_close(fade.tick(), 4.0, "step 2");
        assert_close(fade.tick(), 6.0, "step 3");
        assert_bits_equal(fade.tick(), 8.0, "settle tick");
        assert!(fade.is_settled());
        for _ in 0..100 {
            assert_bits_equal(fade.tick(), 8.0, "post-settle hold");
        }
    }

    /// A rising fade is strictly increasing between its endpoints and
    /// never overshoots the target.
    #[test]
    fn rising_fade_is_monotone_between_endpoints() {
        let mut fade = FixtureFade::new(0.5, 2.0, 8).expect("valid fade");
        let mut previous = fade.intensity();
        for _ in 0..8 {
            let next = fade.tick();
            assert!(
                next > previous,
                "rising fade must increase: {previous} to {next}"
            );
            assert!(next <= 2.0, "fade must not overshoot the target: {next}");
            previous = next;
        }
        assert_bits_equal(fade.intensity(), 2.0, "settled at target");
    }

    /// A falling fade is strictly decreasing between its endpoints and
    /// never undershoots the target.
    #[test]
    fn falling_fade_is_monotone_between_endpoints() {
        let mut fade = FixtureFade::new(2.0, 0.5, 8).expect("valid fade");
        let mut previous = fade.intensity();
        for _ in 0..8 {
            let next = fade.tick();
            assert!(
                next < previous,
                "falling fade must decrease: {previous} to {next}"
            );
            assert!(next >= 0.5, "fade must not undershoot the target: {next}");
            previous = next;
        }
        assert_bits_equal(fade.intensity(), 0.5, "settled at target");
    }

    /// A zero settle is the documented immediate hard cut: settled at the
    /// target from construction, and ticking changes nothing.
    #[test]
    fn zero_settle_is_an_immediate_hard_cut() {
        let mut fade = FixtureFade::new(1.0, 0.0, 0).expect("valid fade");
        assert_bits_equal(fade.intensity(), 0.0, "hard cut");
        assert_bits_equal(fade.target(), 0.0, "hard-cut target");
        assert!(fade.is_settled());
        for _ in 0..4 {
            assert_bits_equal(fade.tick(), 0.0, "hard cut holds");
            assert!(fade.is_settled());
        }
    }

    /// A held fixture sits at its value forever.
    #[test]
    fn holding_keeps_the_value_forever() {
        let mut fade = FixtureFade::holding(3.0).expect("valid hold");
        assert_bits_equal(fade.target(), 3.0, "hold target");
        assert!(fade.is_settled());
        for _ in 0..8 {
            assert_bits_equal(fade.tick(), 3.0, "hold");
        }
    }

    /// A mid-fade retarget restarts from the actual current intensity
    /// without a discontinuity, eases to the new target, and lands on it
    /// bitwise at the new settle tick.
    #[test]
    fn mid_fade_retarget_continues_without_a_jump() {
        let mut fade = FixtureFade::new(0.0, 8.0, 8).expect("valid fade");
        for _ in 0..4 {
            fade.tick();
        }
        assert_close(fade.intensity(), 4.0, "halfway");
        fade.retarget(2.0, 4).expect("valid retarget");
        assert_bits_equal(fade.intensity(), 4.0, "the retarget must not jump");
        assert_bits_equal(fade.target(), 2.0, "new target");
        assert_close(fade.tick(), 3.5, "retarget step 1");
        assert_close(fade.tick(), 3.0, "retarget step 2");
        assert_close(fade.tick(), 2.5, "retarget step 3");
        assert_bits_equal(fade.tick(), 2.0, "retarget settle tick");
        assert!(fade.is_settled());
        assert_bits_equal(fade.tick(), 2.0, "post-settle hold");
    }

    /// A retarget onto the current value holds it over the new settle:
    /// the constant fade is the degenerate monotone case.
    #[test]
    fn retarget_onto_the_current_value_holds_it() {
        let mut fade = FixtureFade::holding(1.5).expect("valid hold");
        fade.retarget(1.5, 4).expect("valid retarget");
        assert!(!fade.is_settled());
        for _ in 0..4 {
            assert_bits_equal(fade.tick(), 1.5, "constant fade");
        }
        assert!(fade.is_settled());
    }

    /// A rejected retarget is atomic: the fade keeps its value, target,
    /// and progress exactly.
    #[test]
    fn rejected_retarget_leaves_the_fade_untouched() {
        let mut fade = FixtureFade::new(0.0, 8.0, 8).expect("valid fade");
        fade.tick();
        assert_close(fade.intensity(), 1.0, "one tick in");
        for target in [f32::NAN, f32::INFINITY, f32::NEG_INFINITY, -0.5] {
            let result = fade.retarget(target, 4);
            assert!(result.is_err(), "target {target} must be rejected");
            assert_bits_equal(fade.target(), 8.0, "target unchanged");
            assert_close(fade.intensity(), 1.0, "progress unchanged");
            assert!(!fade.is_settled());
        }
    }

    /// Authoring validates fail-loud: non-finite and negative inputs
    /// construct nothing, in either endpoint. Rejections name their
    /// variant, finite rejections carry the offending value, and the
    /// Display text says which rule fired.
    #[test]
    fn construction_rejects_non_finite_and_negative_intensities() {
        let assert_non_finite = |err: FixtureFadeError| {
            assert!(
                matches!(err, FixtureFadeError::NonFiniteIntensity { .. }),
                "a non-finite intensity must name the non-finite variant: {err}"
            );
        };
        let assert_negative = |err: FixtureFadeError| {
            assert!(
                matches!(err, FixtureFadeError::NegativeIntensity { .. }),
                "a negative intensity must name the negative variant: {err}"
            );
        };
        for value in [f32::NAN, f32::INFINITY, f32::NEG_INFINITY] {
            assert_non_finite(
                FixtureFade::new(value, 1.0, 4).expect_err("bad initial must be rejected"),
            );
            assert_non_finite(
                FixtureFade::new(1.0, value, 4).expect_err("bad target must be rejected"),
            );
        }
        assert_negative(FixtureFade::new(-1.0, 1.0, 4).expect_err("bad initial must be rejected"));
        assert_negative(FixtureFade::new(1.0, -1.0, 4).expect_err("bad target must be rejected"));
        assert_negative(FixtureFade::holding(-1.0).expect_err("bad hold must be rejected"));

        // The finite rejections carry the offending value exactly.
        assert_eq!(
            FixtureFade::new(-1.0, 1.0, 4),
            Err(FixtureFadeError::NegativeIntensity { got: -1.0 })
        );
        assert_eq!(
            FixtureFade::holding(-1.0),
            Err(FixtureFadeError::NegativeIntensity { got: -1.0 })
        );
        // And the Display text says which rule fired.
        assert!(
            FixtureFade::new(f32::NAN, 1.0, 4)
                .expect_err("display check")
                .to_string()
                .contains("non-finite")
        );
        assert!(
            FixtureFade::new(1.0, -0.25, 4)
                .expect_err("display check")
                .to_string()
                .contains("negative")
        );
    }
}
