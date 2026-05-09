"""Tests for Autopilot skill assets and workspace integration."""
from __future__ import annotations

from pathlib import Path

import pytest

from cortex.ide.prompts import build_all_prompts, build_autopilot_prompts
from cortex.setup.cortex_workspace import (
    _autopilot_skills_dir,
    autopilot_file_map,
    ensure_cortex_workspace,
)


class TestAutopilotSkillFiles:
    """Validate the meta-skill content shipped in the package."""

    def test_using_cortex_autopilot_exists(self) -> None:
        path = _autopilot_skills_dir() / "using-cortex-autopilot.md"
        assert path.exists(), "using-cortex-autopilot.md must exist"

    def test_cortex_autopilot_finish_exists(self) -> None:
        path = _autopilot_skills_dir() / "cortex-autopilot-finish.md"
        assert path.exists(), "cortex-autopilot-finish.md must exist"

    def test_meta_skill_word_count_under_1500(self) -> None:
        path = _autopilot_skills_dir() / "using-cortex-autopilot.md"
        text = path.read_text(encoding="utf-8")
        words = len(text.split())
        assert words < 1500, f"Meta-skill is {words} words, must be < 1500"

    def test_meta_skill_has_anti_rationalization_table(self) -> None:
        path = _autopilot_skills_dir() / "using-cortex-autopilot.md"
        text = path.read_text(encoding="utf-8")
        assert "Senales de que estas saltando el flujo" in text
        assert '| "Es una pregunta simple, no necesito preflight"' in text

    def test_meta_skill_has_verification_rule(self) -> None:
        path = _autopilot_skills_dir() / "using-cortex-autopilot.md"
        text = path.read_text(encoding="utf-8")
        assert "Regla de verificacion" in text
        assert "Identifica que comando prueba tu afirmacion" in text
        assert "NO es aceptable:" in text

    def test_meta_skill_has_instruction_priority(self) -> None:
        path = _autopilot_skills_dir() / "using-cortex-autopilot.md"
        text = path.read_text(encoding="utf-8")
        assert "Prioridad de instrucciones" in text
        assert "El usuario tiene el control" in text

    def test_meta_skill_has_all_11_points(self) -> None:
        path = _autopilot_skills_dir() / "using-cortex-autopilot.md"
        text = path.read_text(encoding="utf-8")
        required_sections = [
            "Prioridad de instrucciones",
            "Regla de memoria",
            "Cuando activar preflight",
            "Cuando evitar preflight",
            "Presupuesto de contexto",
            "Regla de documentacion final",
            "Tracks",
            "Manejo de fallas de tool",
            "Senales de que estas saltando el flujo",
            "Regla de verificacion",
        ]
        for section in required_sections:
            assert section in text, f"Missing mandatory section: {section}"


class TestAutopilotFileMap:
    def test_returns_expected_files(self) -> None:
        files = autopilot_file_map()
        assert ".cortex/skills/using-cortex-autopilot.md" in files
        assert ".cortex/skills/cortex-autopilot-finish.md" in files
        for content in files.values():
            assert len(content) > 50


class TestEnsureCortexWorkspace:
    def test_normal_setup_does_not_install_autopilot_skills(self, tmp_path: Path) -> None:
        result = ensure_cortex_workspace(tmp_path, overwrite=True)
        created = result["created"]
        autopilot_files = [c for c in created if "autopilot" in c]
        assert not autopilot_files, "Normal setup must not install Autopilot skills"

    def test_autopilot_setup_installs_skills(self, tmp_path: Path) -> None:
        result = ensure_cortex_workspace(tmp_path, overwrite=True, autopilot=True)
        created = result["created"]
        assert ".cortex/skills/using-cortex-autopilot.md" in created
        assert ".cortex/skills/cortex-autopilot-finish.md" in created

    def test_skills_are_readable_after_install(self, tmp_path: Path) -> None:
        ensure_cortex_workspace(tmp_path, overwrite=True, autopilot=True)
        skill_path = tmp_path / ".cortex" / "skills" / "using-cortex-autopilot.md"
        assert skill_path.exists()
        assert "Prioridad de instrucciones" in skill_path.read_text(encoding="utf-8")


class TestPromptBuilders:
    def test_build_all_prompts_does_not_include_autopilot(self, tmp_path: Path) -> None:
        # Create a minimal workspace
        ensure_cortex_workspace(tmp_path, overwrite=True, autopilot=False)
        prompts = build_all_prompts(tmp_path)
        assert "using-cortex-autopilot" not in prompts
        assert "cortex-autopilot-finish" not in prompts

    def test_build_autopilot_prompts_returns_fallback_when_not_installed(self, tmp_path: Path) -> None:
        ensure_cortex_workspace(tmp_path, overwrite=True, autopilot=False)
        prompts = build_autopilot_prompts(tmp_path)
        assert "using-cortex-autopilot" in prompts
        assert "cortex-autopilot-finish" in prompts
        # Fallback message from get_skill_prompt
        assert "Skill file not found" in prompts["using-cortex-autopilot"]

    def test_build_autopilot_prompts_reads_installed_skills(self, tmp_path: Path) -> None:
        ensure_cortex_workspace(tmp_path, overwrite=True, autopilot=True)
        prompts = build_autopilot_prompts(tmp_path)
        assert "Prioridad de instrucciones" in prompts["using-cortex-autopilot"]
        assert "Cuando usar" in prompts["cortex-autopilot-finish"]
