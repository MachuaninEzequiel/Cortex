"""Gate de Fase B: `cortex next` corre <2s y expone JSON/explain-why-not."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

from typer.testing import CliRunner

from cortex.cli.main import app

runner = CliRunner()


def _repo_mediano(tmp_path: Path) -> Path:
    """Repo con config + vault con ~50 docs (mediano, determinista)."""
    dot = tmp_path / ".cortex"
    dot.mkdir(parents=True)
    config = dot / "config.yaml"
    config.write_text(
        "episodic:\n"
        "  persist_dir: .memory/chroma\n"
        "  collection_name: cortex_episodic\n"
        "  embedding_model: all-MiniLM-L6-v2\n"
        "  embedding_backend: onnx\n"
        "semantic:\n"
        "  vault_path: vault\n",
        encoding="utf-8",
    )
    decisions = dot / "vault" / "decisions"  # layout canónico: .cortex/vault
    decisions.mkdir(parents=True)
    for i in range(1, 51):
        (decisions / f"ADR-{i:03d}-demo.md").write_text(
            f"---\ntitle: ADR {i}\ndoc_type: adr\nstatus: accepted\n---\n\n"
            f"# ADR {i}\n\n" + "contenido determinista " * 20,
            encoding="utf-8",
        )
    return tmp_path


class TestCortexNext:
    def test_gate_menos_de_2_segundos_en_repo_mediano(self, tmp_path: Path) -> None:
        repo = _repo_mediano(tmp_path)

        t0 = time.perf_counter()
        proc = subprocess.run(
            [sys.executable, "-m", "cortex.cli.main", "next", "--project-root", str(repo)],
            capture_output=True, text=True, timeout=60,
        )
        elapsed = time.perf_counter() - t0

        assert proc.returncode == 0, proc.stderr
        assert elapsed < 2.0, f"cortex next tardó {elapsed:.2f}s — gate Fase B es <2s"

    def test_json_maquina_legible(self, tmp_path: Path) -> None:
        repo = _repo_mediano(tmp_path)
        resultado = runner.invoke(
            app, ["next", "--json", "--project-root", str(repo)]
        )
        assert resultado.exit_code == 0, resultado.output
        payload = json.loads(resultado.output)

        assert "acciones" in payload and "elapsed_ms" in payload
        ids = {a["id"] for a in payload["acciones"]}
        assert "vault.validate_docs" in ids  # hay docs que validar
        assert all("score" in a and "effect" in a for a in payload["acciones"])

    def test_explain_why_not_explica_faltantes(self, tmp_path: Path) -> None:
        repo = _repo_mediano(tmp_path)
        resultado = runner.invoke(
            app,
            ["next", "--json", "--explain-why-not", "--project-root", str(repo)],
        )
        assert resultado.exit_code == 0
        payload = json.loads(resultado.output)

        why_not = payload["why_not"]
        assert isinstance(why_not, dict) and why_not
        # setup.finish_bootstrap no aparece: el config YA existe en este repo
        assert "config.yaml" in " ".join(why_not.get("setup.finish_bootstrap", []))

    def test_preferencia_never_suprime(self, tmp_path: Path) -> None:
        repo = _repo_mediano(tmp_path)
        (repo / ".cortex" / "actions.yaml").write_text(
            "acciones:\n"
            "  vault.validate_docs:\n"
            "    never: true\n"
            "    skips: 0\n"
            "    accepts: 0\n",
            encoding="utf-8",
        )
        resultado = runner.invoke(app, ["next", "--json", "--project-root", str(repo)])
        payload = json.loads(resultado.output)
        ids = {a["id"] for a in payload["acciones"]}
        assert "vault.validate_docs" not in ids

    def test_sin_config_sale_con_error_claro(self, tmp_path: Path) -> None:
        vacio = tmp_path / "vacio"
        vacio.mkdir()
        resultado = runner.invoke(
            app, ["next", "--project-root", str(vacio)]
        )
        assert resultado.exit_code == 1
        assert "no está configurado" in resultado.output or "No encuentro" in resultado.output
