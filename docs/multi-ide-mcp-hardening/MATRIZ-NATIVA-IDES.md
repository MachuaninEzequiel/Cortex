# Matriz nativa de IDEs/CLIs — estructura real verificada

**Fecha:** 2026-05-15
**Reemplaza:** la seccion 2 (superficial) de `INVENTARIO.md`.
**Origen:** lectura completa de `cortex/ide/` + `cortex/setup/cortex_workspace.py` + WebFetch a la documentacion oficial **vigente** de cada IDE/CLI.

---

## 0. Por que existe este documento

En la Fase 0 inicial, la seccion 2 de `INVENTARIO.md` describio los adapters de IDE basandose **solo en lo que cada adapter de Cortex hace hoy**. Esa lectura era circular: si un adapter esta mal escrito, el inventario lo registra mal.

El creador instruyo (instruccion del 2026-05-15):

> "necesito que para hacer el setup dentro de los agentes, hagas una busqueda por internet, en cada una de las documentacion de los IDEs y CLIs, para sacar de ahi la estructura exacta que usa cada uno. (...) cada ide/cli tiene su forma de ser configurado. Tenes la obligacion de buscar en las documentaciones oficiales (...) para que podamos inyectar el mcp server y todo el flujo completo de agentes de cortex de forma no generica y adaptada a cada uno"

Este documento consolida la **realidad nativa** de cada target IDE contra el **estado actual** del adapter de Cortex. Cuando hay divergencia, el adapter esta mal — la documentacion oficial es la verdad.

**Fuentes consultadas (URLs):**

| IDE/CLI | Documentacion oficial |
|---|---|
| Claude Code subagents | https://code.claude.com/docs/en/sub-agents |
| Claude Code skills | https://code.claude.com/docs/en/skills |
| opencode agents | https://opencode.ai/docs/agents/ |
| opencode config | https://opencode.ai/docs/config/ |
| opencode MCP | https://opencode.ai/docs/mcp-servers/ |
| Codex AGENTS.md | https://developers.openai.com/codex/guides/agents-md |
| Codex MCP | https://developers.openai.com/codex/mcp |
| pi (pi-mono coding-agent) | https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/README.md |
| Cursor subagents | https://cursor.com/docs/subagents |

---

## 1. TARGET IDES — analisis exhaustivo

### 1.1 Claude Code

#### Primitivas nativas reales (segun docs oficiales)

**Subagents** (`https://code.claude.com/docs/en/sub-agents`):
- **Path**: `.claude/agents/<name>.md` (project) o `~/.claude/agents/<name>.md` (user). Soporta subfolders, pero el identificador viene del campo `name` en frontmatter — no del path.
- **Frontmatter** (todos los fields conocidos):
  - `name` (required): identificador unico.
  - `description` (required): cuando usarlo.
  - `tools` (opcional): lista separada por comas. Si se omite, hereda TODAS las tools del padre. Acepta nombres como `Read, Grep, Glob, Bash` y MCP tools como `mcp__cortex__cortex_save_session`.
  - `model` (opcional): modelo a usar, ej. `sonnet`, `inherit`.
  - `skills` (opcional): skills a precargar en el subagent.
  - `hooks`, `mcpServers`, `permissionMode` (opcional, NO disponibles para plugin subagents).
  - `disallowedTools`, `maxTurns`, `initialPrompt`, `memory`, `effort`, `background`, `isolation`, `color` (opcional).
- **Body**: markdown que es el system prompt del subagent.
- **Invocacion**: Task tool nativo, @-mention, o automatica cuando Claude detecta match con `description`.

**Skills** (`https://code.claude.com/docs/en/skills`):
- **Path**: `~/.claude/skills/<skill-name>/SKILL.md` (personal) o `.claude/skills/<skill-name>/SKILL.md` (project). **Cada skill es un FOLDER**, no un archivo suelto.
- **Frontmatter**:
  - `name` (opcional, default = nombre del directorio).
  - `description` (recomendado): para auto-trigger.
  - `disable-model-invocation: true|false` (opcional).
  - `user-invocable: true|false` (opcional).
  - `allowed-tools` (opcional): grants sin pedir permiso.
  - `model`, `effort` (opcional).
  - `context: fork` + `agent: <subagent-type>` (opcional): **ejecuta la skill en un subagent forkeado**. Esto une skills + subagents en una sola primitiva.
  - `arguments`, `argument-hint`, `paths`, `shell`, `hooks`.
