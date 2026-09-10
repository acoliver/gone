//! Command-plan helpers for building and running `std::process::Command`.
//!
//! Every cargo-backed step is an argument vector on `std::process::Command`,
//! never a shell string, so the same automation runs natively on every
//! platform (ported from jefe's xtask, issue #4).

use std::borrow::Cow;
use std::env;
use std::ffi::OsStr;
use std::path::{Path, PathBuf};
use std::process::{Command, Output, Stdio};

/// A captured failure while running an xtask-driven child process.
#[derive(Debug)]
pub struct CommandFailed {
    pub program: String,
    pub args: Vec<String>,
    pub status: Option<i32>,
    pub stdout: Vec<u8>,
    pub stderr: Vec<u8>,
}

impl std::fmt::Display for CommandFailed {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "command `{}` exited with status {:?}",
            shell_like(&self.program, &self.args),
            self.status
        )?;
        if !self.stdout.is_empty() {
            write!(
                f,
                "\n--- stdout ---\n{}",
                String::from_utf8_lossy(&self.stdout).trim_end()
            )?;
        }
        if !self.stderr.is_empty() {
            write!(
                f,
                "\n--- stderr ---\n{}",
                String::from_utf8_lossy(&self.stderr).trim_end()
            )?;
        }
        Ok(())
    }
}

impl std::error::Error for CommandFailed {}

/// A planned child process. Building a plan never spawns a process, so tests
/// can assert command shapes deterministically.
#[derive(Debug, Clone)]
pub struct CommandPlan {
    pub program: String,
    pub args: Vec<String>,
    pub env: Vec<(String, String)>,
    pub current_dir: Option<PathBuf>,
}

impl CommandPlan {
    pub fn new(program: impl Into<String>) -> Self {
        Self {
            program: program.into(),
            args: Vec::new(),
            env: Vec::new(),
            current_dir: None,
        }
    }

    #[must_use]
    pub fn args(mut self, args: impl IntoIterator<Item = impl AsRef<OsStr>>) -> Self {
        for arg in args {
            self.args.push(arg.as_ref().to_string_lossy().into_owned());
        }
        self
    }

    #[must_use]
    pub fn env(mut self, key: impl Into<String>, value: impl Into<String>) -> Self {
        self.env.push((key.into(), value.into()));
        self
    }

    #[must_use]
    pub fn current_dir(mut self, dir: impl Into<PathBuf>) -> Self {
        self.current_dir = Some(dir.into());
        self
    }

    /// Build the underlying `std::process::Command` without running it.
    #[must_use]
    pub fn to_command(&self) -> Command {
        let mut cmd = Command::new(&self.program);
        cmd.args(&self.args);
        for (key, value) in &self.env {
            cmd.env(key, value);
        }
        if let Some(dir) = &self.current_dir {
            cmd.current_dir(dir);
        }
        cmd
    }

    /// Run the plan with inherited stdio so the child's output streams to the
    /// caller.
    ///
    /// # Errors
    /// Returns `CommandFailed` if the child cannot be spawned or exits nonzero.
    pub fn run_inherit(&self) -> Result<(), CommandFailed> {
        let status = self.to_command().status().map_err(|err| CommandFailed {
            program: self.program.clone(),
            args: self.args.clone(),
            status: None,
            stdout: Vec::new(),
            stderr: format!("failed to spawn `{}`: {err}", self.program).into_bytes(),
        })?;
        if status.success() {
            Ok(())
        } else {
            Err(CommandFailed {
                program: self.program.clone(),
                args: self.args.clone(),
                status: status.code(),
                stdout: Vec::new(),
                stderr: Vec::new(),
            })
        }
    }

    /// Run the plan capturing stdout and stderr, for policy checks that must
    /// inspect child output.
    ///
    /// # Errors
    /// Returns `CommandFailed` on spawn failure or nonzero exit, carrying the
    /// captured streams.
    pub fn run_captured(&self) -> Result<Output, CommandFailed> {
        let output = self
            .to_command()
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .output()
            .map_err(|err| CommandFailed {
                program: self.program.clone(),
                args: self.args.clone(),
                status: None,
                stdout: Vec::new(),
                stderr: format!("failed to spawn `{}`: {err}", self.program).into_bytes(),
            })?;
        if output.status.success() {
            Ok(output)
        } else {
            Err(CommandFailed {
                program: self.program.clone(),
                args: self.args.clone(),
                status: output.status.code(),
                stdout: output.stdout,
                stderr: output.stderr,
            })
        }
    }

