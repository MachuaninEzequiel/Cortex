# 🧠 Guía de Uso de Cortex — Manual Maestro

> **Documento de referencia único para el uso diario de Cortex.**
> Cubre: el ciclo de vida de una sesión, **los cuatro modos operativos**
> (Managed, Observed, BYO y el propuesto COMPOSED), cada familia de
> comandos con ejemplos verificados, la memoria híbrida, docs y CI, el
> MCP para agentes, el Action Engine, el brain local, la TUI y la
> configuración avanzada.
>
> Prerequisito: instalación completa → [`GUIA-INSTALACION.md`](GUIA-INSTALACION.md).
>
> Versión del documento: **2026-08-27** · Todas las salidas de ejemplo
> fueron capturadas contra el binario nativo 0.7.0 real.

---

## 1. El modelo mental de Cortex

Cortex organiza el trabajo de agentes alrededor de **tres conceptos**:

```
┌────────────────────────────────────────────────────────────┐
│  VAULT   el conocimiento curado del proyecto (markdown)     │
│          specs · notas · decisiones · runbooks · designs    │
├────────────────────────────────────────────────────────────┤
│  SESSION  la unidad de trabajo: spec → checkpoints → close  │
│           (open) → trabajo → (checkpoints/tasks) → finish   │
├────────────────────────────────────────────────────────────┤
│  MEMORIA  lo que pasó (episódica) + lo que sabemos (vault)  │
│          fusionado por RRF para retrieval híbrido           │
└────────────────────────────────────────────────────────────┘
```

**La Sesión es el corazón.** Todo trabajo significativo abre una sesión
(spec-driven), registra progreso en checkpoints (inmutables, append-only),
y se cierra con verificación (`cortex finish-session`). El **modo** de la
sesión describe *cómo llegaron los checkpoints* — y se infiere solo.

**La regla de oro:** *"listo" significa probado, no dicho*. El cierre corre
verification hooks declarados en la spec, y el documenter reconstruye la
nota de sesión con la evidencia real.

---

## 2. Arranque diario (el flujo de 60 segundos)

```bash
cd ~/mi-proyecto

cortex session current          # ¿hay sesión activa? ¿cuál?
cortex session list             # todas las sesiones en disco
cortex next                     # ¿qué sugiere el Action Engine?
cortex search "estado pagos"    # ¿qué sabemos/memorizamos sobre X?
cortex context                  # bundle de contexto para la tarea actual
```

Si es la primera vez en el día:

```bash
cortex doctor                   # salud del proyecto (rápido)
cortex tutor                    # guía interactiva offline
cortex hint                     # tip contextual de qué hacer ahora
```

---

## 3. Referencia rápida de comandos (todas las familias)

| Familia | Subcomandos | Para qué |
|---|---|---|
| `cortex session` | current · list · show · switch · diff · checkpoint · abandon · task ×5 · hooks ×4 · watch/tui | El ciclo de vida de sesiones |
| `cortex search` | `search <query>` | Retrieval híbrido (episódico + semántico) |
| `cortex context` | `context [-f format]` | Bundle de contexto enriquecido |
| `cortex next` | `next [--json]` | Sugerencias del Action Engine |
| `cortex stats` | `stats` | Estado de memoria y topología |
| `cortex reindex` | `reindex --dry-run` | Plan de rebuild del índice semántico |
| `cortex remember/forget` | `remember <content>` · `forget <id>` | Escritura/borrado episódico directo |
| `cortex docs` | search · migrate · validate · restore · list-backups · routing-table | Gobierno del vault |
| `cortex ci` | validate-pr · open-review-session · report-checkpoint · close-review-session | Plugin CI |
| `cortex pr-context` | capture · store · search · generate · full | Contexto de PRs |
| `cortex hu` | import · list · show | Work items externos (Jira) |
| `cortex ide` | list · setup · remove · status | Integraciones con IDEs/agentes |
| `cortex setup` | agent · pipeline · full · webgraph · enterprise | Bootstrap por perfil |
| `cortex autopilot` | start · preflight · checkpoint · finish · status · doctor | Capa de decisión |
| `cortex webgraph` | export · serve · doctor | Visualización web del grafo |
| `cortex mcp-serve` | (server stdio) | Servidor MCP para agentes |
| `cortex init` | `init --non-interactive` | Alias de `setup agent` |
| `cortex doctor` / `tutor` / `hint` | — | Salud, guía, tips |
| `cortex brain` | (binario separado) | Asistente local (ver §10) |

