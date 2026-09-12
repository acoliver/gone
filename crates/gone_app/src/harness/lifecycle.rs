//! Lifecycle-lane protocol surface (issue #5 / stage B).
//!
//! The lifecycle lane verifies app-lifecycle outcomes as native window
//! observations: focus loss clears pending/held input, reacquisition leaves
//! no stuck motion or mouse jump, a window resize updates the recorded
//! surface/capture dimensions without restarting the phase timeline, and the
//! run still closes cleanly. The scenario's `lifecycle` section is the scene
//! description: it pins the tick of each window drive (focus loss,
//! reacquisition, resize), the app performs them through its real window
//! surface, and the observations enter the report as tick-stamped events.
//!
//! This module owns the lane's scenario section and the input adapter's
//! focus-clearing extension (an inherent impl on [`InputAdapter`], kept here
//! so the shared adapter file stays within the source-size gate); the
//! `TimedEvent` variants the observations use live with the report schema.

use super::input::{Button, Edge, InputAdapter};

/// One lifecycle window drive pinned to a tick.
#[derive(Clone, Copy, Debug, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct LifecycleStep {
    /// The tick whose update performs the drive. The native window event the
    /// drive causes (focus change, resize) arrives across later updates at
    /// the OS's own cadence; the report's observations carry their own
    /// stamps, so the scripted tick is the earliest moment the effect can
    /// be observed, never a promise about its exact tick.
    pub at_tick: u64,
}

/// The resize drive: the window's new size in physical pixels, at the lane's
/// forced scale factor of 1.0, so logical pixels equal physical pixels.
#[derive(Clone, Copy, Debug, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct LifecycleResize {
    /// The tick whose update performs the resize.
    pub at_tick: u64,
    /// New window width in physical pixels (the lane pins the scale factor
    /// to 1.0, so the logical width matches).
    pub width: u32,
    /// New window height in physical pixels (logical matches at the lane's
    /// scale factor).
    pub height: u32,
}

/// The lifecycle lane's predeclared window drives. Required exactly when the
/// scenario mode is `lifecycle` (enforced by `parse_scenario`, like the
/// calibration section).
#[derive(Clone, Copy, Debug, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct LifecycleParams {
    /// The focus-loss drive: the app hides its window, and the OS resigns
    /// the window's key status, delivering a real unfocused observation.
    pub focus_loss: LifecycleStep,
    /// The reacquisition drive: the app re-shows its window and requests
    /// focus, and the OS delivers a real focused observation.
    pub reacquire: LifecycleStep,
    /// The resize drive: the app resizes its window through the OS surface.
    pub resize: LifecycleResize,
}

impl LifecycleParams {
    /// Validate the cross-field ordering: the reacquisition may not precede
    /// the focus loss, the resize may not precede the reacquisition, and
    /// the resize must name a positive window size (a zero extent cannot
    /// reach here as a real resize and would only encode an authoring
    /// error).
    ///
    /// # Errors
    /// A message naming the offending field and both ticks (or extents).
    pub fn validate(&self) -> Result<(), String> {
        if self.reacquire.at_tick <= self.focus_loss.at_tick {
            return Err(format!(
                "lifecycle reacquire tick {} must be after the focus-loss tick {}",
                self.reacquire.at_tick, self.focus_loss.at_tick
            ));
        }
        if self.resize.at_tick <= self.reacquire.at_tick {
            return Err(format!(
                "lifecycle resize tick {} must be after the reacquire tick {}",
                self.resize.at_tick, self.reacquire.at_tick
            ));
        }
        if self.resize.width == 0 || self.resize.height == 0 {
            return Err(format!(
                "lifecycle resize size {}x{} must be positive",
                self.resize.width, self.resize.height
            ));
        }
        Ok(())
    }
}

/// What one input-layer focus clear did: how many buffered-but-undelivered
/// edges were dropped, and which held buttons the clear released (each
/// released button's synthetic release edge joins the adapter's exactly-once
/// delivery stream, so the next step delivers it exactly once).
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct InputClearing {
    /// Buffered-but-undelivered button edges discarded by the clear.
    pub dropped_edges: usize,
    /// Held buttons the clear released, in held order.
    pub released: Vec<Button>,
}

impl InputAdapter {
    /// Clear the input layer's pending and held input: drop buffered
    /// edges and any undelivered motion or movement, and release every
    /// held button by queueing its synthetic release edge. The synthetic
    /// releases deliver through the adapter's ordinary exactly-once
    /// stream (the step after this call), so the run's input timeline
    /// shows the held key going up at the clear — the scripted analog of
    /// a real device's stuck key being released when the window loses
    /// focus. A second clear releases nothing: the held set is empty
    /// after the first.
    pub fn clear_held(&mut self) -> InputClearing {
        let dropped_edges = self.edge_queue.len();
        self.edge_queue.clear();
        self.pending_motion = super::input::Delta::zero();
        self.pending_movement = super::input::MoveMotion::zero();
        let released = std::mem::take(&mut self.held);
        for button in &released {
            self.synthetic_releases
                .push_back(release_edge(button.clone()));
        }
        InputClearing {
            dropped_edges,
            released,
        }
    }
}

/// The synthetic release edge for one held button.
#[must_use]
fn release_edge(button: Button) -> super::input::ButtonEdge {
    super::input::ButtonEdge {
        button,
        edge: Edge::Release,
    }
}

#[cfg(test)]
mod tests {
    use super::{InputClearing, LifecycleParams, LifecycleResize, LifecycleStep};
    use crate::harness::input::{Button, Edge, InputAdapter, Key, MoveMotion, ScriptedAction};

