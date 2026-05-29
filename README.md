<div align="center">
  <br />
    <a href="https://github.com/MachuaninEzequiel/Cortex" target="_blank">
      <img src="assets/logo.png" alt="Cortex Logo" width="500">
    </a>
  <br />

  <h1>CORTEX</h1>

  <p>
    <strong>Calidad, Seguridad, Documentación y Memoria Corporativa como sistema de gobernanza para Organizaciones y DevAgents</strong>
  </p>

  <p>
    <a href="https://github.com/MachuaninEzequiel/Cortex"><img src="https://img.shields.io/badge/Architecture-Pluggable--Middle-orange.svg" alt="Architecture" /></a>
    <a href="https://github.com/MachuaninEzequiel/Cortex"><img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python 3.11+" /></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT" /></a>
  </p>

</div>

---

## El Manifiesto Cortex: Gobernanza Total + Memoria Corporativa

En la era de los agentes de IA, la **Amnesia de Sesión** es el mayor enemigo de la productividad. Los agentes convencionales inician cada tarea en blanco, ignorando las decisiones arquitectónicas pasadas, las vulnerabilidades detectadas y el contexto histórico de tu negocio.

**Cortex redefine la relación humano-agente.** No es solo una base de conocimientos; es un **Sistema de Gobernanza** que obliga a la IA a seguir un ciclo de vida disciplinado de ingeniería de software. Cortex escala esta gobernanza al nivel **corporativo**: memoria institucional, promoción auditable de conocimiento, retrieval multi-nivel y observabilidad operativa, todo gobernado por una topología declarativa (`org.yaml`).

>  Para un documento exhaustivo del estado completo de Cortex, consultá el [Manifiesto Cortex](docs/enterprise/MANIFIESTO-CORTEX-ENTERPRISE.md).

---

## ¿Por qué Cortex?

| Problema | Solución Cortex |
| --- | --- |
| Agentes olvidan contexto entre sesiones | Memoria Híbrida RRF persistente (local + enterprise) |
| Specs vagos sin criterio objetivo de éxito | `verification_hooks` ejecutables declarados en cada spec |
| Sin trazabilidad de decisiones arquitectónicas | ADRs sugeridos desde los checkpoints + Especificaciones técnicas (`create-spec`) |
| Cada IDE trabaja distinto | Pluggable Middle: Cortex se adapta al modo de trabajo (Managed / Observed / BYO) |
| Documentación que envejece sola | Documenter por reconstrucción: compara spec vs. `git diff` real al cerrar |
| Vulnerabilidades detectadas tarde | SecuritySubAgent en tiempo real |
| Tests como afterthought | TestSubAgent integrado en flujo |
| PRs sin trazabilidad de lo prometido vs. entregado | Plugin de CI valida cada PR contra su Session + spec |
| Conocimiento aislado por proyecto | Promotion Pipeline hacia vault corporativo |
| Sin visibilidad sobre salud de memoria | `memory-report` con JSON estable + TUI viva de sesiones |
| Configuración enterprise compleja | Setup guiado con presets por industria |
| Cambio de contexto manual entre tareas | Autopilot: capa autónoma opt-in con políticas |
| Workspace disperso en la raíz del repo | Layout v2: todo en `.cortex/`, `WorkspaceLayout` central |

---

## Modelo de Ejecución: Pluggable Middle

Cortex envuelve cada unidad de trabajo en tres puntos: **sync** (antes), **middle** (durante) y **documenter** (después). Sync y documenter son fijos; el middle es **pluggable** y admite tres modos según cómo quieras (o puedas) trabajar.

### 1. `cortex-sync` — El Analista

Recupera contexto histórico del Vault y de la memoria episódica para refinar los requisitos. Produce una `Spec` con `verification_hooks` ejecutables (comandos que prueban objetivamente que el trabajo está hecho) y **abre la Session automáticamente** al persistir el spec.

Sub-paso opcional: emisión de una **propuesta** previa a la spec (`--proposal-mode optional|required|skip`) para alinear con el usuario antes de comprometer alcance.

### 2. Middle (Pluggable)

