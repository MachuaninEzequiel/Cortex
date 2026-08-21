# Informe de revisión: `cortex/enterprise`, `cortex/ide`, `cortex/mcp`

Revisor: subsistema enterprise / ide / mcp. Solo lectura. Repo: `/home/chucho/Cortex`.
Alcance: 33 archivos Python, ~8.700 líneas.

---

## 1. Propósito y arquitectura interna

### 1.1 `cortex.enterprise` (~2.300 líneas)

Sistema de memoria organizacional multi-proyecto/multi-tenant encima del vault local.

- **`config.py`** (289 l): carga/escritura de `.cortex/org.yaml`. Punto clave:
  `load_enterprise_config()` (l.55) con doble modo de resolución de path
  (WorkspaceLayout nuevo vs path legacy `project_root/.cortex/org.yaml`);
  `build_enterprise_org_config()` (l.100) genera presets; `write_enterprise_config()` /
  `render_enterprise_config_yaml()`; `describe_enterprise_topology()` para resúmenes.
- **`models.py`** (183 l): pydantic `EnterpriseOrgConfig` con secciones
  organization/memory/promotion/governance/integration + extensión "Fase 10"
  (teams, classifications, policies, `RetentionPolicy`). Validadores cruzados en
  `_validate_cross_section_rules` (l.139): promotion exige semantic enabled;
  episodic exige project_memory_mode=isolated.
- **`governance.py`** (152 l): permisos puros sin IO. `user_team`,
  `team_can_promote/review`, `classification_visible_to`,
  `allowed_classifications_for`, `assert_can_promote/review`. Sentinel `ADMIN_TEAM`.
- **`knowledge_promotion.py`** (338 l): pipeline legacy de promoción vault→vault
  enterprise. Clases: `PromotionRepository` (JSONL append-only),
  `PromotionRulesEngine` (filtros por doc_type), `KnowledgePromotionService`
  (discover → review → plan → apply), helpers `_split_frontmatter`,
  `_upsert_frontmatter`, `_normalized_markdown_fingerprint`.
- **`promotion_models.py`**: pydantic `PromotionCandidate/Decision/Record/Issue/Event`.
  Record es append-only con events y fingerprint como key de idempotencia.
- **`promotion_doctype.py`** (448 l): pipeline NUEVO DocType-aware (Fase 10),
  convive con el legacy por diseño ("opt-in", docstring l.1-30). Entry point
  `promote_note_doctype_aware()`: valida actor vía governance, resuelve
  `RouteSpec`, aplica modos `as-is | summarize | review-required`, inyecta
  frontmatter de gobernanza (owner/team/classification/retention_days/
  audit_trail). Además `mark_as_accepted/rejected`, `list_pending_drafts`.
- **`maintenance.py`** (168 l): retención. `scan_retention_violations()` +
  `archive_violations()` a `<vault>/_archived/`. Sin ejecución automática.
- **`reporting.py`** (218 l): `EnterpriseReportingService.build_memory_report()`:
  combina doctor + conteo de markdown + reporte de promoción en `MemoryReportPayload`.
- **`retrieval_service.py`** (221 l): `EnterpriseRetrievalService.search()` —
  búsqueda local+enterprise con fusión RRF (`_RRF_K=60`) y pesos configurables.
- **`sources.py`** (114 l): adapters finos sobre `VaultReader` y
  `EpisodicMemoryStore`; etiquetan cada hit con `origin_scope/project_id/vault`.

### 1.2 `cortex.ide` (~2.900 líneas)

Capa de inyección de perfiles/MCP en IDEs.

- **`__init__.py`** (161 l): API pública `inject/inject_all/uninstall/uninstall_all`;
  `_find_project_root()`; caso especial para Pi por nombre (l.60-63).
- **`base.py`** (258 l): ABC `IDEAdapter` (inject_profiles/inject_mcp/detect/
  validate/uninstall), helpers `_generate_autogen_header`, `_backup_file`,
  `_deep_merge_dict`, `_is_wsl`, `_create_shielded_wrapper` (wrapper bash que
  filtra stderr WSL para proteger el handshake JSON-RPC).
- **`registry.py`** (190 l): registro lazy de 11 adapters, alias
  (`claude`→claude_code, etc.), tiers TARGET/COMMUNITY/EXPERIMENTAL y set
  VALIDATED_IDES firmado en el plan multi-IDE 2026-05-15.
