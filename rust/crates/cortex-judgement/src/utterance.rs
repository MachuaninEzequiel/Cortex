//! Portero (spec 09): clasifica el acto. Fail-open ⇒ None.

use serde_json::json;

use crate::catalog::Catalog;
use crate::purpose::Purpose;
use crate::request::JudgementRequest;
use crate::JudgementClient;

pub const KEEP_SESSION: f64 = 0.50;
pub const KEEP_REMEMBER: f64 = 0.25;
pub const KEEP_FINISH: f64 = 0.50;
pub const WORK_CONFIDENCE_FLOOR: f64 = 0.50;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum WorkKind {
    Question,
    Implement,
    Chore,
    Done,
}

impl WorkKind {
    pub fn as_str(self) -> &'static str {
        match self {
            WorkKind::Question => "question",
            WorkKind::Implement => "implement",
            WorkKind::Chore => "chore",
            WorkKind::Done => "done",
        }
    }

    fn parse(s: &str) -> Self {
        match s {
            "implement" => WorkKind::Implement,
            "chore" => WorkKind::Chore,
            "done" => WorkKind::Done,
            _ => WorkKind::Question,
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct UtteranceJudgement {
    pub work: WorkKind,
    pub work_confidence: f64,
    pub needs_session: f64,
    pub worth_remembering: f64,
    pub needs_finish: f64,
}

impl UtteranceJudgement {
    pub fn should_open_session(&self, has_active_session: bool) -> bool {
        self.work == WorkKind::Implement
            && self.needs_session >= KEEP_SESSION
            && !has_active_session
    }

    pub fn should_remember(&self) -> bool {
        self.work != WorkKind::Question && self.worth_remembering >= KEEP_REMEMBER
    }

    pub fn should_finish(&self) -> bool {
        self.work == WorkKind::Done && self.needs_finish >= KEEP_FINISH
    }
}

/// Fail-open: off/429 ⇒ permitir remember (Direct). Question / noul bajo ⇒ no.
pub fn allow_remember(
    client: &dyn JudgementClient,
    catalog: &Catalog,
    text: &str,
    files: &[String],
) -> bool {
    if !client.enabled(Purpose::Utterance) {
        return true;
    }
    match classify_utterance(client, catalog, text, false, files) {
        None => true,
        Some(j) => j.should_remember(),
    }
}

/// `None` = purpose off / 429 / error → Direct (no inventar sesión).
pub fn classify_utterance(
    client: &dyn JudgementClient,
    catalog: &Catalog,
    text: &str,
    has_active_session: bool,
    files: &[String],
) -> Option<UtteranceJudgement> {
    if !client.enabled(Purpose::Utterance) {
        return None;
    }
    let req = JudgementRequest::system_one(
        json!({
            "text": text,
            "has_active_session": has_active_session,
            "files": files,
        }),
        &catalog.model,
        catalog.utterance_questions(),
    );
    let resp = client.evaluate(&req).ok()?;
    let work_ans = resp.answers.get("work");
    let choice = work_ans
        .and_then(|v| v.get("choice"))
        .and_then(|v| v.as_str())
        .unwrap_or("question");
    let conf = work_ans
        .and_then(|v| v.get("confidence"))
        .and_then(|v| v.as_f64())
        .unwrap_or(0.0);
    let work = if conf < WORK_CONFIDENCE_FLOOR {
        WorkKind::Question
    } else {
        WorkKind::parse(choice)
    };
    Some(UtteranceJudgement {
        work,
        work_confidence: conf,
        needs_session: noul_of(&resp.answers, "needs_session"),
        worth_remembering: noul_of(&resp.answers, "worth_remembering"),
        needs_finish: noul_of(&resp.answers, "needs_finish"),
    })
}

fn noul_of(answers: &serde_json::Map<String, serde_json::Value>, key: &str) -> f64 {
    answers
        .get(key)
        .and_then(|v| v.get("noul"))
        .and_then(|v| v.as_f64())
        .unwrap_or(0.0)
}
