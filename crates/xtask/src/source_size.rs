//! Source file length policy (issue #4).
//!
//! Warns at 750 lines and hard-fails at 1000 lines per Rust source file,
//! scanning every first-party root (`crates/*/src` plus any `crates/*/tests`)
//! recursively. Line counts use `wc -l` semantics (a line is a `\n` byte).
//! Ported from jefe's `source_size` gate, with scan roots adapted to this
//! workspace's layout. Like every policy gate, this one fails closed: a
//! scan that cannot complete (unreadable directory, metadata, or file) is a
//! gate failure, never a pass over a partial tree.

use std::path::{Path, PathBuf};

use crate::process::CommandFailed;

/// Recommended (warning) limit, in lines.
pub const WARN_LIMIT: usize = 750;
/// Hard failure limit, in lines.
pub const HARD_LIMIT: usize = 1000;

/// Directory whose `*/src` subtrees hold all first-party Rust code.
const CRATES_DIR: &str = "crates";

/// First-party subdirectories of each crate that hold Rust sources: the
/// library roots and, where they exist, the integration-test roots.
const FIRST_PARTY_SUBDIRS: [&str; 2] = ["src", "tests"];

/// One file's measured length.
#[derive(Debug, Clone)]
pub struct FileLength {
    pub path: PathBuf,
    pub lines: usize,
}

/// A length policy violation: a hard error or a warning.
#[derive(Debug, Clone)]
pub enum Violation {
    Hard {
        path: PathBuf,
        lines: usize,
        limit: usize,
    },
    Warn {
        path: PathBuf,
        lines: usize,
        limit: usize,
    },
}

impl Violation {
    /// The file path that violated the policy.
    #[must_use]
    pub fn path(&self) -> &Path {
        match self {
            Self::Hard { path, .. } | Self::Warn { path, .. } => path,
        }
    }
}

/// Configuration for the source-size policy.
#[derive(Debug, Clone)]
pub struct Policy {
    pub hard_limit: usize,
    pub warn_limit: usize,
}

impl Default for Policy {
    fn default() -> Self {
        Self {
            hard_limit: HARD_LIMIT,
            warn_limit: WARN_LIMIT,
        }
    }
}

/// Measured lengths plus files that could not be read. Unreadable files are
/// surfaced so an incomplete scan can never pass silently.
#[derive(Debug, Clone)]
pub struct Measurement {
    pub lengths: Vec<FileLength>,
    pub unreadable: Vec<PathBuf>,
}

/// Run the policy over the workspace's first-party roots.
///
/// # Errors
/// Returns `CommandFailed` when the scan cannot complete (unreadable
/// directory, metadata, or file) or any file meets the hard limit; warnings
/// are printed to stderr without failing the gate.
pub fn run_repo_check(root: &Path) -> Result<(), CommandFailed> {
    let roots = scan_roots(root).map_err(|message| gate_failure(&message))?;
    let tests_roots = roots
        .iter()
        .filter(|dir| dir.file_name().is_some_and(|name| name == "tests"))
        .count();
    if tests_roots == 0 {
        eprintln!("note: no crates/*/tests roots exist; the scan covers crates/*/src only");
    }
    run_with_roots(&roots, &Policy::default(), root)
}

/// First-party scan roots: every existing `crates/*/src`, plus every
/// existing `crates/*/tests` (integration-test sources are first-party code
/// the line policy covers).
///
/// # Errors
/// A message when the crates directory cannot be read or an entry's
/// metadata cannot be inspected: a scan with unknown coverage must fail the
/// gate, not silently narrow it.
pub fn scan_roots(repo_root: &Path) -> Result<Vec<PathBuf>, String> {
    let crates_dir = repo_root.join(CRATES_DIR);
    let entries = std::fs::read_dir(&crates_dir)
        .map_err(|e| format!("cannot read `{}`: {e}", crates_dir.display()))?;
    let mut roots = Vec::new();
    for entry in entries {
        let entry = entry
            .map_err(|e| format!("cannot read an entry of `{}`: {e}", crates_dir.display()))?;
        for subdir in FIRST_PARTY_SUBDIRS {
            let dir = entry.path().join(subdir);
            match std::fs::metadata(&dir) {
                Ok(metadata) if metadata.is_dir() => roots.push(dir),
                Ok(_) => {}
                Err(e) if e.kind() == std::io::ErrorKind::NotFound => {}
                Err(e) => return Err(format!("cannot inspect `{}`: {e}", dir.display())),
            }
        }
    }
    roots.sort();
    Ok(roots)
}