| Modo | Quién hace el trabajo | Cuándo usarlo |
|---|---|---|
| 🟢 **Managed** | `cortex-SDDwork` + subagents (Fast/Deep Track) | Sin tooling propio o querés disciplina forzada. |
| 🟡 **Observed** | Tu agente / skills + IDE hooks | Tenés tus skills/agentes preferidos; Cortex observa los checkpoints. |
| 🔵 **BYO** | Lo que sea (manual, otro agente, vibe coding) | Máxima libertad; Cortex reconstruye desde el diff observable. |

El modo **se infiere al cerrar** a partir de las fuentes de checkpoint registradas: sin checkpoints → BYO; sólo fuentes Cortex → Managed; cualquier otra → Observed. En los tres modos, cada paso significativo del middle puede emitir un **checkpoint** en la Session vía `cortex_session_checkpoint`. El contrato inter-agente es la **Session**, no YAML inline.

**Deep Track (Managed) — pipeline de subagents:**

`cortex-code-explorer` → `cortex-code-designer` → `cortex-code-implementer` → wrap-up. El designer puede saltearse con una nota mínima cuando `task_type == "docs-only"`.

```
Especificación → [Fast Track | Deep Track] → SecuritySubAgent → TestSubAgent → [Loop hasta aprobar]
```

**IDE hooks para el modo Observed:**

| IDE | Soporte | Mecanismo | Comando |
|---|---|---|---|
| Claude Code | ✓ Nativo | Hook `PostToolUse` en `.claude/settings.json` | `cortex session hooks install --ide claude-code` |
| Cursor / VSCode / Cline / Roo | ✓ Vía git | `.git/hooks/post-commit` (independiente del IDE) | `cortex session hooks install --ide cursor` |
| opencode | ✓ Nativo | Bloque markdown en `.opencode/hooks.md` | `cortex session hooks install --ide opencode` |
| Pi Coding Agent | ✓ Nativo | Recipes en `justfile` | `cortex session hooks install --ide pi` |
| Codex | ❌ Sin hooks | — (modo BYO con `cortex finish-session` manual) | — |

Inspeccionar/desinstalar:

```bash
cortex session hooks list           # tabla con estado de cada IDE
cortex session hooks status         # idem (formato detallado)
cortex session hooks uninstall --ide cursor
```

Los hooks emiten checkpoints con `source=ide-hook`. Si Cortex no está disponible o falla, el hook **no aborta** la operación del IDE (garantizado por `|| true` en los scripts shell y por `try/except` en los hooks JSON nativos).

### 3. `cortex-documenter` — El Guardián

Paso final via `cortex finish-session` (CLI) o `cortex_finish_session` (MCP). Reconstruye el contexto desde la Session: carga el spec, computa `git diff`, ejecuta los verification hooks, detecta scope drift, evalúa candidatos ADR, y persiste el session note + ADRs. Cierra la Session como `CLOSED` o `HANDOFF` según los resultados.

**Dos modos de documenter:**

- **`auto` (default)** — corre la pipeline completa sin pedir nada. `cortex finish-session` la usa por default.
- **`interactive`** — renderiza el draft + ADRs sugeridos en consola, permite editar título/cuerpo via `$EDITOR`, aprobar/rechazar ADRs uno por uno, o forzar HANDOFF / cancelar. Activarlo:
  - flag CLI: `cortex finish-session --interactive`.
  - default per-proyecto: `documenter.default_mode: interactive` en `.cortex/config.yaml`.

---

## La primitiva Session

La **Session** es el YAML atómico que ancla el ciclo de vida de cada unidad de trabajo, desde `create-spec` hasta `finish-session`. Vive en `.cortex/sessions/<session_id>.yaml`; el pointer `.cortex/sessions/active.txt` marca la sesión activa.

Captura: identidad (`session_id`, `spec_path`), snapshot (`start_commit`, `start_branch`, `opened_at`), live state (`status`, `mode`), enriquecimiento (`checkpoints` append-only, `verification_results`, `tasks` opt-in) y cierre (`closed_at`, `end_commit`, `documenter_decision`, `session_note_path`, `adrs_created`).

### Verification hooks

Cada spec declara uno o más `verification_hooks`: comandos ejecutables que **prueban** que el trabajo está hecho. El documenter los corre al cerrar.

```bash
cortex create-spec --title "Auth JWT" --goal "Implementar refresh tokens" \
  --verification-hook "name=tests;command=pytest tests/auth/" \
  --verification-hook "name=types;command=mypy src/auth.py" \
  --verification-hook "name=lint;command=ruff check src/auth.py;required=false"
```

