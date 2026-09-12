//! App discovery, run-identity, and the child-process contract: find the
//! built app binary, resolve its asset root, spawn it with the harness env
//! (including `BEVY_ASSET_ROOT`), and wait on it with the runner-owned
//! timeout, kill, and reap.

use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::time::{Duration, Instant};

use crate::error::{RunnerError, bail};

const ENV_HARNESS: &str = "GONE_HARNESS";
const ENV_SCENARIO: &str = "GONE_SCENARIO";
const ENV_OUT_DIR: &str = "GONE_OUT_DIR";
/// The environment name for the app-binary content hash the runner computed.
const ENV_APP_HASH: &str = "GONE_APP_HASH";
/// The environment name for the scenario content hash the runner computed.
const ENV_SCENARIO_HASH: &str = "GONE_SCENARIO_HASH";
/// The environment name bevy's asset server reads its asset base path from
/// (ahead of its `CARGO_MANIFEST_DIR` fallback). The runner sets it so the
/// child's asset resolution is explicit and never inherited from the
/// runner's own manifest context.
const ENV_ASSET_ROOT: &str = "BEVY_ASSET_ROOT";
/// Selects the app's canary lane: the run opens the window (focused: it must
/// be ordered in for its surface to present) and saves exactly one onscreen
/// capture at the first beat (verified by the `onscreen` protocol module in
/// `gone_harness`).
const ENV_RENDER_CHECK: &str = "GONE_RENDER_CHECK";

/// Spawn the app with harness env. The child is kept alive and reaped by this runner.
pub(crate) struct AppChild {
    pub(crate) child: Child,
}

impl Drop for AppChild {
    fn drop(&mut self) {
        // Never orphan: on drop (including panic paths) kill the child if it is
        // still running and reap it.
        if let Ok(None) = self.child.try_wait() {
            let _ = self.child.kill();
            let _ = self.child.wait();
        }
    }
}

/// The run-identity hashes the runner computes from the exact bytes it spawns
/// and sends; the app echoes them back in the report's identity. Each field is
/// a sha2-256 hex string: `app` of the binary, `scenario` of the scenario
/// file, `config` of the config string.
pub(crate) struct RunIdentity<'a> {
    pub(crate) app: &'a str,
    pub(crate) scenario: &'a str,
    pub(crate) config: &'a str,
}

/// The app's asset base path: the `gone_app` crate directory, whose `assets/`
/// subtree holds the game's assets (bevy joins its configured `assets` folder
/// onto this base). Taken from `gone_app`'s compile-time manifest path, so it
/// is absolute and independent of this runner's invocation cwd or inherited
/// environment, and validated here so a layout mismatch fails the launch by
/// name instead of surfacing later as the child's required-asset load failure.
pub(crate) fn app_asset_root() -> Result<PathBuf, RunnerError> {
    let base = PathBuf::from(gone_app::APP_CRATE_DIR);
    if !base.is_absolute() {
        bail!("gone_app crate dir is not absolute: {}", base.display());
    }
    let assets = base.join("assets");
    if !assets.is_dir() {
        bail!(
            "gone_app assets dir not found: {} (BEVY_ASSET_ROOT must name the gone_app \
             crate dir whose assets/ subtree holds the game's assets)",
            assets.display()
        );
    }
    Ok(base)
}

/// Spawn the app with harness env and the run-identity hashes. Under
/// `render_check` the child also gets `GONE_RENDER_CHECK=1`, selecting the
/// canary lane (focused window: it must be ordered in for its surface to
/// present, plus the one onscreen capture). The child's `BEVY_ASSET_ROOT` is
/// always set explicitly (see [`app_asset_root`]), so its asset resolution
/// never depends on the environment this runner inherited.
pub(crate) fn spawn_app(
    root: &Path,
    scenario_path: &Path,
    out_dir: &Path,
    identity: &RunIdentity<'_>,
    render_check: bool,
) -> Result<AppChild, RunnerError> {
    let app = root.join("target").join("debug").join("gone_app");
    if !app.is_file() {
        bail!(
            "app binary not found: {} (build with cargo build first)",
            app.display()
        );
    }
    let asset_root = app_asset_root()?;
    let mut command = Command::new(&app);
    command
        .env(ENV_HARNESS, "1")
        .env(ENV_ASSET_ROOT, asset_root)
        .env(ENV_SCENARIO, scenario_path)
        .env(ENV_OUT_DIR, out_dir)
        .env(ENV_APP_HASH, identity.app)
        .env(ENV_SCENARIO_HASH, identity.scenario)
        .env("GONE_CONFIG_HASH", identity.config);
    if render_check {
        command.env(ENV_RENDER_CHECK, "1");
    }
    let child = command
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit())
        .current_dir(root)
        .spawn()
        .map_err(|e| RunnerError(format!("failed to spawn {}: {e}", app.display())))?;
    Ok(AppChild { child })
}

/// Wait for the app child to finish, killing it after `timeout` seconds.
pub(crate) fn wait_for_app(
    child: &mut AppChild,
    timeout: Duration,
    scenario: &str,
) -> Result<std::process::ExitStatus, RunnerError> {
    let start = Instant::now();
    loop {
        if start.elapsed() > timeout {
            child
                .child
                .kill()
                .map_err(|e| RunnerError(format!("kill failed: {e}")))?;
            let _ = child.child.wait();
            bail!(
                "scenario `{scenario}` timed out after {}s",
                timeout.as_secs()
            );
        }
        match child.child.try_wait() {
            Ok(Some(status)) => return Ok(status),
            Ok(None) => std::thread::sleep(Duration::from_millis(10)),
            Err(e) => bail!("waitpid error: {e}"),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::app_asset_root;

    /// The spawn path's asset root: absolute, and pointing at the `gone_app`
    /// assets subtree that holds the required metering mask, whatever this
    /// process's invocation cwd or inherited environment. This is the value
    /// the child's `BEVY_ASSET_ROOT` is built from; a wrong root made bevy
    /// look under the runner crate's (empty) assets dir and failed the
    /// gameplay lane's required-asset barrier.
    #[test]
    fn computed_asset_root_holds_the_required_asset() {
        let base = app_asset_root().expect("gone_app assets dir exists in the repo layout");
        assert!(
            base.is_absolute(),
            "BEVY_ASSET_ROOT must be absolute: {}",
            base.display()
        );
        let required = base.join("assets").join("post/metering_mask.png");
        assert!(
            required.is_file(),
            "the required asset must exist under the computed root: {}",
            required.display()
        );
    }
}