/// Run the policy against explicit scan roots, reporting paths relative to
/// `relativize_to` for stable diagnostics.
///
/// # Errors
/// Returns `CommandFailed` when the scan cannot complete (an unreadable
/// directory or file) or any file meets the hard limit.
pub fn run_with_roots(
    roots: &[PathBuf],
    policy: &Policy,
    relativize_to: &Path,
) -> Result<(), CommandFailed> {
    let mut files = Vec::new();
    for root in roots {
        collect_rust_files(root, &mut files).map_err(|message| gate_failure(&message))?;
    }
    files.sort();
    if files.is_empty() {
        return Ok(());
    }
    let measurement = measure_files(&files);
    if !measurement.unreadable.is_empty() {
        let names = measurement
            .unreadable
            .iter()
            .map(|path| relativize(path, relativize_to))
            .collect::<Vec<_>>()
            .join(", ");
        return Err(gate_failure(&format!(
            "scan incomplete: {} unreadable file(s) were not measured: {names}",
            measurement.unreadable.len()
        )));
    }
    let violations = classify(&measurement.lengths, policy);
    let mut errors = 0usize;
    let mut warnings = 0usize;
    for violation in &violations {
        let relative = relativize(violation.path(), relativize_to);
        match violation {
            Violation::Hard { lines, limit, .. } => {
                eprintln!("ERROR: {relative} has {lines} lines (max {limit})");
                errors += 1;
            }
            Violation::Warn { lines, limit, .. } => {
                eprintln!("WARNING: {relative} has {lines} lines (recommended max {limit})");
                warnings += 1;
            }
        }
    }
    if warnings > 0 {
        eprintln!("Emitted {warnings} file length warning(s).");
    }
    if errors > 0 {
        return Err(CommandFailed {
            program: "xtask".into(),
            args: vec!["check".into(), "source-size".into()],
            status: Some(1),
            stdout: Vec::new(),
            stderr: format!("Found {errors} file(s) exceeding the hard limit.").into_bytes(),
        });
    }
    Ok(())
}

/// Package a fail-closed scan error (unreadable directory, metadata, or
/// file) as a `CommandFailed` for the `check source-size` invocation.
fn gate_failure(message: &str) -> CommandFailed {
    CommandFailed {
        program: "xtask".into(),
        args: vec!["check".into(), "source-size".into()],
        status: Some(1),
        stdout: Vec::new(),
        stderr: message.as_bytes().to_vec(),
    }
}

/// Measure line counts; unreadable files land in `Measurement::unreadable`.
#[must_use]
pub fn measure_files(files: &[PathBuf]) -> Measurement {
    let mut lengths = Vec::with_capacity(files.len());
    let mut unreadable = Vec::new();
    for file in files {
        match std::fs::read_to_string(file) {
            Ok(content) => lengths.push(FileLength {
                path: file.clone(),
                lines: count_lines(&content),
            }),
            Err(_) => unreadable.push(file.clone()),
        }
    }
    Measurement {
        lengths,
        unreadable,
    }
}

/// Count lines with `wc -l` semantics: only `\n`-terminated lines count.
#[must_use]
pub fn count_lines(content: &str) -> usize {
    content.bytes().filter(|&b| b == b'\n').count()
}

/// Classify measured lengths. `>=` semantics: a file at exactly the warn
/// limit warns, and a file at exactly the hard limit fails.
#[must_use]
pub fn classify(lengths: &[FileLength], policy: &Policy) -> Vec<Violation> {
    let mut out = Vec::new();
    for file in lengths {
        if file.lines >= policy.hard_limit {
            out.push(Violation::Hard {
                path: file.path.clone(),
                lines: file.lines,
                limit: policy.hard_limit,
            });
        } else if file.lines >= policy.warn_limit {
            out.push(Violation::Warn {
                path: file.path.clone(),
                lines: file.lines,
                limit: policy.warn_limit,
            });
        }
    }
    out
}

