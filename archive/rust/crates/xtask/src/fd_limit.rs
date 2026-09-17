//! Startup file-descriptor limit raise (issue #17).
//!
//! Linking a workspace of this size spawns many concurrent processes, and on
//! macOS the default soft `RLIMIT_NOFILE` (256) sits below what that fan-out
//! needs, so cargo children intermittently die at link with EMFILE/ENFILE.
//! xtask raises its own soft limit toward the hard limit at startup, before
//! any child can spawn, so gates and harness builds no longer depend on the
//! caller remembering `ulimit -n 10240`.
//!
//! The raise never lowers the limit, never asks for privileges, and stays
//! quiet on success; only an unexpected (non-permission) OS failure is loud.

use std::io;

/// The soft limit xtask aims for when the current limit is lower (issue #17).
///
/// High enough that cargo's concurrent link jobs stop hitting EMFILE on the
/// machines this repo builds on; still raised only toward the hard limit.
pub const MIN_SOFT_TARGET: u64 = 10_240;

/// ENFILE: the system-wide file table is full (errno 23 on macOS and Linux).
const ENFILE: i32 = 23;
/// EMFILE: the per-process file-descriptor limit is hit (errno 24 on macOS
/// and Linux, 24 in the Windows CRT).
const EMFILE: i32 = 24;

/// Appended to spawn-failure output when the OS refused for lack of file
/// descriptors. The startup raise is the real fix; this hint exists for the
/// residual case where the environment still exhausts the limit.
pub const FD_EXHAUSTION_HINT: &str = "\nhint: the OS refused to spawn the child because the file-descriptor limit \
     (RLIMIT_NOFILE) is exhausted; xtask raises its own limit at startup, so run \
     the step through `cargo xtask`, or raise the shell limit (e.g. `ulimit -n 10240`) and retry";

/// Compute the soft limit to raise to from the current soft/hard pair.
///
/// The target is at least [`MIN_SOFT_TARGET`], never above `hard`, and never
/// below the current soft limit, so applying it can only raise.
#[must_use]
pub fn target_soft(soft: u64, hard: u64) -> u64 {
    soft.max(MIN_SOFT_TARGET).min(hard)
}

/// Does this I/O error mean the OS ran out of file descriptors?
///
/// Matches both ENFILE (system-wide table) and EMFILE (per-process limit):
/// the issue reports errno 23, which is ENFILE on macOS and Linux, and both
/// errnos surface the same practical failure for spawned children.
#[must_use]
pub fn is_too_many_open_files(err: &io::Error) -> bool {
    matches!(err.raw_os_error(), Some(ENFILE | EMFILE))
}

/// Raise this process's soft `RLIMIT_NOFILE` toward the hard limit.
///
/// Quiet by design: the ok case returns the effective soft limit without
/// output. A permission shortfall keeps the inherited limit (still ok — the
/// limit is only ever raised toward what the OS already allows). Any other
/// failure is loud: the error names the current limits and the OS error.
///
/// # Errors
/// Returns the current limits and the underlying error when reading or
/// raising the limit fails for a reason other than permission. On platforms
/// without `RLIMIT_NOFILE` the function is an infallible no-op returning 0.
pub fn raise_self() -> Result<u64, String> {
    #[cfg(unix)]
    {
        use rlimit::{Resource, getrlimit, increase_nofile_limit};

        let (soft, hard) = getrlimit(Resource::NOFILE)
            .map_err(|err| format!("could not read the file-descriptor limit: {err}"))?;
        let target = target_soft(soft, hard);
        if target <= soft {
            return Ok(soft);
        }
        match increase_nofile_limit(target) {
            Ok(achieved) => Ok(achieved),
            Err(err) if matches!(err.kind(), io::ErrorKind::PermissionDenied) => Ok(soft),
            Err(err) => Err(format!(
                "could not raise the file-descriptor soft limit \
                 (current soft {soft}, hard {hard}, target {target}): {err}"
            )),
        }
    }
    #[cfg(not(unix))]
    {
        // No RLIMIT_NOFILE on this platform: keep the inherited limit.
        Ok(0)
    }
}

