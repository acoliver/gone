//! Command-plan helpers for building and running `std::process::Command`.
//!
//! Every cargo-backed step is an argument vector on `std::process::Command`,
//! never a shell string, so the same automation runs natively on every
//! platform (ported from jefe's xtask, issue #4).

use std::borrow::Cow;
use std::env;
use std::ffi::OsStr;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Output, Stdio};

use crate::fd_limit::{FD_EXHAUSTION_HINT, is_too_many_open_files};

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

/// Build the `CommandFailed` for a spawn that never started, appending the
/// fd-exhaustion hint when the OS refused for lack of file descriptors
/// (issue #17: the startup raise is the real fix, this only makes the
/// residual failure actionable).
fn spawn_failure(program: &str, args: &[String], err: &std::io::Error) -> CommandFailed {
    let mut stderr = format!("failed to spawn `{program}`: {err}");
    if is_too_many_open_files(err) {
        stderr.push_str(FD_EXHAUSTION_HINT);
    }
    CommandFailed {
        program: program.to_string(),
        args: args.to_vec(),
        status: None,
        stdout: Vec::new(),
        stderr: stderr.into_bytes(),
    }
}

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
        let status = self
            .to_command()
            .status()
            .map_err(|err| spawn_failure(&self.program, &self.args, &err))?;
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
            .map_err(|err| spawn_failure(&self.program, &self.args, &err))?;
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

/// RAII guard holding a display-awake assertion for one harness lane
/// (issue #23).
///
/// macOS declines Metal presentations to a sleeping display even while the
/// desktop keeps compositing in memory, so a lane that opens the canary
/// window fails every present while the display is asleep, regardless of
/// which lane is running. The guard spawns `caffeinate -d -u` (hold a
/// display-awake assertion and declare user activity, which also wakes an
/// already-sleeping display) with null stdio and holds it for the lane's
/// whole duration; [`Drop`] kills and reaps it.
///
/// Spawn failure (no `caffeinate` on PATH) degrades to an inert guard with a
/// one-line warning instead of failing the lane: the canary present gate
/// remains the real windowed-lane guard. On non-macOS targets the guard is
/// an unconditional no-op, so every call site compiles unchanged.
///
/// Bind the guard to a named variable (`let _display = ...`), never
/// `let _ =`: the latter drops it at the end of the statement.
pub struct DisplayAssertion {
    /// The held assertion process, or `None` when the guard is inert
    /// (non-macOS target or spawn failure).
    child: Option<Child>,
}

impl DisplayAssertion {
    /// Acquire the lane's display-awake assertion.
    ///
    /// Infallible by design: on non-macOS targets, or when the assertion
    /// program cannot be spawned, the guard degrades to an inert no-op (see
    /// the type docs) rather than failing the lane.
    #[must_use]
    pub fn acquire() -> Self {
        if cfg!(target_os = "macos") {
            Self::spawn("caffeinate", &["-d", "-u"])
        } else {
            Self { child: None }
        }
    }

    /// Spawn `program` with `args` as the assertion holder. Split out from
    /// [`acquire`](Self::acquire) so tests can hold a plain `sleep` instead
    /// of `caffeinate` and observe the kill-on-drop teardown.
    fn spawn(program: &str, args: &[&str]) -> Self {
        match Command::new(program)
            .args(args)
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()
        {
            Ok(child) => Self { child: Some(child) },
            Err(err) => {
                eprintln!(
                    "xtask: warning: display-awake assertion unavailable \
                     (`{program}` failed to spawn: {err}); the canary present \
                     gate remains the windowed-lane guard"
                );
                Self { child: None }
            }
        }
    }

    /// Test-only pid of the held child; `None` when the guard is inert.
    #[cfg(all(test, unix))]
    fn test_pid(&self) -> Option<u32> {
        self.child.as_ref().map(Child::id)
    }
}

