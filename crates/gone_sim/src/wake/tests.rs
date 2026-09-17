//! Coverage of the wake timeline: the readiness contract (hold closed,
//! start exactly once, tick zero fully closed, delayed readiness, reset),
//! the exact authored boundaries through both blinks, batching-independent
//! sampling, the neutral completion tail, and every fail-loud authoring
//! rejection.

use glam::Vec2;

use super::{
    AUTHORED_BEAT_MILLIS, AuthoredBoundaries, LOGICAL_TICK_SECS, LOGICAL_TICKS_PER_SECOND,
    SWAY_OFFSET_MAX_RADIANS, WakeAuthoring, WakeBeat, WakeField, WakeSample, WakeStart, WakeState,
    WakeTimeline, WakeTimelineError, ticks_for,
};

/// The named boundaries of the authored table, the values the harness
/// temporal captures will pin. The authored milliseconds ([1250, 700, 450,
/// 900, 400, 1000]) encode at the 60 Hz logical rate to beats of 75, 42,
/// 27, 54, 24, and 60 ticks.
const B: AuthoredBoundaries = AuthoredBoundaries {
    first_opening_start: 75,
    first_blink_start: 117,
    second_opening_start: 144,
    second_blink_start: 198,
    final_opening_start: 222,
    complete_tick: 282,
};

/// Epsilon for interior eased samples (pure products of authored
/// literals and one f32 division).
const EASE_EPSILON: f32 = 1e-6;

/// A wake machine over the authored timeline.
fn authored_state() -> WakeState {
    WakeState::new(WakeTimeline::authored())
}

/// Run the authored timeline from readiness, collecting the sample at
/// every logical tick through `ticks` inclusive.
fn ready_run(ticks: u64) -> Vec<WakeSample> {
    let mut state = authored_state();
    assert_eq!(state.mark_ready(), WakeStart::Started);
    let mut samples = vec![state.sample()];
    for _ in 0..ticks {
        samples.push(state.tick());
    }
    samples
}

/// Asserts two samples are bitwise identical, field by field: boundary
/// ticks must land on authored states with no interpolation error, and
/// 0.0 against -0.0 would pass `==` while differing in bits.
fn assert_bitwise_equal(actual: WakeSample, expected: WakeSample, label: &str) {
    assert_eq!(
        actual.lid_openness.to_bits(),
        expected.lid_openness.to_bits(),
        "{label} lid openness"
    );
    assert_eq!(
        actual.blur.to_bits(),
        expected.blur.to_bits(),
        "{label} blur"
    );
    assert_eq!(
        actual.exposure_ramp.to_bits(),
        expected.exposure_ramp.to_bits(),
        "{label} exposure ramp"
    );
    assert_eq!(
        actual.sway_offset.x.to_bits(),
        expected.sway_offset.x.to_bits(),
        "{label} sway x"
    );
    assert_eq!(
        actual.sway_offset.y.to_bits(),
        expected.sway_offset.y.to_bits(),
        "{label} sway y"
    );
}

/// Asserts per-component closeness for an eased sample.
fn assert_close(actual: WakeSample, expected: WakeSample, label: &str) {
    let openness = (actual.lid_openness - expected.lid_openness).abs();
    let blur = (actual.blur - expected.blur).abs();
    let ramp = (actual.exposure_ramp - expected.exposure_ramp).abs();
    let sway = (actual.sway_offset - expected.sway_offset)
        .abs()
        .max_element();
    assert!(
        openness < EASE_EPSILON
            && blur < EASE_EPSILON
            && ramp < EASE_EPSILON
            && sway < EASE_EPSILON,
        "{label}: expected {expected:?}, got {actual:?}"
    );
}

/// The timeline holds fully closed before readiness, and pre-ready ticks
/// consume nothing: the sample and the counter both stay put.
#[test]
fn holds_closed_before_readiness_and_pre_ready_ticks_consume_nothing() {
    let mut state = authored_state();
    assert!(!state.is_started());
    assert!(!state.is_complete());
    assert_eq!(state.current_tick(), 0);
    assert_bitwise_equal(state.sample(), WakeSample::CLOSED, "fresh hold");

    for _ in 0..5 {
        assert_bitwise_equal(state.tick(), WakeSample::CLOSED, "pre-ready tick");
    }
    assert_eq!(state.current_tick(), 0, "pre-ready ticks never count");
    assert!(!state.is_started());
    assert!(!state.is_complete());
}