- **`prompts.py`** (141 l): lee skills/subagents canónicos desde WorkspaceLayout
  (SSoT); `build_all_prompts()` devuelve los 3 anchors triádicos.
- **`canonical_tools.py`** (324 l): vocabulario canónico de tools + matriz de
  traducción canonical→IDE-native (`translate`, `translate_list`). Solo
  claude_code y opencode validados (`ValidatedIDE`).
- **Adapters**: claude_code (293 l, CLAUDE.md + .claude/skills + agents con
  traducción de tools), codex (621 l, AGENTS.md con marcadores + config.toml TOML
  + trust en ~/.codex/config.toml global), cursor (324 l), opencode (184 l,
  perfiles con permission matrix), pi (247 l, copia bundle cortex-pi verbatim,
  sync_canonical neutralizado), vscode/windsurf/zed/antigravity/hermes/
  claude_desktop (best-effort, no validados).

### 1.3 `cortex.mcp` (~3.200 líneas)

- **`server.py`** (2.977 l): `CortexMCPServer`, server MCP stdio pasivo con ~28
  tools: health (`cortex_ping`), retrieval (`cortex_search[_vector]`,
  `cortex_context`), flujo sync/spec/proposal (`cortex_sync_ticket`,
  `cortex_emit_proposal`, `cortex_create_spec`), documentación
  (`cortex_save_session`, `cortex_write_doc`, `write_design_note_canonical`),
  sesiones (`cortex_session_*`, `cortex_close_session`,
  `cortex_documenter_briefing`, `cortex_finish_session`,
  `cortex_review_checkpoint`, tasks), handoff/claims, HU import, autopilot (5).
- Arquitectura defensiva post-incidente 2026-05-15: cada tool call corre en
  `ThreadPoolExecutor` con `asyncio.wait_for` timeout por-tool
  (`_TOOL_TIMEOUTS`, l.160); logging solo a archivo (stderr opt-in con
  `CORTEX_MCP_LOG_TO_STDERR=1`, l.245); `safe_run` nunca propaga.
- **`_subprocess.py`** (188 l): `Result` dataclass + `safe_run()` (timeout,
  creationflags Windows, captura de todas las exceptions) y
  `git_branch_exists()` pre-check barato.

---

## 2. Flujo de datos y puntos de entrada/salida

**enterprise**
- Entrada: `org.yaml` (disco), vault local, records JSONL. Llamadores externos:
  `cortex/cli/main.py`, `cli/review_knowledge.py`, `core.py` (líneas 38-40, usa
  `EnterpriseRetrievalService` dentro de AgentMemory), `doctor.py`,
  `setup/*`, `webgraph/service.py`.
- Salida: vault enterprise (markdown con frontmatter inyectado),
  `promotion_records.jsonl`, reportes JSON (CLI), resultados de búsqueda
  fusionados hacia `AgentMemory.retrieve`.

**ide**
- Entrada: prompts/skills/subagents canónicos bajo `.cortex/{skills,subagents}/`
  (via WorkspaceLayout), bundle `cortex-pi/`.
- Salida: archivos nativos de IDE (CLAUDE.md, .mcp.json, AGENTS.md, TOML,
  opencode.json, etc.) en el proyecto o `$HOME`. Llamado por CLI
  (`uninstall_ide` en cli/main.py l.1884) y setup orchestrator.
- El MCP config que escribe apunta al binario `cortex mcp-server --stdio`.

**mcp**
- Entrada: stdio JSON-RPC desde cualquier IDE (configurado por la capa ide).
- Salida: texto/JSON por tool; escrituras en vault via `AgentMemory` y
  `cortex.documentation.writers`; subprocesos git via `safe_run`.
- Dependencias internas fuertes: `core.AgentMemory` (retrieve/enrich/create_spec/
  session service), `documenter.Reconstructor/Persister`,
  `session.*` (SessionRecord, Task, quality_gates, proposal), `autopilot.*`,
  `context_enricher`, `security.paths.resolve_safe`.

Cadena completa típica: usuario instala → ide adapter escribe config MCP → IDE
arranca `cortex mcp-server --stdio --project-root X` → skill `/cortex-sync` del
IDE llama `cortex_sync_ticket` → `cortex_create_spec` (guard de gobernanza)
→ trabajo → `/cortex-documenter` → briefing/write_doc/close_session → notas en
vault → (opcional) promoción enterprise.