> 💡 `info`: todos los comandos aceptan `--project-root <ruta>` para operar
> sobre un proyecto distinto del cwd, y la mayoría `--json` para salida
> machine-readable.

---

## 4. Los modos operativos (Managed / Observed / BYO / COMPOSED)

### 4.1 Qué es el "modo" y cómo se infiere

El `mode` de una sesión describe **quién y cómo registró el progreso**
(checkpoints). Se infiere automáticamente al cerrar la sesión, según el
origen de los checkpoints:

| Modo | Cuándo se infiere | Cómo se registra el progreso |
|---|---|---|
| `managed` | Todos los checkpoints vienen de agentes de Cortex (`cortex-sync`, `cortex-SDDwork`, `cortex-code-*`) | Un skill orquestador verifica cada paso antes de avanzar |
| `observed` | Los checkpoints vienen de hooks del IDE (`ide-hook`), skills del usuario o manual | Tu IDE emite checkpoints automáticamente |
| `byo` | **Ningún** checkpoint — solo git diff | Traés tu workflow; el reconstructor sintetiza la sesión desde el diff |
| `ci-review` | Todos los checkpoints son `ci-bot` | Auditoría de CI (plug-in) |
| `composed` *(propuesto)* | Checkpoints con **fase** (`grill→spec→plan→implement→review`) de skills externas | Cualquier cadena de skills; Cortex registra y documenta |

> Ver el estado de una sesión: `cortex session show <id> --json` y mirá el
> campo `mode` (mientras está abierta: `unknown`; al cerrarse se fija).

### 4.2 Modo Managed — el camino recomendado sin flujo propio

El modo Managed es el que Cortex orquesta con su skill **`cortex-SDDwork`**
(instalada por `cortex setup agent` en `.cortex/skills/`). El contrato es
la **Sesión** (cero YAML entre subagentes).

**Flujo típico:**

```bash
cd ~/mi-proyecto
cortex session current                      # pre-flight: debe existir sesión abierta
# (si no: abrirla — ver §5.1)
```

1. **Sync/pre-flight** (`cortex-sync`): crea la spec, inyecta contexto
   histórico (`cortex_sync_ticket` es obligatorio antes de `create_spec` —
   el server MCP lo exige).
2. **SDDwork decide la vía:**
   - 🟢 **FAST TRACK** (1-2 archivos): implementa y emite **un checkpoint**
     con `source=cortex-SDDwork`, claims verificados y artefactos.
   - 🔴 **DEEP TRACK** (refactor grande): delega a subagentes
     `cortex-code-explorer` → `cortex-code-designer` → `cortex-code-implementer`
     — cada uno emite su propio checkpoint y `cortex_review_checkpoint`
     gatea entre pasos (redelegate → repetir con guidance; warn → anotar).
3. **Cierre:** el usuario cierra con `cortex finish-session` (o el
   oráculo `/cortex-documenter` en el IDE).

Comandos útiles del modo Managed:

```bash
cortex session checkpoint --source cortex-SDDwork \
  --note "implementé X" \
  --verified-claim "corre tests de <módulo>" \
  --verified-claim "clippy sin warnings" \
  --artifact src/nuevo.rs --artifact tests/nuevo_test.rs
```

### 4.3 Modo Observed — tu IDE emite checkpoints

Con los hooks instalados (`cortex session hooks install --ide <tu-ide>`),
tu IDE ejecuta un artefacto que llama a `cortex session checkpoint
--source ide-hook` automáticamente (p. ej. cursor: git post-commit;
claude_code/pi/opencode: evento del IDE).

**No tenés que hacer nada en el flujo:** trabajás, y cada acción relevante
deja su checkpoint. El cierre reconstruye la sesión rica en eventos reales.

```bash
# Verificar que el hook está activo:
cortex session hooks status --ide cursor
# forzar un checkpoint manual si querés:
cortex session checkpoint --source manual --note "decisión: usar serde_json"
```

### 4.4 Modo BYO — traé tu flujo, Cortex lo sintetiza

Sin checkpoints: trabajás con tu agente/proceso como siempre, y al cerrar,
el documenter **reconstruye la sesión desde git diff** (archivos tocados,
scope vs spec, archivos fuera de alcance, unimplemented).

