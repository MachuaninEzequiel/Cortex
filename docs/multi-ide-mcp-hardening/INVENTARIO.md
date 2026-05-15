# Inventario — estado previo al plan multi-IDE & MCP hardening

**Fecha:** 2026-05-15
**Fase:** FASE-0 (read-only).
**Output de:** Tasks 0.1, 0.2, 0.3, 0.4 del plan.
**Aprobado por:** [pendiente firma del creador]

---

## 1. Copias paralelas de prompts canonicos

### 1.1 Subagentes con doble copia (`.cortex/subagents/` vs `cortex-pi/.pi/agents/`)

| Logical name | `.cortex/subagents/` | `cortex-pi/.pi/agents/` | Diferencias semanticas |
|---|---|---|---|
| cortex-code-explorer.md | hash `33490745915946fa` | hash `33490745915946fa` (canonicalizado a LF) | **IDENTICOS** — solo CRLF/LF. |
| cortex-code-implementer.md | hash `3bb57ad1806723dd` | hash `3bb57ad1806723dd` (canonicalizado a LF) | **IDENTICOS** — solo CRLF/LF. |
| cortex-documenter.md | hash `1a81a5c1383cfdc3` | hash `9433167051972cc3` | **DRIFT SEMANTICO REAL**: la copia en `.cortex/subagents/` cita funciones MCP que **no existen** (`write_session_note`, `write_spec_note`); la copia en `cortex-pi/.pi/agents/` cita los nombres reales (`write_session_note_canonical`, `write_spec_note_canonical`, definidos en `cortex/documentation/writers.py:590,609`). |

**Implicancia para Fase 4:** la SSoT actual `.cortex/subagents/cortex-documenter.md` tiene contenido OBSOLETO. La reconciliacion debe favor de la copia `cortex-pi/.pi/agents/cortex-documenter.md` (que tiene los nombres reales del codigo).

### 1.2 Mecanismo de sincronizacion existente

`cortex/ide/adapters/pi.py:37-84` define `sync_canonical_subagents()` que sobrescribe los 3 archivos compartidos en `cortex-pi/.pi/agents/` desde `.cortex/subagents/` antes de cada `inject_profiles`. Esto significa:

- Pi NO trata a `cortex-pi/.pi/agents/` como SSoT paralela. Es un **staging directory** que pi mantiene actualizado.
- El drift detectado en `cortex-documenter.md` indica que `.cortex/subagents/cortex-documenter.md` fue modificado **despues del ultimo `pi inject`** y nadie corrio `pi inject` para sincronizar — o la situacion inversa: alguien edito directamente la copia de pi sin propagar.
- El hecho de que `.cortex/subagents/cortex-documenter.md` cite funciones inexistentes mientras la copia de pi cita las correctas sugiere que la copia de pi se actualizo primero (probablemente al hacerse el rename canonical) y `.cortex/subagents/` quedo desactualizado.

### 1.3 Archivos huerfanos en `cortex-pi/.pi/agents/` (sin contraparte en `.cortex/subagents/`)

| Archivo | Categoria | Decision para Fase 4 |
|---|---|---|
| cortex-SDDwork.md | AGENT en pi (no es subagente delegable). | Mantener como exclusivo de pi. NO migrar a `.cortex/subagents/`. |
| cortex-sync.md | AGENT en pi. | Idem. |
| cortex-security-auditor.md | AGENT exclusivo pi. | Decidir con el creador si se migra (usable en otros IDEs) o queda solo en pi. |
| cortex-test-verifier.md | AGENT exclusivo pi. | Idem. |

Tambien existen `agent-chain.yaml` y `teams.yaml` en `cortex-pi/.pi/agents/` — son configs de orquestacion exclusivas de pi/opencode (no son prompts, fuera de alcance del plan).

### 1.4 Skills canonicos (`.cortex/skills/` vs otras ubicaciones)