    /// Render the plan as a shell-like string for diagnostics and tests.
    #[must_use]
    pub fn render(&self) -> String {
        shell_like(&self.program, &self.args)
    }
}

/// Resolve the repository root: the nearest ancestor of the xtask manifest
/// directory whose `Cargo.toml` declares a `[workspace]`. xtask lives at
/// `crates/xtask`, so the search walks up past `crates/` to the repo root.
///
/// # Errors
/// Returns an error if `CARGO_MANIFEST_DIR` is unset — xtask is only
/// supported via `cargo xtask`, which always sets it — or if no workspace
/// manifest is found above it.
pub fn repo_root() -> Result<PathBuf, String> {
    let dir = env::var_os("CARGO_MANIFEST_DIR")
        .ok_or_else(|| "CARGO_MANIFEST_DIR is not set; run xtask via `cargo xtask`".to_string())?;
    repo_root_from(Path::new(&dir))
}

/// Pure core of `repo_root`, split out so the ascent is testable with
/// fixture trees instead of process-wide environment state.
fn repo_root_from(start: &Path) -> Result<PathBuf, String> {
    let mut current = start;
    loop {
        let manifest = current.join("Cargo.toml");
        let declares_workspace = manifest.is_file()
            && std::fs::read_to_string(&manifest).is_ok_and(|text| text.contains("[workspace]"));
        if declares_workspace {
            return Ok(current.to_path_buf());
        }
        match current.parent() {
            Some(parent) => current = parent,
            None => {
                return Err(format!(
                    "no workspace root (Cargo.toml with [workspace]) found above {}",
                    start.display()
                ));
            }
        }
    }
}

fn shell_like(program: &str, args: &[String]) -> String {
    let mut parts = Vec::with_capacity(args.len() + 1);
    parts.push(Cow::Borrowed(program));
    for arg in args {
        parts.push(Cow::Borrowed(arg.as_str()));
    }
    parts.join(" ")
}

/// Tests for plan construction and repo-root resolution.
#[cfg(test)]
mod tests {
    use super::CommandPlan;
    use super::repo_root_from;
    use crate::test_support::unique_temp_dir;
    use std::fs;

    #[test]
    fn render_joins_program_and_args() {
        let plan = CommandPlan::new("cargo")
            .args(["fmt", "--all", "--check"])
            .current_dir("/repo");
        assert_eq!(plan.render(), "cargo fmt --all --check");
        assert_eq!(plan.current_dir, Some("/repo".into()));
    }

    #[test]
    fn env_entries_survive_construction() {
        let plan = CommandPlan::new("cargo").env("CLIPPY_CONF_DIR", "/repo/.github/clippy");
        assert_eq!(
            plan.env,
            vec![("CLIPPY_CONF_DIR".into(), "/repo/.github/clippy".into())]
        );
    }

    #[test]
    fn workspace_root_is_found_above_the_xtask_crate() {
        let repo = unique_temp_dir("root");
        fs::create_dir_all(repo.join("crates/xtask/src")).expect("dirs");
        fs::write(
            repo.join("Cargo.toml"),
            "[workspace]\nmembers = [\"crates/xtask\"]\n",
        )
        .expect("write workspace manifest");
        let root = repo_root_from(&repo.join("crates/xtask")).expect("root must resolve");
        assert_eq!(root, repo);
    }

    #[test]
    fn manifest_at_the_repo_root_is_recognized_directly() {
        let repo = unique_temp_dir("root-flat");
        fs::write(repo.join("Cargo.toml"), "[workspace]\n").expect("write manifest");
        assert_eq!(repo_root_from(&repo).expect("root must resolve"), repo);
    }

    #[test]
    fn member_manifest_does_not_stop_the_ascent() {
        let repo = unique_temp_dir("root-member");
        fs::create_dir_all(repo.join("crates/gone_sim/src")).expect("dirs");
        // A member manifest exists but declares no [workspace] table; the
        // root manifest below does.
        fs::write(
            repo.join("crates/gone_sim/Cargo.toml"),
            "[package]\nname = \"gone_sim\"\n",
        )
        .expect("write member manifest");
        fs::write(
            repo.join("Cargo.toml"),
            "[workspace]\nmembers = [\"crates/gone_sim\"]\n",
        )
        .expect("write workspace manifest");
        let root = repo_root_from(&repo.join("crates/gone_sim")).expect("root must resolve");
        assert_eq!(root, repo);
    }

    #[test]
    fn tree_without_workspace_manifest_is_rejected() {
        let dir = unique_temp_dir("root-none");
        let err = repo_root_from(&dir).expect_err("no workspace manifest must fail");
        assert!(err.contains("no workspace root"));
    }
}
