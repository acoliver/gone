//! The authored eyelid wake timeline (issue #8, sim slice).
//!
//! The story beat: the player's eyes open in stages — the first blink is a
//! smear of light and blur, the second resolves shapes, and then the eye
//! holds open and the room is theirs to look at. This module owns the
//! simulation side of that beat as pure, validated data plus a
//! deterministic sampler:
//!
//! * [`WakeTimeline`] authors the sequence as a table of beats — eyes
//!   closed, first opening, first blink, second opening, second blink,
//!   final opening — each with an explicit duration authored in
//!   milliseconds ([`AUTHORED_BEAT_MILLIS`]) and encoded once to logical
//!   ticks at the documented [`LOGICAL_TICKS_PER_SECOND`], plus an
//!   explicit end state.
//!   [`WakeTimeline::authored`] is the canonical
//!   opening-beat instance; [`WakeTimeline::try_new`] is the validated
//!   general constructor, and it rejects malformed authoring instead of
//!   clamping or falling back: a timeline that fails validation does not
//!   exist.
//! * [`WakeState`] drives the timeline behind the readiness contract the
//!   app's asset barrier imposes: the sample holds fully closed until
//!   readiness is marked, readiness starts the timeline exactly once, the
//!   first ready sample is the fully closed tick zero, completion lands
//!   deterministically at the authored tick count, every later sample is
//!   the neutral hold, and [`WakeState::reset`] returns the machine to its
//!   fresh, restartable state.
//! * [`AuthoredBoundaries`] names the authored timeline's tick boundaries —
//!   where each blink begins, where the final opening starts, when the
//!   wake completes — so the harness's temporal captures (short timestamped
//!   frame sequences covering before/during/after) and the app's post-pass
//!   consumers pin ticks from named values, never from literals.
//!
//! # Sample contract (documented and frozen)
//!
//! One sample is four numbers a post-pass or camera consumer reads:
//! normalized lid openness (0 shut, 1 open), normalized blur (0 sharp, 1
//! fully smeared), the authored exposure ramp (0 the authored floor, 1
//! neutral), and a small camera sway offset in radians. Every sample is a
//! pure function of the logical tick: [`WakeTimeline::sample_at`] walks the
//! beat table and eases linearly from each beat's start state (the
//! previous beat's end state) to its end state, so batching ticks
//! differently can never change a sample — only how many ticks were
//! consumed. The sample at a boundary tick is exactly the state crossing
//! into that boundary's beat, computed with no accumulated float error:
//! the interpolation progress is a single division by the beat's tick
//! duration, never a running sum.
//!
//! After the last beat's end boundary the wake is complete, and the
//! neutral hold is structural, not authored: openness 1, blur 0, the ramp
//! neutral, no sway, forever. Validation requires the last authored beat
//! to land on exactly that state, so the tail is continuous with the
//! table by construction.
//!
//! # What is not here
//!
//! The phase machine ([`crate::WakePhase`]) is untouched: delivering
//! `wake_complete` at the completion boundary is the app integration's
//! decision, behind the app's own readiness barrier. There is no wall
//! clock, no render frame, no dt, and no Bevy here; a tick is a tick.
//!
//! Units: openness, blur, and the ramp are normalized [0, 1]; sway offsets
//! are radians about the authored camera pose. Pure: no Bevy, no clocks,
//! no RNG.

use glam::Vec2;

/// The game's logical tick rate, in ticks per second: the fixed clock every
/// tick-driven system runs on. The harness scenario clock's default
/// (`gone_app::harness::scenario::TICKS_PER_SECOND`) is the same number, and
/// a `gone_app` test pins the two against each other, so an authored wake
/// duration plays at its authored wall pace on every lane that runs the
/// production driver. The width keeps every seconds conversion lossless:
/// `f32::From` exists for `u16` and a 60 Hz rate cannot lose precision
/// through it.
pub const LOGICAL_TICKS_PER_SECOND: u16 = 60;

