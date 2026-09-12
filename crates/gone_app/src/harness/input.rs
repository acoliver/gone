//! Input adapter protocol (issue #6 / slice A).
//!
//! The harness lane feeds scripted input *upstream* of gameplay through the same
//! input layer real devices feed, so gameplay never learns whether an input came from a
//! human or the runner. The adapter is a pure state machine over the scenario's
//! scripted actions; an ECS resource in the app owns one of these and drives it
//! exactly once per fixed update. Each edge is delivered to *exactly one* fixed
//! update even when multiple fixed updates run in a single rendered frame
//! (consume-on-step) or none do (edges stay buffered), which is the
//! reproducible-clock guarantee the design documents need.
//!
//! The adapter buffers press/release edges and accumulated mouse motion, and moves
//! live in [`ButtonEdge::move_delta`] so movement and buttons share one
//! exactly-once delivery stream. The adapter is a pure std struct; it never touches
//! Bevy.

use std::collections::VecDeque;
use std::fmt;

/// A mouse button the adapter can press/release.
#[derive(Clone, Copy, Debug, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub enum MouseButton {
    /// Primary button.
    Primary,
    /// Secondary button.
    Secondary,
    /// Middle button.
    Middle,
    /// No button (reserved; look never touches the buttons).
    None,
}

/// A keyboard key the adapter can press/release. Kept minimal (the gameplay slice
/// only scripts movement/activation placeholders); the adapter is the boundary, so
/// growing this enum is a harness change, not an app change.
#[derive(Clone, Debug, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub enum Key {
    /// The key bound to move forward.
    Forward,
    /// The key bound to move left.
    Left,
    /// The key bound to move back.
    Back,
    /// The key bound to move right.
    Right,
    /// The activate / jump key.
    Activate,
    /// A sprint / secondary key.
    Secondary,
    /// The key that releases the captured cursor. Scripted Escape presses
    /// enter the shared gameplay input plane and release the cursor exactly
    /// as the physical key does.
    Escape,
    /// Any other key, named by its usage.
    Other(String),
}

/// A single edge for one button: press or release.
#[derive(Clone, Copy, Debug, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub enum Edge {
    /// The key went from released to pressed at this point in the timeline.
    Press,
    /// The key went from pressed to released.
    Release,
}

/// A single buffered button edge delivered to exactly one fixed update.
#[derive(Clone, Debug, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct ButtonEdge {
    /// Button the edge applies to.
    pub button: Button,
    /// Press or release.
    pub edge: Edge,
}

/// Input events name their edge so opposite edges of one button are
/// distinguishable in events, checkpoints, and compare streams.
impl fmt::Display for ButtonEdge {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{} {}", self.button, self.edge)
    }
}

impl fmt::Display for Edge {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.word())
    }
}

impl Edge {
    /// The edge word used in event descriptions.
    #[must_use]
    pub const fn word(&self) -> &'static str {
        match self {
            Self::Press => "press",
            Self::Release => "release",
        }
    }
}

impl fmt::Display for Button {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Key(key) => write!(f, "Key({key:?})"),
            Self::Mouse(button) => write!(f, "Mouse({button:?})"),
        }
    }
}

/// Which physical button an edge targets.
#[derive(Clone, Debug, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub enum Button {
    /// A keyboard key.
    Key(Key),
    /// A mouse button.
    Mouse(MouseButton),
}