/// The first readiness poll starts the machine, and the sample at logical
/// tick zero is bitwise the closed rest state.
#[test]
fn first_readiness_starts_and_tick_zero_is_fully_closed() {
    let mut state = authored_state();
    assert_eq!(state.mark_ready(), WakeStart::Started);
    assert!(state.is_started());
    assert!(!state.is_complete());
    assert_eq!(state.current_tick(), 0);
    assert_bitwise_equal(state.sample(), WakeSample::CLOSED, "tick zero");
}

/// Duplicate readiness never restarts the timeline: the machine runs on
/// from where it is, and completion still lands on the first start's
/// schedule.
#[test]
fn duplicate_readiness_is_a_no_op_and_never_restarts() {
    let mut state = authored_state();
    assert_eq!(state.mark_ready(), WakeStart::Started);
    for _ in 0..7 {
        state.tick();
    }
    assert_eq!(state.current_tick(), 7);
    for _ in 0..3 {
        assert_eq!(state.mark_ready(), WakeStart::AlreadyStarted);
    }
    assert_eq!(state.current_tick(), 7, "duplicate polls never reset");

    // Even after completion a duplicate poll must not restart the run.
    for _ in 7..B.complete_tick + 4 {
        state.tick();
    }
    assert!(state.is_complete());
    assert_eq!(state.mark_ready(), WakeStart::AlreadyStarted);
    assert_bitwise_equal(state.sample(), WakeSample::NEUTRAL, "still complete");
}

/// A readiness barrier that opens late produces exactly the immediate
/// timeline: pre-ready ticks consume nothing, so both runs' sample
/// vectors match tick for tick.
#[test]
fn delayed_readiness_produces_the_immediate_timeline() {
    let immediate = ready_run(B.complete_tick + 2);

    let mut delayed = authored_state();
    for _ in 0..10 {
        assert_bitwise_equal(delayed.tick(), WakeSample::CLOSED, "held");
    }
    assert_eq!(delayed.mark_ready(), WakeStart::Started);
    assert_eq!(delayed.current_tick(), 0, "the timeline starts at zero");
    let mut late = vec![delayed.sample()];
    for _ in 0..B.complete_tick + 2 {
        late.push(delayed.tick());
    }

    assert_eq!(immediate, late, "delayed readiness cannot shorten the wake");
}

/// Every named boundary samples bitwise the authored state crossing into
/// it: tick zero and the closed hold, both blink bottoms, both peek
/// apexes, and the neutral completion.
#[test]
fn named_boundaries_sample_exactly_through_both_blinks() {
    let timeline = WakeTimeline::authored();
    let closed = WakeSample::CLOSED;

    assert_bitwise_equal(
        timeline.sample_at(0),
        closed,
        "tick zero (the readiness sample)",
    );
    assert_bitwise_equal(
        timeline.sample_at(B.first_opening_start),
        closed,
        "the boundary the first opening eases from",
    );
    assert_bitwise_equal(
        timeline.sample_at(B.first_blink_start),
        WakeSample {
            lid_openness: 0.35,
            blur: 0.85,
            exposure_ramp: 0.35,
            sway_offset: Vec2::new(0.012, 0.008),
        },
        "the first peek's widest sample",
    );
    assert_bitwise_equal(
        timeline.sample_at(B.second_opening_start),
        WakeSample {
            lid_openness: 0.0,
            blur: 1.0,
            exposure_ramp: 0.35,
            sway_offset: Vec2::new(0.010, 0.007),
        },
        "the first blink fully shut, smear at peak",
    );
    assert_bitwise_equal(
        timeline.sample_at(B.second_blink_start),
        WakeSample {
            lid_openness: 0.70,
            blur: 0.45,
            exposure_ramp: 0.75,
            sway_offset: Vec2::new(0.010, 0.006),
        },
        "the second peek's widest sample, shapes resolving",
    );
    assert_bitwise_equal(
        timeline.sample_at(B.final_opening_start),
        WakeSample {
            lid_openness: 0.0,
            blur: 0.60,
            exposure_ramp: 0.75,
            sway_offset: Vec2::new(0.008, 0.005),
        },
        "the second blink fully shut, half-resolved blur",
    );
    assert_bitwise_equal(
        timeline.sample_at(B.complete_tick),
        WakeSample::NEUTRAL,
        "the completion tick is neutral",
    );
}

