//! The runner's error type: a formatted message naming the artifact or check
//! that failed.

use std::fmt;

#[derive(Debug)]
pub(crate) struct RunnerError(pub(crate) String);

impl fmt::Display for RunnerError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        self.0.fmt(f)
    }
}

impl std::error::Error for RunnerError {}

macro_rules! bail {
    ($($arg:tt)*) => {
        return Err(RunnerError(format!($($arg)*)))
    };
}
pub(crate) use bail;
