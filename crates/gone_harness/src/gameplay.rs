//! Gameplay-lane runner tooling: the built-in gameplay smoke scenario and the
//! machine verification over a gameplay run's report.
//!
//! The gameplay lane boots the real game (stasis room, player rig with
//! first-person look, post chain) instead of the calibration scene, so its
//! verification goes beyond the capture-lane checks: the report must carry a
//! room observation matching the registry's count, and the rig's yaw samples
//! must show exactly the scripted look delta between pinned beats. This is
//! the negative proof the lane exists for: a report from a run whose player
//! systems never integrated scripted look (stale or missing yaw samples)
//! fails here, as does a run whose scene failed to build its pods.

use gone_app::harness::report::{Report, TimedEvent};
use gone_app::harness::scenario::TICKS_PER_SECOND;
use gone_app::harness::{Action, Beat, Content, Scenario, ScenarioMode, ScriptedAction};

/// How far the sampled yaw may drift from the scripted replay, in degrees.
/// The app integrates the same f32 constants the scenario serializes, so a
/// correct run differs by a few ulp of the accumulated sum; the tolerance is
/// orders of magnitude above that and orders of magnitude below any real
/// look.
pub const YAW_TOLERANCE_DEG: f32 = 0.5;

/// The built-in gameplay smoke scenario: the real stasis-room content, a
/// scripted look of 3 degrees per tick on ticks 5 through 14 (30 degrees in
/// total), a movement action the report records, and two beats pinned on
/// look-quiet ticks around the turn (2 and 20), so each beat's yaw sample is
/// the integrated angle at the rendered moment.
#[must_use]
pub fn gameplay_smoke_scenario() -> Scenario {
    let mut actions = vec![ScriptedAction::move_delta(3, 1.0, 0.0)];
    for tick in 5..=14 {
        actions.push(ScriptedAction::look(tick, 3.0, 0.0));
    }
    Scenario {
        name: "gameplay-smoke".to_owned(),
        seed: 1234,
        ticks_per_second: TICKS_PER_SECOND,
        actions,
        beats: vec![Beat::new("wake", 2), Beat::new("turned", 20)],
        pacing: None,
        max_frames: 600,
        mode: ScenarioMode::Capture,
        warmup_frames: 0,
        sample_frames: 0,
        content: Content::Gameplay,
    }
}

/// Verify a gameplay run's report: the room observation must be present and
/// matching, every pinned beat must carry a yaw sample at exactly the
/// (tick, frame) its PNG decodes to, and the yaw movement between
/// consecutive pinned beats must equal the scripted look delta between
/// their ticks.
///
/// # Errors
/// A message naming the first failed check: the missing or mismatched room
/// observation, the beat whose yaw sample is absent, or the yaw movement
/// that does not match the script.
pub fn verify_gameplay(scenario: &Scenario, report: &Report) -> Result<(), String> {
    verify_room(report)?;
    let anchored = beat_yaw_samples(report)?;
    verify_yaw_replay(scenario, &anchored)
}

