# Estructura — `cortex/ide`

## Para qué existe esta carpeta

cortex.ide ---------- IDE adapter layer for Cortex agent profile injection.

## Árbol interno (código, sin `__pycache__`)

```
ide/
├── adapters/
│   ├── __init__.py
│   ├── antigravity.py
│   ├── claude_code.py
│   ├── claude_desktop.py
│   ├── codex.py
│   ├── cursor.py
│   ├── hermes.py
│   ├── opencode.py
│   ├── pi.py
│   ├── vscode.py
│   ├── windsurf.py
│   └── zed.py
├── __init__.py
├── base.py
├── canonical_tools.py
├── prompts.py
└── registry.py
```

## Archivos Python cubiertos aquí

| Archivo | Líneas | Síntesis observada |
|---|---:|---|
| `cortex/ide/__init__.py` | 162 | cortex.ide ---------- IDE adapter layer for Cortex agent profile injection. |
| `cortex/ide/adapters/__init__.py` | 6 | cortex.ide.adapters ------------------- IDE-specific adapters for Cortex profile injection. |
| `cortex/ide/adapters/antigravity.py` | 176 | AntigravityAdapter, _unique_backup |
| `cortex/ide/adapters/claude_code.py` | 477 | ClaudeCodeAdapter, _render_claude_markdown, _parse_canonical_tools, _claude_workflow_doc |
| `cortex/ide/adapters/claude_desktop.py` | 114 | ClaudeDesktopAdapter |
| `cortex/ide/adapters/codex.py` | 624 | cortex.ide.adapters.codex — Codex CLI adapter. |
| `cortex/ide/adapters/cursor.py` | 366 | cortex.ide.adapters.cursor — Cursor IDE adapter. |
| `cortex/ide/adapters/hermes.py` | 133 | HermesAdapter |
| `cortex/ide/adapters/opencode.py` | 281 | OpenCodeAdapter |
| `cortex/ide/adapters/pi.py` | 328 | PiAdapter, _default_pi_bundle_dir |
| `cortex/ide/adapters/vscode.py` | 221 | VSCodeAdapter, _render_vscode_agent, _render_claude_agent |
| `cortex/ide/adapters/windsurf.py` | 171 | WindsurfAdapter, _unique_backup |
| `cortex/ide/adapters/zed.py` | 115 | ZedAdapter |
| `cortex/ide/base.py` | 417 | cortex.ide.base --------------- Abstract base class for IDE adapters. |
| `cortex/ide/canonical_tools.py` | 325 | cortex.ide.canonical_tools -------------------------- Vocabulario canonico de tools de Cortex y matriz de traduccion por IDE. |
| `cortex/ide/prompts.py` | 142 | cortex.ide.prompts ------------------ Centralized prompt generation for Cortex agent profiles. |
| `cortex/ide/registry.py` | 191 | cortex.ide.registry ------------------- Auto-discovery and registration of IDE adapters. |

## Relaciones de la carpeta

### Recibe de (unión de imports `cortex.*` de los módulos de este nivel)

- `cortex.ide.prompts`
- `cortex.ide.registry`
- `cortex.workspace.layout`

### Envía a (módulos `cortex.*` que importan a este nivel)

- `cortex.cli._setup_helpers`
- `cortex.cli.ide`
- `cortex.ide`
- `cortex.ide.adapters.antigravity`
- `cortex.ide.adapters.claude_code`
- `cortex.ide.adapters.claude_desktop`
- `cortex.ide.adapters.codex`
- `cortex.ide.adapters.cursor`
- `cortex.ide.adapters.hermes`
- `cortex.ide.adapters.opencode`
- `cortex.ide.adapters.pi`
- `cortex.ide.adapters.vscode`
- `cortex.ide.adapters.windsurf`
- `cortex.ide.adapters.zed`

---
Fuente: árbol de `cortex/` + AST de imports. No se usó documentación previa.
