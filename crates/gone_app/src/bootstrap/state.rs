//! Scenario run state for the harness lane (issue #15).
//!
//! [`HarnessState`] is the run's single ledger: the logical tick and rendered
//! frame counters, the input adapter, the event/checkpoint timeline, and the two
//! beat ledgers (manifest entries pinned at request time, captured names
//! recorded when the PNG lands on disk). [`Readiness`] is the loading/ready
//! handshake state, [`drive_allowed`] is the one gate every driving system
//! shares — nothing runs before the renderer has presented, and nothing runs
//! after completion or failure — and [`fail_scenario`] records an unrecoverable
//! failure exactly once, as does [`fail_at_deadline`] when the scenario's
//! `max_frames` rendered-frame deadline passes with beats still uncaptured.
//!
//! Everything here is plain state plus pure accounting, so the beat-accounting
//! and readiness-gate regressions are unit-tested without a renderer (see
//! `super::tests`). The ECS wiring that drives this state lives in `super`.

use std::collections::{BTreeMap, BTreeSet};
use std::path::PathBuf;

use bevy::ecs::prelude::{Component, Resource};

/// How the app captures and presents this run (the two-mode capture
/// architecture, issue #5a). [`select_run_mode`] derives it from the
/// environment; harness runs insert it as a resource so the scene setup and
/// the capture requester can gate window-only behavior.
#[derive(Resource, Clone, Copy, Debug, PartialEq, Eq)]
pub enum RunMode {
    /// The normal game: a plain winit windowed app with no harness plugin.
    Normal,
    /// The harness lane's default: no window at all. The schedule runner
    /// drives updates and the offscreen capture target is the only render
    /// target; no onscreen capture happens and no onscreen file exists.
    Headless,
    /// The harness canary (`GONE_RENDER_CHECK=1`): a real, unfocused window
    /// presents the scene through a second camera, and one onscreen capture
    /// is saved next to the first beat's PNG.
    Canary,
}

/// Derive the run mode from the harness environment: `GONE_HARNESS=1` selects
/// the harness lane — headless unless `GONE_RENDER_CHECK=1` also selects the
/// canary — and absence selects the normal game. An empty value counts as
/// unset. Unknown values are rejected loudly: a stale or misspelled variable
/// must fail the launch instead of silently selecting another mode.
///
/// # Errors
/// A message naming the offending variable and its value.
pub fn select_run_mode(
    harness: Option<&str>,
    render_check: Option<&str>,
) -> Result<RunMode, String> {
    let harness = non_empty(harness);
    let render_check = non_empty(render_check);
    match (harness, render_check) {
        (None, None) => Ok(RunMode::Normal),
        (Some("1"), None) => Ok(RunMode::Headless),
        (Some("1"), Some("1")) => Ok(RunMode::Canary),
        (Some("1"), Some(value)) => Err(format!(
            "unknown GONE_RENDER_CHECK value `{value}` (expected `1` or unset)"
        )),
        (Some(value), _) => Err(format!(
            "unknown GONE_HARNESS value `{value}` (expected `1` or unset)"
        )),
        (None, Some("1")) => Err("GONE_RENDER_CHECK=1 requires GONE_HARNESS=1".to_owned()),
        (None, Some(value)) => Err(format!(
            "unknown GONE_RENDER_CHECK value `{value}` (expected `1` or unset)"
        )),
    }
}

/// An env value with empty strings collapsed to absent (unset-equivalent).
fn non_empty(value: Option<&str>) -> Option<&str> {
    value.filter(|v| !v.is_empty())
}

/// The onscreen-capture gate: a canary run captures the primary window
/// exactly once, at the first beat's request; a headless run has no window,
/// so no onscreen capture is ever requested.
pub(super) fn onscreen_capture_due(mode: RunMode, first_beat_request: bool) -> bool {
    mode == RunMode::Canary && first_beat_request
}

/// The canary onscreen capture's file for a beat: saved next to the beat PNG
/// in the same run directory, distinguished by the `.onscreen` infix.
pub(super) fn onscreen_file_name(beat: &str) -> String {
    format!("beats/{beat}.onscreen.png")
}

/// Frame-time sampler for the perf lane: skips `warmup_frames` rendered frames
use crate::harness::{Beat, BeatEntry, InputAdapter, Scenario, TimedEvent};

/// Frame-time sampler for the perf lane: skips `warmup_frames` rendered frames
/// after the readiness boundary, then records `sample_frames` wall-clock
/// deltas. Pure accounting — the perf system feeds it exactly one delta per
/// update, and extra records past the target are ignored (completion ends the
/// run that frame).
pub(super) struct PerfSampler {
    warmup_remaining: u64,
    target: u64,
    samples_ms: Vec<f64>,
}

