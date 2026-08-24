#!/usr/bin/env python3
"""Oráculo P8b: notas canónicas byte-a-byte (writers Python → goldens).

Genera un caso por DocType (+ variantes enterprise / auto-numerado /
defaults mutantes) con reloj CONGELADO y captura el archivo exacto que
escriben los writers canónicos de cortex.documentation.writers.

Salida:
    bench/parity/golden_setup/writers/inputs.json   # pedidos (doc_type+kwargs)
    bench/parity/golden_setup/writers/<case>/**     # archivos resultantes

El test Rust (cortex-setup/tests/writers_parity.rs) reconstruye cada nota
con el mismo input/reloj y compara byte-a-byte.
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

OUT = REPO / "bench/parity/golden_setup/writers"

# Reloj congelado compartido con el lado Rust.
NOW = datetime(2026, 8, 24, 12, 34, 56, 789012, tzinfo=UTC)
NOW_Z = "2026-08-24T12:34:56.789012Z"


def _patch_now() -> None:
    """Congela `_now_utc` del módulo writers y el reloj de audit."""
    import cortex.documentation.writers as W

    W._now_utc = lambda: NOW
    # append_audit_event usa datetime.now(UTC) del módulo audit.
    import cortex.documentation.audit as A

    class _FrozenDatetime:
        @staticmethod
        def now(_tz=None):
            return NOW

    A.datetime = _FrozenDatetime


def main() -> int:
    from cortex.session.models import VerificationHook

    hooks = [
        {
            "name": "build",
            "command": "cargo build --release",
            "required": True,
            "success_criteria": "exit code 0",
            "timeout_seconds": 600,
        },
        {
            "name": "lint",
            "command": "ruff check . || true",
            "required": False,
            "success_criteria": "sin errores bloqueantes",
            "timeout_seconds": 120,
        },
    ]
    telemetry = {
        "enricher_run_id": "run-2026-08-24-01",
        "context_items_offered": 12,
        "context_items_used": 5,
        "context_hit_rate": 0.416667,
        "context_by_type": {"spec": 3, "adr": 2},
        "context_by_strategy": {"bm25": 4, "vector": 1},
        "context_by_scope": {"local": 5},
        "enriched_score_p50": 0.62,
        "enriched_score_p95": 0.88,
        "enricher_latency_ms": 41,
        "filters_applied": None,
    }

    CASES = [
        ("adr", {
            "doc_type": "adr",
            "scope": "local",
            "fields": {
                "title": "Usar tokens vs sesiones para auth",
                "tags": ["auth", "latencia"],
                "status": "accepted",
                "links": ["spec-2026-08-01"],
                "context": "El servicio necesita recordar al usuario entre despliegues: "
                           "la sesión en memoria no sobrevive restarts y la latencia p99 "
                           "de regenerar sesión es inaceptable para el SLA acordado.",
                "decision": "Emitimos tokens opacos firmados con rotación cada 24h.",
                "alternatives_considered": [
                    "sesiones httpOnly con store compartido",
                    "JWT stateless con revocación vía blacklist",
                ],
                "consequences": "Requiere cache Redis; simplifica el escalamiento horizontal.",
                "adr_number": 7,
                "supersedes": [],
                "superseded_by": None,
                "acceptance_criteria_met": True,
            },
        }),
        ("adr_auto_number", {
            # Sin adr_number: el writer escanea decisions/ y asigna el próximo.
            "doc_type": "adr",
            "scope": "local",
            "pre_files": {"decisions/ADR-001-previo.md": "---\nprevia\n---\n"},
            "fields": {
                "title": "Migrar colas a Redis Streams",
                "status": "proposed",
                "context": "La cola actual pierde mensajes.",
                "decision": "Redis Streams con consumer groups.",
                "consequences": "Requiere redis >= 6.2.",
            },
        }),
        ("adr_enterprise", {
            "doc_type": "adr",
            "scope": "enterprise",
            "project_id": "appfutbol",
            "actor": "lead@empresa.co",
            "fields": {
                "title": "Política de retención de datos personales",
                "tags": ["governance"],
                "status": "accepted",
                "owner": "dpo@empresa.co",
                "team": "platform",
                "classification": "confidential",
                "retention_days": 365,
                "context": "Cumplimiento normativo.",
                "decision": "Borrado automático a los 365 días.",
                "consequences": "Jobs nocturnos de purga.",
                "adr_number": 12,
            },
        }),
        ("session_full", {
            "doc_type": "session",
            "scope": "local",
            "fields": {
                "title": "Refactor autenticación + tests verdes",
                "tags": ["backend"],
                "status": "auto-draft",
                "session_id": "2026-08-24_refactor-auth",
                "spec_summary": "Mejorar la autenticación del servicio sin cortar consumidores.",
                "changes_made": [
                    "src/auth.py refactorizado a tokens",
                    "tests/auth_test.py cubre rotación",
                    "Café & Sueño: decisión ✓ tomada",
                ],
                "files_touched": ["src/auth.py", "tests/auth_test.py", ".env.example"],
                "key_decisions": ["tokens opacos sobre JWT"],
                "next_steps": ["rotación en worker", "documentar endpoint /logout"],
                "pr": "#142",
                "branch": "feature/auth-tokens",
                "commit": "abc1234",
                "verified_state": ["pytest verde local"],
                "unverified_claims": ["rendimiento igual en staging"],
                "blockers": [],
                "suggested_skills": ["cortex-sync"],
                "cortex_telemetry": telemetry,
                "task_type": "",
                "tasks": [
                    {"id": "1", "description": "refactor auth", "status": "done"},
                    {"id": "2", "description": "tests", "status": "done"},
                ],
                "tasks_total": 2,
                "tasks_done": 2,
                "tasks_skipped": 0,
                "gitless": False,
            },
        }),
        ("session_gitless_security", {
            "doc_type": "session",
            "scope": "local",
            "fields": {
                "title": "Auditoría rápida de secretos",
                "status": "",
                "session_id": "2026-08-24_secret-scan",
                "task_type": "security",
                "verified_state": ["gitleaks sin hallazgos"],
                "unverified_claims": ["no revisé variables CI"],
                "gitless": True,
                "spec_summary": "",
                "changes_made": [],
                "files_touched": [],
                "key_decisions": [],
                "next_steps": [],
            },
        }),
        ("handoff_open", {
            "doc_type": "handoff",
            "scope": "local",
            "fields": {
                "title": "Handoff migración colas",
                "status": "open",
                "parent_session_id": "2026-08-24_refactor-auth",
                "next_session_needs": ["revisar consumer groups", "medir lag"],
                "blockers": ["acceso staging pendiente"],
                "verified_state": ["build ok"],
                "unverified_claims": [],
                "suggested_skills": [],
                "context_required": "Contexto del ADR-007 de tokens.",
            },
        }),
        ("spec_hooks", {
            "doc_type": "spec",
            "scope": "local",
            "fields": {
                "title": "Spec: endpoint /sessions",
                "tags": ["api"],
                "status": "approved",
                "goal": "Exponer /sessions con paginación.",
                "requirements": ["GET lista sesiones", "filtro por fecha"],
                "files_in_scope": ["src/api/sessions.py"],
                "constraints": ["p95 < 200ms"],
                "acceptance_criteria": ["curl devuelve 200", "tests integración verdes"],
                "verification_hooks": hooks,
            },
        }),
        ("design_default_title", {
            # title vacío ⇒ muta a "Design for <session_id>"
            "doc_type": "design",
            "scope": "local",
            "fields": {
                "status": "draft",
                "session_id": "2026-08-24_refactor-auth",
                "spec_path": "vault/specs/2026-08-24_endpoint.md",
                "architecture_decision": "Capa servicio delgada sobre repositorio.",
                "data_model_changes": ["tabla sessions nueva"],
                "api_contracts": ["GET /v1/sessions"],
                "test_plan": ["unit service", "integration api"],
                "risks": ["migración de datos existentes"],
            },
        }),
        ("decision_reversible", {
            "doc_type": "decision",
            "scope": "local",
            "fields": {
                "title": "Flag CORTEX_PY activo durante transición",
                "status": "active",
                "context": "Doble vía CLI.",
                "decision": "Env var fuerza CLI viejo.",
                "alternative_rejected": "Feature flags por comando",
                "reason": "Simplicidad operativa.",
                "reversible_within_days": 14,
            },
        }),
        ("incident_open", {
            "doc_type": "incident",
            "scope": "local",
            "fields": {
                "title": "MCP server colgado 14 minutos",
                "status": "mitigated",
                "incident_number": 3,
                "severity": "high",
                "opened_at": "2026-05-15T09:30:00.000000Z",
                "closed_at": None,
                "affected_services": ["mcp-server", "opencode"],
                "timeline": [
                    "09:30 primer reporte",
                    "10:12 mitigado reiniciando pipe stderr",
                ],
                "impact": "subagente bloqueado, contexto perdido",
                "short_description": "stderr sin drenar bloqueó el event loop",
                "root_cause_postmortem": None,
            },
        }),
        ("postmortem_pm003", {
            "doc_type": "postmortem",
            "scope": "local",
            "fields": {
                "title": "PM: MCP server colgado",
                "status": "published",
                "incident_number": 3,
                "incident_path": "INC-003-2026-05-15-mcp-colgado.md",
                "root_cause": "contrapresión del pipe stderr",
                "contributing_factors": ["logging a stderr", "cliente lento"],
                "what_went_well": ["diagnóstico rápido"],
                "what_went_wrong": ["alerta tardía"],
                "action_items": ["logs sólo a archivo", "drain background"],
                "timeline": ["2026-05-15 incidente", "2026-05-16 fix"],
                "severity": "high",
            },
        }),
        ("runbook_deploy", {
            "doc_type": "runbook",
            "scope": "local",
            "fields": {
                "title": "Runbook deploy producción",
                "tags": ["ops"],
                "status": "verified",
                "runbook_kind": "deploy",
                "description": "Pasos para desplegar cortex-memory.",
                "prerequisites": ["green CI", "backup store"],
                "procedure": [
                    "taggear release",
                    "correr wheels workflow",
                    "actualizar pipx",
                ],
                "rollback_procedure": ["reinstalar versión previa", "restaurar store"],
                "verification": ["cortex doctor --strict"],
                "applies_to": ["producción"],
                "estimated_duration_minutes": 45,
                "last_verified_at": "2026-08-01T00:00:00.000000Z",
            },
        }),
        ("changelog_070", {
            "doc_type": "changelog",
            "scope": "local",
            "fields": {
                "title": "Changelog 0.7.0",
                "status": "released",
                "version": "0.7.0",
                "release_date": "2026-08-20T18:00:00.000000Z",
                "added": ["brain nativo", "TUI splash"],
                "changed": ["store v3 append-only"],
                "deprecated": ["chromadb episódico"],
                "removed": [],
                "fixed": ["drain stderr MCP"],
                "security": [],
            },
        }),
        ("hu_jira", {
            "doc_type": "hu",
            "scope": "local",
            "fields": {
                "title": "HU COR-482 búsqueda semántica",
                "status": "in-progress",
                "external_id": "COR-482",
                "source": "jira",
                "kind": "story",
                "description": "Como usuario quiero buscar en mi bóveda semánticamente.",
                "acceptance_criteria": ["búsqueda híbrida responde <1s"],
                "assignee": "chucho",
                "external_url": "https://empresa.atlassian.net/browse/COR-482",
                "synced_at": "2026-08-22T14:03:00.000000Z",
            },
        }),
        ("glossary_term_as_title", {
            # title vacío ⇒ muta a term
            "doc_type": "glossary",
            "scope": "local",
            "fields": {
                "status": "canonical",
                "term": "Sesión",
                "definition": "Unidad de trabajo con checkpoints verificables.",
                "examples": ["sesión de refactor auth"],
                "related_terms": ["checkpoint", "spec"],
                "domain": "memoria cognitiva",
            },
        }),
    ]

    _patch_now()
    import cortex.documentation.writers as W

    from cortex.documentation.data import (
        ADRData,
        ArchitectureData,
        ChangelogData,
        DecisionData,
        DesignDocData,
        GlossaryEntryData,
        HandoffData,
        HUData,
        IncidentData,
        PostmortemData,
        RunbookData,
        SessionData,
        SpecData,
    )

    DATA_CLASS_BY_TYPE = {
        "adr": ADRData,
        "decision": DecisionData,
        "incident": IncidentData,
        "postmortem": PostmortemData,
        "runbook": RunbookData,
        "architecture": ArchitectureData,
        "changelog": ChangelogData,
        "handoff": HandoffData,
        "glossary": GlossaryEntryData,
        "session": SessionData,
        "spec": SpecData,
        "hu": HUData,
        "design": DesignDocData,
    }

    WRITER_BY_TYPE = {
        "adr": W.write_adr_note,
        "decision": W.write_decision_note,
        "incident": W.write_incident_note,
        "postmortem": W.write_postmortem_note,
        "runbook": W.write_runbook_note,
        "architecture": W.write_architecture_note,
        "changelog": W.write_changelog_note,
        "handoff": W.write_handoff_note,
        "glossary": W.write_glossary_entry,
        "session": W.write_session_note_canonical,
        "spec": W.write_spec_note_canonical,
        "hu": W.write_hu_note,
        "design": W.write_design_note,
    }

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    inputs = []
    for name, case in CASES:
        doc_type = case["doc_type"]
        scope = case.get("scope", "local")
        project_id = case.get("project_id")
        actor = case.get("actor")
        vault = OUT / name / "vault"
        for rel, content in case.get("pre_files", {}).items():
            p = vault / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")

        kwargs = dict(case["fields"])
        if "verification_hooks" in kwargs:
            kwargs["verification_hooks"] = [VerificationHook(**h) for h in kwargs["verification_hooks"]]
        data = DATA_CLASS_BY_TYPE[doc_type](**kwargs)

        class V:
            path = vault

            def index_file(self, rel):  # noqa: ARG002
                return True

        path = WRITER_BY_TYPE[doc_type](
            data, vault=V(), vault_scope=scope, project_id=project_id,
            actor=actor, overwrite=True,
        )
        rel = path.relative_to(OUT / name).as_posix()
        inputs.append({
            "case": name,
            "doc_type": doc_type,
            "scope": scope,
            "project_id": project_id,
            "actor": actor,
            "expected_rel": rel,
            "pre_files": case.get("pre_files", {}),
            "fields": case["fields"],
        })

    (OUT / "inputs.json").write_text(
        json.dumps({"now": NOW_Z, "cases": inputs}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print(f"{len(inputs)} casos capturados en {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
