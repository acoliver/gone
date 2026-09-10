//! Bevy glue layer for the game `gone`.
//!
//! Contract: this crate renders state owned by `gone_sim` and never owns
//! simulation state itself. The Bevy dependency arrives with issue #6; until
//! then this crate stays a dependency-free placeholder that must build on
//! every supported target.

/// Render-side mirror of one ship, kept in sync from `gone_sim` state.
/// Placeholder for the real component types that arrive with issue #6.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct RenderedShip {
    /// Mirrored hull integrity; drives the damage visuals.
    hull: u32,
}

impl RenderedShip {
    /// Creates the mirror from the current simulation hull value.
    #[must_use]
    pub fn from_hull(hull: u32) -> Self {
        Self { hull }
    }

    /// Hull integrity last mirrored from the simulation.
    #[must_use]
    pub fn hull(&self) -> u32 {
        self.hull
    }
}

/// Tests for `RenderedShip`.
#[cfg(test)]
mod tests {
    use super::RenderedShip;

    /// The mirror carries exactly the hull value it was created from.
    #[test]
    fn mirror_carries_hull_value() {
        let rendered = RenderedShip::from_hull(42);

        assert_eq!(rendered.hull(), 42);
        assert_ne!(rendered, RenderedShip::from_hull(0));
    }
}