/// Collect `.rs` files under `dir` recursively.
///
/// # Errors
/// A message when any directory or entry cannot be read or inspected: an
/// unwalkable subtree means the scan's coverage is unknown, so the caller
/// fails the gate instead of measuring a subset.
fn collect_rust_files(dir: &Path, out: &mut Vec<PathBuf>) -> Result<(), String> {
    let entries = std::fs::read_dir(dir)
        .map_err(|e| format!("cannot read directory `{}`: {e}", dir.display()))?;
    for entry in entries {
        let entry =
            entry.map_err(|e| format!("cannot read an entry of `{}`: {e}", dir.display()))?;
        let path = entry.path();
        // Follow symlinks when classifying: `DirEntry::metadata` reports the
        // link itself, so a broken link would silently skip (scan coverage
        // unknown) instead of failing the gate.
        let metadata = std::fs::metadata(&path)
            .map_err(|e| format!("cannot inspect `{}`: {e}", path.display()))?;
        if metadata.is_dir() {
            collect_rust_files(&path, out)?;
        } else if metadata.is_file() && path.extension().is_some_and(|ext| ext == "rs") {
            out.push(path);
        }
    }
    Ok(())
}

fn relativize(path: &Path, base: &Path) -> String {
    path.strip_prefix(base)
        .map_or_else(|_| path.to_path_buf(), Path::to_path_buf)
        .to_string_lossy()
        .into_owned()
}

/// Tests for line counting, classification boundaries, root discovery, and
/// the end-to-end gate over fixture trees.
#[cfg(test)]
mod tests {
    use super::{
        FileLength, Policy, classify, count_lines, measure_files, run_with_roots, scan_roots,
    };
    use crate::test_support::unique_temp_dir;
    use std::fs;
    use std::path::{Path, PathBuf};

    fn write_rust_lines(root: &Path, relative: &str, lines: usize) -> PathBuf {
        let path = root.join(relative);
        fs::create_dir_all(path.parent().expect("parent")).expect("dirs");
        fs::write(&path, "fn line() {}\n".repeat(lines)).expect("write");
        path
    }

    #[test]
    fn count_lines_matches_wc_l() {
        assert_eq!(count_lines(""), 0);
        assert_eq!(count_lines("abc"), 0);
        assert_eq!(count_lines("abc\n"), 1);
        assert_eq!(count_lines("a\nb\n"), 2);
        assert_eq!(count_lines("a\nb"), 1);
    }

    #[test]
    fn classification_boundaries() {
        let policy = Policy::default();
        let build = |lines: usize| {
            vec![FileLength {
                path: PathBuf::from("x.rs"),
                lines,
            }]
        };
        assert!(classify(&build(749), &policy).is_empty());
        assert!(matches!(
            classify(&build(750), &policy)[0],
            super::Violation::Warn { lines: 750, .. }
        ));
        assert!(matches!(
            classify(&build(999), &policy)[0],
            super::Violation::Warn { .. }
        ));
        assert!(matches!(
            classify(&build(1000), &policy)[0],
            super::Violation::Hard { lines: 1000, .. }
        ));
        assert!(matches!(
            classify(&build(1001), &policy)[0],
            super::Violation::Hard { .. }
        ));
    }

    #[test]
    fn scan_roots_include_src_and_any_tests_dirs() {
        let dir = unique_temp_dir("roots");
        fs::create_dir_all(dir.join("crates/gone_sim/src")).expect("dirs");
        fs::create_dir_all(dir.join("crates/gone_sim/tests")).expect("dirs");
        fs::create_dir_all(dir.join("crates/no_src")).expect("dirs");
        let roots = scan_roots(&dir).expect("scan runs");
        assert_eq!(
            roots,
            vec![
                dir.join("crates/gone_sim/src"),
                dir.join("crates/gone_sim/tests"),
            ]
        );
    }

    #[test]
    fn missing_crates_dir_fails_closed() {
        // Regression: a missing or unreadable crates dir used to scan to an
        // empty root list, so the gate passed over nothing. Unknown coverage
        // must fail, not pass.
        let err = scan_roots(Path::new("/definitely/not/here")).expect_err("must fail");
        assert!(err.contains("cannot read"), "names the failure: {err}");
    }

    #[test]
    fn missing_src_but_present_tests_are_both_handled() {
        // A crate with only a tests dir (no src) still contributes its
        // tests root; nothing is invented for the missing src.
        let dir = unique_temp_dir("roots-tests-only");
        fs::create_dir_all(dir.join("crates/only_tests/tests")).expect("dirs");
        let roots = scan_roots(&dir).expect("scan runs");
        assert_eq!(roots, vec![dir.join("crates/only_tests/tests")]);
    }

    #[test]
    fn under_limit_file_passes_clean() {
        let dir = unique_temp_dir("size-clean");
        let src = dir.join("crates/gone_sim/src");
        write_rust_lines(&src, "small.rs", 10);
        let result = run_with_roots(&[src], &Policy::default(), &dir);
        assert!(result.is_ok());
    }

