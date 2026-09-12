//! The run-identity hashing: real SHA-256 over the exact bytes the runner
//! spawns and sends.

use std::fmt::Write as _;

use sha2::{Digest as _, Sha256};

/// Real SHA-256 of `bytes`, lowercase hex, the run-identity hash used
/// everywhere the protocol names a build, scenario, or config.
#[must_use]
pub(crate) fn sha256_hex(bytes: &[u8]) -> String {
    let digest = Sha256::digest(bytes);
    hex_of(&digest)
}

/// Lowercase hex of a byte slice.
#[must_use]
pub(crate) fn hex_of(bytes: &[u8]) -> String {
    let mut out = String::with_capacity(bytes.len() * 2);
    for b in bytes {
        let _ = write!(out, "{b:02x}");
    }
    out
}
