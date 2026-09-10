//! Shared fixture helpers for xtask unit tests. Compiled only under `cfg(test)`;
//! sibling modules gate their use the same way.

use std::path::PathBuf;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

/// Create a unique directory under the system temp dir.
///
/// Uniqueness comes from pid + nanos + an in-process counter, so concurrent
/// test binaries and threads can never alias each other's fixtures.
#[must_use]
pub fn unique_temp_dir(tag: &str) -> PathBuf {
    static COUNTER: AtomicU64 = AtomicU64::new(0);
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |d| d.as_nanos());
    let n = COUNTER.fetch_add(1, Ordering::Relaxed);
    let dir = std::env::temp_dir().join(format!(
        "gone-xtask-{tag}-{}-{nanos}-{n}",
        std::process::id()
    ));
    std::fs::create_dir_all(&dir).expect("create temp fixture dir");
    dir
}
