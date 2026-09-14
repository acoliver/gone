//! Gameplay-lane runner tooling: the built-in gameplay smoke scenario and the
//! machine verification over a gameplay run's report.
//!
//! The gameplay lane boots the real game (stasis room, player rig with
//! first-person look, post chain) instead of the calibration scene, so its
//! verification goes beyond the capture-lane checks: the report must carry a
//! room observation matching the registry's count, and the rig's yaw samples
//! must show exactly the scripted look delta between the pinned beats that
//! sit at or after the wake handoff. This is
//! the negative proof the lane exists for: a report from a run whose player
//! systems never integrated scripted look (stale or missing yaw samples)
//! fails here, as does a run whose scene failed to build its pods.
//!
//! The lane's scenario schedule is derived, never measured: the production
//! wake driver plays the authored timeline 1:1 on the scenario clock (the
//! app's gameplay proof gate waits on the driver's own readiness legs), so
//! the `Waking -> AwakeInPod` handoff lands on the update that drives
//! scenario tick [`wake_handoff_tick`], and every authored input is scheduled
//! after it. The `full` submodule is the gameplay-full lane: the built-in
//! scenario that plays the whole opening beat (wake, get-up, turn, walk to
//! the hatch) and the position and phase-sequence verification over its
//! report.

use gone_app::gone_sim::WakeTimeline;
use gone_app::harness::report::{Report, TimedEvent};
use gone_app::harness::scenario::TICKS_PER_SECOND;
use gone_app::harness::{Action, Beat, Content, Scenario, ScenarioMode, ScriptedAction};

mod full;

pub use full::{GAMEPLAY_FULL_SCENARIO_NAME, gameplay_full_scenario, verify_gameplay_full};

/// The driven scenario tick on whose update the production wake driver hands
/// `Waking -> AwakeInPod`. The gameplay lane paces the driver's logical clock
/// 1:1 with the scenario clock — the machine consumes its first logical tick
/// on driven tick zero and sits at logical tick `k + 1` once scenario tick
/// `k` has driven — so the timeline's completion tick
/// ([`WakeTimeline::complete_tick`]) is consumed on the update that drives
/// this scenario tick, and every later tick's update runs wholly inside
/// `AwakeInPod`, input included. Derived from the authored timeline itself
/// (its beat table is heap data, so this is a call, not a const), never from
/// a measured run.
#[must_use]
pub fn wake_handoff_tick() -> u64 {
    WakeTimeline::authored().complete_tick() - 1
}

/// One temporal wake beat: pins the authored wake timeline's `wake_tick`
/// sample. The pin is post-tick state — the update that drove scenario tick
/// `wake_tick - 1` left the machine at logical tick `wake_tick`, and the
/// frame it renders shows exactly that tick's authored sample — so the
/// scenario tick is one below the named wake tick.
fn wake_beat(name: &str, wake_tick: u64) -> Beat {
    Beat::new(name, wake_tick - 1)
}

/// How far the sampled yaw may drift from the scripted replay, in degrees.
/// The app integrates the same f32 constants the scenario serializes, so a
/// correct run differs by a few ulp of the accumulated sum; the tolerance is
/// orders of magnitude above that and orders of magnitude below any real
/// look.
pub const YAW_TOLERANCE_DEG: f32 = 0.5;