---

## 3. Invariantes y decisiones de diseño importantes

1. **Idempotencia por fingerprint** (knowledge_promotion.py): `origin_id =
   {project_slug}:{rel_path}` + sha256 del body normalizado. Skip si promoted con
   mismo fingerprint; re-promoción si cambia contenido.
2. **Append-only records**: PromotionRecord nunca se muta; cada transición agrega
   un record nuevo con events. `load_latest_by_origin_id` toma el último.
3. **Gobernanza pura**: governance.py no hace IO ni importa writers — testeable y
   reusable (consumido por promotion_doctype y doctor).
4. **Back-compat estricta en org.yaml**: campos Fase 10 todos opcionales con
   defaults vacíos (models.py l.120-131).
5. **Permisividad backward-compatible**: sin teams configurados, todo actor puede
   promover/revisar (governance.py l.44-47, 58-61).
6. **SSoT de prompts en `.cortex/`**, nunca hardcodear contenido (prompts.py);
   traducción de tools SOLO en frontmatter, nunca en el cuerpo (canonical_tools).
7. **Pi como bundle SSoT propio**: sync_canonical neutralizado deliberadamente
   (pi.py l.90-230 comentado; ide/__init__.py docstring).
8. **Aislamiento de bloqueos en MCP**: timeouts por tool, executor threads,
   stderr shielded wrapper para WSL, logging a archivo. Todo trazado a los
   incidentes del 2026-05-15 y 2026-05-22 (AppFutbol).
9. **Guard de gobernanza**: `cortex_create_spec` rechaza si `cortex_sync_ticket`
   no fue llamado antes (server.py l.1795+); proposal_mode='required' exige gap
   temporal ≥2s entre emit_proposal y confirmación (l.197-199, `_validate_proposal_gap`).
10. **Codex trust global**: Codex descarta la capa project-local hasta que el
    proyecto esté trusted en `~/.codex/config.toml`; el adapter escribe esa
    entrada con marcadores por-path y avisa explícitamente (codex.py l.470+).

---

## 4. Bugs potenciales (con file:line)

1. **`governance.user_team` nunca devuelve el sentinel ADMIN_TEAM** —
   governance.py l.37-45: el docstring promete devolver `ADMIN_TEAM` "si actor es
   el admin", pero la implementación no tiene ningún camino que lo retorne. El
   admin implícito solo existe si un team se llama literalmente "admin". Los
   checks `team_id == ADMIN_TEAM` (l.50, 64, 96) son casi dead-code salvo por
   nombre de team colisional. Además no hay noción de actor admin fuera de teams.
2. **Versiones de server inconsistentes** — mcp/server.py l.173
   `SERVER_VERSION = "2.2"` vs l.2831 `InitializationOptions(server_version="2.1")`.
   `cortex_ping` reporta 2.2 mientras el handshake MCP dice 2.1.
3. **Guard de gobernanza es de vida del servidor, no de sesión** —
   server.py l.1796-1806: `_called_tools` es un set acumulativo desde el inicio
   del proceso. Una vez que CUALQUIER llamada pasó por `cortex_sync_ticket`, el
   guard queda abierto para siempre (incluida otra tarea del usuario horas
   después). El gate real de flujo depende del prompt, no del server.
4. **Timeout no mata el thread del handler** — server.py l.1370-1382:
   `asyncio.wait_for` cancela la espera pero el worker del ThreadPoolExecutor
   sigue corriendo el handler bloqueado. Con suficientes timeouts encadenados se
   agotan los 4 workers y el server deja responder aunque `cortex_ping` diga ok
   (ping corre en el mismo executor, l.1359: también puede quedare sin worker).
5. **`except (ValueError, Exception)`** — server.py l.2160 y l.2177: redundante,
   captura todo; oculta bugs de programación como errores esperados.
6. **`codex.uninstall()` y `cursor.uninstall()` usan `Path.cwd()`, no
   project_root** — codex.py l.566 (`cwd = Path.cwd()`) vs `inject_profiles`
   que recibe `project_root`; cursor.py l.290 igual. `uninstall(ide)` en
   ide/__init__.py l.110 llama `adapter.uninstall()` sin argumento: si el CLI no
   corre desde la raíz del proyecto, desinstala del directorio equivocado (o no
   hace nada). Pi sí acepta project_root opcional pero default None → no-op
   silencioso (pi.py l.239-240).
