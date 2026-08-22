"""Test de sincronía workspace_files (deuda V8, Obra 01 fase P7).

Los contenidos que ``cortex setup`` escribe en ``.cortex/`` (skills,
subagents, system prompt, obsidian) vivían como strings embebidos en
``cortex_workspace.py`` (~1400 líneas) sin fuente externa. Ahora son
archivos reales en ``cortex/setup/workspace_files/`` y los renderers
solo LEEN. Este test congela esa relación y valida invariantes de
frontmatter para que ningún archivo quede roto.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cortex.setup import cortex_workspace as cw

FILES_DIR = Path(cw.__file__).resolve().parent / "workspace_files"

RENDERERS = {
    "render_system_prompt": "system-prompt.md",
    "render_agent_overview": "agent-overview.md",
    "render_cortex_sync_skill": "cortex-sync.md",
    "render_cortex_sddwork_skill": "cortex-SDDwork.md",
    "render_cortex_documenter_skill": "cortex-documenter.md",
    "render_subagent_explorer": "subagent-cortex-code-explorer.md",
    "render_subagent_implementer": "subagent-cortex-code-implementer.md",
    "render_subagent_documenter": "subagent-cortex-documenter.md",
    "render_subagent_designer": "subagent-cortex-code-designer.md",
}

OBSIDIAN_VARS = [
    "obsidian_markdown",
    "obsidian_bases",
    "json_canvas",
    "defuddle",
    "obsidian_index",
]


class TestFuenteUnica:
    def test_todos_los_archivos_existen_y_no_son_vacios(self) -> None:
        for archivo in set(RENDERERS.values()) | {
            f"obsidian-{v}.md" for v in OBSIDIAN_VARS
        }:
            ruta = FILES_DIR / archivo
            assert ruta.is_file(), f"falta {archivo}"
            assert ruta.read_text(encoding="utf-8").strip(), f"{archivo} vacío"

    @pytest.mark.parametrize("renderer,archivo", sorted(RENDERERS.items()))
    def test_render_lee_exactamente_el_archivo(self, renderer: str, archivo: str) -> None:
        assert getattr(cw, renderer)() == (FILES_DIR / archivo).read_text(encoding="utf-8")

    def test_workspace_file_map_consistente(self) -> None:
        """El mapa que instala .cortex/ no debe perder entradas ni contenido."""
        mapa = cw.workspace_file_map()
        assert ".cortex/skills/cortex-sync.md" in mapa
        assert ".cortex/subagents/cortex-code-designer.md" in mapa
        assert all(v.strip() for k, v in mapa.items() if not k.endswith(".gitkeep"))

    def test_obsidian_skills_desde_archivos(self) -> None:
        obs = cw._obsidian_skill_files()
        assert len(obs) == 5
        for var in OBSIDIAN_VARS:
            esperado = (FILES_DIR / f"obsidian-{var}.md").read_text(encoding="utf-8")
            assert esperado in obs.values()


@pytest.mark.parametrize(
    "archivo",
    ["cortex-sync.md", "cortex-SDDwork.md", "cortex-documenter.md"],
)
def test_skills_con_frontmatter_valido(archivo: str) -> None:
    texto = (FILES_DIR / archivo).read_text(encoding="utf-8")
    assert texto.startswith("---\n")
    cierre = texto.index("\n---", 4)
    frontmatter = texto[4:cierre]
    assert "name:" in frontmatter
    assert "description:" in frontmatter