/// One logical tick's duration in seconds: the fixed step the production
/// driver accumulates real seconds against in the normal game (harness
/// lanes drive whole ticks and never need it). Authored as the literal
/// division because `f32::From` is not const-callable yet; the wake tests
/// pin this constant to [`LOGICAL_TICKS_PER_SECOND`] through the lossless
/// `f32::From<u16>` conversion, so the two cannot drift apart.
pub const LOGICAL_TICK_SECS: f32 = 1.0 / 60.0;

/// The largest sway offset magnitude a validated timeline may author, in
/// radians. The authored table peaks far below this; the bound exists so
/// malformed authoring fails construction instead of handing the camera a
/// violent offset.
pub const SWAY_OFFSET_MAX_RADIANS: f32 = 0.05;

/// Convert an authored duration in milliseconds to its logical tick count
/// at [`LOGICAL_TICKS_PER_SECOND`], rounded to the nearest whole tick in
/// exact integer arithmetic. This is the only duration-to-ticks conversion
/// in the module: the authored beat table stores milliseconds and calls
/// this, so the timeline's production pacing is authored in wall units and
/// encoded once, never hand-counted in frames. An authored duration that
/// overflows the conversion, or that encodes outside a beat's
/// 1..=[`u16::MAX`] tick width, fails construction loudly: there is no
/// clamping fallback for malformed authoring.
///
/// # Panics
/// For an authored duration that cannot encode: overflow in the scaled
/// milliseconds-to-ticks arithmetic, a result above a beat's `u16::MAX`
/// tick width, or one that rounds to zero ticks (shorter than half a
/// logical tick, so it could never carry a boundary).
#[must_use]
fn ticks_for(millis: u64) -> u16 {
    let scaled = millis
        .checked_mul(u64::from(LOGICAL_TICKS_PER_SECOND))
        .and_then(|scaled| scaled.checked_add(500))
        .expect("an authored wake duration must not overflow the tick conversion");
    // Nearest-tick rounding in exact integers: the 500 added above is half
    // a tick in milliseconds, so a half tick rounds up into the beat that
    // carries it.
    let ticks = scaled / 1000;
    let ticks = u16::try_from(ticks).unwrap_or_else(|_| {
        panic!(
            "an authored wake duration encodes to {ticks} ticks: above a beat's {max} tick width",
            max = u16::MAX
        )
    });
    assert!(
        ticks >= 1,
        "an authored wake duration encodes to zero ticks: shorter than half a logical tick"
    );
    ticks
}

/// One sampled moment of the wake timeline: the four values the post pass
/// and camera consumers read.
///
/// Plain data: construction is authoring, and validation happens where the
/// authoring is consumed ([`WakeTimeline::try_new`]).
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct WakeSample {
    /// Normalized lid openness: 0 fully shut, 1 fully open.
    pub lid_openness: f32,
    /// Normalized blur: 0 sharp, 1 fully smeared.
    pub blur: f32,
    /// The authored exposure ramp: 0 the authored floor (the pass darkens
    /// fully), 1 neutral (no authored adjustment).
    pub exposure_ramp: f32,
    /// Small camera sway offset in radians as `(yaw, pitch)` about the
    /// authored pose. Zero once the wake is complete.
    pub sway_offset: Vec2,
}

impl WakeSample {
    /// The neutral hold: fully open, sharp, ramp neutral, no sway. The
    /// sample every completed wake returns, and the state the last
    /// authored beat must land on exactly.
    pub const NEUTRAL: Self = Self {
        lid_openness: 1.0,
        blur: 0.0,
        exposure_ramp: 1.0,
        sway_offset: Vec2::ZERO,
    };

    /// The fully closed, fully smeared, dark rest state the timeline holds
    /// before readiness and starts from at tick zero.
    pub const CLOSED: Self = Self {
        lid_openness: 0.0,
        blur: 1.0,
        exposure_ramp: 0.0,
        sway_offset: Vec2::ZERO,
    };