impl PerfSampler {
    /// A sampler over a warmup + sample window (as the scenario declares).
    pub(super) fn new(warmup_frames: u64, sample_frames: u64) -> Self {
        Self {
            warmup_remaining: warmup_frames,
            target: sample_frames,
            samples_ms: Vec::new(),
        }
    }

    /// Record one rendered frame's wall-clock delta in ms. Warmup frames are
    /// skipped unrecorded.
    pub(super) fn record(&mut self, delta_ms: f64) {
        if self.warmup_remaining > 0 {
            self.warmup_remaining -= 1;
            return;
        }
        if (self.samples_ms.len() as u64) < self.target {
            self.samples_ms.push(delta_ms);
        }
    }

    /// True when the sample window is full.
    pub(super) fn is_complete(&self) -> bool {
        self.samples_ms.len() as u64 >= self.target
    }

    /// The recorded wall-clock samples in sample order.
    pub(super) fn samples_ms(&self) -> &[f64] {
        &self.samples_ms
    }
}

/// The readiness handshake state.
#[derive(Resource, Default, PartialEq, Eq, Clone, Copy, Debug)]
pub(super) enum Readiness {
    /// Loading presentation until the renderer has rendered a captured frame
    /// into the offscreen capture target.
    #[default]
    Loading,
    /// The renderer rendered the proof frame; the scenario clock runs from zero.
    Ready,
}

/// A beat screenshot request handed to the render world, with the manifest
/// numbers it is bound to.
#[derive(Clone, Debug, PartialEq, Eq)]
pub(super) struct CaptureRequest {
    pub(super) name: String,
    pub(super) tick: u64,
    pub(super) frame: u64,
    pub(super) request_id: u64,
}

/// Marks a spawned screenshot entity as one beat's capture request.
#[derive(Component)]
pub(super) struct BeatCapture {
    pub(super) name: String,
    pub(super) tick: u64,
    pub(super) frame: u64,
    pub(super) request_id: u64,
}

/// Marks a spawned screenshot entity as the canary run's single onscreen
/// (primary-window) capture. The observer saves it under the beat's
/// `.onscreen.png` name; a save failure is terminal, as for beat captures.
#[derive(Component)]
pub(super) struct OnscreenCapture {
    /// The beat whose request triggered the capture: it names the file and
    /// any failure.
    pub(super) beat: String,
}

/// The scenario state resource.
#[derive(Resource)]
pub(super) struct HarnessState {
    pub(super) scenario: Scenario,
    pub(super) out_dir: PathBuf,
    pub(super) config_hash: String,
    pub(super) tick: u64,
    pub(super) frame: u64,
    /// True once the `GONE_READY` boundary ran (exactly once).
    pub(super) announced: bool,
    pub(super) adapter: InputAdapter,
    pub(super) events: Vec<TimedEvent>,
    /// Checkpoints (frame-qualified text).
    pub(super) checkpoints: Vec<String>,
    /// Beat name -> manifest entry.
    pub(super) beats: BTreeMap<String, BeatEntry>,
    /// Request id counter.
    pub(super) next_request_id: u64,
    /// Frame at which the last beat was successfully captured.
    pub(super) last_beat_frame: u64,
    /// Request cursor: how many leading scenario beats have a manifest request
    /// recorded. Advances only in [`HarnessState::pin_next_beat`], never on
    /// capture, so a captured early beat cannot skip a later one.
    pub(super) requested_beats: usize,
    /// Names of beats whose capture file was written. Completion requires every
    /// scenario beat to appear here; a request alone never counts.
    pub(super) captured_beats: BTreeSet<String>,
    /// The beat screenshot currently being captured, if any. One capture is in
    /// flight at a time: bevy captures at most one screenshot per render target
    /// per frame.
    pub(super) capture_in_flight: Option<CaptureRequest>,
    /// True once the report was written and the exit requested.
    pub(super) done: bool,
    /// The first unrecoverable failure (artifact + error), if any.
    pub(super) failed: Option<String>,
    /// The perf lane's warmup/sample ledger (derived from the scenario; the
    /// capture lane never records into it).
    pub(super) sampler: PerfSampler,
}

impl HarnessState {
    /// Build the run state for one scenario run: counters at zero, empty
    /// ledgers, and the adapter unstepped (its clock starts at zero and is
    /// first stepped only after the readiness boundary).
    pub(super) fn new(
        scenario: Scenario,
        out_dir: PathBuf,
        config_hash: String,
        adapter: InputAdapter,
    ) -> Self {
        let sampler = PerfSampler::new(scenario.warmup_frames, scenario.sample_frames);
        Self {
            scenario,
            out_dir,
            config_hash,
            tick: 0,
            frame: 0,
            announced: false,
            adapter,
            events: Vec::new(),
            checkpoints: Vec::new(),
            beats: BTreeMap::new(),
            next_request_id: 1,
            last_beat_frame: 0,
            requested_beats: 0,
            captured_beats: BTreeSet::new(),
            capture_in_flight: None,
            done: false,
            failed: None,
            sampler,
        }
    }

