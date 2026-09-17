//! Harness protocol-module surface policy (issue #5 stage A).
//!
//! cargo's dependency graph cannot see modules, so the rule that keeps
//! scenario scripts unable to call gameplay internals is enforced at the
//! source level: every file under `crates/gone_app/src/harness/` (the
//! protocol surface `gone_harness` re-exports) must not reference the
//! simulation crate. Scanning strips comments and string literals via the
//! shared lexer and matches the crate name on identifier boundaries, so
//! prose that merely mentions `gone_sim` cannot trip the gate while a real
//! `use gone_sim::...` (or any `gone_sim::path`) always does.
//!
//! Like every policy gate, this fails closed: a missing module directory or
//! an unreadable file is an error, never a pass.

use std::path::Path;

use crate::rust_lexer::{is_ident_continue, strip_comments_and_literals};

/// Directory (relative to the repo root) holding the harness protocol module.
const HARNESS_MODULE_DIR: &str = "crates/gone_app/src/harness";

/// The crate the protocol surface must never reference.
const BANNED_CRATE: &str = "gone_sim";

/// A surface violation: one protocol-module file referencing the simulation
/// crate.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SurfaceViolation {
    /// File that violates the rule, relative to the repo root.
    pub file: String,
}

impl std::fmt::Display for SurfaceViolation {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let file = &self.file;
        write!(
            f,
            "harness protocol module `{file}` references banned package `{BANNED_CRATE}`"
        )
    }
}

/// Scan the protocol module on disk and report every file that references the
/// simulation crate.
///
/// # Errors
/// Returns a message when the module directory is missing or any Rust file
/// under it cannot be read (fail closed).
pub fn violations_from_disk(root: &Path) -> Result<Vec<SurfaceViolation>, String> {
    let dir = root.join(HARNESS_MODULE_DIR);
    if !dir.is_dir() {
        return Err(format!(
            "harness protocol module directory `{HARNESS_MODULE_DIR}` is missing; \
             cannot check architecture boundaries"
        ));
    }
    let mut sources = Vec::new();
    collect_sources(&dir, root, &mut sources)?;
    Ok(find_violations(&sources))
}

/// Pure core: scan `(file, source text)` pairs and report every file whose
/// code (comments and literals stripped) references the banned crate.
#[must_use]
pub fn find_violations(sources: &[(String, String)]) -> Vec<SurfaceViolation> {
    sources
        .iter()
        .filter(|(_, text)| references_crate(&strip_comments_and_literals(text), BANNED_CRATE))
        .map(|(file, _)| SurfaceViolation { file: file.clone() })
        .collect()
}

/// True when `stripped` (comment/literal-free source) contains `crate_name`
/// as a standalone identifier: every occurrence must have non-identifier
/// bytes on both sides, so `gone_sim::World` matches but `gone_simulated`
/// and `my_gone_sim` do not.
#[must_use]
fn references_crate(stripped: &str, crate_name: &str) -> bool {
    let bytes = stripped.as_bytes();
    let mut search = 0usize;
    while let Some(offset) = stripped[search..].find(crate_name) {
        let start = search + offset;
        let end = start + crate_name.len();
        let before = start == 0 || !is_ident_continue(bytes[start - 1]);
        let after = end == bytes.len() || !is_ident_continue(bytes[end]);
        if before && after {
            return true;
        }
        search = start + 1;
    }
    false
}

/// Recursively collect `(repo-relative path, source text)` pairs for every
/// `.rs` file under `dir`, sorted per directory for stable diagnostics.
///
/// # Errors
/// Returns a message naming the path when a directory or file cannot be read.
fn collect_sources(dir: &Path, root: &Path, out: &mut Vec<(String, String)>) -> Result<(), String> {
    let mut children = Vec::new();
    for entry in std::fs::read_dir(dir)
        .map_err(|err| format!("cannot read `{}`: {err}", relative(dir, root)))?
    {
        let entry = entry
            .map_err(|err| format!("cannot read an entry of `{}`: {err}", relative(dir, root)))?;
        children.push(entry.path());
    }
    children.sort();
    for child in children {
        if child.is_dir() {
            collect_sources(&child, root, out)?;
        } else if child.extension().is_some_and(|ext| ext == "rs") {
            let text = std::fs::read_to_string(&child)
                .map_err(|err| format!("cannot read `{}`: {err}", relative(&child, root)))?;
            out.push((relative(&child, root), text));
        }
    }
    Ok(())
}

/// Repo-root-relative rendering of `path` for stable, short diagnostics.
fn relative(path: &Path, root: &Path) -> String {
    path.strip_prefix(root)
        .unwrap_or(path)
        .to_string_lossy()
        .into_owned()
}

