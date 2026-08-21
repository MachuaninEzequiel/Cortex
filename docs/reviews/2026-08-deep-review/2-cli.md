# Revisión del subsistema CLI — `cortex/cli/**` (cortex-memory)

**Alcance:** los 13 archivos de `cortex/cli/` (~5.100 líneas). Solo lectura.
**Veredicto general:** subsistema funcional y bien testeado (17 archivos en
`tests/unit/cli/`), pero con un `main.py` monolítico de 2.277 líneas, varios
flags muertos, duplicación real entre comandos y accesos a atributos privados
que acoplan la CLI a los internos del core.

---

## 1. Propósito y arquitectura interna

La CLI es el punto de entrada canónico del paquete (`pyproject.toml:62` →
`cortex = "cortex.cli.main:app"`). Es una app **Typer/Click** que se compone de:

### Módulos

| Archivo | Líneas | Responsabilidad |
|---|---|---|
| `main.py` | 2277 | App raíz + ~35 comandos top-level + subapps `setup`, `pr-context`, `hu`. Helpers `_load_memory`, `_get_staged_files`, `_parse_verification_hooks`. |
| `session.py` | 842 | Subapp `cortex session`: current/list/show/diff/watch/switch/checkpoint/abandon + subapps `task` (list/done/in-progress/skip/block) e `hooks` (list/install/uninstall/status). |
| `session_tui.py` | 726 | TUI read-only (`rich.Live`) para `session watch`. Snapshot inmutable `SessionTuiState` + renderer puro `render_layout(state) -> Layout` + loop de polling con detección de cambios por mtime. |
| `ci.py` | 286 | Subapp `cortex ci`: `validate-pr` (gate CI con códigos 0/1/2/3), y Level 3: `open-review-session` / `report-checkpoint` / `close-review-session`. |
| `docs_subcommand.py` | 133 | Grupo `cortex docs`: monta `routing-table` propio y re-registra funciones de `docs_migrate` y `docs_search`. |
| `docs_search.py` | 121 | `cortex docs search` sobre `ContextEnricher.enrich()` con filtros estructurales; formatos text/json/compact. |
| `docs_migrate.py` | 160 | `migrate` / `validate` / `restore` / `list-backups` del vault (backup tar.gz antes de --apply). |
| `docs_vectorization.py` | 106 | `stats` / `compact` / `clear` del cache de vectores (Fase 06). |
| `review_knowledge.py` | 215 | Subapp `review-knowledge`: cola de revisión enterprise (`pending/approve/reject` sobre frontmatter draft + `candidate` legacy sobre JSONL). |
| `_search_filters.py` | 103 | Helper compartido CLI/MCP para construir `EnrichmentFilters` y detectar "modo estructural" (`has_any_filter`). También usado por `cortex/mcp/server.py:1768`. |
| `_setup_helpers.py` | 65 | `select_ide_interactive()`: precedencia `--ide` > non-interactive > menú numerado. Compartido por `setup agent` y `setup full`. |
| `_unicode_fallback.py` | 63 | Glifos unicode→ASCII según encoding de consola (Windows cp1252). Usado por el TUI. |
| `__init__.py` | 3 | Exporta `app`. |

### Patrón arquitectónico dominante

- **Thin controllers**: casi todos los comandos parsean flags, delegan en un
  servicio (`AgentMemory`, `SessionService`, `CiValidator`,
  `KnowledgePromotionService`, `ContextEnricher`, `SetupOrchestrator`) y
  formatean salida. La lógica vive fuera de la CLI — buen diseño.
- **Imports diferidos selectivos**: la mayoría de dependencias pesadas se
  importan dentro de cada comando (`from cortex.doc_verifier import ...`),
  para mantener barato el arranque y `--help`. Excepciones que rompen la regla:
  `AgentMemory`, `WorkspaceLayout`, `yaml`, `webgraph_app` y `autopilot_app`
  se importan a nivel de módulo en `main.py`.
- **Convención de salida dual**: casi todo comando soporta `--json`
  (text plano vs JSON machine-readable); `search`/`docs search` añaden
  `--format text|json|compact`.

---

## 2. Flujo de datos y puntos de entrada/salida

### Entradas
- Flags Typer + argumentos posicionales.
- Git: `_get_staged_files()` (main.py:2241) corre `git diff --cached`,
  `git diff`, `git ls-files --others` con timeout de 10s.