/// The shape of a scripted input action from the scenario.
#[derive(Clone, Debug, PartialEq, serde::Serialize, serde::Deserialize)]
pub enum Action {
    /// Look: the player camera turns by these pitch/yaw deltas (angles in
    /// degrees), accumulated for one fixed update.
    Look {
        /// Horizontal turn delta in degrees.
        yaw_deg: f32,
        /// Vertical turn delta in degrees.
        pitch_deg: f32,
    },
    /// Move: movement is a 2D vector in world axes (forward/strafe),
    /// delivered in [`Step::movement`], never mixed into the look channel.
    MoveDelta {
        /// Forward/back component.
        forward: f32,
        /// Left/right strafe component.
        strafe: f32,
    },
    /// A button goes down.
    Press {
        /// Button affected.
        button: Button,
    },
    /// A button goes up.
    Release {
        /// Button affected.
        button: Button,
    },
    /// Wait: consume `duration` scenario seconds of the fixed clock before
    /// any later action dispatches, whatever those actions' own ticks say.
    /// The duration converts to whole ticks against the scenario's
    /// `ticks_per_second` (rounded up), so the wait spans at least the
    /// scripted simulation time. A wait delivers nothing itself.
    Wait {
        /// Scenario seconds to wait; zero waits nothing.
        duration: f32,
    },
    /// Wait until the scripted clock reaches `tick` before any later
    /// action dispatches. A target at or before the clock's current tick
    /// waits nothing; a later target holds later actions even when their
    /// own ticks came first. A wait delivers nothing itself.
    WaitUntilTick {
        /// The tick the clock must reach before later actions run.
        tick: u64,
    },
}

/// One action slot in the script: execute `action` when the clock reaches `tick`.
#[derive(Clone, Debug, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct ScriptedAction {
    /// Tick at which to run this action.
    pub tick: u64,
    /// The action to run.
    pub action: Action,
}

/// A tiny x/y delta used for look motion, kept here so the adapter stays std-only;
/// the app converts to its own coordinates on injection.
#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub struct Delta {
    /// Horizontal delta.
    pub x: f32,
    /// Vertical delta.
    pub y: f32,
}

impl Delta {
    /// A zero delta.
    #[must_use]
    pub const fn zero() -> Self {
        Self { x: 0.0, y: 0.0 }
    }
}

/// One fixed update's movement intent in scenario axes: forward/back and
/// strafe. A distinct typed payload from look motion ([`Delta`]), so a
/// consumer can tell forward from backward from no movement, and movement
/// from look, by type instead of by convention.
#[derive(Clone, Copy, Debug, Default, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct MoveMotion {
    /// Forward/back component (positive is forward).
    pub forward: f32,
    /// Left/right strafe component (positive is right).
    pub strafe: f32,
}

impl MoveMotion {
    /// A zero movement, meaning "no scripted movement this tick".
    #[must_use]
    pub const fn zero() -> Self {
        Self {
            forward: 0.0,
            strafe: 0.0,
        }
    }
}

/// Pure scripted-input state machine. Not an ECS component: the app owns one as a
/// resource and drives it exactly once per fixed update. Waits hold the
/// dispatch of later actions: a [`Action::Wait`] consumes its duration as
/// ticks of the fixed clock, and a [`Action::WaitUntilTick`] pins the
/// dispatch floor at its target tick, so either one orders later actions
/// regardless of their own ticks.
#[derive(Clone, Debug)]
pub struct InputAdapter {
    actions: VecDeque<ScriptedAction>,
    /// Pending button edges, drained one tick at a time.
    pub(super) edge_queue: VecDeque<ButtonEdge>,
    /// Synthetic release edges queued by a focus clear. They deliver ahead
    /// of `edge_queue` (they are older than anything dispatched later) and
    /// a later clear never drops them: a release that joined the
    /// exactly-once stream always delivers exactly once, whatever else the
    /// input layer drops at a later boundary.
    pub(super) synthetic_releases: VecDeque<ButtonEdge>,
    /// Look motion to deliver on the next fixed update.
    pub(super) pending_motion: Delta,
    /// Movement to deliver on the next fixed update.
    pub(super) pending_movement: MoveMotion,
    tick_floor: u64,
    /// The scenario clock's rate, in ticks per second: a wait duration
    /// converts to whole ticks against it.
    ticks_per_second: u64,
    /// The tick the clock must reach before actions queued after a
    /// wait-until dispatch. Zero when none is in force.
    hold_until_tick: u64,
    /// Ticks still held by the duration wait that dispatched most recently,
    /// spent one exact tick per step. Zero when none is in force.
    hold_remaining_ticks: f32,
    /// Buttons currently held: presses whose release has not been
    /// dispatched yet. The lifecycle lane's focus clear releases every
    /// held button (see `lifecycle::InputAdapter::clear_held`), the
    /// scripted analog of a real device's stuck key.
    pub(super) held: Vec<Button>,
}

