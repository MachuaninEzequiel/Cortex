//! Errores del puerto. El adapter traduce cualquiera de estos a fail-open.

use std::fmt;

/// Fallos de `evaluate`. Nunca deben vaciar un search.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum JudgementError {
    Skipped,
    NoKey,
    Timeout,
    Http(u16),
    Transport(String),
    Validation(String),
}

impl fmt::Display for JudgementError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            JudgementError::Skipped => write!(f, "judgement skipped"),
            JudgementError::NoKey => write!(f, "TYPESAFE_API_KEY missing"),
            JudgementError::Timeout => write!(f, "typesafe timeout"),
            JudgementError::Http(code) => write!(f, "typesafe http {code}"),
            JudgementError::Transport(m) => write!(f, "typesafe transport: {m}"),
            JudgementError::Validation(m) => write!(f, "judgement validation: {m}"),
        }
    }
}

impl std::error::Error for JudgementError {}
