//! DocType enum y estados válidos — réplica de
//! `cortex/documentation/doc_type.py`.

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum DocType {
    Session,
    Handoff,
    Spec,
    Adr,
    Decision,
    Incident,
    Postmortem,
    Runbook,
    Architecture,
    Changelog,
    Hu,
    Glossary,
    Design,
}

impl DocType {
    pub fn as_str(self) -> &'static str {
        match self {
            DocType::Session => "session",
            DocType::Handoff => "handoff",
            DocType::Spec => "spec",
            DocType::Adr => "adr",
            DocType::Decision => "decision",
            DocType::Incident => "incident",
            DocType::Postmortem => "postmortem",
            DocType::Runbook => "runbook",
            DocType::Architecture => "architecture",
            DocType::Changelog => "changelog",
            DocType::Hu => "hu",
            DocType::Glossary => "glossary",
            DocType::Design => "design",
        }
    }

    pub fn parse(s: &str) -> Option<DocType> {
        Some(match s {
            "session" => DocType::Session,
            "handoff" => DocType::Handoff,
            "spec" => DocType::Spec,
            "adr" => DocType::Adr,
            "decision" => DocType::Decision,
            "incident" => DocType::Incident,
            "postmortem" => DocType::Postmortem,
            "runbook" => DocType::Runbook,
            "architecture" => DocType::Architecture,
            "changelog" => DocType::Changelog,
            "hu" => DocType::Hu,
            "glossary" => DocType::Glossary,
            "design" => DocType::Design,
            _ => return None,
        })
    }

    /// Estados válidos (VALID_STATUSES). Devueltos ORDENADOS para que la
    /// coerción (`_default_status`) tome el primero idéntico a Python.
    pub fn valid_statuses(self) -> &'static [&'static str] {
        match self {
            DocType::Session => &["auto-draft", "completed", "draft", "fallback", "handoff"],
            DocType::Handoff => &["consumed", "open", "stale"],
            DocType::Spec => &["abandoned", "approved", "done", "draft", "implementing"],
            DocType::Adr => &["accepted", "proposed", "rejected", "superseded"],
            DocType::Decision => &["active", "reverted"],
            DocType::Incident => &["closed", "mitigated", "open"],
            DocType::Postmortem => &["actions-tracked", "complete", "draft", "published"],
            DocType::Runbook => &["deprecated", "draft", "verified"],
            DocType::Architecture => &["current", "deprecated", "draft"],
            DocType::Changelog => &["released", "unreleased"],
            DocType::Hu => &["backlog", "cancelled", "done", "in-progress"],
            DocType::Glossary => &["canonical", "deprecated", "draft"],
            DocType::Design => &["approved", "draft", "superseded"],
        }
    }
}