| Logical name | Ubicacion 1 | Ubicacion 2 | Estado |
|---|---|---|---|
| cortex-sync.md (SKILL) | `.cortex/skills/cortex-sync.md` (hash `1b8dde229a530fd0`) | (no existe en pi/skills) | OK, unico canonico. |
| cortex-SDDwork.md (SKILL) | `.cortex/skills/cortex-SDDwork.md` (hash `4724da1f7cdc3436`) | (no existe en pi/skills) | OK, unico canonico. |
| cortex-SDDwork-cursor.md (SKILL) | `.cortex/skills/cortex-SDDwork-cursor.md` (hash `e27225d74a470de4`) | (no existe en otra parte) | **VIOLA principio rector**: variante de SKILL especifica por IDE en la SSoT. Cursor adapter usa `build_cursor_prompts()` para producirla. Fase 4 debe eliminar la variante e introducir la traduccion en el adapter. |

**Notar tambien:** `cortex-sync` y `cortex-SDDwork` existen como SKILL en `.cortex/skills/` (consumibles por Claude Code, opencode, codex como `/cortex-sync`, `/cortex-sddwork`) Y como AGENT en `cortex-pi/.pi/agents/` (consumibles por pi como agentes). Los archivos NO son identicos entre las dos categorias (hashes distintos). Esto es **una distincion conceptual real** entre IDEs: en algunos IDEs estos workflows se exponen como skill/slash-command, en pi como agent. Fase 4 debe documentar como manejar esta dualidad sin violar la SSoT.

### 1.5 Skills genericos (no Cortex)

Los skills genericos `defuddle`, `json-canvas`, `obsidian-bases`, `obsidian-cli`, `obsidian-markdown` existen duplicados **identicos** en:

- `cortex/skills/<name>/SKILL.md` (templates en el codigo)
- `.cortex/skills/<name>/SKILL.md` (output del setup en el proyecto)

La duplicacion es esperada: el setup copia los templates al proyecto. Fuera de alcance del plan multi-IDE & MCP.

`cortex-pi/.pi/skills/` tiene skills propios de pi (`cortex-python`, `cortex-testing`, `cortex-vault`, `obsidian`, `obsidian-index`) sin contraparte en `.cortex/skills/`. Son exclusivos de pi. Fuera de alcance.

### 1.6 Otros archivos system/AGENT.md

- `.cortex/AGENT.md`, `.cortex/system-prompt.md` — system prompts del proyecto, no son subagentes ni skills.
- `cortex-pi/.pi/system.md` — system prompt de pi.
- `docs/agents/`, `docs/agents/plan/`, `docs/agents/implementacion/` — documentacion historica del plan tripartito previo. NO son prompts vivos, son docs de roadmap. Fuera de alcance.

---

## 2. Adapters de IDE y vocabulario de tools

### 2.1 Tabla por adapter

