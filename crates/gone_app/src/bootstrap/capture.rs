//! Capture I/O for the harness lane, split out of `super` for size.
//!
//! This module is the receiver side of the capture protocol: the
//! [`ScreenshotCaptured`] observer that routes every readback of the run (the
//! canary present probe, beat captures, the canary's single onscreen capture,
//! and the readiness proof), the convert/save paths behind them, and the
//! latency-proof delay knob. The routing rules and the failure policy are the
//! ones `super`'s module doc describes; nothing here retries.

use std::path::Path;
use std::time::Duration;

use bevy::ecs::prelude::{On, Query, Res, ResMut, Resource, With};
use bevy::ecs::system::SystemParam;
use bevy::image::Image;
use bevy::render::view::screenshot::ScreenshotCaptured;

use super::state::{
    BeatCapture, HarnessState, OnscreenCapture, PRESENT_BUDGET_FRAMES, PresentGate, PresentProbe,
    Readiness, fail_scenario,
};
use crate::capture::capture_to_png;

/// Where the loading-frame capture is written inside the run directory. The
/// proof is the rendered loading presentation (dark clear, no authored content
/// on calibration; the first provisioned game frame on gameplay).
const READINESS_PROOF_FILE: &str = "readiness-proof.png";

/// The observer's run-ledger access: the readiness handshake, the scenario
/// state, the present gate, and the capture-delay knob in one
/// [`SystemParam`], keeping the observer's parameter count small and the
/// access exact.
#[derive(SystemParam)]
pub(super) struct RunLedger<'w> {
    readiness: ResMut<'w, Readiness>,
    state: ResMut<'w, HarnessState>,
    present: ResMut<'w, PresentGate>,
    delay: Res<'w, CaptureDelay>,
}

/// The receiver for every bevy screenshot of this run. A capture carrying a
/// [`PresentProbe`] is the canary's present verdict: rendered content opens
/// the present gate, the zeroed skip signature counts a declined frame. A
/// capture carrying a [`BeatCapture`] is that beat's rendered frame: convert
/// and write it now, no retry. One carrying an [`OnscreenCapture`] is the
/// canary run's single primary-window capture. Any other capture is a
/// readiness proof.
pub(super) fn on_screenshot_captured(
    mut captured: On<ScreenshotCaptured>,
    mut run: RunLedger,
    beats: Query<&BeatCapture>,
    onscreens: Query<&OnscreenCapture>,
    probes: Query<(), With<PresentProbe>>,
) {
    let captured = captured.event_mut();
    if probes.get(captured.entity).is_ok() {
        capture_present_probe(&mut run.present, &mut run.state, &captured.image);
        return;
    }
    if let Ok(beat) = beats.get(captured.entity) {
        capture_beat(&mut run.state, run.delay.0, beat, &captured.image);
        return;
    }
    if let Ok(onscreen) = onscreens.get(captured.entity) {
        capture_onscreen(&mut run.state, onscreen, &captured.image);
        return;
    }
    if *run.readiness == Readiness::Ready {
        return; // a duplicate proof landing after the boundary
    }
    match save_capture(&run.state.out_dir, READINESS_PROOF_FILE, &captured.image) {
        Ok(()) => {
            bevy::log::info!(
                "harness: readiness proof captured ({}x{} screenshot of the offscreen target)",
                captured.image.width(),
                captured.image.height()
            );
            run.state
                .checkpoints
                .push("readiness proof captured".to_owned());
            *run.readiness = Readiness::Ready;
        }
        Err(err) => fail_scenario(
            &mut run.state,
            format!("readiness proof capture failed: {err}"),
        ),
    }
}

/// Handle one present-probe verdict. The probe lane is single-slot, the beat
/// lane's one-in-flight discipline: a verdict may land only while the gate is
/// still closed and the requester's probe is out, and any other arrival is a
/// protocol breach that fails the run by name. A capture with a rendered byte
/// is the window's first capturable frame: open the present gate and release
/// the drive. An entirely zeroed capture is bevy's skipped window composite on
/// a frame whose drawable the compositor declined: count it against the
/// present budget and fail the run by name when the budget is gone. There is
/// no silent retry: every declined frame is counted and logged, and the
/// budget failure names the mechanism.
fn capture_present_probe(present: &mut PresentGate, state: &mut HarnessState, image: &Image) {
    if present.presenting() {
        fail_scenario(
            state,
            "present-probe verdict arrived after the first present".to_owned(),
        );
        return;
    }
    if !present.probe_in_flight() {
        fail_scenario(
            state,
            "present-probe verdict arrived with no probe in flight".to_owned(),
        );
        return;
    }
    if capture_proves_present(image) {
        present.record_presented();
        bevy::log::info!(
            "harness: canary window presented its first capturable frame after {} declined frames",
            present.declined_frames()
        );
        return;
    }
    present.record_declined();
    bevy::log::info!(
        "harness: canary present probe declined ({}/{} budget frames)",
        present.declined_frames(),
        PRESENT_BUDGET_FRAMES
    );
    if !present.awaiting_first_present() {
        fail_scenario(
            state,
            format!(
                "canary window never presented a capturable frame: the compositor declined \
                 {} frames within the {PRESENT_BUDGET_FRAMES}-frame present budget, so the \
                 onscreen capture cannot start",
                present.declined_frames()
            ),
        );
    }
}