```bash
cortex finish-session     # sintetiza: diff real + spec = nota verificable
```

Ideal para el usuario que no quiere que Cortex intervenga en el medio —
solo quiere la **documentación y la verificación al final**.

### 4.5 Modo COMPOSED (propuesta — ver `docs/transformacion/PROPUESTA-MODO-COMPOSED.md`)

El cuarto modo, en diseño: cualquier cadena de skills externas
(mattpocock-style, superpowers-style, o propias) que emite checkpoints
**con fase** (`grill`, `spec`, `plan`, `implement`, `review`, `close`).
Cortex no orquesta: reconoce, registra la línea de fases y documenta. El
contrato es un checkpoint enriquecido; la familia de skills de referencia
se instalaría con `cortex setup composed` (cuando se implemente).

---

## 5. Sesiones — la guía completa

### 5.1 Abrir una sesión

Hoy el arranque de una sesión se hace con el flujo orquestador
(cortex-sync en Managed) o desde los adapters/hooks del IDE. Desde el CLI
nativo, el control es:

```bash
cortex session current                    # ¿cuál es la activa?
# → 2026-08-26_refactor                    (o error si no hay)
```

Con una sesión cerrada y querés trabajar sobre otra spec:

```bash
cortex session switch 2026-08-24_pagos    # activa otra sesión existente
cortex session current --json             # info completa de la activa
```

### 5.2 Registrar progreso: checkpoints

```bash
cortex session checkpoint \
  --note "avance: autenticación con refresh tokens" \
  --verified-claim "pasa tests/unit/test_auth.py" \
  --verified-claim "fmt y clippy limpios" \
  --unverified-claim "el backend JWT soporta rotación" \
  --artifact cortex/auth/refresh.py

# respuesta: checkpoint #N appended (source=manual) to <session_id>
```

| Flag | Significado |
|---|---|
| `--source` | `manual`, `cortex-SDDwork`, `ide-hook`, `user-skill`, `cortex-sync`, `cortex-code-*`, `ci-bot` |
| `--verified-claim` (repetible) | Lo que verificaste (leíste archivos, corriste tests) |
| `--unverified-claim` (repetible) | Lo que asumís sin probar |
| `--artifact` (repetible) | Paths que tocaste |
| `--session-id` | Apuntar a otra sesión (default: activa) |
| `--json` | Salida machine-readable |

> Los checkpoints son **inmutables** (`frozen=True`): append-only, nunca se
> editan. Son la materia prima del documenter al cerrar.

### 5.3 Tareas dentro de una sesión (session task)

Las sesiones tienen tareas con estado `pending | in-progress | done |
skipped | blocked`:

```bash
cortex session task list                          # tareas de la sesión activa
cortex session task list --status in-progress     # filtro
cortex session task list --json                   # machine-readable

cortex session task done T1.2 --note "implementado"
cortex session task in-progress T1.1
cortex session task skip T1.3 --reason "no hace falta"
cortex session task block T1.4 --reason "bloqueado por API externa"
```

Salida texto: `T1.2 → done` · JSON: `{"session_id", "task_id", "status"}`.
Los ids siguen el patrón `T\d+(\.\d+)*` (validado).

### 5.4 Ver la sesión

```bash
cortex session list                      # tabla rich con ID/STATUS/MODE/OPENED/CKPTS/SUMMARY
cortex session list --status open        # filtro por estado
cortex session list --json               # array de records completos

cortex session show 2026-08-24_pagos     # detalle: status, mode, spec, summary, checkpoints
cortex session show --json 2026-08-24_pagos

cortex session diff 2026-08-24_pagos     # diff git del rango de la sesión
```

### 5.5 Pantalla en vivo (TUI)

```bash
cortex session watch                      # pantalla ratatui en vivo (requiere TTY)
cortex session watch --status open        # filtro
cortex session tui                        # alias del mismo entrypoint
```

Sin TTY (CI/docker), emite un **snapshot** del render actual y sale con
rc 0 — útil para capturas y verificación.

### 5.6 Abandonar una sesión

```bash
cortex session abandon 2026-08-24_pagos --reason "cambio de prioridad"
# o con confirmación explícita:
cortex session abandon 2026-08-24_pagos --reason "…" --yes
```

