//! Architecture boundary policy (issue #4).
//!
//! `gone_sim` is the pure simulation crate: it must never reach Bevy (the
//! `bevy` crate or any `bevy_*` crate), `gone_app`, or `gone_harness` through
//! a normal or build dependency edge. The check reads the resolved workspace
//! graph from `cargo metadata --format-version 1` — a dependency-edge check,
//! not an import grep — and fails on direct declarations (including
//! optional, not-yet-enabled ones) and on any transitive path alike.

use std::collections::{BTreeMap, BTreeSet, VecDeque};
use std::path::Path;

use serde_json::Value;

use crate::process::{CommandFailed, CommandPlan};

/// The crate whose dependency subgraph is guarded.
pub const GUARDED_CRATE: &str = "gone_sim";

/// A resolved dependency edge between two packages.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Edge {
    /// Canonical name of the package being depended on.
    pub to: String,
    /// True when any usage of the edge is a normal or build dependency;
    /// dev-only edges are permitted.
    pub normal_or_build: bool,
}

/// A dependency declared in a package manifest, from the `dependencies`
/// array of `cargo metadata` output.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DeclaredDep {
    /// Package name as declared.
    pub name: String,
    /// True for normal or build dependencies; false for dev dependencies.
    pub normal_or_build: bool,
}

/// The workspace dependency graph: resolved edges plus manifest
/// declarations, both keyed by canonical package name.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct DepGraph {
    pub edges: BTreeMap<String, Vec<Edge>>,
    pub declared: BTreeMap<String, Vec<DeclaredDep>>,
}

/// A boundary violation: the banned package and the dependency path from
/// `gone_sim` that reaches it. A two-element path is a direct declaration.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Violation {
    pub package: String,
    pub path: Vec<String>,
}

