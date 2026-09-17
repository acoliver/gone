//! Shared fixture helpers for xtask unit tests. Compiled only under `cfg(test)`;
//! sibling modules gate their use the same way.

use std::path::PathBuf;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use crate::metadata_graph::{DepGraph, extract_graph};

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

/// Fixture `cargo metadata` JSON for `packages`, where each package is
/// `(name, deps)` and each dep is `(dep name, kind)` with kind `normal`,
/// `build`, or `dev`. Mirrors the cargo 1.98 layout: manifest declarations
/// under `packages[*].dependencies`, resolved edges under
/// `resolve.nodes[*].deps` with `dep_kinds`.
#[must_use]
pub fn fixture_metadata_json(packages: &[(&str, &[(&str, &str)])]) -> String {
    let (package_entries, node_entries): (Vec<String>, Vec<String>) = packages
        .iter()
        .map(|(name, deps)| {
            let id = fixture_package_id(name);
            let declarations = deps
                .iter()
                .map(|(dep, kind)| {
                    let kind_json = if *kind == "normal" {
                        "null".to_string()
                    } else {
                        format!("\"{kind}\"")
                    };
                    format!("{{\"name\":\"{dep}\",\"kind\":{kind_json}}}")
                })
                .collect::<Vec<_>>()
                .join(",");
            let package_entry = format!(
                "{{\"id\":\"{id}\",\"name\":\"{name}\",\"dependencies\":[{declarations}]}}"
            );
            let dep_entries = deps
                .iter()
                .map(|(dep, kind)| {
                    let kind_json = if *kind == "normal" {
                        "null".to_string()
                    } else {
                        format!("\"{kind}\"")
                    };
                    format!(
                        "{{\"name\":\"{dep}\",\"pkg\":\"{}\",\
                         \"dep_kinds\":[{{\"kind\":{kind_json},\"target\":null}}]}}",
                        fixture_package_id(dep)
                    )
                })
                .collect::<Vec<_>>()
                .join(",");
            let node_entry = format!(
                "{{\"id\":\"{id}\",\"dependencies\":[],\"deps\":[{dep_entries}],\"features\":[]}}"
            );
            (package_entry, node_entry)
        })
        .unzip();
    format!(
        "{{\"packages\":[{}],\"resolve\":{{\"nodes\":[{}]}}}}",
        package_entries.join(","),
        node_entries.join(",")
    )
}

/// Opaque-looking cargo package id for a fixture package name.
#[must_use]
pub fn fixture_package_id(name: &str) -> String {
    format!("registry+https://example#{name}@0.1.0")
}

/// Parse fixture metadata into a `DepGraph`, panicking on malformed fixtures
/// (a broken fixture is a broken test, not a policy case).
#[must_use]
pub fn fixture_graph(packages: &[(&str, &[(&str, &str)])]) -> DepGraph {
    extract_graph(&fixture_metadata_json(packages)).expect("fixture metadata must parse")
}