Cierra la sesión como `abandoned` con checkpoint MANUAL de la razón.

### 5.7 Cerrar una sesión (finish-session)

El cierre corre **verification hooks** declarados en la spec y el
**documenter** reconstruye la nota:

```bash
cortex finish-session
# pasos internos:
#   1. reconstruct (gitless o git-aware según la sesión)
#   2. suggested_status (CLOSED si todos los hooks pasan y no hay
#      archivos unimplemented; HANDOFF si no)
#   3. nota de sesión + ADRs sugeridos  4. persiste
```

> El comando escribe la nota y devuelve el payload con
> `session_note_path` — la ruta física de la nota generada. Es el
> entregable final del ciclo: *la sesión documentada con evidencia*.

---

## 6. Memoria: búsqueda y contexto

### 6.1 `cortex search`

Retrieval híbrido que fusiona las dos capas con **RRF** (Reciprocal Rank
Fusion):

```bash
cortex search "pagos" --top-k 5
```

Salida real (ejemplo):

```text
Query: 'pagos'

Unified Results (RRF-fused across both sources):
  [SEMANTIC] Ubiquitous Language Guide  (…/vault/context.md)  score=0.0164
  [SEMANTIC] Architecture Overview      (…/vault/architecture.md)  score=0.0161
  [SEMANTIC] Runbooks                    (…/vault/runbooks/README.md)  score=0.0159
```

Filtros disponibles (verificados):

| Flag | Uso |
|---|---|
| `-k, --top-k` | Cantidad de resultados (default 5) |
| `--doc-type` / `--exclude-doc-type` (repetible) | Filtrar por tipo de doc del vault |
| `--status`, `--tag`, `--tag-any` | Filtrar por frontmatter |
| `--scope all` | Ámbito del vault |
| `--max-age-days` | Solo docs recientes |
| `--project-id` | Multi-proyecto |
| `--strict` | Solo matches estrictos |
| `-f, --format text\|json\|compact` | Formato de salida |
| `--json` | Salida JSON |

### 6.2 `cortex context`

Bundle de contexto enriquecido para la tarea actual (inyección a agentes):

```bash
cortex context                            # formato markdown (default)
cortex context -f compact                 # más breve
cortex context -f markdown -e             # expandir
cortex context -o archivo.md              # volcar a archivo
cortex context -f src/a.rs -f src/b.rs    # context centrado en archivos
```

La salida incluye memorias relacionadas (semánticas y episódicas) con el
motivo de match (`Matched by: topic_search, file_search`).

### 6.3 Escribir/borrar memoria directa

```bash
cortex remember "Refactor del núcleo de búsqueda híbrida completado" \
  --type decision --tag arquitectura --file rust/crates/cortex-app/src/search.rs

# → Memory stored -> mem_abc123…
#   type: decision
#   summary: Refactor del núcleo…

cortex forget mem_abc123
# → Memory mem_abc123 deleted.
```

Flags de `remember`: `-t/--type`, `--tag` (repetible), `--file`
(repetible), `--branch`, `--repo`, `--commit`, `-s/--summarize`.

### 6.4 `cortex stats` y `cortex reindex`

```bash
cortex stats
# {
#   "episodic_count": 0,
#   "semantic_docs": 4,
#   "vault_path": "…/.cortex/vault",
#   "persist_dir": "…/.cortex/.memory/chroma",
#   "enterprise_topology": "profile=small-company, …"
# }

cortex reindex --dry-run
# [dry-run] reindex plan: model/backend · vault · would move → backup …
```

> ⚠️ `reindex` **sin** `--dry-run` es fallo explícito en el binario nativo
> (aún no hay escritor de vector-cache persistente). Si necesitás rebuild
> real, usá el oráculo Python legacy en desarrollo.

---

## 7. Docx, CI y PR Context (familias de gobernanza)

### 7.1 `cortex docs`

```bash
# buscar dentro del vault (con filtros semánticos/estructurales)
cortex docs search "auth" --doc-type adr --format text
cortex docs search "auth" --json
cortex docs search "auth" -k 10 --exclude-doc-type runbook

# migración del vault (Fase 11)
cortex docs migrate --apply                          # aplicar migración
cortex docs migrate --apply --force --no-backup      # sin backup
cortex docs migrate --path <vault> --output report.json --json

# validación estructural
cortex docs validate
cortex docs validate --json     # payload {vault_path, total, valid, invalid, no_frontmatter, issues}

# backups y restore
cortex docs list-backups
cortex docs restore <backup> --target <dir>   # → Restored: <ruta>
cortex docs routing-table                     # tabla canónica DOC_TYPE_ROUTING
cortex docs routing-table --doc-type adr --json
```