impl Drop for DisplayAssertion {
    fn drop(&mut self) {
        // Best-effort teardown: killing an already-exited child fails
        // harmlessly, and `wait` reaps in every case so no zombie outlives
        // the guard.
        if let Some(child) = &mut self.child {
            let _ = child.kill();
            let _ = child.wait();
        }
    }
}

/// Tests for plan construction, repo-root resolution, and the
/// display-assertion guard.
#[cfg(test)]
mod tests {
    use super::CommandPlan;
    use super::DisplayAssertion;
    use super::repo_root_from;
    use super::spawn_failure;
    use crate::test_support::unique_temp_dir;
    use std::fs;

    #[test]
    fn fd_exhaustion_spawn_errors_carry_the_raise_hint() {
        // errno 23 is the ENFILE report from issue #17; errno 24 is EMFILE,
        // the same practical failure. Both must name the limit and the raise.
        for errno in [23, 24] {
            let err = std::io::Error::from_raw_os_error(errno);
            let failed = spawn_failure("cargo", &["build".to_string()], &err);
            assert!(failed.status.is_none());
            let stderr = String::from_utf8_lossy(&failed.stderr);
            assert!(stderr.starts_with("failed to spawn `cargo`"));
            assert!(
                stderr.contains("\nhint:"),
                "errno {errno} must append a hint line, got: {stderr}"
            );
            assert!(
                stderr.contains("RLIMIT_NOFILE"),
                "hint must name the fd limit, got: {stderr}"
            );
            assert!(
                stderr.contains("ulimit -n 10240"),
                "hint must suggest the raise, got: {stderr}"
            );
        }
    }

    #[test]
    fn ordinary_spawn_errors_carry_no_hint() {
        let err = std::io::Error::from_raw_os_error(2);
        let failed = spawn_failure("cargo", &[], &err);
        let stderr = String::from_utf8_lossy(&failed.stderr);
        assert!(stderr.starts_with("failed to spawn `cargo`"));
        assert!(!stderr.contains("hint"), "got: {stderr}");
    }

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

    #[cfg(unix)]
    #[test]
    fn guard_kills_its_child_on_drop() {
        use std::process::{Command, Stdio};
        use std::time::{Duration, Instant};

        let guard = DisplayAssertion::spawn("sleep", &["30"]);
        let pid = guard.test_pid().expect("sleep child must spawn");

        // Watcher exits as soon as `kill -0` can no longer signal the pid,
        // i.e. the process is gone — killed and reaped, since a zombie would
        // still be signalable.
        let mut watcher = Command::new("sh")
            .arg("-c")
            .arg(format!(
                "while kill -0 {pid} 2>/dev/null; do sleep 0.05; done"
            ))
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()
            .expect("spawn the liveness watcher");
        std::thread::sleep(Duration::from_millis(150));
        assert!(
            watcher.try_wait().expect("watcher poll").is_none(),
            "sleep must stay alive while the guard is held"
        );

        drop(guard);

        let deadline = Instant::now() + Duration::from_secs(10);
        loop {
            if let Some(status) = watcher.try_wait().expect("watcher poll after drop") {
                assert!(
                    status.success(),
                    "watcher must exit cleanly once the pid is gone"
                );
                break;
            }
            assert!(
                Instant::now() < deadline,
                "sleep {pid} outlived the guard's drop"
            );
            std::thread::sleep(Duration::from_millis(50));
        }
    }

    #[cfg(unix)]
    #[test]
    fn spawn_failure_degrades_to_an_inert_guard() {
        let guard = DisplayAssertion::spawn("gone-issue23-definitely-not-a-binary", &[]);
        assert_eq!(
            guard.test_pid(),
            None,
            "a failed spawn must degrade to the inert guard"
        );
        drop(guard);
    }

    #[test]
    fn acquire_constructs_and_drops_without_error_on_every_platform() {
        // macOS: briefly holds and releases the real caffeinate assertion;
        // elsewhere: exercises the no-op path. Either way the production
        // entry point must construct and drop without panicking.
        drop(DisplayAssertion::acquire());
    }
}
