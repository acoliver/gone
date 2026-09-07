//! Play-test harness for the game `gone`.
//!
//! Contract: this crate drives the real `gone_app` binary as an external
//! process and observes it in place of a human play-tester. The process
//! protocol and observation surface land with issue #5; until then this crate
//! stays a dependency-free placeholder.

use std::path::{Path, PathBuf};

/// Where and how to launch the game binary. Placeholder for the full launch
/// specification that arrives with issue #5.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct LaunchSpec {
    /// Filesystem path of the game executable to drive.
    program_path: PathBuf,
}

impl LaunchSpec {
    /// Creates a launch spec pointing at the game executable at `program_path`.
    #[must_use]
    pub fn new(program_path: &Path) -> Self {
        Self {
            program_path: program_path.to_path_buf(),
        }
    }

    /// Path of the game executable to drive.
    #[must_use]
    pub fn program_path(&self) -> &Path {
        &self.program_path
    }
}

/// Tests for `LaunchSpec`.
#[cfg(test)]
mod tests {
    use super::LaunchSpec;
    use std::path::Path;

    /// Paths are stored verbatim: relative stays relative, with no separator
    /// rewriting and no canonicalization.
    #[test]
    fn program_path_is_stored_verbatim() {
        let program = Path::new("target").join("debug").join("gone_app");
        let spec = LaunchSpec::new(&program);

        assert_eq!(spec.program_path(), program);
        assert!(!spec.program_path().is_absolute());
    }
}
