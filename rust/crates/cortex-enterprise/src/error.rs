use std::fmt;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum EnterpriseError {
    Validation(String),
    Permission(String),
    NotFound(String),
    BackendUnavailable(&'static str),
    Backend(String),
    Io(String),
}

impl fmt::Display for EnterpriseError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Validation(message)
            | Self::Permission(message)
            | Self::NotFound(message)
            | Self::Backend(message)
            | Self::Io(message) => f.write_str(message),
            Self::BackendUnavailable(message) => f.write_str(message),
        }
    }
}

impl std::error::Error for EnterpriseError {}

impl From<std::io::Error> for EnterpriseError {
    fn from(error: std::io::Error) -> Self {
        Self::Io(error.to_string())
    }
}

impl From<serde_yaml::Error> for EnterpriseError {
    fn from(error: serde_yaml::Error) -> Self {
        Self::Validation(error.to_string())
    }
}
