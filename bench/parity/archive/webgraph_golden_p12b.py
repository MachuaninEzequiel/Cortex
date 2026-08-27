#!/usr/bin/env python3
"""Oráculo de paridad P12B-2 — servidor WebGraph Flask vs axum nativo.

Sub-comandos:
  build   — construye los fixtures deterministas y captura el golden.
  verify  — regenera TODO en temp y compara contra lo commiteado.
  fixtures — sólo reconstruye el fixture pristine para el checker Rust.

Uso:
  python webgraph_golden_p12b.py build --out bench/parity/golden_webgraph \
      [--fixtures /tmp/p12bfix]
  python webgraph_golden_p12b.py verify --out bench/parity/golden_webgraph

El lado Rust se verifica con:
  cargo run -q -p cortex-webgraph-server --example webgraph_check -- \
      <fixtures_dir> <golden_dir>

Ambos lados levantan su server REAL sobre puerto efímero (bind :0 ⇒ el
puerto asignado NO se compara; la config de puertos se congela en CFG).
Endpoints golpeados con header X-Cortex-WebGraph: 1.

CONTRATO de normalización (documentado; el resto es byte-parity):
  1. ``{{ROOT}}`` reemplaza la base de fixtures.
  2. ``"generated_at": "<ISO>"`` → ``{{TS}}`` (reloj real).
  3. ``"fingerprint": "<64 hex>"`` → ``{{FP}}`` (hash de mtimes).
  4. Guard 403 sin header: sólo STATUS (body HTML de werkzeug no es
     contrato JSON; se marca STATUS_ONLY).
  5. Un único ``\\n`` final por bloque.

DETERMINISMO DEL FIXTURE (para siempre):
  - Embeddings: función PURA compartida fake_embed(text) = 8 dims desde
    SHA-256(text) ⇒ bits idénticos en ambos runtimes sin modelos ONNX.
  - Episódicos: export neutro P3 con ids fijos y timestamps fijos; orden
    canónico sorted-by-id en ambos lados.
  - Vault: recorrido SORTED por rel_path en ambos lados (el índice nativo
    ya itera sorted; el oráculo envuelve iter_documents ordenado).
  - Sin org.yaml (enterprise enrichment es P12B-3; sin org.yaml Python
    tampoco agrega nodos).

DESVÍOS DECLARADOS (no simulados):
  - origin_project_id/origin_scope del reader federado no llegan al nodo
    (SemDoc nativo no los expone): metadata queda vault_scope="local".
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import http.client
import json
import re
import shutil
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

# ── embedder puro compartido ────────────────────────────────────────────────


def fake_embed(text: str) -> list[float]:
    """8 dimensiones derivadas de SHA-256(text) — MISMA función en Rust."""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    vec = []
    for i in range(8):
        chunk = int.from_bytes(digest[8 * i : 8 * i + 8], "little")
        vec.append(((chunk >> 11) / float(2**53)) * 2.0 - 1.0)
    return vec


# ── fixture ─────────────────────────────────────────────────────────────────

CONFIG_A = "semantic:\n  vault_path: vault\n"
CONFIG_WEBGRAPH = "default_mode: hybrid\nignored_tags: [general, noise]\n"

VAULT_DOCS = {
    "specs/2026-05-01_auth-spec.md": (
        "---\ntitle: Spec de autenticación\nstatus: accepted\n---\n\n"
        "# Spec: autenticación\n\n"
        "Login con tokens [[ADR-001]] y fusion [[glossary/rrf]].\n"
        "Runbook asociado: [[RB-deploy]].\n"
    ),
    "decisions/ADR-001-tokens.md": (
        "---\ntitle: ADR-001 tokens JWT\nadr_number: 1\n---\n\n"
        "# ADR-001: tokens JWT\n\nDecidimos usar tokens JWT cortos.\n"
    ),
    "decisions/ADR-000-legacy.md": (
        "---\ntitle: ADR-000 legacy\nadr_number: 0\nsuperseded_by: ADR-001\n---\n\n"
        "# ADR-000\n\nSistema viejo de sesiones cookie.\n"
    ),
    "decisions/DEC-2026-05-02-cache.md": (
        "---\ntitle: DEC cache híbrido\n---\n\n"
        "# Decisión cache\n\nCache híbrido para retrieval del spec.\n"
    ),
    "sessions/2026-05-03_login-session.md": (
        "---\ntitle: Sesión login\ntags: [session]\n---\n\n"
        "# Sesión: login\n\nSe implementó el spec de autenticación con "
        "tokens jwt y cache retrieval.\n"
    ),
    "glossary/rrf.md": (
        "---\ntitle: RRF\n---\n\n"
        "# RRF\n\nReciprocal Rank Fusion combina rankings de retrieval.\n"
    ),
    "runbooks/RB-deploy.md": (
        "---\ntitle: RB deploy\n---\n\n# Runbook deploy\n\nDeploy con rollback seguro.\n"
    ),
    "notes/ideas.md": (
        "---\ntitle: Ideas varias\n---\n\nIdeas sin clasificar todavía.\n"
    ),
}

MEMORIAS = [
    ("mem_03", "Incidente: outage de login durante el deploy del servicio.",
     "general", [], ["runbooks/RB-deploy.md"],
     "2026-05-04T10:00:00+00:00", {"person": ["ada"]}),
    ("mem_01", "Se arregló el bug del parser de tokens del login.",
     "session", ["session"], ["specs/2026-05-01_auth-spec.md"],
     "2026-05-03T09:00:00+00:00", {}),
    ("mem_02", "Spec promoted: autenticación con tokens y cache.",
     "spec", ["spec"], [],
     "2026-05-02T08:00:00+00:00", {}),
]

BETA_DOCS = {
    "glossary/bm25.md": (
        "---\ntitle: BM25 beta\n---\n\nBM25 rankea documentos del proyecto beta.\n"
    ),
}


def construir_fixture(base: Path) -> Path:
    alpha = base / "alpha"
    (alpha / ".cortex" / "webgraph").mkdir(parents=True)
    (alpha / "memory").mkdir(parents=True)
    (alpha / "memory" / "dummy.txt").write_text("cache-token-file\n",
                                                encoding="utf-8")
    (alpha / "config.yaml").write_text(CONFIG_A, encoding="utf-8")
    (alpha / ".cortex" / "webgraph" / "config.yaml").write_text(
        CONFIG_WEBGRAPH, encoding="utf-8")
    for rel, contenido in VAULT_DOCS.items():
        p = alpha / "vault" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(contenido, encoding="utf-8")

    rows = []
    for mid, content, mtype, tags, files, ts, entities in sorted(MEMORIAS):
        meta = {
            "id": mid,
            "memory_type": mtype,
            "tags": json.dumps(tags),
            "files": json.dumps(files),
            "timestamp": ts,
        }
        if entities:
            for etype, values in entities.items():
                for v in values:
                    meta[f"entity_{etype}_{v}"] = True
        rows.append({
            "id": mid,
            "document": content,
            "meta": meta,
            "embedding": fake_embed(content),
        })
    (alpha / "memory" / "episodic_export.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
        encoding="utf-8",
    )

    beta = base / "beta"
    (beta / ".cortex").mkdir(parents=True)
    (beta / "config.yaml").write_text("semantic:\n  vault_path: vault\n",
                                      encoding="utf-8")
    for rel, contenido in BETA_DOCS.items():
        p = beta / "vault" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(contenido, encoding="utf-8")

    ws = base / "ws"
    (ws / ".cortex" / "webgraph").mkdir(parents=True)
    payload = {
        "projects": [
            {"id": "alpha", "root": str(alpha.resolve())},
            {"id": "beta", "root": str(beta.resolve())},
        ]
    }
    import yaml

    (ws / ".cortex" / "webgraph" / "workspace.yaml").write_text(
        yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return ws


# ── inyección determinista para create_app ──────────────────────────────────


def cargar_episodicos(persist_dir: Path):
    """Entradas desde el export P3 (ids/timestamps fijos)."""
    from cortex.models import MemoryEntry

    jsonl = persist_dir / "episodic_export.jsonl"
    entries = []
    for line in jsonl.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        meta = dict(row["meta"])
        entities = {}
        clean = {}
        for k, v in meta.items():
            if k.startswith("entity_") and v is True:
                rest = k[len("entity_"):]
                etype, _, evalue = rest.partition("_")
                entities.setdefault(etype, []).append(evalue)
            else:
                clean[k] = v
        ts = clean.pop("timestamp")
        metadata = {}
        flags_meta = {}
        # entity_* flags NO van al metadata dict (el webgraph lee
        # metadata["entities"]); replicar extract del store real.
        if entities:
            metadata["entities"] = entities
        entries.append(MemoryEntry(
            id=clean["id"],
            content=row["document"],
            memory_type=clean.get("memory_type", "general"),
            tags=json.loads(clean.get("tags", "[]")),
            files=json.loads(clean.get("files", "[]")),
            timestamp=__import__("datetime").datetime.fromisoformat(ts),
            metadata=metadata,
        ))
        del flags_meta
    return entries


class _FakeStore:
    """EpisodicMemoryStore offline sobre el export P3."""

    def __init__(self, persist_dir=None, collection_name=None,
                 embedding_model=None, embedding_backend=None, **_kw):
        self.persist_dir = Path(persist_dir)
        if (self.persist_dir / "episodic_export.jsonl").exists():
            self._entries = cargar_episodicos(self.persist_dir)
        else:
            self._entries = []

    embedder = None

    @property
    def cache_token(self) -> int:
        return 7

    def count(self) -> int:
        return len(self._entries)

    def list_entries(self):
        return list(self._entries)


class _FakeEmbedder:
    def embed(self, text: str) -> list[float]:
        return fake_embed(text)


def inyectar_fakes() -> None:
    import cortex.webgraph.episodic_source as es_mod
    import cortex.webgraph.semantic_source as ss_mod

    ss_mod.Embedder = lambda **_kw: _FakeEmbedder()
    es_mod.Embedder = lambda **_kw: _FakeEmbedder()
    es_mod.EpisodicMemoryStore = _FakeStore


class _SortedReader:
    """VaultReader con iteración canónica ordenada por rel_path."""

    def __init__(self, inner):
        self._inner = inner

    def iter_documents(self):
        yield from sorted(self._inner.iter_documents(), key=lambda kv: kv[0])


def crear_app_determinista(alpha: Path):
    """create_app con embedder/store falsos e iteración ordenada."""
    import cortex.webgraph.server as server_mod
    import cortex.webgraph.semantic_source as ss_mod
    from cortex.webgraph.server import create_app

    original_reader = ss_mod.VaultReader

    class ReaderOrdenado(original_reader):
        def iter_documents(self):
            yield from sorted(super().iter_documents(), key=lambda kv: kv[0])

    ss_mod.VaultReader = ReaderOrdenado
    try:
        app = create_app(alpha)
    finally:
        ss_mod.VaultReader = original_reader
    return app, server_mod


# ── transporte ──────────────────────────────────────────────────────────────


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _serve(app, port: int) -> threading.Thread:
    t = threading.Thread(
        target=lambda: app.run(host="127.0.0.1", port=port, debug=False,
                               use_reloader=False),
        daemon=True,
    )
    t.start()
    return t


def _wait_ready(port: int) -> None:
    for _ in range(200):
        try:
            status, _, _ = _request(port, "GET", "/api/snapshot", header=False)
            if status in (200, 403):
                return
        except OSError:
            time.sleep(0.05)
    raise RuntimeError(f"server {port} no arrancó")


def _request(port: int, method: str, path: str, *, header: bool = True,
             body: bytes | None = None) -> tuple[int, str, bytes]:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
    headers = {"Connection": "close"}
    if header:
        headers["X-Cortex-WebGraph"] = "1"
    if body is not None:
        headers["Content-Type"] = "application/json"
    conn.request(method, path, body=body, headers=headers)
    r = conn.getresponse()
    data = r.read()
    ct = r.getheader("Content-Type", "")
    conn.close()
    return r.status, ct, data


# ── secuencia de escenarios ─────────────────────────────────────────────────


def _normalizar(texto: str, base: Path) -> str:
    texto = texto.replace(str(base), "{{ROOT}}")
    texto = re.sub(r'"generated_at":\s*"[^"]*"', '"generated_at":"{{TS}}"',
                   texto)
    texto = re.sub(r'"fingerprint":\s*"[0-9a-f]{64}"',
                   '"fingerprint":"{{FP}}"', texto)
    if not texto.endswith("\n"):
        texto += "\n"
    return texto


def correr_secuencia(base: Path) -> str:
    from cortex.webgraph.config import WebGraphConfig

    alpha = base / "alpha"
    ws_file = base / "ws" / ".cortex" / "webgraph" / "workspace.yaml"

    bloques: list[str] = []

    def registrar(case_id: str, status: int, ct: str, body: bytes,
                  *, status_only: bool = False) -> None:
        if status_only:
            bloques.append(f"### {case_id} rc={status} STATUS_ONLY")
            return
        text = body.decode("utf-8", errors="replace")
        bloques.append(f"### {case_id} rc={status} ct={ct}")
        bloques.append(_normalizar(text, base))

    # ── CFG: config canónica (puertos/rutas por defecto) ──
    cfg = WebGraphConfig()
    dump_cfg = json.dumps(cfg.model_dump(), sort_keys=True,
                          separators=(",", ":"), ensure_ascii=True)
    bloques.append("### CFG rc=200 ct=application/json")
    bloques.append(_normalizar(dump_cfg, base))

    # ── server single ──
    inyectar_fakes()
    app, server_mod = crear_app_determinista(alpha)
    port = _free_port()
    _serve(app, port)
    _wait_ready(port)

    # Apertura stubbeada (sin side-effects del SO).
    abiertos: list[str] = []
    server_mod.open_path = lambda p: abiertos.append(str(p))

    s, ct, b = _request(port, "GET", "/api/snapshot", header=False)
    registrar("S00_sin_header", s, ct, b, status_only=(s == 403))

    s, ct, b = _request(port, "GET", "/api/snapshot")
    registrar("S01_snapshot_hybrid_default", s, ct, b)
    snap = json.loads(b)

    s, ct, b = _request(port, "GET", "/api/snapshot?mode=semantic")
    registrar("S02_snapshot_semantic", s, ct, b)

    s, ct, b = _request(port, "GET", "/api/snapshot?mode=episodic")
    registrar("S03_snapshot_episodic", s, ct, b)

    s, ct, b = _request(port, "GET", "/api/snapshot?mode=bogus")
    registrar("S04_mode_invalido", s, ct, b)

    # Nodo semántico con wikilinks (URL-encoded).
    node_id = "semantic:specs%2F2026-05-01_auth-spec.md"
    s, ct, b = _request(port, "GET", f"/api/node/{node_id}")
    registrar("S05_node_detail_spec", s, ct, b)

    s, ct, b = _request(port, "GET", "/api/node/missing-node")
    registrar("S06_node_missing", s, ct, b)

    s, ct, b = _request(
        port, "GET",
        "/api/subgraph?node_id=semantic%3Aspecs%2F2026-05-01_auth-spec.md&depth=1")
    registrar("S07_subgraph_depth1", s, ct, b)

    s, ct, b = _request(
        port, "GET",
        "/api/subgraph?node_id=semantic%3Anotes%2Fideas.md&depth=2"
        "&edge_types=shared_tag,wikilink")
    registrar("S08_subgraph_edge_types", s, ct, b)

    s, ct, b = _request(port, "POST", "/api/open",
                        body=json.dumps({"node_id": "missing"}).encode())
    registrar("S09_open_unknown", s, ct, b)

    s, ct, b = _request(port, "POST", "/api/open", body=b"{}",)
    registrar("S10_open_body_invalido", s, ct, b)

    # Nodo episódico SIN files ⇒ "Selected node has no local document".
    s, ct, b = _request(port, "POST", "/api/open",
                        body=json.dumps({"node_id": "episodic:mem_02"}).encode())
    registrar("S11_open_sin_doc_local", s, ct, b)

    # Éxito: nodo semántico local (open_path stubbeado).
    s, ct, b = _request(port, "POST", "/api/open",
                        body=json.dumps({
                            "node_id": "semantic:glossary/rrf.md"
                        }).encode())
    registrar("S12_open_ok", s, ct, b)
    assert len(abiertos) == 1, f"open_path debió llamarse una vez: {abiertos}"

    s, ct, b = _request(port, "GET", "/static/style.css")
    registrar("S13_static_css", s, ct, b)

    s, ct, b = _request(port, "GET", "/static/app.js")
    registrar("S14_static_js", s, ct, b)

    s, ct, b = _request(port, "GET", "/")
    registrar("S15_index_html", s, ct, b)

    # ── server federado ──
    app_ws = server_mod.create_app(alpha, workspace_file=ws_file)
    port_ws = _free_port()
    _serve(app_ws, port_ws)
    _wait_ready(port_ws)

    s, ct, b = _request(port_ws, "GET", "/api/snapshot")
    registrar("F01_snapshot_federated", s, ct, b)
    fsnap = json.loads(b)
    prefijado = None
    for n in fsnap.get("nodes", []):
        if n["id"].startswith("alpha::semantic:glossary/rrf.md"):
            prefijado = n["id"]
            break
    assert prefijado is not None, "falta nodo prefijado en federación"

    s, ct, b = _request(port_ws, "GET", f"/api/node/{prefijado.replace('/', '%2F').replace(':', '%3A')}")
    registrar("F02_node_prefijado", s, ct, b)

    s, ct, b = _request(port_ws, "GET", "/api/node/no-existe")
    registrar("F03_node_missing_federated", s, ct, b)

    return "\n".join(bloques) + "\n"


# ── main ────────────────────────────────────────────────────────────────────


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("build", "verify", "fixtures"):
        p = sub.add_parser(name)
        p.add_argument("--out", type=Path,
                       default=REPO_ROOT / "bench/parity/golden_webgraph")
        p.add_argument("--fixtures", type=Path, default=None)
    ns = ap.parse_args()

    ns.out.mkdir(parents=True, exist_ok=True)
    destino_golden = ns.out / "golden_webgraph.txt"

    if ns.cmd == "fixtures":
        if not ns.fixtures:
            print("--fixtures requerido")
            return 2
        if ns.fixtures.exists():
            shutil.rmtree(ns.fixtures)
        ns.fixtures.mkdir(parents=True)
        construir_fixture(ns.fixtures)
        print(f"fixture reconstruido → {ns.fixtures}")
        return 0

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / "fixtures"
        base.mkdir()
        construir_fixture(base)
        contenido = correr_secuencia(base)

        if ns.cmd == "verify":
            esperado = destino_golden.read_text(encoding="utf-8")
            if contenido == esperado:
                print("[PASS] golden_webgraph.txt")
                print("\n✅ ORÁCULO DETERMINISTA")
                return 0
            print("[FAIL] golden_webgraph.txt difiere")
            for l in list(difflib.unified_diff(
                    esperado.splitlines(), contenido.splitlines(),
                    lineterm=""))[:80]:
                print(l)
            print(f"\n❌ diferencias ({destino_golden})")
            return 1

        destino_golden.write_text(contenido, encoding="utf-8")
        print(f"[capturado] {destino_golden}")

        if ns.fixtures:
            if ns.fixtures.exists():
                shutil.rmtree(ns.fixtures)
            ns.fixtures.mkdir(parents=True)
            construir_fixture(ns.fixtures)
            print(f"fixture reconstruido → {ns.fixtures}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
