//! Ship power state for the emergency-lit stasis bay (issue #10).
//!
//! The opening room's premise: the ship's main power is gone, and the bay
//! runs on its emergency cells — the red emergency fixtures are the only
//! sustained light, and everything else (pod systems, indicators, any
//! white work lighting) is unpowered. This module owns the authoritative
//! power state as pure data plus a small machine:
//!
//! * [`PowerState`] names the states the bay can sit in for milestone 1:
//!   [`PowerState::Emergency`] (emergency cells carrying the red
//!   fixtures) and [`PowerState::Dead`] (the cells cut out too; the bay
//!   is dark). There is deliberately no normal-lighting state: milestone
//!   1 cannot reach one, and the enum carries no placeholder for one. A
//!   future repair milestone grows the state space additively, with its
//!   own tests; nothing here reserves room for it.
//! * [`PowerGrid`] is the machine: the bay starts on emergency power, and
//!   the sim's story layer is the only authority that ever changes the
//!   state. Consumers (the app's render bridge) read
//!   [`PowerGrid::state`] and follow it; they never own or set it. The
//!   field is private, there is no setter, and no constructor seeds a
//!   chosen state: the only mutator is the documented transition
//!   [`PowerGrid::cut_emergency_power`].
//! * [`PowerTransition`] reports what one transition attempt did, the
//!   same outcome-or-no-op shape the phase machine uses, so scenario code
//!   can assert the full outcome.
//!
//! # Milestone-1 state graph (documented and frozen)
//!
//! `Emergency --cut_emergency_power--> Dead`. The transition is
//! idempotent: re-delivering the cut to an already dead grid is the
//! no-op [`PowerTransition::Unchanged`], so a story event delivered
//! twice cannot flip the state twice. Nothing in the milestone-1 API
//! moves the state back up: a restored grid is a future milestone's
//! additive transition, and until that lands the graph is one-way
//! downward. The reachable-state test walks the real API and proves the
//! closure is exactly `{Emergency, Dead}` — there is no normal-lighting
//! state to reach and no path that could manufacture one.
//!
//! The fixture-intensity meaning of each state is the single predicate
//! [`PowerState::emergency_fixtures_lit`]: true only in `Emergency`. The
//! render bridge maps that predicate, and the raw state, onto its
//! fixture fades ([`crate::intensity::FixtureFade`]); the sim ships no
//! lighting policy beyond the predicate.
//!
//! Pure: no Bevy, no clocks, no RNG, no render types.

/// The bay's power condition during the opening beat.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Hash)]
pub enum PowerState {
    /// Emergency cells carry the bay: the red emergency fixtures are lit
    /// and everything else is unpowered. The opening beat's state.
    #[default]
    Emergency,
    /// The emergency cells have cut out too: the bay is dark, red
    /// fixtures included. Terminal for milestone 1.
    Dead,
}

impl PowerState {
    /// Whether the red emergency fixtures are lit in this state: true
    /// only in [`PowerState::Emergency`]. The single lighting-meaningful
    /// query the sim ships; the render bridge maps it onto fixture
    /// intensities.
    #[must_use]
    pub const fn emergency_fixtures_lit(self) -> bool {
        match self {
            Self::Emergency => true,
            Self::Dead => false,
        }
    }
}

/// What one power transition attempt did to the grid.
///
/// Every attempt returns exactly one outcome. There is no implicit state
/// and no silent fallback: callers can assert the full outcome.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PowerTransition {
    /// The grid moved from `from` to `to`.
    Advanced {
        /// The state before the attempt.
        from: PowerState,
        /// The state after the attempt.
        to: PowerState,
    },
    /// The grid already sat in the transition's target state, so the
    /// event is already delivered. The state is unchanged: a repeated
    /// story event cannot flip the grid twice.
    Unchanged {
        /// The state the grid held.
        current: PowerState,
    },
}

/// The authoritative power machine for the stasis bay.
///
/// Constructed only through [`PowerGrid::new`] (the opening beat's
/// emergency-powered bay); the field is private and no setter exists, so
/// the state changes only through [`PowerGrid::cut_emergency_power`].
/// Consumers read [`PowerGrid::state`] and follow it: sim-side state
/// changes are the only state changes there are.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct PowerGrid {
    state: PowerState,
}

impl PowerGrid {
    /// The opening beat's grid: emergency cells carrying the bay, red
    /// fixtures lit, everything else unpowered.
    #[must_use]
    pub const fn new() -> Self {
        Self {
            state: PowerState::Emergency,
        }
    }

    /// The current authoritative state. Consumers mirror this value and
    /// update the mirror only from sim output.
    #[must_use]
    pub const fn state(self) -> PowerState {
        self.state
    }

    /// Consume one cut-the-emergency-cells story event.
    ///
    /// In [`PowerState::Emergency`] this kills the cells and advances the
    /// grid to [`PowerState::Dead`]. In `Dead` the event is already
    /// delivered: the no-op [`PowerTransition::Unchanged`], so a repeated
    /// delivery cannot flip the grid twice. Infallible by design: there
    /// is no illegal call shape, and milestone 1 offers no path back up.
    pub fn cut_emergency_power(&mut self) -> PowerTransition {
        match self.state {
            PowerState::Emergency => {
                self.state = PowerState::Dead;
                PowerTransition::Advanced {
                    from: PowerState::Emergency,
                    to: PowerState::Dead,
                }
            }
            PowerState::Dead => PowerTransition::Unchanged {
                current: PowerState::Dead,
            },
        }
    }
}

