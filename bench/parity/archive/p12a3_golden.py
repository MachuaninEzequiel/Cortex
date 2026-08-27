#!/usr/bin/env python3
"""Oráculo de paridad P12A-3 — pr_capture + models.PRContext + PRService.

Espeja tests/unit/pr/test_pr_context.py sobre los portes nativos:
  S01 save_context de PRContext mínimo → JSON pydantic byte-a-byte
  S02 save_context de PRContext completo (unicode/listas/options)
  S03 hu_references (comparado como conjunto ORDENADO — Python usa set())
  S04/S05/S06 has_db_changes / has_api_changes / has_adr_label
  S07 capture_manual en cwd SIN repo (ruta git ⇒ vacía, determinista)
  S08 capture_from_github con env fijo en cwd sin repo
  S09 detectores directos (_detect_db_migrations/_detect_api_changes)
  S10 enrich_with_pipeline (inmutabilidad del original)
  S11 PRService.store_pr_context → payload del sink (fake episódico)
  S12 roundtrip save→load→save (bytes idénticos)

Uso:
  python p12a3_golden.py build --out bench/parity/golden_p12a3
  python p12a3_golden.py verify --out bench/parity/golden_p12a3

Lado Rust:
  cargo run -q -p cortex-app --example p12a3_check -- <golden_dir>

Normalizaciones pactadas:
  - Los escenarios corren en un tmp SIN repo git ⇒ las llamadas git de la
    captura devuelven vacío en AMBOS lados (misma ruta de código).
  - hu_references: orden no es contrato (set() de Python); se emite sorted.
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))


# ── fake episódico espejo de p12a2 ──────────────────────────────────────────


class _FakeEpisodic:
    def __init__(self) -> None:
        self.llamadas: list[dict] = []

    def add(self, *, content, memory_type, tags, files, extra_metadata):
        self.llamadas.append({
            "content": content,
            "memory_type": memory_type,
            "tags": list(tags),
            "files": list(files),
            "extra_metadata": dict(extra_metadata or {}),
        })
        return None


def correr_secuencia(work: Path) -> str:
    """Escenarios sobre cwd sin repo; devuelve el reporte crudo."""
    from cortex.models import PRContext
    from cortex.pr_capture import (
        _detect_api_changes,
        _detect_db_migrations,
        capture_from_github,
        capture_from_json,
        capture_manual,
        enrich_with_pipeline,
        save_context,
    )
    from cortex.services.pr_service import PRService

    bloques: list[str] = []

    def emitir(titulo: str, fn) -> None:
        try:
            salida = fn()
            bloques.append(f"### {titulo}\nrc=0\n{salida}")
        except Exception as exc:  # noqa: BLE001 - el mensaje ES el contrato
            bloques.append(f"### {titulo}\nrc=1\n{type(exc).__name__}: {exc}")

    vault = work / "vault"

    # ── S01/S02: JSON pydantic byte-a-byte ──
    def s01() -> str:
        ctx = PRContext(
            title="Fix login bug",
            author="dev1",
            source_branch="fix/login",
            commit_sha="abc123",
        )
        assert ctx.target_branch == "main"
        assert ctx.files_changed == []
        assert ctx.labels == []
        path = save_context(ctx, work / "ctx_min.json")
        return path.read_text(encoding="utf-8")

    def s02() -> str:
        ctx = PRContext(
            pr_number=42,
            title="Implementar búsqueda semántica",
            body="Cuerpo con acentos: búsqueda\ny salto de línea",
            author="chucho",
            source_branch="feature/hu-42",
            target_branch="develop",
            commit_sha="deadbeefcafe",
            files_changed=["src/routes/users.js", "migrations/001.sql"],
            diff_summary=" src/routes/users.js | 10 ++++\n 1 file changed",
            labels=["rag", "backend"],
            lint_result="pass",
        )
        path = save_context(ctx, work / "ctx_full.json")
        return path.read_text(encoding="utf-8")

    def s03() -> str:
        ctx = PRContext(
            title="Implement HU-42",
            body=(
                "This PR addresses HU-42 and also references HU-100. "
                "Related to #200, hu-7 y us-9."
            ),
            author="dev1",
            source_branch="feature/hu-42",
            commit_sha="abc123",
        )
        return "\n".join(sorted(ctx.hu_references()))

    def s04() -> str:
        con = PRContext(
            title="Add migration",
            author="dev1",
            source_branch="feature/db",
            commit_sha="abc123",
            files_changed=["migrations/001_add_users.sql", "src/app.js"],
        )
        sin = PRContext(
            title="Fix typo",
            author="dev1",
            source_branch="fix/typo",
            commit_sha="abc123",
            files_changed=["README.md"],
        )
        return f"con={con.has_db_changes()}\nsin={sin.has_db_changes()}"

    def s05() -> str:
        con = PRContext(
            title="Add endpoint",
            author="dev1",
            source_branch="feature/api",
            commit_sha="abc123",
            files_changed=["src/routes/users.js", "src/controllers/users.js"],
        )
        sin = PRContext(
            title="Fix CSS",
            author="dev1",
            source_branch="fix/css",
            commit_sha="abc123",
            files_changed=["src/styles/main.css"],
        )
        return f"con={con.has_api_changes()}\nsin={sin.has_api_changes()}"

    def s06() -> str:
        con = PRContext(
            title="Architecture change",
            author="dev1",
            source_branch="feature/arch",
            commit_sha="abc123",
            labels=["adr", "breaking"],
        )
        sin = PRContext(
            title="Small fix",
            author="dev1",
            source_branch="fix/small",
            commit_sha="abc123",
            labels=["bugfix"],
        )
        return f"con={con.has_adr_label()}\nsin={sin.has_adr_label()}"

    def s07() -> str:
        ctx = capture_manual(
            title="Test PR",
            author="dev1",
            branch="test",
            commit="abc123",
            body="Fixed the refresh token issue",
        )
        return (
            f"title={ctx.title}\nauthor={ctx.author}\nbranch={ctx.source_branch}\n"
            f"body={ctx.body}\ntarget={ctx.target_branch}\nfiles={ctx.files_changed}\n"
            f"diff={ctx.diff_summary!r}"
        )

    def s08() -> str:
        env_fijo = {
            "PR_NUMBER": "7",
            "PR_TITLE": "Env captured PR",
            "PR_BODY": "cuerpo con acentos: búsqueda",
            "PR_AUTHOR": "alice",
            "PR_BRANCH": "feature/env",
            "TARGET_BRANCH": "develop",
            "PR_COMMIT": "deadbeef",
            "PR_LABELS": "ci, deploy",
        }
        previos = {k: os.environ.get(k) for k in env_fijo}
        os.environ.update(env_fijo)
        try:
            ctx = capture_from_github()
        finally:
            for k, v in previos.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        return (
            f"number={ctx.pr_number}\ntitle={ctx.title}\nauthor={ctx.author}\n"
            f"source={ctx.source_branch}\ntarget={ctx.target_branch}\n"
            f"commit={ctx.commit_sha}\nlabels={sorted(ctx.labels)}\n"
            f"files={ctx.files_changed}"
        )

    def s09() -> str:
        db_files = ["migrations/001.sql", "src/app.js", "schema.sql"]
        api_files = ["src/routes/users.js", "src/controllers/auth.js", "README.md"]
        return (
            f"db={json.dumps(_detect_db_migrations(db_files))}\n"
            f"api={json.dumps(_detect_api_changes(api_files))}"
        )

    def s10() -> str:
        ctx = capture_manual(
            title="Test PR",
            author="dev1",
            branch="test",
            commit="abc123",
        )
        enriched = enrich_with_pipeline(
            ctx,
            lint_result="pass",
            audit_result="fail: 2 high vulnerabilities",
            test_result="pass",
        )
        return (
            f"enriched_lint={enriched.lint_result}\n"
            f"enriched_audit={enriched.audit_result}\n"
            f"enriched_test={enriched.test_result}\n"
            f"original_lint={ctx.lint_result}"
        )

    def s11() -> str:
        ep = _FakeEpisodic()
        svc = PRService(
            vault_path=vault,
            episodic=ep,
            context_metadata={"workspace": "obra07"},
        )
        ctx = PRContext(
            pr_number=42,
            title="Fix login bug",
            body="refresh token",
            author="dev1",
            source_branch="fix/login",
            target_branch="main",
            commit_sha="abc123def456",
            diff_summary=" src/main.py | 2 +-\n 1 file changed",
            files_changed=[f"f{i}.py" for i in range(30)],
            labels=["bugfix"],
        )
        svc.store_pr_context(ctx, lint_result="pass", test_result="pass")
        return json.dumps(
            {"episodico": ep.llamadas}, indent=1, ensure_ascii=False, sort_keys=True
        )

    def s12() -> str:
        ctx = PRContext(
            pr_number=9,
            title="Roundtrip",
            body="ida y vuelta",
            author="dev1",
            source_branch="rt",
            commit_sha="ffeeddcc",
            labels=["rt"],
        )
        p1 = save_context(ctx, work / "rt1.json")
        loaded = capture_from_json(p1)
        p2 = save_context(loaded, work / "rt2.json")
        iguales = p1.read_bytes() == p2.read_bytes()
        return (
            f"iguales={iguales}\n"
            f"title={loaded.title}\nlabels={loaded.labels}\npr_number={loaded.pr_number}"
        )

    escenarios = [s01, s02, s03, s04, s05, s06, s07, s08, s09, s10, s11, s12]
    titulos = [
        "S01 json mínimo",
        "S02 json completo",
        "S03 hu_references",
        "S04 has_db_changes",
        "S05 has_api_changes",
        "S06 has_adr_label",
        "S07 capture_manual sin repo",
        "S08 capture_from_github env",
        "S09 detectores directos",
        "S10 enrich inmutabilidad",
        "S11 PRService.store_pr_context",
        "S12 roundtrip json",
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
        p.add_argument("--out", type=Path, default=REPO_ROOT / "bench/parity/golden_p12a3")
    ns = ap.parse_args()
    destino = ns.out / "golden_p12a3.txt"

    # Limpiar variables que puedan filtrarse del entorno anfitrión.
    for k in ("PR_NUMBER", "PR_TITLE", "PR_BODY", "PR_AUTHOR", "PR_BRANCH",
              "TARGET_BRANCH", "PR_COMMIT", "PR_LABELS",
              "GITHUB_HEAD_REF", "GITHUB_BASE_REF", "GITHUB_SHA"):
        os.environ.pop(k, None)

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        cwd_previo = Path.cwd()
        os.chdir(work)  # sin repo git ⇒ capturas deterministas
        try:
            contenido = normalizar(correr_secuencia(work), work)
        finally:
            os.chdir(cwd_previo)

        if ns.cmd == "verify":
            esperado = destino.read_text(encoding="utf-8")
            if contenido == esperado:
                print("[PASS] golden_p12a3.txt")
                print("\n✅ ORÁCULO DETERMINISTA (lado Python)")
                return 0
            print("[FAIL] golden_p12a3.txt difiere")
            for l in list(difflib.unified_diff(
                    esperado.splitlines(), contenido.splitlines(),
                    lineterm=""))[:60]:
                print(l)
            return 1

        ns.out.mkdir(parents=True, exist_ok=True)
        destino.write_text(contenido, encoding="utf-8")
        print(f"[capturado] {destino}")
        print("\nVerificación Rust:")
        print(f"  cargo run -q -p cortex-app --example p12a3_check -- {ns.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