| IDE | Adapter file | Lineas | Inyecta subagentes desde SSoT? | Config files que escribe | MCP key | Mecanismo de delegacion |
|---|---|---|---|---|---|---|
| claude_code | `cortex/ide/adapters/claude_code.py` | 194 | Si — usa `get_subagent_prompt()` de `.cortex/subagents/` | `CLAUDE.md`, `.claude/agents/*.md`, `.claude/skills/*/SKILL.md`, `.claude/settings.json`, `.mcp.json` | `mcpServers` | Task tool nativo (`subagent_type: <name>`) |
| opencode | `cortex/ide/adapters/opencode.py` | 162 | Si — copia `.cortex/subagents/*.md` a `~/.config/opencode/subagents/` | `~/.config/opencode/opencode.json`, `~/.config/opencode/skills/*.md`, `~/.config/opencode/subagents/*.md` | `mcp` | Agent profile en JSON con `mode: primary`; `Task: True` en tools |
| codex | `cortex/ide/adapters/codex.py` | 246 | Si — usa `get_subagent_prompt()` | `.codex/AGENTS.md`, `.codex/agents/*.md`, `.codex/skills/*.md`, `.codex/mcp.json` | `mcpServers` | NO tiene Task tool nativo; el handoff es el ultimo mensaje del agente (ver linea 113 del adapter) |
| cursor | `cortex/ide/adapters/cursor.py` | 111 | NO — usa `build_cursor_prompts()` con prompts especiales (`cortex-SDDwork-cursor.md`) | `~/.cursor/agents/*.md`, `~/.cursor/mcp.json` | `mcpServers` | Hibrido: 1 agente (`cortex-SDDwork-cursor`) embebe explorer + implementer. NO delega. |
| pi | `cortex/ide/adapters/pi.py` | 169 | Si — `sync_canonical_subagents()` propaga 3 shared agents a `cortex-pi/.pi/agents/` antes de copiar el bundle entero al project root | `.pi/`, `AGENTS.md`, `justfile`, `README.md` (todo el bundle) | (no usa MCP) | Agentes nativos de pi via `agent-chain.yaml` |
| vscode | `cortex/ide/adapters/vscode.py` | 156 | Si — usa `get_subagent_prompt()` | `.vscode/<archivos>` | `servers` | (depende de extension Cortex) |
| windsurf | `cortex/ide/adapters/windsurf.py` | 81 | NO — solo MCP injection | `<config>/mcp.json` | `mcpServers` | (sin subagentes) |
| zed | `cortex/ide/adapters/zed.py` | 69 | NO — solo MCP injection | `<config>` | (no detectada en grep) | (sin subagentes) |
| hermes | `cortex/ide/adapters/hermes.py` | 80 | NO — solo MCP injection | `<config>` | `mcp` | (sin subagentes) |
| antigravity | `cortex/ide/adapters/antigravity.py` | 80 | NO — solo MCP injection | `<config>` | `mcp_servers` | (sin subagentes) |
| claude_desktop | `cortex/ide/adapters/claude_desktop.py` | 69 | NO — solo MCP injection | `Library/Application Support/Claude/claude_desktop_config.json` o `~/.config/Claude/claude_desktop_config.json` | `mcpServers` | (sin subagentes) |

### 2.2 Vocabulario de tools por IDE (filesystem)

| Canonical | claude_code | opencode | codex | cursor | vscode | pi |
|---|---|---|---|---|---|---|
| read_file | `Read` | `read` (boolean en JSON) | (no declarado en frontmatter — usa MCP/sistema) | (no declarado) | (no declarado en grep rapido) | (bash tools) |
| write_file | `Write` | `write` | idem | idem | idem | idem |
| edit_file | `Edit` | `edit` | idem | idem | idem | idem |
| execute_command | `Bash` | `bash` | idem | idem | idem | idem |
| glob | `Glob` | (no detectado) | idem | idem | idem | idem |
| grep | `Grep` | (no detectado) | idem | idem | idem | idem |

**Observacion:** Los IDEs con frontmatter `tools:` declarado (claude_code, opencode) usan nombres distintos. Los que NO declaran frontmatter `tools:` (codex, cursor, vscode, pi) heredan los tools nativos del IDE sin filtrar.

### 2.3 Vocabulario de tools por IDE (MCP de Cortex)

Tres patrones detectados:

1. **Prefijo `mcp__cortex__`** (claude_code): `cortex_save_session` se invoca como `mcp__cortex__cortex_save_session`.
2. **Nombre directo** (opencode): `cortex_save_session` se declara y se invoca tal cual.
3. **Sin frontmatter de tools — descubrimiento dinamico** (codex, cursor, vscode, claude_desktop, etc.): el IDE descubre los tools del MCP server al conectarse.

### 2.4 Adapters que **NO leen de la SSoT** (alarma)

- **cursor** (linea 53-54 de `cortex/ide/adapters/cursor.py`): si `prompts is None`, llama `build_cursor_prompts(project_root)`. Esa funcion vive en `cortex/ide/prompts.py`. Necesita inspeccion en Fase 4 — probablemente embebe contenido sin leer de `.cortex/subagents/`.
- Los **MCP-only** (windsurf, zed, hermes, antigravity, claude_desktop) no inyectan profiles — no es alarma, es por diseño: dependen de descubrimiento dinamico.