    /// Ease linearly from `from` to `to` by `progress` in `[0, 1]`. At
    /// zero the result is `from` bitwise: the boundary ticks must sample
    /// exactly the authored boundary states, with no interpolation error.
    fn lerp(from: Self, to: Self, progress: f32) -> Self {
        Self {
            lid_openness: from.lid_openness + (to.lid_openness - from.lid_openness) * progress,
            blur: from.blur + (to.blur - from.blur) * progress,
            exposure_ramp: from.exposure_ramp + (to.exposure_ramp - from.exposure_ramp) * progress,
            sway_offset: from.sway_offset + (to.sway_offset - from.sway_offset) * progress,
        }
    }
}

/// One authored beat: an explicit duration in logical ticks and the sample
/// state the beat eases toward at its end boundary. The state the beat
/// eases from is the previous beat's end state, or the timeline's initial
/// state for the first beat.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct WakeBeat {
    /// The beat's duration in logical ticks. Strictly positive: a beat
    /// with no ticks cannot hold a boundary. The width is deliberate:
    /// `u16` converts to the sampler's f32 progress arithmetic losslessly,
    /// and a single beat of 65,535 logical ticks is far past any authored
    /// beat; longer holds are chained beats.
    pub ticks: u16,
    /// The sample state at the beat's end boundary.
    pub end: WakeSample,
}

/// Which authored field an error names.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum WakeField {
    /// Normalized lid openness.
    LidOpenness,
    /// Normalized blur.
    Blur,
    /// The authored exposure ramp.
    ExposureRamp,
    /// The sway offset (either component or the vector's magnitude).
    SwayOffset,
}

/// Where an authored sample sits in the timeline, for error reporting.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum WakeAuthoring {
    /// The timeline's initial state: the sample before readiness and at
    /// tick zero.
    Initial,
    /// The end state of the beat at this table index.
    BeatEnd(usize),
}

impl std::fmt::Display for WakeAuthoring {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Initial => write!(f, "the initial state"),
            Self::BeatEnd(index) => write!(f, "beat {index}'s end state"),
        }
    }
}

/// A rejected wake-timeline construction. Validation is fail-loud: every
/// rejected construction leaves nothing behind to sample.
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum WakeTimelineError {
    /// The timeline carried no beats: it could never complete.
    NoBeats,
    /// The beat at this index authored a zero-tick duration.
    ZeroDurationBeat {
        /// The offending beat's table index.
        index: usize,
    },
    /// An authored sample carried a non-finite value, which would poison
    /// every interpolation downstream.
    NonFiniteValue {
        /// Where the sample sits in the timeline.
        at: WakeAuthoring,
        /// The offending field.
        field: WakeField,
        /// The offending value.
        got: f32,
    },
    /// An authored scalar sat outside the normalized [0, 1] range its
    /// field documents.
    ValueOutOfRange {
        /// Where the sample sits in the timeline.
        at: WakeAuthoring,
        /// The offending field.
        field: WakeField,
        /// The offending value.
        got: f32,
    },
    /// An authored sway offset exceeded [`SWAY_OFFSET_MAX_RADIANS`]: not
    /// the small steadying motion the field documents.
    SwayOffsetTooLarge {
        /// Where the sample sits in the timeline.
        at: WakeAuthoring,
        /// The offending offset magnitude.
        got: f32,
        /// The largest magnitude validation accepts.
        max: f32,
    },
    /// The initial state was not fully closed: the tick-zero sample the
    /// readiness contract promises is the closed rest state.
    InitialNotClosed {
        /// The authored initial openness.
        got: f32,
    },
    /// The last beat's end state was not exactly the neutral hold, so the
    /// structural completion tail would discontinuously jump.
    FinalNotNeutral {
        /// The authored final state.
        got: WakeSample,
    },
}

