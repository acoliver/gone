//! Architecture boundary policy (issues #4 and #5 stage A).
//!
//! Two package-graph rules read the resolved workspace graph from
//! `cargo metadata --format-version 1` — dependency-edge checks, not import
//! greps — and fail on direct declarations (including optional,
//! not-yet-enabled ones) and, for the first rule, on any transitive path:
//!
//! 1. `gone_sim` is the pure simulation crate: it must never reach Bevy (the
//!    `bevy` crate or any `bevy_*` crate), `gone_app`, or `gone_harness`
//!    through a normal or build dependency edge.
//! 2. `gone_harness` is the runner: it must never declare `gone_sim` as a
//!    direct normal or build dependency. Direct only, because the legitimate
//!    shape is `gone_harness -> gone_app -> gone_sim` (the runner consumes
//!    the app's protocol surface, and the app is the game); a direct edge is
//!    the only way runner source can name gameplay types.
//!
//! The third rule is source-level, because cargo's graph cannot see modules:
//! the `gone_app` harness protocol module (the surface `gone_harness`
//! re-exports) must not reference `gone_sim` in its source. That check lives
//! in [`crate::protocol_surface`].
//!
//! Every rule fails closed: unreadable input, malformed metadata, or a
//! missing guarded crate is an error, never a pass.

use std::collections::{BTreeMap, BTreeSet, VecDeque};
use std::path::Path;

use crate::metadata_graph::{DepGraph, extract_graph};
use crate::process::{CommandFailed, CommandPlan};
use crate::protocol_surface;

/// The crate whose dependency subgraph is guarded.
pub const GUARDED_CRATE: &str = "gone_sim";

/// The runner crate, guarded against a direct gameplay dependency.
pub const RUNNER_CRATE: &str = "gone_harness";

/// A boundary violation: the banned package and the dependency path from
/// `gone_sim` that reaches it. A two-element path is a direct declaration.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Violation {
    pub package: String,
    pub path: Vec<String>,
}

impl std::fmt::Display for Violation {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let origin = self.path.first().map_or(GUARDED_CRATE, String::as_str);
        if self.path.len() <= 2 {
            write!(
                f,
                "{origin} directly depends on banned package `{}`",
                self.package
            )
        } else {
            write!(
                f,
                "{origin} transitively depends on banned package `{}` via {}",
                self.package,
                self.path.join(" -> ")
            )
        }
    }
}

/// Is `name` a package `gone_sim` must never reach?
#[must_use]
pub fn is_banned(name: &str) -> bool {
    name == "bevy" || name.starts_with("bevy_") || name == "gone_app" || name == "gone_harness"
}

/// The one package `gone_harness` must never declare directly: the simulation
/// crate. Anything gameplay-shaped in the runner has to arrive through
/// `gone_app`'s protocol surface instead.
#[must_use]
pub fn is_banned_for_runner(name: &str) -> bool {
    name == GUARDED_CRATE
}

/// Rules printed above any violation list so a failure states the whole
/// policy, not just the offending edge.
const BOUNDARY_RULES: &[&str] = &[
    "`gone_sim` must not reach bevy, bevy_*, gone_app, or gone_harness via \
     normal or build dependency edges (direct or transitive)",
    "`gone_harness` must not depend on `gone_sim` via a direct normal or \
     build dependency edge",
    "the `gone_app` harness protocol module (crates/gone_app/src/harness) \
     must not reference `gone_sim` in source",
];

/// Run the architecture policy: resolve the workspace graph via
/// `cargo metadata`, scan the harness protocol module sources, and fail if
/// any boundary rule is violated.
///
/// # Errors
/// Returns `CommandFailed` if `cargo metadata` fails, its output cannot be
/// parsed (fail closed), a guarded crate is missing from the graph, a
/// violation is found, or the protocol module cannot be read (fail closed).
pub fn run_repo_check(root: &Path) -> Result<(), CommandFailed> {
    let args = vec!["check".to_string(), "architecture".to_string()];
    let output = metadata_plan(root).run_captured()?;
    let text = String::from_utf8_lossy(&output.stdout);
    let graph = extract_graph(&text).map_err(|err| gate_failure(&args, err))?;
    let graph_violations = find_violations(&graph).map_err(|err| gate_failure(&args, err))?;
    let surface_violations =
        protocol_surface::violations_from_disk(root).map_err(|err| gate_failure(&args, err))?;
    if graph_violations.is_empty() && surface_violations.is_empty() {
        return Ok(());
    }
    let mut stderr = String::from("architecture boundary violations:\n");
    for rule in BOUNDARY_RULES {
        std::fmt::Write::write_fmt(&mut stderr, format_args!("  rule: {rule}\n")).ok();
    }
    for violation in &graph_violations {
        std::fmt::Write::write_fmt(&mut stderr, format_args!("  {violation}\n")).ok();
    }
    for violation in &surface_violations {
        std::fmt::Write::write_fmt(&mut stderr, format_args!("  {violation}\n")).ok();
    }
    Err(CommandFailed {
        program: "xtask".into(),
        args,
        status: Some(1),
        stdout: Vec::new(),
        stderr: stderr.into_bytes(),
    })
}