/// The built-in gameplay smoke scenario: the real stasis-room content, named
/// temporal wake beats across the authored opening (the closed hold, and
/// before, during, and after both blinks, each tick derived from the
/// timeline's own named boundaries), then the post-wake shape — a scripted
/// look of 3 degrees per tick on ten ticks after the handoff (30 degrees in
/// total), a movement action the report records, and beats pinned on
/// look-quiet ticks around the turn, so each beat's yaw sample is the
/// integrated angle at the rendered moment.
#[must_use]
pub fn gameplay_smoke_scenario() -> Scenario {
    let handoff = wake_handoff_tick();
    let b = WakeTimeline::authored_boundaries();
    let mut beats = vec![
        wake_beat("eyes-closed", 2),
        wake_beat("first-blink-before", b.first_blink_start),
        wake_beat(
            "first-blink-during",
            b.first_blink_start + (b.second_opening_start - b.first_blink_start) / 2,
        ),
        wake_beat(
            "first-blink-after",
            b.second_opening_start + (b.second_blink_start - b.second_opening_start) / 2,
        ),
        wake_beat("second-blink-before", b.second_blink_start),
        wake_beat(
            "second-blink-during",
            b.second_blink_start + (b.final_opening_start - b.second_blink_start) / 2,
        ),
        wake_beat(
            "second-blink-after",
            b.final_opening_start + (b.complete_tick - b.final_opening_start) / 2,
        ),
    ];
    beats.push(Beat::new("wake", handoff + 2));
    beats.push(Beat::new("turned", handoff + 20));
    let look_first = handoff + 5;
    let mut actions = vec![ScriptedAction::move_delta(handoff + 3, 1.0, 0.0)];
    for tick in look_first..look_first + 10 {
        actions.push(ScriptedAction::look(tick, 3.0, 0.0));
    }
    Scenario {
        name: "gameplay-smoke".to_owned(),
        seed: 1234,
        ticks_per_second: TICKS_PER_SECOND,
        actions,
        beats,
        pacing: None,
        max_frames: 600,
        mode: ScenarioMode::Capture,
        warmup_frames: 0,
        sample_frames: 0,
        content: Content::Gameplay,
        calibration: None,
    }
}

/// Verify a gameplay run's report: the room observation must be present and
/// matching, every pinned beat must carry a yaw sample at exactly the
/// (tick, frame) its PNG decodes to, and the yaw movement between
/// consecutive pinned beats at or after the wake handoff must equal the
/// scripted look delta between their ticks. The temporal wake beats stay
/// pinned capture evidence; they never anchor the replay.
///
/// # Errors
/// A message naming the first failed check: the missing or mismatched room
/// observation, the beat whose yaw sample is absent, the replay's missing
/// post-wake anchor pair, or the yaw movement
/// that does not match the script.
pub fn verify_gameplay(scenario: &Scenario, report: &Report) -> Result<(), String> {
    verify_room(report)?;
    let anchored = beat_anchored_samples(report)?;
    verify_yaw_replay(scenario, &replay_anchor_samples(&anchored)?)
}

/// The scripted-look replay's anchors: the anchored beats pinned at or after
/// the derived wake handoff, tick-sorted. Before the handoff the rig's yaw is
/// the wake driver's authored sway projection — look is disarmed behind the
/// phase gate, and the sway is authored rotation the script never asked for —
/// so a "movement equals the scripted sum" check there would measure the wake,
/// not the player systems. From the handoff on the effect is stripped and the
/// rig yaw is look again. At least two post-handoff anchors are required: a
/// replay without a pair proves nothing and fails loudly instead.
///
/// # Errors
/// Fewer than two anchored beats sit at or after the wake handoff.
pub(crate) fn replay_anchor_samples(anchored: &[AnchoredBeat]) -> Result<Vec<(u64, f32)>, String> {
    let handoff = wake_handoff_tick();
    let samples: Vec<(u64, f32)> = anchored
        .iter()
        .filter(|beat| beat.tick >= handoff)
        .map(|beat| (beat.tick, beat.yaw))
        .collect();
    if samples.len() < 2 {
        return Err(format!(
            "the scripted-look replay needs at least two beats pinned at or after the wake \
             handoff (tick {handoff}), found {}",
            samples.len()
        ));
    }
    Ok(samples)
}

/// The report's room observation: both numbers, present and equal, with a
/// nonzero expectation (a registry that builds nothing proves nothing).
pub(crate) fn verify_room(report: &Report) -> Result<(), String> {
    let check = report.events.iter().find_map(|event| match event {
        TimedEvent::RoomCheck {
            pods_expected,
            pods_present,
            ..
        } => Some((*pods_expected, *pods_present)),
        _ => None,
    });
    let Some((pods_expected, pods_present)) = check else {
        return Err(
            "gameplay report has no room check event: the app never observed the stasis room"
                .to_owned(),
        );
    };
    if pods_expected == 0 {
        return Err(format!(
            "room check expects {pods_expected} pods: a scene that builds nothing cannot prove presence"
        ));
    }
    if pods_expected != pods_present {
        return Err(format!(
            "stasis room mismatch: the registry builds {pods_expected} pods but the run found {pods_present}"
        ));
    }
    Ok(())
}