- **Folder structure**: `SKILL.md` (requerido) + opcional `scripts/`, `references/`, `assets/`, `examples/`.
- **Invocacion**: `/skill-name` (slash command) o automatica.
- **Substituciones**: `$ARGUMENTS`, `$N`, `${CLAUDE_SKILL_DIR}`, `${CLAUDE_SESSION_ID}`.
- **Dynamic context**: `` !`<command>` `` se ejecuta antes de inyectar la skill (preprocessing).

**MCP**:
- **Path**: `.mcp.json` (project) y/o `.claude/settings.json` para `enabledMcpjsonServers`.
- **Schema**: `mcpServers.<name>` con `type: "stdio"`, `command`, `args`, `env`.

#### Estado actual del adapter (`cortex/ide/adapters/claude_code.py`)

**Lo que hace bien:**
- Path correcto: `.claude/agents/*.md` y `.claude/skills/<name>/SKILL.md`.
- MCP correcto: `.mcp.json` con `mcpServers.cortex` shape correcto.
- Lee subagents desde `.cortex/subagents/` via `get_subagent_prompt`.

**Lo que hace MAL:**
- En el frontmatter del subagent inyectado (linea 130-143 del adapter), solo escribe `name` y `description`. **NO inyecta el campo `tools`** — el subagent inyectado hereda TODAS las tools del padre, incluso las que su prompt canonico declara que solo deberia usar `read_file, write_file, cortex_save_session, ...`.
- Como consecuencia, el subagent puede invocar tools que su contrato dice que no deberia (ej. ejecutar bash, modificar archivos arbitrarios). Esto **viola la restriccion explicita** que el prompt declara con `tools: read_file, write_file, ...`.
- Los nombres del frontmatter `tools:` del archivo canonico son **canonicos de Cortex** (`read_file`, `write_file`, etc.), pero **Claude Code no los entiende asi** — necesitan traducirse a `Read, Write, Grep, Glob, Bash` y MCP tools a `mcp__cortex__<name>`.

**Acciones correctivas para Fase 4:**
1. Inyectar el campo `tools` en el frontmatter de cada subagent escrito a `.claude/agents/`. El valor traducido se computa con la matriz canonical-tools (Fase 3).
2. Las skills `cortex-sync` y `cortex-sddwork` que el adapter ya inyecta en `.claude/skills/<name>/SKILL.md` estan bien estructuradas.
3. Considerar agregar `allowed-tools` a las skills inyectadas, pre-aprobando los tools MCP de Cortex para evitar prompts repetitivos al adopter.

---

### 1.2 opencode

#### Primitivas nativas reales (segun docs oficiales)

**Agents** (`https://opencode.ai/docs/agents/`):
- **Path**: `~/.config/opencode/agents/<name>.md` (global) o `.opencode/agents/<name>.md` (project). El filename = identificador.
- **Frontmatter**:
  - `description` (required).
  - `mode: primary | subagent | all` (default: `all`).
  - `model: provider/model-id`.
  - `temperature`, `top_p`.
  - `permission`: control granular por tool con `"allow" | "ask" | "deny"`. Soporta glob patterns (ej. `"git *": "ask"`).
  - `prompt: <file ref>`.
  - `steps`, `disable`, `hidden`, `color`.
- **Tools nativos**: `read`, `edit`, `glob`, `grep`, `list`, `bash`, `task`, `external_directory`, `todowrite`, `webfetch`, `websearch`, `lsp`, `skill`, `question`, `doom_loop`. **Todos lowercase**.
- **Invocacion**:
  - Primary: switch con Tab.
  - Subagent: @-mention (`@general help me`) o delegacion del primary via Task.

**Config** (`https://opencode.ai/docs/config/`):
- **Path**: `opencode.json` global (`~/.config/opencode/`) o project root.
- **Agent JSON** (alternativa al markdown):
  ```json
  {
    "agent": {
      "agent-name": {
        "description": "...",
        "model": "provider/model",
        "prompt": "{file:path/to/prompt.md}",
        "tools": { "read": true, "write": false, "bash": true }
      }
    }
  }
  ```