/// The report's room observation: both numbers, present and equal, with a
/// nonzero expectation (a registry that builds nothing proves nothing).
fn verify_room(report: &Report) -> Result<(), String> {
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

/// One beat's yaw sample: the beat's pinned tick and the sampled yaw in
/// degrees. Beats without a sample at their pinned (tick, frame) fail here.
fn beat_yaw_samples(report: &Report) -> Result<Vec<(u64, f32)>, String> {
    let samples: Vec<(u64, u64, f32)> = report
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
    let mut anchored: Vec<(u64, f32)> = Vec::new();
    for (name, entry) in &report.beats {
        let found = samples
            .iter()
            .find(|(tick, frame, _)| *tick == entry.tick && *frame == entry.frame);
        let Some((_, _, yaw)) = found else {
            return Err(format!(
                "beat `{name}` has no player-yaw sample at its pinned (tick {}, frame {}): \
                 the player rig never reported its angle",
                entry.tick, entry.frame
            ));
        };
        anchored.push((entry.tick, *yaw));
    }
    if anchored.len() < 2 {
        return Err(format!(
            "gameplay verification needs at least two beat-pinned yaw samples, found {}",
            anchored.len()
        ));
    }
    anchored.sort_by_key(|(tick, _)| *tick);
    Ok(anchored)
}

/// The shortest-arc signed yaw delta, in degrees, wrapped into (-180, 180].
/// The rig reports yaw wrapped into that same range (the player rig keeps
/// its integrated angle there), so a scripted look across the +/-180
/// boundary arrives as, for example, +175 then -155, and the raw
/// subtraction reads -330 where the rig turned +30. Reducing the raw delta
/// modulo 360 recovers the true signed movement for any look shorter than
/// half a turn between two pinned beats, which every scripted scenario is.
#[must_use]
fn shortest_arc_degrees(raw_delta_degrees: f32) -> f32 {
    let wrapped = raw_delta_degrees.rem_euclid(360.0);
    if wrapped > 180.0 {
        wrapped - 360.0
    } else {
        wrapped
    }
}

/// The scripted-yaw replay: between consecutive pinned beats, the rig's yaw
/// movement must equal the look actions scripted strictly before the later
/// tick minus those before the earlier one, within [`YAW_TOLERANCE_DEG`].
/// (The app samples at the beat request, before its tick drives, so a look
/// on the beat's own tick belongs to the interval after the sample.) The
/// measured movement is the shortest-arc delta ([`shortest_arc_degrees`]),
/// so a spawn yaw near the +/-180 boundary measures the turn, not the wrap.
fn verify_yaw_replay(scenario: &Scenario, anchored: &[(u64, f32)]) -> Result<(), String> {
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
        let actual = shortest_arc_degrees(later_yaw - earlier_yaw);
        if (actual - expected).abs() > YAW_TOLERANCE_DEG {
            return Err(format!(
                "scripted look did not drive the rig: yaw moved {actual:.3} deg between ticks \
                 {earlier_tick} and {later_tick}, scripted {expected:.3} deg \
                 (tolerance {YAW_TOLERANCE_DEG} deg)"
            ));
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use std::collections::BTreeMap;

    use gone_app::harness::report::{BeatEntry, Identity, Report, TimedEvent};
    use gone_app::harness::{Content, Scenario};

    use super::{
        YAW_TOLERANCE_DEG, gameplay_smoke_scenario, shortest_arc_degrees, verify_gameplay,
    };

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
                tick: 2,
                frame: 2,
                request_id: 1,
            },
        );
        beats.insert(
            "turned".to_owned(),
            BeatEntry {
                file: "beats/turned.png".into(),
                tick: 20,
                frame: 20,
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

    #[test]
    fn the_built_in_scenario_scripts_thirty_degrees_between_its_beats() {
        let scenario = gameplay_smoke_scenario();
        assert_eq!(scenario.content, Content::Gameplay);
        assert_eq!(scenario.beats.len(), 2);
        // The replay must be satisfiable by construction: 3 degrees per tick
        // on ticks 5..=14 is 30 degrees strictly before tick 20 and nothing
        // before tick 2.
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
        assert!((before(2) - 0.0).abs() < f32::EPSILON);
        assert!((before(20) - 30.0).abs() < f32::EPSILON);
    }

    #[test]
    fn a_correct_thirty_degree_run_verifies() {
        let scenario = gameplay_smoke_scenario();
        let report = report_with_yaws(&[(2, 0.0), (20, 30.0)]);
        assert!(verify_gameplay(&scenario, &report).is_ok());
    }

    #[test]
    fn a_report_whose_player_systems_never_looked_fails() {
        // Negative proof (player side): yaw samples that never moved are the
        // shape a run produces when the player systems are off or the
        // scripted look never integrates. The lane must reject it.
        let scenario = gameplay_smoke_scenario();
        let report = report_with_yaws(&[(2, 0.0), (20, 0.0)]);
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
        let report = report_with_yaws(&[(2, 170.0), (20, -160.0)]);
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

    #[test]
    fn a_partially_turned_run_fails() {
        // A rig that turned but not by the scripted amount is equally dead:
        // the assertion is on the number, not on motion existing.
        let scenario = gameplay_smoke_scenario();
        let report = report_with_yaws(&[(2, 0.0), (20, 5.0)]);
        assert!(verify_gameplay(&scenario, &report).is_err());
    }

    #[test]
    fn just_inside_the_tolerance_passes_and_just_outside_fails() {
        let scenario = gameplay_smoke_scenario();
        let inside = report_with_yaws(&[(2, 0.0), (20, 30.0 + YAW_TOLERANCE_DEG - 0.01)]);
        assert!(verify_gameplay(&scenario, &inside).is_ok());
        let outside = report_with_yaws(&[(2, 0.0), (20, 30.0 + YAW_TOLERANCE_DEG + 0.01)]);
        assert!(verify_gameplay(&scenario, &outside).is_err());
    }

    #[test]
    fn a_missing_yaw_sample_fails_naming_the_beat() {
        let scenario = gameplay_smoke_scenario();
        let mut report = report_with_yaws(&[(2, 0.0), (20, 30.0)]);
        report
            .events
            .retain(|event| !matches!(event, TimedEvent::PlayerYaw { tick, .. } if *tick == 20));
        let err = verify_gameplay(&scenario, &report).expect_err("missing sample must fail");
        assert!(err.contains("turned"), "names the beat: {err}");
    }

    #[test]
    fn a_report_with_one_sample_cannot_verify() {
        // A single pinned beat cannot prove look: the replay needs two
        // anchors. The report carries one beat with its sample and nothing
        // missing, so the count check is what rejects it.
        let scenario = gameplay_smoke_scenario();
        let mut report = report_with_yaws(&[(2, 0.0)]);
        report.beats.remove("turned");
        let err = verify_gameplay(&scenario, &report).expect_err("one sample cannot verify");
        assert!(err.contains("at least two"), "{err}");
    }

    #[test]
    fn a_room_mismatch_fails_and_a_missing_room_check_fails() {
        let scenario = gameplay_smoke_scenario();
        let mut report = report_with_yaws(&[(2, 0.0), (20, 30.0)]);
        for event in &mut report.events {
            if let TimedEvent::RoomCheck { pods_present, .. } = event {
                *pods_present = 0;
            }
        }
        let err = verify_gameplay(&scenario, &report).expect_err("mismatch must fail");
        assert!(err.contains("stasis room mismatch"), "{err}");
        let mut report = report_with_yaws(&[(2, 0.0), (20, 30.0)]);
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