impl InputAdapter {
    /// New adapter with an empty action list, converting wait durations at
    /// the scenario's tick rate.
    ///
    /// # Panics
    /// Panics when `ticks_per_second` is zero: the fixed clock has no
    /// meaningful step at a zero rate, and the scenario parser rejects
    /// that before an adapter is ever built.
    #[must_use]
    pub fn new(ticks_per_second: u64) -> Self {
        Self::with_actions(Vec::new(), ticks_per_second)
    }
}

impl InputAdapter {
    /// New adapter seeded with an action list (presumed sorted by tick),
    /// converting wait durations at the scenario's tick rate.
    ///
    /// # Panics
    /// Panics when `ticks_per_second` is zero (see [`InputAdapter::new`]).
    #[must_use]
    pub fn with_actions(actions: Vec<ScriptedAction>, ticks_per_second: u64) -> Self {
        assert!(
            ticks_per_second > 0,
            "the input adapter needs a tick rate of at least 1"
        );
        let mut actions = actions.into_iter().collect::<VecDeque<_>>();
        actions.make_contiguous().sort_by_key(|a| a.tick);
        Self {
            actions,
            edge_queue: VecDeque::new(),
            synthetic_releases: VecDeque::new(),
            pending_motion: Delta::zero(),
            pending_movement: MoveMotion::zero(),
            tick_floor: 0,
            ticks_per_second,
            hold_until_tick: 0,
            hold_remaining_ticks: 0.0,
            held: Vec::new(),
        }
    }

    /// The logical tick the adapter is currently qualified to play at.
    #[must_use]
    pub fn tick(&self) -> u64 {
        self.tick_floor
    }

    /// The still-buffered button edges, a focus clear's queued synthetic
    /// releases included (depth = how many fixed updates they would
    /// cover). Mainly diagnostic.
    #[must_use]
    pub fn pending_edges(&self) -> usize {
        self.edge_queue.len() + self.synthetic_releases.len()
    }

    /// True if no scripted actions remain undispatched and no buffered
    /// output (edge queue or synthetic release) is still owed a step.
    #[must_use]
    pub fn is_complete(&self) -> bool {
        self.actions.is_empty() && self.edge_queue.is_empty() && self.synthetic_releases.is_empty()
    }

    /// Inject one action immediately (called from a scripted update).
    pub fn push_action(&mut self, action: ScriptedAction) {
        self.actions.push_back(action);
        self.actions.make_contiguous().sort_by_key(|a| a.tick);
    }

    /// Force-reset to tick zero with the given action list. Part of the protocol
    /// surface for callers that need to restart a timeline; the app does not use
    /// it — it builds the adapter at startup and never steps it before the
    /// readiness boundary, so the clock simply starts at zero there. The
    /// tick rate carries over: waits in the new list convert at the same
    /// rate as the old one.
    pub fn reset(&mut self, actions: Vec<ScriptedAction>) {
        *self = Self::with_actions(actions, self.ticks_per_second);
    }

