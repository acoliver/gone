//! xtask command-line surface and dispatch (issue #4, harness wired in issue #5).
//!
//! One entry point: `cargo xtask <command>`. Argument parsing is hand-rolled
//! over the standard library. Every cargo-backed step is a `CommandPlan`
//! argument vector, never a shell string; policy checks call their modules
//! directly. Aggregate commands fail fast: the first failing step aborts the
//! run and names itself.

use std::path::Path;
use std::process::ExitCode;

use crate::architecture;
use crate::clippy_policy;
use crate::process::{CommandFailed, CommandPlan, repo_root};
use crate::source_size;

/// Cross-target that must keep compiling for Windows players.
const WINDOWS_TARGET: &str = "x86_64-pc-windows-msvc";
/// Cross-target that must keep compiling for Linux players.
const LINUX_TARGET: &str = "x86_64-unknown-linux-gnu";

/// The aggregate `ci` ordering (fail-fast sequence, issue #4). The render
/// canary runs immediately after the harness smoke step: the smoke run
/// exercises the headless default (no window), the render-check step is the
/// one windowed test.
const CI_STEPS: &[&str] = &[
    "fmt",
    "check-clippy-allows",
    "check-source-size",
    "check-architecture",
    "lint",
    "complexity",
    "build",
    "test",
    "cross-check-windows",
    "cross-check-linux",
    "harness",
    "render-check",
];

/// Fast iteration: everything local, no cross-targets, no harness.
const QUICK_STEPS: &[&str] = &[
    "fmt",
    "check-clippy-allows",
    "check-source-size",
    "check-architecture",
    "lint",
    "build",
    "test",
];

/// The xtask exit code for a missing or malformed invocation.
const EXIT_USAGE: u8 = 2;

/// Run the xtask CLI over `argv` (without the program name) and return the
/// process exit code.
#[must_use]
pub fn run(argv: &[String]) -> ExitCode {
    let Some(command) = argv.first() else {
        usage();
        return ExitCode::from(EXIT_USAGE);
    };
    let rest = &argv[1..];
    let outcome = match command.as_str() {
        "ci" => with_root(|root| run_steps("ci", CI_STEPS, root)),
        "quick" => with_root(|root| run_steps("quick", QUICK_STEPS, root)),
        "fmt" => with_root(|root| run_announced(&fmt_plan(root))),
        "lint" => with_root(|root| run_announced(&lint_plan(root))),
        "complexity" => with_root(|root| run_announced(&complexity_plan(root))),
        "build" => with_root(|root| run_announced(&build_plan(root))),
        "test" => with_root(|root| run_announced(&test_plan(root))),
        "harness" => with_root(|root| run_harness_command(rest, root)),
        "check" => with_root(|root| run_check(rest, root)),
        "help" | "--help" | "-h" => {
            usage();
            return ExitCode::SUCCESS;
        }
        other => {
            eprintln!("error: unknown xtask command `{other}`");
            usage();
            return ExitCode::from(EXIT_USAGE);
        }
    };
    exit(outcome)
}

fn usage() {
    eprintln!(
        "usage: cargo xtask <command>

commands:
  ci                   full local CI gate (fail-fast; the harness steps run smoke, then the render canary)
  quick                fmt, the three policy checks, clippy, locked build + test
  fmt                  cargo fmt --all --check
  lint                 strict clippy (warnings as errors)
  complexity           clippy with the complexity-threshold lints surfaced alone
  build                locked workspace build
  test                 locked workspace test
  harness smoke        build gone_app + gone_harness (locked) and run the smoke scenario
  harness <scenario>   run one scenario file (builds both binaries first)
  harness compare <s>   run a scenario twice and diff the event timelines
  harness perf [s]     run the perf calibration lane against the checked-in policy
  harness render-check  run the render canary: smoke scenario windowed, the one onscreen capture machine-verified
  check clippy-allows  zero clippy allow/expect suppressions + clippy.toml sync
  check source-size    per-file line gate (warn 750, fail 1000)
  check architecture   gone_sim/gone_harness dependency + protocol-module boundary gate"
    );
}

fn exit(result: Result<(), CommandFailed>) -> ExitCode {
    match result {
        Ok(()) => ExitCode::SUCCESS,
        Err(err) => {
            eprintln!("xtask: {err}");
            ExitCode::FAILURE
        }
    }
}