impl std::fmt::Display for WakeTimelineError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::NoBeats => write!(f, "a wake timeline needs at least one beat"),
            Self::ZeroDurationBeat { index } => {
                write!(f, "wake beat {index} authored a zero-tick duration")
            }
            Self::NonFiniteValue { at, field, got } => {
                write!(
                    f,
                    "wake timeline {at} carried a non-finite {field:?}: {got}"
                )
            }
            Self::ValueOutOfRange { at, field, got } => write!(
                f,
                "wake timeline {at} carried {field:?} value {got} outside [0, 1]"
            ),
            Self::SwayOffsetTooLarge { at, got, max } => write!(
                f,
                "wake timeline {at} authored sway offset magnitude {got}, \
                 above the {max} rad small-motion bound"
            ),
            Self::InitialNotClosed { got } => write!(
                f,
                "wake timeline initial openness {got} is not fully closed: \
                 the tick-zero sample must be the closed rest state"
            ),
            Self::FinalNotNeutral { got } => {
                write!(
                    f,
                    "wake timeline's last beat must end exactly neutral, got {got:?}"
                )
            }
        }
    }
}

impl std::error::Error for WakeTimelineError {}

/// The named tick boundaries of the authored timeline: the ticks the
/// harness's temporal captures and the app's consumers pin, derived from
/// the same frozen table the sampler walks.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct AuthoredBoundaries {
    /// First tick of the first opening (the boundary the opening eases
    /// from; the eye begins parting on the ticks after it).
    pub first_opening_start: u64,
    /// First tick of the first blink's closing stroke; the first opening's
    /// widest sample sits exactly here.
    pub first_blink_start: u64,
    /// First tick of the second opening, whose ease resolves shapes.
    pub second_opening_start: u64,
    /// First tick of the second blink's closing stroke; the second
    /// opening's widest sample sits exactly here.
    pub second_blink_start: u64,
    /// First tick of the final opening to the neutral hold.
    pub final_opening_start: u64,
    /// First fully complete tick: from here on the sample is the neutral
    /// hold and [`WakeState::is_complete`] is true.
    pub complete_tick: u64,
}

/// The authored timeline's initial state: the closed rest state the
/// timeline holds before readiness and samples at tick zero.
const AUTHORED_INITIAL: WakeSample = WakeSample::CLOSED;

/// The authored beat durations, in explicit milliseconds: the production
/// timing of the opening beat. Encoded to logical ticks by [`ticks_for`] at
/// the documented [`LOGICAL_TICKS_PER_SECOND`], one entry per authored
/// beat, in walk order. The arc: a closed hold long enough for the
/// readiness barrier to open inside it, a drowsy first opening to a narrow
/// smear, the first blink shut, a wider second opening with shapes
/// resolving, the shorter second blink, and the final opening to the
/// neutral hold. Total: 4700 ms (4.70 s), 282 logical ticks.
const AUTHORED_BEAT_MILLIS: [u64; 6] = [1250, 700, 450, 900, 400, 1000];