/// Package a fail-closed policy error (metadata parse, missing crate,
/// unreadable module) as a `CommandFailed` for the `check architecture`
/// invocation.
fn gate_failure(args: &[String], message: String) -> CommandFailed {
    CommandFailed {
        program: "xtask".into(),
        args: args.to_vec(),
        status: Some(1),
        stdout: Vec::new(),
        stderr: message.into_bytes(),
    }
}

fn metadata_plan(root: &Path) -> CommandPlan {
    CommandPlan::new("cargo")
        .args(["metadata", "--format-version", "1"])
        .current_dir(root)
}

/// Find every graph-level boundary violation, shortest path first: for
/// `gone_sim`, banned direct declarations (including optional, disabled ones)
/// plus every banned package reachable over normal/build edges; for
/// `gone_harness`, direct normal/build declarations of `gone_sim` only.
///
/// # Errors
/// Returns a message when a guarded crate is absent from the graph (fail
/// closed).
pub fn find_violations(graph: &DepGraph) -> Result<Vec<Violation>, String> {
    let mut violations = guarded_crate_violations(graph)?;
    violations.extend(runner_direct_violations(graph)?);
    Ok(violations)
}

/// The `gone_sim` subgraph rule: banned direct declarations plus every banned
/// package reachable over normal/build edges, shortest path first.
fn guarded_crate_violations(graph: &DepGraph) -> Result<Vec<Violation>, String> {
    let Some(direct) = graph.edges.get(GUARDED_CRATE) else {
        return Err(format!(
            "cargo metadata does not contain `{GUARDED_CRATE}`; cannot check architecture boundaries"
        ));
    };
    // package -> shortest path from gone_sim; declared paths come first so a
    // direct declaration is never shadowed by a longer route.
    let mut paths: BTreeMap<String, Vec<String>> = BTreeMap::new();
    for edge in direct {
        if edge.normal_or_build && is_banned(&edge.to) {
            paths.insert(
                edge.to.clone(),
                vec![GUARDED_CRATE.to_string(), edge.to.clone()],
            );
        }
    }
    let declared = graph.declared.get(GUARDED_CRATE);
    if let Some(declared) = declared {
        for dep in declared {
            if dep.normal_or_build && is_banned(&dep.name) {
                paths
                    .entry(dep.name.clone())
                    .or_insert_with(|| vec![GUARDED_CRATE.to_string(), dep.name.clone()]);
            }
        }
    }
    for (package, path) in reachable_banned_paths(graph) {
        paths.entry(package).or_insert(path);
    }
    Ok(paths
        .into_iter()
        .map(|(package, path)| Violation { package, path })
        .collect())
}

/// The runner rule: `gone_harness` must not declare `gone_sim` as a normal or
/// build dependency, directly. Transitive reachability through `gone_app` is
/// the intended shape and is not a violation; declared-but-disabled optional
/// edges are flagged like resolved ones.
fn runner_direct_violations(graph: &DepGraph) -> Result<Vec<Violation>, String> {
    let Some(edges) = graph.edges.get(RUNNER_CRATE) else {
        return Err(format!(
            "cargo metadata does not contain `{RUNNER_CRATE}`; cannot check architecture boundaries"
        ));
    };
    let mut paths: BTreeMap<String, Vec<String>> = BTreeMap::new();
    for edge in edges {
        if edge.normal_or_build && is_banned_for_runner(&edge.to) {
            paths.insert(
                edge.to.clone(),
                vec![RUNNER_CRATE.to_string(), edge.to.clone()],
            );
        }
    }
    if let Some(declared) = graph.declared.get(RUNNER_CRATE) {
        for dep in declared {
            if dep.normal_or_build && is_banned_for_runner(&dep.name) {
                paths
                    .entry(dep.name.clone())
                    .or_insert_with(|| vec![RUNNER_CRATE.to_string(), dep.name.clone()]);
            }
        }
    }
    Ok(paths
        .into_iter()
        .map(|(package, path)| Violation { package, path })
        .collect())
}