---

## 3. Callers del delegate experimental

### 3.1 Distincion critica: dos sistemas con nombres similares

| Sistema | Que es | Decision Fase 5 |
|---|---|---|
| **MCP Delegate** (`cortex/mcp/server.py`) | Tools `cortex_delegate_task`, `cortex_delegate_batch`, `cortex_get_task_result` y sus helpers privados `_delegate_task`, `_delegate_batch`, `_store_task_result`, `_get_task_result`. Acoplados a opencode. | **ELIMINAR** — esta en alcance del plan. |
| **Autopilot Delegation Engine** (`cortex/autopilot/delegation.py`) | Funciones `register_task`, `get_task_result`, `_task_registry`, clases `DelegationEngine`, `ReviewVerdict`. Implementa two-stage review independiente del MCP. | **PRESERVAR** — es API interna del autopilot, no es el delegate experimental. Solo se elimina el acoplamiento via `cortex/mcp/server.py:20` (import) y los handlers MCP que la usan. |

### 3.2 Callers en codigo de PRODUCCION

| Path:linea | Que hace | Tipo de dependencia |
|---|---|---|
| `cortex/mcp/server.py:20` | `from cortex.autopilot.delegation import get_task_result, register_task` | Import directo. Eliminar **solo si** se eliminan los handlers MCP que las usan. |
| `cortex/mcp/server.py:454,467,489` | Registracion de los 3 tools en `handle_list_tools`. | Eliminar. |
| `cortex/mcp/server.py:601,615,633` | Dispatch de los 3 tools en `handle_call_tool`. | Eliminar. |
| `cortex/mcp/server.py:603,620` | `register_task(...)` invocado dentro de los handlers MCP. | Eliminar (queda dentro de los handlers eliminados). |
| `cortex/mcp/server.py:636` | `get_task_result(task_id)` invocado en handler `cortex_get_task_result`. | Eliminar. |
| `cortex/mcp/server.py:1030,1059,1083` | Definiciones de `_store_task_result`, `_get_task_result`, `_delegate_task`. | Eliminar. |
| `cortex/setup/cortex_workspace.py:249-250` | Template que GENERA el contenido de la skill canonica `.cortex/skills/cortex-SDDwork.md` con referencia literal a `cortex_delegate_task`. | **CRITICO**: editar el template Y regenerar la skill canonica. |
| `.cortex/skills/cortex-SDDwork.md:63-64` | OUTPUT del template — la skill canonica menciona `cortex_delegate_task`. | Regenerar tras editar `cortex_workspace.py`. |

### 3.3 Callers en TESTS

| Test | Decision Fase 5 |
|---|---|
| `tests/integration/mcp/test_server.py:82,92,115,120,123,126,139,149` (tests `test_get_task_result_returns_saved_delegate_output`, `test_delegate_batch_summarizes_each_subagent`, `test_delegate_task_reports_missing_opencode`) | **ELIMINAR** completos — testean el delegate eliminado. |
| `tests/integration/setup/test_cortex_workspace.py:36` (`assert "cortex_delegate_task" in files[".cortex/skills/cortex-SDDwork.md"]`) | **MODIFICAR** — actualizar la assertion al nuevo contenido sin `cortex_delegate_task`. |
| `tests/unit/autopilot/test_delegation.py` (`register_task`, `get_task_result`, `_task_registry`) | **PRESERVAR** — testean el autopilot delegation engine, no el MCP delegate. |
| `tests/e2e/scenarios/test_autopilot_basic.py:276-291` (`register_task`, `get_task_result`) | **REVISAR** caso por caso. Si el test usa el flujo del MCP delegate, eliminar. Si solo usa la API del autopilot, preservar. |
| `tests/e2e/test_artefact_integrity.py:302` (`"cortex_get_task_result": None`) | **REVISAR** — probablemente una verificacion de contrato MCP que necesita actualizarse al nuevo set sin el delegate. |