Hooks `required=true` (default) que fallen fuerzan la Session a cerrar como `HANDOFF`. Hooks `required=false` registran el resultado pero no bloquean. Para tareas de research/docs el hook puede ser una presencia: `command=test -f docs/research-output.md`.

---

## Novedades Recientes

###  Cortex Autopilot

Autopilot es una capa autónoma **opt-in** que aplica políticas (warnings, blocks, auto-checkpoints) sobre la primitiva Session sin que el usuario tenga que orquestar manualmente el flujo Pluggable Middle. Es un wrapper delgado sobre `SessionService`: la API CLI se mantiene como atajo.

```bash
cortex autopilot start --mode assist    # Adopta la sesión activa
cortex autopilot preflight              # Dry-run del pipeline de detectors
cortex autopilot checkpoint             # Guardar punto de control
cortex autopilot finish --auto          # Cierre y session note automática
cortex autopilot doctor                 # Diagnóstico del módulo
```

**Tres modos de operación:**

| Modo | Comportamiento |
| --- | --- |
| `observe` | Registra sin intervenir. Ideal para adopción gradual. |
| `assist` | Sugiere acciones y pide cierre. Default recomendado. |
| `autopilot` | Preflight y cierre automáticos con políticas activas. |

> Los hooks de IDE ahora se gestionan con `cortex session hooks install|uninstall|list|status --ide <name>`. La auditoría de sesiones se hace con `cortex session list`.

---

### CI Plugin (provider-agnostic)

Un único comando valida un PR contra la Session que lo originó: cruza el `git diff` con `files_in_scope` del spec, corre los `verification_hooks`, y emite el resultado en JSON, texto o **comentario sticky de PR**. Exit codes: `0 pass / 1 warn / 2 blocked / 3 error` — listos para ser gate de CI.

```bash
cortex ci validate-pr --base-branch main --head-branch feature/x
cortex ci validate-pr --format pr-comment   # Markdown con sentinel marker

# Review session dedicada al PR (modo CI_REVIEW)
cortex ci open-review-session
cortex ci report-checkpoint --note "validación pasada"
cortex ci close-review-session
```

Templates listos para copiar en `templates/ci/`:

- `github-actions-cortex-validate.yml`
- `gitlab-ci-cortex-validate.yml`

---

### Sessions TUI

Vista en vivo de la primitiva Session con `rich`. Refresca cada `N` segundos (default 1.5, rango 0.5–30) y se adapta al ancho de la terminal:

```bash
cortex session watch                     # sesión activa
cortex session watch <ID> --refresh 3    # otra sesión
cortex session show <ID> --watch         # alias enfocado
```

Muestra: panel de sesión activa, checkpoints recientes, diff preview truncado, status de verificaciones y sidebar de sesiones recientes. `Ctrl+C` sale limpio.

---

###  Workspace Layout v2

El setup de Cortex consolida **toda** la infraestructura en un único directorio `.cortex/`, eliminando archivos sueltos en la raíz del repo:

```
.cortex/              ← todo Cortex aquí
  config.yaml
  vault/              ← specs/, sessions/, designs/, adrs/, …
  vault-enterprise/
  sessions/           ← <id>.yaml + active.txt
  memory/
  enterprise-memory/
  skills/
  subagents/
  org.yaml
  workspace.yaml      ← layout_version: 2
  webgraph/
  logs/
  scripts/
.github/workflows/    ← único elemento fuera de .cortex (requerido por GitHub)
```

La resolución de rutas está centralizada en `WorkspaceLayout` (`cortex/workspace/layout.py`), que soporta dual-discovery (layout nuevo y legacy) de forma transparente. Los repos inicializados con versiones anteriores siguen funcionando sin migración manual.

---

## Pilares Tecnológicos

### Memoria Híbrida RRF + Enterprise

- **Capa Episódica**: ChromaDB con embeddings ONNX (`<1ms` latency).
- **Capa Semántica**: Vault Markdown (Obsidian-compatible).
- **Capa Enterprise**: Vault corporativo con retrieval multi-nivel y scopes `local`/`enterprise`/`all`.
- **Fusión**: True RRF cross-source con pesos configurables por scope.

### Enterprise Memory Layer