- Archivos JSON de intercambio: `.pr-context.json`, `.past-context.json`,
  `.doc-status.json`, `.doc-validation.json`, `.enterprise-doc-validation.json`
  — la CLI es productora y consumidora de estos artefactos (pipeline CI).
- Config: `WorkspaceLayout.discover(root)` resuelve `config.yaml` /
  `workspace.yaml`; el TUI lee `.cortex/config.yaml` directamente.

### Salidas
- stdout/stderr vía `typer.echo` / `rich.Console`.
- Archivos JSON de estado en el repo del adopter (ver arriba).
- Escrituras reales al workspace: setup/inject/hooks escriben configs de IDE,
  specs/sessions/vault via servicios, backups tar.gz.

### Quién llama a este subsistema
- Usuario final / agentes IDE (comandos directos).
- Hooks de IDE instalados por `session hooks install` → llaman a
  `cortex session checkpoint` (session.py:366-368 lo documenta).
- Workflows CI generados por `setup pipeline` → llaman a `ci validate-pr`,
  `verify-docs`, `validate-docs`.
- MCP server: importa `cortex.cli._search_filters` (consumidor interno).
- Tests E2E vía subprocess (el reconfigure UTF-8 de main.py:47-50 existe
  explícitamente para eso).

### A quién llama (hacia abajo)
`core.AgentMemory` (façade principal), `session.*` (service/storage/git/hooks/
verification), `ci.validator`, `documentation.*` (routing/migration/backup),
`context_enricher.*`, `enterprise.*` (knowledge_promotion/promotion_doctype/
reporting/config), `semantic.vault_reader`, `semantic.vector_cache`,
`setup.orchestrator`, `workspace.layout`, `ide`, `mcp.server`, `tutor.*`.

---

## 3. Invariantes y decisiones de diseño importantes

1. **`cortex session` no usa `AgentMemory`** (session.py:15-18): habla directo
   a `SessionService` para ser rápido y funcionar en repos parcialmente
   configurados. Contraste: casi todo lo demás pasa por `_load_memory()`.
2. **`_load_memory` falla rápido y en español** si no hay `config.yaml`
   (main.py:2229-2237), sugiriendo `cortex setup full --non-interactive`.
   Usa `sys.exit(1)` (no `typer.Exit`) — funciona pero es inconsistente.
3. **TUI frozen-state + renderer puro** (session_tui.py:9-23): el loop nunca
   toca storage desde el renderer; testable sin TTY. Sin threads, sin input
   de teclado; Ctrl+C es la única salida.
4. **Detección de cambios barata por mtime** del pointer activo y de cada
   YAML de sesión (`_detect_changes`, session_tui.py:591-603).
5. **CI exit codes como contrato**: 0 pass / 1 warn / 2 blocked / 3 error
   (ci.py:5-8); `validate-pr` hace `raise typer.Exit(result.exit_code)`
   (ci.py:108).
6. **Dry-run por defecto donde hay escritura destructiva**:
   `promote-knowledge` es `--dry-run/--apply` con default dry-run
   (main.py:1712-1744); `docs migrate` es dry-run salvo `--apply` y crea
   backup tar.gz automático; `review-knowledge reject` mueve a `rejected/`
   salvo `--delete` explícito; `docs vectorization clear` pide confirmación.
7. **Path traversal guard** en approve/reject de review-knowledge:
   `full_path.is_relative_to(vault_root.resolve())` (review_knowledge.py:101,
   139).
8. **Modo estructural vs legacy en `cortex search`**: sin filtros
   estructurales → RRF fusionado legacy; con `--doc-type/--tag/...` → path
   nuevo vía `ContextEnricher` (main.py:~1180-1260). El dispatch lo decide
   `has_any_filter` (_search_filters.py:71).
9. **Compatibilidad hacia atrás deliberada**: `install-ide` deprecated pero
   vivo, `mcp-serve` alias oculto, `init` alias de `setup agent`.

---

## 4. Bugs potenciales y riesgos (con file:line)

