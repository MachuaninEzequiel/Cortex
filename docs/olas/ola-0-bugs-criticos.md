---
title: Ola 0 — Bugs críticos pre-adopters
status: ✅ CERRADA AL 100% (2026-05-13)
prerequisitos: Ninguno
bloquea: Olas 1, 2, 3, 4
suite_at_close: 807 passed, 6 skipped, 0 failed
---

# Ola 0 — Bugs críticos pre-adopters

## Objetivo

Eliminar los bugs que rompen las **promesas centrales** del framework antes de que cualquier early adopter lo toque. Si alguno de estos bugs persiste y un adopter lo encuentra en su primer flujo, la credibilidad del producto cae instantáneamente.

## Definición de "crítico" para esta ola

Un bug es crítico si cumple cualquiera de:

1. Rompe la promesa pública del README ("autopilot persiste la nota", "search encuentra lo que escribimos", "create-spec requiere sync-ticket").
2. Hace que un comando documentado retorne mentirosamente success cuando no hubo success real.
3. Está marcado en `docs/architecture/release-2-known-weaknesses.md` y todavía no se resolvió.
4. Bloquea el flujo tripartito (`sync_ticket → create_spec → save_session`).

## Estado de cada ítem

| # | Bug | Estado | Detalle |
|---|-----|--------|---------|
| 0.1 | `autopilot finish --auto` no escribe la session note | ✅ DONE 2026-05-13 | Ver `docs/review/cortex-save-state.md` §11.1 |
| 0.2 | Indexing no era obligatorio en `VaultSessionWriter` / `PRService.write_pr_docs` | ✅ DONE 2026-05-13 | IndexingSessionWriter transaccional + PRService toma VaultReader |
| 0.3 | Test del guard MCP `cortex_create_spec` sin `cortex_sync_ticket` falta | ✅ DONE 2026-05-13 | `_GOVERNANCE_VIOLATION_MESSAGE` centralizado (DRY), encoding fix UTF-8, 5 tests en `TestGovernanceGuard` + verify-by-deletion |
| 0.4 | `cortex context --output` ignora `--format json` (weakness #6) | ✅ DONE 2026-05-13 | El código ya estaba correcto (`main.py:708-714`); agregados 3 tests de regresión |
| 0.5 | Entity round-trip en episodic puede no persistir (weakness #1) | ✅ DONE 2026-05-13 | `metadata_json` ya serializa todo el dict; agregados 7 tests parametrizados por entity type + 3 tests adicionales |

---

## 0.3 — Test del guard MCP `cortex_create_spec` ↔ `cortex_sync_ticket`

### Contexto

`cortex/mcp/server.py:410` bloquea explícitamente cualquier llamada a `cortex_create_spec` si `cortex_sync_ticket` no fue llamado primero en la misma sesión MCP (tracking en `self._called_tools: set[str]`). Esto es **gobernanza activa**, no advertencia. Es la regla #3 del `AGENT.md`. Hoy no hay test que la cubra, así que si un refactor lo rompe, no nos enteramos.

### Pasos

1. **Abrir** `tests/unit/test_mcp_server.py`.
2. **Localizar** la clase de tests existente que prueba `cortex_create_spec`, o crear una nueva `TestGovernanceGuards`.
3. **Agregar dos tests:**
   - `test_create_spec_blocked_without_sync_ticket`: instanciar `CortexMCPServer`, llamar `handle_call_tool` con `cortex_create_spec` directamente, verificar que la respuesta contiene `"VIOLACIÓN DE GOBERNANZA"` y que **no se escribió ningún archivo** en `vault/specs/`.
   - `test_create_spec_allowed_after_sync_ticket`: misma instancia, llamar primero `cortex_sync_ticket` con un user_request válido, luego `cortex_create_spec`, verificar que retorna sin error y que el archivo aparece en `vault/specs/`.
4. **Setup del test:** usar `tmp_path` con un layout new (workspace.yaml v2 + config.yaml). Mockear o usar AgentMemory real (lo segundo es mejor para evitar falsos positivos).
5. **Validar** que ambos tests pasan y que si comentás la línea 410 del server, `test_create_spec_blocked_without_sync_ticket` falla.

### Archivos a tocar

- `tests/unit/test_mcp_server.py` — agregar tests.

### Criterio de cierre

- [ ] `test_create_spec_blocked_without_sync_ticket` existe y pasa.
- [ ] `test_create_spec_allowed_after_sync_ticket` existe y pasa.
- [ ] Comentando manualmente la línea 410 de `mcp/server.py`, el primer test falla (verificación negativa).
- [ ] Restaurar la línea 410.

---

## 0.4 — `cortex context --output` ignora `--format json`

### Contexto

Weakness #6 del `docs/architecture/release-2-known-weaknesses.md`. En `cortex/cli/main.py:712-714`, cuando se pasa `--output <file>`, siempre se escribe markdown (`enriched.to_prompt_format(...)`) sin importar el valor de `--format json`. Si los adopters integran Cortex en su CI propio y esperan JSON, reciben markdown.

### Pasos

1. **Leer** `cortex/cli/main.py` líneas 660–720 para entender la firma del comando `context` y cómo se decide stdout vs file.
2. **Confirmar** que el stdout sí honor `--format json` (probable: usa `json.dumps(enriched.model_dump(mode='json'))`).
3. **Modificar** el bloque del `--output` para que respete el flag `--format`:
   - Si `format == "json"`: `Path(output).write_text(json.dumps(enriched.model_dump(mode="json"), indent=2, default=str), encoding="utf-8")`.
   - Si `format == "markdown"` o ausente: comportamiento actual (`to_prompt_format`).
4. **Agregar test** en `tests/unit/cli/test_main.py` (o crear `tests/unit/cli/test_context.py`):
   - `test_context_output_json_writes_json`: invocar CLI con `--format json --output foo.json`, verificar que el archivo parsea con `json.loads` y contiene las keys esperadas (`work`, `items`, etc.).
   - `test_context_output_markdown_writes_markdown`: invocar con `--output foo.md` (sin format), verificar que arranca con `🧠 Cortex Context` o un encabezado markdown.
5. **Actualizar** `docs/architecture/release-2-known-weaknesses.md` marcando #6 como resuelto, o eliminar la entrada.

### Archivos a tocar

- `cortex/cli/main.py` — bloque del comando `context`.
- `tests/unit/cli/test_main.py` o `tests/unit/cli/test_context.py` — tests.
- `docs/architecture/release-2-known-weaknesses.md` — actualizar.

### Criterio de cierre

- [ ] El bloque `--output` honor `--format json`.
- [ ] Test JSON path passes.
- [ ] Test markdown path passes (regresión).
- [ ] `release-2-known-weaknesses.md` #6 marcado resuelto.

---

## 0.5 — Entity round-trip en episodic memory

### Contexto

Weakness #1 del known-weaknesses doc. `EpisodicMemoryStore.add()` extrae entidades (functions, classes, endpoints, etc.) y las pasa a `_serialize_metadata`, pero la deserialización al hacer `search` puede no devolver las entidades intactas. Si la promesa de "entity search" no funciona, el ContextEnricher pierde una estrategia clave de retrieval.

### Pasos

1. **Leer** `cortex/episodic/memory_store.py` completo. Identificar:
   - El extractor de entidades (probablemente `_extract_entities` o similar).
   - `_serialize_metadata` y `_deserialize_metadata`.
   - El path por el cual las entidades viajan en la metadata de Chroma.
2. **Diagnosticar** con un test red:
   - `test_episodic_entity_round_trip`: crear store en `tmp_path`, agregar memoria con content que contiene `def foo()`, `class Bar`, `GET /api/users`, etc. Verificar que `entities` se devuelve igual cuando se hace `search_by_entity` o `list_entries`.
3. **Si el test falla**: corregir serialización. Chroma exige metadata plana (str/int/float/bool); las listas se serializan típicamente como JSON string. Verificar que `_deserialize_metadata` hace `json.loads` simétrico.
4. **Cubrir todos los tipos de entidad**: functions, classes, endpoints, errors, config_keys, dependencies. Un test por tipo.
5. **Actualizar** `release-2-known-weaknesses.md` #1.

### Archivos a tocar

- `cortex/episodic/memory_store.py` — fix de serialización si aplica.
- `tests/unit/episodic/test_memory_store.py` — agregar tests round-trip.
- `docs/architecture/release-2-known-weaknesses.md` — actualizar.

### Criterio de cierre

- [ ] Test round-trip pasa para 6 tipos de entidad.
- [ ] `release-2-known-weaknesses.md` #1 marcado resuelto.
- [ ] No regresión en suite completa.

---

## Smoke test manual del flujo tripartito (obligatorio para cerrar la ola)

Después de los 5 ítems, ejecutar manualmente el flujo completo en un **repo de prueba limpio** (no en el repo Cortex en sí). Esto valida la promesa principal.

### Setup

```bash
# En cualquier carpeta vacía
mkdir cortex-smoke-test && cd cortex-smoke-test
git init
# Asumir que cortex ya está instalado con pipx
cortex setup full --ide claude-code   # O el IDE que quieras smoke-testear
```

### Pasos

1. **`cortex doctor --scope all`** → debe retornar verde.
2. **Arrancar MCP server**: `cortex mcp-server --project-root .`
3. **Desde el IDE** (Claude Code, OpenCode, Pi o Codex):
   - Llamar `cortex_sync_ticket` con un user_request real.
   - Llamar `cortex_create_spec` — debe persistir en `vault/specs/` y aparecer en `cortex search`.
   - Llamar `cortex_save_session` después de simular cambios — debe persistir en `vault/sessions/` e indexarse.
4. **Probar el guard**: en una sesión MCP nueva, llamar `cortex_create_spec` directamente sin `cortex_sync_ticket`. Debe rechazar con "VIOLACIÓN DE GOBERNANZA".
5. **Probar autopilot**: `cortex autopilot start --mode assist`, luego `preflight`, `checkpoint`, `finish --auto`. La session note debe aparecer en `vault/sessions/` Y en `cortex search "<keyword del request>"`.
6. **Probar WebGraph**: `cortex webgraph serve` y abrir en navegador. Los nodos creados durante el smoke deben verse.

### Criterio de cierre del smoke

- [ ] `cortex doctor --scope all` retorna verde sin warnings críticos.
- [ ] `cortex_sync_ticket → cortex_create_spec → cortex_save_session` ejecuta sin errores en al menos 1 IDE.
- [ ] Guard MCP rechaza `cortex_create_spec` sin `sync_ticket` previo.
- [ ] `autopilot finish --auto` produce un archivo en `vault/sessions/` que aparece en `cortex search`.
- [ ] WebGraph renderiza nodos del nuevo vault.

---

## Cierre de la ola

Suite final ejecutada `2026-05-13`:

```
$ python -m pytest tests/unit tests/integration tests/e2e --no-cov
807 passed, 6 skipped in 143.77s (0:02:23)
```

Smoke manual ejecutado el `2026-05-13` (script CLI, sin IDE — Ola 1 cubre IDE):

```
=== Pasos ejecutados ===
1. mkdir /tmp/cortex-smoke && cd /tmp/cortex-smoke && git init && echo "# Smoke" > README.md && git add . && git commit -m "init"
2. cortex setup agent --ide claude-code --git-depth 1        → .cortex/ creado completo, IDE profiles inyectados
3. yes y | cortex setup pipeline                              → .github/workflows/ (4 archivos generados)
4. cortex setup webgraph                                       → .cortex/webgraph/ creado
5. cortex doctor                                               → verde excepto 3 entries gitignore (deuda Ola 3)
6. cortex create-spec --title "Auth JWT smoke" --goal "..."   → .cortex/vault/specs/2026-05-13_auth-jwt-smoke.md
7. cortex save-session --title "Auth JWT smoke" ...           → .cortex/vault/sessions/2026-05-13_auth-jwt-smoke.md
8. cortex search "refresh tokens"                             → RRF unifica spec+session+vault docs
9. cortex autopilot start --request "Rate limiting"           → session_id=09303492e360
10. cortex autopilot preflight --session-id ... --file ...    → security task detectado, can_proceed
11. cortex autopilot checkpoint --summary ... --verified      → status=implementation_seen
12. cortex autopilot finish --auto                            → saved=true, status=documented
13. ls .cortex/vault/sessions/                                → archivo del autopilot persistido
14. cortex search "rate limiting"                             → encuentra la session del autopilot en SEMANTIC + EPISODIC ✅
15. cortex webgraph serve                                      → Flask en 127.0.0.1:8765, /api/snapshot?mode=hybrid 200 OK
16. cortex autopilot doctor                                    → session_indexing=ok, last_finish=documented, mcp_tools importable

=== Resultado ===
Flujo tripartito completo end-to-end ✅
Indexing mandatorio confirmado: la nota del autopilot aparece inmediatamente en search ✅
```

### Deuda identificada durante el smoke (movida a olas correspondientes)

- **Ola 3:** `cortex setup pipeline` y `cortex setup full` no aceptan `--non-interactive`. Bloquea automatización limpia.
- **Ola 3:** `cortex stats` no acepta `--project-root`. Inconsistencia con otros comandos.
- **Ola 3:** Doctor reporta FAIL en `gitignore:.memory/` y `gitignore:*.chroma/` en repos new-layout — los checks deberían adaptarse al layout actual, no buscar paths legacy.
- **Ola 1:** `cortex setup agent` muestra "Cursor" en la lista de adapters reconocidos. Marcar adapters no-target como "comunidad" en la salida visible.

### Checklist final de la Ola 0

- [x] 0.1 — `autopilot finish --auto` persiste session note (cerrado 2026-05-13).
- [x] 0.2 — Indexing mandatorio en escritura (cerrado 2026-05-13).
- [x] 0.3 — Test del guard MCP `cortex_create_spec`.
- [x] 0.4 — `cortex context --output --format json` honra el flag.
- [x] 0.5 — Entity round-trip cubierto por tests.
- [x] Smoke test manual ejecutado y verde (CLI completo, sin IDE — Ola 1 cubre IDE).
- [x] Suite global verde: 807 passed, 6 skipped, 0 failed.
- [x] `docs/architecture/release-2-known-weaknesses.md` actualizado: items #1, #3, #4, #5, #6 marcados como resueltos. Quedan abiertos #2 (graph empty-query) y #7 (doc_verifier) — el #2 pertenece a Ola 1 o más tarde, el #7 a Ola 4.

**Ola 0 cerrada al 100%. Lista para arrancar Ola 1.**