- **`.cortex/org.yaml`**: Topología declarativa con schema versionado.
- **Presets**: `small-company`, `multi-project-team`, `regulated-organization`, `custom`.
- **Promotion Pipeline**: `candidate` → `reviewed` → `promoted` con trazabilidad completa.
- **Gobernanza CI**: Perfiles `observability` / `advisory` / `enforced`.
- **Observabilidad**: `cortex memory-report` con salida humana y JSON.

### Quality Gates (managed)

Cinco mecanismos que la pipeline corre inline:

1. **Rollback transaccional** en `NoteService.create` — garantía *"file on disk ⇒ file indexed"*.
2. **`cortex_review_checkpoint`** — review en dos etapas (spec compliance + quality) sobre cualquier checkpoint de una sesión abierta.
3. **Self-review del documenter** — surface placeholders y claims huecos antes de persistir.
4. **Budget task-aware** en `cortex_context` — pasá `task_type` y `(top_k, max_chars)` se dimensionan solos.
5. **Template condicional `session.md.j2`** — renderiza `question-only` / `docs-only` / `security` / `fast-code` / `deep-code` según el `task_type` del spec.

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

---

## CLI Reference

### Comandos Core

| Comando | Descripción |
| --- | --- |
| `cortex setup agent` | Configura Vault, Memoria, Skills y MCP. |
| `cortex setup pipeline` | Configura GitHub Actions y auditoría. |
| `cortex setup full` | Instalación completa (Agent + Pipeline + WebGraph). |
| `cortex setup webgraph` | Configura visualización de grafos. |
| `cortex setup enterprise` | Setup enterprise con wizard o presets. |
| `cortex init` | Alias rápido para `setup agent`. |
| `cortex create-spec` | Define metas, criterios y `verification_hooks`. Abre la Session automáticamente. Flags: `--verification-hook`, `--proposal-mode`, `--with-tasks`. |
| `cortex finish-session [ID]` | Cierra la Session vía la pipeline de reconstrucción del documenter. Flags: `--handoff`, `--abandon`, `--reason`, `--interactive`, `--json`. |
| `cortex save-session` | Persiste cambios y decisiones en el Vault (modo legacy / single-agent IDE). |
| `cortex search` | Búsqueda híbrida RRF (`--scope local\|enterprise\|all`). |
| `cortex context` | Inyecta contexto basado en archivos modificados (acepta `--task-type`). |
| `cortex doctor` | Valida entorno (`--scope project\|enterprise\|all`). |
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

| Comando | Descripción |
| --- | --- |
| `cortex session current` | Id de la sesión activa (o `(no active session)`). |
| `cortex session list` | Lista sesiones (`--status open\|closed\|handoff\|abandoned`, `--json`). |
| `cortex session show [ID]` | Detalle completo de una sesión (default: la activa). Con `--watch` abre la TUI viva. |
| `cortex session watch [ID] [--refresh N]` | TUI viva: refresca cada `N` segundos, muestra checkpoints, diff preview, verification status y sidebar de sesiones recientes. |
| `cortex session diff [ID]` | `git diff start_commit..HEAD` de la sesión. |
| `cortex session task list \| done \| in-progress \| skip \| block` | Tasks granulares (opt-in con `cortex create-spec --with-tasks`). |
| `cortex session switch <ID>` | Cambia la sesión activa. |
| `cortex session abandon <ID> --reason X` | Cierra como `abandoned` sin generar session note. |
| `cortex session checkpoint --source <s> --note "..." [--verified-claim X] [--artifact path]` | Appendea un checkpoint a la sesión activa. |
| `cortex session hooks list \| status \| install \| uninstall --ide <name>` | Gestiona hooks de IDE para el modo Observed. |
| `cortex finish-session [ID]` | Cierra la sesión vía documenter. Flags: `--handoff`, `--abandon`, `--reason`, `--interactive`/`--no-interactive`, `--json`. |

> Las sesiones se crean automáticamente al ejecutar `cortex create-spec`.

### Comandos CI Plugin

| Comando | Descripción |
| --- | --- |
| `cortex ci validate-pr` | Valida un PR contra su Session + spec. Flags: `--base-branch`, `--head-branch`, `--base-commit`, `--head-commit`, `--diff`, `--session`, `--format json\|text\|pr-comment`. Exit codes 0/1/2/3 = pass/warn/blocked/error. |
| `cortex ci open-review-session` | Abre una review session dedicada al PR (modo `CI_REVIEW`). |
| `cortex ci report-checkpoint` | Appendea un checkpoint `CI_BOT` a la review session activa. |
| `cortex ci close-review-session` | Cierra la review session y persiste el resumen. |