### 3.4 Callers en DOCS

| Doc | Decision |
|---|---|
| `CHANGELOG.md:180` | Mantener (es entrada historica de cuando se agrego). Agregar nueva entrada en Fase 5 documentando la eliminacion. |
| `docs/autopilot/README.md:214,812,833,1519-1521` | Actualizar para reflejar el nuevo modelo (los tools fueron eliminados; el engine sigue). |
| `docs/autopilot/fase-09-delegacion-y-deep-track-real/REALIZACION.md` | Mantener como historico (es realizacion de fase pasada). Agregar nota al final del doc indicando que los tools MCP fueron retirados en Fase 5 del plan multi-IDE. |
| `docs/autopilot/fase-11-tests-end-to-end-y-evals/REALIZACION.md:99` | Idem. |
| `docs/autopilot/fase-09-delegacion-y-deep-track-real/README.md:53-55` | Idem. |
| `docs/multi-ide-mcp-hardening/*` | Ya documentan el plan; no requieren cambios. |

### 3.5 Callers fuera del repo (no inventariables)

Si existen adopters externos que invocan `cortex_delegate_task` directamente desde sus prompts o scripts, no podemos saberlo desde dentro del repo. Mitigacion: anuncio en CHANGELOG con migration note (ver Fase 5 Task 5.5). El reemplazo es: dejar que el IDE delegue nativamente.

---

## 4. Shape actual del MCP server

### 4.1 Tools expuestos (19 totales)

| # | Nombre | Categoria |
|---|---|---|
| 1 | cortex_search_vector | Search semantico (ONNX) |
| 2 | cortex_search | Search keyword |
| 3 | cortex_context | Context enricher |
| 4 | cortex_sync_ticket | Spec/ticket sync |
| 5 | cortex_create_spec | Spec creation |
| 6 | cortex_save_session | Session persistence |
| 7 | cortex_validate_handoff | Tripartita Refinada |
| 8 | cortex_verify_session_claims | Tripartita Refinada |
| 9 | cortex_import_hu | HU import |
| 10 | cortex_get_hu | HU read |
| 11 | cortex_sync_vault | Vault sync |
| 12 | cortex_autopilot_start | Autopilot |
| 13 | cortex_autopilot_preflight | Autopilot |
| 14 | cortex_autopilot_checkpoint | Autopilot |
| 15 | cortex_autopilot_finish | Autopilot |
| 16 | cortex_autopilot_status | Autopilot |
| 17 | cortex_delegate_task | **A eliminar (Fase 5)** |
| 18 | cortex_delegate_batch | **A eliminar (Fase 5)** |
| 19 | cortex_get_task_result | **A eliminar (Fase 5)** |

**Bug colateral detectado** (NO en alcance del plan, ver seccion 5): `cortex_search_vector` esta REGISTRADO en `handle_list_tools` (linea 113) pero **no tiene branch en el dispatch** (`handle_call_tool` lineas 519-636). Solo aparece `cortex_search` en linea 519. Invocar `cortex_search_vector` desde un cliente devuelve "Unknown tool" o equivalente.

### 4.2 Subprocess sites

| Linea | Llamada | Riesgo | Cobertura del plan |
|---|---|---|---|
| `server.py:942` | `subprocess.run(["git", "diff", "--unified=0", base, "--"], cwd=project_root, timeout=10)` en `_verify_session_claims_text` | Sin pre-validacion de la rama base, sin proteccion contra zombies en Windows. Si la rama no existe, espera 10s. Si hay git lock, idem. | Fase 1 Capa 3 (defensive subprocess). |
| `server.py:1113` | `shutil.which("opencode")` en `_delegate_task` | A eliminar con Fase 5. | Fase 5. |
| `server.py:1129` | `asyncio.create_subprocess_exec(opencode_bin, "run", "--agent", str(subagent_file), "--task", task, ...)` en `_delegate_task` | A eliminar con Fase 5. | Fase 5. |

### 4.3 Lazy-loaded models