/// Breadth-first search over normal/build edges with parent tracking, so
/// each reachable banned package reports the exact path to it.
fn reachable_banned_paths(graph: &DepGraph) -> BTreeMap<String, Vec<String>> {
    let mut parent: BTreeMap<String, String> = BTreeMap::new();
    let mut visited: BTreeSet<String> = BTreeSet::from([GUARDED_CRATE.to_string()]);
    let mut queue: VecDeque<String> = VecDeque::from([GUARDED_CRATE.to_string()]);
    let mut found: BTreeMap<String, Vec<String>> = BTreeMap::new();
    while let Some(node) = queue.pop_front() {
        let Some(edges) = graph.edges.get(&node) else {
            continue;
        };
        for edge in edges {
            if !edge.normal_or_build || !visited.insert(edge.to.clone()) {
                continue;
            }
            parent.insert(edge.to.clone(), node.clone());
            if is_banned(&edge.to) && edge.to != GUARDED_CRATE {
                found.insert(edge.to.clone(), reconstruct_path(&parent, &edge.to));
            }
            queue.push_back(edge.to.clone());
        }
    }
    found
}

fn reconstruct_path(parent: &BTreeMap<String, String>, end: &str) -> Vec<String> {
    let mut path = vec![end.to_string()];
    let mut current = end;
    while let Some(next) = parent.get(current) {
        path.push(next.clone());
        current = next;
    }
    path.reverse();
    path
}

#[cfg(test)]
mod tests {
    use super::{
        GUARDED_CRATE, RUNNER_CRATE, Violation, find_violations, is_banned, is_banned_for_runner,
    };
    use crate::metadata_graph::extract_graph;
    use crate::test_support::fixture_graph;

    #[test]
    fn banned_names_cover_bevy_family_and_sibling_crates() {
        assert!(is_banned("bevy"));
        assert!(is_banned("bevy_ecs"));
        assert!(is_banned("bevy_internal"));
        assert!(is_banned("gone_app"));
        assert!(is_banned("gone_harness"));
        assert!(!is_banned("bevylike"));
        assert!(!is_banned("serde"));
        assert!(!is_banned("gone_sim"));
    }

    #[test]
    fn clean_graph_has_no_violations() {
        let graph = fixture_graph(&[
            ("gone_sim", &[("serde", "normal")]),
            ("gone_harness", &[]),
            ("serde", &[]),
        ]);
        assert_eq!(find_violations(&graph).expect("roots present"), Vec::new());
    }

    #[test]
    fn direct_normal_edge_is_flagged_once() {
        let graph = fixture_graph(&[
            ("gone_sim", &[("bevy_ecs", "normal")]),
            ("gone_harness", &[]),
            ("bevy_ecs", &[]),
        ]);
        assert_eq!(
            find_violations(&graph).expect("root present"),
            vec![Violation {
                package: "bevy_ecs".into(),
                path: vec!["gone_sim".into(), "bevy_ecs".into()],
            }]
        );
    }

    #[test]
    fn direct_build_edge_is_flagged() {
        let graph = fixture_graph(&[
            ("gone_sim", &[("bevy_app", "build")]),
            ("gone_harness", &[]),
            ("bevy_app", &[]),
        ]);
        assert_eq!(
            find_violations(&graph).expect("root present"),
            vec![Violation {
                package: "bevy_app".into(),
                path: vec!["gone_sim".into(), "bevy_app".into()],
            }]
        );
    }

    #[test]
    fn dev_only_edge_to_sibling_is_allowed() {
        let graph = fixture_graph(&[
            ("gone_sim", &[("gone_harness", "dev")]),
            ("gone_harness", &[]),
        ]);
        assert_eq!(find_violations(&graph).expect("root present"), Vec::new());
    }

    #[test]
    fn transitive_bevy_path_is_flagged_with_full_path() {
        let graph = fixture_graph(&[
            ("gone_sim", &[("helper", "normal")]),
            ("gone_harness", &[]),
            ("helper", &[("bevy_core", "normal")]),
            ("bevy_core", &[]),
        ]);
        assert_eq!(
            find_violations(&graph).expect("root present"),
            vec![Violation {
                package: "bevy_core".into(),
                path: vec!["gone_sim".into(), "helper".into(), "bevy_core".into()],
            }]
        );
    }