/// One report beat anchored to its pinned moment: the yaw the rig reported
/// at exactly the beat's pinned (tick, frame), plus the eye point when the
/// report carries one there (gameplay content samples both at every pin;
/// the smoke lane's assertions use only the yaw).
pub(crate) struct AnchoredBeat {
    /// The beat's name.
    pub(crate) name: String,
    /// The beat's pinned tick.
    pub(crate) tick: u64,
    /// The rig's yaw in degrees at the pinned moment.
    pub(crate) yaw: f32,
    /// The rig's eye point (x, y, z) at the pinned moment, when sampled.
    pub(crate) eye: Option<[f32; 3]>,
}

/// Every report beat anchored to its samples: the yaw at exactly the beat's
/// pinned (tick, frame) (a beat without one fails here, naming the beat),
/// the eye point when present, tick-sorted for the replay. At least two
/// anchors are required: one pinned moment proves nothing about motion.
pub(crate) fn beat_anchored_samples(report: &Report) -> Result<Vec<AnchoredBeat>, String> {
    let yaws: Vec<(u64, u64, f32)> = report
        .events
        .iter()
        .filter_map(|event| match event {
            TimedEvent::PlayerYaw {
                tick,
                frame,
                yaw_degrees,
            } => Some((*tick, *frame, *yaw_degrees)),
            _ => None,
        })
        .collect();
    let positions: Vec<(u64, u64, f32, f32, f32)> = report
        .events
        .iter()
        .filter_map(|event| match event {
            TimedEvent::PlayerPosition {
                tick,
                frame,
                x,
                y,
                z,
            } => Some((*tick, *frame, *x, *y, *z)),
            _ => None,
        })
        .collect();
    let mut anchored: Vec<AnchoredBeat> = Vec::new();
    for (name, entry) in &report.beats {
        let found = yaws
            .iter()
            .find(|(tick, frame, _)| *tick == entry.tick && *frame == entry.frame);
        let Some((_, _, yaw)) = found else {
            return Err(format!(
                "beat `{name}` has no player-yaw sample at its pinned (tick {}, frame {}): \
                 the player rig never reported its angle",
                entry.tick, entry.frame
            ));
        };
        let eye = positions
            .iter()
            .find(|(tick, frame, ..)| *tick == entry.tick && *frame == entry.frame)
            .map(|(_, _, x, y, z)| [*x, *y, *z]);
        anchored.push(AnchoredBeat {
            name: name.clone(),
            tick: entry.tick,
            yaw: *yaw,
            eye,
        });
    }
    if anchored.len() < 2 {
        return Err(format!(
            "gameplay verification needs at least two beat-pinned yaw samples, found {}",
            anchored.len()
        ));
    }
    anchored.sort_by_key(|beat| beat.tick);
    Ok(anchored)
}

/// One angular difference, in degrees, wrapped to its shortest arc in
/// (-180, 180]: the raw difference reduced modulo a full turn, taken from
/// the side with the smaller magnitude (a half turn keeps the positive
/// representative). The rig reports yaw wrapped into that same range (the
/// player rig keeps its integrated angle there), so a scripted look across
/// the +/-180 boundary arrives as, for example, +175 then -155, and the
/// raw subtraction reads -330 where the rig turned +30. Reducing the raw
/// difference modulo 360 recovers the turn.
#[must_use]
fn shortest_arc_degrees(raw_delta_degrees: f32) -> f32 {
    let wrapped = raw_delta_degrees.rem_euclid(360.0);
    if wrapped > 180.0 {
        wrapped - 360.0
    } else {
        wrapped
    }
}