### Comandos Autopilot

| Comando | Descripción |
| --- | --- |
| `cortex autopilot start` | Adopta la sesión activa bajo un modo (`--mode observe\|assist\|autopilot`). |
| `cortex autopilot preflight` | Dry-run del pipeline de detectors. |
| `cortex autopilot checkpoint` | Appendea un checkpoint a la sesión activa. |
| `cortex autopilot finish` | Cierra la sesión activa; con `--auto` corre la pipeline canónica del documenter. |
| `cortex autopilot status` | Estado de la sesión activa o de la indicada. |
| `cortex autopilot doctor` | Diagnóstico del módulo. |

### Comandos Enterprise

| Comando | Descripción |
| --- | --- |
| `cortex org-config` | Muestra configuración enterprise resuelta (`--json`). |
| `cortex promote-knowledge` | Promueve conocimiento al vault enterprise (`--dry-run\|--apply`). |
| `cortex review-knowledge` | Aprueba/rechaza candidatos de promoción (`--approve\|--reject`). |
| `cortex sync-enterprise-vault` | Valida e indexa el vault enterprise. |
| `cortex memory-report` | Reporte de salud y promociones (`--scope`, `--json`). |

### Comandos Adicionales

| Comando | Descripción |
| --- | --- |
| `cortex hu import/list/show` | Gestión de Work Items (Jira read-only). |
| `cortex pr-context capture/store/search/generate/full` | Pipeline DevSecDocOps de PRs. |
| `cortex inject` / `cortex sync-ide` | Configuración de IDEs. |
| `cortex webgraph serve/export` | Visualización de grafos de conocimiento. |

---

## Integración Universal (MCP Server)

> Cortex expone sus capacidades via **Model Context Protocol (MCP)**.

## Configuración por IDE

### Pi Coding Agent  (RECOMENDADO)

Pi es el entorno de ejecución **recomendado** por Cortex. Ofrece Intelligent Routing, Gobernanza de 5 Capas y un Premium Dashboard dedicado. Cortex proporciona un setup completo en `cortex-pi/` con agentes, skills, extensiones TypeScript y un task runner integrado.

```bash
# Prerrequisitos
npm install -g @mariozechner/pi-coding-agent

# Instalar just (Task runner)
# Mac/Linux: brew install just
# Windows: winget install Casey.Just  (o scoop install just / choco install just)

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

**Subagentes bundled** (sincronizados desde `.cortex/subagents/`): `cortex-code-explorer`, `cortex-code-designer`, `cortex-code-implementer`, `cortex-documenter`, `cortex-security-auditor`, `cortex-test-verifier`. El comando `cortex inject --ide pi` corre un mirror canonical → bundle antes de copiar (`--sync-canonical`/`--no-sync-canonical`).

---

### Cursor

`Settings` → `MCP` → `Add Server`: Name=`cortex`, Command=`python`, Args=`-m cortex.cli.main mcp-server --project-root C:\ruta\al\proyecto`

#### Antigravity / Claude Desktop

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

---

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

---

### Herramientas MCP disponibles

**Retrieval / contexto / governance:** `cortex_ping`, `cortex_search`, `cortex_search_vector`, `cortex_context` (acepta `task_type` para dimensionar el budget), `cortex_sync_ticket`, `cortex_create_spec` (soporta `verification_hooks`, `proposal_mode`, `with_tasks`), `cortex_emit_proposal`, `cortex_save_session`, `cortex_write_doc`, `cortex_self_review_note`, `cortex_sync_vault`, `cortex_import_hu`, `cortex_get_hu`.

**Session primitive (Pluggable Middle):** `cortex_session_open`, `cortex_session_checkpoint`, `cortex_session_close`, `cortex_session_status`, `cortex_session_list`, `cortex_finish_session`, `cortex_close_session`, `cortex_documenter_briefing`, `cortex_session_task_list`, `cortex_session_task_update`, `cortex_review_checkpoint`, `cortex_write_design_note_canonical`.

**Legacy / handoff:** `cortex_validate_handoff` y `cortex_verify_session_claims` (kept para el modo Legacy YAML — single-agent IDEs como Codex; emiten `DeprecationWarning`).

**Autopilot:** `cortex_autopilot_start`, `cortex_autopilot_preflight`, `cortex_autopilot_checkpoint`, `cortex_autopilot_finish`, `cortex_autopilot_status`.

---

## Instalación — Guía para Nuevos Usuarios

Esta guía te lleva desde cero hasta tener Cortex funcionando en tu máquina. No necesitás experiencia previa con el proyecto.

### Paso 0: Prerrequisitos

Antes de empezar, asegurate de tener instalado:

- **Python 3.11 o superior** — [Descargar Python](https://www.python.org/downloads/)
- **Git** — [Descargar Git](https://git-scm.com/downloads)
- **pipx** — recomendado si querés usar Cortex como herramienta global para varios proyectos

> **Tip**: Para verificar que los tenés, abrí una terminal y corré `python --version`, `git --version` y `pipx --version`. Si aparecen versiones, estás listo.

---

### Paso 1: Obtener el código fuente de Cortex

Primero, descargá el código de Cortex en algún lugar de tu equipo. Esto solo se hace una vez.

```bash
# Elegí dónde guardar el código base (ejemplo: tu carpeta personal)
cd ~