### 7.2 `cortex ci` — plugin de CI

```bash
# validar un PR contra sesiones (exit codes: 0 pass · 1 warn · 2 blocked · 3 error)
cortex ci validate-pr --base-commit <sha> --head-branch <rama> \
  --pr-number 42 --format json
cortex ci validate-pr --format text
cortex ci validate-pr --format pr-comment          # comentario listo para el PR

# sesión de review (ciclo completo)
cortex ci open-review-session --base-commit <sha> --head-branch <rama> --pr-number 42
cortex ci report-checkpoint --from-validation-result result.json
cortex ci close-review-session --status closed     # closed | handoff | abandoned
```

El exit code es parte del contrato: en un pipeline CI, `0` deja pasar,
`1` avisa, `2` bloquea (gate) y `3` es error interno.

### 7.3 `cortex pr-context`

```bash
# captura del estado del PR → .pr-context.json
cortex pr-context capture --title "Demo PR" --body "…" --head-branch feat/x

# store: recuerda el contexto + enriquece
cortex pr-context store --context-file .pr-context.json
cortex pr-context store --context-file .pr-context.json --lint-result "pass" --test-result "pass"

# búsqueda de contexto pasado relacionado
cortex pr-context search --context-file .pr-context.json --top-k 3
# → escribe .past-context.json con los candidatos relacionados

# genera docs desde el contexto (DocGenerator; escribe en el vault)
cortex pr-context generate --context-file .pr-context.json --vault vault

# full = capture → store → search → generate → sync
cortex pr-context full --title "Demo" --head-branch feat/x
```

### 7.4 `cortex hu` — work items externos

```bash
cortex hu list                          # notas de items importados
cortex hu show <item-id>                # ruta de la nota local
cortex hu import PROJ-123 --provider jira
# → Tracked item imported -> <ruta>
cortex hu import PROJ-123 --no-remember # sin resumen episódico
```

> Para fetch HTTP real de Jira hace falta configurar `integrations.jira`
> (base_url + credenciales por env `JIRA_EMAIL`/`JIRA_API_TOKEN`); el
> binario nativo hoy lee `file://` (gate hermético) — ver deuda en
> `12-AUDITORIA-PYTHON-RESIDUAL.md` §9.6.

---

## 8. Autopilot y Webgraph

### 8.1 `cortex autopilot` — capa de decisión

```bash
cortex autopilot preflight --request "investigar refactor de auth"
cortex autopilot preflight --file src/a.rs --file src/b.rs --json

# adopta la sesión activa bajo un modo
cortex autopilot start --mode observe        # observe | assist | autopilot
cortex autopilot start --json

# checkpoints de autopilot (source default manual)
cortex autopilot checkpoint --note "…" --verified-claim "…" --artifact "…"
cortex autopilot checkpoint --source cortex-SDDwork --in-scope src/ --in-scope tests/

cortex autopilot finish        # cierra con documentación automática
cortex autopilot status
cortex autopilot doctor        # diagnóstico (config/sessions/adapters/hooks/finish/service)
```

> `autopilot doctor` es read-only; rc 0 siempre (como el oráculo). Los
> subcomandos `install`/`uninstall` fueron **eliminados en Fase 04** del
> oráculo — usá `cortex session hooks install/uninstall --ide X`.

### 8.2 `cortex webgraph`

```bash
cortex webgraph export                    # snapshot del grafo (JSON)
cortex webgraph export --mode hybrid --no-cache --workspace-file <f>
cortex webgraph serve                     # sirve la UI (axum) — requiere TTY (Ctrl+C)
cortex webgraph serve --host 0.0.0.0 --port 8080 --no-open
cortex webgraph doctor                    # 5 checks de prerequisitos
```

---

## 9. MCP para agentes (cómo los agentes hablan con Cortex)

### 9.1 Arrancar el servidor

```bash
cortex mcp-serve                 # stdio, bloqueante — lo lanza el cliente MCP
cortex mcp-server --project-root /ruta        # equivalente
```

