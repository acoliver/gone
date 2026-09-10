//! Workspace task runner for the game `gone`.
//!
//! Real commands arrive with issue #4; until then the binary answers `--help`
//! and rejects everything else loudly instead of silently doing nothing.

use std::ffi::OsString;
use std::process::ExitCode;

/// Usage text shown by `--help` and on every rejected invocation.
const USAGE: &str = "\
Usage: cargo xtask <COMMAND>

Workspace task runner for `gone`.

Commands:
  (none yet; commands arrive with issue #4)

Options:
  -h, --help  Print this message
";

fn main() -> ExitCode {
    match std::env::args_os().nth(1) {
        None => reject(None),
        Some(command) if command == "-h" || command == "--help" => {
            print!("{USAGE}");
            ExitCode::SUCCESS
        }
        Some(command) => reject(Some(command)),
    }
}

/// Reports why the invocation was refused and exits with the standard usage
/// error code, `2`.
fn reject(command: Option<OsString>) -> ExitCode {
    match command {
        None => eprintln!("error: missing command"),
        Some(command) => {
            let name = command.to_string_lossy();
            eprintln!("error: unknown command `{name}`");
        }
    }
    usage();
    ExitCode::from(2)
}

/// Prints usage to stderr so stdout stays clean for future command output.
fn usage() {
    eprintln!("{USAGE}");
}