    /// Advance one fixed update. Returns the edges to deliver this tick (exactly the
    /// edges whose turn it is) plus this tick's look motion and movement, each in
    /// its own payload. Queued output is the adapter's oldest delivery tier
    /// (a focus clear's synthetic releases, then the buffered edge queue):
    /// a step with any queued edge delivers exactly those edges and holds
    /// the rest — no same-tick action, motion, or movement beside them, and
    /// the action clock does not advance — so the action that would have
    /// dispatched this tick dispatches on a later step, and each queued
    /// edge delivers exactly once. Actions whose tick is not yet reached stay queued,
    /// and actions queued after a wait stay queued until the wait's hold
    /// lifts, whatever their own ticks say. A duration hold burns one of
    /// its ticks per step (the step that dispatches the wait excluded, the
    /// decrement preceding the checks), so held actions dispatch on
    /// exactly the tick the duration ends.
    ///
    /// # Panics
    /// Panics if the front of the action queue is missing after checking it, which is
    /// unreachable: `front` was just inspected and non-empty.
    #[must_use]
    pub fn step(&mut self) -> Step {
        let mut out = Step {
            edges: Vec::new(),
            motion: Delta::zero(),
            movement: MoveMotion::zero(),
        };
        if !self.synthetic_releases.is_empty() || !self.edge_queue.is_empty() {
            out.edges.extend(self.synthetic_releases.drain(..));
            out.edges.extend(self.edge_queue.drain(..));
            return out;
        }
        if self.hold_remaining_ticks > 0.0 {
            self.hold_remaining_ticks -= 1.0;
        }
        while let Some(front) = self.actions.front() {
            if front.tick > self.tick_floor
                || self.tick_floor < self.hold_until_tick
                || self.hold_remaining_ticks > 0.0
            {
                break;
            }
            let action = self.actions.pop_front().expect("front exists");
            self.apply(action, &mut out);
        }
        out.motion = self.pending_motion;
        self.pending_motion = Delta::zero();
        out.movement = self.pending_movement;
        self.pending_movement = MoveMotion::zero();
        self.tick_floor += 1;
        out
    }

    fn apply(&mut self, action: ScriptedAction, out: &mut Step) {
        match action.action {
            Action::Press { button } => {
                if !self.held.contains(&button) {
                    self.held.push(button.clone());
                }
                out.edges.push(ButtonEdge {
                    button,
                    edge: Edge::Press,
                });
            }
            Action::Release { button } => {
                self.held.retain(|held| held != &button);
                out.edges.push(ButtonEdge {
                    button,
                    edge: Edge::Release,
                });
            }
            Action::Look { yaw_deg, pitch_deg } => {
                self.pending_motion.x += yaw_deg;
                self.pending_motion.y += pitch_deg;
            }
            Action::MoveDelta { forward, strafe } => {
                self.pending_movement.forward += forward;
                self.pending_movement.strafe += strafe;
            }
            Action::Wait { duration } => {
                // A wait only dispatches once any earlier hold has lifted,
                // so its tick count starts whole from its own dispatch
                // floor and composes by sequence, never by mixing with a
                // wait-until's tick target.
                self.hold_remaining_ticks = wait_ticks(duration, self.ticks_per_second);
            }
            Action::WaitUntilTick { tick } => {
                self.hold_until_tick = tick.max(self.tick_floor);
            }
        }
    }
}

/// One wait duration's tick count at the scenario's rate: the duration in
/// scenario seconds, rounded up to whole ticks, so the wait spans at least
/// the scripted time. The count stays in `f32` end to end and is spent one
/// exact tick per step (integers up to 2²⁴ are exact in `f32`, so the
/// per-tick decrement never rounds), which keeps a float-to-int conversion
/// out of the fixed clock's path. Rates above `u16::MAX` saturate there: a
/// scenario tick rate that high is beyond the clock's meaningful range.
/// Negative durations floor to zero (the scenario parser rejects them;
/// programmatic builders get the same treatment), and a duration whose
/// tick count passes f32's exact-integer grid holds indefinitely, which is
/// the honest reading of a script asking for years of scenario time and is
/// ended by the run deadline long before it matters.
#[must_use]
fn wait_ticks(duration: f32, ticks_per_second: u64) -> f32 {
    let rate = f32::from(u16::try_from(ticks_per_second).unwrap_or(u16::MAX));
    (duration.max(0.0) * rate).ceil()
}