/// The authored beat table, in walk order, with end states matching
/// [`AUTHORED_BEAT_MILLIS`] one-to-one. Ticks come from the milliseconds
/// table; only the eased-toward sample states are hand-authored here. The
/// two blinks differ in duration (450 ms against 400 ms) and in their value
/// arcs, so a temporal capture can tell them apart.
fn authored_beats() -> Vec<WakeBeat> {
    vec![
        // The closed hold the readiness contract starts from.
        WakeBeat {
            ticks: ticks_for(AUTHORED_BEAT_MILLIS[0]),
            end: WakeSample::CLOSED,
        },
        // First opening: a narrow peek through heavy smear, the ramp lifting
        // off its floor.
        WakeBeat {
            ticks: ticks_for(AUTHORED_BEAT_MILLIS[1]),
            end: WakeSample {
                lid_openness: 0.35,
                blur: 0.85,
                exposure_ramp: 0.35,
                sway_offset: Vec2::new(0.012, 0.008),
            },
        },
        // First blink: back to fully shut, the light smear at its peak.
        WakeBeat {
            ticks: ticks_for(AUTHORED_BEAT_MILLIS[2]),
            end: WakeSample {
                lid_openness: 0.0,
                blur: 1.0,
                exposure_ramp: 0.35,
                sway_offset: Vec2::new(0.010, 0.007),
            },
        },
        // Second opening: wider, blur falling toward shapes resolving, the
        // ramp most of the way up.
        WakeBeat {
            ticks: ticks_for(AUTHORED_BEAT_MILLIS[3]),
            end: WakeSample {
                lid_openness: 0.70,
                blur: 0.45,
                exposure_ramp: 0.75,
                sway_offset: Vec2::new(0.010, 0.006),
            },
        },
        // Second blink: the shorter close, on half-resolved blur.
        WakeBeat {
            ticks: ticks_for(AUTHORED_BEAT_MILLIS[4]),
            end: WakeSample {
                lid_openness: 0.0,
                blur: 0.60,
                exposure_ramp: 0.75,
                sway_offset: Vec2::new(0.008, 0.005),
            },
        },
        // Final opening: fully open, sharp, neutral ramp, sway spent.
        WakeBeat {
            ticks: ticks_for(AUTHORED_BEAT_MILLIS[5]),
            end: WakeSample::NEUTRAL,
        },
    ]
}

/// The validated wake timeline: an initial state plus a beat table with
/// cumulative boundaries.
///
/// Built only through [`WakeTimeline::try_new`], which validates the
/// authoring, or [`WakeTimeline::authored`], the canonical opening-beat
/// instance. The stored table is the whole sampling truth: boundaries are
/// derived once at construction, so sampling never re-sums durations.
#[derive(Clone, Debug, PartialEq)]
pub struct WakeTimeline {
    initial: WakeSample,
    beats: Vec<WakeBeat>,
    beat_starts: Vec<u64>,
    complete_tick: u64,
}

impl WakeTimeline {
    /// The canonical opening-beat timeline: the closed rest hold, the
    /// first opening to a narrow smear of light, the first blink shut, the
    /// second opening wider with shapes resolving, the second blink shut,
    /// and the final opening to the neutral hold. The first blink runs
    /// three ticks and smears fully shut; the second runs two and closes
    /// on half-resolved blur, so the two blinks are distinguishable in
    /// both duration and value arc.
    #[must_use]
    pub fn authored() -> Self {
        Self::build(AUTHORED_INITIAL, authored_beats())
    }

    /// Author a timeline over an explicit initial state and beat table.
    ///
    /// # Errors
    /// [`WakeTimelineError::NoBeats`] for an empty table,
    /// [`WakeTimelineError::ZeroDurationBeat`] for a zero-tick beat,
    /// [`WakeTimelineError::NonFiniteValue`] and
    /// [`WakeTimelineError::ValueOutOfRange`] for malformed sample fields,
    /// [`WakeTimelineError::SwayOffsetTooLarge`] for a sway offset past
    /// [`SWAY_OFFSET_MAX_RADIANS`], [`WakeTimelineError::InitialNotClosed`]
    /// when the initial state is not fully shut, and
    /// [`WakeTimelineError::FinalNotNeutral`] when the last beat does not
    /// land exactly on the neutral hold.
    pub fn try_new(initial: WakeSample, beats: Vec<WakeBeat>) -> Result<Self, WakeTimelineError> {
        if beats.is_empty() {
            return Err(WakeTimelineError::NoBeats);
        }
        validate_sample(initial, WakeAuthoring::Initial)?;
        if initial.lid_openness != 0.0 {
            return Err(WakeTimelineError::InitialNotClosed {
                got: initial.lid_openness,
            });
        }
        for (index, beat) in beats.iter().enumerate() {
            if beat.ticks == 0 {
                return Err(WakeTimelineError::ZeroDurationBeat { index });
            }
            validate_sample(beat.end, WakeAuthoring::BeatEnd(index))?;
        }
        if let Some(end) = beats
            .last()
            .map(|beat| beat.end)
            .filter(|end| *end != WakeSample::NEUTRAL)
        {
            return Err(WakeTimelineError::FinalNotNeutral { got: end });
        }
        Ok(Self::build(initial, beats))
    }