### 9.2 Tools expuestas (familias verificadas en el catálogo real)

| Familia | Tools |
|---|---|
| **Core/ping** | `cortex_ping` |
| **Búsqueda** | `cortex_search`, `cortex_search_vector`, `cortex_context` |
| **Specs** | `cortex_sync_ticket`, `cortex_create_spec`, `cortex_emit_proposal` |
| **Docs** | `cortex_write_doc` (11+ doc types), `cortex_self_review_note`, `cortex_import_hu`, `cortex_get_hu` |
| **Sesiones** | `cortex_session_open`, `cortex_session_checkpoint`, `cortex_session_close`, `cortex_session_status`, `cortex_session_list`, `cortex_save_session`, `cortex_finish_session`, `cortex_close_session`, `cortex_session_task_list`, `cortex_session_task_update` |
| **Review** | `cortex_review_checkpoint`, `cortex_verify_session_claims`, `cortex_documenter_briefing` |
| **Autopilot** | `cortex_autopilot_start`, `_preflight`, `_checkpoint`, `_finish`, `_status` |

### 9.3 Config en tu agente

Claude Code (`.mcp.json` del proyecto):

```json
{ "mcpServers": { "cortex": { "command": "cortex-cli", "args": ["mcp-serve"] } } }
```

La mayoría de los IDEs: `cortex ide setup --ide <tu-ide>` ya escribe esta
config. Después, en el agente: pedile usar `cortex_search`/`cortex_context`
para memoria, `cortex_session_*` para registrar trabajo, `cortex_write_doc`
para documentar.

---

## 10. Action Engine y Brain

### 10.1 Action Engine (`cortex next`)

Cortex **sugiere** el siguiente paso útil, rankeado con score:

```bash
cortex next
# 🧠 Cortex · 3 acción(es) sugeridas:
#  [1] Validar los documentos del vault   id: vault.validate_docs · score: 8.0
#  [2] Re-indexar el vault semántico      id: vault.reindex · score: 5.0
#  [3] Aprender un tópico del tutor hoy   id: learn.topic · score: 3.0

cortex next --json                    # machine-readable (elapsed_ms + acciones)
cortex next --all                     # todas, sin filtro
cortex next --explain-why-not         # por qué NO se sugieren más
cortex next --stats                   # métricas del motor
```

El motor **aprende** de tus decisiones (accept/skip) vía
`.cortex/actions.yaml` y de las señales de búsqueda
(`[y]=útil` en la TUI) — dominio negativo ⇒ suben acciones de
calidad/mantenimiento; positivo ⇒ de aprendizaje.

### 10.2 Brain (`cortex-brain`)

Asistente conversacional local (Rust + llama.cpp, opcional):

```bash
cortex-brain --model          # con LLM (GGUF en ~/.cache/cortex/models/)
cortex-brain                  # determinista sin modelo (router, cero tokens)
cortex-brain --window         # ventana dedicada
```

Reglas de diseño del brain:
- **Nunca muta.** Las tools son read-only; las mutaciones vuelven como
  comandos exactos para que las corras vos.
- **Bilingüe**: `ui.language: es|en`.
- Tool `actions.propose`: muestra las sugerencias del Action Engine como
  comandos ejecutables.

Ejemplo real:

```text
🧠 cortex-brain — backend: llama.cpp (GGUF)
Vos: ¿cuántas notas hay en el vault?
🔧 sugerencia del modelo [read]: vault.stats
¿Ejecutás 'vault.stats' ? [s/N]: s
Vault: 128 notas .md
```

---

## 11. La TUI (ratatui)

```bash
cortex session watch            # pantalla de sesiones en vivo
```

- **Interacción:** `q`/`Ctrl+C` salen; tick ~250 ms; el snapshot se
  reconstruye por tick (las sesiones cambian en disco).
- **Sin TTY:** emite un snapshot único (útil en CI) y sale rc 0.
- Datos = exactamente los mismos que `cortex session list --json`
  (paridad verificada por gate).

El Home TUI (`cortex-tui`) muestra: proyecto/rama, sesión activa, acciones
pendientes, notas del vault, salud (mcp/vault/embeddings) y tips de atajos
(`a=acciones s=sesión /=buscar q=salir`).

---