    #[test]
    fn warn_range_file_warns_without_failing() {
        let dir = unique_temp_dir("size-warn");
        let src = dir.join("crates/gone_sim/src");
        write_rust_lines(&src, "big.rs", 800);
        let result = run_with_roots(&[src], &Policy::default(), &dir);
        assert!(result.is_ok(), "800 lines must warn, not fail");
    }

    #[test]
    fn hard_limit_file_fails_naming_file() {
        let dir = unique_temp_dir("size-hard");
        let src = dir.join("crates/gone_sim/src");
        write_rust_lines(&src, "huge.rs", 1001);
        let result = run_with_roots(&[src], &Policy::default(), &dir);
        let err = result.expect_err("1001 lines must fail");
        let stderr = String::from_utf8_lossy(&err.stderr);
        assert!(stderr.contains("Found 1 file(s) exceeding the hard limit."));
    }

    /// An unwalkable scan root is a gate failure, not a pass over nothing.
    #[test]
    fn unreadable_scan_root_fails_the_gate() {
        // Regression: `collect_rust_files` silently skipped unreadable
        // directories, so a root that could not be walked scanned as empty
        // and the gate passed.
        let dir = unique_temp_dir("size-unwalkable");
        let missing = dir.join("crates/gone_sim/src");
        let result = run_with_roots(&[missing], &Policy::default(), &dir);
        let err = result.expect_err("an unscannable root must fail the gate");
        let stderr = String::from_utf8_lossy(&err.stderr);
        assert!(
            stderr.contains("cannot read directory"),
            "the error names the unwalkable root: {stderr}"
        );
    }

    /// A collected-but-unmeasurable path fails the gate. On unix a broken
    /// symlink is the direct way to make a walkable tree entry whose
    /// metadata cannot be resolved: the walk must refuse to skip it, and
    /// `run_with_roots` must fail instead of passing over a partial tree.
    #[cfg(unix)]
    #[test]
    fn unmeasurable_path_fails_the_gate_not_pass() {
        let dir = unique_temp_dir("size-broken");
        let src = dir.join("crates/gone_sim/src");
        write_rust_lines(&src, "real.rs", 5);
        std::os::unix::fs::symlink(src.join("no-such-target.rs"), src.join("broken.rs"))
            .expect("create broken symlink");
        let result = run_with_roots(&[src], &Policy::default(), &dir);
        let err = result.expect_err("an unmeasurable path must fail the gate");
        let stderr = String::from_utf8_lossy(&err.stderr);
        assert!(
            stderr.contains("cannot inspect"),
            "the error names the uninspectable path: {stderr}"
        );
    }

    /// Non-unix counterpart: a collected `.rs` file whose bytes are not
    /// valid UTF-8 cannot be measured, and the gate must fail closed over
    /// the partial tree exactly as the unix broken-symlink case does.
    #[cfg(not(unix))]
    #[test]
    fn unmeasurable_path_fails_the_gate_not_pass() {
        let dir = unique_temp_dir("size-unmeasurable");
        let src = dir.join("crates/gone_sim/src");
        write_rust_lines(&src, "real.rs", 5);
        fs::write(src.join("ghost.rs"), [0xFF, 0xFE, 0xFC]).expect("write non-utf8 bytes");
        let result = run_with_roots(&[src], &Policy::default(), &dir);
        let err = result.expect_err("an unmeasurable path must fail the gate");
        let stderr = String::from_utf8_lossy(&err.stderr);
        assert!(
            stderr.contains("scan incomplete"),
            "the error names the unmeasured file: {stderr}"
        );
    }

    #[test]
    fn scan_is_recursive_and_sorted() {
        let dir = unique_temp_dir("size-recursive");
        let src = dir.join("crates/gone_sim/src");
        write_rust_lines(&src, "nested/deep.rs", 5);
        write_rust_lines(&src, "top.rs", 5);
        let mut files = Vec::new();
        super::collect_rust_files(&src, &mut files).expect("walk runs");
        files.sort();
        assert_eq!(files.len(), 2);
        assert_eq!(files[0], src.join("nested/deep.rs"));
    }

    #[test]
    fn unreadable_files_are_surfaced_not_silently_skipped() {
        let dir = unique_temp_dir("size-unreadable");
        let src = dir.join("crates/gone_sim/src");
        let real = write_rust_lines(&src, "real.rs", 5);
        let ghost = src.join("ghost.rs");
        let measurement = measure_files(&[real, ghost.clone()]);
        assert_eq!(measurement.lengths.len(), 1);
        assert_eq!(measurement.unreadable, vec![ghost]);
    }
}