/// One fixed update's worth of adapter output.
#[derive(Default, Debug)]
pub struct Step {
    /// Edges to deliver (button presses/releases).
    pub edges: Vec<ButtonEdge>,
    /// Look motion to deliver, in degrees.
    pub motion: Delta,
    /// Movement to deliver, in scenario axes. Distinct from [`Step::motion`]
    /// so forward, backward, and zero movement stay distinguishable
    /// downstream and can never be read as look motion.
    pub movement: MoveMotion,
}

/// Convenience constructors for scenario definitions.
impl ScriptedAction {
    /// Press a key at `tick`.
    #[must_use]
    pub fn press(tick: u64, key: Key) -> Self {
        Self {
            tick,
            action: Action::Press {
                button: Button::Key(key),
            },
        }
    }

    /// Release a key at `tick`.
    #[must_use]
    pub fn release(tick: u64, key: Key) -> Self {
        Self {
            tick,
            action: Action::Release {
                button: Button::Key(key),
            },
        }
    }

    /// Look at `tick`.
    #[must_use]
    pub fn look(tick: u64, yaw_deg: f32, pitch_deg: f32) -> Self {
        Self {
            tick,
            action: Action::Look { yaw_deg, pitch_deg },
        }
    }

    /// Move at `tick` by the given forward/strafe components.
    #[must_use]
    pub fn move_delta(tick: u64, forward: f32, strafe: f32) -> Self {
        Self {
            tick,
            action: Action::MoveDelta { forward, strafe },
        }
    }

    /// Wait from `tick` for `duration` scenario seconds before later
    /// actions dispatch.
    #[must_use]
    pub fn wait(tick: u64, duration: f32) -> Self {
        Self {
            tick,
            action: Action::Wait { duration },
        }
    }

    /// Hold later actions until the scripted clock reaches `target_tick`.
    #[must_use]
    pub fn wait_until_tick(tick: u64, target_tick: u64) -> Self {
        Self {
            tick,
            action: Action::WaitUntilTick { tick: target_tick },
        }
    }
}

#[cfg(test)]
mod tests {
    use super::{
        Button, ButtonEdge, Delta, Edge, InputAdapter, Key, MouseButton, MoveMotion, ScriptedAction,
    };

    fn key(tick: u64, key: Key) -> ScriptedAction {
        ScriptedAction::press(tick, key)
    }

    fn edge(button: Button, edge: Edge) -> ButtonEdge {
        ButtonEdge { button, edge }
    }

    /// The tests' tick rate, used for wait conversions; the tests without
    /// waits are insensitive to it.
    const RATE: u64 = 60;

    /// An adapter at the tests' tick rate.
    fn adapter(actions: Vec<ScriptedAction>) -> InputAdapter {
        InputAdapter::with_actions(actions, RATE)
    }

    #[test]
    fn press_and_release_are_distinct_in_descriptions() {
        // Regression: the old describe_edge rendered both edges as the bare
        // button name, so `Key(Forward) press` and the release of the same key
        // were indistinguishable in events and compare streams.
        let press = edge(Button::Key(Key::Forward), Edge::Press).to_string();
        let release = edge(Button::Key(Key::Forward), Edge::Release).to_string();
        assert_eq!(press, "Key(Forward) press");
        assert_eq!(release, "Key(Forward) release");
        assert_ne!(press, release);
    }

    #[test]
    fn mouse_and_other_key_buttons_name_their_edge() {
        assert_eq!(
            edge(Button::Mouse(MouseButton::Primary), Edge::Press).to_string(),
            "Mouse(Primary) press"
        );
        assert_eq!(
            edge(Button::Key(Key::Activate), Edge::Release).to_string(),
            "Key(Activate) release"
        );
    }