## 12. Configuración avanzada y escenarios

### 12.1 Multi-proyecto / `--project-root`

Todas las familias aceptan `--project-root <ruta>`:

```bash
cortex session list --project-root /ruta/otro/proyecto
cortex docs validate --project-root /ruta/otro/proyecto
cortex mcp-server --project-root /ruta/otro/proyecto
```

### 12.2 Idioma

```yaml
# .cortex/config.yaml
ui:
  language: en        # UI del brain y la TUI en inglés (default: es)
```

### 12.3 Embeddings por idioma

El bloque `embedding.per_language` activa español mejorado (e5-large,
MRR@10 0.96). Quitarlo = mono-modelo MiniLM. La detección de idioma es
por frontmatter (`lang: es`) o heurística (`language_detection: heuristic`).

### 12.4 Enterprise (pipeline/org)

```bash
cortex setup enterprise --org-config org-file.yaml --preset <p> --json
cortex org-config
cortex review-knowledge           # cola de review enterprise
cortex promote-knowledge          # promover candidatos revisados
cortex memory-report              # salud de memoria enterprise
```

### 12.5 Escenario completo día-a-día (Managed)

```bash
# Mañana: retomar trabajo
cortex session current && cortex next

# Abrir sesión para una spec nueva (flujo orquestado)
cortex session checkpoint --source cortex-sync --note "spec auth v2"
cortex session checkpoint --source cortex-SDDwork \
  --verified-claim "tests auth v2 pasan" --artifact cortex/auth/

# Trabajo con el IDE (modo observed si el hook está instalado)…
# …o cerrar directo (BYO reconstruye del diff):
cortex finish-session

# Documentar/consultar después
cortex search "auth v2" && cortex context -f compact
```

### 12.6 Escenario con agentes (MCP)

```text
1. cortex mcp-serve en la config del agente (o `cortex ide setup`)
2. El agente usa cortex_search para memoria
3. cortex_session_checkpoint para registrar avances
4. cortex_write_doc al terminar
5. El humano cierra con cortex finish-session (verificación real)
```

---

## 13. Errores comunes de uso (y qué significan)

| Error | Causa | Solución |
|---|---|---|
| `Session not found: <id>` | sesión inexistente o id mal escrito | `cortex session list` para ver ids exactos |
| `No active session…` de SDDwork | falta abrir/pre-flight | correr el flujo cortex-sync primero |
| `Cannot update task in session with status 'X'` | sesión cerrada/abandonada | abrir o usar otra sesión |
| `Task id 'T99' not found…` | tarea inexistente | `cortex session task list` para ver las reales |
| `✗ Memory <id> not found` | forget con id inexistente | verificar el id (mayúsculas/guiones) |
| `Unknown work item provider: x` | provider mal escrito | usar `jira` (único provider hoy) |
| `Unknown doc_type: x` | doc-type inválido | la lista válida viene en el mensaje |
| `No such command '<x>'.` (rc 2) | subcomando no existe (baja física) | ver la familia con `cortex <fam>` (sin subcomando) |
| `reindex real no nativo…` | reindex sin --dry-run | usar `--dry-run` o el oráculo Python legacy |
| `watch: terminal no interactivo — snapshot emitido` | sin TTY | es normal en CI; usá TTY para el modo vivo |
| `CORTEX_PY=1 es rollback histórico` (aviso) | variable de entorno vieja | desactivar la var: `unset CORTEX_PY` |

---

## 14. Dónde seguir

| Tema | Recurso |
|---|---|
| Instalación completa | [`GUIA-INSTALACION.md`](GUIA-INSTALACION.md) |
| Los modos en detalle | [`docs/transformacion/02-ESTANDAR-UNICO-IDE-CLI.md`](../docs/transformacion/02-ESTANDAR-UNICO-IDE-CLI.md) |
| Propuesta Modo 4 (COMPOSED) | [`docs/transformacion/PROPUESTA-MODO-COMPOSED.md`](../docs/transformacion/PROPUESTA-MODO-COMPOSED.md) |
| Estado del proyecto y deuda | [`docs/transformacion/12-AUDITORIA-PYTHON-RESIDUAL.md`](../docs/transformacion/12-AUDITORIA-PYTHON-RESIDUAL.md) §9 |
| Guía interactiva offline | `cortex tutor` · `cortex hint` |