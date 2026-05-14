"""cortex.context_enricher.doc_intent - DocType-aware intent detection.

Complements ``cortex.retrieval.intent.QueryIntent`` (EPISODIC/SEMANTIC/MIXED,
which controls RRF weights) with a finer-grained ``DocIntent`` used to boost
specific DocTypes during retrieval.

Example:
    A query like "how do I rollback?" maps to ``DocIntent.RUNBOOK`` which
    boosts ``RUNBOOK`` documents 2.5x via ``RouteSpec.retrieval_boost_per_intent``.

The two layers are orthogonal: ``QueryIntent`` decides episodic-vs-semantic
weights for RRF fusion; ``DocIntent`` decides per-doc_type score multipliers
within the semantic vault.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class DocIntent(str, Enum):
    """Intent label used to boost specific DocTypes during retrieval."""

    GENERIC = "generic"          # no specific signal
    DECISION = "decision"        # why-did, rationale -> ADR boost
    ARCHITECTURE = "architecture"  # design, components -> ARCHITECTURE boost
    RUNBOOK = "runbook"          # procedure, deploy, rollback -> RUNBOOK boost
    INCIDENT = "incident"        # outage, error -> INCIDENT boost
    POSTMORTEM = "postmortem"    # root cause -> POSTMORTEM boost
    HISTORY = "history"          # what did we, when did -> SESSION boost
    RECENT = "recent"            # latest, today -> SESSION recency boost
    SPEC = "spec"                # requirements, acceptance -> SPEC boost


@dataclass(frozen=True)
class DocIntentResult:
    intent: DocIntent
    matched_signals: list[str]
    confidence: float


# ---------------------------------------------------------------------------
# Pattern lexicons (ordered by priority; first match wins).
# ---------------------------------------------------------------------------

_DOC_PATTERNS: list[tuple[DocIntent, list[tuple[re.Pattern, str]]]] = [
    (
        DocIntent.POSTMORTEM,
        [
            (re.compile(r"\broot\s+cause\b", re.I), "root_cause"),
            (re.compile(r"\bpostmortem\b", re.I), "postmortem_kw"),
            (re.compile(r"\bpost[- ]?mortem\b", re.I), "postmortem_kw"),
            (re.compile(r"\bwhat\s+went\s+wrong\b", re.I), "what_went_wrong"),
        ],
    ),
    (
        DocIntent.INCIDENT,
        [
            (re.compile(r"\bincident\b", re.I), "incident_kw"),
            (re.compile(r"\boutage\b", re.I), "outage_kw"),
            (re.compile(r"\bcaida\b", re.I), "caida_kw"),
            (re.compile(r"\bbroke\b", re.I), "broke_kw"),
            (re.compile(r"\bfalla\b", re.I), "falla_kw"),
        ],
    ),
    (
        DocIntent.RUNBOOK,
        [
            (re.compile(r"\b(how\s+do\s+i|how\s+to)\s+(deploy|rollback|restart|start|stop)\b", re.I), "how_to_op"),
            (re.compile(r"\brunbook\b", re.I), "runbook_kw"),
            (re.compile(r"\bplaybook\b", re.I), "playbook_kw"),
            (re.compile(r"\bprocedure\b", re.I), "procedure_kw"),
            (re.compile(r"\b(deploy|rollback|provision)\b", re.I), "ops_verb"),
            (re.compile(r"\bcomo\s+(arranco|despliego|reinici)", re.I), "como_op_es"),
        ],
    ),
    (
        DocIntent.DECISION,
        [
            (re.compile(r"\bwhy\s+did\s+we\b", re.I), "why_did"),
            (re.compile(r"\brationale\b", re.I), "rationale_kw"),
            (re.compile(r"\bpor\s+qu[eé]\s+(decidim|elegim|optam)", re.I), "por_que_es"),
            (re.compile(r"\bdecision\b", re.I), "decision_kw"),
            (re.compile(r"\badr\b", re.I), "adr_kw"),
        ],
    ),
    (
        DocIntent.ARCHITECTURE,
        [
            (re.compile(r"\barchitecture\b", re.I), "arch_kw"),
            (re.compile(r"\barquitectura\b", re.I), "arch_es"),
            (re.compile(r"\bdesign\b", re.I), "design_kw"),
            (re.compile(r"\bdiagram\b", re.I), "diagram_kw"),
            (re.compile(r"\bcomponents?\b", re.I), "components_kw"),
        ],
    ),
    (
        DocIntent.SPEC,
        [
            (re.compile(r"\bspec(ification)?\b", re.I), "spec_kw"),
            (re.compile(r"\brequirements?\b", re.I), "req_kw"),
            (re.compile(r"\bacceptance\s+criteria\b", re.I), "ac_kw"),
            (re.compile(r"\brequisitos\b", re.I), "req_es"),
        ],
    ),
    (
        DocIntent.RECENT,
        [
            (re.compile(r"\b(latest|recent|today|yesterday)\b", re.I), "recent_kw"),
            (re.compile(r"\b(ultim[oa]|reciente|hoy)\b", re.I), "recent_es"),
            (re.compile(r"\bthis\s+(week|month)\b", re.I), "this_window"),
            (re.compile(r"\besta\s+semana\b", re.I), "this_window_es"),
        ],
    ),
    (
        DocIntent.HISTORY,
        [
            (re.compile(r"\bwhat\s+did\s+we\b", re.I), "what_did"),
            (re.compile(r"\bwhen\s+did\s+we\b", re.I), "when_did"),
            (re.compile(r"\bque\s+hicimos\b", re.I), "que_hicimos"),
            (re.compile(r"\blast\s+time\b", re.I), "last_time"),
            (re.compile(r"\bhistor", re.I), "history_kw"),
        ],
    ),
]


class DocIntentDetector:
    """Classifies a query into a ``DocIntent`` via lexicon matching.

    The first intent whose patterns match wins (priority order encoded in
    ``_DOC_PATTERNS``). If nothing matches, returns ``DocIntent.GENERIC``.

    The detector is deterministic and dependency-free (regex only).
    """

    def detect(self, query: str) -> DocIntentResult:
        query = (query or "").strip()
        if not query:
            return DocIntentResult(intent=DocIntent.GENERIC, matched_signals=[], confidence=0.0)

        for intent, patterns in _DOC_PATTERNS:
            signals = [label for pat, label in patterns if pat.search(query)]
            if signals:
                confidence = min(1.0, 0.5 + 0.25 * len(signals))
                return DocIntentResult(
                    intent=intent,
                    matched_signals=signals,
                    confidence=round(confidence, 3),
                )
        return DocIntentResult(
            intent=DocIntent.GENERIC, matched_signals=[], confidence=0.2,
        )


__all__ = ["DocIntent", "DocIntentDetector", "DocIntentResult"]