/// True when a captured window image carries at least one rendered byte. The
/// zeroed capture is bevy's skip signature: the compositor declined the
/// frame's drawable, so the screenshot's composite and readback copy are
/// skipped and the zero-initialized transfer buffer is what fires the capture
/// event. A presented frame always renders something: the canary camera chain
/// clears to a nonzero color before any scene content.
pub(super) fn capture_proves_present(image: &Image) -> bool {
    image
        .data
        .as_deref()
        .is_some_and(|bytes| bytes.iter().any(|&byte| byte != 0))
}

/// The latency-proof knob: the artificial readback delay the capture observer
/// spends on every beat capture. Parsed once at launch from the raw
/// `GONE_TEST_CAPTURE_DELAY_MS` env value (unset or empty means no delay), so
/// a misspelled value fails the launch instead of masquerading as a capture
/// fault mid-run. The runner passes its own environment to the app, so a
/// delayed run is a normal runner invocation with the variable set. Tests
/// insert the resource directly and drive the same observer path.
#[derive(Resource, Clone, Copy, Debug, Default)]
pub(super) struct CaptureDelay(pub Duration);

impl CaptureDelay {
    /// Parse the knob from the environment.
    ///
    /// # Panics
    /// Panics when the variable is set but not a millisecond count: the
    /// launch fails naming the variable rather than failing the first
    /// capture with an error a reader could mistake for renderer trouble.
    pub(super) fn from_env() -> Self {
        match parse_capture_delay(std::env::var("GONE_TEST_CAPTURE_DELAY_MS").ok().as_deref()) {
            Ok(delay) => Self(delay),
            Err(what) => panic!("{what}"),
        }
    }
}

/// Parse the raw `GONE_TEST_CAPTURE_DELAY_MS` env value (`None` = unset).
/// Unset or empty means no delay; a present value must be a millisecond
/// count, and anything else is an error naming the variable: a silently
/// ignored knob would fake the latency proof it exists for.
fn parse_capture_delay(raw: Option<&str>) -> Result<Duration, String> {
    let Some(raw) = raw.filter(|value| !value.is_empty()) else {
        return Ok(Duration::ZERO);
    };
    raw.parse::<u64>()
        .map(Duration::from_millis)
        .map_err(|e| format!("GONE_TEST_CAPTURE_DELAY_MS `{raw}` is not a millisecond count: {e}"))
}

/// Convert and write one beat's captured target frame to its manifest file,
/// then record the capture. Failures name the beat and underlying error and are
/// terminal. The latency-proof delay, when set, is spent before the in-flight
/// request is released: the capture lane stays busy for the whole artificial
/// delay, the scenario clock holds under `drive_allowed`, and the next beat
/// still pins its own scripted tick.
fn capture_beat(state: &mut HarnessState, delay: Duration, request: &BeatCapture, image: &Image) {
    std::thread::sleep(delay);
    let Some(in_flight) = state.capture_in_flight.take() else {
        fail_scenario(
            state,
            format!(
                "beat `{}` capture arrived with none in flight",
                request.name
            ),
        );
        return;
    };
    if in_flight.request_id != request.request_id {
        fail_scenario(
            state,
            format!(
                "beat `{}` capture does not match the in-flight request",
                request.name
            ),
        );
        return;
    }
    let Some(entry) = state.beats.get(&request.name) else {
        fail_scenario(
            state,
            format!("beat `{}` has no manifest entry", request.name),
        );
        return;
    };
    let file = entry.file.clone();
    match save_capture(&state.out_dir, &file, image) {
        Ok(()) => {
            bevy::log::info!(
                "harness: beat `{}` captured from the offscreen target at tick {}, frame {}, \
                 request {} ({})",
                request.name,
                request.tick,
                request.frame,
                request.request_id,
                file
            );
            state.mark_captured(
                &request.name,
                request.tick,
                request.frame,
                request.request_id,
            );
        }
        Err(err) => fail_scenario(
            state,
            format!("beat `{}` capture failed: {err}", request.name),
        ),
    }
}