    /// The next scenario beat whose capture has not been requested yet, if its
    /// tick has been reached. Beats are requested strictly in scenario order:
    /// the request cursor (`requested_beats`) advances only in
    /// [`HarnessState::pin_next_beat`], so a capture can never reorder or skip
    /// the request schedule.
    pub(super) fn next_due_beat(&self) -> Option<Beat> {
        let beat = self.scenario.beats.get(self.requested_beats)?;
        (beat.tick <= self.tick).then(|| beat.clone())
    }

    /// Pin the manifest entry for the next due beat at `(tick, frame)`, assign
    /// its request id, and advance the request cursor. Called only from
    /// `request_beat_captures`, in the same update that spawns the beat's
    /// screenshot, so the entry names the exact rendered frame the capture will
    /// show and the capture always decodes to the numbers the report claims.
    pub(super) fn pin_next_beat(&mut self, tick: u64, frame: u64) -> (String, BeatEntry) {
        let beat = self.scenario.beats[self.requested_beats].clone();
        let request_id = self.next_request_id;
        self.next_request_id += 1;
        let entry = BeatEntry {
            file: format!("beats/{}.png", beat.name),
            tick,
            frame,
            request_id,
        };
        self.beats.insert(beat.name.clone(), entry.clone());
        self.requested_beats += 1;
        bevy::log::info!(
            "harness: beat `{}` requested at tick {tick}, frame {frame}, request {request_id}",
            beat.name
        );
        (beat.name, entry)
    }

    /// Record a successful capture: the beat joins the captured set, the settle
    /// anchor moves to its frame, and the capture event + checkpoint are recorded.
    pub(super) fn mark_captured(&mut self, name: &str, tick: u64, frame: u64, request_id: u64) {
        self.last_beat_frame = frame;
        self.captured_beats.insert(name.to_owned());
        self.events.push(TimedEvent::Beat {
            name: name.to_owned(),
            tick,
            frame,
            request_id,
        });
        self.checkpoints.push(format!("beat {name} captured"));
    }

    /// True when every scenario beat has been captured to disk. Counts
    /// *captures*, not requests, so an early capture cannot complete the run
    /// while a later beat is still pending. Scenario beat names are unique, so
    /// one captured name per beat is exactly all of them.
    pub(super) fn all_beats_captured(&self) -> bool {
        self.captured_beats.len() == self.scenario.beats.len()
    }
}

/// The drive gate: no scenario tick, input edge, or capture request may run
/// before the renderer has presented ([`Readiness::Ready`]), and nothing runs
/// after completion or failure.
pub(super) fn drive_allowed(readiness: Readiness, state: &HarnessState) -> bool {
    readiness == Readiness::Ready && !state.done && state.failed.is_none()
}

/// Record an unrecoverable failure exactly once: a `Failure` event naming the
/// artifact and the underlying error, plus a matching checkpoint.
/// `finish_scan` turns this into the report and a nonzero exit.
pub(super) fn fail_scenario(state: &mut HarnessState, what: String) {
    if state.failed.is_some() {
        return;
    }
    bevy::log::error!("harness: {what}");
    let frame = state.frame;
    state.checkpoints.push(format!("failed: {what}"));
    state.events.push(TimedEvent::Failure {
        frame,
        what: what.clone(),
    });
    state.failed = Some(what);
}

/// The `max_frames` deadline: a scripted beat that is still uncaptured when
/// the rendered-frame count reaches the scenario's `max_frames` fails the run
/// — the deadline is the deadline, there is no waiting past it. Names every
/// uncaptured beat in the runner's `missing beat` shape so the report says
/// exactly why. No-op once a failure is recorded or every beat is captured,
/// so the captured happy path (finish after the settle window) is untouched.
pub(super) fn fail_at_deadline(state: &mut HarnessState) {
    if state.failed.is_some()
        || state.all_beats_captured()
        || state.frame < state.scenario.max_frames
    {
        return;
    }
    let missing: Vec<String> = state
        .scenario
        .beats
        .iter()
        .filter(|beat| !state.captured_beats.contains(&beat.name))
        .map(|beat| format!("missing beat `{}` (expected tick {})", beat.name, beat.tick))
        .collect();
    let frame = state.frame;
    fail_scenario(
        state,
        format!(
            "max_frames {frame} reached with uncaptured beats: {}",
            missing.join("; ")
        ),
    );
}
