#!/usr/bin/env python3
"""Golden CIERRE T1 — handlers MCP no-sesión in-process.

Los escenarios invocan el DISPATCHER REAL de ``cortex/mcp/server.py``
(``_dispatch_tool_sync``) sobre instancias construidas con ``__new__``
(mismo patrón de tests/unit/test_mcp_server.py), con una memoria fake
determinista y los motores pesados ya gateados reemplazados por fakes
(ContextEnricher → P7, Reconstructor/Persister → P5). La familia write_doc
usa los writers REALES de cortex.documentation sobre un vault tmp; las
excepciones se formatean como en ``handle_call_tool``
(``Error ejecutando <name>: <exc>``), punto de comparación simétrico con
el dispatcher Rust.

Normalización: {{ROOT}} (tmp del oráculo). Determinista: timestamps fijos;
los fixtures usan un solo token placeholder/claim por caso para no depender
del orden de iteración de frozensets.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path, PurePosixPath
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("PYTHONHASHSEED", "0")

from cortex.mcp.server import CortexMCPServer  # noqa: E402
from cortex.models import (  # noqa: E402
    EnrichedContext,
    EnrichedItem,
    EpisodicHit,
    MemoryEntry,
    RetrievalResult,
    SemanticDocument,
    UnifiedHit,
    WorkContext,
)

ROOT_MARK = "{{ROOT}}"


def j(v) -> str:
    return json.dumps(v, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Memoria fake unificada (contratos ya gateados por fase)
# ---------------------------------------------------------------------------

class UnifiedFakeMemory:
    """retrieve/enrich con modelos reales; spec/hu/sesiones configurables."""

    def __init__(self, spec_mode="ok", get_hu_fail_id="HU-999"):
        self.spec_mode = spec_mode
        self.get_hu_fail_id = get_hu_fail_id
        self.last_retrieve: tuple | None = None
        self.last_enrich: dict | None = None
        self.spec_kwargs: dict | None = None
        # Atributos que los handlers leen del motor (fakes neutrales).
        self.episodic = None
        self.semantic = None
        self.workspace_root = None
        self.repo_root = None
        self._session_service = SimpleNamespace()
        self._note_service = SimpleNamespace()
        self._vault_path_resolved = Path("/tmp/fake-vault")

    # -- search/context ----------------------------------------------------
    def retrieve(self, query, top_k=5, use_embeddings=False):
        self.last_retrieve = (query, top_k, use_embeddings)
        if query == "EMPTY":
            return RetrievalResult(query=query)
        if query == "FALLBACK":
            return RetrievalResult(
                query=query,
                episodic_hits=[
                    EpisodicHit(
                        entry=MemoryEntry(
                            id="mem_fb1aaaa",
                            content="Sesión previa de auth",
                            memory_type="session",
                            files=["src/a.py"],
                            timestamp=datetime(2026, 8, 20, 10, 0, 0),
                            confidence=None,
                        ),
                        score=0.87,
                    )
                ],
                semantic_hits=[
                    SemanticDocument(
                        path="specs/auth.md",
                        title="Auth spec",
                        content="Contenido\nmultilínea",
                        score=3.21,
                    )
                ],
            )
        return RetrievalResult(
            query=query,
            unified_hits=[
                UnifiedHit(
                    source="episodic",
                    score=0.03278688524590164,
                    entry=MemoryEntry(
                        id="mem_aaa11111",
                        content="Implementamos login con JWT",
                        memory_type="session",
                        tags=["auth"],
                        files=["src/auth.py", "src/jwt.py"],
                        timestamp=datetime(2026, 8, 25, 10, 0, 0),
                        confidence="verified",
                    ),
                    metadata={},
                ),
                UnifiedHit(
                    source="semantic",
                    score=0.016393442622950872,
                    doc=SemanticDocument(
                        path="specs/auth.md",
                        title="Auth",
                        content="Primera línea\nde dos",
                        score=4.5,
                    ),
                    metadata={},
                ),
            ],
        )

    def enrich(self, changed_files, keywords=None, pr_title=None, *, top_k=None):
        self.last_enrich = {
            "changed_files": list(changed_files),
            "keywords": list(keywords or []),
            "pr_title": pr_title,
            "top_k": top_k,
        }
        if not keywords:
            items: list[EnrichedItem] = []
        else:
            items = [
                EnrichedItem(
                    source="episodic",
                    source_id="mem_aaa11111",
                    title="[SESSION] Implementamos login",
                    content="Implementamos login con JWT y refresh tokens",
                    score=0.5,
                    enriched_score=0.75,
                    matched_by=["topic_search", "keyword_search"],
                    files_mentioned=["src/auth.py"],
                    date=datetime(2026, 8, 25, 10, 0, 0),
                    tags=["auth", "jwt"],
                    confidence="verified",
                ),
                EnrichedItem(
                    source="semantic",
                    source_id="specs/auth.md",
                    title="Auth spec",
                    content="Spec del módulo de autenticación",
                    score=0.4,
                    enriched_score=0.4,
                    matched_by=["topic_search"],
                    date=datetime(2026, 8, 1, 9, 30, 0),
                ),
            ]
        return EnrichedContext(
            work=WorkContext(
                source="manual",
                changed_files=list(changed_files),
                keywords=list(keywords or []),
                pr_title=pr_title,
                search_queries=[" ".join(keywords[:1])] if keywords else [],
            ),
            items=items,
            total_items=len(items),
        )

    # -- sync_vault ----------------------------------------------------------
    def sync_vault(self):
        return 3

    # -- spec ------------------------------------------------------------------
    def create_spec_note(self, **kwargs):
        self.spec_kwargs = dict(kwargs)
        if self.spec_mode == "value_error":
            raise ValueError("El título es obligatorio para crear una spec.")
        if self.spec_mode == "duplicate":
            from cortex.documentation.errors import DuplicateDocumentError

            raise DuplicateDocumentError(
                "Document already exists with different content: "
                "vault/specs/demo-spec-title.md. Pass overwrite=True to "
                "replace, or choose a different title."
            )
        session = SimpleNamespace(is_gitless=True)
        if self.spec_mode != "gitless":
            session = None
        return SimpleNamespace(
            path=Path("vault/specs/demo-spec-title.md"), session=session
        )

    # -- hu ----------------------------------------------------------------------
    def import_work_item(self, external_id, *, provider="jira", remember=True):
        return Path(f"vault/hu/{str(external_id).lower()}.md")

    def get_work_item_note(self, item_id):
        if item_id == self.get_hu_fail_id:
            raise FileNotFoundError(f"Tracked item not found in vault: {item_id}")
        return Path(f"vault/hu/{str(item_id).lower()}.md")

    # -- sesiones (finish/briefing) ----------------------------------------------
    def get_active_session(self):
        return getattr(self, "_active", None)

    def get_session(self, sid):
        rec = getattr(self, "_records", {}).get(sid)
        if rec is None:
            raise KeyError(sid)
        return rec


from cortex.session import SessionStatus as _SS


class ClosedRecord:
    session_id = "2026-05-16_demo"
    status = _SS.CLOSED


class OpenRecord:
    session_id = "2026-05-16_demo"
    status = _SS.OPEN


def _server(memory, **extra) -> CortexMCPServer:
    srv = CortexMCPServer.__new__(CortexMCPServer)
    srv.memory = memory  # type: ignore[assignment]
    srv._called_tools = set()
    srv._tool_call_history = []
    srv._last_proposal_emitted_at = None
    for k, v in extra.items():
        setattr(srv, k, v)
    return srv


# ---------------------------------------------------------------------------
# Escenarios
# ---------------------------------------------------------------------------

def build_report(root: Path) -> str:
    blocks: list[str] = []

    def norm(text: str) -> str:
        return text.replace(str(root), ROOT_MARK)

    def emit(name, fn):
        try:
            out = fn()
            blocks.append(f"### {name}\nrc=0\n{out}")
        except Exception as exc:  # noqa: BLE001
            blocks.append(f"### {name}\nrc=1\nException: {type(exc).__name__}: {exc}")

    def call(srv, name, args=None):
        """Espejo de handle_call_tool: registra la llamada en _called_tools y
        captura excepciones al formato canónico."""
        srv._called_tools.add(name)
        try:
            return srv._dispatch_tool_sync(name, dict(args or {}))
        except Exception as exc:  # noqa: BLE001
            return f"Error ejecutando {name}: {exc}"

    # ---- familia search/context/sync_ticket ------------------------------
    mem = UnifiedFakeMemory()
    srv = _server(mem, project_root=root)

    def s01():
        out = call(srv, "cortex_search", {"query": "login jwt"})
        assert mem.last_retrieve == ("login jwt", 5, False), mem.last_retrieve
        return out

    emit("S01 search legacy unified", s01)

    def s02():
        return call(srv, "cortex_search", {"query": "EMPTY", "limit": 3})

    emit("S02 search vacio", s02)

    def s03():
        return call(srv, "cortex_search_vector", {"query": "FALLBACK", "limit": 2})

    emit("S03 search fallback listas separadas", s03)

    def s04():
        big = RetrievalResult(
            query="big",
            unified_hits=[
                UnifiedHit(
                    source="semantic",
                    score=0.5,
                    doc=SemanticDocument(path="x.md", title="X", content="a" * 5000),
                    metadata={},
                )
            ],
        )
        return str(big.to_prompt())

    emit("S04 search truncado 4000 chars", s04)

    def s05():
        out = call(srv, "cortex_search_vector", {"query": "login jwt", "limit": "7"})
        flag = mem.last_retrieve[2]
        k = mem.last_retrieve[1]
        first = out.splitlines()[0]
        return f"use_embeddings={flag} top_k={k}\n{first}"

    emit("S05 search_vector embeddings flag", s05)

    def s06():
        captured: dict = {}

        class FakeEnricher:
            def __init__(self, *, episodic, semantic, config, observer):
                pass

            def enrich(self, work, *, top_k, filters):
                captured["top_k"] = top_k
                captured["work_keywords"] = list(work.keywords)
                captured["queries"] = list(work.search_queries)
                dt = (
                    sorted(d.value for d in filters.doc_types)
                    if filters.doc_types
                    else []
                )
                captured["scope"] = filters.vault_scope
                ctx = mem.enrich([], keywords=["auth"])
                ctx.items[0].title = f"structural doc_types={dt}"
                return ctx

        with (
            patch("cortex.context_enricher.enricher.ContextEnricher", FakeEnricher),
            patch("cortex.context_enricher.telemetry.make_observer", lambda **kw: None),
        ):
            out = call(
                srv,
                "cortex_search",
                {"query": "auth flow", "doc_type": ["adr", "spec"], "limit": 4},
            )
        meta = (
            f"captured={captured['top_k']}|{captured['work_keywords']}"
            f"|{captured['queries']}|scope={captured.get('scope')}"
        )
        return f"{meta}\n{out.splitlines()[0]}"

    emit("S06 search structural con filtros", s06)

    def s07():
        with patch.object(
            sys.modules["cortex.cli._search_filters"],
            "build_enrichment_filters_from_cli",
            side_effect=ValueError("Invalid --scope value: 'galaxy'"),
        ):
            return call(srv, "cortex_search", {"query": "q", "scope": "galaxy"})

    emit("S07 search filtro inválido", s07)

    def s08():
        out = call(
            srv,
            "cortex_context",
            {
                "query": "release 2 context",
                "changed_files": ["cortex/core.py", " , ", ""],
                "task_type": "deep-code",
                "complexity": "",
            },
        )
        tk = mem.last_enrich["top_k"]
        pt = mem.last_enrich["pr_title"]
        kw = mem.last_enrich["keywords"]
        return f"enriched_kwargs={tk}|{pt}|{kw}\n{out}"

    emit("S08 context task_type budget", s08)

    def s09():
        (root / "auth.py").write_text("x = 1\n", encoding="utf-8")
        sub = root / "src"
        sub.mkdir(exist_ok=True)
        (sub / "core.py").write_text("y = 2\n", encoding="utf-8")
        req = "Revisar auth.py y src/core.py del flujo de login"
        out = call(srv, "cortex_sync_ticket", {"user_request": req, "top_k": 5})
        lines = out.split("\n")
        scope = lines[lines.index("## Scope detectado") + 1]
        kwline = lines[lines.index("## Keywords") + 1]
        return norm(f"scope={scope}\nkeywords={kwline}")

    emit("S09 sync_ticket candidatos inferidos", s09)

    def s10():
        return call(srv, "cortex_sync_ticket", {})

    emit("S10 sync_ticket sin user_request", s10)

    # ---- familia proposal / create_spec (datetime congelado) --------------
    class FrozenDatetime(datetime):
        now_value: float = 1000.0

        @classmethod
        def now(cls, tz=None):  # noqa: ANN001
            base = datetime.fromtimestamp(cls.now_value)
            if tz is not None:
                return base.replace(tzinfo=tz)
            return base

    frozen = FrozenDatetime

    def frozen_ctx(value: float):
        frozen.now_value = value
        return patch("cortex.mcp.tools.documenter.datetime", frozen)

    def s11():
        p = _server(UnifiedFakeMemory())
        payload = {
            "summary": "Migrar el módulo de pagos a pasarela nueva.",
            "alternatives": [
                {"id": "A", "description": "Proveedor X, costo bajo"},
                {
                    "id": "B",
                    "description": "Proveedor Y, más features",
                    "rejected_reason": "costo alto",
                },
            ],
            "recommendation_id": "A",
            "risks": ["  ", "migración doble escritura"],
        }
        with frozen_ctx(1000.0):
            return call(p, "cortex_emit_proposal", payload)

    emit("S11 proposal card válida", s11)

    def bad_call(payload):
        p = _server(UnifiedFakeMemory())
        with frozen_ctx(1000.0):
            return call(p, "cortex_emit_proposal", payload)

    ALTS_OK = [
        {"id": "A", "description": "hacer X"},
        {"id": "B", "description": "hacer Y", "rejected_reason": "más caro"},
    ]

    def s12():
        return bad_call({"summary": "", "alternatives": ALTS_OK, "recommendation_id": "A"})

    emit("S12 proposal summary vacío", s12)

    def s13():
        alts = [
            {"id": "a b", "description": "d"},
            {"id": "B", "description": "e", "rejected_reason": "r"},
        ]
        return bad_call({"summary": "s", "alternatives": alts, "recommendation_id": "A"})

    emit("S13 proposal id patrón inválido", s13)

    def s14():
        alts = [{"id": "A", "description": "d"}, {"id": "A", "description": "e"}]
        return bad_call({"summary": "s", "alternatives": alts, "recommendation_id": "A"})

    emit("S14 proposal ids duplicados", s14)

    def s15():
        return bad_call({"summary": "s", "alternatives": ALTS_OK, "recommendation_id": "Z"})

    emit("S15 recommendation inexistente", s15)

    def s16():
        alts = [
            {"id": "A", "description": "d", "rejected_reason": "mal"},
            {"id": "B", "description": "e", "rejected_reason": "r"},
        ]
        return bad_call({"summary": "s", "alternatives": alts, "recommendation_id": "A"})

    emit("S16 recomendada con rejected_reason", s16)

    def s17():
        alts = [{"id": "A", "description": "d"}, {"id": "B", "description": "e"}]
        return bad_call({"summary": "s", "alternatives": alts, "recommendation_id": "A"})

    emit("S17 no-recomendada sin reason", s17)

    def s18():
        alts = [
            {"id": "A", "description": "d", "zzz": 1},
            {"id": "B", "description": "e", "rejected_reason": "r"},
        ]
        return bad_call({"summary": "s", "alternatives": alts, "recommendation_id": "A"})

    emit("S18 campo extra en alternativa", s18)

    def s19():
        return bad_call({"summary": "", "alternatives": [], "recommendation_id": ""})

    emit("S19 tres errores orden declaración", s19)

    def s20():
        return bad_call({"summary": 42, "alternatives": ALTS_OK, "recommendation_id": "A"})

    emit("S20 summary no string", s20)

    def s21():
        return bad_call({
            "summary": "s",
            "alternatives": ALTS_OK,
            "recommendation_id": "A",
            "risks": ["r" * 301],
        })

    emit("S21 risk demasiado largo", s21)

    def s22():
        alts = [{"id": i, "description": "d", "rejected_reason": "r"} for i in "ABCDEF"]
        return bad_call({"summary": "s", "alternatives": alts, "recommendation_id": "A"})

    emit("S22 demasiadas alternativas", s22)

    # ---- create_spec -------------------------------------------------------
    def s23():
        m = UnifiedFakeMemory()
        p = _server(m, project_root=root)
        call(p, "cortex_ping", {})
        return call(p, "cortex_create_spec", {"title": "T", "goal": "G"})

    emit("S23 governance violation tras ping", s23)

    def s24():
        m = UnifiedFakeMemory()
        p = _server(m, project_root=root)
        call(p, "cortex_sync_ticket", {"user_request": "algo"})
        out = call(p, "cortex_create_spec", {
            "title": "Demo Spec Title",
            "goal": "Meta clara",
            "requirements": ["R1"],
            "files_in_scope": ["src/a.py"],
            "constraints": [],
            "acceptance_criteria": ["A1"],
            "tags": ["demo"],
            "verification_hooks": [{
                "name": "tests", "command": "pytest -q", "required": True,
                "success_criteria": "todo verde", "timeout_seconds": 300,
            }],
            "no_sync": True,
            "proposal_mode": "optional",
        })
        hooks = m.spec_kwargs["verification_hooks"] if m.spec_kwargs else None
        sync = m.spec_kwargs["sync_vault"] if m.spec_kwargs else None
        pm = m.spec_kwargs["proposal_mode"] if m.spec_kwargs else None
        return f"kwargs={hooks}|{sync}|{pm}\n{out}"

    emit("S24 create_spec happy", s24)

    def s25():
        p = _server(UnifiedFakeMemory(spec_mode="gitless"), project_root=root)
        call(p, "cortex_sync_ticket", {"user_request": "x"})
        return call(p, "cortex_create_spec", {"title": "Demo Spec Title"})

    emit("S25 create_spec gitless degraded", s25)

    def s26():
        p = _server(UnifiedFakeMemory(spec_mode="value_error"), project_root=root)
        call(p, "cortex_sync_ticket", {"user_request": "x"})
        return call(p, "cortex_create_spec", {"title": ""})

    emit("S26 create_spec ValueError", s26)

    def s27():
        p = _server(UnifiedFakeMemory(spec_mode="duplicate"), project_root=root)
        call(p, "cortex_sync_ticket", {"user_request": "x"})
        return call(p, "cortex_create_spec", {"title": "Demo Spec Title"})

    emit("S27 create_spec duplicada", s27)

    def s28():
        p = _server(UnifiedFakeMemory(), project_root=root)
        call(p, "cortex_sync_ticket", {"user_request": "x"})
        return call(p, "cortex_create_spec", {
            "title": "T", "goal": "G",
            "proposal_mode": "required", "proposal_confirmed": True,
        })

    emit("S28 required sin emit previo", s28)

    def s29():
        p = _server(UnifiedFakeMemory(), project_root=root)
        call(p, "cortex_sync_ticket", {"user_request": "x"})
        with frozen_ctx(1000.0):
            p._emit_proposal_text({
                "summary": "s", "alternatives": ALTS_OK, "recommendation_id": "A"
            })
            frozen.now_value = 1001.0
            return call(p, "cortex_create_spec", {
                "title": "T", "goal": "G",
                "proposal_mode": "required", "proposal_confirmed": True,
            })

    emit("S29 gap menor a 2s", s29)

    def s30():
        p = _server(UnifiedFakeMemory(), project_root=root)
        call(p, "cortex_sync_ticket", {"user_request": "x"})
        with frozen_ctx(1000.0):
            p._emit_proposal_text({
                "summary": "s", "alternatives": ALTS_OK, "recommendation_id": "A"
            })
        with frozen_ctx(1003.5):
            return call(p, "cortex_create_spec", {
                "title": "T", "goal": "G",
                "proposal_mode": "required", "proposal_confirmed": True,
            })

    emit("S30 gap suficiente pasa", s30)

    # ---- self_review_note ---------------------------------------------------
    def s31():
        p = _server(UnifiedFakeMemory())
        return call(p, "cortex_self_review_note", {
            "body": "Esto queda TBD para después."
        })

    emit("S31 placeholder único", s31)

    def s32():
        p = _server(UnifiedFakeMemory())
        return call(p, "cortex_self_review_note", {
            "body": "El build exitoso terminó.",
            "verification_hooks_passed": False,
        })

    emit("S32 claim hueco", s32)

    def s33():
        p = _server(UnifiedFakeMemory())
        return call(p, "cortex_self_review_note", {
            "body": "Verificación completa.", "verification_hooks_passed": True
        })

    emit("S33 limpio pasa", s33)

    def s34():
        p = _server(UnifiedFakeMemory())
        return call(p, "cortex_self_review_note", {
            "body": "FIXME pendiente; build exitoso.",
            "verification_hooks_passed": False,
        })

    emit("S34 placeholder + claim hueco", s34)

    # ---- write_doc (writers REALES sobre tmp vault) -------------------------
    from cortex.workspace.layout import WorkspaceLayout

    def make_doc_server():
        layout = WorkspaceLayout.discover(root)
        return _server(UnifiedFakeMemory(), _layout=layout, project_root=root)

    def s35():
        return norm(call(make_doc_server(), "cortex_write_doc", {
            "doc_type": "adr",
            "payload": {
                "title": "Usar Rust para el núcleo",
                "context": "Python es lento",
                "decision": "Portear a Rust",
            },
        }))

    emit("S35 write_doc adr success", s35)

    def s36():
        return call(make_doc_server(), "cortex_write_doc", {
            "doc_type": "changelog", "payload": {"version": ""}
        })

    emit("S36 changelog falta version", s36)

    def s37():
        return call(make_doc_server(), "cortex_write_doc", {
            "doc_type": "zzz", "payload": {}
        })

    emit("S37 doc_type desconocido", s37)

    def s38():
        return call(make_doc_server(), "cortex_write_doc", {
            "doc_type": "adr", "payload": [1, 2]
        })

    emit("S38 payload no objeto", s38)

    def s39():
        srv_d = make_doc_server()
        args = {
            "doc_type": "adr",
            "payload": {"title": "Dup", "context": "c", "decision": "d",
                        "adr_number": 1},
        }
        args2 = {
            "doc_type": "adr",
            "payload": {"title": "Dup", "context": "c", "decision": "OTRA",
                        "adr_number": 1},
        }
        call(srv_d, "cortex_write_doc", args)
        out2 = call(srv_d, "cortex_write_doc", args2)
        if not out2.startswith("Error ejecutando"):
            return f"sin duplicado?? -> {out2}"
        return norm(out2)

    emit("S39 adr duplicada", s39)

    def s40():
        return call(make_doc_server(), "cortex_write_doc", {
            "doc_type": "handoff",
            "vault_scope": "enterprise",
            "payload": {"title": "H", "parent_session_id": "s1"},
        })

    emit("S40 handoff local-only", s40)

    def s40b():
        return call(make_doc_server(), "cortex_write_doc", {
            "doc_type": "adr",
            "vault_scope": "enterprise",
            "payload": {"title": "E", "context": "c", "decision": "d"},
        })

    emit("S40b adr enterprise sin owner/team", s40b)

    def s41():
        return norm(call(make_doc_server(), "cortex_write_doc", {
            "doc_type": "glossary",
            "payload": {
                "title": "Fingerprint",
                "term": "Fingerprint",
                "definition": "SHA-256 del body",
            },
        }))

    emit("S41 glossary title fallback", s41)

    def s42():
        return norm(call(make_doc_server(), "write_design_note_canonical", {
            "session_id": "2026-08-25_demo",
            "spec_path": "vault/specs/demo.md",
            "architecture_decision": "Monolito modular",
        }))

    emit("S42 design note success", s42)

    def s43():
        srv_d = make_doc_server()
        a = call(srv_d, "write_design_note_canonical", {})
        b = call(srv_d, "write_design_note_canonical", {"session_id": "s1"})
        return f"{a}\n{b}"

    emit("S43 design validaciones", s43)

    def s44():
        p = _server(UnifiedFakeMemory())
        return call(p, "cortex_import_hu", {"external_id": "HU-123", "provider": "linear"})

    emit("S44 import_hu", s44)

    def s45():
        p = _server(UnifiedFakeMemory())
        ok = call(p, "cortex_get_hu", {"item_id": "HU-123"})
        bad = call(p, "cortex_get_hu", {"item_id": "HU-999"})
        return f"{ok}\n{bad}"

    emit("S45 get_hu ok y missing", s45)

    # ---- finish/briefing ------------------------------------------------------
    def s46():
        m = UnifiedFakeMemory()
        m._active = OpenRecord()
        p = _server(m)
        return call(p, "cortex_finish_session", {"interactive": True})

    emit("S46 finish interactive rechazado", s46)

    def s47():
        m = UnifiedFakeMemory()
        m._active = OpenRecord()
        m._records = {"2026-05-16_demo": OpenRecord()}
        p = _server(m)
        a = call(p, "cortex_finish_session", {"intent": "bogus"})
        b = call(p, "cortex_finish_session", {"intent": "handoff"})
        p2 = _server(UnifiedFakeMemory())
        c = call(p2, "cortex_finish_session", {})
        return f"{a}\n{b}\n{c}"

    emit("S47 finish validaciones", s47)

    def s48():
        m = UnifiedFakeMemory()
        m._records = {"2026-05-16_demo": ClosedRecord()}
        p = _server(m)
        return call(p, "cortex_finish_session", {"session_id": "2026-05-16_demo"})

    emit("S48 finish sesión cerrada", s48)

    def s49():
        captured: dict = {}

        class FakePersister:
            def __init__(self, *, note_service, session_service, vault_path):
                pass

            def finalize(self, out, overrides=None):
                forced = (
                    overrides.forced_status.value
                    if overrides and overrides.forced_status
                    else None
                )
                captured["forced"] = forced
                return SimpleNamespace(
                    session_id="2026-05-16_demo",
                    final_status=SimpleNamespace(value=forced or "handoff"),
                    session_note_path=PurePosixPath(
                        "vault/sessions/2026-05-16_demo.md"
                    ),
                    adrs_created=[PurePosixPath("vault/decisions/ADR-001-usar-rust.md")],
                    summary="Resumen de cierre",
                    already_closed=False,
                )

        class FakeRunner:
            def __init__(self, *, repo_root):
                pass

        class FakeRecon:
            def __init__(self, *, session_service, verification_runner, repo_root):
                pass

            def reconstruct(self, inp):
                return SimpleNamespace()

        def run():
            m = UnifiedFakeMemory()
            m._active = OpenRecord()
            m._records = {"2026-05-16_demo": OpenRecord()}
            p = _server(m)
            return call(p, "cortex_finish_session", {})

        with (
            patch("cortex.documenter.Reconstructor", FakeRecon),
            patch("cortex.session.verification.VerificationRunner", FakeRunner),
            patch("cortex.documenter.DocumenterPersister", FakePersister),
        ):
            out = run()
        return f"forced={captured['forced']}\n{out}"

    emit("S49 finish auto happy", s49)

    def s51():
        captured: dict = {}

        class FakeReconstructor:
            def __init__(self, *, session_service, verification_runner, repo_root):
                pass

            def reconstruct(self, inp):
                captured["run_hooks"] = inp.run_hooks
                captured["session_id"] = inp.session_id
                return SimpleNamespace(
                    session_id="2026-05-16_demo",
                    spec=SimpleNamespace(
                        path=PurePosixPath("vault/specs/demo.md"),
                        title="Demo",
                        goal="Meta demo",
                        files_in_scope=[PurePosixPath("src/a.py")],
                        constraints=[],
                        acceptance_criteria=["Criterio uno"],
                        verification_hooks=[
                            SimpleNamespace(
                                name="tests",
                                command="pytest -q",
                                required=True,
                                success_criteria="verde",
                                timeout_seconds=300,
                            )
                        ],
                    ),
                    diff_text="diff --git a/src/a.py\n+b\n",
                    diff_entries=[
                        SimpleNamespace(action="added", path=PurePosixPath("src/a.py"))
                    ],
                    files_touched=[PurePosixPath("src/a.py")],
                    files_verified_by_git=[PurePosixPath("src/a.py")],
                    files_declared_only=[],
                    in_scope_files=[PurePosixPath("src/a.py")],
                    out_of_scope_files=[],
                    unimplemented_files=[],
                    verification_results=[
                        SimpleNamespace(
                            name="tests",
                            command="pytest -q",
                            passed=True,
                            exit_code=0,
                            output="1 passed",
                            duration_ms=120,
                            run_at=datetime(2026, 8, 25, 12, 0, 0),
                        )
                    ],
                    contradictions=[
                        SimpleNamespace(
                            prior_record="ADR-000 decía X",
                            current_claim="ahora es Y",
                            evidence=["src/a.py:1"],
                            severity="high",
                        )
                    ],
                    suggested_status=SimpleNamespace(value="handoff"),
                    suggested_adrs=[
                        SimpleNamespace(
                            title="ADR demo",
                            rationale="porque sí",
                            source_checkpoint_index=0,
                            evidence=["claim"],
                            confidence=0.85,
                        )
                    ],
                    raw_checkpoints=[
                        SimpleNamespace(
                            timestamp=datetime(2026, 8, 25, 11, 0, 0),
                            source=SimpleNamespace(value="manual"),
                            verified_claims=["claim"],
                            unverified_claims=[],
                            artifacts_touched=["src/a.py"],
                            note="nota",
                        )
                    ],
                    end_commit="b" * 40,
                    gitless=False,
                )

        class FakeRunner:
            def __init__(self, *, repo_root):
                pass

        def run():
            m = UnifiedFakeMemory()
            m._active = OpenRecord()
            m._records = {"2026-05-16_demo": OpenRecord()}
            p = _server(m)
            return call(p, "cortex_documenter_briefing", {"session_id": "2026-05-16_demo"})

        with (
            patch("cortex.documenter.Reconstructor", FakeReconstructor),
            patch("cortex.session.verification.VerificationRunner", FakeRunner),
        ):
            out = run()
        meta = f"captured={captured['run_hooks']}|{captured['session_id']}"
        return f"{meta}\n{out}"

    emit("S51 briefing serialización completa", s51)

    return "\n".join(blocks) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify"))
    parser.add_argument("--out", default="bench/parity/.p12-cierre-mcp")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    golden_path = out_dir / "golden_cierre_mcp.txt"

    with tempfile.TemporaryDirectory(prefix="cierre_mcp_") as td:
        root = Path(td).resolve()
        report = build_report(root)

    if args.mode == "build":
        golden_path.write_text(report, encoding="utf-8")
        print(f"[BUILD] {golden_path} ({len(report.splitlines())} líneas)")
        return 0

    expected = golden_path.read_text(encoding="utf-8")
    if report != expected:
        exp_lines = expected.splitlines()
        got_lines = report.splitlines()
        for i, (a, b) in enumerate(zip(exp_lines, got_lines)):
            if a != b:
                print(f"[FAIL] primera divergencia en línea {i + 1}:")
                print(f"  esperado: {a!r}")
                print(f"  obtenido: {b!r}")
                break
        else:
            print(f"[FAIL] longitud difiere: {len(exp_lines)} vs {len(got_lines)}")
        return 1
    print(f"[PASS] golden_cierre_mcp.txt ({len(expected.splitlines())} líneas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