    #[test]
    fn each_edge_consumed_once_even_over_multiple_ticks() {
        let mut adapter = adapter(vec![
            key(0, Key::Forward),
            ScriptedAction::release(1, Key::Forward),
        ]);
        let first = adapter.step();
        assert_eq!(first.edges[0].edge, Edge::Press);
        assert_eq!(first.edges.len(), 1);
        assert_eq!(
            first.edges[0],
            super::ButtonEdge {
                button: Button::Key(Key::Forward),
                edge: Edge::Press,
            }
        );
        let second = adapter.step();
        assert_eq!(second.edges.len(), 1);
        assert_eq!(
            second.edges[0],
            super::ButtonEdge {
                button: Button::Key(Key::Forward),
                edge: Edge::Release,
            }
        );
        // Draining a tick with nothing due delivers nothing a third time.
        assert_eq!(adapter.step().edges.len(), 0);
    }

    #[test]
    fn multiple_actions_same_tick_delivered_together() {
        // Regression for the test's own name: it used to schedule its two
        // actions on different ticks and only ever assert one edge per step.
        // Two presses scripted for the same tick must land together in the
        // one step whose clock reaches that tick.
        let mut adapter = adapter(vec![
            key(1, Key::Left),
            key(1, Key::Right),
            ScriptedAction::release(1, Key::Left),
        ]);
        // Tick 0 delivers nothing: nothing is due yet.
        let first = adapter.step();
        assert_eq!(first.edges.len(), 0);
        // Tick 1 delivers all three edges in one step.
        let second = adapter.step();
        assert_eq!(second.edges.len(), 3);
        assert!(
            second
                .edges
                .iter()
                .all(|e| e.edge == Edge::Press || e.edge == Edge::Release)
        );
        // Draining a tick with nothing due delivers nothing a third time.
        assert_eq!(adapter.step().edges.len(), 0);
    }

    #[test]
    fn future_edges_stay_buffered_until_their_tick() {
        // A rendered frame can run zero fixed updates; with no step call the
        // adapter cannot lose state, so the observable guarantee is the
        // complementary one: fixed updates that run before a scripted
        // action's tick deliver nothing and leave the action buffered, and
        // the buffered action fires intact on exactly its own tick.
        let mut adapter = adapter(vec![key(3, Key::Forward)]);
        for _ in 0..3 {
            let early = adapter.step();
            assert_eq!(early.edges.len(), 0, "nothing is due before tick 3");
            assert_eq!(early.movement, MoveMotion::zero());
        }
        let due = adapter.step();
        assert_eq!(due.edges.len(), 1, "the buffered tick-3 press survives");
        assert_eq!(due.edges[0].edge, Edge::Press);
    }

    #[test]
    fn multiple_fixed_updates_deliver_one_press_per_tick() {
        // Simulates two fixed updates in one rendered frame: each `step` is one
        // fixed update. tick 0 has a press; tick 1 has two presses all of
        // which land when the clock reaches 1.
        let mut adapter = adapter(vec![
            key(0, Key::Forward),
            key(1, Key::Left),
            key(1, Key::Right),
        ]);
        let first = adapter.step();
        assert_eq!(first.edges[0].edge, Edge::Press);
        assert_eq!(first.edges.len(), 1);
        let second = adapter.step();
        assert_eq!(second.edges.len(), 2);
        let _ = adapter.step();
        assert_eq!(adapter.step().edges.len(), 0);
    }