# Clonar el repositorio
git clone https://github.com/MachuaninEzequiel/Cortex.git C:\Cortex
```

---

### Paso 2: Elegir el modo de instalación

#### Opción recomendada: instalar Cortex con `pipx`

Recomendamos `pipx` como modalidad principal porque creemos que Cortex funciona mejor como un framework transversal a la organización: una herramienta de gobierno, memoria y automatización que puede operar sobre múltiples proyectos sin quedar atada al `.venv` de uno solo.

`pipx` instala Cortex en un entorno aislado propio y publica el comando `cortex` de forma global para tu usuario. Eso te permite usar Cortex desde cualquier repositorio, mantener sus dependencias separadas de tus proyectos y desinstalarlo fácilmente cuando quieras.

```bash
# Instalar Cortex desde el repo clonado en el Paso 1
pipx install --editable C:\Cortex

# Variante con extras opcionales
pipx install --editable "C:\Cortex[all]"

# Actualizar Cortex cuando haya cambios en el repo
# (después de hacer git pull en C:\Cortex)
pipx upgrade cortex-memory

# Desinstalar Cortex cuando ya no lo necesites
pipx uninstall cortex-memory
```

> **¿Cómo actualizo Cortex?** Si instalaste con `pipx` en modo `--editable`, los cambios del código se aplican automáticamente al hacer `git pull`. Si necesitás actualizar el entorno virtual de pipx (por ejemplo, porque agregamos dependencias nuevas a `pyproject.toml`), simplemente ejecutá `pipx upgrade cortex-memory`. No hace falta desinstalar y reinstalar.

#### Opción alternativa: instalar Cortex dentro del `.venv` del proyecto

Esta modalidad se recomienda solo para una prueba rápida dentro de un proyecto particular. Si no tenés un `.venv` ya creado en el proyecto donde querés probar Cortex, esta es una forma simple de levantarlo sin afectar otros repositorios. No es la opción principal si querés usar Cortex como herramienta habitual en varios proyectos.

```bash
# 1. Ir a TU proyecto
cd D:\MiProyecto

# 2. Crear el entorno virtual del proyecto
python -m venv .venv

# 3. Activarlo
# Windows (PowerShell): .venv\Scripts\Activate.ps1
# Windows (CMD):        .venv\Scripts\activate.bat
# Linux / macOS:        source .venv/bin/activate

# 4. Instalar Cortex desde el repo clonado en el Paso 1
pip install -e C:\Cortex

# Variante con extras opcionales
pip install -e "C:\Cortex[all]"
```

> En esta modalidad, el comando `cortex` queda disponible solo mientras ese `.venv` está activado.

---

### Paso 3: Inicializar Cortex en tu proyecto

Una vez instalado Cortex con `pipx` o dentro del `.venv`, navegá al proyecto donde querés usarlo e inicializá la memoria:

```bash
cd D:\MiProyecto
cortex setup agent
```

Esto crea en tu proyecto el layout `.cortex/` (Cortex Workspace v2):
- `.cortex/config.yaml` — Configuración de Cortex
- `.cortex/vault/` — Tu base de conocimiento (archivos Markdown)
- `.cortex/sessions/` — Sesiones activas y cerradas (YAML atómico)
- `.cortex/memory/` — Base de datos de memoria episódica (ChromaDB)
- `.cortex/skills/` — Habilidades de escritura de documentación
- `.cortex/subagents/` — Subagentes canónicos
- `.cortex/workspace.yaml` — Declaración de layout (v2)
- `.cortex/org.yaml` — Topología enterprise
- `.github/workflows/` — CI/CD pipelines

**A partir de acá, todos los comandos se corren desde la carpeta de tu proyecto:**

```bash
# Crear una especificación técnica con verification hooks
cortex create-spec --title "Auth JWT" --goal "Implementar refresh tokens" \
  --verification-hook "name=tests;command=pytest tests/auth/"