- ONNX embeddings se cargan via `cortex/semantic/vector_cache.py:VectorCache`.
- `VectorCache` tiene `threading.RLock()` (linea 108) — protege la cache **a nivel de cache**, NO la INICIALIZACION del modelo.
- No hay lock alrededor de la carga del modelo en si. **Si dos requests `cortex_search_vector` llegan concurrentes la primera vez, se cargan dos modelos en paralelo.** Cobertura: Fase 1 Capa 4.

### 4.4 Bloqueantes potenciales

| Sitio | Tipo de bloqueo | Cobertura |
|---|---|---|
| `subprocess.run(timeout=10)` en `_verify_session_claims_text` | Sincrono dentro de async — bloquea el event loop entero por hasta 10s. | Fase 1 Capa 1 (executor) + Capa 3 (defensive). |
| `self.memory.search_vector(...)` (carga ONNX) | Sincrono dentro de async — primer hit puede tardar segundos a minutos. | Fase 1 Capa 1 + Capa 4. |
| `self.memory.sync_vault()` en `_sync_vault_text` | IO masivo de disco, sincrono. | Fase 1 Capa 1. |
| `self.memory.save_session_note(...)` y similares | IO de disco, sincrono pero rapido. | Probablemente OK con executor de Capa 1 sin tratamiento especial. |
| `logging.basicConfig` con `StreamHandler(sys.stderr)` (linea 50-57) | **CRITICO**: en stdio Windows, logger.info bloquea si Claude Code no drena stderr. | Fase 1 Capa 2 (logging exclusivo a archivo en modo stdio). |

### 4.5 Configuracion de logging

```
linea 50-57:
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),       # archivo en logs_dir
        logging.StreamHandler(sys.stderr)    # << BUG LATENTE: stderr en stdio mode
    ]
)
```

**Hallazgo:** el server SIEMPRE corre en modo stdio (linea 1006: `mcp.server.stdio.stdio_server()`). No hay branch HTTP. Por lo tanto, el `StreamHandler(sys.stderr)` SIEMPRE es el bug — la condicion del plan ("solo en stdio mode") es siempre true. Fase 1 Capa 2 puede simplificarse: eliminar `StreamHandler(sys.stderr)` directamente (manteniendo el escape hatch via env var documentado en el plan).

### 4.6 Concurrencia y locks

- **No hay `ThreadPoolExecutor`** — todo corre en el event loop async.
- **No hay `asyncio.Lock` alrededor de operaciones que pueden race** (ej. carga de modelos).
- **Si hay `threading.RLock`** en `VectorCache` (linea 108) — protege solo la cache.
- **`asyncio.gather`** se usa en `_delegate_batch:1184` (a eliminar con Fase 5).
- **stdout hijack** durante `AgentMemory` init (linea 65-72): `sys.stdout = sys.stderr` — solo cubre stdout, solo en init. NO protege durante runtime.

### 4.7 Init y transport

- `mcp.server.stdio.stdio_server` exclusivo (linea 1006).
- `Server("cortex-federated-server")` (linea 73).
- `InitializationOptions(server_name="cortex", server_version="2.1", ...)` (linea 1010-1017).
- No hay endpoint HTTP, no hay version REST, no hay otro transport.

---

## 5. Hallazgos imprevistos

Durante el inventario aparecieron hallazgos que NO estaban contemplados en el plan original. Cada uno se clasifica como (a) input adicional para una fase del plan, (b) deuda preexistente fuera de alcance documentada como ARRASTRE, o (c) decision pendiente del creador.

### 5.1 Drift semantico de `.cortex/subagents/cortex-documenter.md` apunta a funciones inexistentes

- **Tipo:** input para Fase 4.
- **Detalle:** la SSoT actual cita `write_session_note` y `write_spec_note`, pero el codigo solo tiene `write_session_note_canonical` y `write_spec_note_canonical`.
- **Accion en Fase 4:** reconciliar a favor de la copia `cortex-pi/.pi/agents/cortex-documenter.md`.