#[cfg(test)]
mod tests {
    use super::{SurfaceViolation, find_violations, references_crate, violations_from_disk};
    use crate::test_support::unique_temp_dir;
    use std::fs;

    fn sources_of(file: &str, text: &str) -> Vec<(String, String)> {
        vec![(file.to_string(), text.to_string())]
    }

    #[test]
    fn use_statement_is_flagged() {
        let sources = sources_of(
            "crates/gone_app/src/harness/input.rs",
            "use gone_sim::World;\nfn f() {}\n",
        );
        assert_eq!(
            find_violations(&sources),
            vec![SurfaceViolation {
                file: "crates/gone_app/src/harness/input.rs".into(),
            }]
        );
    }

    #[test]
    fn qualified_path_and_extern_crate_references_are_flagged() {
        let paths = sources_of("beat.rs", "fn f() { let _ = gone_sim::World::new(); }\n");
        let externs = sources_of("mod.rs", "extern crate gone_sim;\n");
        assert_eq!(find_violations(&paths).len(), 1);
        assert_eq!(find_violations(&externs).len(), 1);
    }

    #[test]
    fn comment_and_literal_mentions_are_allowed() {
        let text = "// gone_sim is out of bounds here\n\
                    /* use gone_sim::World; */\n\
                    const S: &str = \"gone_sim\";\n\
                    const R: &str = r#\"gone_sim\"#;\n\
                    fn f() {}\n";
        let sources = sources_of("mod.rs", text);
        assert_eq!(find_violations(&sources), Vec::new());
    }

    #[test]
    fn identifier_boundaries_are_exact() {
        let text = "fn gone_simulated() {}\n\
                    fn my_gone_sim() {}\n\
                    const GONE_SIM: u8 = 0;\n\
                    fn f() {}\n";
        let sources = sources_of("frame.rs", text);
        assert_eq!(find_violations(&sources), Vec::new());
    }

    #[test]
    fn references_crate_boundaries() {
        assert!(references_crate("use gone_sim::World;", "gone_sim"));
        assert!(references_crate("gone_sim", "gone_sim"));
        assert!(!references_crate("gone_simulated", "gone_sim"));
        assert!(!references_crate("my_gone_sim", "gone_sim"));
        assert!(!references_crate("", "gone_sim"));
    }

    #[test]
    fn violations_list_every_offending_file() {
        let sources = vec![
            ("a.rs".to_string(), "use gone_sim as _;\n".to_string()),
            ("b.rs".to_string(), "fn f() {}\n".to_string()),
            ("c.rs".to_string(), "gone_sim::tick();\n".to_string()),
        ];
        assert_eq!(
            find_violations(&sources),
            vec![
                SurfaceViolation {
                    file: "a.rs".into()
                },
                SurfaceViolation {
                    file: "c.rs".into()
                },
            ]
        );
    }

    #[test]
    fn surface_violation_display_names_the_file() {
        let violation = SurfaceViolation {
            file: "crates/gone_app/src/harness/input.rs".into(),
        };
        assert_eq!(
            violation.to_string(),
            "harness protocol module `crates/gone_app/src/harness/input.rs` \
             references banned package `gone_sim`"
        );
    }

    #[test]
    fn missing_module_directory_fails_closed() {
        let root = unique_temp_dir("surface-missing");
        let err = violations_from_disk(&root).expect_err("missing dir must fail");
        assert!(err.contains("missing"));
    }

    #[test]
    fn clean_module_tree_passes() {
        let root = unique_temp_dir("surface-clean");
        let dir = root.join("crates/gone_app/src/harness");
        fs::create_dir_all(&dir).expect("dirs");
        fs::write(
            dir.join("mod.rs"),
            "// mentions gone_sim in a comment\npub mod input;\n",
        )
        .expect("write");
        fs::write(dir.join("input.rs"), "use serde::Serialize;\n").expect("write");
        assert_eq!(
            violations_from_disk(&root).expect("clean tree passes"),
            Vec::new()
        );
    }

    #[test]
    fn dirty_module_tree_fails_naming_the_file() {
        let root = unique_temp_dir("surface-dirty");
        let dir = root.join("crates/gone_app/src/harness");
        fs::create_dir_all(&dir).expect("dirs");
        fs::write(dir.join("input.rs"), "use gone_sim::World;\n").expect("write");
        let violations = violations_from_disk(&root).expect("scan runs");
        assert_eq!(
            violations,
            vec![SurfaceViolation {
                file: "crates/gone_app/src/harness/input.rs".into(),
            }]
        );
    }
}