/// Convert and write the canary run's single onscreen capture next to its
/// beat's PNG (`beats/<beat>.onscreen.png`, same run directory). Same policy
/// as beat saves: a failure is terminal and names the beat and the
/// underlying error.
fn capture_onscreen(state: &mut HarnessState, request: &OnscreenCapture, image: &Image) {
    let file = super::state::onscreen_file_name(&request.beat);
    match save_capture(&state.out_dir, &file, image) {
        Ok(()) => bevy::log::info!(
            "harness: canary onscreen capture for beat `{}` saved ({file}, {}x{})",
            request.beat,
            image.width(),
            image.height()
        ),
        Err(err) => fail_scenario(
            state,
            format!("onscreen capture for beat `{}` failed: {err}", request.beat),
        ),
    }
}

/// Convert a captured frame image to PNG bytes and write it under the run
/// directory at `rel`.
///
/// # Errors
/// A message naming `rel` and the underlying error; the caller fails the run.
pub(super) fn save_capture(out_dir: &Path, rel: &str, image: &Image) -> Result<(), String> {
    let path = out_dir.join(rel);
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("capture `{rel}` mkdir: {e}"))?;
    }
    let png = capture_to_png(image)?;
    std::fs::write(&path, png).map_err(|e| format!("capture `{rel}` save: {e}"))?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use std::time::Duration;

    use bevy::app::{App, AppExit, TaskPoolPlugin, Update};
    use bevy::asset::RenderAssetUsages;
    use bevy::ecs::prelude::{Entity, With};
    use bevy::ecs::schedule::IntoScheduleConfigs;
    use bevy::image::Image;
    use bevy::render::render_resource::{Extent3d, TextureDimension, TextureFormat};
    use bevy::render::view::screenshot::ScreenshotCaptured;
    use gone_sim::WakePhase;

    use super::super::ChipSprite;
    use super::super::drive::{readiness_boundary, request_present_probe};
    use super::super::gameplay::advance_wake_at_readiness;
    use super::super::state::{HarnessState, PresentGate, PresentProbe, Readiness, RunMode};
    use super::{CaptureDelay, on_screenshot_captured, parse_capture_delay};
    use crate::harness::{Content, InputAdapter, Scenario, TICKS_PER_SECOND, TimedEvent};
    use crate::scene::SimWakePhase;

    /// An 8x8 capture in the target's BGRA family with a full-length buffer,
    /// the shape the render world's readbacks actually carry (the offscreen
    /// target captures `Bgra8UnormSrgb`, window readbacks the swapchain's
    /// BGRA): the proof verdict takes the real convert/save path, so the
    /// buffer must match the texture's pixel count or `capture_to_png` fails
    /// the run. `rendered` decides whether any byte is nonzero (the present
    /// probe's skip signature versus a real frame).
    fn probe_image(rendered: bool) -> Image {
        let mut image = Image::new(
            Extent3d {
                width: 8,
                height: 8,
                depth_or_array_layers: 1,
            },
            TextureDimension::D2,
            vec![0; 8 * 8 * 4],
            TextureFormat::Bgra8UnormSrgb,
            RenderAssetUsages::MAIN_WORLD,
        );
        if rendered {
            image.data = Some(vec![3; 8 * 8 * 4]);
        }
        image
    }

    /// A canary-lane app with the readiness handshake resources and the
    /// announcement chain. The render world is played by hand: the proof and
    /// probe verdicts are `ScreenshotCaptured` triggers.
    fn canary_app(tag: &str) -> App {
        let mut app = App::new();
        app.add_plugins(TaskPoolPlugin::default());
        app.init_resource::<ChipSprite>();
        app.insert_resource(Readiness::Loading);
        app.insert_resource(PresentGate::canary());
        app.insert_resource(RunMode::Canary);
        app.insert_resource(SimWakePhase::new(WakePhase::Waking));
        app.insert_resource(HarnessState::new(
            Scenario {
                name: "canary-boundary".to_owned(),
                content: Content::Calibration,
                ..Scenario::default()
            },
            std::env::temp_dir().join(format!("gone-canary-{}-{tag}", std::process::id())),
            String::new(),
            InputAdapter::new(TICKS_PER_SECOND),
        ));
        app.insert_resource(CaptureDelay(Duration::ZERO));
        app.add_observer(on_screenshot_captured);
        app.add_message::<AppExit>();
        app.add_systems(
            Update,
            (
                readiness_boundary,
                advance_wake_at_readiness,
                request_present_probe,
            )
                .chain(),
        );
        app
    }

    /// The readiness proof (a plain capture with no marker components)
    /// delivered by hand, the way the render world delivers it.
    fn land_proof(app: &mut App) {
        let entity = app.world_mut().spawn_empty().id();
        app.world_mut().trigger(ScreenshotCaptured {
            entity,
            image: probe_image(true),
        });
    }

    /// The present probe's verdict, delivered on the probe entity the
    /// requester actually spawned and despawned on landing, the way the real
    /// one-shot screenshot request leaves the world: the observer routes the
    /// readback by the entity's [`PresentProbe`] marker, exactly as it does
    /// in the real run. `rendered` decides whether the readback carries a
    /// real frame or the zeroed skip signature.
    fn land_probe(app: &mut App, rendered: bool) {
        let mut probes = app
            .world_mut()
            .query_filtered::<Entity, With<PresentProbe>>();
        let entity = probes
            .iter(app.world())
            .next()
            .expect("a probe capture is in flight");
        app.world_mut().trigger(ScreenshotCaptured {
            entity,
            image: probe_image(rendered),
        });
        app.world_mut().despawn(entity);
    }

    #[test]
    fn the_canary_boundary_waits_for_the_present_gate() {
        // The gap this closes: a locked-screen canary used to announce ready
        // (GONE_READY, the Ready event, the wake advance) the moment the
        // proof landed, with zero presented frames. The announcement and the
        // wake must wait for the present gate: the drive stays held, probes
        // run against the closed gate, and only a rendered probe verdict
        // opens the boundary. The bounded budget still applies: declined
        // probes count, and a rendered one releases.
        let mut app = canary_app("waits");
        // The proof lands (a plain capture with no marker components): the
        // readiness ledger opens, but the gate is still closed.
        land_proof(&mut app);
        app.update();
        {
            let state = app.world().resource::<HarnessState>();
            assert!(!state.announced, "a closed gate holds the announcement");
            assert!(
                !state
                    .events
                    .iter()
                    .any(|event| matches!(event, TimedEvent::Ready { .. })),
                "no ready event before the first present"
            );
            assert_eq!(
                app.world().resource::<SimWakePhase>().phase(),
                WakePhase::Waking,
                "the wake waits behind the announcement"
            );
        }
        // One declined frame: the probe window stays open, the run holds.
        land_probe(&mut app, false);
        app.update();
        assert!(
            !app.world().resource::<HarnessState>().announced,
            "a declined probe must not open the boundary"
        );
        // The rendered probe verdict opens the gate; the next update
        // announces exactly once and the wake override fires behind it.
        land_probe(&mut app, true);
        app.update();
        {
            let state = app.world().resource::<HarnessState>();
            assert!(state.announced, "the first present opens the boundary");
            let ready = state
                .events
                .iter()
                .filter(|event| matches!(event, TimedEvent::Ready { .. }))
                .count();
            assert_eq!(ready, 1, "exactly one announcement");
            assert_eq!(
                app.world().resource::<SimWakePhase>().phase(),
                WakePhase::AwakeInPod,
                "the wake advance waits for the gate too"
            );
        }
        app.update();
        assert_eq!(
            app.world()
                .resource::<HarnessState>()
                .events
                .iter()
                .filter(|event| matches!(event, TimedEvent::Ready { .. }))
                .count(),
            1,
            "the announcement never repeats"
        );
    }

    #[test]
    fn an_unset_or_empty_capture_delay_is_no_delay() {
        assert_eq!(parse_capture_delay(None), Ok(Duration::ZERO));
        assert_eq!(parse_capture_delay(Some("")), Ok(Duration::ZERO));
    }

    #[test]
    fn a_capture_delay_value_parses_as_milliseconds() {
        assert_eq!(parse_capture_delay(Some("0")), Ok(Duration::ZERO));
        assert_eq!(
            parse_capture_delay(Some("25")),
            Ok(Duration::from_millis(25))
        );
    }

    #[test]
    fn a_nonnumeric_capture_delay_names_the_variable() {
        let err = parse_capture_delay(Some("soon")).expect_err("not a millisecond count");
        assert!(
            err.contains("GONE_TEST_CAPTURE_DELAY_MS"),
            "the error names the variable: {err}"
        );
        assert!(err.contains("soon"), "the error carries the value: {err}");
    }
}
