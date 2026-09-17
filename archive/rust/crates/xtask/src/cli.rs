//! xtask command-line surface and dispatch (issue #4, harness wired in issue #5).
//!
//! One entry point: `cargo xtask <command>`. Argument parsing is hand-rolled
//! over the standard library. Every cargo-backed step is a `CommandPlan`
//! argument vector, never a shell string; policy checks call their modules
//! directly. Aggregate commands fail fast: the first failing step aborts the
//! run and names itself.
//!
//! Harness lanes are parsed into a [`HarnessLane`] before anything runs, so an
//! invalid lane fails the invocation by name and the display-awake assertion
//! is scoped by lane semantics, not by substring matching: only a lane that
//! opens a real window and presents to it (the render canary, issue #23)
//! holds `caffeinate -d -u`, because macOS declines Metal presentations to a
//! sleeping display. Offscreen lanes render into the harness `Image` target,
//! never touch the `WindowServer`, and acquire no assertion and no synthesized
//! activity, so they run unattended while the desktop stays in the user's
//! control (issue #8).

use std::path::Path;
use std::process::ExitCode;

use crate::architecture;
use crate::clippy_policy;
use crate::process::{CommandFailed, CommandPlan, DisplayAssertion, repo_root};
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
        "capture-opening" => with_root(run_capture_opening),
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
  harness gameplay-smoke  run the gameplay lane: real game content, room and scripted-look yaw assertions
  harness gameplay-full  run the whole opening beat: wake, get-up, walk to the hatch, position assertions
  harness <scenario>   run one scenario file (builds both binaries first)
  harness compare <s>   run a scenario twice and diff the event timelines
  harness calibration  run the 4-cell calibration matrix (luminance step AE on/off, patch metering, uniform control) against predeclared assertions
  harness perf [s]     run the perf calibration lane against the checked-in policy
  harness render-check  run the render canary: smoke scenario windowed, the one onscreen capture machine-verified
  capture-opening      windowless GPU capture of the authored opening: gameplay-smoke then gameplay-full,
                       each lane's exact run dir printed on its ARTIFACTS line; fails if either lane fails
  display-awake assertion (caffeinate -d -u): held only by lanes that open a real window and present
  to it (render-check; issue #23). Offscreen lanes open no window, need no drawable, and acquire no
  assertion and no synthesized activity, so they run unattended while the desktop stays usable (issue #8)
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

/// One harness invocation, parsed before anything runs (issue #8). The
/// variants are exactly the lanes the runner knows; the parse rejects
/// builtin misuse with a named error instead of forwarding it as a scenario
/// path. [`needs_display`](Self::needs_display) is the display-assertion
/// gate: the runner opens a window only on the render canary.
#[derive(Debug, PartialEq, Eq)]
enum HarnessLane {
    /// The bootstrap smoke scenario (the default).
    Smoke,
    /// The built-in gameplay smoke lane: room + scripted-look yaw assertions,
    /// and the wake beats (closed hold, both blink triplets, post-wake look).
    GameplaySmoke,
    /// The built-in whole-opening-beat lane: wake progression, standing at
    /// the exit waypoint, the door walk.
    GameplayFull,
    /// The 4-cell calibration-evidence matrix.
    Calibration,
    /// The perf lane, optionally against a caller-named perf scenario.
    Perf {
        /// Optional scenario file; omitted selects the policy-derived one.
        scenario: Option<String>,
    },
    /// The determinism compare lane over one scenario.
    Compare {
        /// The scenario file compared.
        scenario: String,
    },
    /// One caller-named scenario file.
    Scenario {
        /// The scenario path forwarded verbatim.
        path: String,
    },
    /// The render canary: the one lane that opens a real window.
    RenderCheck,
}

impl HarnessLane {
    /// True only for lanes that present to a real window. A windowed lane
    /// needs the display awake for its whole duration (issue #23); offscreen
    /// lanes render into the harness `Image` target, need no drawable, and
    /// acquire no assertion (issue #8). A future windowed lifecycle lane
    /// would join `RenderCheck` here.
    #[must_use]
    fn needs_display(&self) -> bool {
        matches!(self, HarnessLane::RenderCheck)
    }

    /// The runner arguments this lane forwards, verbatim.
    #[must_use]
    fn runner_args(&self) -> Vec<&str> {
        match self {
            HarnessLane::Smoke => vec!["smoke"],
            HarnessLane::GameplaySmoke => vec!["gameplay-smoke"],
            HarnessLane::GameplayFull => vec!["gameplay-full"],
            HarnessLane::Calibration => vec!["calibration"],
            HarnessLane::Perf { scenario: None } => vec!["perf"],
            HarnessLane::Perf { scenario: Some(s) } => vec!["perf", s],
            HarnessLane::Compare { scenario } => vec!["compare", scenario],
            HarnessLane::Scenario { path } => vec![path],
            HarnessLane::RenderCheck => vec!["--render-check", "smoke"],
        }
    }

    /// The lane's name for step labels and failure messages.
    #[must_use]
    fn label(&self) -> &'static str {
        match self {
            HarnessLane::Smoke => "smoke",
            HarnessLane::GameplaySmoke => "gameplay-smoke",
            HarnessLane::GameplayFull => "gameplay-full",
            HarnessLane::Calibration => "calibration",
            HarnessLane::Perf { .. } => "perf",
            HarnessLane::Compare { .. } => "compare",
            HarnessLane::Scenario { .. } => "scenario",
            HarnessLane::RenderCheck => "render-check",
        }
    }
}

/// Parse a `cargo xtask harness` argument tail into a lane. Builtin misuse
/// (missing or extra arguments, unknown flags) is a parse error naming the
/// problem — never a silent forward to the runner as a scenario path.
///
/// # Errors
/// A message naming the malformed lane invocation.
fn parse_harness_lane(rest: &[String]) -> Result<HarnessLane, String> {
    match rest {
        [] => Ok(HarnessLane::Smoke),
        [one] => match one.as_str() {
            "smoke" => Ok(HarnessLane::Smoke),
            "gameplay-smoke" => Ok(HarnessLane::GameplaySmoke),
            "gameplay-full" => Ok(HarnessLane::GameplayFull),
            "calibration" => Ok(HarnessLane::Calibration),
            "perf" => Ok(HarnessLane::Perf { scenario: None }),
            "render-check" => Ok(HarnessLane::RenderCheck),
            "compare" => Err("compare requires a scenario: `harness compare <scenario>`".into()),
            arg if arg.starts_with('-') => Err(format!(
                "unknown harness flag `{arg}` (flags belong to the runner binary, not xtask lanes)"
            )),
            arg => Ok(HarnessLane::Scenario {
                path: arg.to_owned(),
            }),
        },
        [first, rest @ ..] => match first.as_str() {
            "render-check" => Err(
                "render-check takes no scenario (it runs the smoke scenario in the canary lane)"
                    .into(),
            ),
            "perf" if rest.len() == 1 => Ok(HarnessLane::Perf {
                scenario: Some(rest[0].clone()),
            }),
            "compare" if rest.len() == 1 => Ok(HarnessLane::Compare {
                scenario: rest[0].clone(),
            }),
            "perf" | "compare" => Err(format!("too many arguments for `{first} <scenario>`")),
            other => Err(format!("unexpected arguments after harness lane `{other}`")),
        },
    }
}

/// The runner command plan for one parsed lane: the same binary, working
/// dir, and argument forwarding the per-command match arms used to build
/// inline, now derived from the lane itself so the aggregate lanes cannot
/// drift from the single-lane ones.
fn harness_lane_plan(lane: &HarnessLane, root: &Path) -> CommandPlan {
    CommandPlan::new("cargo")
        .args(["run", "-p", "gone_harness", "--bin", "gone_harness", "--"])
        .args(lane.runner_args())
        .current_dir(root)
}

/// `harness <lane>` parses the invocation first (invalid lanes fail fast by
/// name), then builds the binaries, then runs the runner. The display-awake
/// assertion is scoped to the parsed lane: acquired only when the lane
/// actually opens a window (the render canary), before the build, exactly as
/// the unconditional pre-issue-#8 path held it for the whole lane (issue
/// #23). The runner owns the child app's lifecycle (spawn, kill-on-timeout,
/// reap), so xtask just forwards the exit code.
fn run_harness_command(rest: &[String], root: &Path) -> Result<(), CommandFailed> {
    let lane = parse_harness_lane(rest).map_err(|reason| usage_error("harness", &reason))?;
    let _display_awake = lane.needs_display().then(DisplayAssertion::acquire);
    build_harness_binaries(root)?;
    run_announced(&harness_lane_plan(&lane, root))
}

/// The opening-capture sequence, in run order: `gameplay-smoke` pins the
/// closed-eye hold, both blink triplets, and the post-wake look;
/// `gameplay-full` pins standing at the exit waypoint and the door walk.
/// Both are offscreen lanes (issue #8).
fn capture_opening_lanes() -> [HarnessLane; 2] {
    [HarnessLane::GameplaySmoke, HarnessLane::GameplayFull]
}

/// `capture-opening`: one documented command for the whole authored-opening
/// capture (issue #8). It builds the two binaries once, then runs the two
/// built-in gameplay lanes sequentially through the runner they always go
/// through — no new renderer, no window, no input injection, no display
/// assertion. Fail-fast: the first failing lane aborts the run and names
/// itself, so a nonzero exit means at least one lane's machine checks did
/// not hold. Each lane prints its exact run dir on its `ARTIFACTS:` line.
fn run_capture_opening(root: &Path) -> Result<(), CommandFailed> {
    eprintln!(
        "xtask capture-opening: windowless GPU capture of the authored opening \
         (no window, no display assertion; the desktop stays usable)"
    );
    build_harness_binaries(root)?;
    for lane in capture_opening_lanes() {
        eprintln!("xtask capture-opening: lane `{}`", lane.label());
        run_announced(&harness_lane_plan(&lane, root))
            .map_err(|err| named_failure("capture-opening", lane.label(), &err))?;
    }
    eprintln!(
        "xtask capture-opening: both lanes passed; exact run dirs are the \
         ARTIFACTS lines above, under\ngameplay-smoke: {}\ngameplay-full:  {}",
        root.join("tmp/harness/gameplay-smoke").display(),
        root.join("tmp/harness/gameplay-full").display(),
    );
    Ok(())
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
        CI_STEPS, EXIT_USAGE, HarnessLane, QUICK_STEPS, build_plan, capture_opening_lanes,
        complexity_plan, cross_check_plan, fmt_plan, harness_lane_plan, lint_plan,
        parse_harness_lane, run, test_plan,
    };
    use std::path::PathBuf;
    use std::process::ExitCode;

    fn root() -> PathBuf {
        PathBuf::from("/cfg-root")
    }

    /// Parse a harness tail written as string slices.
    fn lane(rest: &[&str]) -> Result<HarnessLane, String> {
        let owned: Vec<String> = rest.iter().map(|s| (*s).to_owned()).collect();
        parse_harness_lane(&owned)
    }

    #[test]
    fn offscreen_lanes_hold_no_display_assertion() {
        // Every lane xtask can run except the canary is the headless capture
        // lane: no window, no drawable, no assertion (issue #8).
        for parsed in [
            lane(&[]),
            lane(&["smoke"]),
            lane(&["gameplay-smoke"]),
            lane(&["gameplay-full"]),
            lane(&["calibration"]),
            lane(&["perf"]),
            lane(&["perf", "s.json"]),
            lane(&["compare", "s.json"]),
            lane(&["scenarios/one.json"]),
        ] {
            let parsed = parsed.expect("valid lane");
            assert!(
                !parsed.needs_display(),
                "lane `{parsed:?}` must not hold a display-awake assertion"
            );
        }
    }

    #[test]
    fn render_check_is_the_one_native_lane() {
        let parsed = lane(&["render-check"]).expect("valid lane");
        assert_eq!(parsed, HarnessLane::RenderCheck);
        assert!(parsed.needs_display(), "the canary presents to a window");
        assert_eq!(parsed.runner_args(), vec!["--render-check", "smoke"]);
    }

    #[test]
    fn invalid_harness_invocations_fail_the_parse() {
        for rest in [
            &["render-check", "smoke"][..],
            &["render-check", "anything"][..],
            &["compare"][..],
            &["compare", "a", "b"][..],
            &["perf", "a", "b"][..],
            &["smoke", "extra"][..],
            &["gameplay-smoke", "extra"][..],
            &["--render-check"][..],
            &["scenario.json", "extra"][..],
        ] {
            let err = lane(rest).expect_err("invalid lane must fail fast");
            assert!(
                err.contains("render-check takes no scenario")
                    || err.contains("requires a scenario")
                    || err.contains("too many arguments")
                    || err.contains("unexpected arguments")
                    || err.contains("unknown harness flag"),
                "parse error must name the problem for {rest:?}: {err}"
            );
        }
    }

    #[test]
    fn gameplay_lanes_forward_verbatim_and_stay_offscreen() {
        for (args, expected) in [
            (&["gameplay-smoke"][..], "gameplay-smoke"),
            (&["gameplay-full"][..], "gameplay-full"),
        ] {
            let parsed = lane(args).expect("valid lane");
            assert_eq!(parsed.runner_args(), vec![expected]);
            assert!(!parsed.needs_display());
        }
    }

    #[test]
    fn capture_opening_is_the_two_gameplay_lanes_windowless() {
        let lanes = capture_opening_lanes();
        assert!(matches!(lanes[0], HarnessLane::GameplaySmoke));
        assert!(matches!(lanes[1], HarnessLane::GameplayFull));
        assert!(
            lanes.iter().all(|lane| !lane.needs_display()),
            "the opening capture must never acquire a display assertion"
        );
    }

    #[test]
    fn lane_plans_target_the_runner_binary_at_the_root() {
        let plan = harness_lane_plan(&HarnessLane::GameplayFull, &root());
        assert_eq!(
            plan.render(),
            "cargo run -p gone_harness --bin gone_harness -- gameplay-full"
        );
        assert_eq!(plan.current_dir, Some(root()));
        let canary = harness_lane_plan(&HarnessLane::RenderCheck, &root());
        assert_eq!(
            canary.render(),
            "cargo run -p gone_harness --bin gone_harness -- --render-check smoke"
        );
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