**MCP local stdio** (`https://opencode.ai/docs/mcp-servers/`):
- **Path**: `opencode.json`.
- **Schema EXACTO**:
  ```json
  {
    "mcp": {
      "<server-name>": {
        "type": "local",
        "command": ["cortex", "mcp-server", "--stdio", "--project-root", "<path>"],
        "enabled": true,
        "environment": { "PYTHONWARNINGS": "ignore" }
      }
    }
  }
  ```
- Notar: `type: "local"` (no "stdio"), `command` es array, env field es `environment` (no `env`).

#### Estado actual del adapter (`cortex/ide/adapters/opencode.py`)

**Lo que hace bien:**
- MCP config correcta: usa `"type": "local"`, `command` array, `environment` object. **Alineado con docs**.
- Inyecta agents en `agent` del JSON (formato valido).
- Copia subagents a `~/.config/opencode/subagents/` (path adicional, opencode tambien busca aca).

**Lo que hace MAL:**
- Inyecta los profiles de `cortex-sync` y `cortex-SDDwork` con un set de tools que incluye `cortex_create_spec`, `cortex_sync_ticket`, `cortex_save_session`, etc. — **estos son MCP tools, NO tools nativas de opencode**. El campo `tools` de un agent en opencode acepta SOLO los nombres de la lista nativa (read, edit, glob, grep, list, bash, task, external_directory, todowrite, webfetch, websearch, lsp, skill, question, doom_loop). Los MCP tools se acceden a traves de `task` o se descubren dinamicamente — no se declaran en el frontmatter de tools.
- Path `~/.config/opencode/skills/` — opencode no tiene un concepto explicito de "skills" como folder. Tiene el tool `skill` y los Agent Skills, pero la estructura es a traves de markdown agents con `mode: subagent`.

**Acciones correctivas para Fase 4:**
1. Limpiar el campo `tools` del agent profile inyectado: dejar SOLO los tools nativos lowercase (`read`, `write`, `edit`, `bash`, `task`).
2. Eliminar las claves `cortex_*` del campo `tools` — esas son tools MCP descubiertas en runtime, no se declaran a priori.
3. Considerar usar `permission` (en lugar de `tools`) para grants granulares, ya que `permission` es la forma nativa de opencode de gating de tools.
4. Decidir si seguir copiando a `~/.config/opencode/skills/` o consolidar todo en `agents/` con `mode: subagent`.

---

### 1.3 Codex (OpenAI Codex CLI)

#### Primitivas nativas reales (segun docs oficiales)

**AGENTS.md** (`https://developers.openai.com/codex/guides/agents-md`):
- **Path**: `~/.codex/AGENTS.md` (global) y/o `AGENTS.md` en project root y/o cualquier directorio padre desde cwd. Codex hace merge root-down.
- **Override**: `AGENTS.override.md` toma precedencia sobre `AGENTS.md` en el mismo directorio.
- **Formato**: markdown plano. **NO soporta frontmatter**. Solo guidance/instrucciones.
- **NO existen "subagents personalizados"** en Codex. Es UN solo agente que lee guidance layered desde varios AGENTS.md. Cita literal: *"Not supported. The documentation describes layered instructions, not distinct agent definitions. There is no mechanism to define multiple named agents within a repository."*

**MCP** (`https://developers.openai.com/codex/mcp`):
- **Path**: `~/.codex/config.toml` (global) o `.codex/config.toml` (project, "trusted projects only").
- **Formato**: TOML, NO JSON.
- **Schema EXACTO**:
  ```toml
  [mcp_servers.cortex]
  command = "cortex"
  args = ["mcp-server", "--stdio", "--project-root", "<path>"]
  env_vars = ["PYTHONWARNINGS"]

  [mcp_servers.cortex.env]
  PYTHONWARNINGS = "ignore"
  ```
- Key es `mcp_servers` (snake_case), no `mcpServers`.
- `enabled = true|false` opcional para toggle por server.

#### Estado actual del adapter (`cortex/ide/adapters/codex.py`)

**Lo que hace bien:**
- Genera AGENTS.md con guidance de Cortex.