impl std::fmt::Display for Violation {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        if self.path.len() <= 2 {
            write!(
                f,
                "{GUARDED_CRATE} directly depends on banned package `{}`",
                self.package
            )
        } else {
            write!(
                f,
                "{GUARDED_CRATE} transitively depends on banned package `{}` via {}",
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

/// Run the architecture policy: resolve the workspace graph via
/// `cargo metadata` and fail if `gone_sim` can reach a banned package.
///
/// # Errors
/// Returns `CommandFailed` if `cargo metadata` fails, its output cannot be
/// parsed (fail closed), `gone_sim` is missing from the graph, or a
/// violation is found.
pub fn run_repo_check(root: &Path) -> Result<(), CommandFailed> {
    let args = vec!["check".to_string(), "architecture".to_string()];
    let output = metadata_plan(root).run_captured()?;
    let text = String::from_utf8_lossy(&output.stdout);
    let graph = extract_graph(&text).map_err(|err| CommandFailed {
        program: "xtask".into(),
        args: args.clone(),
        status: Some(1),
        stdout: Vec::new(),
        stderr: err.into_bytes(),
    })?;
    let violations = find_violations(&graph).map_err(|err| CommandFailed {
        program: "xtask".into(),
        args: args.clone(),
        status: Some(1),
        stdout: Vec::new(),
        stderr: err.into_bytes(),
    })?;
    if violations.is_empty() {
        return Ok(());
    }
    let mut stderr = format!(
        "architecture boundary violations ({GUARDED_CRATE} must not reach bevy, bevy_*, gone_app, or gone_harness via normal or build dependency edges):\n"
    );
    for violation in &violations {
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

fn metadata_plan(root: &Path) -> CommandPlan {
    CommandPlan::new("cargo")
        .args(["metadata", "--format-version", "1"])
        .current_dir(root)
}

/// Parse `cargo metadata` output into a `DepGraph`: manifest declarations
/// from `packages[*].dependencies` and the resolved edge graph from
/// `resolve.nodes[*].deps` (cargo 1.86+ stopped emitting `packages[*].deps`,
/// so the resolve section is the only source of resolved edges).
///
/// # Errors
/// Returns a message when the JSON is invalid or structurally unexpected, so
/// callers fail closed instead of passing on a partial graph.
pub fn extract_graph(metadata_json: &str) -> Result<DepGraph, String> {
    let value: Value = serde_json::from_str(metadata_json)
        .map_err(|err| format!("cargo metadata output is not valid JSON: {err}"))?;
    let packages = value
        .get("packages")
        .and_then(Value::as_array)
        .ok_or_else(|| "cargo metadata output has no `packages` array".to_string())?;
    let mut graph = DepGraph::default();
    let mut id_to_name = BTreeMap::new();
    for package in packages {
        let (id, name, declared) = extract_package(package)?;
        id_to_name.insert(id, name.clone());
        graph.declared.insert(name, declared);
    }
    let nodes = value
        .get("resolve")
        .and_then(|resolve| resolve.get("nodes"))
        .and_then(Value::as_array)
        .ok_or_else(|| "cargo metadata output has no `resolve.nodes` array".to_string())?;
    for node in nodes {
        let (name, edges) = extract_node(node, &id_to_name)?;
        graph.edges.insert(name, edges);
    }
    Ok(graph)
}

fn extract_package(package: &Value) -> Result<(String, String, Vec<DeclaredDep>), String> {
    let id = package
        .get("id")
        .and_then(Value::as_str)
        .ok_or_else(|| "cargo metadata package entry has no `id`".to_string())?
        .to_string();
    let name = package
        .get("name")
        .and_then(Value::as_str)
        .ok_or_else(|| "cargo metadata package entry has no `name`".to_string())?
        .to_string();
    let declarations = package
        .get("dependencies")
        .and_then(Value::as_array)
        .ok_or_else(|| format!("cargo metadata package `{name}` has no `dependencies` array"))?;
    let mut declared = Vec::with_capacity(declarations.len());
    for declaration in declarations {
        declared.push(extract_declared(declaration)?);
    }
    Ok((id, name, declared))
}

fn extract_node(
    node: &Value,
    id_to_name: &BTreeMap<String, String>,
) -> Result<(String, Vec<Edge>), String> {
    let node_id = node
        .get("id")
        .and_then(Value::as_str)
        .ok_or_else(|| "resolve node has no `id`".to_string())?;
    let name = canonical_name(node_id, id_to_name)?;
    let deps = node
        .get("deps")
        .and_then(Value::as_array)
        .ok_or_else(|| format!("resolve node `{name}` has no `deps` array"))?;
    let mut edges = Vec::with_capacity(deps.len());
    for dep in deps {
        let pkg_id = dep
            .get("pkg")
            .and_then(Value::as_str)
            .ok_or_else(|| format!("dependency of `{name}` has no `pkg` id"))?;
        let to = canonical_name(pkg_id, id_to_name)?;
        let kinds = dep
            .get("dep_kinds")
            .and_then(Value::as_array)
            .ok_or_else(|| format!("dependency `{name}` -> `{to}` has no `dep_kinds` array"))?;
        let normal_or_build = any_restricted_kind(&name, &to, kinds)?;
        edges.push(Edge {
            to,
            normal_or_build,
        });
    }
    Ok((name, edges))
}

/// Canonical package name for a resolve-graph id. Ids are opaque strings in
/// modern cargo (`path+file:///...#0.1.0`, `registry+...#serde_json@1.0.151`),
/// so names come from the package table rather than id parsing.
fn canonical_name(pkg_id: &str, id_to_name: &BTreeMap<String, String>) -> Result<String, String> {
    id_to_name
        .get(pkg_id)
        .cloned()
        .ok_or_else(|| format!("resolve graph references unknown package id `{pkg_id}`"))
}

fn extract_declared(declaration: &Value) -> Result<DeclaredDep, String> {
    let name = declaration
        .get("name")
        .and_then(Value::as_str)
        .ok_or_else(|| "declared dependency has no `name`".to_string())?
        .to_string();
    let normal_or_build = match declaration.get("kind") {
        // A missing/null kind is cargo's encoding for a normal dependency.
        None | Some(Value::Null) => true,
        Some(Value::String(s)) => match s.as_str() {
            "build" => true,
            "dev" => false,
            other => {
                return Err(format!(
                    "declared dependency `{name}` has unknown kind `{other}`"
                ));
            }
        },
        Some(_) => {
            return Err(format!(
                "declared dependency `{name}` has a non-string kind"
            ));
        }
    };
    Ok(DeclaredDep {
        name,
        normal_or_build,
    })
}

/// True when any recorded usage of the edge is normal or build. An empty
/// `dep_kinds` array is treated as restricted so a malformed graph cannot
/// open a silent hole.
fn any_restricted_kind(from: &str, to: &str, kinds: &[Value]) -> Result<bool, String> {
    if kinds.is_empty() {
        return Ok(true);
    }
    let restricted = kinds
        .iter()
        .map(|kind| kind_restricted(from, to, kind))
        .collect::<Result<Vec<_>, _>>()?;
    Ok(restricted.iter().any(|&r| r))
}

fn kind_restricted(from: &str, to: &str, kind: &Value) -> Result<bool, String> {
    match kind.get("kind") {
        None | Some(Value::Null) => Ok(true),
        Some(Value::String(s)) => match s.as_str() {
            "build" => Ok(true),
            "dev" => Ok(false),
            other => Err(format!(
                "dependency `{from}` -> `{to}` has unknown kind `{other}`"
            )),
        },
        Some(_) => Err(format!(
            "dependency `{from}` -> `{to}` has a non-string kind"
        )),
    }
}

/// Find every boundary violation, shortest path first: banned direct
/// declarations (including optional, disabled ones) plus every banned
/// package reachable over normal/build edges.
///
/// # Errors
/// Returns a message when `gone_sim` is absent from the graph (fail closed).
pub fn find_violations(graph: &DepGraph) -> Result<Vec<Violation>, String> {
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

/// Fixture metadata builder for the tests: packages are `(name, deps)` where
/// each dep is `(dep name, kind)` with kind `normal`, `build`, or `dev`.
#[cfg(test)]
mod tests {
    use super::{DepGraph, GUARDED_CRATE, Violation, extract_graph, find_violations, is_banned};

    fn metadata_json(packages: &[(&str, &[(&str, &str)])]) -> String {
        // Mirrors the cargo 1.98 layout: manifest declarations under
        // `packages[*].dependencies`, resolved edges under
        // `resolve.nodes[*].deps` with dep_kinds.
        let (package_entries, node_entries): (Vec<String>, Vec<String>) = packages
            .iter()
            .map(|(name, deps)| {
                let id = fixture_id(name);
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
                let package_entry =
                    format!("{{\"id\":\"{id}\",\"name\":\"{name}\",\"dependencies\":[{declarations}]}}");
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
                            fixture_id(dep)
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

    fn fixture_id(name: &str) -> String {
        format!("registry+https://example#{name}@0.1.0")
    }

    fn graph_from(packages: &[(&str, &[(&str, &str)])]) -> DepGraph {
        extract_graph(&metadata_json(packages)).expect("fixture metadata must parse")
    }

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
        let graph = graph_from(&[("gone_sim", &[("serde", "normal")]), ("serde", &[])]);
        assert_eq!(find_violations(&graph).expect("root present"), Vec::new());
    }

    #[test]
    fn direct_normal_edge_is_flagged_once() {
        let graph = graph_from(&[("gone_sim", &[("bevy_ecs", "normal")]), ("bevy_ecs", &[])]);
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
        let graph = graph_from(&[("gone_sim", &[("bevy_app", "build")]), ("bevy_app", &[])]);
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
        let graph = graph_from(&[
            ("gone_sim", &[("gone_harness", "dev")]),
            ("gone_harness", &[]),
        ]);
        assert_eq!(find_violations(&graph).expect("root present"), Vec::new());
    }

    #[test]
    fn transitive_bevy_path_is_flagged_with_full_path() {
        let graph = graph_from(&[
            ("gone_sim", &[("helper", "normal")]),
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
        let graph = graph_from(&[
            ("gone_sim", &[("a", "normal")]),
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
        let graph = graph_from(&[("serde", &[])]);
        let err = find_violations(&graph).expect_err("missing root must fail");
        assert!(err.contains(GUARDED_CRATE));
    }

    #[test]
    fn extract_graph_rejects_invalid_json() {
        assert!(extract_graph("not json").is_err());
        assert!(extract_graph("{}").is_err());
    }

    #[test]
    fn empty_dep_kinds_are_treated_as_restricted() {
        let json = "{\"packages\":[{\"id\":\"registry+https://example#gone_sim@0.1.0\",\
                    \"name\":\"gone_sim\",\"dependencies\":[]},\
                    {\"id\":\"registry+https://example#bevy_ecs@0.1.0\",\"name\":\"bevy_ecs\",\
                    \"dependencies\":[]}],\"resolve\":{\"nodes\":[\
                    {\"id\":\"registry+https://example#gone_sim@0.1.0\",\"deps\":[\
                    {\"name\":\"bevy_ecs\",\"pkg\":\"registry+https://example#bevy_ecs@0.1.0\",\
                    \"dep_kinds\":[]}]}]}}";
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
                    \"optional\":true}]}],\"resolve\":{\"nodes\":[\
                    {\"id\":\"registry+https://example#gone_sim@0.1.0\",\"deps\":[]}]}}";
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
                    \"kind\":\"dev\"}]}],\"resolve\":{\"nodes\":[\
                    {\"id\":\"registry+https://example#gone_sim@0.1.0\",\"deps\":[]}]}}";
        let graph = extract_graph(json).expect("parses");
        assert_eq!(find_violations(&graph).expect("root present"), Vec::new());
    }

    #[test]
    fn metadata_without_resolve_section_fails_closed() {
        let json = "{\"packages\":[{\"id\":\"registry+https://example#gone_sim@0.1.0\",\
                    \"name\":\"gone_sim\",\"dependencies\":[]}]}";
        assert!(extract_graph(json).is_err());
    }

    #[test]
    fn unknown_resolve_package_id_fails_closed() {
        let json = "{\"packages\":[{\"id\":\"registry+https://example#gone_sim@0.1.0\",\
                    \"name\":\"gone_sim\",\"dependencies\":[]}],\"resolve\":{\"nodes\":[\
                    {\"id\":\"registry+https://example#gone_sim@0.1.0\",\"deps\":[\
                    {\"name\":\"ghost\",\"pkg\":\"registry+https://example#ghost@0.1.0\",\
                    \"dep_kinds\":[{\"kind\":null,\"target\":null}]}]}]}}";
        let err = extract_graph(json).expect_err("unknown id must fail");
        assert!(err.contains("ghost"));
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
}
