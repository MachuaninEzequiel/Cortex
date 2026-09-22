//! Client apagado. No reimplementa lexicon: el caller ni lo invoca.

use crate::error::JudgementError;
use crate::purpose::Purpose;
use crate::request::{JudgementRequest, JudgementResponse};
use crate::JudgementClient;

#[derive(Debug, Default, Clone, Copy)]
pub struct NullClient;

impl JudgementClient for NullClient {
    fn enabled(&self, _purpose: Purpose) -> bool {
        false
    }

    fn evaluate(&self, _request: &JudgementRequest) -> Result<JudgementResponse, JudgementError> {
        Err(JudgementError::Skipped)
    }
}