    #[test]
    fn movement_carries_its_forward_and_strafe_components() {
        // Regression: `ButtonEdge::move_delta` discarded both arguments and
        // emitted a marker edge, so forward, backward, and zero movement
        // were indistinguishable downstream. Movement now arrives in its
        // own typed payload, summed across same-tick actions.
        let mut adapter = adapter(vec![
            ScriptedAction::move_delta(0, 1.0, 0.0),
            ScriptedAction::move_delta(0, 0.0, -0.5),
            ScriptedAction::move_delta(2, -1.0, 0.25),
        ]);
        let s0 = adapter.step();
        assert_eq!(
            s0.movement,
            MoveMotion {
                forward: 1.0,
                strafe: -0.5,
            }
        );
        assert_eq!(s0.edges.len(), 0, "movement is not a button edge");
        assert_eq!(s0.motion, Delta::zero(), "movement is not look motion");
        let s1 = adapter.step();
        assert_eq!(s1.movement, MoveMotion::zero());
        let s2 = adapter.step();
        assert_eq!(
            s2.movement,
            MoveMotion {
                forward: -1.0,
                strafe: 0.25,
            }
        );
    }

    #[test]
    fn look_and_movement_stay_in_their_own_payloads() {
        let mut adapter = adapter(vec![
            ScriptedAction::look(0, 5.0, -2.0),
            ScriptedAction::move_delta(0, 1.0, 0.0),
        ]);
        let step = adapter.step();
        assert_eq!(step.motion, Delta { x: 5.0, y: -2.0 });
        assert_eq!(
            step.movement,
            MoveMotion {
                forward: 1.0,
                strafe: 0.0,
            }
        );
    }

    #[test]
    fn motion_accumulates_and_resets_each_step() {
        let mut adapter = adapter(vec![
            ScriptedAction::look(0, 5.0, -2.0),
            ScriptedAction::look(0, 3.0, 1.0),
            ScriptedAction::look(1, 1.0, 0.0),
        ]);
        let s0 = adapter.step();
        assert_eq!(s0.motion, Delta { x: 8.0, y: -1.0 });
        let s1 = adapter.step();
        assert_eq!(s1.motion, Delta { x: 1.0, y: 0.0 });
        let s2 = adapter.step();
        assert_eq!(s2.motion, Delta::zero());
    }

    #[test]
    fn reset_brings_clock_and_edges_back_to_zero() {
        let mut adapter = adapter(vec![key(0, Key::Forward)]);
        let _ = adapter.step();
        adapter.reset(vec![key(0, Key::Activate)]);
        assert_eq!(adapter.tick(), 0);
        let step = adapter.step();
        assert_eq!(step.edges[0].edge, Edge::Press);
        assert_eq!(step.edges.len(), 1);
        let _ = adapter.step();
    }

    #[test]
    fn completion_ignores_remaining_future_actions() {
        let mut adapter = adapter(vec![key(5, Key::Forward)]);
        let _ = adapter.step();
        assert!(!adapter.is_complete());
        // Stepping past the schedule drains it eventually. Six steps land the clock
        // at 0..=5 and the tick-5 press fires during step 6.
        for _ in 0..5 {
            let _ = adapter.step();
        }
        let _ = adapter.step();
        assert!(adapter.is_complete());
    }

    #[test]
    fn wait_until_tick_holds_later_actions_until_the_clock_reaches_it() {
        // Regression (wait restoration): the second look's own tick (0)
        // comes first, but the wait pins the dispatch floor at tick 5, so
        // nothing more delivers until the clock reaches it and the held
        // action delivers intact there.
        let mut adapter = adapter(vec![
            ScriptedAction::look(0, 5.0, 0.0),
            ScriptedAction::wait_until_tick(0, 5),
            ScriptedAction::look(0, 3.0, 0.0),
        ]);
        let first = adapter.step();
        assert_eq!(first.motion, Delta { x: 5.0, y: 0.0 });
        for floor in 1..5 {
            let held = adapter.step();
            assert_eq!(held.motion, Delta::zero(), "held at floor {floor}");
        }
        assert_eq!(adapter.tick(), 5, "the hold spans floors 1 through 4");
        let released = adapter.step();
        assert_eq!(released.motion, Delta { x: 3.0, y: 0.0 });
    }