fn with_root(run: impl FnOnce(&Path) -> Result<(), CommandFailed>) -> Result<(), CommandFailed> {
    repo_root().map_err(|err| CommandFailed {
        program: "xtask".into(),
        args: Vec::new(),
        status: None,
        stdout: Vec::new(),
        stderr: err.into_bytes(),
    })?;
    let root = repo_root().expect("root resolved above");
    run(&root)
}

/// Run an ordered step list, printing each step name and the command it
/// runs, and stop at the first failure.
fn run_steps(label: &str, steps: &[&str], root: &Path) -> Result<(), CommandFailed> {
    for step in steps {
        eprintln!("xtask {label}: {step}");
        run_named_step(step, root).map_err(|err| named_failure(label, step, &err))?;
    }
    Ok(())
}

fn run_named_step(step: &str, root: &Path) -> Result<(), CommandFailed> {
    match step {
        "fmt" => run_announced(&fmt_plan(root)),
        "check-clippy-allows" => clippy_policy::run_repo_check(root),
        "check-source-size" => source_size::run_repo_check(root),
        "check-architecture" => architecture::run_repo_check(root),
        "lint" => run_announced(&lint_plan(root)),
        "complexity" => run_announced(&complexity_plan(root)),
        "build" => run_announced(&build_plan(root)),
        "test" => run_announced(&test_plan(root)),
        "cross-check-windows" => run_announced(&cross_check_plan(root, WINDOWS_TARGET)),
        "cross-check-linux" => run_announced(&cross_check_plan(root, LINUX_TARGET)),
        "harness" => run_harness_command(&[], root),
        "render-check" => run_harness_command(&["render-check".to_string()], root),
        unknown => Err(CommandFailed {
            program: "xtask".into(),
            args: vec![unknown.into()],
            status: None,
            stdout: Vec::new(),
            stderr: format!("unknown xtask step `{unknown}`").into_bytes(),
        }),
    }
}

fn run_announced(plan: &CommandPlan) -> Result<(), CommandFailed> {
    eprintln!("xtask: `{}`", plan.render());
    plan.run_inherit()
}

fn named_failure(label: &str, step: &str, err: &CommandFailed) -> CommandFailed {
    CommandFailed {
        program: format!("xtask {label} step `{step}`"),
        args: Vec::new(),
        status: err.status,
        stdout: Vec::new(),
        stderr: format!("step `{step}` failed\ncaused by: {err}").into_bytes(),
    }
}

/// `harness smoke` builds the two binaries (locked) and runs the smoke scenario;
/// `harness <scenario-path>` runs one scenario; `harness compare <scenario>`
/// builds once then runs the scenario twice and diffs the timelines;
/// `harness perf [scenario]` runs the perf calibration lane against the
/// checked-in policy (default scenario derived from the policy);
/// `harness render-check` runs the smoke scenario through the canary lane
/// (the runner's `--render-check`: windowed, onscreen capture machine-verified,
/// run dir prefixed `rc`). The runner owns the child app's lifecycle (spawn,
/// kill-on-timeout, reap), so xtask just forwards the exit code.
fn run_harness_command(rest: &[String], root: &Path) -> Result<(), CommandFailed> {
    build_harness_binaries(root)?;
    let mut plan = CommandPlan::new("cargo")
        .args(["run", "-p", "gone_harness", "--bin", "gone_harness", "--"])
        .current_dir(root);
    match rest {
        [] => {
            plan = plan.args(["smoke"]);
        }
        [cmd] if cmd == "render-check" => {
            plan = plan.args(["--render-check", "smoke"]);
        }
        [cmd, ..] if cmd == "render-check" => {
            return Err(usage_error(
                "harness",
                "render-check takes no scenario (it runs the smoke scenario in the canary lane)",
            ));
        }
        [cmd, scenario] if cmd == "compare" => {
            plan = plan.args(["compare", scenario]);
        }
        [cmd, ..] if cmd == "compare" => {
            return Err(usage_error(
                "harness",
                "too many arguments for `compare <scenario>`",
            ));
        }
        [cmd] if cmd == "smoke" => {
            plan = plan.args(["smoke"]);
        }
        [cmd] if cmd == "perf" => {
            plan = plan.args(["perf"]);
        }
        [cmd, scenario] if cmd == "perf" => {
            plan = plan.args(["perf", scenario]);
        }
        [path, ..] => {
            plan = plan.args([path]);
        }
    }
    run_announced(&plan)
}

