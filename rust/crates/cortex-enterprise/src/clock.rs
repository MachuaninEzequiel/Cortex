use chrono::{DateTime, Timelike, Utc};

use crate::error::EnterpriseError;

pub trait Clock: Send + Sync {
    fn now(&self) -> DateTime<Utc>;
}

#[derive(Debug, Default, Clone, Copy)]
pub struct SystemClock;

impl Clock for SystemClock {
    fn now(&self) -> DateTime<Utc> {
        Utc::now()
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FixedClock(DateTime<Utc>);

impl FixedClock {
    pub fn new(value: DateTime<Utc>) -> Self {
        Self(value)
    }

    pub fn parse(value: &str) -> Result<Self, EnterpriseError> {
        DateTime::parse_from_rfc3339(value)
            .map(|parsed| Self(parsed.with_timezone(&Utc)))
            .map_err(|error| EnterpriseError::Validation(error.to_string()))
    }
}

impl Clock for FixedClock {
    fn now(&self) -> DateTime<Utc> {
        self.0
    }
}

/// `datetime.now(UTC).isoformat()` de Python (sin timespec): microsegundos
/// sólo cuando no son cero, offset `+00:00`.
pub fn isoformat_full(value: DateTime<Utc>) -> String {
    if value.nanosecond().is_multiple_of(1_000_000) {
        value.to_rfc3339_opts(chrono::SecondsFormat::Secs, false)
    } else {
        value.to_rfc3339_opts(chrono::SecondsFormat::Micros, false)
    }
}

/// `datetime.now(UTC).isoformat(timespec="seconds")` de Python:
/// `2026-08-25T12:00:00+00:00`.
pub fn isoformat_seconds(value: DateTime<Utc>) -> String {
    value.to_rfc3339_opts(chrono::SecondsFormat::Secs, false)
}

/// Default serde para timestamps ausentes en líneas históricas del JSONL
/// (Pydantic aplicaría `now()` al validar; se replica con el reloj del
/// sistema).
pub fn default_now_string() -> String {
    isoformat_seconds(Utc::now())
}