    #[test]
    fn cycles_do_not_confuse_the_search() {
        let graph = fixture_graph(&[
            ("gone_sim", &[("a", "normal")]),
            ("gone_harness", &[]),
            ("a", &[("b", "normal")]),
            ("b", &[("a", "normal"), ("gone_app", "normal")]),
            ("gone_app", &[]),
        ]);
        assert_eq!(
            find_violations(&graph).expect("root present"),
            vec![Violation {
                package: "gone_app".into(),
                path: vec!["gone_sim".into(), "a".into(), "b".into(), "gone_app".into()],
            }]
        );
    }

    #[test]
    fn missing_guarded_crate_fails_closed() {
        let graph = fixture_graph(&[("serde", &[])]);
        let err = find_violations(&graph).expect_err("missing root must fail");
        assert!(err.contains(GUARDED_CRATE));
    }

    #[test]
    fn empty_dep_kinds_are_treated_as_restricted() {
        let json = "{\"packages\":[{\"id\":\"registry+https://example#gone_sim@0.1.0\",\
                    \"name\":\"gone_sim\",\"dependencies\":[]},\
                    {\"id\":\"registry+https://example#gone_harness@0.1.0\",\
                    \"name\":\"gone_harness\",\"dependencies\":[]},\
                    {\"id\":\"registry+https://example#bevy_ecs@0.1.0\",\"name\":\"bevy_ecs\",\
                    \"dependencies\":[]}],\"resolve\":{\"nodes\":[\
                    {\"id\":\"registry+https://example#gone_sim@0.1.0\",\"deps\":[\
                    {\"name\":\"bevy_ecs\",\"pkg\":\"registry+https://example#bevy_ecs@0.1.0\",\
                    \"dep_kinds\":[]}]},\
                    {\"id\":\"registry+https://example#gone_harness@0.1.0\",\"deps\":[]}]}}";
        let graph = extract_graph(json).expect("parses");
        assert_eq!(
            find_violations(&graph).expect("root present"),
            vec![Violation {
                package: "bevy_ecs".into(),
                path: vec!["gone_sim".into(), "bevy_ecs".into()],
            }]
        );
    }

    #[test]
    fn optional_disabled_declaration_is_flagged() {
        // A declared-but-disabled optional bevy dependency never appears in
        // the resolved `deps`, only in `dependencies` — the gate must still
        // catch it.
        let json = "{\"packages\":[{\"id\":\"registry+https://example#gone_sim@0.1.0\",\
                    \"name\":\"gone_sim\",\"dependencies\":[{\"name\":\"bevy\",\"kind\":null,\
                    \"optional\":true}]},\
                    {\"id\":\"registry+https://example#gone_harness@0.1.0\",\
                    \"name\":\"gone_harness\",\"dependencies\":[]}],\"resolve\":{\"nodes\":[\
                    {\"id\":\"registry+https://example#gone_sim@0.1.0\",\"deps\":[]},\
                    {\"id\":\"registry+https://example#gone_harness@0.1.0\",\"deps\":[]}]}}";
        let graph = extract_graph(json).expect("parses");
        assert_eq!(
            find_violations(&graph).expect("root present"),
            vec![Violation {
                package: "bevy".into(),
                path: vec!["gone_sim".into(), "bevy".into()],
            }]
        );
    }

    #[test]
    fn optional_disabled_dev_declaration_is_allowed() {
        let json = "{\"packages\":[{\"id\":\"registry+https://example#gone_sim@0.1.0\",\
                    \"name\":\"gone_sim\",\"dependencies\":[{\"name\":\"gone_harness\",\
                    \"kind\":\"dev\"}]},{\"id\":\"registry+https://example#gone_harness@0.1.0\",\
                    \"name\":\"gone_harness\",\"dependencies\":[]}],\"resolve\":{\"nodes\":[\
                    {\"id\":\"registry+https://example#gone_sim@0.1.0\",\"deps\":[]},\
                    {\"id\":\"registry+https://example#gone_harness@0.1.0\",\"deps\":[]}]}}";
        let graph = extract_graph(json).expect("parses");
        assert_eq!(find_violations(&graph).expect("root present"), Vec::new());
    }

