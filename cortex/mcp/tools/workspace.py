"""Handlers MCP del dominio workspace/docs/HU (mixín de CortexMCPServer).

Extraído del monolito server.py (deuda V1, Obra 01 fase P3). Los métodos
conservan su firma y semántica ``self.`` exactas; el contrato observable
está congelado por tests/unit/mcp/test_golden_contract.py.
"""

from __future__ import annotations

import json
from typing import Any

from cortex.mcp.vault_adapter import PathVault


class WorkspaceToolsMixin:
    """Mixín: handlers MCP de workspace/docs/HU."""

    def _write_design_note_text(self, arguments: dict[str, Any]) -> str:
        """Tool: ``write_design_note_canonical`` (Phase 09.B).

        Persists a design document under ``vault/designs/`` using the
        canonical writer. The vault path is resolved via the active
        :class:`WorkspaceLayout`; failures (invalid spec_path, missing
        required field) come back as ``❌ <message>`` for the LLM.
        """
        from cortex.documentation import write_design_note_canonical
        from cortex.documentation.data import DesignDocData
        from cortex.documentation.errors import SchemaValidationError
        from cortex.documentation.writers import VaultLike

        title = str(arguments.get("title", "")).strip()
        session_id = str(arguments.get("session_id", "")).strip()
        spec_path = str(arguments.get("spec_path", "")).strip()
        if not session_id:
            return "❌ session_id is required for write_design_note_canonical."
        if not spec_path:
            return "❌ spec_path is required for write_design_note_canonical."

        data = DesignDocData(
            title=title or f"Design for {session_id}",
            tags=list(arguments.get("tags", []) or []),
            status=str(arguments.get("status", "draft")),
            session_id=session_id,
            spec_path=spec_path,
            architecture_decision=str(arguments.get("architecture_decision", "")),
            data_model_changes=list(arguments.get("data_model_changes", []) or []),
            api_contracts=list(arguments.get("api_contracts", []) or []),
            test_plan=list(arguments.get("test_plan", []) or []),
            risks=list(arguments.get("risks", []) or []),
        )

        # Reuse the same vault discovery the spec / session writers use.
        layout = self._get_layout()
        vault_root = layout.vault_path
        vault_root.mkdir(parents=True, exist_ok=True)

        vault: VaultLike = PathVault(vault_root)
        try:
            path = write_design_note_canonical(data, vault=vault)
        except SchemaValidationError as exc:
            return f"❌ {exc}"
        return json.dumps({"path": str(path)}, ensure_ascii=False)

    _DOC_TYPE_DISPATCH: dict[str, tuple[str, str]] = {
        # doc_type → (DataClass name, writer name) — resolved at runtime
        # against ``cortex.documentation.data`` and ``cortex.documentation``
        # so the table stays compact and self-documenting.
        "session": ("SessionData", "write_session_note_canonical"),
        "handoff": ("HandoffData", "write_handoff_note"),
        "adr": ("ADRData", "write_adr_note"),
        "decision": ("DecisionData", "write_decision_note"),
        "incident": ("IncidentData", "write_incident_note"),
        "postmortem": ("PostmortemData", "write_postmortem_note"),
        "runbook": ("RunbookData", "write_runbook_note"),
        "architecture": ("ArchitectureData", "write_architecture_note"),
        "changelog": ("ChangelogData", "write_changelog_note"),
        "glossary": ("GlossaryEntryData", "write_glossary_entry"),
        "hu": ("HUData", "write_hu_note"),
    }

    def _write_doc_text(self, arguments: dict[str, Any]) -> str:
        """Tool: ``cortex_write_doc`` (Phase 09.A+ / May 2026).

        Dispatch the payload to the appropriate canonical writer based
        on ``doc_type``. The skill calls this for each note it wants to
        persist (one session + zero or more ADRs / decisions / runbooks
        / etc.). Returns JSON ``{path, doc_type}`` on success or
        ``❌ <message>`` on validation failure.

        ``spec`` and ``design`` are not routed here on purpose — those
        have their own governance flows (``cortex_create_spec`` and
        ``write_design_note_canonical``).
        """
        from cortex.documentation import data as data_module
        from cortex.documentation import (
            write_adr_note,
            write_architecture_note,
            write_changelog_note,
            write_decision_note,
            write_glossary_entry,
            write_handoff_note,
            write_hu_note,
            write_incident_note,
            write_postmortem_note,
            write_runbook_note,
            write_session_note_canonical,
        )
        from cortex.documentation.errors import SchemaValidationError
        from cortex.documentation.writers import VaultLike

        doc_type = str(arguments.get("doc_type", "")).strip()
        if doc_type not in self._DOC_TYPE_DISPATCH:
            return (
                f"❌ Unknown doc_type {doc_type!r}. Must be one of: "
                f"{', '.join(sorted(self._DOC_TYPE_DISPATCH))}."
            )

        payload = arguments.get("payload") or {}
        if not isinstance(payload, dict):
            return "❌ 'payload' must be an object."

        # Fail-fast validation of the minimum-required-fields contract
        # documented in the tool description. Without this, the failure
        # happens deeper in ``write_*_canonical`` via ``SchemaValidationError``
        # with a less actionable message. The list below mirrors the bullets
        # in the tool description; keep them in sync.
        _REQUIRED_BY_DOC_TYPE: dict[str, tuple[str, ...]] = {
            "session": ("title", "spec_summary", "session_id"),
            "handoff": ("title", "parent_session_id"),
            "adr": ("title", "context", "decision"),
            "decision": ("title", "context", "decision"),
            "incident": ("title", "short_description", "severity"),
            "postmortem": ("title", "incident_path", "incident_number", "root_cause"),
            "runbook": ("title", "runbook_kind", "procedure"),
            "architecture": ("title", "summary"),
            "changelog": ("title", "version"),
            "glossary": ("title", "term", "definition"),
            "hu": ("title", "external_id", "source"),
        }
        required_fields = _REQUIRED_BY_DOC_TYPE.get(doc_type, ())
        missing = [f for f in required_fields if not payload.get(f)]
        if missing:
            return (
                f"❌ payload for doc_type={doc_type!r} is missing required "
                f"field(s): {', '.join(missing)}. See the tool description "
                f"for the full per-type contract."
            )

        vault_scope = str(arguments.get("vault_scope", "local"))
        overwrite = bool(arguments.get("overwrite", False))

        data_class_name, writer_name = self._DOC_TYPE_DISPATCH[doc_type]
        data_class = getattr(data_module, data_class_name)
        writer_map = {
            "write_session_note_canonical": write_session_note_canonical,
            "write_handoff_note": write_handoff_note,
            "write_adr_note": write_adr_note,
            "write_decision_note": write_decision_note,
            "write_incident_note": write_incident_note,
            "write_postmortem_note": write_postmortem_note,
            "write_runbook_note": write_runbook_note,
            "write_architecture_note": write_architecture_note,
            "write_changelog_note": write_changelog_note,
            "write_glossary_entry": write_glossary_entry,
            "write_hu_note": write_hu_note,
        }
        writer = writer_map[writer_name]

        # Reuse the same vault discovery as other writers.
        layout = self._get_layout()
        vault_root = layout.vault_path
        vault_root.mkdir(parents=True, exist_ok=True)

        vault: VaultLike = PathVault(vault_root)

        # Build the dataclass from the payload, dropping unknown fields
        # so an over-eager LLM that includes extras doesn't crash the call.
        valid_fields = {f.name for f in data_class.__dataclass_fields__.values()}
        clean_payload = {k: v for k, v in payload.items() if k in valid_fields}
        try:
            data = data_class(**clean_payload)
            path = writer(data, vault=vault, vault_scope=vault_scope, overwrite=overwrite)
        except SchemaValidationError as exc:
            return f"❌ {exc}"
        except TypeError as exc:
            return f"❌ Invalid payload for doc_type={doc_type!r}: {exc}"
        return json.dumps(
            {"path": str(path), "doc_type": doc_type}, ensure_ascii=False
        )

    def _import_hu_text(self, arguments: dict[str, Any]) -> str:
        path = self.memory.import_work_item(
            arguments.get("external_id", ""),
            provider=arguments.get("provider", "jira"),
            remember=not arguments.get("no_remember", False),
        )
        return f"Tracked item imported -> {path}"

    def _get_hu_text(self, arguments: dict[str, Any]) -> str:
        path = self.memory.get_work_item_note(arguments.get("item_id", ""))
        return f"Tracked item note -> {path}"