**Lo que hace MAL (multiple errores fundamentales):**
- **Path incorrecto de AGENTS.md**: lo escribe a `.codex/AGENTS.md`. Codex lee `AGENTS.md` en project root, NO dentro de `.codex/`. Comentario en el adapter dice que es para "evitar colision con repos que ya tienen AGENTS.md", pero esa decision rompe el descubrimiento por Codex. Codex no va a leer `.codex/AGENTS.md`.
- **Crea archivos de "subagents"** en `.codex/agents/cortex-{code-explorer,code-implementer,documenter}.md` — Codex **no soporta subagents personalizados**. Estos archivos son ignorados por Codex completamente.
- **Crea archivos de "skills"** en `.codex/skills/cortex-{sync,sddwork}.md` — Codex **no tiene concepto de skills**. Estos archivos son ignorados.
- **MCP en formato JSON incorrecto**: escribe `.codex/mcp.json` con clave `mcpServers` (camelCase) y type `"stdio"`. Codex lee `.codex/config.toml` con clave `[mcp_servers.<name>]` (snake_case TOML). El adapter actual **no instala MCP en Codex**.

**Acciones correctivas para Fase 4 (rediseno completo del adapter):**
1. Escribir `AGENTS.md` (plano, sin extension `.codex/`) en project root con guidance Cortex completa. Usar el mecanismo de merge layering para que conviva con AGENTS.md preexistente del adopter (probablemente como `AGENTS.override.md` si Cortex es el ultimo override, o appendear con header).
2. **Eliminar** la inyeccion de `.codex/agents/*.md` y `.codex/skills/*.md` — son no-ops.
3. **Reescribir** la inyeccion MCP: TOML en `~/.codex/config.toml` (global) o `.codex/config.toml` (project) con la sintaxis `[mcp_servers.cortex]`.
4. La "delegacion" en Codex se materializa como instrucciones del AGENTS.md ("para implementacion compleja, leer estos archivos via cortex_search...") porque no hay subagents reales. El plan tripartito (explorer/implementer/documenter) en Codex se ejecuta como flujo secuencial del UN agent — NO como subagentes paralelos.

---

### 1.4 pi (pi-mono coding-agent)

#### Primitivas nativas reales (segun docs oficiales)

**Repo:** github.com/badlogic/pi-mono/packages/coding-agent.

**Agents/Context** (README oficial):
- **Path AGENTS.md**: `~/.pi/agent/AGENTS.md` (global), parent directories desde cwd, current directory. Pi merge-a todos los matches. Tambien acepta `CLAUDE.md` como fallback (compatibilidad).
- **NO existe `AGENTS.md` dentro de `.pi/`** — esta en project root, igual que Codex.

**Skills** (README oficial):
- **Path**: `~/.pi/agent/skills/`, `~/.agents/skills/`, `.pi/skills/`, `.agents/skills/`. Searched walking up from cwd.
- **Formato**: Agent Skills standard — markdown con `SKILL.md`.

**Subagents:**
- **NO EXISTEN.** Cita literal del README: *"No sub-agents. There's many ways to do this. Spawn pi instances via tmux, or build your own with extensions"*.

**MCP:**
- **NO SOPORTADO NATIVAMENTE.** Cita literal: *"No MCP. Build CLI tools with READMEs (see Skills), or build an extension that adds MCP support."*

**Settings y system prompt:**
- `.pi/settings.json` — settings de proyecto.
- `.pi/SYSTEM.md` — sobreescribe system prompt.
- `.pi/APPEND_SYSTEM.md` — appendea al system prompt.

**Tools default**: `read`, `write`, `edit`, `bash` (4 tools).

#### Estado actual del adapter (`cortex/ide/adapters/pi.py`)

**Lo que hace MAL (rediseno completo):**
- **Copia el bundle entero `cortex-pi/` a project root**, incluyendo `cortex-pi/.pi/agents/*.md`. Pi **no usa `.pi/agents/`** — esa carpeta no existe en el modelo de pi. Los archivos copiados ahi son **completamente ignorados por pi**.
- Copia tambien `cortex-pi/.pi/skills/` — pero pi busca skills en `.pi/skills/` (correcto coincidencia! por casualidad funciona).
- Copia `AGENTS.md`, `justfile`, `README.md`, `extensions` al project root. AGENTS.md es OK; el resto puede ser para el bundle pi-coding-agent en si.
- El `sync_canonical_subagents()` (linea 37-84 del adapter) sincroniza los 3 subagents shared a `cortex-pi/.pi/agents/` — pero como pi no usa esa carpeta, la sincronizacion es **trabajo desperdiciado**.
- **Intenta inyectar MCP**: `inject_mcp` retorna lista vacia comentando "Pi Coding Agent uses bash tools, MCP injection not required." — esto es CORRECTO por casualidad (porque pi no soporta MCP), pero el comentario suena como decision arbitraria, no informada por la limitacion real de pi.

