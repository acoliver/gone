//! Source file length policy (issue #4).
//!
//! Warns at 750 lines and hard-fails at 1000 lines per Rust source file,
//! scanning every first-party root (`crates/*/src`) recursively. Line counts
//! use `wc -l` semantics (a line is a `\n` byte). Ported from jefe's
//! `source_size` gate, with scan roots adapted to this workspace's layout.

use std::path::{Path, PathBuf};

use crate::process::CommandFailed;

/// Recommended (warning) limit, in lines.
pub const WARN_LIMIT: usize = 750;
/// Hard failure limit, in lines.
pub const HARD_LIMIT: usize = 1000;

/// Directory whose `*/src` subtrees hold all first-party Rust code.
const CRATES_DIR: &str = "crates";

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
/// Returns `CommandFailed` when any file meets the hard limit; warnings are
/// printed to stderr without failing the gate.
pub fn run_repo_check(root: &Path) -> Result<(), CommandFailed> {
    run_with_roots(&scan_roots(root), &Policy::default(), root)
}

/// First-party scan roots: every `crates/*/src` directory.
#[must_use]
pub fn scan_roots(repo_root: &Path) -> Vec<PathBuf> {
    let mut roots = Vec::new();
    let Ok(entries) = std::fs::read_dir(repo_root.join(CRATES_DIR)) else {
        return roots;
    };
    for entry in entries.flatten() {
        let src = entry.path().join("src");
        if src.is_dir() {
            roots.push(src);
        }
    }
    roots.sort();
    roots
}

/// Run the policy against explicit scan roots, reporting paths relative to
/// `relativize_to` for stable diagnostics.
///
/// # Errors
/// Returns `CommandFailed` when any file meets the hard limit.
pub fn run_with_roots(
    roots: &[PathBuf],
    policy: &Policy,
    relativize_to: &Path,
) -> Result<(), CommandFailed> {
    let mut files = Vec::new();
    for root in roots {
        collect_rust_files(root, &mut files);
    }
    files.sort();
    if files.is_empty() {
        return Ok(());
    }
    let measurement = measure_files(&files);
    for skipped in &measurement.unreadable {
        eprintln!(
            "WARNING: could not read {}; file was not measured (scan is incomplete)",
            relativize(skipped, relativize_to)
        );
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

fn collect_rust_files(dir: &Path, out: &mut Vec<PathBuf>) {
    let Ok(entries) = std::fs::read_dir(dir) else {
        return;
    };
    for entry in entries.flatten() {
        let path = entry.path();
        let Ok(metadata) = entry.metadata() else {
            continue;
        };
        if metadata.is_dir() {
            collect_rust_files(&path, out);
        } else if metadata.is_file() && path.extension().is_some_and(|ext| ext == "rs") {
            out.push(path);
        }
    }
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
    fn scan_roots_only_include_member_src_dirs() {
        let dir = unique_temp_dir("roots");
        fs::create_dir_all(dir.join("crates/gone_sim/src")).expect("dirs");
        fs::create_dir_all(dir.join("crates/no_src")).expect("dirs");
        let roots = scan_roots(&dir);
        assert_eq!(roots, vec![dir.join("crates/gone_sim/src")]);
    }

    #[test]
    fn missing_crates_dir_scans_nothing() {
        assert!(scan_roots(Path::new("/definitely/not/here")).is_empty());
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

    #[test]
    fn scan_is_recursive_and_sorted() {
        let dir = unique_temp_dir("size-recursive");
        let src = dir.join("crates/gone_sim/src");
        write_rust_lines(&src, "nested/deep.rs", 5);
        write_rust_lines(&src, "top.rs", 5);
        let mut files = Vec::new();
        super::collect_rust_files(&src, &mut files);
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