7. **`pi.uninstall()` borra AGENTS.md completo del proyecto** — pi.py l.248-256:
   elimina `AGENTS.md`, `justfile`, `README.md`, `extensions/` sin marcadores ni
   backup. Eso destruye el AGENTS.md que el adapter de codex mantiene con secciones
   propias del adopter (y cualquier README/justfile del usuario). Riesgo alto de
   pérdida de datos.
8. **`windsurf.inject_profiles` y `claude_code` pisan CLAUDE.md/AGENTS.md
   enteros** — windsurf.py l.31-52 y claude_code.py l.110-160 usan `write_text`
   sobre el archivo completo (con backup timestamped, sí, pero el contenido del
   adopter desaparece del archivo activo). Codex demuestra el patrón correcto
   (marcadores BEGIN/END); el resto no lo sigue.
9. **Fusión RRF: precedencia sutil** — retrieval_service.py l.157 y l.172:
   `existing is None or existing.metadata.get("scope") != "enterprise" and ...`
   evalúa `A or (B and C)`. Funciona como parece quererse (preferir hit
   enterprise ante colisión de key), pero es frágil y sin paréntesis ni test
   evidente de la colisión. Además `_episodic_key` trunca contenido a 160 chars
   (l.196): dos entradas episódicas distintas con mismo prefijo se fusionan.
10. **`_extract_check_count` parsea texto humano** — reporting.py l.186-196:
    cuenta errores haciendo split del primer token del `detail` del doctor
    ("<n> error(s) across ..."). Si el mensaje del doctor cambia de formato, el
    reporte reporta 0 o 1 silenciosamente. Deuda de contrato frágil.
11. **Antigravity pisa `system_instructions`** — antigravity.py l.36-46: reemplaza
    el campo entero en `~/.gemini/settings.json` (comentario lo reconoce). Sin
    merge ni restauración en uninstall (la clase tampoco define uninstall).
12. **`mark_as_rejected(delete=True)` pierde el audit trail** —
    promotion_doctype.py l.400-404: borra el archivo tras armar el evento en
    memoria; el comentario lo admite ("no record of the rejection survives").
13. **`_global_has_foreign_trust` no maneja single-quoted escapes** — codex.py
    l.432-446: solo desescapa `\\` (basic strings); un path con comilla simple
    escapada daría falso negativo (menor).
14. **Cursor `get_config_paths` contradictorio** — cursor.py l.128-136: el
    comentario dice "project-level por default" pero devuelve `~/.cursor/*`
    (home); `user_agents_dir` declarado nunca se usa. El `detect_installation()`
    heredado chequeará dirs globales.
15. **`vscode` MCP usa `${workspaceFolder}`** — vscode.py l.117: a diferencia de
    todos los otros adapters que fijan `--project-root` absoluto (decisión
    documentada en claude_code.py l.280-284), vscode delega en la variable del
    IDE. Si VS Code abre una subcarpeta, Cortex resuelve otro root.
16. **Ping puede morir de hambre de workers** — ver punto 4; además
    `handle_call_tool` despacha TODO (incluido ping) por el executor, cuando el
    docstring de ping promete "NO hace IO" — podría correr inline en el loop.

## 5. Código muerto / duplicación

- **`_sync_vault_text`** (server.py l.2819-2821): nunca llamado; el dispatcher
  l.1478-1480 inlined `self.memory.sync_vault()`. Muerto.
- **Duplicación `_PathVault`** definida inline dos veces idéntica (server.py
  l.2222-2235 y l.2380-2392) — extraer helper.
- **Dispatcher if-chain gigante** (server.py l.1408-1560): ~35 ramas
  `if name == ...` repetitando el patrón dispatch+log; un dict `name → method`
  eliminaría ~150 líneas y el riesgo de olvidar el log.
- **Presets de config duplicados** — config.py l.113-215: cuatro branches de
  perfil que comparten ~80% de las claves (solo cambian 4 valores). Tabla de
  overrides sería más mantenible.
- **prompts.py `build_autopilot_prompts`**: no referenciado por ningún adapter
  del scope (solo tests) — verificar si quedó huérfano tras Phase 09.A+.