**Acciones correctivas para Fase 4 (rediseno completo del adapter):**
1. **Eliminar** la copia de `cortex-pi/.pi/agents/` al project root. Pi no las lee. Y como pi no tiene MCP, los subagents de Cortex (que dependen de tools MCP) no pueden funcionar en pi.
2. Generar `AGENTS.md` en project root con instrucciones de Cortex adaptadas a pi (sin referencias a tools MCP que pi no tiene).
3. Generar skills relevantes en `.pi/skills/cortex-{sync,sddwork}/SKILL.md` (formato Agent Skills).
4. Pi NO soporta el flujo tripartito (explorer/implementer/documenter como subagents). Los workflows de Cortex en pi se ejecutan como secuencias dentro del UN agente principal, similar a Codex.
5. **Confirmar al creador**: pi puede ser un target IDE solo en modo "lectura/seguimiento" porque no tiene MCP. ¿Vale la pena mantenerlo como TARGET o degradarlo a community?

---

## 2. Resumen del impacto en el plan

### 2.1 Cambios estructurales necesarios

| Adapter | Cambio principal | Tamaño del cambio |
|---|---|---|
| `claude_code` | Inyectar `tools` traducido en frontmatter de subagents. | Pequeño (1-2 lineas + uso de canonical-tools de Fase 3). |
| `opencode` | Limpiar `tools` field de profiles (solo nombres nativos lowercase). Decidir si consolidar paths de subagents. | Mediano. |
| `codex` | **Rediseno completo**: AGENTS.md a project root, eliminar agents/skills (no soportado), MCP en TOML. | Grande. |
| `pi` | **Rediseno completo**: eliminar copia `.pi/agents/`, generar skills en `.pi/skills/`, AGENTS.md en root, NO inyectar MCP. | Grande. |

### 2.2 Implicancias para los principios rectores del plan

El **principio rector #1** del plan (`Cortex se comporta igual en todos los IDEs`) necesita refinamiento:

- El **comportamiento conceptual** de Cortex (verification gate, tripartita refinada, persistencia en vault) es uniforme: el flujo tiene los mismos pasos.
- Pero la **materializacion** en cada IDE difiere significativamente:
  - Claude Code: explorer/implementer/documenter como subagents nativos, delegacion via Task.
  - opencode: explorer/implementer/documenter como subagents con `mode: subagent`, delegacion via @ o Task tool.
  - Codex: NO HAY subagents — el flujo se ejecuta como secuencia en el agente unico, con AGENTS.md guiando los pasos.
  - pi: NO HAY subagents NI MCP — Cortex en pi es **degradado** a flujo basico (CLAUDE.md / AGENTS.md guidance + skills locales), sin verification gate (que requiere `cortex_verify_session_claims` MCP) ni `cortex_save_session`.

**Decision arquitectural pendiente del creador**: ¿se acepta que Cortex en pi y Codex sea **funcionalmente reducido** (sin tripartita refinada porque no hay subagents)? O ¿se redefine Cortex para que el flujo no dependa de subagents y funcione 100% en single-agent mode?

### 2.3 Implicancias para Fase 3 (canonical-tools)

La matriz `canonical_tools.py` ahora tiene mas claridad:

| canonical | Claude Code | opencode | Codex | pi |
|---|---|---|---|---|
| `read_file` | `Read` | `read` | (uso nativo del agente, sin gating) | `read` |
| `write_file` | `Write` | `write` | idem | `write` |
| `edit_file` | `Edit` | `edit` | idem | `edit` |
| `execute_command` | `Bash` | `bash` | idem | `bash` |
| `glob` | `Glob` | `glob` | idem | (no aplica) |
| `grep` | `Grep` | `grep` | idem | (no aplica) |
| `cortex_save_session` | `mcp__cortex__cortex_save_session` | `cortex_save_session` (descubierto) | `cortex_save_session` (descubierto) | **N/A — pi no tiene MCP** |
| `cortex_search` | `mcp__cortex__cortex_search` | `cortex_search` (descubierto) | `cortex_search` (descubierto) | **N/A** |