### B1. `--dry-run` declarado e ignorado en 3 comandos (bug de UX/contrato)
`setup_agent` (main.py:438), `setup_pipeline` (main.py:480) y `setup_full`
(main.py:504) aceptan `--dry-run` pero **nunca lo usan**: no se pasa al
`SetupOrchestrator` ni se ramifica. `setup webgraph` ni siquiera lo finge
(`del dry_run`, main.py:579) y `setup enterprise` sí lo implementa
(main.py:667). Un usuario de CI que pase `--dry-run` a `setup full` ejecutará
escrituras reales creyendo que era simulación.

### B2. Ventana de protección del handshake MCP demasiado corta (probable bug)
`mcp_server` redirige `sys.stdout → sys.stderr` solo alrededor del constructor
`CortexMCPServer(...)` y lo **restaura antes de `asyncio.run(server.run())`**
(main.py:1912-1924). Cualquier print accidental durante el serveo real vuelve a
corromper el handshake JSON-RPC, que es exactamente lo que el comentario dice
querer proteger.

### B3. Dispatch inconsistente de filtros en `cortex search`
`has_any_filter` se llama con `project_id=None` y `scope="local"`
hard-codeados (main.py:~1200-1210), ignorando los valores que el usuario pasó.
Efecto: `--scope enterprise` solo, o `--project-id X` solo, caen al path
legacy (que sí los soporta), pero `--tag foo --scope enterprise` va al path
estructural. Resultados y formato cambian según combinación de flags —
frágil y difícil de documentar.

### B4. Doble sistema de output flags en `cortex search`
Legacy usa `--json`; el modo estructural usa `--format json|compact|text`.
Si el usuario pasa `--format json` sin filtros estructurales, el flag se
ignora silenciosamente y obtiene texto legacy (main.py:~1180 y ~1250+).

### B5. Optimización del TUI anulada por `_detect_changes`
El sidebar "caro" solo se refresca cada 10 ticks (session_tui.py:60, 524-528),
pero `_snapshot_session_mtimes()` hace `service.list()` completo en **cada**
tick (session_tui.py:575-588, llamado desde 601). El ahorro es ilusorio; en
vaults grandes el polling O(n) por tick persiste. Además los contadores
(`total_open/closed/...`) se calculan del snapshot potencialmente stale
(session_tui.py:538-541).

### B6. Accesos a privados de otros módulos (acoplamiento frágil)
- `finish_session` toca `mem._session_service`, `mem._note_service`,
  `mem._vault_path_resolved` (main.py:1560-1580 aprox).
- TUI: `service._storage._file_for(...)`, `storage._active_pointer()`
  (session_tui.py:582-584, 598-599, 664-665).
Cualquier refactor del core/session rompe la CLI sin señal de tipo.

### B7. `warnings.filterwarnings("ignore")` global al importar (main.py:53)
Supresión total de warnings como efecto secundario de importar `cortex.cli` —
enmascara DeprecationWarnings del propio paquete y de librerías en procesos
que solo querían `--help` programático. Ídem el reconfigure de stdout a UTF-8
en Windows (main.py:46-50): side effect razonable pero no documentado para
embedders.

### B8. Código muerto / muerto-en-la-práctica
- Fallback `importlib.resources ... except AttributeError` en
  `agent_guidelines` (main.py:~1090): el paquete exige Python >=3.11
  (pyproject.toml:11) y usa `datetime.UTC` (Python 3.11+) en ci.py:16 y
  session_tui.py:30. El fallback py<3.9 es inalcanzable.
- `docs_migrate.app` define su propio Typer app + callback (docs_migrate.py:20-25)
  que **nunca se monta**: `docs_subcommand.py:40-43` re-registra las funciones
  sueltas. La app interna es código muerto y el callback documenta un grupo
  que no existe en el árbol final.
