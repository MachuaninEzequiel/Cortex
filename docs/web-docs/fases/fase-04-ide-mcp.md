---
title: Fase 04 — Integraciones IDE y MCP
doc_type: phase
phase: 4
status: pending
depends_on: [phase-03]
unlocks: [phase-05]
estimated_duration: 4 días-persona
---

# Fase 04 — Integraciones IDE y MCP

## Objetivo

Documentar la integración con cada IDE soportado por Cortex de forma exhaustiva. Cada guía debe permitirle a un usuario configurar Cortex con su IDE preferido **sin abrir un ticket**.

IDEs soportados:

1. **Pi Coding Agent** (recomendado por Cortex)
2. **Claude Code** (CLI de Anthropic)
3. **Cursor**
4. **VSCode + Cline/Roo**
5. **OpenCode**
6. **Codex**

## Entregables

### Sección `/ide/` — 7 páginas

| Slug | Contenido |
| --- | --- |
| `ide/overview` | Comparativa, cuándo elegir cuál |
| `ide/pi` | Setup Pi completo (recomendado) |
| `ide/claude-code` | Setup Claude Code |
| `ide/cursor` | Setup Cursor |
| `ide/vscode` | Setup VSCode + Cline/Roo |
| `ide/opencode` | Setup OpenCode |
| `ide/codex` | Setup Codex |

### Estructura de página IDE

Cada página por IDE sigue esta plantilla:

```mdx
---
title: Cortex + {IDE}
doc_type: how-to
summary: |
  Cómo configurar Cortex con {IDE} y usar memoria híbrida en tu agente.
section: ide
audience: [developer]
tags: [ide, {ide-slug}, mcp, integration]
since_version: 0.x.0
last_review: 2026-05-14
status: stable
---

## Introducción

{IDE} es {breve descripción}. Esta guía te muestra cómo conectar Cortex.

## Prerrequisitos

- {IDE} instalado.
- Cortex instalado: ver [Quickstart](../getting-started/installation).
- Tu proyecto inicializado: `cortex setup full`.

## Instalación rápida

```bash data-runnable
cortex inject --ide {ide-slug}
```

Esto:

- Crea `{archivo-config-ide}` con la configuración MCP.
- Inyecta `{archivos-prompt}` con system prompts.
- Verifica conectividad.

## Verificación

1. Abrí {IDE}.
2. En el chat/prompt, preguntá: "¿Qué tools de Cortex tenés disponibles?"
3. Deberías ver: `cortex_search`, `cortex_create_spec`, `cortex_save_session`, etc.

## Configuración manual (si la auto falla)

Crear `{archivo-config}` con:

```json
{
  "mcpServers": {
    "cortex": {
      "command": "python",
      "args": ["-m", "cortex.cli.main", "mcp-server", "--project-root", "{path}"]
    }
  }
}
```

## Flujo de trabajo típico

1. Pedile al agente: "Buscá en memoria 'auth jwt'" → llama `cortex_search`.
2. Pedile: "Creá spec para feature X" → llama `cortex_create_spec`.
3. Al final: "Guardá session" → llama `cortex_save_session`.

## Tips específicos {IDE}

- {Tip 1}
- {Tip 2}

## Troubleshooting

<Callout type="warning">
Si el servidor MCP no se conecta...
</Callout>

- Error: `MCP server not responding` → verificá que Python está en PATH.
- Error: `Tools not visible` → reiniciá {IDE}.

## Limitaciones

- {Limitación 1}
- {Limitación 2}

## Recursos

- [{IDE} docs oficial]({link})
- [MCP protocol overview](../mcp/overview)
```

## Detalle por IDE

### `ide/pi.mdx`

- Es el **recomendado** por Cortex.
- Incluir:
  - Setup `npm install -g @mariozechner/pi-coding-agent`.
  - Setup `just` (task runner): brew/winget/scoop.
  - Uso de `just cortex`, `just sdd`, `just hotfix`, `just audit`.
  - Lista de teams disponibles (`cortex-sddwork`, `cortex-hotfix`, `cortex-research`, `cortex-audit`).
  - Estructura de `cortex-pi/` (agents, skills, teams).
  - Filosofía de Pi: Intelligent Routing, gobernanza 5 capas.