### 5.2 `cortex-SDDwork-cursor.md` viola el principio rector

- **Tipo:** input para Fase 4.
- **Detalle:** existe una variante de SKILL especifica por IDE en la SSoT (`.cortex/skills/cortex-SDDwork-cursor.md`).
- **Accion en Fase 4:** Cursor adapter debe traducir desde la skill canonica `cortex-SDDwork.md`, no desde una variante hardcodeada. La variante se elimina.

### 5.3 Dualidad SKILL vs AGENT para cortex-sync y cortex-SDDwork

- **Tipo:** decision pendiente del creador.
- **Detalle:** estos dos workflows existen como SKILL en `.cortex/skills/` (Claude Code, opencode, codex los exponen como slash commands) y como AGENT en `cortex-pi/.pi/agents/` (pi los trata como agentes nativos). Los archivos NO son identicos — el contenido difiere por la naturaleza del mecanismo (skill vs agent).
- **Pregunta abierta:** ¿es correcto mantener dos versiones del mismo workflow categorizadas distinto por IDE? ¿O es deuda conceptual que viola el principio rector?
- **Recomendacion para discusion:** mantener la dualidad como diferencia de mecanismo del IDE (una skill no es una agent), pero ambas versiones deben provenir de un mismo "concepto" canonico. Fase 4 puede definir esto formalmente.

### 5.4 `cortex_search_vector` registrado pero sin handler dispatch

- **Tipo:** ARRASTRE — bug preexistente fuera de alcance del plan.
- **Detalle:** linea 113 de `cortex/mcp/server.py` registra el tool `cortex_search_vector`, pero el dispatch en `handle_call_tool` (lineas 519-636) NO tiene branch para el. Solo `cortex_search` esta dispatched. Invocar `cortex_search_vector` devuelve error.
- **Decision propuesta:** documentar como ARRASTRE-1 en `docs/multi-ide-mcp-hardening/ARRASTRE-1.md` y discutir con el creador si entra al alcance de Fase 1 (es una correccion menor mientras se refactoriza el server) o se difiere a un plan separado.

### 5.5 Distincion MCP Delegate vs Autopilot Delegation Engine

- **Tipo:** input para Fase 5.
- **Detalle:** el plan original asumia que `_delegate_task`, `_delegate_batch`, `_store_task_result`, `_get_task_result` eran todos parte del delegate experimental. La realidad es que existen en `cortex/mcp/server.py` (eliminar) Y en `cortex/autopilot/delegation.py` con nombres similares (`register_task`, `get_task_result`) que SI son legitimos (two-stage review engine, NO acoplado a opencode). Fase 5 debe diferenciar ambos sistemas claramente.

### 5.6 `cortex/setup/cortex_workspace.py` template de skill incluye `cortex_delegate_task`

- **Tipo:** input para Fase 5.
- **Detalle:** la skill canonica `.cortex/skills/cortex-SDDwork.md` no es escrita a mano — es generada por `cortex/setup/cortex_workspace.py:249-250` que tiene un template literal con `cortex_delegate_task`. Editar la skill canonica sin editar el template haria que el siguiente `cortex setup` revierta el cambio.
- **Accion en Fase 5:** editar PRIMERO `cortex_workspace.py` (template) y LUEGO regenerar la skill canonica.

### 5.7 cortex-pi/.pi/agents/ NO es SSoT paralela — es staging managed

- **Tipo:** clarificacion arquitectural.
- **Detalle:** el plan original hablaba de "eliminar cortex-pi/.pi/agents/ como copia paralela". Lectura mas precisa: pi adapter (`pi.py:37-84`) ya trata `.cortex/subagents/` como SSoT y usa `cortex-pi/.pi/agents/` como staging que sincroniza antes de cada `inject_profiles`. El "drift" detectado es porque alguien edito una sin propagar.
- **Decision para Fase 4:** mantener `cortex-pi/.pi/agents/` como staging managed por el adapter pi. Eliminar SOLO los archivos huerfanos que NO sean exclusivos de pi (los exclusivos como `cortex-security-auditor.md`, `cortex-test-verifier.md` se mantienen como "agentes nativos de pi" o se migran a `.cortex/subagents/` si tienen valor cross-IDE). Decision pendiente del creador.