/// Interior ticks ease linearly between their beat's boundary states: the
/// first opening one tick into its 42-tick ease, and the final opening two
/// ticks into its 60-tick ease.
#[test]
fn interior_ticks_ease_linearly_within_their_beat() {
    let timeline = WakeTimeline::authored();
    let one_of_42 = 1.0 / 42.0;
    assert_close(
        timeline.sample_at(B.first_opening_start + 1),
        WakeSample {
            lid_openness: 0.35 * one_of_42,
            blur: 1.0 - (1.0 - 0.85) * one_of_42,
            exposure_ramp: 0.35 * one_of_42,
            sway_offset: Vec2::new(0.012 * one_of_42, 0.008 * one_of_42),
        },
        "first opening, one tick in",
    );
    // The final opening eases from the second blink's bottom toward
    // neutral: two ticks into its sixty-tick ease, progress is 2/60.
    let two_of_60 = 2.0 / 60.0;
    assert_close(
        timeline.sample_at(B.final_opening_start + 2),
        WakeSample {
            lid_openness: WakeSample::NEUTRAL.lid_openness * two_of_60,
            blur: 0.60 * (1.0 - two_of_60),
            exposure_ramp: 0.75 + (1.0 - 0.75) * two_of_60,
            sway_offset: Vec2::new(0.008 * (1.0 - two_of_60), 0.005 * (1.0 - two_of_60)),
        },
        "final opening, two ticks in",
    );
}

/// A sample is a pure function of the logical tick: consuming the same
/// span in uneven bursts lands on exactly the same samples as consuming
/// it one tick at a time.
#[test]
fn sampling_is_independent_of_tick_batching() {
    let one_by_one = ready_run(30);
    let timeline = WakeTimeline::authored();

    // 3 + 7 + 1 + 5 + 2 + 8 + 4 = 30 ticks, consumed in seven bursts.
    let mut bursty = authored_state();
    bursty.mark_ready();
    let mut burst = vec![bursty.sample()];
    for ticks in [3, 7, 1, 5, 2, 8, 4] {
        for _ in 0..ticks {
            burst.push(bursty.tick());
        }
    }
    assert_eq!(burst.len(), 31, "the bursts covered the whole span");
    assert_eq!(
        one_by_one, burst,
        "the burst run matches the one-by-one run"
    );

    // The pure mapping agrees with every consumed step.
    for (tick, &sample) in one_by_one.iter().enumerate() {
        assert_eq!(timeline.sample_at(tick as u64), sample);
    }
}

/// From the completion tick on, the machine rests in the neutral hold:
/// fully open, zero residual blur and sway, the ramp neutral, forever.
#[test]
fn completion_holds_neutral_forever() {
    let mut state = authored_state();
    state.mark_ready();
    for _ in 0..B.complete_tick - 1 {
        state.tick();
    }
    assert!(!state.is_complete(), "the last authored tick is not done");
    state.tick();
    assert_eq!(state.current_tick(), B.complete_tick);
    assert!(state.is_complete());
    assert_bitwise_equal(state.sample(), WakeSample::NEUTRAL, "completion");

    for _ in 0..50 {
        state.tick();
        assert!(state.is_complete());
        assert_bitwise_equal(state.tick(), WakeSample::NEUTRAL, "neutral hold");
    }
}