# Trabajar (el modo Managed / Observed / BYO depende de tu setup) ...

# Cerrar la sesión: el documenter reconstruye y persiste el session note
cortex finish-session

# Buscar en tu memoria (episódica + semántica)
cortex search "error handling en middleware"

# Ver la sesión activa en vivo
cortex session watch

# Verificar que todo esté sano
cortex doctor

# Ver estadísticas de tu memoria
cortex stats
```

---

### Paso 4: Conectar Cortex con tu IDE (Opcional)

Si usás un IDE con soporte MCP (Cursor, VSCode con Cline, Claude Desktop, opencode, Pi), Cortex puede funcionar como un servidor de herramientas para tu agente de IA:

```bash
# Desde la carpeta de tu proyecto:
cortex inject --ide cursor        # Para Cursor
cortex inject --ide claude-code   # Para Claude Code / Claude Desktop
cortex inject --ide opencode      # Para opencode
cortex inject --ide codex         # Para Codex
cortex inject --ide pi            # Para Pi
cortex inject                     # Menú interactivo para elegir IDE
```

O podés iniciar el servidor MCP manualmente:

```bash
cortex mcp-server --project-root D:\MiProyecto
```

Para activar el modo **Observed** (Cortex registra checkpoints automáticamente desde tu IDE):

```bash
cortex session hooks install --ide claude-code
cortex session hooks install --ide cursor       # vía .git/hooks/post-commit
cortex session hooks install --ide opencode
cortex session hooks install --ide pi
```

---

### Paso 5: Activar Autopilot (Opcional)

Si querés que Cortex opere de forma más autónoma, podés activar el módulo Autopilot:

```bash
# Iniciar Autopilot para una sesión
cortex autopilot start --mode assist
```

Autopilot es completamente opt-in y reversible.

---

### Resumen del flujo diario

```bash
# 1. Abrir terminal
# 2. Si instalaste Cortex en un .venv, activarlo ahora
# Windows (PowerShell): .venv\Scripts\Activate.ps1
# Linux / macOS:        source .venv/bin/activate

# 3. Ir al proyecto sobre el que vas a trabajar
cd D:\MiProyecto

# 4. Trabajar con Cortex
cortex search "lo que necesito recordar"
cortex create-spec --title "Mi Feature" --verification-hook "name=tests;command=pytest"
# ... codear ...
cortex finish-session             # Cierra la sesión y deja todo documentado
```

---
### ¿Querés contribuir al desarrollo de Cortex?

Si querés contribuir con código al proyecto, necesitás instalar las dependencias de desarrollo y los hooks de pre-commit. Lee la guía completa en [CONTRIBUTING.md](CONTRIBUTING.md).

### Enterprise

Para configurar Cortex en modo corporativo con topologías organizacionales, consultá la sección Enterprise del [Manifiesto Cortex](docs/enterprise/MANIFIESTO-CORTEX-ENTERPRISE.md#enterprise-memory-productization).

---

## Integración Jira (read-only)

```yaml
# En config.yaml
integrations:
  jira:
    enabled: true
    base_url: "https://TU-DOMINIO.atlassian.net"
    email_env: JIRA_EMAIL
    token_env: JIRA_API_TOKEN
