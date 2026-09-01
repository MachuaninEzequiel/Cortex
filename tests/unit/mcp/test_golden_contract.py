"""Golden tests de contrato MCP para ``CortexMCPServer``.

Red de seguridad OBLIGATORIA antes del split de ``cortex/mcp/server.py``
(Obra 01 fase P3). Congelan el contrato observable por cualquier cliente
MCP (plugin pi, IDEs):

1. ``list_tools`` — set exacto de tools anunciados, en orden, con sus
   descriptions e inputSchema byte-a-byte contra snapshot commiteado
   (``golden/list_tools.json``, generado del código pre-split).
2. Tabla de ruteo del dispatcher: cada nombre anunciado llega a SU handler.
3. Mensaje de error para herramienta desconocida.
4. Versión de servidor expuesta por ``cortex_ping``.

Si un test acá falla tras el split, el split rompió el contrato: NO
actualizar el snapshot para "arreglar" el test sin decisión explícita
documentada en docs/transformacion/.
"""

from __future__ import annotations

import asyncio
import json
from collections import deque
from pathlib import Path
from types import SimpleNamespace

import mcp.types as types
from mcp.server.lowlevel import Server

from cortex.mcp.server import CortexMCPServer

GOLDEN_PATH = Path(__file__).parent / "golden" / "list_tools.json"


def _bare_server() -> CortexMCPServer:
    """Instancia mínima sin __init__ (patrón de tests/unit/test_mcp_server.py).

    Suficiente para registrar los handlers (``_setup_tools``) y para invocar
    ``_dispatch_tool_sync`` con handlers parcheados.
    """
    s = CortexMCPServer.__new__(CortexMCPServer)
    s.server = Server("golden-contract")
    s._called_tools = set()
    s._tool_call_history = []
    s._error_history = deque(maxlen=10)
    s._setup_tools()
    return s


def _listed_tools() -> list[types.Tool]:
    s = _bare_server()
    handler = s.server.request_handlers[types.ListToolsRequest]
    req = types.ListToolsRequest(method="tools/list", params=None)
    res = asyncio.run(handler(req))
    return res.model_dump(mode="json")["tools"]


class TestGoldenListTools:
    def test_snapshot_coincide_byte_a_byte(self) -> None:
        """El list_tools completo (orden incluido) es idéntico al snapshot."""
        golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
        actuales = _listed_tools()
        assert actuales == golden["tools"], (
            "El contrato MCP cambió. Si el cambio es intencional, regenerá el "
            "snapshot y documentalo en docs/transformacion/; si no, hay una "
            "regresión."
        )

    def test_nombres_sin_duplicados(self) -> None:
        nombres = [t["name"] for t in _listed_tools()]
        assert len(nombres) == len(set(nombres))

    def test_cada_tool_anunciado_tiene_schema_objeto(self) -> None:
        for t in _listed_tools():
            assert t["inputSchema"].get("type") == "object", t["name"]
            assert "properties" in t["inputSchema"], t["name"]

    def test_server_version_expuesta(self) -> None:
        golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
        assert CortexMCPServer.SERVER_VERSION == golden["server_version"] == "2.2"


# Tabla nombre → handler que DEBE recibir la llamada. Derivada del dispatcher
# pre-split; el split debe preservarla exactamente (incluida la ruta especial
# de ``cortex_sync_vault``, que llama directo a ``memory.sync_vault``).
ROUTING_ESPERADO: dict[str, str] = {
    "cortex_ping": "_ping_text",
    "cortex_search": "_search_text_dispatch",
    "cortex_search_vector": "_search_vector_text",
    "cortex_context": "_context_text",
    "cortex_sync_ticket": "_build_sync_ticket_context",
    "cortex_create_spec": "_create_spec_text",
    "cortex_emit_proposal": "_emit_proposal_text",
    "cortex_save_session": "_save_session_text",
    "cortex_validate_handoff": "_validate_handoff_text",
    "cortex_verify_session_claims": "_verify_session_claims_text",
    "cortex_import_hu": "_import_hu_text",
    "cortex_get_hu": "_get_hu_text",
    "cortex_autopilot_start": "_autopilot_tools.start",
    "cortex_autopilot_preflight": "_autopilot_tools.preflight",
    "cortex_autopilot_checkpoint": "_autopilot_tools.checkpoint",
    "cortex_autopilot_finish": "_autopilot_tools.finish",
    "cortex_autopilot_status": "_autopilot_tools.status",
    "cortex_session_open": "_session_open_text",
    "cortex_session_checkpoint": "_session_checkpoint_text",
    "cortex_session_close": "_session_close_text",
    "cortex_session_status": "_session_status_text",
    "cortex_session_list": "_session_list_text",
    "cortex_finish_session": "_finish_session_text",
    "cortex_documenter_briefing": "_documenter_briefing_text",
    "cortex_close_session": "_close_session_text",
    "cortex_review_checkpoint": "_session_review_checkpoint_text",
    "write_design_note_canonical": "_write_design_note_text",
    "cortex_write_doc": "_write_doc_text",
    "cortex_self_review_note": "_self_review_note_text",
    "cortex_session_task_list": "_session_task_list_text",
    "cortex_session_task_update": "_session_task_update_text",
}

# Los anunciados deben ser exactamente los ruteados + sync_vault (que el
# dispatcher resuelve inline contra memory.sync_vault()).
NOMBRES_ANUNCIADOS_EXCLUIR_SYNC_VAULT = set(ROUTING_ESPERADO) | {"cortex_sync_vault"}


class TestGoldenRouting:
    def test_anunciados_son_exactamente_los_ruteables(self) -> None:
        nombres = {t["name"] for t in _listed_tools()}
        assert nombres == NOMBRES_ANUNCIADOS_EXCLUIR_SYNC_VAULT

    def test_cada_nombre_llega_a_su_handler(self) -> None:
        s = _bare_server()
        recibidas: list[str] = []

        def _recibir(tool: str, sentinel: str, args=None) -> str:
            recibidas.append(tool)
            return sentinel

        for tool, ruta in ROUTING_ESPERADO.items():
            sentinel = f"SENTINEL::{tool}"
            if ruta.startswith("_autopilot_tools."):
                stub = SimpleNamespace(
                    **{
                        m: (lambda args=None, _t=tool, _s=sentinel: _recibir(_t, _s, args))
                        for m in ("start", "preflight", "checkpoint", "finish", "status")
                    }
                )
                s._autopilot_tools = stub  # type: ignore[assignment]
            else:
                setattr(
                    s,
                    ruta,
                    lambda args=None, _t=tool, _s=sentinel: _recibir(_t, _s, args),
                )

            resultado = s._dispatch_tool_sync(tool, {})

            assert resultado == f"SENTINEL::{tool}", (
                f"{tool} NO llegó a su handler esperado ({ruta}); devolvió: {resultado!r}"
            )

        assert sorted(recibidas) == sorted(ROUTING_ESPERADO)

    def test_sync_vault_delega_en_memory(self) -> None:
        s = _bare_server()

        class _Mem:
            def sync_vault(self) -> int:
                return 7

        s.memory = _Mem()  # type: ignore[assignment]
        resultado = s._dispatch_tool_sync("cortex_sync_vault", {})
        assert resultado == "Vault synced - 7 documents indexed."

    def test_herramienta_desconocida_devuelve_mensaje_estable(self) -> None:
        s = _bare_server()
        resultado = s._dispatch_tool_sync("cortex_no_existe", {})
        assert resultado == "Herramienta desconocida: cortex_no_existe"

