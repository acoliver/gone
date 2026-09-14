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

/// Write `bytes` to `path`, creating the file's parent directory first: the
/// writer owns its output tree, so the scenario writes under the gitignored
/// workspace `tmp/` work in a fresh checkout without any consumer-side
/// mkdir. Both the parent creation and the write report contextual I/O
/// errors; neither failure is swallowed.
pub(crate) fn write_or(context: &str, path: &Path, bytes: &[u8]) -> Result<(), RunnerError> {
    if let Some(parent) = path
        .parent()
        .filter(|parent| !parent.as_os_str().is_empty())
    {
        std::fs::create_dir_all(parent).map_err(|e| {
            RunnerError(format!(
                "failed to create {context} parent {}: {e}",
                parent.display()
            ))
        })?;
    }
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

#[cfg(test)]
mod tests {
    use std::path::PathBuf;
    use std::time::{SystemTime, UNIX_EPOCH};

    use gone_harness::scenario::{parse_scenario, scenario_to_json};

    use super::write_or;

    /// A scratch root unique to this test process (pid + nanos), existing
    /// but deliberately missing the `tmp/` subtree a fresh workspace has.
    fn fresh_root(tag: &str) -> PathBuf {
        let nanos = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map_or(0, |d| d.as_nanos());
        let dir =
            std::env::temp_dir().join(format!("gone-paths-{tag}-{}-{nanos}", std::process::id()));
        std::fs::create_dir_all(&dir).expect("create scratch root");
        dir
    }

    /// Issue #28: the runner's built-in scenario writes land under
    /// `<root>/tmp/`, which does not exist in a fresh checkout (the dir is
    /// gitignored and never committed). The writer owns its output parent,
    /// so the first write into a root without `tmp/` must create it and
    /// still produce the correct scenario JSON, with no consumer-side mkdir.
    #[test]
    fn built_in_scenario_write_into_a_fresh_root_creates_tmp() {
        let root = fresh_root("fresh-tmp");
        let scenario = gone_harness::gameplay::gameplay_smoke_scenario();
        let path = root.join("tmp").join("gameplay-smoke-scenario.json");
        assert!(
            !root.join("tmp").exists(),
            "the test root must start without a tmp/ dir"
        );

        let json = scenario_to_json(&scenario).expect("scenario json");
        write_or("built-in scenario", &path, json.as_bytes()).expect("write into the fresh root");

        let text = std::fs::read_to_string(&path).expect("read back the written scenario");
        let parsed = parse_scenario(&text).expect("the written scenario parses");
        assert_eq!(parsed.name, scenario.name);
        assert_eq!(parsed.seed, scenario.seed);
        assert_eq!(parsed.ticks_per_second, scenario.ticks_per_second);
        assert_eq!(parsed.warmup_frames, scenario.warmup_frames);
        assert_eq!(parsed.sample_frames, scenario.sample_frames);
        assert_eq!(parsed.beats.len(), scenario.beats.len());
        assert_eq!(parsed.actions.len(), scenario.actions.len());
        std::fs::remove_dir_all(&root).expect("clean up the scratch root");
    }

    /// A parent that exists but is a regular file is a reported failure:
    /// the error names the context, the blocking path, and the OS error,
    /// instead of swallowing the failure or panicking without context.
    #[test]
    fn write_fails_with_context_when_the_parent_is_a_file() {
        let root = fresh_root("parent-is-file");
        let blocker = root.join("tmp");
        std::fs::write(&blocker, b"not a directory").expect("create the blocking file");
        let path = blocker.join("gameplay-smoke-scenario.json");

        let err =
            write_or("built-in scenario", &path, b"{}").expect_err("a file-shaped parent fails");

        let message = err.to_string();
        assert!(
            message.contains("failed to create built-in scenario parent"),
            "the error names the context and the parent: {message}"
        );
        assert!(
            message.contains(&blocker.display().to_string()),
            "the error names the blocking path: {message}"
        );
        assert!(
            message.contains("os error"),
            "the OS error travels with the message: {message}"
        );
        std::fs::remove_file(&blocker).expect("clean up the blocking file");
        std::fs::remove_dir(&root).expect("clean up the scratch root");
    }
}