- Docstring obsoleto de `docs_subcommand` ("In Fase 02 this group exposes a
  single command", docs_subcommand.py:3-4) cuando ya monta 7 subcomandos.

### B9. Duplicación significativa
- Lógica de "store PR en memoria" copiada entre `pr_context store`
  (main.py:~247-290) y step 2 de `pr_context full` (main.py:~560-600):
  mismo armado de `content_parts`, mismos tags/files. Ídem búsqueda duplicada
  entre `pr_context search` y step 3 de `full`. Un cambio de esquema de
  metadata obliga a editar 2 lugares.
- Formateo triple repetido en `context` (echo + write_text para 3 formatos,
  main.py:~700-740).
- Tres caminos para inyectar IDE: `install-ide`, `uninstall-ide`,
  `inject`, `sync-ide` (main.py:1867-2009) con comportamientos distintos
  ante `--ide` ausente (`inject` abre menú; `install-ide` ejecuta bulk
  deprecated con warning — sorpresa para el usuario).

### B10. Menores
- `memory_report` imprime `"window_days: N (0 events found)"` vía ternario
  dentro de f-string concat (main.py:2163-2168) — correcto pero ilegible;
  candidato a refactor.
- `reject_command` hace `new_path.relative_to(vault_root)` (review_knowledge.py:155)
  que lanzaría ValueError si `mark_as_rejected` devolviera un path con otro
  prefijo; hoy no ocurre, pero no está defendido como el guard de arriba.
- `index_docs` valida archivo por archivo e informa skips, pero luego
  `mem.sync_vault()` indexa el vault entero de todas formas (main.py:~1050-1070):
  la validación no gatea nada, solo reporta.
- `_resolve_documenter_mode` reconstruye a mano `repo_root/.cortex/config.yaml`
  (session_tui.py:623) en vez de usar `layout.config_path` — drift risk con
  el layout v2.
- `run_tui` muta handlers del root logger globalmente y los restaura en
  `finally` (session_tui.py:677-681, 718-719): OK pero afecta todo el proceso.

---

## 5. Deudas y oportunidades de refactor

1. **Partir `main.py`** (2.277 líneas, 19 usos de `_load_memory`). Split
   natural ya insinuado por los comentarios de sección: `cmd_setup`,
   `cmd_pr_context`, `cmd_docs_pipeline` (verify/validate/index), `cmd_enterprise`,
   `cmd_ide_mcp`, `cmd_memory`. El patrón `docs_*`/`session.py`/`ci.py` demuestra
   que el equipo ya migra hacia subapps modulares — terminarla.
2. **Extraer el bloque duplicado de pr-context** a un helper
   `_store_pr_context(mem, ctx)` y `_search_past_prs(mem, ctx)`.
3. **Unificar la interfaz de salida** (`--json` vs `--format`) y el manejo
   de errores (`typer.Exit` vs `sys.exit(1)` vs `_error_exit` de session.py).
4. **Exponer API pública en SessionService/AgentMemory** para lo que hoy se
   accede por underscore (B6): p.ej. `service.session_file_mtime(id)` y
   `service.active_pointer_mtime()`.
5. **Eliminar flags muertos** (`--dry-run` fake, `all_ides` deprecated) o
   implementarlos.
6. **Mover `has_any_filter` a semántica consistente**: decidir si
   scope/project_id fuerzan modo estructural y hacerlo explícito en ambos paths.
7. **Consolidar imports a nivel de módulo** en main.py o documentar la política.

---

## 6. Preparación para un cambio grande: qué tocar primero y qué es frágil

### Frágil (no tocar sin tests de caracterización)
- **`finish_session`** (main.py:~1500-1620): orquesta Reconstructor +
  VerificationRunner + DocumenterPersister vía privados del core; es el flujo
  con más ramificación (interactive/handoff/abandon/json) y el peor acoplamiento.
- **Dispatch de `cortex search`** (structural vs legacy): cualquier cambio de
  flags puede mover queries entre dos motores con outputs distintos.
- **Contrato de exit codes de `ci validate-pr`**: workflows externos ya
  dependen de 0/1/2/3.
- **`_load_memory` y `WorkspaceLayout.discover`**: punto único de resolución
  de raíz; cambiarlo afecta a 19 call sites.

### Orden sugerido para un cambio grande
1. Tests de caracterización de salida (--json) de los comandos más usados
   (search/context/session list/show/ci validate-pr). Ya existe base sólida
   en `tests/unit/cli/` (17 módulos) — apoyarse ahí.
2. Split mecánico de `main.py` en subapps sin cambiar comportamiento.
3. Deduplicar pr-context y unificar salida --format/--json.
4. Recién entonces: arreglar B1 (dry-run), B2 (stdout MCP), B3/B4 (dispatch).

### Salud del subsistema
**Buena con deudas controladas.** Arquitectura thin-controller sana,
separación clara CLI/servicios, buena cobertura de tests unitarios y
convenciones consistentes de --json/--project-root. Los riesgos están
concentrados en: tamaño de main.py, flags mentirosos (dry-run), acoplamiento
a privados del core y la doble vía de `cortex search`.