    #[test]
    fn violation_display_names_direct_and_transitive_shapes() {
        let direct = Violation {
            package: "bevy".into(),
            path: vec!["gone_sim".into(), "bevy".into()],
        };
        assert_eq!(
            direct.to_string(),
            "gone_sim directly depends on banned package `bevy`"
        );
        let transitive = Violation {
            package: "bevy_core".into(),
            path: vec!["gone_sim".into(), "helper".into(), "bevy_core".into()],
        };
        assert_eq!(
            transitive.to_string(),
            "gone_sim transitively depends on banned package `bevy_core` via gone_sim -> helper -> bevy_core"
        );
    }

    #[test]
    fn runner_bans_only_the_simulation_crate() {
        assert!(is_banned_for_runner("gone_sim"));
        assert!(!is_banned_for_runner("bevy"));
        assert!(!is_banned_for_runner("gone_app"));
        assert!(!is_banned_for_runner("serde"));
        assert!(!is_banned_for_runner(RUNNER_CRATE));
    }

    #[test]
    fn runner_direct_normal_dep_on_gone_sim_is_flagged() {
        let graph = fixture_graph(&[
            ("gone_harness", &[("gone_sim", "normal")]),
            ("gone_sim", &[]),
        ]);
        assert_eq!(
            find_violations(&graph).expect("roots present"),
            vec![Violation {
                package: "gone_sim".into(),
                path: vec!["gone_harness".into(), "gone_sim".into()],
            }]
        );
    }

    #[test]
    fn runner_direct_build_dep_on_gone_sim_is_flagged() {
        let graph = fixture_graph(&[
            ("gone_harness", &[("gone_sim", "build")]),
            ("gone_sim", &[]),
        ]);
        assert_eq!(
            find_violations(&graph).expect("roots present"),
            vec![Violation {
                package: "gone_sim".into(),
                path: vec!["gone_harness".into(), "gone_sim".into()],
            }]
        );
    }

    #[test]
    fn runner_transitive_path_through_gone_app_is_allowed() {
        // The legitimate shape: the runner consumes the app's protocol
        // surface, and the app is the game, so gone_sim stays reachable
        // transitively without a direct runner edge.
        let graph = fixture_graph(&[
            ("gone_harness", &[("gone_app", "normal")]),
            ("gone_app", &[("gone_sim", "normal")]),
            ("gone_sim", &[]),
        ]);
        assert_eq!(find_violations(&graph).expect("roots present"), Vec::new());
    }

    #[test]
    fn runner_dev_dep_on_gone_sim_is_allowed() {
        let graph = fixture_graph(&[("gone_harness", &[("gone_sim", "dev")]), ("gone_sim", &[])]);
        assert_eq!(find_violations(&graph).expect("roots present"), Vec::new());
    }

    #[test]
    fn runner_optional_disabled_gone_sim_declaration_is_flagged() {
        let json = "{\"packages\":[{\"id\":\"registry+https://example#gone_harness@0.1.0\",\
                    \"name\":\"gone_harness\",\"dependencies\":[{\"name\":\"gone_sim\",\
                    \"kind\":null,\"optional\":true}]},\
                    {\"id\":\"registry+https://example#gone_sim@0.1.0\",\"name\":\"gone_sim\",\
                    \"dependencies\":[]}],\"resolve\":{\"nodes\":[\
                    {\"id\":\"registry+https://example#gone_harness@0.1.0\",\"deps\":[]},\
                    {\"id\":\"registry+https://example#gone_sim@0.1.0\",\"deps\":[]}]}}";
        let graph = extract_graph(json).expect("parses");
        assert_eq!(
            find_violations(&graph).expect("roots present"),
            vec![Violation {
                package: "gone_sim".into(),
                path: vec!["gone_harness".into(), "gone_sim".into()],
            }]
        );
    }

    #[test]
    fn runner_missing_from_graph_fails_closed() {
        let graph = fixture_graph(&[("gone_sim", &[])]);
        let err = find_violations(&graph).expect_err("missing runner must fail");
        assert!(err.contains(RUNNER_CRATE));
    }

    #[test]
    fn violation_display_names_the_runner_origin() {
        let violation = Violation {
            package: "gone_sim".into(),
            path: vec!["gone_harness".into(), "gone_sim".into()],
        };
        assert_eq!(
            violation.to_string(),
            "gone_harness directly depends on banned package `gone_sim`"
        );
    }
}