/// The scripted-yaw replay: between consecutive pinned beats (the post-wake
/// anchors [`replay_anchor_samples`] selects), the rig's
/// yaw movement must equal the look actions scripted strictly before the
/// later tick minus those before the earlier one, compared modulo a full
/// turn within [`YAW_TOLERANCE_DEG`]. (The app samples at the beat
/// request, before its tick drives, so a look on the beat's own tick
/// belongs to the interval after the sample.) Both sides are angular
/// endpoints, so they compare modulo 360: the rig wraps its reported angle
/// into (-180, 180], so a correct +270 degree script measures -90, and
/// exactly +/-180 read as each other. The price of endpoint sampling is
/// aliasing: a whole number of extra full turns between two beats is
/// indistinguishable from no turn, and scenario authors pin beats so that
/// cannot masquerade as a pass.
pub(crate) fn verify_yaw_replay(
    scenario: &Scenario,
    anchored: &[(u64, f32)],
) -> Result<(), String> {
    let scripted_before = |tick: u64| -> f32 {
        scenario
            .actions
            .iter()
            .filter(|action| action.tick < tick)
            .filter_map(|action| match action.action {
                Action::Look { yaw_deg, .. } => Some(yaw_deg),
                _ => None,
            })
            .sum()
    };
    for pair in anchored.windows(2) {
        let (earlier_tick, earlier_yaw) = (pair[0].0, pair[0].1);
        let (later_tick, later_yaw) = (pair[1].0, pair[1].1);
        let expected = scripted_before(later_tick) - scripted_before(earlier_tick);
        let measured = shortest_arc_degrees(later_yaw - earlier_yaw);
        let error = shortest_arc_degrees(measured - expected);
        if error.abs() > YAW_TOLERANCE_DEG {
            return Err(format!(
                "scripted look did not drive the rig: yaw moved {measured:.3} deg (mod a full \
                 turn) between ticks {earlier_tick} and {later_tick}, scripted {expected:.3} deg \
                 (tolerance {YAW_TOLERANCE_DEG} deg)"
            ));
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use std::collections::BTreeMap;
    use std::sync::LazyLock;

    use gone_app::harness::report::{BeatEntry, Identity, Report, TimedEvent};
    use gone_app::harness::{Beat, Content, Scenario};

    use super::{
        YAW_TOLERANCE_DEG, gameplay_smoke_scenario, shortest_arc_degrees, verify_gameplay,
        wake_handoff_tick,
    };
    use gone_app::gone_sim::WakeTimeline;

    /// The built-in scenario's post-wake beat pins (derived once per process).
    static WAKE_BEAT_TICK: LazyLock<u64> = LazyLock::new(|| wake_handoff_tick() + 2);
    static TURNED_BEAT_TICK: LazyLock<u64> = LazyLock::new(|| wake_handoff_tick() + 20);

    /// A synthetic gameplay report over `samples` (tick, yaw) pairs: the two
    /// beats of the built-in scenario pinned at frames matching their ticks,
    /// a matching room check, and the ready/complete scaffolding. The yaw
    /// values are what a correct 30-degree run produces.
    fn report_with_yaws(yaws: &[(u64, f32)]) -> Report {
        let mut report = Report::new(
            3,
            "gameplay-smoke",
            1234,
            Identity {
                app_hash: "a".into(),
                scenario_hash: "s".into(),
                config_hash: "c".into(),
            },
        );
        let mut beats = BTreeMap::new();
        beats.insert(
            "wake".to_owned(),
            BeatEntry {
                file: "beats/wake.png".into(),
                tick: *WAKE_BEAT_TICK,
                frame: *WAKE_BEAT_TICK,
                request_id: 1,
            },
        );
        beats.insert(
            "turned".to_owned(),
            BeatEntry {
                file: "beats/turned.png".into(),
                tick: *TURNED_BEAT_TICK,
                frame: *TURNED_BEAT_TICK,
                request_id: 2,
            },
        );
        report.beats = beats;
        report.events.push(TimedEvent::Ready { frame: 0 });
        report.events.push(TimedEvent::RoomCheck {
            frame: 0,
            pods_expected: 7,
            pods_present: 7,
        });
        for (tick, yaw) in yaws {
            report.events.push(TimedEvent::PlayerYaw {
                tick: *tick,
                frame: *tick,
                yaw_degrees: *yaw,
            });
        }
        report.events.push(TimedEvent::Complete { frame: 30 });
        report
    }

    /// The scenario beat named `name`'s pinned tick.
    fn tick_of_name(scenario: &Scenario, name: &str) -> u64 {
        scenario
            .beats
            .iter()
            .find(|beat| beat.name == name)
            .unwrap_or_else(|| panic!("beat `{name}` is authored"))
            .tick
    }

    #[test]
    fn the_built_in_scenario_scripts_thirty_degrees_between_its_beats() {
        let scenario = gameplay_smoke_scenario();
        assert_eq!(scenario.content, Content::Gameplay);
        // The replay must be satisfiable by construction: 3 degrees per tick
        // on the ten ticks after the wake handoff is 30 degrees strictly
        // before the `turned` beat and nothing before the `wake` beat.
        let before = |tick: u64| -> f32 {
            scenario
                .actions
                .iter()
                .filter(|action| action.tick < tick)
                .filter_map(|action| match action.action {
                    gone_app::harness::Action::Look { yaw_deg, .. } => Some(yaw_deg),
                    _ => None,
                })
                .sum()
        };
        assert!((before(*WAKE_BEAT_TICK) - 0.0).abs() < f32::EPSILON);
        assert!((before(*TURNED_BEAT_TICK) - 30.0).abs() < f32::EPSILON);
    }

    #[test]
    fn the_smoke_wake_beats_pin_the_authored_wake_regions() {
        // Each temporal wake beat pins exactly the authored moment its name
        // claims: the beat's scenario tick plus one (the post-tick pin) is
        // the wake tick the sample comes from, and the regions come from the
        // timeline's own named boundaries, never literals.
        let b = WakeTimeline::authored_boundaries();
        let scenario = gameplay_smoke_scenario();
        let wake_tick_of = |name: &str| -> u64 {
            scenario
                .beats
                .iter()
                .find(|beat| beat.name == name)
                .unwrap_or_else(|| panic!("beat `{name}` is authored"))
                .tick
                + 1
        };
        assert!(
            wake_tick_of("eyes-closed") < b.first_opening_start,
            "the first beat samples the closed hold"
        );
        assert_eq!(
            wake_tick_of("first-blink-before"),
            b.first_blink_start,
            "the first opening's widest sample sits exactly at the blink boundary"
        );
        let during_first = wake_tick_of("first-blink-during");
        assert!(
            b.first_blink_start < during_first && during_first < b.second_opening_start,
            "mid first blink's closing stroke: {during_first}"
        );
        let after_first = wake_tick_of("first-blink-after");
        assert!(
            b.second_opening_start < after_first && after_first < b.second_blink_start,
            "inside the reopen after the first blink: {after_first}"
        );
        assert_eq!(
            wake_tick_of("second-blink-before"),
            b.second_blink_start,
            "the second opening's widest sample sits exactly at the blink boundary"
        );
        let during_second = wake_tick_of("second-blink-during");
        assert!(
            b.second_blink_start < during_second && during_second < b.final_opening_start,
            "mid second blink's closing stroke: {during_second}"
        );
        let after_second = wake_tick_of("second-blink-after");
        assert!(
            b.final_opening_start < after_second && after_second < b.complete_tick,
            "inside the final opening after the second blink: {after_second}"
        );
        // The post-wake beats sit inside AwakeInPod, on look-quiet ticks
        // around the turn.
        let wake = tick_of_name(&scenario, "wake");
        let turned = tick_of_name(&scenario, "turned");
        assert_eq!(wake, *WAKE_BEAT_TICK);
        assert_eq!(turned, *TURNED_BEAT_TICK);
        assert!(wake_handoff_tick() < wake && turned < scenario.max_frames);
        // The beats are pinned in tick order, as the app's request cursor
        // requires.
        let ticks: Vec<u64> = scenario.beats.iter().map(|beat| beat.tick).collect();
        let mut sorted = ticks.clone();
        sorted.sort_unstable();
        assert_eq!(ticks, sorted);
    }

    #[test]
    fn a_correct_thirty_degree_run_verifies() {
        let scenario = gameplay_smoke_scenario();
        let report = report_with_yaws(&[(*WAKE_BEAT_TICK, 0.0), (*TURNED_BEAT_TICK, 30.0)]);
        assert!(verify_gameplay(&scenario, &report).is_ok());
    }

    #[test]
    fn a_report_whose_player_systems_never_looked_fails() {
        // Negative proof (player side): yaw samples that never moved are the
        // shape a run produces when the player systems are off or the
        // scripted look never integrates. The lane must reject it.
        let scenario = gameplay_smoke_scenario();
        let report = report_with_yaws(&[(*WAKE_BEAT_TICK, 0.0), (*TURNED_BEAT_TICK, 0.0)]);
        let err = verify_gameplay(&scenario, &report).expect_err("stale yaw must fail");
        assert!(
            err.contains("scripted look did not drive the rig"),
            "names the failure: {err}"
        );
        assert!(err.contains("30.000"), "names the scripted amount: {err}");
    }

    #[test]
    fn a_look_across_the_wrap_boundary_measures_the_shortest_arc() {
        // The authored spawn yaw sits near +/-180, so the scripted +30 look
        // wraps (170 -> -160): the raw subtraction reads -330, but the rig
        // turned +30, and the replay must measure the shortest arc.
        let scenario = gameplay_smoke_scenario();
        let report = report_with_yaws(&[(*WAKE_BEAT_TICK, 170.0), (*TURNED_BEAT_TICK, -160.0)]);
        assert!(verify_gameplay(&scenario, &report).is_ok());
    }

    #[test]
    fn the_shortest_arc_helper_wraps_exact_deltas() {
        // Every input here is an exact f32 integer, so the outputs are
        // exact too; each distance below is zero (one f32::EPSILON is one
        // ulp at 1.0, orders above these results' spacing).
        assert!((shortest_arc_degrees(30.0) - 30.0).abs() < f32::EPSILON);
        assert!(
            (shortest_arc_degrees(-330.0) - 30.0).abs() < f32::EPSILON,
            "170 -> -160"
        );
        assert!(
            (shortest_arc_degrees(330.0) - -30.0).abs() < f32::EPSILON,
            "-170 -> 160"
        );
        assert!(shortest_arc_degrees(0.0).abs() < f32::EPSILON);
        // Exactly half a turn is its own boundary; the helper keeps the
        // positive representative for both signs.
        assert!((shortest_arc_degrees(180.0) - 180.0).abs() < f32::EPSILON);
        assert!((shortest_arc_degrees(-180.0) - 180.0).abs() < f32::EPSILON);
    }

    /// A two-beat scenario whose scripted look between the pinned beats is
    /// `total` degrees: ten equal look steps on the ten ticks after the wake
    /// handoff land exactly `total` before the `turned` beat and nothing
    /// before the `wake` beat (the built-in scenario's own post-wake shape),
    /// so the reports below isolate the endpoint arithmetic.
    fn turn_scenario(total: f32) -> Scenario {
        let look_first = wake_handoff_tick() + 5;
        let mut actions = vec![gone_app::harness::ScriptedAction::move_delta(
            wake_handoff_tick() + 3,
            1.0,
            0.0,
        )];
        for tick in look_first..look_first + 10 {
            actions.push(gone_app::harness::ScriptedAction::look(
                tick,
                total / 10.0,
                0.0,
            ));
        }
        Scenario {
            name: "turn".to_owned(),
            seed: 1234,
            ticks_per_second: gone_app::harness::TICKS_PER_SECOND,
            actions,
            beats: vec![
                Beat::new("wake", *WAKE_BEAT_TICK),
                Beat::new("turned", *TURNED_BEAT_TICK),
            ],
            pacing: None,
            max_frames: 600,
            mode: gone_app::harness::ScenarioMode::Capture,
            warmup_frames: 0,
            sample_frames: 0,
            content: Content::Gameplay,
            calibration: None,
        }
    }

    /// A synthetic gameplay report over `samples` (tick, yaw) pairs with
    /// beats named a/b/c pinned at those ticks (frames matching their
    /// ticks), for multi-beat verification past a full revolution.
    fn three_beat_report(samples: &[(u64, f32)]) -> Report {
        let mut report = Report::new(
            3,
            "turn",
            1234,
            Identity {
                app_hash: "a".into(),
                scenario_hash: "s".into(),
                config_hash: "c".into(),
            },
        );
        let names = ["a", "b", "c"];
        let mut beats = BTreeMap::new();
        for (index, (tick, _)) in samples.iter().enumerate() {
            beats.insert(
                names[index].to_owned(),
                BeatEntry {
                    file: format!("beats/{}.png", names[index]),
                    tick: *tick,
                    frame: *tick,
                    request_id: index as u64 + 1,
                },
            );
        }
        report.beats = beats;
        report.events.push(TimedEvent::Ready { frame: 0 });
        report.events.push(TimedEvent::RoomCheck {
            frame: 0,
            pods_expected: 7,
            pods_present: 7,
        });
        for (tick, yaw) in samples {
            report.events.push(TimedEvent::PlayerYaw {
                tick: *tick,
                frame: *tick,
                yaw_degrees: *yaw,
            });
        }
        report.events.push(TimedEvent::Complete { frame: 50 });
        report
    }

    #[test]
    fn a_two_hundred_seventy_degree_turn_verifies_mod_a_full_turn() {
        // Regression: the verifier compared the wrapped measurement against
        // the unwrapped scripted sum, so a correct +270 degree turn failed
        // because the rig reports the wrapped endpoint -90. Endpoints
        // compare modulo a full turn, and both spellings of the endpoint
        // verify.
        let scenario = turn_scenario(270.0);
        let report = report_with_yaws(&[(*WAKE_BEAT_TICK, 0.0), (*TURNED_BEAT_TICK, -90.0)]);
        assert!(verify_gameplay(&scenario, &report).is_ok());
        let unwrapped = report_with_yaws(&[(*WAKE_BEAT_TICK, 0.0), (*TURNED_BEAT_TICK, 270.0)]);
        assert!(verify_gameplay(&scenario, &unwrapped).is_ok());
    }

    #[test]
    fn a_minus_two_hundred_seventy_degree_turn_verifies_mod_a_full_turn() {
        // The -270 script measures +90 once the rig wraps its endpoint; the
        // modulo comparison accepts it and rejects a rig that never turned.
        let scenario = turn_scenario(-270.0);
        let report = report_with_yaws(&[(*WAKE_BEAT_TICK, 0.0), (*TURNED_BEAT_TICK, 90.0)]);
        assert!(verify_gameplay(&scenario, &report).is_ok());
        let stale = report_with_yaws(&[(*WAKE_BEAT_TICK, 0.0), (*TURNED_BEAT_TICK, 0.0)]);
        let err = verify_gameplay(&scenario, &stale).expect_err("no turn must fail");
        assert!(err.contains("scripted look did not drive the rig"), "{err}");
    }

    #[test]
    fn an_exact_half_turn_verifies_from_either_reported_endpoint() {
        // Exactly +/-180 is the boundary the shortest-arc reduction cannot
        // sign: both the scripted +180 and -180 pass against either
        // reported endpoint spelling, because the endpoints coincide mod a
        // full turn.
        for total in [180.0, -180.0] {
            let scenario = turn_scenario(total);
            for endpoint in [180.0, -180.0] {
                let report =
                    report_with_yaws(&[(*WAKE_BEAT_TICK, 0.0), (*TURNED_BEAT_TICK, endpoint)]);
                assert!(
                    verify_gameplay(&scenario, &report).is_ok(),
                    "scripted {total} must verify against reported {endpoint}"
                );
            }
        }
    }

    #[test]
    fn a_cumulative_turn_past_a_full_revolution_verifies() {
        // Three post-wake beats spanning 500 scripted degrees (200 by the
        // middle beat, 300 more by the last). The rig wraps each reported
        // endpoint into (-180, 180]: 200 reports as -160 and 500 as 140.
        // Both beat pairs verify modulo a full turn.
        let handoff = wake_handoff_tick();
        let mut actions = Vec::new();
        for tick in handoff + 5..handoff + 15 {
            actions.push(gone_app::harness::ScriptedAction::look(tick, 20.0, 0.0));
        }
        for tick in handoff + 25..handoff + 35 {
            actions.push(gone_app::harness::ScriptedAction::look(tick, 30.0, 0.0));
        }
        let scenario = Scenario {
            name: "revolution".to_owned(),
            seed: 1234,
            ticks_per_second: gone_app::harness::TICKS_PER_SECOND,
            actions,
            beats: vec![
                Beat::new("a", handoff + 2),
                Beat::new("b", handoff + 20),
                Beat::new("c", handoff + 40),
            ],
            pacing: None,
            max_frames: 600,
            mode: gone_app::harness::ScenarioMode::Capture,
            warmup_frames: 0,
            sample_frames: 0,
            content: Content::Gameplay,
            calibration: None,
        };
        let report = three_beat_report(&[
            (handoff + 2, 0.0),
            (handoff + 20, -160.0),
            (handoff + 40, 140.0),
        ]);
        assert!(verify_gameplay(&scenario, &report).is_ok());
    }

    #[test]
    fn a_replay_without_post_wake_anchors_fails() {
        // Every beat pinned before the wake handoff: the rig's yaw there is
        // the wake's authored sway, not scripted look, so there is no replay
        // to run and the verifier must say so instead of vacuously passing.
        let handoff = wake_handoff_tick();
        let scenario = Scenario {
            name: "all-pre-wake".to_owned(),
            seed: 1234,
            ticks_per_second: gone_app::harness::TICKS_PER_SECOND,
            actions: vec![gone_app::harness::ScriptedAction::look(
                handoff + 5,
                30.0,
                0.0,
            )],
            beats: vec![Beat::new("a", handoff - 40), Beat::new("b", handoff - 20)],
            pacing: None,
            max_frames: 600,
            mode: gone_app::harness::ScenarioMode::Capture,
            warmup_frames: 0,
            sample_frames: 0,
            content: Content::Gameplay,
            calibration: None,
        };
        let report = three_beat_report(&[(handoff - 40, 0.0), (handoff - 20, 0.0)]);
        let err = verify_gameplay(&scenario, &report).expect_err("no anchor pair must fail");
        assert!(err.contains("at or after the wake handoff"), "{err}");
    }

    #[test]
    fn a_partially_turned_run_fails() {
        // A rig that turned but not by the scripted amount is equally dead:
        // the assertion is on the number, not on motion existing.
        let scenario = gameplay_smoke_scenario();
        let report = report_with_yaws(&[(*WAKE_BEAT_TICK, 0.0), (*TURNED_BEAT_TICK, 5.0)]);
        assert!(verify_gameplay(&scenario, &report).is_err());
    }

    #[test]
    fn just_inside_the_tolerance_passes_and_just_outside_fails() {
        let scenario = gameplay_smoke_scenario();
        let inside = report_with_yaws(&[
            (*WAKE_BEAT_TICK, 0.0),
            (*TURNED_BEAT_TICK, 30.0 + YAW_TOLERANCE_DEG - 0.01),
        ]);
        assert!(verify_gameplay(&scenario, &inside).is_ok());
        let outside = report_with_yaws(&[
            (*WAKE_BEAT_TICK, 0.0),
            (*TURNED_BEAT_TICK, 30.0 + YAW_TOLERANCE_DEG + 0.01),
        ]);
        assert!(verify_gameplay(&scenario, &outside).is_err());
    }

    #[test]
    fn a_missing_yaw_sample_fails_naming_the_beat() {
        let scenario = gameplay_smoke_scenario();
        let mut report = report_with_yaws(&[(*WAKE_BEAT_TICK, 0.0), (*TURNED_BEAT_TICK, 30.0)]);
        report
            .events
            .retain(|event| !matches!(event, TimedEvent::PlayerYaw { tick, .. } if *tick == *TURNED_BEAT_TICK));
        let err = verify_gameplay(&scenario, &report).expect_err("missing sample must fail");
        assert!(err.contains("turned"), "names the beat: {err}");
    }

    #[test]
    fn a_report_with_one_sample_cannot_verify() {
        // A single pinned beat cannot prove look: the replay needs two
        // anchors. The report carries one beat with its sample and nothing
        // missing, so the count check is what rejects it.
        let scenario = gameplay_smoke_scenario();
        let mut report = report_with_yaws(&[(*WAKE_BEAT_TICK, 0.0)]);
        report.beats.remove("turned");
        let err = verify_gameplay(&scenario, &report).expect_err("one sample cannot verify");
        assert!(err.contains("at least two"), "{err}");
    }

    #[test]
    fn a_room_mismatch_fails_and_a_missing_room_check_fails() {
        let scenario = gameplay_smoke_scenario();
        let mut report = report_with_yaws(&[(*WAKE_BEAT_TICK, 0.0), (*TURNED_BEAT_TICK, 30.0)]);
        for event in &mut report.events {
            if let TimedEvent::RoomCheck { pods_present, .. } = event {
                *pods_present = 0;
            }
        }
        let err = verify_gameplay(&scenario, &report).expect_err("mismatch must fail");
        assert!(err.contains("stasis room mismatch"), "{err}");
        let mut report = report_with_yaws(&[(*WAKE_BEAT_TICK, 0.0), (*TURNED_BEAT_TICK, 30.0)]);
        report
            .events
            .retain(|event| !matches!(event, TimedEvent::RoomCheck { .. }));
        let err = verify_gameplay(&scenario, &report).expect_err("missing check must fail");
        assert!(err.contains("no room check event"), "{err}");
    }

    #[test]
    fn the_scenario_serializes_with_its_content_field() {
        let scenario = gameplay_smoke_scenario();
        let json = gone_app::harness::scenario::scenario_to_json(&scenario).expect("serializes");
        assert!(json.contains("\"content\":\"gameplay\""), "{json}");
        let parsed: Scenario =
            gone_app::harness::scenario::parse_scenario(&json).expect("parses back");
        assert_eq!(parsed, scenario);
    }
}
