# El Manifiesto Cortex

<div align="center">

**Cortex Enterprise**

*Calidad, Seguridad, Documentación y Memoria Corporativa como sistema de gobernanza para Organizaciones y DevAgents*

</div>

---

## Índice

1. [¿Por qué Cortex?](#por-qué-cortex)
2. [Modelo de Ejecución: Pluggable Middle](#modelo-de-ejecución-pluggable-middle)
3. [La primitiva Session](#la-primitiva-session)
4. [Verification hooks](#verification-hooks)
5. [Documenter por reconstrucción](#documenter-por-reconstrucción)
6. [Pilares tecnológicos](#pilares-tecnológicos)
7. [CLI Reference](#cli-reference)
8. [Plugin de CI](#plugin-de-ci)
9. [Servidor MCP](#servidor-mcp)
10. [Instalación](#instalación)
11. [Configuración por IDE](#configuración-por-ide)
12. [Configuración YAML](#configuración-yaml)
13. [Estructura del proyecto](#estructura-del-proyecto)
14. [Testing y calidad](#testing-y-calidad)
15. [Enterprise Memory Productization](#enterprise-memory-productization)

---

## ¿Por qué Cortex?

| Problema | Solución Cortex |
| --- | --- |
| Agentes olvidan contexto entre sesiones | Memoria Híbrida RRF persistente (local + enterprise) |
| Specs sin criterios objetivos de éxito | `verification_hooks` ejecutables declarados en cada spec |
| Decisiones arquitectónicas sin trazabilidad | ADRs sugeridos automáticamente desde checkpoints |
| Tres IDEs, tres formas de trabajar | Pluggable Middle: Managed / Observed / BYO se adaptan al setup del equipo |
| Documentación desincronizada del código | El documenter reconstruye desde el `git diff` y los verification results |
| PRs sin trazabilidad de lo prometido vs. entregado | Plugin de CI con comentario sticky de PR |
| Conocimiento aislado por proyecto | Promotion Pipeline `candidate → reviewed → promoted` hacia vault corporativo |
| Sin visibilidad sobre salud de memoria | `memory-report`, `doctor`, `session watch` |
| Configuración enterprise compleja | Setup guiado con presets por industria |
| Gobernanza CI inexistente | Perfiles `observability` / `advisory` / `enforced` |
| Workspace disperso en la raíz del repo | Workspace v2: todo en `.cortex/`, `WorkspaceLayout` central |
| Drift entre canonical (`.cortex/`) y bundle Pi | Mirror automático canonical → bundle en `cortex inject --ide pi` |

---

## Modelo de Ejecución: Pluggable Middle

Cortex envuelve cada unidad de trabajo en tres puntos: **sync** (antes), **middle** (durante) y **documenter** (después). Sync y documenter son fijos; el middle es **pluggable** y admite tres modos.

### 1. `cortex-sync` — El Analista

Recupera contexto histórico del Vault y de la memoria episódica para refinar los requisitos. Produce una `Spec` con `verification_hooks` ejecutables y **abre la Session automáticamente** al persistirla.

Sub-paso opcional: emisión de una **propuesta** previa a la spec (`--proposal-mode optional|required|skip`) para alinear con el usuario antes de comprometer alcance.

### 2. Middle (Pluggable)

| Modo | Quién hace el trabajo | Cuándo usarlo |
|---|---|---|
| 🟢 **Managed** | `cortex-SDDwork` + subagents | Sin tooling propio o querés disciplina forzada. |
| 🟡 **Observed** | Tu agente / skills + IDE hooks | Tenés tus skills/agentes preferidos; Cortex observa los checkpoints. |
| 🔵 **BYO** | Lo que sea (manual, otro agente, vibe coding) | Máxima libertad; Cortex reconstruye desde el diff observable. |

El modo **se infiere al cerrar** según las fuentes de checkpoint registradas: sin checkpoints → BYO; sólo fuentes Cortex → Managed; cualquier otra → Observed.

**Managed Deep Track — pipeline de 4 subagents:**

`cortex-code-explorer` → `cortex-code-designer` → `cortex-code-implementer` → wrap-up. El designer puede saltearse con una nota mínima cuando `task_type == "docs-only"`.

**Modo Observed — IDE hooks soportados:**

| IDE | Mecanismo | Comando |
|---|---|---|
| Claude Code | Hook `PostToolUse` en `.claude/settings.json` | `cortex session hooks install --ide claude-code` |
| Cursor / VSCode / Cline / Roo | `.git/hooks/post-commit` | `cortex session hooks install --ide cursor` |
| opencode | Bloque markdown en `.opencode/hooks.md` | `cortex session hooks install --ide opencode` |
| Pi Coding Agent | Recipes en `justfile` | `cortex session hooks install --ide pi` |
| Codex | Sin hooks nativos — modo BYO con `cortex finish-session` manual | — |

Los hooks emiten checkpoints con `source=ide-hook` y están guardados con `|| true` (o `try/except` en JSON) para que un fallo de Cortex nunca aborte la operación del IDE.

Inspeccionar / gestionar:

```bash
cortex session hooks list            # tabla con estado por IDE
cortex session hooks status          # idem en formato detallado
cortex session hooks uninstall --ide cursor
```

### 3. `cortex-documenter` — El Guardián

Paso final vía `cortex finish-session` (CLI) o `cortex_finish_session` (MCP). Reconstruye el contexto desde la Session y persiste el session note + ADRs sugeridos. Cierra como `CLOSED` o `HANDOFF` según los resultados.

**Dos modos de documenter:**

- **`auto` (default)** — corre la pipeline completa sin pedir nada.
- **`interactive`** — `cortex finish-session --interactive` abre una UI con `rich` que renderiza el draft + ADRs sugeridos, permite editar título/cuerpo vía `$EDITOR`, aprobar/rechazar ADRs uno por uno y forzar HANDOFF o cancelar. Default per-proyecto: `documenter.default_mode: interactive` en `.cortex/config.yaml`.

---

## La primitiva Session

`cortex.session.SessionRecord` es el YAML atómico que ancla cada unidad de trabajo. Vive en `.cortex/sessions/<session_id>.yaml`. El pointer `.cortex/sessions/active.txt` indica cuál es la sesión activa.

**Campos:**

- **Identidad**: `session_id`, `spec_path`, `spec_summary`.
- **Snapshot**: `start_commit`, `start_branch`, `opened_at`.
- **Live state**: `status` (`open` / `closed` / `handoff` / `abandoned`), `mode` (inferido al cerrar).
- **Enriquecimiento**: `checkpoints` (append-only), `verification_results`, `tasks` (opt-in, Sub-fase 09.C).
- **Cierre**: `closed_at`, `end_commit`, `documenter_decision`, `session_note_path`, `adrs_created`.

**Operaciones disponibles:** open, append checkpoint, close, abandon, list, switch active, watch (TUI viva).

**Comandos:**

| Comando | Descripción |
| --- | --- |
| `cortex session current` | Id de la sesión activa (o `(no active session)`). |
| `cortex session list` | Lista sesiones (`--status open\|closed\|handoff\|abandoned`, `--json`). |
| `cortex session show [ID]` | Detalle completo (default: la activa). Con `--watch` abre la TUI. |
| `cortex session watch [ID] [--refresh N]` | TUI viva con `rich`. Refresca cada `N` s (default 1.5, rango 0.5–30). Muestra sesión activa, checkpoints, diff preview, verification status, sidebar de sesiones recientes. `Ctrl+C` para salir. |
| `cortex session diff [ID]` | `git diff start_commit..HEAD` de la sesión. |
| `cortex session task list \| done \| in-progress \| skip \| block` | Tasks granulares (opt-in vía `cortex create-spec --with-tasks`). |
| `cortex session switch <ID>` | Cambia la sesión activa. |
| `cortex session abandon <ID> --reason X` | Cierra como `abandoned` sin generar session note. |
| `cortex session checkpoint --source <s> --note "..." [--verified-claim X] [--artifact path]` | Appendea un checkpoint a la sesión activa. |
| `cortex session hooks list \| status \| install \| uninstall --ide <name>` | Gestiona hooks de IDE para el modo Observed. |
| `cortex finish-session [ID]` | Cierra la sesión vía la pipeline de reconstrucción. Flags: `--handoff --reason X`, `--abandon --reason X`, `--interactive`, `--no-interactive`, `--json`. |

---

## Verification hooks

Cada `cortex create-spec` declara uno o más `verification_hooks`: comandos ejecutables que **prueban objetivamente** que el trabajo está hecho. El documenter los corre al cerrar la sesión.

```bash
cortex create-spec --title "Auth JWT" --goal "Implementar refresh tokens" \
  --verification-hook "name=tests;command=pytest tests/auth/" \
  --verification-hook "name=types;command=mypy src/auth.py" \
  --verification-hook "name=lint;command=ruff check src/auth.py;required=false"
```

**Reglas:**

- `required=true` (default): si falla, la Session cierra como `HANDOFF` (trabajo incompleto).
- `required=false`: el resultado se registra pero no bloquea el cierre.
- Para tareas de research o docs-only el hook puede ser una presencia: `command=test -f docs/research-output.md`.
- El runner trunca la salida a `MAX_VERIFICATION_OUTPUT_BYTES` y aplica timeout configurable (`timeout_seconds`).

**Flags adicionales en `cortex create-spec`:**

- `--proposal-mode optional|required|skip` — gate de la propuesta previa (`required` pide `--proposal-confirmed`).
- `--with-tasks` — pide a SDDwork emitir descomposición granular de tasks (`T1`, `T1.2`, `T3.4.1`, …) que después se pueden mutar con `cortex session task ...`.
- `--tag X` — tags repetibles (`tasks-required` se agrega automáticamente con `--with-tasks`).
- `--no-sync` — saltea la re-indexación del vault tras escribir el spec.

---

## Documenter por reconstrucción

El documenter está implementado en `cortex.documenter` como una **pipeline de 8 pasos**:

1. **Load spec** — carga el spec original con sus `verification_hooks`.
2. **Diff** — computa `git diff start_commit..HEAD` (modo gitless si no hay repo).
3. **Hooks** — ejecuta los `verification_hooks` declarados.
4. **Scope cross-check** — cruza `files_in_scope` (declarados) vs. archivos efectivamente tocados.
5. **Contradiction detection** — busca claims contradictorios entre checkpoints y memorias previas.
6. **Handoff synthesis** — arma un `AgentHandoff` sintético desde el estado de la sesión.
7. **Status decision** — decide `CLOSED` / `HANDOFF` / `ABANDONED`.
8. **Persist** — escribe el session note + ADRs sugeridos via `DocumenterPersister`.

**Self-review pass** (incluido en `DocumenterPersister`): escanea el draft antes de persistirlo en busca de placeholders, menciones de archivos no tocados y claims huecos. Es informacional — marca con tag `auto-draft` y entradas `[self-review]` en `next_steps`; nunca bloquea el cierre.

**Rollback transaccional en `NoteService.create`:** si la indexación falla después de escribir el archivo, el session note se desindexa y borra. Garantía: *"file on disk ⇒ file indexed"*.

---

## Pilares tecnológicos

### Memoria Híbrida RRF + Enterprise

- **Capa Episódica**: ChromaDB con embeddings ONNX (`<1ms` latency).
- **Capa Semántica**: Vault Markdown (Obsidian-compatible).
- **Capa Enterprise**: Vault corporativo con retrieval multi-nivel y scopes `local` / `enterprise` / `all`.
- **Fusión**: True RRF cross-source con pesos configurables por scope y trazabilidad por hit (scope, project_id, origin_vault).

### Enterprise Memory Layer

- **`.cortex/org.yaml`**: topología declarativa con schema versionado.
- **Presets**: `small-company`, `multi-project-team`, `regulated-organization`, `custom`.
- **Promotion Pipeline**: `candidate` → `reviewed` → `promoted` con trazabilidad completa.
- **Gobernanza CI**: perfiles `observability` / `advisory` / `enforced`.
- **Observabilidad**: `cortex memory-report` con salida humana y JSON.

### Quality Gates (managed)

Cinco mecanismos de calidad que la pipeline corre **inline**:

1. **Rollback transaccional** en `NoteService.create`.
2. **`cortex_review_checkpoint`** — MCP tool con review en dos etapas (spec compliance + quality) sobre cualquier checkpoint de una sesión abierta. SDDwork la invoca tras cada subagent en Deep Track.
3. **Self-review del documenter** — surface placeholders y claims huecos antes de persistir.
4. **Budget task-aware** en `cortex_context` — pasá `task_type` y `(top_k, max_chars)` se dimensionan automáticamente.
5. **Template condicional `session.md.j2`** — renderiza `question-only` / `docs-only` (sin *Changes Made*), `security` (sección dedicada de Security Review) y `fast-code` / `deep-code` con layout completo.

### Eficiencia ONNX

```
Modelo:           all-MiniLM-L6-v2 (384 dimensions)
Latencia:         <1ms por embedding (CPU)
Memory footprint: ~50MB (vs ~2.5GB PyTorch)
API keys:         No requeridas
```

### Context Enricher Proactivo

Detección de dominio, co-occurrence boost, multi-strategy search con budget control y `task_type`-aware sizing.

### WebGraph

Visualización interactiva del grafo de conocimiento (episódico + semántico + enterprise) con contrato JSON estable, resiliencia frontend y filtros por scope, tipo y proyecto.

```bash
cortex webgraph serve     # Inicia el servidor de visualización
cortex webgraph export    # Exporta snapshot del grafo
```

### Workspace v2 (`.cortex/`)

Todo el estado de Cortex consolidado en un único directorio:

```
.cortex/
  config.yaml
  workspace.yaml          ← layout_version: 2
  org.yaml
  vault/                  ← specs/, sessions/, designs/, adrs/, …
  vault-enterprise/
  sessions/               ← <id>.yaml + active.txt
  memory/                 ← ChromaDB
  enterprise-memory/
  skills/
  subagents/
  webgraph/
  logs/
  scripts/
.github/workflows/        ← único elemento fuera de .cortex
```

Resolución de rutas centralizada en `WorkspaceLayout` (`cortex/workspace/layout.py`), con dual-discovery para soporte transparente del layout legacy.

---

## CLI Reference

### Comandos Core

| Comando | Descripción |
| --- | --- |
| `cortex setup agent` | Configura Vault, Memoria, Skills y MCP. |
| `cortex setup pipeline` | Configura GitHub Actions y auditoría (`--non-interactive`). |
| `cortex setup full` | Instalación completa (Agent + Pipeline + WebGraph). |
| `cortex setup webgraph` | Configura visualización de grafos. |
| `cortex setup enterprise` | Setup enterprise con wizard o presets. |
| `cortex init` | Alias rápido para `setup agent`. |
| `cortex create-spec` | Define metas, criterios y `verification_hooks`. Abre la Session automáticamente. Flags: `--verification-hook`, `--proposal-mode`, `--proposal-confirmed`, `--with-tasks`, `--tag`, `--no-sync`. |
| `cortex finish-session [ID]` | Cierra la Session vía la pipeline de reconstrucción del documenter. Flags: `--handoff`, `--abandon`, `--reason`, `--interactive`/`--no-interactive`, `--json`. |
| `cortex save-session` | Persiste cambios y decisiones en el Vault (modo legacy / single-agent IDE). |
| `cortex search` | Búsqueda híbrida RRF (`--scope local\|enterprise\|all`). |
| `cortex context` | Inyecta contexto basado en archivos modificados. Acepta `--task-type` para dimensionar el budget. |
| `cortex doctor` | Valida entorno (`--scope project\|enterprise\|all`). Emite secciones `[sessions]`, `[autopilot]`, `[pluggable_middle]`. |
| `cortex validate-docs` | Valida frontmatter y estructura Markdown. |
| `cortex verify-docs` | Verifica documentación de agente en PRs. |
| `cortex index-docs` | Indexa docs del vault como memoria semántica. |
| `cortex remember` | Almacena memorias episódicas (`--summarize`). |
| `cortex forget` | Elimina memorias por ID. |
| `cortex stats` | Estadísticas del vault y memoria. |
| `cortex install-skills` | Inyecta habilidades Obsidian. |
| `cortex mcp-server` | Inicia servidor MCP para IDEs. |
| `cortex agent-guidelines` | Muestra guidelines del agente. |

### Comandos Sessions

(ver [La primitiva Session](#la-primitiva-session) — `cortex session current|list|show|watch|diff|task|switch|abandon|checkpoint|hooks|...`)

### Comandos CI Plugin

| Comando | Descripción |
| --- | --- |
| `cortex ci validate-pr` | Valida un PR contra su Session + spec. Flags: `--base-branch`, `--head-branch`, `--base-commit`, `--head-commit`, `--diff <path>`, `--session <ID>`, `--format json\|text\|pr-comment`, `--project-root`. Exit codes `0/1/2/3` = `pass/warn/blocked/error`. |
| `cortex ci open-review-session` | Abre una review session dedicada al PR (modo `CI_REVIEW`). |
| `cortex ci report-checkpoint` | Appendea un checkpoint `CI_BOT` a la review session activa. |
| `cortex ci close-review-session` | Cierra la review session y persiste el resumen. |

### Comandos Autopilot

| Comando | Descripción |
| --- | --- |
| `cortex autopilot start` | Adopta la sesión activa bajo un modo (`--mode observe\|assist\|autopilot`). |
| `cortex autopilot preflight` | Dry-run del pipeline de detectors (sin mutar estado). |
| `cortex autopilot checkpoint` | Appendea un checkpoint a la sesión activa. |
| `cortex autopilot finish` | Cierra la sesión activa; con `--auto` corre la pipeline canónica del documenter. |
| `cortex autopilot status` | Estado de la sesión activa o de la indicada. |
| `cortex autopilot doctor` | Diagnóstico del módulo. |

> Los subcomandos `install`, `uninstall`, `cleanup` y `report` fueron retirados. Usá `cortex session hooks ...` para gestión de hooks y `cortex session list` para auditoría.

### Comandos Enterprise

| Comando | Descripción |
| --- | --- |
| `cortex org-config` | Muestra configuración enterprise resuelta (`--json`). |
| `cortex promote-knowledge` | Promueve conocimiento al vault enterprise (`--dry-run`/`--apply`). |
| `cortex review-knowledge` | Aprueba/rechaza candidatos de promoción (`--approve`/`--reject`). |
| `cortex sync-enterprise-vault` | Valida e indexa el vault enterprise. |
| `cortex memory-report` | Reporte de salud y promociones (`--scope`, `--json`). |

### Comandos Work Items y PR Context

| Comando | Descripción |
| --- | --- |
| `cortex hu import \| list \| show` | Gestión de HU/work items (Jira read-only). |
| `cortex pr-context capture \| store \| search \| generate \| full` | Pipeline DevSecDocOps de PRs. |
| `cortex inject` / `cortex sync-ide` | Configuración de IDEs. |
| `cortex webgraph serve \| export` | Visualización del grafo de conocimiento. |

---

## Plugin de CI

Un único comando valida un PR contra su Session + spec, con tres niveles independientes:

- **Nivel 1 — Validation gate**: `cortex ci validate-pr` cruza el `git diff` con `files_in_scope`, corre los `verification_hooks` y emite JSON / texto. El exit code (`0/1/2/3`) es el gate.
- **Nivel 2 — PR comment sticky**: `cortex ci validate-pr --format pr-comment` emite Markdown delimitado por el sentinel `<!-- cortex-pr-summary -->` para deduplicación con `gh pr comment --edit-last`.
- **Nivel 3 — Review sessions**: `cortex ci open-review-session` / `report-checkpoint` / `close-review-session` driveean una Session dedicada al PR (modo `CI_REVIEW`).

**Templates listos para copiar:**

- `templates/ci/github-actions-cortex-validate.yml`
- `templates/ci/gitlab-ci-cortex-validate.yml`
- `templates/ci/README.md` con tips de adopción.

---

## Servidor MCP

Cortex expone sus capacidades vía **Model Context Protocol (MCP)**. El servidor se inicia con `cortex mcp-server --project-root <ruta>`.

**Herramientas MCP disponibles:**

**Retrieval / contexto / governance:**

- `cortex_ping` — health-check con `last_error_seen` rolling buffer.
- `cortex_search`, `cortex_search_vector` — búsqueda híbrida y vectorial.
- `cortex_context` — enriquecimiento de contexto (acepta `task_type` para dimensionar el budget).
- `cortex_sync_ticket` — inyección de contexto previo a la spec.
- `cortex_create_spec` — creación de spec (soporta `verification_hooks`, `proposal_mode`, `with_tasks`).
- `cortex_emit_proposal` — emisión de propuesta previa (Sub-fase 09.A).
- `cortex_save_session`, `cortex_write_doc`, `cortex_self_review_note` — persistencia de notas.
- `cortex_sync_vault` — re-indexación del vault.
- `cortex_import_hu`, `cortex_get_hu` — work items.

**Session primitive (Pluggable Middle):**

- `cortex_session_open`, `cortex_session_checkpoint`, `cortex_session_close`, `cortex_session_status`, `cortex_session_list`.
- `cortex_finish_session`, `cortex_close_session`.
- `cortex_documenter_briefing` — payload completo para que el documenter trabaje.
- `cortex_session_task_list`, `cortex_session_task_update` (también create-or-update con `description`).
- `cortex_review_checkpoint` — review en dos etapas (spec compliance + quality).
- `cortex_write_design_note_canonical` — nota de diseño canónica (Sub-fase 09.B).

**Legacy / single-agent IDE:**

- `cortex_validate_handoff`, `cortex_verify_session_claims` — mantenidos para Codex y otros IDEs sin checkpoints nativos. Emiten `DeprecationWarning`.

**Autopilot:**

- `cortex_autopilot_start`, `cortex_autopilot_preflight`, `cortex_autopilot_checkpoint`, `cortex_autopilot_finish`, `cortex_autopilot_status`.

---

## Instalación

### Prerrequisitos

- **Python 3.11** o superior
- **Git 2.30** o superior
- **pip 22.0** o superior
- *(Opcional)* `pipx` si querés usar Cortex como herramienta global multi-proyecto

### Opción A — `pipx` (recomendada para uso multi-proyecto)

`pipx` instala Cortex en un entorno aislado y publica el comando `cortex` global para tu usuario:

```bash
# 1. Clonar el repo donde quieras (ej.: tu carpeta personal)
git clone https://github.com/MachuaninEzequiel/Cortex.git C:\Cortex

# 2. Instalar con pipx en modo editable
pipx install --editable C:\Cortex

# Variante con extras opcionales
pipx install --editable "C:\Cortex[all]"

# Actualizar Cortex tras un `git pull`
pipx upgrade cortex-memory

# Desinstalar
pipx uninstall cortex-memory
```

> En modo `--editable` los cambios del código se aplican automáticamente al hacer `git pull`. Sólo necesitás `pipx upgrade cortex-memory` cuando cambien las dependencias en `pyproject.toml`.

### Opción B — `.venv` por proyecto (uso puntual)

```bash
cd D:\MiProyecto
python -m venv .venv

# Windows (PowerShell): .venv\Scripts\Activate.ps1
# Windows (CMD):        .venv\Scripts\activate.bat
# Linux / macOS:        source .venv/bin/activate

pip install -e C:\Cortex
# o con extras:
pip install -e "C:\Cortex[all]"
```

### Opción C — Desarrollo / contribuir

```bash
git clone https://github.com/MachuaninEzequiel/Cortex.git
cd Cortex
python -m venv .venv
# Activar (ver arriba)
pip install -e ".[dev]"
pre-commit install

ruff check .
pytest
mypy cortex/
```

### Inicialización en tu proyecto

```bash
cd D:\MiProyecto
cortex setup agent
```

Esto crea el workspace `.cortex/` (Workspace v2) con `config.yaml`, `vault/`, `memory/`, `skills/`, `subagents/`, `workspace.yaml`, `org.yaml` y `.github/workflows/`.

### Verificación

```bash
cortex doctor                    # Estado general (sections [sessions], [autopilot], [pluggable_middle])
cortex doctor --scope enterprise # Estado enterprise
cortex org-config                # Configuración enterprise resuelta
cortex stats                     # Estadísticas de memoria
```

### Dependencias opcionales

```bash
pip install "cortex-memory[local]"     # sentence-transformers + PyTorch (~2.5GB)
pip install "cortex-memory[openai]"    # Backend OpenAI
pip install "cortex-memory[anthropic]" # Backend Claude
pip install "cortex-memory[ollama]"    # LLMs locales
pip install "cortex-memory[webgraph]"  # UI de visualización
pip install "cortex-memory[all]"       # Todo
```

---

## Configuración por IDE

### Pi Coding Agent (recomendado)

Pi es el entorno de ejecución **recomendado** por Cortex. Ofrece Intelligent Routing, gobernanza de capas y un Premium Dashboard dedicado. Cortex provee un setup completo en `cortex-pi/` con agentes, skills, extensiones TypeScript y task runner integrado.

```bash
# Prerrequisitos
npm install -g @mariozechner/pi-coding-agent

# Task runner (just)
# macOS:    brew install just
# Windows:  winget install Casey.Just   (o scoop install just / choco install just)

# Iniciar
just cortex            # Dashboard principal
just sdd               # Pipeline SDDwork completo
just hotfix            # Fast Track directo
just audit             # Auditoría de calidad
```

**Teams disponibles:**

| Team | Uso |
| --- | --- |
| `cortex-sddwork` | Feature completa (sync → SDDwork → security → test → doc) |
| `cortex-hotfix` | Fix urgente (Fast Track) |
| `cortex-research` | Investigación |
| `cortex-audit` | Auditoría de código |

**Subagentes bundled** (sincronizados desde `.cortex/subagents/`):
`cortex-code-explorer`, `cortex-code-designer`, `cortex-code-implementer`, `cortex-documenter`, `cortex-security-auditor`, `cortex-test-verifier`.

El comando `cortex inject --ide pi` corre un mirror canonical → bundle antes de copiar (`--sync-canonical` / `--no-sync-canonical`).

### Cursor

`Settings` → `MCP` → `Add Server`:

- Name: `cortex`
- Command: `python`
- Args: `-m cortex.cli.main mcp-server --project-root C:\ruta\al\proyecto`

### Claude Code / Claude Desktop / Antigravity

```json
{
  "mcpServers": {
    "cortex": {
      "command": "python",
      "args": ["-m", "cortex.cli.main", "mcp-server", "--project-root", "/ruta/al/proyecto"]
    }
  }
}
```

### VSCode (Cline / Roo)

`.vscode/mcp.json`:

```json
{
  "servers": {
    "cortex": {
      "command": "python",
      "args": ["-m", "cortex.cli.main", "mcp-server", "--project-root", "${workspaceFolder}"]
    }
  }
}
```

### Codex

`cortex inject --ide codex` escribe `.codex/AGENTS.md`, `.codex/mcp.json` (con `--project-root` absoluto), `.codex/skills/` y `.codex/agents/`. Codex opera en modo single-agent: la "delegación" se hace por convención y la sesión se cierra manualmente con `cortex finish-session`.

### opencode

`cortex inject --ide opencode` configura los agents bajo `.opencode/` y, opcionalmente, instala el hook nativo:

```bash
cortex session hooks install --ide opencode
```

### Inyección rápida

```bash
cortex inject --ide cursor
cortex inject --ide claude-code
cortex inject --ide opencode
cortex inject --ide pi
cortex inject --ide codex
cortex inject                     # menú interactivo
```

---

## Configuración YAML

### `.cortex/config.yaml` (runtime local)

```yaml
episodic:
  persist_dir: .cortex/memory/chroma
  collection_name: cortex_episodic
  embedding_model: all-MiniLM-L6-v2
  embedding_backend: onnx           # onnx | local | openai

semantic:
  vault_path: .cortex/vault

retrieval:
  top_k: 5
  episodic_weight: 1.0
  semantic_weight: 1.0

context_enricher:
  min_score: 0.1
  domain_confidence: 0.5
  max_items: 8
  max_chars: 2000
  multi_match_boost: 1.5
  co_occurrence_boost: 0.3
  strategies:
    topic: true
    files: true
    keywords: true
    pr_title: true
    graph_expansion: true

documenter:
  default_mode: auto                # auto | interactive

llm:
  provider: none                    # none | openai | anthropic | ollama
  model: ""

pipeline:
  abort_early: true
  stages:
    security:
      enabled: true
      block_on_failure: true
      audit_level: high             # low | moderate | high | critical
    lint:
      enabled: true
      block_on_failure: true
    test:
      enabled: true
      block_on_failure: true
      min_coverage: 0
    documentation:
      enabled: true
      block_on_failure: false

integrations:
  jira:
    enabled: false
    base_url: "https://TU-DOMINIO.atlassian.net"
    email_env: JIRA_EMAIL
    token_env: JIRA_API_TOKEN
```

### `.cortex/org.yaml` (enterprise)

```yaml
schema_version: 1
organization:
  name: "Mi Empresa"
  slug: "mi-empresa"
  profile: "multi-project-team"    # small-company | multi-project-team | regulated-organization | custom

memory:
  mode: layered
  enterprise_vault_path: vault-enterprise
  enterprise_memory_path: memory/enterprise/chroma
  enterprise_semantic_enabled: true
  enterprise_episodic_enabled: false
  project_memory_mode: isolated
  branch_isolation_enabled: false
  retrieval_default_scope: all     # local | enterprise | all
  retrieval_local_weight: 1.0
  retrieval_enterprise_weight: 1.2

promotion:
  enabled: true
  allowed_doc_types: [spec, decision, runbook, hu, incident]
  require_review: true
  default_targets: [enterprise_vault]

governance:
  git_policy: balanced             # balanced | strict | custom
  ci_profile: advisory             # observability | advisory | enforced
  version_sessions_in_git: false

integration:
  github_actions_enabled: true
  webgraph_workspace_enabled: true
  ide_profiles: []
```

---

## Estructura del proyecto

```
Cortex/
├── cortex/                       # Núcleo del Sistema (AgentMemory)
│   ├── cli/                      # Interfaz Typer
│   │   ├── main.py               # entrypoint + sub-apps (session, ci, autopilot, …)
│   │   ├── session.py            # `cortex session ...`
│   │   ├── session_tui.py        # TUI viva con `rich`
│   │   ├── ci.py                 # `cortex ci ...` (plugin)
│   │   └── _unicode_fallback.py  # Degrade ASCII para consolas legacy (cp1252)
│   ├── core.py                   # Fachada Principal (AgentMemory)
│   ├── session/                  # PRIMITIVA Session
│   │   ├── models.py             # SessionRecord, Checkpoint, VerificationHook, Task
│   │   ├── service.py            # SessionService: open / checkpoint / close / list
│   │   ├── storage.py            # Persistencia atómica YAML en .cortex/sessions/
│   │   ├── git.py                # HEAD / branch / diff (con placeholder gitless)
│   │   ├── verification.py       # VerificationRunner con timeout + truncation
│   │   ├── proposal.py           # Gate del proposal de cortex-sync
│   │   ├── quality_gates.py      # cortex_review_checkpoint
│   │   └── hooks/                # Installer de IDE hooks (claude-code, cursor, opencode, pi)
│   ├── documenter/               # Pipeline de reconstrucción
│   │   ├── reconstruction.py     # Algoritmo de 8 pasos
│   │   ├── spec_loader.py
│   │   ├── diff_parser.py
│   │   ├── contradiction_detector.py
│   │   ├── adr_evaluator.py
│   │   ├── persistence.py        # DocumenterPersister + self-review
│   │   └── interactive.py        # UI guiada con `rich`
│   ├── ci/                       # Plugin de CI provider-agnostic
│   │   ├── validator.py          # CiValidator + validate_pull_request
│   │   ├── session_matcher.py
│   │   ├── diff_io.py
│   │   ├── markdown_formatter.py # PR-comment sticky
│   │   ├── result.py
│   │   └── review_session.py     # Review sessions CI-owned
│   ├── autopilot/                # Policy + lifecycle sobre Sessions
│   │   ├── policies.py
│   │   ├── service.py
│   │   ├── lifecycle.py
│   │   ├── doctor.py
│   │   └── detectors/
│   ├── services/                 # Servicios de dominio
│   │   ├── spec_service.py       # Validación + persistencia de specs
│   │   ├── note_service.py       # Persistencia transaccional de session notes
│   │   └── pr_service.py         # Intake de PRs + fallback docs
│   ├── handoff.py                # AgentHandoff (kept para Legacy YAML mode)
│   ├── enterprise/               # Capa Enterprise Corporativa
│   ├── pipeline/                 # Abstracciones DevSecDocOps (CI/CD Gates)
│   ├── episodic/                 # ChromaDB + RRF
│   ├── semantic/                 # Vault Markdown
│   ├── retrieval/                # Adaptive RRF
│   ├── embedders/                # Factory (ONNX / local / openai)
│   ├── context_enricher/         # Enriquecimiento + budget_resolver task-aware
│   ├── documentation/            # Sistema canónico (doc_type, schemas, templates, writers)
│   ├── workspace/                # WorkspaceLayout — resolución central de rutas
│   ├── mcp/                      # Servidor MCP
│   ├── setup/                    # Orquestador (Agent/Pipeline/Full/Enterprise/WebGraph)
│   ├── webgraph/                 # Visualización del grafo
│   ├── workitems/                # Integración Jira (read-only)
│   └── ide/                      # Adaptadores IDE + canonical_tools
├── cortex-pi/                    # Entorno Pi Agent (Premium Edition)
├── templates/
│   └── ci/                       # GitHub Actions / GitLab CI listos para el plugin
├── tests/
│   ├── unit/                     # session/, documenter/, ci/, cli/, …
│   ├── integration/              # MCP, CLI, telemetría
│   └── e2e/                      # managed_flow, observed_flow, byo_flow, proposal_flow
├── docs/
│   ├── architecture/             # session-primitive, pluggable-middle-overview, ci-plugin, review-sessions
│   ├── pluggable-middle/         # Arquitectura canónica + planes de implementación
│   ├── enterprise/               # Manifiesto (este doc), backlogs, planes y bitácoras
│   ├── autopilot/                # Plan, contratos y tests
│   ├── business/                 # Plan de adopción (md/html/pdf)
│   ├── simulacion/               # Simulación día-a-día
│   ├── BusinessSignal/           # Propuesta: inteligencia de negocio sobre memoria
│   └── refact/                   # Specs de refactorización
├── .github/workflows/            # CI/CD Pipelines (PR, Enterprise, Security, Release)
├── .cortex/                      # Cortex Workspace v2
├── CHANGELOG.md
└── pyproject.toml
```

---

## Testing y calidad

- **Coverage objetivo**: >85%.
- **Linting**: Ruff (`ruff check .` / `ruff format .`).
- **Type checking**: Mypy (`mypy cortex/`). Módulo `cortex.documentation.*` corre bajo `mypy --strict`.
- **Pre-commit hooks**: automáticos en dev mode.
- **CI/CD**: GitHub Actions con pipeline DevSecDocOps + Enterprise Governance.
- **Property-Based Testing**: Hypothesis para algoritmos complejos (RRF).
- **Suites dedicadas**: `tests/unit/{session,documenter,ci,cli,services}/` + `tests/e2e/test_{managed,observed,byo,proposal,interactive}_flow.py`.

```bash
ruff check .
ruff format .
pytest --cov=cortex --cov-report=term-missing
mypy cortex/
cortex doctor --scope all
cortex memory-report --json
```

---

## Enterprise Memory Productization

| Epic | Estado | Descripción |
| --- | --- | --- |
| E1 - Modelo Organizacional | ✅ Completado | Topología formal declarativa (`.cortex/org.yaml`) |
| E2 - Retrieval Multi-nivel | ✅ Completado | Consulta local + enterprise con trazabilidad |
| E3 - Promotion Pipeline | ✅ Completado | Promoción auditable de conocimiento |
| E4 - Gobernanza y CI | ✅ Completado | Políticas automáticas de memoria en CI |
| E5 - Setup Enterprise | ✅ Completado | Instalación guiada con wizard y presets |
| E6 - Observabilidad | ✅ Completado | Salud de memoria, promotion reporting, WebGraph |
| E7 - Presets, Docs, Hardening | ✅ Completado | Documentación final, adopción, cierre |

---

<div align="center">

**Cortex: La memoria dejó de ser el pasado. Ahora es infraestructura corporativa.**

</div>
