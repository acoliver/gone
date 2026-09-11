//! Run-dir management and path resolution: the workspace root, the run-id
//! scheme, the read/write helpers that name the failing artifact, and
//! scenario-path/scenario-file loading.

use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

use gone_harness::scenario::{Scenario, parse_scenario};

use crate::error::{RunnerError, bail};

pub(crate) fn repo_root() -> Result<PathBuf, RunnerError> {
    let dir = std::env::var_os("CARGO_MANIFEST_DIR")
        .ok_or_else(|| RunnerError("CARGO_MANIFEST_DIR is not set".into()))?;
    let mut current = Path::new(&dir).to_path_buf();
    loop {
        let manifest = current.join("Cargo.toml");
        if manifest.is_file()
            && std::fs::read_to_string(&manifest).is_ok_and(|text| text.contains("[workspace]"))
        {
            return Ok(current);
        }
        match current.parent() {
            Some(p) => current = p.to_path_buf(),
            None => bail!("no workspace root above {}", dir.to_string_lossy()),
        }
    }
}

/// The run id: `<unix-nanos>-s<seed>` so concurrent sessions cannot clobber
/// each other; render-check (canary) runs carry an `rc` prefix so the windowed
/// check runs are identifiable in `tmp/harness`.
pub(crate) fn run_id(seed: u64, render_check: bool) -> String {
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |d| d.as_nanos());
    let prefix = if render_check { "rc" } else { "" };
    format!("{prefix}{nanos}-s{seed}")
}

pub(crate) fn read_or(context: &str, path: &Path) -> Result<Vec<u8>, RunnerError> {
    std::fs::read(path)
        .map_err(|e| RunnerError(format!("failed to read {context} {}: {e}", path.display())))
}

pub(crate) fn write_or(context: &str, path: &Path, bytes: &[u8]) -> Result<(), RunnerError> {
    std::fs::write(path, bytes)
        .map_err(|e| RunnerError(format!("failed to write {context} {}: {e}", path.display())))
}

pub(crate) fn root_scenario(arg: &str) -> Result<PathBuf, RunnerError> {
    if arg == "smoke" {
        let root = repo_root()?;
        return Ok(root.join("tmp").join("smoke-scenario.json"));
    }
    let p = PathBuf::from(arg);
    if p.is_absolute() {
        Ok(p)
    } else {
        Ok(repo_root()?.join(p))
    }
}

pub(crate) fn load_scenario(path: &Path) -> Result<Scenario, RunnerError> {
    let bytes = read_or("scenario file", path)?;
    let text = String::from_utf8_lossy(&bytes);
    parse_scenario(&text).map_err(RunnerError)
}