    /// Build without re-validating: the caller has checked the table (the
    /// authored table by tests over `try_new`, general callers by
    /// `try_new` itself).
    fn build(initial: WakeSample, beats: Vec<WakeBeat>) -> Self {
        let mut beat_starts = Vec::with_capacity(beats.len());
        let mut complete_tick = 0u64;
        for beat in &beats {
            beat_starts.push(complete_tick);
            complete_tick += u64::from(beat.ticks);
        }
        Self {
            initial,
            beats,
            beat_starts,
            complete_tick,
        }
    }

    /// The beat table's start ticks, ascending, one per beat. The first is
    /// always 0; the completion tick is the first tick past the last.
    #[must_use]
    pub fn boundaries(&self) -> &[u64] {
        &self.beat_starts
    }

    /// The first fully complete tick: the first tick past the last beat.
    #[must_use]
    pub fn complete_tick(&self) -> u64 {
        self.complete_tick
    }

    /// The named boundaries of the authored timeline, for temporal capture
    /// and consumer pinning. The authored table's six beats pin the
    /// indexes; tests over [`WakeTimeline::authored`] assert the values
    /// against [`AuthoredBoundaries`] field for field.
    #[must_use]
    pub fn authored_boundaries() -> AuthoredBoundaries {
        let timeline = Self::authored();
        let starts = &timeline.beat_starts;
        AuthoredBoundaries {
            first_opening_start: starts[1],
            first_blink_start: starts[2],
            second_opening_start: starts[3],
            second_blink_start: starts[4],
            final_opening_start: starts[5],
            complete_tick: timeline.complete_tick,
        }
    }

    /// The sample at logical tick `tick`: the held initial state before
    /// and at the timeline's start, the eased beat state through the
    /// table, and the neutral hold from the completion tick on. A pure
    /// function of the tick: no accumulated state, so any batching of
    /// ticks produces the same sample.
    #[must_use]
    pub fn sample_at(&self, tick: u64) -> WakeSample {
        if tick >= self.complete_tick {
            return WakeSample::NEUTRAL;
        }
        let index = self.beat_index_for(tick);
        let start = self.beat_starts[index];
        let beat = self.beats[index];
        let from = if index == 0 {
            self.initial
        } else {
            self.beats[index - 1].end
        };
        // The enclosing branch bounds `tick - start` below the beat's own
        // u16 duration, so the conversion cannot fail; the fallback is the
        // workspace's tick-to-f32 convention (never reached here).
        let offset = u16::try_from(tick - start).unwrap_or(u16::MAX);
        let progress = f32::from(offset) / f32::from(beat.ticks);
        WakeSample::lerp(from, beat.end, progress)
    }

    /// The index of the beat whose tick range covers `tick`. `tick` is
    /// strictly below the completion tick here, so the scan always lands.
    fn beat_index_for(&self, tick: u64) -> usize {
        let mut index = 0;
        for (candidate, &start) in self.beat_starts.iter().enumerate() {
            if start > tick {
                break;
            }
            index = candidate;
        }
        index
    }
}

/// Validate one authored sample: every scalar finite and in [0, 1], the
/// sway offset finite and within the small-motion bound.
fn validate_sample(sample: WakeSample, at: WakeAuthoring) -> Result<(), WakeTimelineError> {
    check_ranged(sample.lid_openness, WakeField::LidOpenness, at)?;
    check_ranged(sample.blur, WakeField::Blur, at)?;
    check_ranged(sample.exposure_ramp, WakeField::ExposureRamp, at)?;
    if !sample.sway_offset.x.is_finite() || !sample.sway_offset.y.is_finite() {
        return Err(WakeTimelineError::NonFiniteValue {
            at,
            field: WakeField::SwayOffset,
            got: sample.sway_offset.x + sample.sway_offset.y,
        });
    }
    let magnitude = sample.sway_offset.length();
    if magnitude > SWAY_OFFSET_MAX_RADIANS {
        return Err(WakeTimelineError::SwayOffsetTooLarge {
            at,
            got: magnitude,
            max: SWAY_OFFSET_MAX_RADIANS,
        });
    }
    Ok(())
}

