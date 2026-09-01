//! Puertos de `cortex.autopilot.errors` y `cortex.autopilot.models`.

/// `ConfigError`.
#[derive(Debug, Clone)]
pub enum AutopilotError {
    Config(String),
    NoActiveSession,
}

impl std::fmt::Display for AutopilotError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Config(m) => write!(f, "ConfigError: {m}"),
            Self::NoActiveSession => write!(f, "NoActiveSessionError"),
        }
    }
}
impl std::error::Error for AutopilotError {}