/// Tests for the pure target computation, errno classification, and the
/// startup raise against the real OS limits.
#[cfg(test)]
mod tests {
    use super::{MIN_SOFT_TARGET, is_too_many_open_files, raise_self, target_soft};

    #[test]
    fn below_floor_targets_the_floor() {
        assert_eq!(target_soft(256, u64::MAX), MIN_SOFT_TARGET);
        assert_eq!(target_soft(0, u64::MAX), MIN_SOFT_TARGET);
    }

    #[test]
    fn already_high_limits_are_never_lowered() {
        assert_eq!(target_soft(20_000, 20_000), 20_000);
        assert_eq!(target_soft(500_000, 1_048_576), 500_000);
        assert_eq!(target_soft(u64::MAX, u64::MAX), u64::MAX);
    }

    #[test]
    fn target_is_capped_at_the_hard_limit() {
        assert_eq!(target_soft(256, 2_560), 2_560);
        assert_eq!(target_soft(256, MIN_SOFT_TARGET - 1), MIN_SOFT_TARGET - 1);
    }

    #[test]
    fn target_always_stays_within_current_bounds() {
        for (soft, hard) in [
            (0u64, 0),
            (64, 256),
            (256, 2_560),
            (10_239, u64::MAX),
            (10_240, 10_240),
            (500_000, 1_048_576),
        ] {
            let target = target_soft(soft, hard);
            assert!(target >= soft, "soft={soft} hard={hard} target={target}");
            assert!(target <= hard, "soft={soft} hard={hard} target={target}");
        }
    }

    #[test]
    fn enfile_and_emfile_are_recognized_as_fd_exhaustion() {
        assert!(is_too_many_open_files(&std::io::Error::from_raw_os_error(
            super::ENFILE
        )));
        assert!(is_too_many_open_files(&std::io::Error::from_raw_os_error(
            super::EMFILE
        )));
        assert!(!is_too_many_open_files(&std::io::Error::from_raw_os_error(
            2
        )));
        assert!(!is_too_many_open_files(&std::io::Error::other("no errno")));
    }

    #[cfg(unix)]
    #[test]
    fn startup_raise_meets_the_computed_target() {
        use rlimit::{Resource, getrlimit, setrlimit};

        let (soft_before, hard) = getrlimit(Resource::NOFILE).expect("read RLIMIT_NOFILE");
        if soft_before >= MIN_SOFT_TARGET {
            // The ambient shell is already high; drop the soft limit so the
            // raise below exercises the real syscall path either way.
            // Lowering is always unprivileged-allowed.
            setrlimit(Resource::NOFILE, 64, hard).expect("lower soft limit for the test");
        }
        let (soft_low, hard) = getrlimit(Resource::NOFILE).expect("read RLIMIT_NOFILE");
        let target = target_soft(soft_low, hard);

        let achieved = raise_self().expect("startup raise must succeed on unix");
        let (soft_after, _) = getrlimit(Resource::NOFILE).expect("read RLIMIT_NOFILE");

        assert!(
            soft_after >= soft_low,
            "must never lower the limit (raised from {soft_low}, got {soft_after})"
        );
        assert_eq!(
            soft_after, achieved,
            "the reported limit must match the kernel"
        );
        // Platform permitting (Linux, or macOS with maxfilesperproc >= the
        // floor), the raise reaches the full computed target. A shortfall
        // here means the OS caps below the floor and the machine needs
        // tuning; the test must fail loudly, not swallow the result.
        assert!(
            soft_after >= target,
            "soft {soft_after} did not reach target {target} (started at {soft_low}, hard {hard})"
        );
    }

    #[cfg(not(unix))]
    #[test]
    fn raise_is_a_quiet_noop_without_rlimit_support() {
        assert!(raise_self().is_ok());
    }
}