### 5.8 Cantidad de copias de prompts mayor a la asumida

- **Tipo:** clarificacion.
- **Detalle:** el plan asumia 2 ubicaciones. La realidad incluye al menos:
  - `.cortex/subagents/` (SSoT para subagentes)
  - `.cortex/skills/` (SSoT para skills)
  - `cortex-pi/.pi/agents/` (staging para pi + huerfanos)
  - `cortex-pi/.pi/skills/` (skills exclusivos de pi)
  - `cortex/skills/` (templates en codigo, fuera de alcance)
  - `cortex/autopilot/skills/` y `cortex/autopilot/pi/skills/` (skills del autopilot)
- **Accion:** Fase 4 debe documentar explicitamente cuales son SSoT y cuales son derivados/exclusivos. La proximo seccion al final del INVENTARIO lista la conclusion.

---

## 6. Conclusion: matriz de SSoT vs derivados

| Categoria | SSoT | Derivados / generados | Exclusivos |
|---|---|---|---|
| Subagentes Cortex (cross-IDE) | `.cortex/subagents/*.md` (3 archivos) | `cortex-pi/.pi/agents/<los 3 shared>.md`, `.claude/agents/*.md`, `~/.config/opencode/subagents/*.md`, `.codex/agents/*.md`, etc. | (ninguno) |
| Skills Cortex (cross-IDE) | `.cortex/skills/cortex-*.md` (3 archivos: cortex-sync, cortex-SDDwork; **eliminar cortex-SDDwork-cursor**) | `.claude/skills/*/SKILL.md`, `~/.config/opencode/skills/*.md`, `.codex/skills/*.md`, `~/.cursor/agents/*.md` (cursor categoriza como agent), etc. | (ninguno) |
| Workflows pi (skill+agent dual) | `.cortex/skills/cortex-sync.md` (skill canonica), `cortex-pi/.pi/agents/cortex-sync.md` (agent canonica para pi) | (idem para cortex-SDDwork) | Decision Fase 4: ¿una sola fuente conceptual con doble materializacion? |
| Agentes exclusivos de pi | (no SSoT en .cortex/) | (no derivados) | `cortex-pi/.pi/agents/cortex-security-auditor.md`, `cortex-pi/.pi/agents/cortex-test-verifier.md` |
| Skills exclusivos de pi | (no SSoT en .cortex/) | (no derivados) | `cortex-pi/.pi/skills/cortex-python/`, `cortex-vault/`, `cortex-testing/`, etc. |
| Skills genericos (obsidian/json-canvas/defuddle) | `cortex/skills/<name>/SKILL.md` (templates en codigo) | `.cortex/skills/<name>/SKILL.md` (output del setup) | Fuera de alcance del plan. |

---

## 7. Items para discutir con el creador antes de cerrar Fase 0

1. **5.3** — ¿Como tratar la dualidad skill/agent de cortex-sync y cortex-SDDwork? ¿Una sola fuente con doble render? ¿Dos fuentes legitimas con nombres distintos?
2. **5.4** — `cortex_search_vector` sin handler dispatch: ¿se arregla en Fase 1 (oportunidad mientras se refactoriza el server) o se difiere a plan futuro?
3. **5.7** — Archivos huerfanos exclusivos de pi (`cortex-security-auditor.md`, `cortex-test-verifier.md`): ¿se mantienen en `cortex-pi/.pi/agents/` o se migran a `.cortex/subagents/` para uso cross-IDE?
4. **5.8** — Confirmar la matriz final de SSoT vs derivados (tabla en seccion 6).

Cuando el creador firme estas decisiones, Fase 0 se da por cerrada y Fase 1, Fase 3 y Fase 6 (las que no dependen de las respuestas) pueden empezar.
