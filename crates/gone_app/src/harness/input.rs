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

/// The synthetic key name [`ButtonEdge::move_delta`] uses so movement and buttons
/// share one exactly-once delivery stream.
pub const MOVE_DELTA_MARKER: &str = "__move";

/// A single buffered button edge delivered to exactly one fixed update.
#[derive(Clone, Debug, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct ButtonEdge {
    /// Button the edge applies to.
    pub button: Button,
    /// Press or release.
    pub edge: Edge,
}

impl ButtonEdge {
    /// A synthetic edge carrying a movement delta (the app reads it as the move
    /// vector for this fixed update). The vector itself lives in [`Step::motion`];
    /// this edge marks "movement happened this tick" so movement and buttons share one
    /// exactly-once delivery stream.
    #[must_use]
    pub fn move_delta(_forward: f32, _strafe: f32) -> Self {
        Self {
            button: Button::Key(Key::Other(MOVE_DELTA_MARKER.to_owned())),
            edge: Edge::Press,
        }
    }
}

/// Input events name their edge so opposite edges of one button are
/// distinguishable in events, checkpoints, and compare streams.
impl fmt::Display for ButtonEdge {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        if self.button == Button::Key(Key::Other(MOVE_DELTA_MARKER.to_owned())) {
            return write!(f, "move-delta");
        }
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
    /// Move: movement is a 2D vector in world axes (forward/strafe).
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
    /// Wait in fixed-update terms: no new input, just let the clock advance.
    Wait {
        /// Number of ticks to hold still.
        ticks: u64,
    },
    /// Wait until the logical clock reaches `tick` (inclusive), for long-form
    /// pacing.
    WaitUntilTick {
        /// Target tick.
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

/// Pure scripted-input state machine. Not an ECS component: the app owns one as a
/// resource and drives it exactly once per fixed update.
#[derive(Clone, Debug)]
pub struct InputAdapter {
    actions: VecDeque<ScriptedAction>,
    /// Pending button edges, drained one tick at a time.
    edge_queue: VecDeque<ButtonEdge>,
    /// Motion to deliver on the next fixed update.
    pending_motion: Delta,
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
    /// edges whose turn it is) and the motion for this tick. Actions whose tick is not
    /// yet reached stay queued.
    ///
    /// # Panics
    /// Panics if the front of the action queue is missing after checking it, which is
    /// unreachable: `front` was just inspected and non-empty.
    #[must_use]
    pub fn step(&mut self) -> Step {
        let mut out = Step {
            edges: Vec::new(),
            motion: Delta::zero(),
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
                out.edges.push(ButtonEdge::move_delta(forward, strafe));
            }
            Action::Wait { .. } | Action::WaitUntilTick { .. } => {}
        }
    }
}

/// One fixed update's worth of adapter output.
#[derive(Default, Debug)]
pub struct Step {
    /// Edges to deliver (button presses/releases + synthetic move-delta edges).
    pub edges: Vec<ButtonEdge>,
    /// Look motion to deliver.
    pub motion: Delta,
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

    /// Wait at `tick`.
    #[must_use]
    pub fn wait(tick: u64, ticks: u64) -> Self {
        Self {
            tick,
            action: Action::Wait { ticks },
        }
    }

    /// Wait until the logical clock reaches `tick` (inclusive).
    #[must_use]
    pub fn wait_until(tick: u64, target: u64) -> Self {
        Self {
            tick,
            action: Action::WaitUntilTick { tick: target },
        }
    }
}

#[cfg(test)]
mod tests {
    use super::{
        Action, Button, ButtonEdge, Delta, Edge, InputAdapter, Key, MouseButton, ScriptedAction,
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
    fn move_delta_edge_describes_itself() {
        assert_eq!(ButtonEdge::move_delta(1.0, 0.0).to_string(), "move-delta");
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
        let mut adapter = InputAdapter::with_actions(vec![
            key(0, Key::Forward),
            ScriptedAction::release(1, Key::Forward),
        ]);
        let first = adapter.step();
        assert_eq!(first.edges.len(), 1);
        assert_eq!(first.edges[0].edge, Edge::Press);
        let _ = adapter.step();
        // Draining a tick with nothing due delivers nothing a third time.
        assert_eq!(adapter.step().edges.len(), 0);
    }

    #[test]
    fn zero_fixed_updates_deliver_nothing_and_preserve_edges() {
        // Simulates a rendered frame in which no fixed update ran: stepping the
        // clock from nothing delivers nothing, and a later step still sees the edge.
        let mut adapter = InputAdapter::with_actions(vec![key(0, Key::Forward)]);
        let _ = adapter.step();
        assert_eq!(adapter.step().edges.len(), 0);
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
    fn wait_actions_wait_without_new_edges() {
        let mut adapter = InputAdapter::with_actions(vec![
            ScriptedAction {
                tick: 3,
                action: Action::Wait { ticks: 5 },
            },
            key(3, Key::Activate),
        ]);
        // Stepping 0..=2 holds the key; the third step's clock is 3 where both
        // the wait and the press fire, delivering exactly one edge.
        let s3 = adapter.step();
        assert!(s3.edges.is_empty());
        let s4 = adapter.step();
        assert!(s4.edges.is_empty());
        let s5 = adapter.step();
        assert!(s5.edges.is_empty());
        let s6 = adapter.step();
        assert_eq!(s6.edges.len(), 1);
        let _ = adapter.step();
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
