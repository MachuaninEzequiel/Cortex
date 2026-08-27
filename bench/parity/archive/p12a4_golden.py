#!/usr/bin/env python3
"""Oráculo de paridad P12A-4 — doc_generator + doc_validator + doc_verifier.

Espeja tests/unit/pr/test_pr_context.py (TestDocGenerator) más el
comportamiento real de los tres módulos:

  S01 generate_session completo (pipeline results, tags, files) → content
  S02 generate_session vacío (defaults: not run / none / No description)
  S03 _safe_filename edge cases
  S04 generate_all con/sin skip_types
  S05 write_docs crea archivos
  S06 validate_file inexistente ⇒ error
  S07 nota sin frontmatter ⇒ warning frontmatter (+info date no aplica)
  S08 nota válida: wikilinks/embeds/properties
  S09 embed roto ⇒ warning; limpieza de targets (| # ^)
  S10 YAML inválido ⇒ error (mensaje normalizado {{YAML_ERR}})
  S11 fm parcial: sin title (warning) / sin date ni created (info)
  S12 DocVerifier.verify_from_list → to_json byte-a-byte
  S13 verify_from_diff git en non-repo ⇒ "git status failed: None"
  S14 vault fuera de root ⇒ "Vault directory not found"

Uso:
  python p12a4_golden.py build --out bench/parity/golden_p12a4
  python p12a4_golden.py verify --out bench/parity/golden_p12a4

Lado Rust:
  cargo run -q -p cortex-app --example p12a4_check -- <work_fixtures> <golden_dir>

Normalizaciones pactadas:
  - Reloj CONGELADO vía monkeypatch de cortex.doc_generator.datetime
    (patrón _patch_now de p8_writers_golden) ⇒ filename/fecha deterministas.
  - El mensaje "Invalid YAML: ..." depende del parser ⇒ se emite
    {{YAML_ERR}} en ambos lados.
"""

from __future__ import annotations

import argparse
import difflib
import os
import re
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

FECHA_FIJA = "2026-06-01"


def patch_now() -> None:
    """Congela el reloj de cortex.doc_generator."""
    import cortex.doc_generator as DG

    class _FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):  # noqa: ANN001
            return datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)

    DG.datetime = _FixedDatetime


def construir_vault(base: Path) -> Path:
    """Vault fixture para validator/verifier."""
    v = base / "vaultfix"
    v.mkdir(parents=True)
    (v / "ok.md").write_text(
        "---\ntitle: Nota OK\ndate: '2026-05-01'\ntags: [a, b]\n---\n"
        "Véase [[otra]] y [[con display]] [[ancla#sec]] [[bloque^x]].\n"
        "![[embed-ok]] ![[ok2]]\n",
        encoding="utf-8",
    )
    (v / "embed-ok.md").write_text("---\ntitle: E\n---\ncontenido\n", encoding="utf-8")
    (v / "ok2.md").write_text("---\ntitle: E2\n---\nx\n", encoding="utf-8")
    (v / "broken.md").write_text(
        "---\ntitle: Rota\n---\n![[no-existe]] y [[link-normal]]\n", encoding="utf-8"
    )
    (v / "nofm.md").write_text("solo texto\n", encoding="utf-8")
    (v / "badyaml.md").write_text("---\ntitle: [unclosed\n---\ncuerpo\n", encoding="utf-8")
    (v / "partial.md").write_text("---\ntags: [solo-tags]\n---\nx\n", encoding="utf-8")
    return v