Para opencode/Codex, los MCP tools NO se declaran en frontmatter `tools:` — se descubren dinamicamente. El canonical-tools matrix tiene que reflejar esto con un valor especial (`AUTO_DISCOVERED` o `None`).

### 2.4 Implicancias para Fase 4 (adapters SSoT)

El alcance de Fase 4 se TRIPLICA:

- **claude_code**: 1 cambio acotado.
- **opencode**: cleanup + revision de paths.
- **codex**: rediseno desde cero.
- **pi**: rediseno desde cero + decisiones arquitecturales sobre que features de Cortex son posibles.
- **community/experimental** (vscode, cursor, windsurf, claude_desktop, antigravity, hermes, zed): revisar caso por caso, pero menos critico.

### 2.5 Implicancias para Fase 5 (cleanup delegate MCP)

`cortex_delegate_task` no afecta nada de esta matriz: es un MCP tool que Codex y opencode pueden invocar pero no usar (porque el delegate apunta a opencode binary). Su eliminacion sigue siendo correcta y se mantiene como en la Fase 5 original.

---

## 3. IDEs community y experimental — nota breve

Para no contaminar el alcance, los community y experimental se documentan brevemente:

| IDE | Adapter | Tier | Observacion |
|---|---|---|---|
| cursor | `cortex/ide/adapters/cursor.py` | community | Cursor 2.4 (enero 2026) introdujo subagents nativos en `.cursor/agents/`. El adapter actual usa `~/.cursor/agents/` (user-level OK pero project-level posible). El `cortex-SDDwork-cursor.md` hibrido era un workaround pre-2.4 obsoleto. |
| vscode | `cortex/ide/adapters/vscode.py` | community | Escribe a `.github/agents/` (Github Copilot Workspace agents) Y `.claude/agents/` (compatibilidad). MCP en `.vscode/mcp.json` con key `servers`. |
| claude_desktop | `cortex/ide/adapters/claude_desktop.py` | community | Solo MCP. Path correcto. |
| windsurf | `cortex/ide/adapters/windsurf.py` | community | Solo MCP + AGENTS.md global. |
| antigravity | experimental | Solo system_instructions JSON + MCP. |
| hermes | experimental | JSON config con prompts + MCP. |
| zed | experimental | agents.json + sin MCP. |

Estos se revisan en Fase 4 si el alcance lo permite, o se marcan explicitamente como "no certificados contra docs oficiales 2026" para que el adopter sepa el riesgo.

---

## 4. Decisiones firmadas por el creador (2026-05-15)

El creador firmo las 4 decisiones pendientes:

### Decision 1 — pi se mantiene como TARGET, adapter NO se toca

> "Dejemos pi como esta, porque si revisas la carpeta cortex-pi/, tiene muchisimas cosas adentro, que la comunidad fue desarrollando y demas, que hace que funcione correctamente, por lo que, debes dejarlo asi como esta por ahora."

**Implicancia:** Fase 4 NO toca `cortex/ide/adapters/pi.py` ni el bundle `cortex-pi/`. Aunque la documentacion oficial de pi-mono diga que `.pi/agents/` no se usa, el bundle de cortex-pi tiene contribuciones de comunidad (extensiones, justfile, agents propios, skills propios) que el creador confirma que funcionan. Se respeta ese estado.

**Lo que NO se hace en Fase 4:**
- NO eliminar `cortex-pi/.pi/agents/`.
- NO reescribir el adapter pi.
- NO cambiar `sync_canonical_subagents()`.
- NO cambiar el comportamiento de copia del bundle.

**Lo que SI se mantiene como pendiente para una fase futura (no este plan):**
- Eventualmente, validar el bundle cortex-pi/ contra la realidad nativa de pi-mono actual y consolidar lo que se use con lo que no. Pero NO en este plan.

### Decision 2 — Codex: subagente unico ejecuta tripartita secuencialmente

> "correcto, que en codex lo haga todo un subagente con una secuencia de flujo"

