//! Workspace task runner for the game `gone` (issue #4).
//!
//! Invoked via the `cargo xtask` alias defined in `.cargo/config.toml`.
//! `main` stays a thin entry point over the library modules; the policy and
//! command logic lives beside its tests in `cli`, `clippy_policy`,
//! `rust_lexer`, `source_size`, `architecture`, `metadata_graph`, and
//! `protocol_surface`.

use std::process::ExitCode;

mod architecture;
mod cli;
mod clippy_policy;
mod metadata_graph;
mod process;
mod protocol_surface;
mod rust_lexer;
mod source_size;
#[cfg(test)]
mod test_support;

fn main() -> ExitCode {
    // Non-UTF-8 argv entries are lossily stringified rather than panicking;
    // every xtask command name and flag is ASCII, so nothing real is lost.
    let argv: Vec<String> = std::env::args_os()
        .skip(1)
        .map(|arg| arg.to_string_lossy().into_owned())
        .collect();
    cli::run(&argv)
}