def correr_secuencia(work: Path) -> str:
    from cortex.doc_generator import DocGenerator
    from cortex.doc_validator import DocValidator
    from cortex.doc_verifier import DocVerifier
    from cortex.models import PRContext

    patch_now()

    bloques: list[str] = []

    def emitir(titulo: str, fn) -> None:
        try:
            salida = fn()
            bloques.append(f"### {titulo}\nrc=0\n{salida}")
        except Exception as exc:  # noqa: BLE001
            bloques.append(f"### {titulo}\nrc=1\n{type(exc).__name__}: {exc}")

    vaultfix = work / "vaultfix"
    gen = DocGenerator(vault_path=work / "vault_out")

    def ctx_full() -> PRContext:
        return PRContext(
            pr_number=42,
            title="Fix login bug",
            body="Cuerpo del PR con detalles.",
            author="dev1",
            source_branch="fix/login",
            target_branch="main",
            commit_sha="abc123def4567890",
            files_changed=[f"f{i}.py" for i in range(25)],
            diff_summary=" f0.py | 1 +\n 1 file changed",
            labels=["rag", "backend", "ci", "x", "y", "z"],
            lint_result="pass",
            audit_result="pass",
            test_result="pass",
        )

    def s01() -> str:
        doc = gen.generate_session(ctx_full())
        assert doc.filename == f"{FECHA_FIJA}_fix-login-bug.md", doc.filename
        return f"filename={doc.filename}\n---\n{doc.content}"

    def s02() -> str:
        ctx = PRContext(
            title="T", author="a", source_branch="b", commit_sha="c"
        )
        doc = gen.generate_session(ctx)
        return f"filename={doc.filename}\n---\n{doc.content}"

    def s03() -> str:
        return "\n".join([
            gen._safe_filename("Fix login bug! @#$%"),   # noqa: SLF001
            gen._safe_filename("***"),
            gen._safe_filename("A B".upper()),
        ])

    def s04() -> str:
        docs_all = gen.generate_all(ctx_full())
        docs_skip = gen.generate_all(ctx_full(), skip_types=["session"])
        return (
            f"all={[d.doc_type for d in docs_all]}\nskip={docs_skip}\n"
            f"filenames={[d.filename for d in docs_all]}"
        )

    def s05() -> str:
        docs = gen.generate_all(ctx_full())
        written = gen.write_docs(docs)
        rels = [str(p.relative_to(work)) for p in written]
        contenidos_no_vacios = all(p.read_text(encoding="utf-8").strip() for p in written)
        return f"rels={rels}\nno_vacios={contenidos_no_vacios}"

    val = DocValidator(vault_path=vaultfix)

    def issues_breve(result) -> str:
        partes = [
            f"{i.severity}|{i.field}|{i.message}" for i in result.issues
        ]
        return "; ".join(partes)

    def s06() -> str:
        r = val.validate_file(vaultfix / "fantasma.md")
        return f"is_valid={r.is_valid}\n{issues_breve(r)}"

    def s07() -> str:
        r = val.validate_file(vaultfix / "nofm.md")
        return f"is_valid={r.is_valid}\n{issues_breve(r)}"

    def s08() -> str:
        r = val.validate_file(vaultfix / "ok.md")
        claves = sorted(r.properties.keys())
        return (
            f"is_valid={r.is_valid}\nprops_keys={claves}\n"
            f"title={r.properties.get('title')}\ntags={r.properties.get('tags')}\n"
            f"wikilinks={sorted(r.wikilinks)}\nembeds={sorted(r.embeds)}\n"
            f"errors={len(r.errors)} warnings={len(r.warnings)}"
        )

    def s09() -> str:
        r = val.validate_file(vaultfix / "broken.md")
        return (
            f"is_valid={r.is_valid}\nwikilinks={sorted(r.wikilinks)}\n"
            f"embeds={sorted(r.embeds)}\n{issues_breve(r)}"
        )

    def s10() -> str:
        r = val.validate_file(vaultfix / "badyaml.md")
        breve = "; ".join(
            f"{i.severity}|{i.field}|"
            + ("{{YAML_ERR}}" if i.message.startswith("Invalid YAML") else i.message)
            for i in r.issues
        )
        return f"is_valid={r.is_valid}\n{breve}"

    def s11() -> str:
        r_partial = val.validate_file(vaultfix / "partial.md")
        return f"is_valid={r_partial.is_valid}\n{issues_breve(r_partial)}"

    ver = DocVerifier(vault_path=vaultfix, root=work)

    def s12() -> str:
        files = [
            "vaultfix/nuevo.md",
            "vaultfix/editado.md",
            "vaultfix/borrado.md",
            "vaultfix/nota.txt",
            "fuera/f.md",
            "vaultfix/",
        ]
        r = ver.verify_from_list(files)
        return r.to_json()

    def s13() -> str:
        cwd_previo = Path.cwd()
        os.chdir(work)  # sin repo git
        try:
            r = ver.verify_from_diff("main")
        finally:
            os.chdir(cwd_previo)
        return r.to_json()

    def s14() -> str:
        # vault RELATIVO no bajo root ⇒ relative_to falla ⇒ error.
        ver2 = DocVerifier(vault_path="elsewhere/vault", root=work)
        r = ver2.verify_from_list(["x.md"])
        return r.to_json()

    escenarios = [s01, s02, s03, s04, s05, s06, s07, s08, s09, s10, s11, s12, s13, s14]
    titulos = [
        "S01 session completa",
        "S02 session vacía",
        "S03 safe_filename edges",
        "S04 generate_all skip_types",
        "S05 write_docs archivos",
        "S06 validate inexistente",
        "S07 sin frontmatter",
        "S08 nota válida",
        "S09 embed roto",
        "S10 yaml inválido",
        "S11 fm parcial",
        "S12 verifier from_list",
        "S13 verifier git nonrepo",
        "S14 verifier vault fuera",
    ]
    for titulo, fn in zip(titulos, escenarios):
        emitir(titulo, fn)
    return "".join(bloques)


def normalizar(texto: str, work: Path) -> str:
    texto = texto.replace(str(work), "{{ROOT}}")
    if not texto.endswith("\n"):
        texto += "\n"
    return texto


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("build", "verify"):
        p = sub.add_parser(name)
        p.add_argument("--out", type=Path, default=REPO_ROOT / "bench/parity/golden_p12a4")
        p.add_argument("--fixtures", type=Path, default=None)
    ns = ap.parse_args()
    destino = ns.out / "golden_p12a4.txt"

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        construir_vault(base)
        contenido = normalizar(correr_secuencia(base), base)

        if ns.cmd == "verify":
            esperado = destino.read_text(encoding="utf-8")
            if contenido == esperado:
                print("[PASS] golden_p12a4.txt")
                print("\n✅ ORÁCULO DETERMINISTA (lado Python)")
                return 0
            print("[FAIL] golden_p12a4.txt difiere")
            for l in list(difflib.unified_diff(
                    esperado.splitlines(), contenido.splitlines(),
                    lineterm=""))[:60]:
                print(l)
            return 1

        ns.out.mkdir(parents=True, exist_ok=True)
        destino.write_text(contenido, encoding="utf-8")
        print(f"[capturado] {destino}")
        if ns.fixtures:
            import shutil

            if ns.fixtures.exists():
                shutil.rmtree(ns.fixtures)
            shutil.copytree(base, ns.fixtures)
            print(f"fixture reconstruido → {ns.fixtures}")
        print("\nVerificación Rust:")
        print(
            f"  cargo run -q -p cortex-app --example p12a4_check -- "
            f"<work_dir_con_vaultfix> {ns.out}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