- Section dedicada a la **Gobernanza Total con Handoffs Verificables** (0.5.0).

### `ide/claude-code.mdx`

- Setup `cortex inject --ide claude-code`.
- Archivo generado: `.claude/mcp.json`.
- `CLAUDE.md` con system prompt.
- Cómo invocar tools desde Claude Code (`@cortex_search ...`).
- Tips específicos: usar `/cortex-save` como atajo.

### `ide/cursor.mdx`

- Setup vía `Settings → MCP → Add Server`.
- O `cortex inject --ide cursor`.
- Archivo `.cursor/mcp.json`.

### `ide/vscode.mdx`

- VSCode no tiene MCP nativo; usar **Cline** o **Roo**.
- `.vscode/mcp.json` config.
- Diferencias Cline vs Roo brevemente.

### `ide/opencode.mdx` y `ide/codex.mdx`

- Setups equivalentes.
- Archivos `.opencode/mcp.json` y `.codex/mcp.json`.

### `ide/overview.mdx`

Tabla comparativa:

| Feature | Pi (recomendado) | Claude Code | Cursor | VSCode (Cline) | OpenCode | Codex |
| --- | --- | --- | --- | --- | --- | --- |
| MCP nativo | ✅ | ✅ | ✅ | ⚠️ (vía extensión) | ✅ | ✅ |
| Skills inyectables | ✅ | ⚠️ | ⚠️ | ❌ | ⚠️ | ⚠️ |
| Teams pre-config | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Intelligent Routing | ✅ | ⚠️ via Autopilot | ⚠️ idem | ⚠️ idem | ⚠️ idem | ⚠️ idem |
| Setup time | 5 min | 2 min | 2 min | 5 min | 2 min | 2 min |

## Cobertura MCP cruzada

Cada página IDE debe linkear a `/mcp/overview` y a `/mcp/integration-guide`.

`/mcp/integration-guide.mdx` (escrito en Fase 03) actúa como **referencia neutral** que cada IDE-specific page complementa con detalles concretos.

## Tareas detalladas

### 4.1 Overview (0.5 día)

- [ ] Página `ide/overview.mdx` con tabla comparativa.
- [ ] Cards a cada IDE.
- [ ] Recomendación clara: "Si dudás, Pi".

### 4.2 Pi guide (1 día — la más larga)

- [ ] Reutilizar contenido de `docs/guides/ide-pi.md`.
- [ ] Cubrir:
  - Instalación Pi + just.
  - `cortex inject --ide pi`.
  - Estructura cortex-pi/.
  - Teams disponibles.
  - Modos: Fast Track, Deep Track, Forced SDD.
  - Damage control rules.
  - Tripartita Refinada (handoffs verificables).

### 4.3 Claude Code, Cursor, VSCode, OpenCode, Codex (2 días, 5 guides)

- [ ] Una por una con plantilla.
- [ ] Reutilizar `docs/guides/ide-*.md` cuando exista.
- [ ] Cada uno con screenshot real del IDE mostrando tools de Cortex disponibles.

### 4.4 Screenshots (0.5 día)

- [ ] Capturar screenshots de cada IDE post-inyección, mostrando:
  - Tools de Cortex en la lista.
  - Ejemplo de invocación.
  - Output formateado.
- [ ] Guardar en `apps/docs/public/screenshots/ide/{ide-slug}/`.
- [ ] Variantes dark/light si el IDE permite.

## Criterios de aceptación

- ✅ Las 7 páginas de IDE completas.
- ✅ Cada IDE tiene troubleshooting section con ≥ 3 issues comunes.
- ✅ Screenshots actualizados.
- ✅ Linkcheck verde.
- ✅ Coverage MCP 100%.
- ✅ Tester real (3 usuarios diferentes) puede configurar su IDE siguiendo solo la doc.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| IDE cambia UI y screenshots envejecen | Plan de re-captura trimestral; en metadata `screenshots_taken_at` |
| Cortex agrega o quita soporte de IDE | Schema page tiene `since` y `deprecated_in` para gestión |
| Comando `cortex inject --ide X` falla en CI | Tests E2E con Docker containers de cada IDE (parcial) |

## Siguiente fase

→ [Fase 05 — Tutoriales y cookbooks](fase-05-tutoriales-cookbooks.md)