/// Coverage of the milestone-1 power contract: the initial state, the
/// one-way transition and its idempotence, the authority boundary as far
/// as sim scope can exercise it, and the reachable-state closure that
/// proves no normal-lighting state exists to reach.
#[cfg(test)]
mod tests {
    use super::{PowerGrid, PowerState, PowerTransition};

    /// The opening grid is on emergency power, and `Default` agrees with
    /// `new`.
    #[test]
    fn opening_grid_defaults_to_emergency() {
        let grid = PowerGrid::new();
        assert_eq!(grid.state(), PowerState::Emergency);
        assert_eq!(PowerGrid::default(), grid);
        assert!(grid.state().emergency_fixtures_lit());
    }

    /// The one cut event advances Emergency to Dead exactly once and
    /// names both endpoints in its outcome.
    #[test]
    fn cut_advances_emergency_to_dead_exactly_once() {
        let mut grid = PowerGrid::new();
        assert_eq!(
            grid.cut_emergency_power(),
            PowerTransition::Advanced {
                from: PowerState::Emergency,
                to: PowerState::Dead,
            }
        );
        assert_eq!(grid.state(), PowerState::Dead);
        assert!(!grid.state().emergency_fixtures_lit());
    }

    /// Re-delivered cut events are no-ops: the grid holds Dead no matter
    /// how many times the event arrives.
    #[test]
    fn repeated_cuts_after_death_are_idempotent() {
        let mut grid = PowerGrid::new();
        assert!(matches!(
            grid.cut_emergency_power(),
            PowerTransition::Advanced { .. }
        ));
        for _ in 0..8 {
            assert_eq!(
                grid.cut_emergency_power(),
                PowerTransition::Unchanged {
                    current: PowerState::Dead,
                }
            );
            assert_eq!(grid.state(), PowerState::Dead);
        }
    }

    /// Dead is terminal for milestone 1: after the cut, the only mutator
    /// the API exposes cannot leave Dead, so nothing restores power.
    #[test]
    fn dead_is_terminal_nothing_restores_power() {
        let mut grid = PowerGrid::new();
        grid.cut_emergency_power();
        for _ in 0..16 {
            grid.cut_emergency_power();
            assert_eq!(grid.state(), PowerState::Dead);
        }
    }

    /// The reachable-state closure over the real API is exactly the two
    /// milestone states. This is the negative reachability proof: from
    /// the opening grid, the full mutator walked through repeated
    /// deliveries observes only Emergency and Dead, and neither state
    /// means normal lighting — Emergency lights only the emergency
    /// fixtures, Dead lights nothing. The API cannot manufacture a third
    /// state because none exists to construct and no constructor or
    /// setter accepts one.
    #[test]
    fn no_normal_lighting_state_is_reachable() {
        let mut pending = vec![PowerGrid::new()];
        let mut observed = Vec::new();
        // Exercise every supported event at each reachable state, including
        // terminal-state redelivery, until no new state can be discovered.
        let events = [PowerGrid::cut_emergency_power];
        while let Some(grid) = pending.pop() {
            if observed.contains(&grid.state()) {
                continue;
            }
            observed.push(grid.state());
            match grid.state() {
                PowerState::Emergency => assert!(grid.state().emergency_fixtures_lit()),
                PowerState::Dead => assert!(!grid.state().emergency_fixtures_lit()),
            }
            for event in events {
                let mut next = grid;
                let _ = event(&mut next);
                pending.push(next);
            }
        }
        assert_eq!(
            observed,
            vec![PowerState::Emergency, PowerState::Dead],
            "the reachable closure must be exactly the milestone state set"
        );
        assert!(PowerState::Emergency.emergency_fixtures_lit());
        assert!(!PowerState::Dead.emergency_fixtures_lit());
    }

    /// A consumer mirrors the sim's state and may update the mirror only
    /// from sim output: every transition outcome agrees with the grid's
    /// own read-back, and the mirror never diverges from it. The full
    /// consumer-side enforcement (the app may only follow) lands with the
    /// render bridge's integration tests; this is the sim-scope half.
    #[test]
    fn consumer_mirror_follows_sim_output_only() {
        let mut grid = PowerGrid::new();
        let mut mirror = grid.state();
        assert_eq!(mirror, grid.state());
        let outcome = grid.cut_emergency_power();
        let PowerTransition::Advanced { to, .. } = outcome else {
            panic!("the first cut from the opening grid must advance");
        };
        mirror = to;
        assert_eq!(mirror, grid.state());
        for _ in 0..3 {
            let outcome = grid.cut_emergency_power();
            assert_eq!(
                outcome,
                PowerTransition::Unchanged { current: mirror },
                "a no-op outcome must report exactly the mirrored state"
            );
            assert_eq!(mirror, grid.state());
        }
    }
}