/// Check one authored scalar: finite, then within the normalized [0, 1]
/// range its field documents.
fn check_ranged(value: f32, field: WakeField, at: WakeAuthoring) -> Result<(), WakeTimelineError> {
    if !value.is_finite() {
        return Err(WakeTimelineError::NonFiniteValue {
            at,
            field,
            got: value,
        });
    }
    if !(0.0..=1.0).contains(&value) {
        return Err(WakeTimelineError::ValueOutOfRange {
            at,
            field,
            got: value,
        });
    }
    Ok(())
}

/// What one readiness poll did to the wake machine.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum WakeStart {
    /// The timeline started: tick zero is now, holding fully closed.
    Started,
    /// The timeline had already started; the poll changed nothing, exactly
    /// like a re-delivered phase boundary signal.
    AlreadyStarted,
}

/// The tick-driven wake machine over one [`WakeTimeline`]: holds closed
/// until readiness, runs the table one logical tick per
/// [`WakeState::tick`], and rests in the neutral hold from completion on.
///
/// Before readiness the machine consumes nothing: ticks arrive, the
/// sample holds fully closed, and the tick counter stays at zero, so a
/// readiness barrier that opens late cannot shorten the authored
/// sequence. Readiness starts the timeline exactly once; duplicate polls
/// are the no-op [`WakeStart::AlreadyStarted`]. [`WakeState::reset`]
/// returns the machine to its fresh, restartable state at any point.
#[derive(Clone, Debug, PartialEq)]
pub struct WakeState {
    timeline: WakeTimeline,
    tick: u64,
    started: bool,
}

impl WakeState {
    /// A wake machine over `timeline`, holding fully closed until
    /// readiness is marked.
    #[must_use]
    pub fn new(timeline: WakeTimeline) -> Self {
        Self {
            timeline,
            tick: 0,
            started: false,
        }
    }

    /// Mark the readiness barrier open. The first poll starts the
    /// timeline at tick zero (whose sample is the fully closed rest
    /// state); every later poll returns [`WakeStart::AlreadyStarted`] and
    /// changes nothing.
    pub fn mark_ready(&mut self) -> WakeStart {
        if self.started {
            return WakeStart::AlreadyStarted;
        }
        self.started = true;
        WakeStart::Started
    }

    /// Whether the timeline has started.
    #[must_use]
    pub fn is_started(&self) -> bool {
        self.started
    }

    /// The current logical tick: zero until readiness starts the
    /// timeline, one per [`WakeState::tick`] after.
    #[must_use]
    pub fn current_tick(&self) -> u64 {
        self.tick
    }

    /// Whether the timeline has reached its completion tick.
    #[must_use]
    pub fn is_complete(&self) -> bool {
        self.started && self.tick >= self.timeline.complete_tick
    }

    /// The sample at the current logical tick, without advancing.
    #[must_use]
    pub fn sample(&self) -> WakeSample {
        self.timeline.sample_at(self.tick)
    }

    /// Consume one logical tick. Before readiness this consumes nothing:
    /// the sample holds fully closed and the counter stays at zero, the
    /// documented pre-ready hold. After readiness the counter advances by
    /// exactly one and the returned sample is the new tick's; after
    /// completion every tick samples the neutral hold.
    pub fn tick(&mut self) -> WakeSample {
        if self.started {
            self.tick += 1;
        }
        self.sample()
    }

    /// Return the machine to its fresh state: not started, tick zero,
    /// holding fully closed, restartable. The timeline data is kept.
    pub fn reset(&mut self) {
        self.tick = 0;
        self.started = false;
    }
}

#[cfg(test)]
mod tests;