    const RATE: u64 = 60;

    /// An adapter over `actions` at the tests' tick rate.
    fn adapter(actions: Vec<ScriptedAction>) -> InputAdapter {
        InputAdapter::with_actions(actions, RATE)
    }

    fn press(tick: u64, key: Key) -> ScriptedAction {
        ScriptedAction::press(tick, key)
    }

    fn release(tick: u64, key: Key) -> ScriptedAction {
        ScriptedAction::release(tick, key)
    }

    fn key_edge(key: Key, edge: Edge) -> String {
        Button::Key(key).to_string()
            + " "
            + match edge {
                Edge::Press => "press",
                Edge::Release => "release",
            }
    }

    #[test]
    fn a_held_key_releases_exactly_once_at_the_clear() {
        // The stuck-key cure: a press with no scripted release is held
        // input; the clear releases it, and the release delivers on the
        // next step (and only there), spelled like any scripted release.
        let mut adapter = adapter(vec![press(0, Key::Forward)]);
        let held = adapter.step();
        assert_eq!(held.edges.len(), 1, "the press delivered while held");
        let clearing = adapter.clear_held();
        assert_eq!(
            clearing,
            InputClearing {
                dropped_edges: 0,
                released: vec![Button::Key(Key::Forward)],
            }
        );
        let next = adapter.step();
        assert_eq!(next.edges.len(), 1, "the synthetic release delivers");
        assert_eq!(
            next.edges[0].to_string(),
            key_edge(Key::Forward, Edge::Release)
        );
        assert!(
            adapter.step().edges.is_empty(),
            "the release delivers exactly once"
        );
    }

    #[test]
    fn a_second_clear_releases_nothing() {
        let mut adapter = adapter(vec![press(0, Key::Activate)]);
        let _ = adapter.step();
        let first = adapter.clear_held();
        assert_eq!(first.released.len(), 1);
        let second = adapter.clear_held();
        assert_eq!(
            second,
            InputClearing {
                dropped_edges: 0,
                released: Vec::new(),
            }
        );
        // The first clear's release is still queued; it delivers intact.
        assert_eq!(adapter.step().edges.len(), 1);
    }

    #[test]
    fn a_released_key_is_not_held_input() {
        // A press whose release already delivered holds nothing: the clear
        // synthesizes no edge for it.
        let mut adapter = adapter(vec![press(0, Key::Forward), release(1, Key::Forward)]);
        let _ = adapter.step();
        let _ = adapter.step();
        let clearing = adapter.clear_held();
        assert!(clearing.released.is_empty(), "nothing was held");
        assert!(adapter.step().edges.is_empty());
    }

    #[test]
    fn the_clear_drops_pending_motion_and_movement() {
        // Look and movement dispatch with their tick and deliver on the
        // same step, so at rest nothing is pending; the clear's contract is
        // still that anything undelivered goes. The held-button release is
        // the observable part this scenario pins.
        let mut adapter = adapter(vec![
            press(0, Key::Forward),
            release(0, Key::Forward),
            ScriptedAction::look(1, 3.0, 1.0),
        ]);
        let first = adapter.step();
        assert_eq!(first.edges.len(), 2, "same-tick press and release");
        let clearing = adapter.clear_held();
        assert!(clearing.released.is_empty());
        assert_eq!(clearing.dropped_edges, 0);
        let second = adapter.step();
        assert_eq!(
            second.motion,
            crate::harness::input::Delta { x: 3.0, y: 1.0 }
        );
        assert_eq!(second.movement, MoveMotion::zero());
    }

    #[test]
    fn multiple_held_keys_release_in_held_order() {
        let mut adapter = adapter(vec![press(0, Key::Forward), press(0, Key::Left)]);
        let _ = adapter.step();
        let clearing = adapter.clear_held();
        assert_eq!(
            clearing.released,
            vec![Button::Key(Key::Forward), Button::Key(Key::Left)]
        );
        let next = adapter.step();
        assert_eq!(next.edges.len(), 2);
        assert_eq!(
            next.edges[0].to_string(),
            key_edge(Key::Forward, Edge::Release)
        );
        assert_eq!(
            next.edges[1].to_string(),
            key_edge(Key::Left, Edge::Release)
        );
    }

    #[test]
    fn lifecycle_params_validate_the_drive_order() {
        let step = |tick: u64| LifecycleStep { at_tick: tick };
        let resize = |tick: u64| LifecycleResize {
            at_tick: tick,
            width: 1280,
            height: 720,
        };
        let valid = LifecycleParams {
            focus_loss: step(40),
            reacquire: step(90),
            resize: resize(140),
        };
        assert_eq!(valid.validate(), Ok(()));
        let reacquire_first = LifecycleParams {
            reacquire: step(40),
            focus_loss: step(90),
            resize: resize(140),
        };
        let err = reacquire_first.validate().expect_err("order must fail");
        assert!(err.contains("reacquire tick"), "{err}");
        let resize_first = LifecycleParams {
            focus_loss: step(40),
            reacquire: step(90),
            resize: resize(90),
        };
        let err = resize_first.validate().expect_err("order must fail");
        assert!(err.contains("resize tick"), "{err}");
        let zero_size = LifecycleParams {
            focus_loss: step(40),
            reacquire: step(90),
            resize: LifecycleResize {
                at_tick: 140,
                width: 0,
                height: 720,
            },
        };
        let err = zero_size
            .validate()
            .expect_err("a nonpositive size must fail");
        assert!(err.contains("positive"), "{err}");
    }
}
