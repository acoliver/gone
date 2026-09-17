//! `cargo metadata` graph parsing for the architecture policy (issue #4).
//!
//! Turns `cargo metadata --format-version 1` output into a
//! [`DepGraph`]: manifest declarations from `packages[*].dependencies`
//! and the resolved edge graph from `resolve.nodes[*].deps` (cargo 1.86+
//! stopped emitting `packages[*].deps`, so the resolve section is the only
//! source of resolved edges). Parsing is separated from the policy in
//! [`crate::architecture`] so each half stays small and testable.

use std::collections::BTreeMap;

use serde_json::Value;

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

/// Parse `cargo metadata` output into a `DepGraph`.
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

#[cfg(test)]
mod tests {
    use super::extract_graph;

    #[test]
    fn extract_graph_rejects_invalid_json() {
        assert!(extract_graph("not json").is_err());
        assert!(extract_graph("{}").is_err());
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
}