/// Reset returns the machine to its fresh restartable state, and a
/// second run over the reset machine reproduces the first run bitwise.
#[test]
fn reset_returns_to_a_fresh_restartable_state() {
    let first = ready_run(B.complete_tick + 2);
    let mut state = authored_state();
    state.mark_ready();
    for _ in 0..B.complete_tick + 2 {
        state.tick();
    }
    assert!(state.is_complete());

    state.reset();
    assert!(!state.is_started());
    assert!(!state.is_complete());
    assert_eq!(state.current_tick(), 0);
    assert_bitwise_equal(state.sample(), WakeSample::CLOSED, "reset hold");

    assert_eq!(state.mark_ready(), WakeStart::Started, "reset restarts");
    let mut second = vec![state.sample()];
    for _ in 0..B.complete_tick + 2 {
        second.push(state.tick());
    }
    assert_eq!(first, second, "a reset run reproduces the first");
}

/// Reset works mid-run too: a machine interrupted partway and restarted
/// never carries state across.
#[test]
fn reset_mid_run_restarts_cleanly() {
    let canonical = ready_run(10);
    let mut state = authored_state();
    state.mark_ready();
    for _ in 0..4 {
        state.tick();
    }
    state.reset();
    state.mark_ready();
    let mut restarted = vec![state.sample()];
    for _ in 0..10 {
        restarted.push(state.tick());
    }
    assert_eq!(canonical, restarted);
}

/// The two authored blinks are distinguishable: the first runs 0.45 s and
/// smears fully shut from a narrow peek, the second runs 0.40 s and closes
/// from the wider shapes-resolving opening on half-resolved blur.
#[test]
fn authored_blinks_are_distinguishable() {
    let first_blink = B.second_opening_start - B.first_blink_start;
    let second_blink = B.final_opening_start - B.second_blink_start;
    assert_eq!(first_blink, 27);
    assert_eq!(second_blink, 24);
    assert_ne!(first_blink, second_blink, "the durations differ");

    let timeline = WakeTimeline::authored();
    let first_bottom = timeline.sample_at(B.second_opening_start);
    let second_bottom = timeline.sample_at(B.final_opening_start);
    assert!(
        first_bottom.blur > second_bottom.blur,
        "the first blink smears fully, the second stays half-resolved"
    );
    assert_eq!(first_bottom.blur.to_bits(), 1.0f32.to_bits());
    assert_eq!(second_bottom.blur.to_bits(), 0.60f32.to_bits());

    let first_apex = timeline.sample_at(B.first_blink_start);
    let second_apex = timeline.sample_at(B.second_blink_start);
    assert!(
        first_apex.lid_openness < second_apex.lid_openness,
        "the first peek is narrow, the second resolves shapes"
    );
}

/// The authored table is exactly what the general constructor accepts,
/// and `authored` builds it: the frozen instance cannot drift from the
/// validated path.
#[test]
fn authored_table_is_valid_by_the_general_constructor() {
    let rebuilt = WakeTimeline::try_new(super::AUTHORED_INITIAL, super::authored_beats())
        .expect("the authored table passes its own validation");
    assert_eq!(rebuilt, WakeTimeline::authored());
}

/// The authored boundaries match the frozen table's derived boundaries
/// field for field, start at zero, and ascend to the completion tick.
#[test]
fn authored_boundaries_match_the_authored_table() {
    let timeline = WakeTimeline::authored();
    let starts = timeline.boundaries();
    let named = WakeTimeline::authored_boundaries();

    assert_eq!(starts.len(), 6, "one boundary per authored beat");
    assert_eq!(starts.first().copied(), Some(0));
    assert_eq!(
        named,
        AuthoredBoundaries {
            first_opening_start: starts[1],
            first_blink_start: starts[2],
            second_opening_start: starts[3],
            second_blink_start: starts[4],
            final_opening_start: starts[5],
            complete_tick: timeline.complete_tick(),
        }
    );
    assert_eq!(named, B, "the authored boundaries are the frozen numbers");
    for pair in starts.windows(2) {
        assert!(pair[0] < pair[1], "boundaries ascend: {starts:?}");
    }
    assert_eq!(*starts.last().expect("six beats"), B.final_opening_start);
}

