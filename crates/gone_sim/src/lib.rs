//! Headless ship-systems simulation for the game `gone`.
//!
//! Contract: this crate owns and advances the authoritative simulation state
//! with no display server, no GPU, and no render code involved. It must never
//! depend on Bevy or any render crate; the architecture gate added in
//! issue #4 enforces that boundary mechanically.
//!
//! The wake phase contract for the opening beat lives in [`phase`]; the
//! frozen first-person controller specification lives in [`controller`]; the
//! stasis pod registry (the layout and state truth the scene is built from)
//! lives in [`pods`]. The static world's axis-aligned collider set lives in
//! [`colliders`], and the swept-capsule per-tick movement resolver built on
//! it lives in [`resolve`].

pub mod colliders;
pub mod controller;
pub mod exit;
pub mod phase;
pub mod pods;
pub mod resolve;

pub use colliders::{Aabb, ColliderError, ColliderSet};
pub use phase::{PhaseError, PhaseTransition, WakePhase};
pub use pods::{
    HatchPlacement, POD_COUNT, Pod, PodId, PodPlacement, PodRegistry, PodRegistryError, PodState,
};
pub use resolve::{Capsule, NonFiniteInput, ResolveError, ResolvedMotion, resolve_motion};

/// Minimal stand-in for a full ship entity: enough state to prove the crate
/// builds and its logic runs standalone until real ship systems arrive.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct ShipState {
    /// Remaining hull integrity, where `0` means destroyed.
    hull: u32,
}

impl ShipState {
    /// Creates a ship with the given hull integrity.
    #[must_use]
    pub fn new(hull: u32) -> Self {
        Self { hull }
    }

    /// Remaining hull integrity, where `0` means destroyed.
    #[must_use]
    pub fn hull(&self) -> u32 {
        self.hull
    }

    /// Applies hull damage, clamped so a ship never falls below zero hull.
    pub fn apply_damage(&mut self, amount: u32) {
        self.hull = self.hull.saturating_sub(amount);
    }

    /// Whether any hull integrity remains.
    #[must_use]
    pub fn is_intact(&self) -> bool {
        self.hull > 0
    }
}

/// Tests for `ShipState`.
#[cfg(test)]
mod tests {
    use super::ShipState;

    /// Damage reduces hull and clamps at total loss.
    #[test]
    fn damage_reduces_hull_and_clamps_at_loss() {
        let mut ship = ShipState::new(10);
        assert!(ship.is_intact());

        ship.apply_damage(4);
        assert_eq!(ship.hull(), 6);
        assert!(ship.is_intact());

        ship.apply_damage(10);
        assert_eq!(ship.hull(), 0);
        assert!(!ship.is_intact());
    }
}