/// Locked build of the two binaries the runner drives.
fn build_harness_binaries(root: &Path) -> Result<(), CommandFailed> {
    let plan = CommandPlan::new("cargo")
        .args([
            "build",
            "--locked",
            "--bin",
            "gone_app",
            "--bin",
            "gone_harness",
        ])
        .current_dir(root);
    run_announced(&plan)
}

fn run_check(rest: &[String], root: &Path) -> Result<(), CommandFailed> {
    let Some(target) = rest.first() else {
        eprintln!("usage: cargo xtask check <clippy-allows|source-size|architecture>");
        return Err(usage_error("check", "missing policy name"));
    };
    match target.as_str() {
        "clippy-allows" => clippy_policy::run_repo_check(root),
        "source-size" => source_size::run_repo_check(root),
        "architecture" => architecture::run_repo_check(root),
        other => {
            eprintln!("error: unknown check target `{other}`");
            Err(usage_error("check", "unknown policy name"))
        }
    }
}

fn usage_error(command: &str, reason: &str) -> CommandFailed {
    CommandFailed {
        program: "xtask".into(),
        args: vec![command.into()],
        status: None,
        stdout: Vec::new(),
        stderr: format!("usage error: {reason}").into_bytes(),
    }
}

fn clippy_conf_dir(root: &Path) -> String {
    root.join(".github")
        .join("clippy")
        .to_string_lossy()
        .into_owned()
}

fn fmt_plan(root: &Path) -> CommandPlan {
    CommandPlan::new("cargo")
        .args(["fmt", "--all", "--check"])
        .current_dir(root)
}

fn lint_plan(root: &Path) -> CommandPlan {
    CommandPlan::new("cargo")
        .args([
            "clippy",
            "--workspace",
            "--all-targets",
            "--",
            "-D",
            "warnings",
        ])
        .env("CLIPPY_CONF_DIR", clippy_conf_dir(root))
        .current_dir(root)
}

fn complexity_plan(root: &Path) -> CommandPlan {
    // Same clippy driver as `lint`, surfaced separately: groups are allowed
    // (command-line -A outranks the workspace manifest denies) so only the
    // five threshold lints can fail the run.
    CommandPlan::new("cargo")
        .args([
            "clippy",
            "--workspace",
            "--all-targets",
            "--",
            "-A",
            "clippy::all",
            "-A",
            "clippy::pedantic",
            "-D",
            "clippy::cognitive_complexity",
            "-D",
            "clippy::too_many_lines",
            "-D",
            "clippy::too_many_arguments",
            "-D",
            "clippy::type_complexity",
            "-D",
            "clippy::struct_excessive_bools",
        ])
        .env("CLIPPY_CONF_DIR", clippy_conf_dir(root))
        .current_dir(root)
}

fn build_plan(root: &Path) -> CommandPlan {
    CommandPlan::new("cargo")
        .args(["build", "--workspace", "--locked"])
        .current_dir(root)
}

fn test_plan(root: &Path) -> CommandPlan {
    CommandPlan::new("cargo")
        .args(["test", "--workspace", "--locked"])
        .current_dir(root)
}

fn cross_check_plan(root: &Path, target: &str) -> CommandPlan {
    CommandPlan::new("cargo")
        .args([
            "check",
            "--workspace",
            "--locked",
            "--all-targets",
            "--target",
            target,
        ])
        .current_dir(root)
}

/// Tests asserting step ordering invariants and command-plan shapes without
/// spawning any process.
#[cfg(test)]
mod tests {
    use super::{
        CI_STEPS, EXIT_USAGE, QUICK_STEPS, build_plan, complexity_plan, cross_check_plan, fmt_plan,
        lint_plan, run, test_plan,
    };
    use std::path::PathBuf;
    use std::process::ExitCode;

    fn root() -> PathBuf {
        PathBuf::from("/cfg-root")
    }

    #[test]
    fn usage_and_unknown_commands_exit_two() {
        assert_eq!(run(&[]), ExitCode::from(EXIT_USAGE));
        assert_eq!(
            run(&["definitely-not-a-command".to_string()]),
            ExitCode::from(EXIT_USAGE)
        );
    }

    #[test]
    fn help_exits_success() {
        assert_eq!(run(&["--help".to_string()]), ExitCode::SUCCESS);
        assert_eq!(run(&["help".to_string()]), ExitCode::SUCCESS);
    }