/// Malformed scalar authoring is rejected with its typed error, naming
/// the location and the offending value.
#[test]
fn malformed_scalars_are_rejected_with_typed_errors() {
    let mut initial = WakeSample::CLOSED;
    initial.blur = f32::NAN;
    // NaN never equals itself, so the rejection is matched structurally.
    assert!(matches!(
        WakeTimeline::try_new(initial, super::authored_beats()),
        Err(WakeTimelineError::NonFiniteValue {
            at: WakeAuthoring::Initial,
            field: WakeField::Blur,
            ..
        })
    ));

    let mut initial = WakeSample::CLOSED;
    initial.exposure_ramp = f32::INFINITY;
    assert_eq!(
        WakeTimeline::try_new(initial, super::authored_beats()),
        Err(WakeTimelineError::NonFiniteValue {
            at: WakeAuthoring::Initial,
            field: WakeField::ExposureRamp,
            got: f32::INFINITY,
        })
    );

    let mut beats = super::authored_beats();
    beats[1].end.exposure_ramp = 1.5;
    assert_eq!(
        WakeTimeline::try_new(WakeSample::CLOSED, beats),
        Err(WakeTimelineError::ValueOutOfRange {
            at: WakeAuthoring::BeatEnd(1),
            field: WakeField::ExposureRamp,
            got: 1.5,
        })
    );

    let mut beats = super::authored_beats();
    beats[4].end.sway_offset = Vec2::new(SWAY_OFFSET_MAX_RADIANS * 2.0, 0.0);
    let too_large = WakeTimeline::try_new(WakeSample::CLOSED, beats);
    assert!(matches!(
        too_large,
        Err(WakeTimelineError::SwayOffsetTooLarge {
            at: WakeAuthoring::BeatEnd(4),
            ..
        })
    ));
}

/// Malformed timeline structure is rejected: no beats, a zero-tick beat,
/// a non-closed initial state, and a landing off the neutral hold.
#[test]
fn malformed_structure_is_rejected_with_typed_errors() {
    assert_eq!(
        WakeTimeline::try_new(WakeSample::CLOSED, Vec::new()),
        Err(WakeTimelineError::NoBeats)
    );

    let mut beats = super::authored_beats();
    beats[3].ticks = 0;
    assert_eq!(
        WakeTimeline::try_new(WakeSample::CLOSED, beats),
        Err(WakeTimelineError::ZeroDurationBeat { index: 3 })
    );

    let mut initial = WakeSample::CLOSED;
    initial.lid_openness = 0.5;
    assert_eq!(
        WakeTimeline::try_new(initial, super::authored_beats()),
        Err(WakeTimelineError::InitialNotClosed { got: 0.5 })
    );

    let mut beats = super::authored_beats();
    beats[5].end.blur = 0.25;
    assert_eq!(
        WakeTimeline::try_new(WakeSample::CLOSED, beats),
        Err(WakeTimelineError::FinalNotNeutral {
            got: WakeSample {
                lid_openness: 1.0,
                blur: 0.25,
                exposure_ramp: 1.0,
                sway_offset: Vec2::ZERO,
            },
        })
    );
}

/// Rejection text names the location and the offending value, so a bad
/// authoring edit fails with something readable.
#[test]
fn rejections_display_their_location_and_value() {
    let mut beats = super::authored_beats();
    beats[2].end.blur = -0.1;
    let error = WakeTimeline::try_new(WakeSample::CLOSED, beats)
        .expect_err("a negative blur must be rejected");
    let text = error.to_string();
    assert!(text.contains("beat 2's end state"), "display: {text}");
    assert!(text.contains("-0.1"), "display: {text}");

    let mut initial = WakeSample::CLOSED;
    initial.lid_openness = 0.2;
    let error = WakeTimeline::try_new(initial, super::authored_beats())
        .expect_err("a non-closed initial state must be rejected");
    let text = error.to_string();
    assert!(text.contains("not fully closed"), "display: {text}");
    assert!(text.contains("0.2"), "display: {text}");
}

