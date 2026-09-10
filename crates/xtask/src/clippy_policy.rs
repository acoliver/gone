//! Clippy allow/expect suppression policy and clippy.toml sync check (issue #4).
//!
//! Zero-tolerance gate for clippy `allow`/`expect` suppressions in tracked
//! first-party Rust code, plus a check that the root `clippy.toml` and its
//! `.github/clippy` copy carry the same five complexity thresholds so the CI
//! `CLIPPY_CONF_DIR` cannot silently fall back to defaults. Ported from jefe.

use std::path::{Path, PathBuf};

use crate::process::{CommandFailed, CommandPlan};
use crate::rust_lexer;

/// One clippy `allow`/`expect` suppression found in a source file.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Suppression {
    pub file: PathBuf,
    pub attribute: String,
}

/// The five complexity thresholds that must match between root and CI
/// `clippy.toml`. Single source of truth so the sync check and its tests
/// cannot drift from the shipped configs.
const COMPLEXITY_THRESHOLDS: &[&str] = &[
    "cognitive-complexity-threshold",
    "too-many-lines-threshold",
    "too-many-arguments-threshold",
    "max-struct-bools",
    "type-complexity-threshold",
];

/// Run the clippy-allow policy against the repository root: scan every
/// tracked (or untracked-but-not-ignored) first-party Rust file and verify
/// the clippy.toml threshold sync.
///
/// # Errors
/// Returns `CommandFailed` if file enumeration fails (fail closed), any
/// suppression is found, or the two clippy.toml copies are missing or
/// mismatched.
pub fn run_repo_check(root: &Path) -> Result<(), CommandFailed> {
    let files = first_party_rust_files(root).map_err(|err| CommandFailed {
        program: "xtask".into(),
        args: vec!["check".into(), "clippy-allows".into()],
        status: Some(1),
        stdout: Vec::new(),
        stderr: format!("clippy allow scanner failed: {err}").into_bytes(),
    })?;
    let mut suppressions = Vec::new();
    for file in &files {
        match scan_file(file) {
            Ok(found) => suppressions.extend(found),
            Err(err) => {
                return Err(CommandFailed {
                    program: "xtask".into(),
                    args: vec!["check".into(), "clippy-allows".into()],
                    status: Some(1),
                    stdout: Vec::new(),
                    stderr: err.clone().into_bytes(),
                });
            }
        }
    }
    if !suppressions.is_empty() {
        let mut stderr = String::from(
            "first-party clippy allow/expect attributes are forbidden; remove them:\n",
        );
        for suppression in &suppressions {
            let relative = relative_path(&suppression.file, root);
            std::fmt::Write::write_fmt(
                &mut stderr,
                format_args!("  {relative}\t{}\n", suppression.attribute),
            )
            .ok();
        }
        return Err(CommandFailed {
            program: "xtask".into(),
            args: vec!["check".into(), "clippy-allows".into()],
            status: Some(1),
            stdout: Vec::new(),
            stderr: stderr.into_bytes(),
        });
    }
    match check_config_sync(root) {
        Ok(()) => Ok(()),
        Err(messages) => Err(CommandFailed {
            program: "xtask".into(),
            args: vec!["check".into(), "clippy-allows".into()],
            status: Some(1),
            stdout: Vec::new(),
            stderr: messages.join("\n").into_bytes(),
        }),
    }
}

/// Scan a single file for clippy allow/expect suppressions.
///
/// # Errors
/// Returns an error message when the file cannot be read (fail closed).
pub fn scan_file(path: &Path) -> Result<Vec<Suppression>, String> {
    let source = std::fs::read_to_string(path)
        .map_err(|err| format!("io error reading {}: {err}", path.display()))?;
    Ok(rust_lexer::scan_source(&source)
        .into_iter()
        .map(|attribute| Suppression {
            file: path.to_path_buf(),
            attribute,
        })
        .collect())
}

/// Verify the five complexity thresholds are present and equal in both
/// `clippy.toml` and `.github/clippy/clippy.toml`.
///
/// # Errors
/// Returns failure messages when a file is missing or any threshold is
/// absent or mismatched.
pub fn check_config_sync(root: &Path) -> Result<(), Vec<String>> {
    let root_config = root.join("clippy.toml");
    let ci_config = root.join(".github").join("clippy").join("clippy.toml");
    let mut errors = Vec::new();
    let Ok(root_text) = std::fs::read_to_string(&root_config) else {
        return Err(vec![format!(
            "required file is missing: {}",
            root_config.display()
        )]);
    };
    let Ok(ci_text) = std::fs::read_to_string(&ci_config) else {
        return Err(vec![format!(
            "required file is missing: {}",
            ci_config.display()
        )]);
    };
    for key in COMPLEXITY_THRESHOLDS {
        let root_value = config_value(&root_text, key);
        let ci_value = config_value(&ci_text, key);
        match (root_value, ci_value) {
            (Some(rv), Some(cv)) if rv != cv => errors.push(format!(
                "clippy threshold mismatch for {key}: clippy.toml={rv}, .github/clippy/clippy.toml={cv}"
            )),
            (None, _) => errors.push(format!("clippy.toml is missing clippy threshold: {key}")),
            (_, None) => {
                errors.push(format!(
                    ".github/clippy/clippy.toml is missing clippy threshold: {key}"
                ));
            }
            _ => {}
        }
    }
    if errors.is_empty() {
        Ok(())
    } else {
        Err(errors)
    }
}