    #[test]
    fn wait_duration_consumes_whole_ticks_of_scenario_time() {
        // 0.5 seconds at 60 ticks per second is 30 whole ticks: the press
        // queued behind the wait delivers on exactly the tick the duration
        // ends, and nothing delivers before it.
        let mut adapter = adapter(vec![ScriptedAction::wait(0, 0.5), key(0, Key::Forward)]);
        let first = adapter.step();
        assert!(first.edges.is_empty(), "the wait itself delivers nothing");
        for floor in 1..30 {
            assert!(adapter.step().edges.is_empty(), "held at floor {floor}");
        }
        assert_eq!(adapter.tick(), 30, "half a second at 60 tps is 30 ticks");
        let released = adapter.step();
        assert_eq!(released.edges.len(), 1);
        assert_eq!(released.edges[0].edge, Edge::Press);
    }

    #[test]
    fn a_wait_between_actions_orders_their_delivery() {
        // A press at tick 0, then a one-second wait, then a release whose
        // own tick (1) is long past: the release waits out the hold and
        // lands on tick 60.
        let mut adapter = adapter(vec![
            key(0, Key::Forward),
            ScriptedAction::wait(0, 1.0),
            ScriptedAction::release(1, Key::Forward),
        ]);
        let first = adapter.step();
        assert_eq!(first.edges.len(), 1, "the tick-0 press delivers first");
        for floor in 1..60 {
            assert!(adapter.step().edges.is_empty(), "held at floor {floor}");
        }
        assert_eq!(adapter.tick(), 60);
        let released = adapter.step();
        assert_eq!(
            released.edges,
            vec![edge(Button::Key(Key::Forward), Edge::Release)]
        );
    }

    #[test]
    fn a_zero_duration_wait_holds_nothing() {
        // A wait of zero seconds converts to zero ticks and consumes no
        // scenario time: the action behind it dispatches on the same tick.
        let mut adapter = adapter(vec![ScriptedAction::wait(0, 0.0), key(0, Key::Forward)]);
        let first = adapter.step();
        assert_eq!(
            first.edges.len(),
            1,
            "a zero wait consumes no scenario time"
        );
    }

    #[test]
    fn queued_edges_deliver_before_the_same_ticks_actions() {
        // The lifecycle focus clear queues synthetic releases; the queue is
        // the adapter's oldest-output lane, so a queued edge delivers on the
        // next step, ahead of any action dispatching that same tick, and
        // exactly once.
        let mut adapter = adapter(vec![key(0, Key::Forward), key(2, Key::Left)]);
        let _ = adapter.step();
        adapter.edge_queue.push_back(super::ButtonEdge {
            button: Button::Key(Key::Forward),
            edge: Edge::Release,
        });
        let next = adapter.step();
        assert_eq!(next.edges.len(), 1, "the queued release delivered alone");
        assert_eq!(next.edges[0].edge, Edge::Release);
        // A later step cannot deliver it again.
        assert_eq!(adapter.step().edges.len(), 0);
    }

    #[test]
    fn waits_compose_and_a_reached_target_holds_nothing() {
        // Two half-second waits dispatch one after the other and hold one
        // second in total; the trailing wait-until a reached target is a
        // no-op. The press behind them lands after the whole hold.
        let mut adapter = adapter(vec![
            ScriptedAction::wait(0, 0.5),
            ScriptedAction::wait(0, 0.5),
            key(0, Key::Activate),
            ScriptedAction::wait_until_tick(0, 0),
        ]);
        let first = adapter.step();
        assert!(first.edges.is_empty(), "the first wait holds everything");
        for floor in 1..60 {
            assert!(adapter.step().edges.is_empty(), "held at floor {floor}");
        }
        assert_eq!(adapter.tick(), 60, "one second of waits composes");
        let released = adapter.step();
        assert_eq!(released.edges.len(), 1, "the press lands after the hold");
        assert!(adapter.is_complete(), "a drained schedule is complete");
    }
}