/// The duration table: the authored milliseconds encode at the logical rate
/// to the frozen tick counts, the completion tick is their sum, and the
/// rate is the production logical clock's.
#[test]
fn authored_durations_sum_to_the_frozen_boundaries() {
    assert_eq!(LOGICAL_TICKS_PER_SECOND, 60);
    let ticks: Vec<u16> = super::authored_beats()
        .iter()
        .map(|beat| beat.ticks)
        .collect();
    assert_eq!(ticks, vec![75, 42, 27, 54, 24, 60]);
    for (&millis, &encoded) in AUTHORED_BEAT_MILLIS.iter().zip(&ticks) {
        assert_eq!(
            ticks_for(millis),
            encoded,
            "authored {millis} ms must encode to its documented tick count"
        );
    }
    let total: u64 = ticks.iter().copied().map(u64::from).sum();
    assert_eq!(total, B.complete_tick);
    assert_eq!(WakeTimeline::authored().complete_tick(), B.complete_tick);
    // The authored wall-clock total is the sum of the milliseconds table:
    // 4700 ms, the 4.70 s the opening beat is written to.
    let total_millis: u64 = AUTHORED_BEAT_MILLIS.iter().sum();
    assert_eq!(total_millis, 4700, "authored total in milliseconds");
}

/// A duration that cannot fill one logical tick encodes to zero ticks and
/// fails construction loudly: there is no clamp-to-one fallback.
#[test]
#[should_panic(expected = "encodes to zero ticks")]
fn a_duration_shorter_than_half_a_tick_fails_explicitly() {
    // 8 ms at 60 Hz is 0.48 ticks: it cannot carry a boundary.
    let _ = ticks_for(8);
}

/// The seconds-per-tick constant is exactly one over the tick rate,
/// computed through the lossless `f32::From<u16>` conversion. The constant
/// itself is a literal because `f32::From` is not const-callable yet; this
/// test is the pin that keeps the pair from drifting. Both sides run the
/// identical IEEE-754 division (1.0 by the tick rate), whose result is
/// fully determined by the operands, so the pin is compared bit for bit.
#[test]
fn the_tick_secs_constant_is_one_over_the_tick_rate() {
    assert_eq!(
        LOGICAL_TICK_SECS.to_bits(),
        (1.0 / f32::from(LOGICAL_TICKS_PER_SECOND)).to_bits()
    );
}

/// A duration encoding past a beat's `u16` width fails construction loudly:
/// there is no clamp-to-max fallback (long holds are chained beats).
#[test]
#[should_panic(expected = "above a beat's 65535 tick width")]
fn a_duration_wider_than_a_beat_fails_explicitly() {
    // 2,000,000 ms at 60 Hz encodes to 120,000 ticks: chain beats instead.
    let _ = ticks_for(2_000_000);
}

/// A beat authored to end exactly neutral is accepted even when earlier
/// beats carry the wake's dynamics: validation constrains the landing,
/// not the arc.
#[test]
fn a_two_beat_timeline_with_a_neutral_landing_is_valid() {
    let timeline = WakeTimeline::try_new(
        WakeSample::CLOSED,
        vec![WakeBeat {
            ticks: 1,
            end: WakeSample {
                lid_openness: 0.5,
                blur: 0.5,
                exposure_ramp: 0.5,
                sway_offset: Vec2::new(0.01, 0.0),
            },
        }],
    )
    .expect_err("one beat cannot both move and land neutral");
    assert!(
        matches!(timeline, WakeTimelineError::FinalNotNeutral { .. }),
        "the single beat's end is not neutral"
    );

    let timeline = WakeTimeline::try_new(
        WakeSample::CLOSED,
        vec![
            WakeBeat {
                ticks: 1,
                end: WakeSample {
                    lid_openness: 0.5,
                    blur: 0.5,
                    exposure_ramp: 0.5,
                    sway_offset: Vec2::new(0.01, 0.0),
                },
            },
            WakeBeat {
                ticks: 1,
                end: WakeSample::NEUTRAL,
            },
        ],
    )
    .expect("the landing beat is exactly neutral");
    assert_eq!(timeline.complete_tick(), 2);
    assert_eq!(timeline.boundaries(), &[0, 1]);
    assert_bitwise_equal(timeline.sample_at(2), WakeSample::NEUTRAL, "landed");
}