    #[test]
    fn ci_is_fail_fast_ending_at_the_render_canary() {
        assert_eq!(*CI_STEPS.last().expect("nonempty"), "render-check");
        assert_eq!(
            CI_STEPS.first().copied(),
            Some("fmt"),
            "fmt must run before every policy step"
        );
    }

    #[test]
    fn ci_render_check_runs_immediately_after_the_smoke_step() {
        let harness_pos = CI_STEPS
            .iter()
            .position(|s| *s == "harness")
            .expect("harness step");
        assert_eq!(
            CI_STEPS.get(harness_pos + 1),
            Some(&"render-check"),
            "the render canary is its own step, directly after smoke"
        );
    }

    #[test]
    fn ci_cross_targets_run_after_test_and_before_harness() {
        let test_pos = CI_STEPS
            .iter()
            .position(|s| *s == "test")
            .expect("test step");
        let windows_pos = CI_STEPS
            .iter()
            .position(|s| *s == "cross-check-windows")
            .expect("windows");
        let linux_pos = CI_STEPS
            .iter()
            .position(|s| *s == "cross-check-linux")
            .expect("linux");
        let harness_pos = CI_STEPS
            .iter()
            .position(|s| *s == "harness")
            .expect("harness");
        assert!(test_pos < windows_pos && windows_pos < harness_pos);
        assert!(test_pos < linux_pos && linux_pos < harness_pos);
    }

    #[test]
    fn ci_has_no_duplicate_steps() {
        let mut seen = CI_STEPS.to_vec();
        seen.sort_unstable();
        seen.dedup();
        assert_eq!(seen.len(), CI_STEPS.len());
    }

    #[test]
    fn quick_is_ci_without_complexity_cross_targets_and_harness_lanes() {
        let excluded = [
            "complexity",
            "cross-check-windows",
            "cross-check-linux",
            "harness",
            "render-check",
        ];
        for step in QUICK_STEPS {
            assert!(!excluded.contains(step), "{step} must not run under quick");
        }
        let expected: Vec<&str> = CI_STEPS
            .iter()
            .copied()
            .filter(|s| !excluded.contains(s))
            .collect();
        assert_eq!(QUICK_STEPS, expected.as_slice());
    }

    #[test]
    fn fmt_plan_checks_everything() {
        assert_eq!(fmt_plan(&root()).render(), "cargo fmt --all --check");
    }

    #[test]
    fn lint_plan_denies_warnings_with_ci_conf_dir() {
        let plan = lint_plan(&root());
        assert_eq!(
            plan.render(),
            "cargo clippy --workspace --all-targets -- -D warnings"
        );
        assert_eq!(plan.env[0].0, "CLIPPY_CONF_DIR");
        assert!(plan.env[0].1.ends_with(".github/clippy"));
    }

    #[test]
    fn complexity_plan_denies_only_the_threshold_lints() {
        let plan = complexity_plan(&root());
        let deny_positions: Vec<usize> = plan
            .args
            .iter()
            .enumerate()
            .filter_map(|(i, a)| (a == "-D").then_some(i))
            .collect();
        let denied: Vec<&str> = deny_positions
            .iter()
            .map(|&i| plan.args[i + 1].as_str())
            .collect();
        assert_eq!(
            denied,
            vec![
                "clippy::cognitive_complexity",
                "clippy::too_many_lines",
                "clippy::too_many_arguments",
                "clippy::type_complexity",
                "clippy::struct_excessive_bools",
            ]
        );
        assert!(plan.args.contains(&"-A".to_string()));
        assert!(plan.args.contains(&"clippy::pedantic".to_string()));
    }

    #[test]
    fn build_and_test_are_locked() {
        assert!(build_plan(&root()).args.contains(&"--locked".to_string()));
        assert!(test_plan(&root()).args.contains(&"--locked".to_string()));
    }

    #[test]
    fn cross_check_plan_targets_the_requested_triple() {
        let plan = cross_check_plan(&root(), "x86_64-pc-windows-msvc");
        assert!(plan.render().contains("--target x86_64-pc-windows-msvc"));
        assert!(plan.args.contains(&"--all-targets".to_string()));
        assert!(plan.args.contains(&"--locked".to_string()));
    }

    #[test]
    fn plans_anchor_at_the_repo_root() {
        assert_eq!(fmt_plan(&root()).current_dir, Some(root()));
    }
}