/// Enumerate first-party Rust files via `git ls-files`: tracked files plus
/// untracked-but-not-ignored ones, so newly written code is gated before the
/// orchestrator commits it. Entries missing from disk are skipped.
fn first_party_rust_files(root: &Path) -> Result<Vec<PathBuf>, String> {
    let output = CommandPlan::new("git")
        .args([
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "*.rs",
        ])
        .current_dir(root)
        .run_captured()
        .map_err(|err| format!("git ls-files failed: {err}"))?;
    let stdout = String::from_utf8_lossy(&output.stdout);
    let mut files: Vec<PathBuf> = stdout
        .lines()
        .filter(|line| !line.is_empty())
        .map(|line| root.join(line))
        .filter(|path| path.is_file())
        .collect();
    files.sort();
    Ok(files)
}

/// Extract a `key = value` line's value from clippy.toml text, trimming
/// whitespace and any trailing `# comment`. Returns the first match.
fn config_value(text: &str, key: &str) -> Option<String> {
    for line in text.lines() {
        let trimmed = line.trim_start();
        let Some(rest) = trimmed.strip_prefix(key) else {
            continue;
        };
        let Some(after_eq) = rest.trim_start().strip_prefix('=') else {
            continue;
        };
        let mut value = after_eq.trim();
        if let Some(hash) = value.find('#') {
            value = value[..hash].trim_end();
        }
        return Some(value.to_string());
    }
    None
}

fn relative_path(file: &Path, root: &Path) -> String {
    file.strip_prefix(root)
        .map_or_else(|_| file.to_path_buf(), Path::to_path_buf)
        .to_string_lossy()
        .into_owned()
}

/// Tests for the sync check, value parsing, and policy wiring.
#[cfg(test)]
mod tests {
    use super::{check_config_sync, config_value, relative_path};
    use crate::test_support::unique_temp_dir;
    use std::fs;
    use std::path::{Path, PathBuf};

    const SYNCED_CONFIG: &str = "cognitive-complexity-threshold = 15\ntoo-many-lines-threshold = 60\ntoo-many-arguments-threshold = 6\nmax-struct-bools = 3\ntype-complexity-threshold = 250\n";

    fn write_repo(config: &str) -> PathBuf {
        let dir = unique_temp_dir("sync");
        fs::create_dir_all(dir.join(".github/clippy")).expect("dirs");
        fs::write(dir.join("clippy.toml"), config).expect("write root config");
        fs::write(dir.join(".github/clippy/clippy.toml"), config).expect("write ci config");
        dir
    }

    #[test]
    fn synced_configs_pass() {
        assert!(check_config_sync(&write_repo(SYNCED_CONFIG)).is_ok());
    }

    #[test]
    fn drifted_threshold_fails_naming_key() {
        let drifted = SYNCED_CONFIG.replace(
            "too-many-lines-threshold = 60",
            "too-many-lines-threshold = 80",
        );
        let dir = write_repo(SYNCED_CONFIG);
        fs::write(dir.join("clippy.toml"), drifted).expect("rewrite");
        let errors = check_config_sync(&dir).expect_err("drift must fail");
        assert!(
            errors
                .iter()
                .any(|e| e.contains("too-many-lines-threshold"))
        );
    }

    #[test]
    fn missing_threshold_fails() {
        let incomplete = "cognitive-complexity-threshold = 15\n";
        let dir = write_repo(incomplete);
        let errors = check_config_sync(&dir).expect_err("missing keys must fail");
        assert_eq!(errors.len(), 4);
    }

    #[test]
    fn missing_ci_copy_fails() {
        let dir = unique_temp_dir("sync-missing");
        fs::write(dir.join("clippy.toml"), SYNCED_CONFIG).expect("write root config");
        let errors = check_config_sync(&dir).expect_err("missing copy must fail");
        assert!(errors[0].contains(".github"));
    }

    #[test]
    fn config_value_handles_comments_and_spacing() {
        let text = "# comment\ntoo-many-lines-threshold   =  60  # inline note\nother = 1\n";
        assert_eq!(
            config_value(text, "too-many-lines-threshold"),
            Some("60".to_string())
        );
        assert_eq!(config_value(text, "absent"), None);
    }

    #[test]
    fn relative_path_stays_stable() {
        let root = Path::new("/repo");
        assert_eq!(
            relative_path(&root.join("crates/x/src/lib.rs"), root),
            "crates/x/src/lib.rs"
        );
        assert_eq!(
            relative_path(Path::new("/elsewhere/lib.rs"), root),
            "/elsewhere/lib.rs"
        );
    }

    #[test]
    fn policy_error_names_file_and_attribute() {
        let dir = unique_temp_dir("allows");
        let src = dir.join("src");
        fs::create_dir_all(&src).expect("src");
        let file = src.join("lib.rs");
        fs::write(&file, "#[allow(clippy::too_many_arguments)]\nfn f() {}\n").expect("write");
        let found = crate::clippy_policy::scan_file(&file).expect("scan ok");
        assert_eq!(found.len(), 1);
        assert_eq!(found[0].file, file);
        assert_eq!(found[0].attribute, "#[allow(clippy::too_many_arguments)]");
    }

    #[test]
    fn unreadable_file_fails_closed() {
        let missing = unique_temp_dir("allows-missing").join("gone.rs");
        assert!(crate::clippy_policy::scan_file(&missing).is_err());
    }
}
