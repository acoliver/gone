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
/// resource and drives it exactly once per fixed update.
#[derive(Clone, Debug)]
pub struct InputAdapter {
    actions: VecDeque<ScriptedAction>,
    /// Pending button edges, drained one tick at a time.
    edge_queue: VecDeque<ButtonEdge>,
    /// Look motion to deliver on the next fixed update.
    pending_motion: Delta,
    /// Movement to deliver on the next fixed update.
    pending_movement: MoveMotion,
    tick_floor: u64,
}

impl InputAdapter {
    /// New adapter with an empty action list.
    #[must_use]
    pub fn new() -> Self {
        Self::with_actions(Vec::new())
    }
}

impl Default for InputAdapter {
    fn default() -> Self {
        Self::new()
    }
}

impl InputAdapter {
    /// New adapter seeded with an action list (presumed sorted by tick).
    #[must_use]
    pub fn with_actions(actions: Vec<ScriptedAction>) -> Self {
        let mut actions = actions.into_iter().collect::<VecDeque<_>>();
        actions.make_contiguous().sort_by_key(|a| a.tick);
        Self {
            actions,
            edge_queue: VecDeque::new(),
            pending_motion: Delta::zero(),
            pending_movement: MoveMotion::zero(),
            tick_floor: 0,
        }
    }

    /// The logical tick the adapter is currently qualified to play at.
    #[must_use]
    pub fn tick(&self) -> u64 {
        self.tick_floor
    }

    /// The still-buffered button edges (depth = how many fixed updates they would
    /// cover). Mainly diagnostic.
    #[must_use]
    pub fn pending_edges(&self) -> usize {
        self.edge_queue.len()
    }

    /// True if no scripted actions remain undispatched.
    #[must_use]
    pub fn is_complete(&self) -> bool {
        self.actions.is_empty() && self.edge_queue.is_empty()
    }

    /// Inject one action immediately (called from a scripted update).
    pub fn push_action(&mut self, action: ScriptedAction) {
        self.actions.push_back(action);
        self.actions.make_contiguous().sort_by_key(|a| a.tick);
    }

    /// Force-reset to tick zero with the given action list. Part of the protocol
    /// surface for callers that need to restart a timeline; the app does not use
    /// it — it builds the adapter at startup and never steps it before the
    /// readiness boundary, so the clock simply starts at zero there.
    pub fn reset(&mut self, actions: Vec<ScriptedAction>) {
        *self = Self::with_actions(actions);
    }

    /// Advance one fixed update. Returns the edges to deliver this tick (exactly the
    /// edges whose turn it is) plus this tick's look motion and movement, each in
    /// its own payload. Actions whose tick is not yet reached stay queued.
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
        while let Some(front) = self.actions.front() {
            if front.tick > self.tick_floor {
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
            Action::Press { button } => out.edges.push(ButtonEdge {
                button,
                edge: Edge::Press,
            }),
            Action::Release { button } => out.edges.push(ButtonEdge {
                button,
                edge: Edge::Release,
            }),
            Action::Look { yaw_deg, pitch_deg } => {
                self.pending_motion.x += yaw_deg;
                self.pending_motion.y += pitch_deg;
            }
            Action::MoveDelta { forward, strafe } => {
                self.pending_movement.forward += forward;
                self.pending_movement.strafe += strafe;
            }
        }
    }
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
        let mut adapter = InputAdapter::with_actions(vec![
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
        let mut adapter = InputAdapter::with_actions(vec![
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
        let mut adapter = InputAdapter::with_actions(vec![key(3, Key::Forward)]);
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
        let mut adapter = InputAdapter::with_actions(vec![
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
        let mut adapter = InputAdapter::with_actions(vec![
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
        let mut adapter = InputAdapter::with_actions(vec![
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
        let mut adapter = InputAdapter::with_actions(vec![
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
        let mut adapter = InputAdapter::with_actions(vec![key(0, Key::Forward)]);
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
        let mut adapter = InputAdapter::with_actions(vec![key(5, Key::Forward)]);
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
}