```

```bash
cortex hu import PROJ-123
cortex hu list
cortex hu show PROJ-123
```

---

## 📁 Estructura del Proyecto

```
Cortex/
├── cortex/                    # Núcleo del Sistema (AgentMemory)
│   ├── cli/                   # Interfaz Typer (sub-apps: session, ci, autopilot, …)
│   ├── core.py                # Fachada Principal (Inyección de Servicios)
│   ├── session/               # PRIMITIVA Session (SessionRecord, hooks, verification)
│   ├── documenter/            # Pipeline de reconstrucción + persistencia + interactive UI
│   ├── ci/                    # CI plugin provider-agnostic (validate-pr + review sessions)
│   ├── autopilot/             # Capa de política + lifecycle sobre Sessions
│   ├── enterprise/            # Capa Enterprise Corporativa (org.yaml, promotion, reporting)
│   ├── services/              # Lógica de negocio (SpecService, NoteService, PRService)
│   ├── handoff.py             # AgentHandoff (kept para Legacy YAML / single-agent IDEs)
│   ├── pipeline/              # Abstracciones DevSecDocOps (CI/CD Gates)
│   ├── episodic/              # Memoria episódica (ChromaDB + RRF)
│   ├── semantic/              # Memoria semántica (Vault Markdown)
│   ├── retrieval/             # Motor de búsqueda híbrida adaptativo
│   ├── embedders/             # Factory de backends (ONNX, local, openai)
│   ├── context_enricher/      # Enriquecimiento proactivo + budget task-aware
│   ├── documentation/         # Sistema canónico (doc_type, schemas, templates, writers)
│   ├── workspace/             # WorkspaceLayout — resolución central de rutas
│   ├── mcp/                   # Servidor Model Context Protocol
│   ├── setup/                 # Orquestador (Agent/Pipeline/Full/Enterprise/WebGraph)
│   ├── webgraph/              # Visualización de grafos + nodos enterprise
│   ├── workitems/             # Integración Work Items (Jira)
│   └── ide/                   # Adaptadores IDE (Claude Code, Cursor, opencode, Codex, Pi)
├── cortex-pi/                 # Entorno Pi Agent (Premium Edition)
├── templates/
│   └── ci/                    # GitHub Actions / GitLab CI listos para el plugin
├── tests/                     # Suite (unit/, integration/, e2e/)
├── docs/
│   ├── enterprise/            # Manifiesto, planes y bitácoras Enterprise
│   ├── autopilot/             # Plan, contratos y estrategia de tests
│   ├── BusinessSignal/        # Propuesta: inteligencia de negocio sobre memoria
│   └── refact/                # Specs de refactorización (workspace, WebGraph)
├── .github/workflows/         # CI/CD Pipelines (PR, Enterprise, Security, Release)
├── .cortex/                   # Cortex Workspace v2 (new-layout default)
│   ├── config.yaml            # Configuración principal
│   ├── workspace.yaml         # Layout versión y proyectos
│   ├── vault/                 # Knowledge base (Obsidian compatible)
│   ├── sessions/              # Sessions YAML + active.txt pointer
│   ├── memory/                # Memoria episódica ChromaDB
│   ├── skills/                # Agent skills
│   ├── subagents/             # Subagentes canónicos
│   ├── org.yaml               # Topología enterprise
│   └── scripts/               # Scripts DevSecDocOps
├── CHANGELOG.md
└── pyproject.toml             # Configuración de empaquetado
```

---

## Testing y Calidad

```bash
ruff check .          # Linting estático
ruff format .         # Formateo automático
pytest --cov=cortex   # Tests con coverage
mypy cortex/          # Type checking
```

Coverage objetivo: >85%. Suite dividida en `unit/`, `integration/`, `e2e/`. Property-Based Testing con Hypothesis. El módulo `cortex.documentation.*` corre bajo `mypy --strict`.

---

## 🤝 Contribuir

¡Las contribuciones son bienvenidas! Lee [CONTRIBUTING.md](CONTRIBUTING.md) para setup, estándares y guía de PRs.

---

## 📄 Licencia

MIT — ver [LICENSE](LICENSE).

## 👥 Autor

**MachuaninEzequiel** — [@MachuaninEzequiel](https://github.com/MachuaninEzequiel)

## Agradecimientos

- **ChromaDB** por el excelente vector database
- **ONNX Runtime** por hacer embeddings lightning-fast
- **Obsidian** por inspirar el formato de vault
- Todos los contribuyentes early-adopters de Cortex

---

<div align="center">
  <p>¿Problemas? ¿Ideas? ¡<a href="https://github.com/MachuaninEzequiel/Cortex/issues">Abre un issue</a>!</p>
  <p><strong>Cortex: La memoria dejó de ser el pasado. Ahora es infraestructura corporativa.</strong></p>
</div>
