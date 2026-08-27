#!/usr/bin/env python3
"""Oráculo de paridad P12A-2 — WorkItemService (hu/workitems) nativo.

El porte Rust (cortex-app::workitems) consume el writer canónico
cortex-setup::writers::build_note("hu") cuya escritura ya está gateada
byte-a-byte por el golden hu_jira de writers (P8b). Este oráculo congela el
COMPORTAMIENTO DEL SERVICIO espejando tests/unit/workitems/test_service.py:

  S01 import escribe HU-{id}.md en hu/ y get_item_note lo encuentra
  S02 contenido de la nota (normalizado {{TS}}/{{ROOT}})
  S03 legacy slug sigue resolviendo
  S04 get_item_note inexistente ⇒ FileNotFoundError msg exacto
  S05 provider desconocido / no configurado / has_provider
  S06 re-import mismo item ⇒ no-op idempotente (un solo archivo)
  S07 duplicado con contenido distinto ⇒ DuplicateDocumentError
  S08 remember=True ⇒ resumen episódico (content/tags/files/metadata)
  S09 list_item_notes ordenado
  S10 index_file llamado con la rel correcta

Uso:
  python p12a2_golden.py build --out bench/parity/golden_p12a2 [--fixtures /tmp/p12a2fix]
  python p12a2_golden.py verify --out bench/parity/golden_p12a2

Lado Rust:
  cargo run -q -p cortex-app --example p12a2_check -- <fixtures_dir> <golden_dir>

Normalizaciones pactadas:
  - {{ROOT}} por la ruta absoluta del fixture/workdir.
  - created_at/updated_at del frontmatter (reloj real) → ``{{TS}}``.
    El synced_at del item es FIJO en el provider fake ⇒ el resto (incluido
    fingerprint) queda determinista y se compara byte-a-byte.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

SYNC_FIJA = "2026-08-22T14:03:00.000000Z"

# ── fakes espejo de tests/unit/workitems ────────────────────────────────────


@dataclass
class _FakeEpisodic:
    llamadas: list = field(default_factory=list)

    def add(self, *, content, memory_type, tags, files, extra_metadata):
        self.llamadas.append({
            "content": content,
            "memory_type": memory_type,
            "tags": list(tags),
            "files": list(files),
            "extra_metadata": dict(extra_metadata or {}),
        })


@dataclass
class _FakeSemantic:
    llamadas: list = field(default_factory=list)

    def index_file(self, rel_path: str) -> bool:
        self.llamadas.append(rel_path)
        return False


def _provider_fake():
    from cortex.workitems.models import TrackedItem, WorkItemKind, WorkItemSource
    from cortex.workitems.providers.base import WorkItemProvider

    class FakeProvider(WorkItemProvider):
        def __init__(self, configurado: bool = True) -> None:
            self._configurado = configurado

        def source_name(self) -> str:
            return "fake"

        def is_configured(self) -> bool:
            return self._configurado

        def get_item(self, external_id: str) -> TrackedItem:
            import datetime as dt

            return TrackedItem(
                id=external_id,
                external_id=external_id,
                source=WorkItemSource.JIRA,
                kind=WorkItemKind.STORY,
                title=f"HU {external_id} búsqueda semántica",
                description="Como usuario quiero buscar en mi bóveda semánticamente.",
                acceptance_criteria=["búsqueda híbrida responde <1s"],
                labels=["rag"],
                assignee="chucho",
                external_url=f"https://empresa.atlassian.net/browse/{external_id}",
                sync_timestamp=dt.datetime.fromisoformat(
                    SYNC_FIJA.replace("Z", "+00:00")
                ),
            )

    return FakeProvider


def construir_fixture(base: Path) -> Path:
    """Vault pristine con la nota legacy del slug."""
    vault = base / "vault"
    (vault / "hu").mkdir(parents=True)
    (vault / "hu" / "cor-999.md").write_text("---\ntitle: x\n---\n", encoding="utf-8")
    return base


def correr_secuencia(work: Path) -> str:
    """Ejecuta los escenarios sobre una COPIA y devuelve el reporte crudo."""
    from cortex.workitems.service import WorkItemService

    FakeProvider = _provider_fake()

    bloques: list[str] = []

    def emitir(titulo: str, fn) -> None:
        ep = _FakeEpisodic()
        sem = _FakeSemantic()
        try:
            salida = fn(ep, sem)
            bloques.append(f"### {titulo}\nrc=0\n{salida}")
        except Exception as exc:  # noqa: BLE001 - el mensaje ES el contrato
            bloques.append(f"### {titulo}\nrc=1\n{type(exc).__name__}: {exc}")

    def nuevo_svc(ep, sem, configurado=True, ctx=None) -> WorkItemService:
        return WorkItemService(
            vault_path=work / "vault",
            semantic=sem,
            episodic=ep,
            providers={"fake": FakeProvider(configurado=configurado)},
            context_metadata=ctx or {},
        )

    def s01(ep, sem):
        svc = nuevo_svc(ep, sem)
        path = svc.import_item("COR-482", provider="fake", remember=False)
        encontrado = svc.get_item_note("COR-482")
        return f"path={path.relative_to(work)}\nencontrado={encontrado.relative_to(work)}"

    def s02(ep, sem):
        svc = nuevo_svc(ep, sem)
        svc.import_item("COR-482", provider="fake", remember=False)
        nota = svc.get_item_note("COR-482")
        return nota.read_text(encoding="utf-8")

    def s03(ep, sem):
        svc = nuevo_svc(ep, sem)
        return str(svc.get_item_note("COR-999").relative_to(work))

    def s04(ep, sem):
        svc = nuevo_svc(ep, sem)
        svc.get_item_note("NOPE-1")
        return "no debería llegar"

    def s05(ep, sem):
        out = []
        out.append(f"desconocido={nuevo_svc(ep, sem).has_provider('nope')}")
        out.append(f"fake_ok={nuevo_svc(ep, sem).has_provider('fake')}")
        out.append(f"FAKE_normaliza={nuevo_svc(ep, sem).has_provider('FAKE')}")
        try:
            nuevo_svc(ep, sem).import_item("X-1", provider="nope", remember=False)
        except Exception as exc:  # noqa: BLE001
            out.append(f"nope={type(exc).__name__}: {exc}")
        try:
            nuevo_svc(ep, sem, configurado=False).import_item(
                "X-1", provider="fake", remember=False
            )
        except Exception as exc:  # noqa: BLE001
            out.append(f"sin_conf={type(exc).__name__}: {exc}")
        return "\n".join(out)

    def s06(ep, sem):
        svc = nuevo_svc(ep, sem)
        svc.import_item("A-1", provider="fake", remember=False)
        antes = (work / "vault" / "hu" / "HU-A-1.md").read_text(encoding="utf-8")
        svc.import_item("A-1", provider="fake", remember=False)
        despues = (work / "vault" / "hu" / "HU-A-1.md").read_text(encoding="utf-8")
        archivos = sorted(p.name for p in (work / "vault" / "hu").glob("*.md"))
        return f"noop_igual={antes == despues}\narchivos={archivos}"

    def s07(ep, sem):
        svc = nuevo_svc(ep, sem)
        path = svc.import_item("DUP-7", provider="fake", remember=False)
        path.write_text("---\ntitle: otra cosa\nfingerprint: deadbeefdeadbeef\n---\ncuerpo distinto\n", encoding="utf-8")
        svc.import_item("DUP-7", provider="fake", remember=False)
        return "no debería llegar"

    def s08(ep, sem):
        ctx = {"workspace": "obra07"}
        svc = nuevo_svc(ep, sem, ctx=ctx)
        svc.import_item("EP-3", provider="fake", remember=True)
        return json.dumps({"episodico": ep.llamadas, "semantic": sem.llamadas},
                          indent=1, ensure_ascii=False, sort_keys=True)

    def s09(ep, sem):
        svc = nuevo_svc(ep, sem)
        for eid in ("B-2", "A-1", "C-3"):
            svc.import_item(eid, provider="fake", remember=False)
        return "\n".join(str(p.relative_to(work)) for p in svc.list_item_notes())

    # Cada escenario corre sobre su propia copia del vault para aislamiento.
    escenarios = [s01, s02, s03, s04, s05, s06, s07, s08, s09]
    titulos = [
        "S01 import+get canonical",
        "S02 contenido nota ({{TS}}/{{ROOT}})",
        "S03 legacy slug",
        "S04 no existente",
        "S05 providers",
        "S06 re-import noop",
        "S07 duplicado distinto",
        "S08 remember episódico+semantic",
        "S09 list ordenado",
    ]
    pristine = work.parent / "pristine_vault"
    if not pristine.exists():
        shutil.copytree(work / "vault", pristine)
    for titulo, fn in zip(titulos, escenarios):
        shutil.rmtree(work / "vault")
        shutil.copytree(pristine, work / "vault")
        emitir(titulo, fn)
    return "".join(bloques)


def normalizar(texto: str, work: Path) -> str:
    texto = texto.replace(str(work), "{{ROOT}}")
    # created_at/updated_at del frontmatter (reloj real; yaml_dump_safe
    # las emite entre comillas simples).
    texto = re.sub(
        r"(created_at|updated_at): '?\d{4}-\d{2}-\d{2}T[0-9:.+\-Z]+'?",
        r"\1: '{{TS}}'",
        texto,
    )
    if not texto.endswith("\n"):
        texto += "\n"
    return texto


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("build", "verify"):
        p = sub.add_parser(name)
        p.add_argument("--out", type=Path, default=REPO_ROOT / "bench/parity/golden_p12a2")
        p.add_argument("--fixtures", type=Path, default=None)
    ns = ap.parse_args()
    destino = ns.out / "golden_p12a2.txt"

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        pristine = construir_fixture(base / "fixtures")
        work = base / "work"
        shutil.copytree(pristine, work)

        contenido = normalizar(correr_secuencia(work), work)

        if ns.cmd == "verify":
            esperado = destino.read_text(encoding="utf-8")
            if contenido == esperado:
                print("[PASS] golden_p12a2.txt")
                print("\n✅ ORÁCULO DETERMINISTA (lado Python)")
                return 0
            print("[FAIL] golden_p12a2.txt difiere")
            for l in list(difflib.unified_diff(
                    esperado.splitlines(), contenido.splitlines(),
                    lineterm=""))[:60]:
                print(l)
            return 1

        ns.out.mkdir(parents=True, exist_ok=True)
        destino.write_text(contenido, encoding="utf-8")
        print(f"[capturado] {destino}")

        if ns.fixtures:
            if ns.fixtures.exists():
                shutil.rmtree(ns.fixtures)
            shutil.copytree(pristine, ns.fixtures)
            print(f"fixture reconstruido → {ns.fixtures}")
        print("\nVerificación Rust:")
        print(
            f"  cargo run -q -p cortex-app --example p12a2_check -- "
            f"<fixtures_dir> {ns.out}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