**Implicancia:** El adapter de Codex se redisena para que:
- Inyecte `AGENTS.md` en project root (no en `.codex/`) con instrucciones explicitas para que el agente unico ejecute las 3 fases (explorer / implementer / documenter) **secuencialmente** dentro de la misma sesion.
- NO inyecte archivos en `.codex/agents/` ni `.codex/skills/` (Codex no los lee).
- Inyecte MCP en `.codex/config.toml` (o `~/.codex/config.toml` global) con sintaxis TOML correcta `[mcp_servers.cortex]`.
- El AGENTS.md genera un flujo tipo "checkpoint" donde el agente:
  1. Ejecuta fase de explorer (analisis read-only) y persiste un handoff intermedio en `.cortex/vault/...`.
  2. Ejecuta fase de implementer leyendo ese handoff.
  3. Ejecuta fase de documenter al final, persistiendo via `cortex_save_session`.
- El verification gate se mantiene: el agente unico ejecuta `cortex_verify_session_claims` antes de cerrar la sesion. Lo que se pierde es la paralelizacion / aislamiento de contextos.

### Decision 3 — Cursor: usar los 3 subagentes reales (eliminar hibrido)

> "okay, en caso de que podamos utilizar los agentes que ya tenemos, meterlos dentro de cursor, esta perfecto"

**Implicancia:** El adapter de Cursor se redisena para:
- Inyectar los 3 subagentes canonicos (`cortex-code-explorer`, `cortex-code-implementer`, `cortex-documenter`) en `.cursor/agents/` (project) o `~/.cursor/agents/` (user), usando los renders auteticos de `cortex_workspace.py`.
- Eliminar `cortex-SDDwork-cursor.md` (variante hibrida obsoleta).
- Eliminar `build_cursor_prompts()` o reescribirlo para usar los renders standard.
- MCP en `~/.cursor/mcp.json` con el schema validado.

### Decision 4 — Community/experimental marcados como NO VALIDADOS

> "hay que marcarlos como no validados por ahora. Debemos de concentrarnos y que funcionen bien opencode, claude code, pi y codex"

**Implicancia:** Foco TOTAL del plan en los 4 target IDEs:
- claude_code
- opencode
- pi (sin tocar)
- codex (rediseno)

Y cursor sale del scope community y se VALIDA tambien (porque Decision 3 lo trabaja). En total: 5 adapters trabajados.

Los demas (vscode, claude_desktop, windsurf, antigravity, hermes, zed) se marcan en `cortex/ide/registry.py` y/o en `docs/architecture/ide-support-matrix.md` como **"community/experimental — no validado contra docs oficiales 2026"**. El plan NO los toca. Si un adopter los usa, sabe que es best-effort.

---

## 5. Alcance corregido de Fase 4 con decisiones firmadas

| Adapter | Accion en Fase 4 | Tamaño |
|---|---|---|
| `claude_code` | Inyectar `tools` traducido en frontmatter de subagents. | Pequeño. |
| `opencode` | Limpiar `tools` field (solo nombres nativos lowercase). | Mediano. |
| `cursor` | **Rediseno**: 3 subagents nativos en `.cursor/agents/`, eliminar `cortex-SDDwork-cursor.md` y `build_cursor_prompts()`. | Mediano. |
| `codex` | **Rediseno**: AGENTS.md en root con flujo tripartito secuencial, MCP en TOML, eliminar `.codex/agents/*.md` y `.codex/skills/*.md`. | Grande. |
| `pi` | **NO TOCAR**. Decision firmada del creador. | Cero. |
| `vscode`, `claude_desktop`, `windsurf`, `antigravity`, `hermes`, `zed` | Marcar como "no validado 2026" en registry + doc. **No reescribir**. | Cero (solo metadata). |

---

## 6. Cambios en los principios rectores del plan

Las decisiones del creador clarifican el **principio rector #1** asi:

> Cortex tiene un **comportamiento conceptual uniforme** (mismas fases, mismo verification gate, misma persistencia en vault). La **materializacion** varia por IDE segun lo que cada IDE soporta nativamente:
>
> - **Subagentes paralelos + delegacion + MCP**: claude_code, opencode (full tripartita refinada).
> - **Subagentes paralelos + MCP**: cursor (tripartita refinada usando subagents nativos de Cursor 2.4+).
> - **Single agent + MCP, flujo secuencial**: codex (las "3 fases" se ejecutan como pasos consecutivos dentro de la misma sesion).
> - **Single agent + sin MCP, modo degradado**: pi (Cortex funciona como guidance + skills, sin verification gate via MCP).

Esto reemplaza la version simplista anterior del plan que asumia que todos los IDEs podian materializar el mismo flujo.
