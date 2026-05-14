---
title: Cortex + Pi Coding Agent — guía para adopters
date: 2026-05-13
status: target IDE (oficialmente soportado, recomendado por Cortex)
---

# Cortex con Pi Coding Agent

[Pi Coding Agent](https://github.com/mariozechner/pi-coding-agent) es el **entorno recomendado por Cortex** y uno de los 4 IDEs target oficiales. A diferencia de los otros IDEs, Pi trae **infraestructura propia** dentro del repo (`cortex-pi/`), incluyendo extensiones TypeScript, justfile, themes y skills específicas.

## Prerrequisitos

- Node.js 18+ con npm.
- Python 3.10+.
- [Just](https://github.com/casey/just) (task runner) — Mac: `brew install just`; Windows: `winget install Casey.Just`; Linux: `cargo install just`.
- (Opcional) [Bun](https://bun.sh) para correr las extensiones TypeScript de Pi sin compilación previa.
- Cortex instalado: `pipx install --editable C:\ruta\al\repo\Cortex` (o equivalente).

Instalar Pi globalmente:

```bash
npm install -g @mariozechner/pi-coding-agent
pi --version  # verificación
```

## Setup en tu repo

```bash
cd /ruta/a/tu/repo
cortex setup full --ide pi --git-depth 5
cortex doctor --scope all
```

Esto:

1. Crea el `.cortex/` estándar (workspace cognitivo).
2. Copia **todo el contenido de `cortex-pi/`** al root de tu proyecto. Eso incluye:
   - `.pi/` — directorio que Pi reconoce nativamente, con `mcp.json`, `settings.json`, `system.md`, `damage-control-rules.yaml`, agents (9 archivos), skills, extensions, themes.
   - `AGENTS.md` — gobernanza global del proyecto (Release 2.5: tripartito + 5-layer governance).
   - `justfile` — task runner con los 4 modos principales.
   - `extensions/` — extensiones TypeScript (dashboard, memory widget, spec tracker, subagent widget).
   - `README.md` — documentación de uso Pi-específica.

**Importante:** si tu proyecto ya tiene un `AGENTS.md` o `justfile` propio, hacé backup antes de correr el setup — Cortex hace backup automático con timestamp pero conviene revisar el resultado.

## Verificación

```bash
cortex doctor                # verde general
which pi                     # confirma que Pi está en PATH
just --list                  # lista los comandos disponibles
```

## Uso

Pi expone 4 modos principales vía `just`:

| Comando | Modo | Cuándo usarlo |
|---------|------|---------------|
| `just cortex` | Normal | Day-to-day. Carga `system-select` + `agent-chain` + `damage-control`. |
| `just sdd` | SDDwork completo | Feature compleja end-to-end (sync → SDDwork → explorer → implementer → security → test → documenter). |
| `just hotfix` | Fast Track | Fix urgente. Saltea explorer/implementer y va directo a SDDwork → security → test → documenter. |
| `just audit` | Quality | Sin implementar, solo: sync → explorer → security → test → documenter. |

Los **teams** se definen en `.pi/agents/teams.yaml`. La cadena de delegación entre subagents está en `.pi/agents/agent-chain.yaml`. Las reglas de damage control viven en `.pi/damage-control-rules.yaml`.

### MCP server

Pi NO usa el adapter MCP de Cortex de la misma forma que Claude Code / OpenCode / Codex. En su lugar usa el bridge nativo de Pi al servidor MCP de Cortex via `pipx-bin:cortex-memory:cortex`, configurado en `.pi/mcp.json`. La env var `CORTEX_CONFIG_PATH=${cwd}/config.yaml` queda definida automáticamente.

### Modo autonomo (Autopilot)

```bash
cortex autopilot install --ide pi
```

Esto instala la extensión `.pi/extensions/cortex-autopilot.ts` y la skill `using-cortex-autopilot/SKILL.md`. El doctor verifica su presencia.

## Diferencias clave con los otros 3 IDEs target

| Aspecto | Claude Code / OpenCode / Codex | Pi |
|---------|--------------------------------|-----|
| Subagents | 3 (explorer, implementer, documenter) en `.cortex/subagents/` | 9 en `.pi/agents/` (incluye security-auditor, test-verifier, sync, SDDwork como agentes propios) |
| Extension model | Profile / skills / MCP | Extensiones TypeScript + skills + agents + themes |
| Orchestration | Vía Cortex MCP guard | Vía `agent-chain.yaml` + `just` |
| Damage control | Vía MCP governance violations | `.pi/damage-control-rules.yaml` |

Los 3 subagents que están duplicados entre `.cortex/subagents/` y `.pi/agents/` pueden tener pequeños drift por encoding o EOL — son aceptablemente compatibles. Si editás uno, considerá editar el otro a mano (o usar `cortex inject --ide pi` para regenerar la copia Pi-side desde el canonical de `cortex-pi/`).

## Troubleshooting

**`just cortex` falla con "pi: command not found".** Confirma `npm install -g @mariozechner/pi-coding-agent` y reabrí la terminal.

**Las extensiones TS no se cargan.** Pi necesita Bun para correrlas sin build. Instalá Bun (`curl -fsSL https://bun.sh/install | bash`).

**`cortex doctor` reporta `pi` adapter pero `which pi` falla.** A partir de Ola 1 (2026-05-13), `PiAdapter.detect_installation()` chequea `shutil.which("pi")`. Si Pi no está instalado globalmente, doctor lo va a marcar — instalá Pi o quitá la opción `--ide pi` del setup.

**Cambios en agents no se reflejan tras `cortex inject`.** El adapter usa `dirs_exist_ok=True` (sobrescribe). Si seguís viendo el comportamiento viejo, verificá que no haya cache en `.pi/` y que tu skill no tenga override en `.pi/skills/`.

## Tripartita Refinada (0.5.0)

A partir de Cortex **0.5.0**, Pi recibe los contratos verificables de *Tripartita Refinada*. Es el IDE más impactado porque tiene 7 agents (vs 3 en los otros target IDEs) y un `agent-chain.yaml` declarativo. Lo que vas a notar como adopter:

### 1. Sync automático canonical → bundle

Históricamente el bundle `cortex-pi/.pi/agents/{cortex-code-explorer,cortex-code-implementer,cortex-documenter}.md` quedaba congelado en el repo Cortex y podía driftear de los archivos canonical en `.cortex/subagents/`. **0.5.0 lo arregla:** `cortex inject --ide pi` ahora ejecuta `PiAdapter.sync_canonical_subagents` antes de copiar el bundle al proyecto, así los 3 subagents compartidos siempre llegan con los markers Tripartita Refinada (`HIGH-SIGNAL`, `VERIFICATION GATE`, `Modo Handoff`, `3 criterios ADR`, `Anti-rationalization`, `Contrato de Salida`).

**Para opt-out** (snapshot mode, reproducir un bundle viejo exactamente):

```bash
cortex inject --ide pi --no-sync-canonical
```

El default es `--sync-canonical` y es el path recomendado para todo uso normal.

### 2. Los 4 agents Pi-only ya tienen Contrato de Salida YAML

`cortex-sync.md`, `cortex-SDDwork.md`, `cortex-security-auditor.md` y `cortex-test-verifier.md` (los 4 agents que existen sólo en el bundle Pi y no en `.cortex/subagents/`) ahora cierran su turno con un bloque YAML conforme al schema `cortex.handoff.AgentHandoff`. Cuando el usuario corre `just sdd` (o cualquier chain de Pi), cada agent emite ese YAML y el siguiente lo consume. El orquestador `cortex-SDDwork` valida cada handoff con `cortex_validate_handoff` antes de pasarlo al próximo.

Cada uno también tiene una sección **Anti-Rationalization Signals** específica al rol — atajos mentales conocidos (e.g. "el finding es low severity, lo dejo pasar") con la realidad del impacto y la acción correcta.

### 3. `agent-chain.yaml` con keys declarativas

Los 3 chains de Pi (`sddwork`, `hotfix`, `refactor`) ahora declaran por step:

- `validate_handoff: true | false` — si el step espera handoff entrante.
- `expected_input_agent: <nombre>` — qué agent debe haber producido el handoff.

La extensión Pi actual ignora estas keys (las consume el orquestador SDDwork manualmente vía la sección "Validación de handoffs" de su prompt). Cuando un futuro runtime Pi implemente el hook automático, las keys ya están disponibles sin rework.

### 4. `damage-control-rules.yaml` con `handoffRules`

Tres reglas nuevas a nivel governance:

- **`handoff-malformed`** (severity: block) — si un handoff falla `cortex_validate_handoff`, el chain se detiene. No reparar handoffs corruptos automáticamente.
- **`handoff-status-mismatch`** (severity: warn) — si un agent declara `complete` pero su `verified_claims` está vacío, el documenter persiste la memoria con `confidence: asserted` (no `verified`).
- **`handoff-context-overflow`** (severity: warn) — si `context_for_next` supera ~2000 chars, truncar antes de pasar al próximo step.

### 5. `cortex-vault` skill con CONTEXT.md awareness

El skill que enseña a interactuar con la memoria ahora tiene una sección **CONTEXT.md awareness** que explica: chequear `CONTEXT.md` antes de buscar (para usar términos canónicos), antes de persistir memoria (idem), y sugerir términos nuevos vía `suggested_context_terms` del handoff (no agregar directamente — eso lo hace el documenter).

También documenta los **confidence labels** que aparecen en respuestas de búsqueda post-0.5.0: `[verified]` (cruzado con diff), `[asserted]` (sin verificar), `[contradicted]` (diff dice lo opuesto).

## Próximos pasos

- Personalizá `.pi/themes/cortex-dark.json` si querés cambiar la paleta.
- Activa el premium dashboard: `just cortex` con `extensions/cortex-dashboard.ts` cargado por default.
- Configurá `.pi/settings.json` con tu modelo preferido (`claude-sonnet-4-...` es el default).