- **`_search_text` vs `_search_vector_text` vs enricher dispatch** (server.py
  l.1745-1800): tres caminos de búsqueda con solapamiento conceptual.
- **Adapters community/experimental repiten el mismo boilerplate** JSON
  read-backup-merge-write (claude_desktop, windsurf, zed, antigravity, hermes):
  ~5 copias del mismo bloque `contextlib.suppress(json.loads(...))`. Extraer a
  base helper `merge_json_config(path, key, value)`.
- **`_audit_event` / `_write_with_updates`** en promotion_doctype.py son helpers
  privados con firma distinta al pipeline principal; `_summarize_session` solo
  cubre 2 headers hardcodeados.
- **Marcador legacy `_SHARED_AGENTS`** en pi.py l.42-43 mantenido solo por tests.

## 6. Deudas y oportunidades de refactor

1. **server.py monolítico (2.977 líneas)**: schemas de tools (~900 líneas de
   JSON-Schema inline), dispatcher, y handlers viven juntos. Separar en
   `tool_schemas.py`, `handlers/retrieval.py`, `handlers/session.py`,
   `handlers/docs.py`. Es EL refactor habilitante para cualquier cambio grande.
2. **Dos pipelines de promoción coexisten** (legacy knowledge_promotion vs
   promotion_doctype). Definir plan de migración/deprecación; hoy el lector debe
   entender ambos y sus diferencias de fingerprinting/frontmatter.
3. **Contratos por string**: reporting↔doctor (parseo de detail), canonical_tools
   matriz dict-vs-Literal (el `type: ignore[arg-type]` en claude_code.py l.232 lo
   confiesa), `_REQUIRED_BY_DOC_TYPE` duplicando bullets del docstring (server.py
   l.2350, con comentario "keep them in sync"). Mover estos contratos a datos
   tipados compartidos.
4. **Tests de uninstall por adapter**: los bugs de cwd (puntos 4.x) muestran que
   falta un test que ejecute inject+uninstall desde un cwd distinto al root.
5. **Estado de sesión del server** (`_called_tools`, `_last_proposal_emitted_at`)
   debería ser por-sesión conversacional o vivir en SessionService, no en atributos
   del proceso.
6. **Log rotation**: cada arranque crea `mcp_calls_<ts>.log` en `.cortex/logs/`
   (server.py l.248-251) sin cleanup — crecimiento ilimitado.
7. **`_tool_call_history` en memoria crece sin tope** (server.py l.226-244) —
   leak lento en procesos longevos.

## 7. Preparación para un cambio grande — qué tocaría primero

**Frágil (alto riesgo al tocar):**
- `mcp/server.py`: el acople schema-dispatcher-handler significa que agregar un
  tool toca 3 lugares (+ canonical_tools + prompts de skills). Cambios de
  contrato de `AgentMemory` se propagan directo aquí.
- Adapters de IDE: formatos nativos cambian sin aviso; 6 de 11 adapters NO están
  validados contra docs oficiales (registry.py l.48-56). No confiar en ellos
  para un cambio grande sin re-validar.
- La resolución dual legacy/layout en config.py y models.py (`workspace_layout`
  opcional en TODAS las firmas) duplica cada path-decisión. Consolidar antes de
  cambiar topología.

**Orden sugerido:**
1. Extraer schemas y dispatcher de server.py (refactor mecánico, tests existen:
   tests/unit/mcp/, tests/integration/mcp/).
2. Unificar uninstall/inject alrededor de `project_root` explícito (bug real hoy).
3. Adoptar el patrón de marcadores de codex.py en claude_code/windsurf/pi.
4. Definir el futuro del pipeline de promoción legacy.
5. Corregir versiones SERVER_VERSION/handshake y el guard `_called_tools`
   por-sesión.

**Evaluación de salud general: media-alta.** Enterprise es el subsistema más
limpio (modelos pydantic, gobernanza pura, bien testeado). IDE es funcional pero
con inconsistencias serias de seguridad de datos del adopter (pisar archivos,
uninstalls destructivos/cwd-dependientes). MCP server es robusto en su capa
defensiva (aprendida de incidentes reales y bien documentada) pero es un
monolito de ~3k líneas con estado global difuso. Ningún bug encontrado bloquea
el uso normal; los más serios son destructivos solo en uninstall (Pi) o
degradan gobernanza silenciosamente (`_called_tools`, ADMIN_TEAM muerto).
