# FASE 2 — REALIZACION

**Fecha de ejecucion:** 2026-05-15
**Output formal:** tool `cortex_ping` + tracking `last_error_seen` integrados a `cortex/mcp/server.py`; doc `docs/architecture/mcp-server-resilience.md` ampliado con Capa 5.
**Estado:** Completada. 14 tests nuevos pasando, 120 tests preexistentes sin regresion (134 totales). Linter `ruff` verde.

---

## 1. Tasks ejecutadas

| Task | Descripcion | Archivo principal |
|---|---|---|
| 2.1 | Implementar tool `cortex_ping` | `cortex/mcp/server.py` (definicion del tool + handler `_ping_text`) |
| 2.2 | Tracking interno `last_error_seen` con buffer rolling | `cortex/mcp/server.py` (`_error_history`, `_register_error`, hook en `handle_call_tool`) |
| 2.3 | Tests de latencia, estados, y no-leak de secrets | `tests/unit/mcp/test_ping.py` (14 tests) |
| 2.4 | Documentacion del nuevo contrato + este archivo | `docs/architecture/mcp-server-resilience.md` (Capa 5) + este archivo |

---

## 2. Decisiones tomadas durante la realizacion

### 2.1 Schema del payload del ping

**Decision:** devolver JSON con las 6 keys: `status`, `version`, `uptime_seconds`, `indices_loaded`, `models_loaded`, `last_error_seen`.

**Razon:**
- `status` (`ok` / `degraded` / `starting`) es la accion-clave que el agente lee primero. Bool no sirve porque hay 3 estados conceptuales.
- `version` permite al cliente detectar incompatibilidad de protocolo sin parsing especial.
- `uptime_seconds` permite distinguir entre "el server arranco hace 10s y todavia inicializa indices" vs "el server lleva 1h corriendo y empezo a fallar ahora".
- `indices_loaded` y `models_loaded` son indicadores granulares para diagnostico. Un agente puede ver `status: degraded` + `models_loaded: []` y entender que ONNX nunca cargo.
- `last_error_seen` permite al agente reportar al usuario un mensaje accionable, no un generico "MCP no disponible".

### 2.2 Status `starting` con grace period configurable

**Decision:** introducir constante `_STARTUP_GRACE_SECONDS = 2.0`. Mientras `uptime_seconds < _STARTUP_GRACE_SECONDS`, el status es `"starting"`.

**Razon:** evita falsos negativos durante el arranque. Sin esta gracia, un ping inmediato post-init veria errores transitorios del primer momento (carga de configs, locks) como `degraded`. Con el grace period, el agente sabe que tiene que reintentar si recibe `starting`.

El threshold es `_STARTUP_GRACE_SECONDS: float` class-level — los tests lo override con `monkeypatch` para no esperar 2 segundos reales.

### 2.3 Tracking sanitizado: solo mensaje top-level, truncado

**Decision:** `_register_error(tool, msg)` recibe solo el mensaje (string), no la exception completa. Trunca a 200 chars (`_ERROR_MESSAGE_MAX_CHARS`) con sufijo `...`.

**Razon:**
- El `last_error_seen` se expone via MCP a cualquier cliente. Si guardasemos tracebacks completos, podriamos leakear paths del filesystem del adopter (ej. `/Users/ana/.cortex/config.yaml`) o nombres de archivos sensibles.
- 200 chars son suficientes para que un humano entienda la categoria del error ("timeout after 60s", "git binary not found", "permission denied opening...").
- El traceback completo SI se loguea a archivo (`mcp_calls_*.log` via `logger.exception`). Esto se mantiene para diagnostico forense en disco — solo el endpoint MCP esta sanitizado.

### 2.4 Buffer circular `collections.deque(maxlen=10)`

**Decision:** mantener los 10 errores mas recientes en memoria.

**Razon:**
- 10 es suficiente para que un agente vea patrones (todos los errores son timeouts de `cortex_search_vector` → ONNX no cargo).
- `deque` con `maxlen` es O(1) en append y descarte automatico del mas viejo. Sin un cleanup manual que se pueda olvidar.
- Sin persistencia: reinicio del server limpia la cola. Esto es intencional — el tracking es para diagnostico inmediato, no auditoria historica (esa la cubre el log a archivo).

### 2.5 `models_loaded` introspecciona el singleton de OnnxEmbedder

**Decision:** dentro de `_ping_text`, hacer `from cortex.embedders.onnx import OnnxEmbedder` y checkear `OnnxEmbedder._onnx_fn is not None`.

**Razon:** Capa 4 (Fase 1) introdujo el singleton class-level del modelo ONNX. Es el unico modo de saber, sin disparar la carga, si el modelo esta listo. El import lazy dentro del metodo evita acoplamiento del modulo del server al de embedders (aunque en runtime ya esta importado por `AgentMemory`).

Si el import falla por algun motivo (en un entorno sin chromadb), el `try/except` defensivo devuelve `models_loaded: []` en lugar de crashear el ping.

### 2.6 Timeout corto para el ping: 5 segundos

**Decision:** `_TOOL_TIMEOUTS["cortex_ping"] = 5.0` (en lugar del default 30s).

**Razon:** el ping NO hace IO, NO toca disco, NO invoca subprocesos. Si responde en mas de 5 segundos, algo esta gravemente mal (event loop totalmente saturado, executor con todos los workers ocupados por tools muy lentos). Mejor fallar rapido que esperar 30s.

Esto es consistente con el "fail-fast diagnostico" del principio rector #3 ("MCP debe funcionar siempre — si cae, abortar").

### 2.7 Test de latencia con threshold p99 <50ms

**Decision:** test que mide 100 llamadas consecutivas y verifica que la p99 (sample 98) este bajo 50ms.

**Razon:** este es el objetivo declarado en el plan. Cubre el caso "ping rapido bajo carga normal". No simulo carga concurrente porque cada test individual pyt corre serial — los tests de carga concurrente real son alcance de Fase 7 (validacion E2E).

50ms es generoso (la implementacion real toma <1ms en hardware moderno). El threshold genero deja margen para CI lento sin causar flakiness.

---

## 3. Cumplimiento del gate de cero deuda tecnica de Fase 2

| Item del gate | Estado |
|---|---|
| CERO `TODO` agregados | OK — grep en archivos modificados devuelve 0. |
| `last_error_seen` no leakea secrets (sanitizado) | OK — truncado a 200 chars, sin traceback. Test `test_error_message_is_truncated` valida el comportamiento. |
| Latencia p99 <50ms verificada | OK — test `test_ping_latency_under_50ms_p99` (100 samples, p99 measured). |
| `cortex_ping` registrado en `handle_list_tools` y dispatch | OK — test `test_ping_dispatchable_via_dispatcher` valida via `_dispatch_tool_sync`. |
| Estados `ok`, `degraded`, `starting` reproducibles | OK — 3 tests dedicados. |
| Buffer rolling respeta maxlen | OK — test `test_error_history_respects_maxlen` agrega 15 errores y verifica que sobreviven solo los 10 mas recientes. |
| Linter `ruff` verde | OK. |
| Documentacion | OK — `mcp-server-resilience.md` Capa 5 + ejemplo de payload en seccion 3.1. |
| CERO flags de feature transitorios | OK — no se agregaron env vars nuevas. |

---

## 4. Acoplamiento con Fase 1 — verificacion

Capa 5 depende de:
- **Capa 1 (executor)**: `cortex_ping` corre en el executor con timeout 5s. Si el executor esta saturado, el ping recibe timeout y el cliente lo sabe. ✓
- **Capa 2 (logging a archivo)**: el ping loguea via `logger.info`, que va al FileHandler. No risk de stderr block. ✓
- **Capa 3 (defensive subprocess)**: el ping NO usa subprocess. No depende de Capa 3 directamente. ✓
- **Capa 4 (ONNX locked)**: el ping introspecciona `OnnxEmbedder._onnx_fn` (singleton class-level) — la misma estructura que la Capa 4 introdujo. No hay race condition porque solo lee, no escribe. ✓

Las 5 capas se refuerzan mutuamente: si el ping mismo se demora (Capa 1 lo aborta), el agente recibe error explicito en lugar de quedarse esperando.

---

## 5. Items para handoff a Fase 3 / Fase 4

### Lo que Fase 4 debe inyectar en los prompts canonicos

El plan original de Fase 2 (`FASE-2-health-check.md` task 2.5) propone un bloque pre-flight check para los prompts canonicos. La inyeccion final se hace en Fase 4 cuando se reescriban los adapters. El bloque a inyectar:

```markdown
## Pre-flight check (obligatorio)

Antes de cualquier otra operacion, invocar `cortex_ping`. Si la respuesta no es `status: "ok"`, abortar la operacion con error claro al usuario:

> El MCP server de Cortex no esta disponible (status: <status>; last_error: <error>). Reinicia el IDE o ejecuta `cortex doctor` para diagnosticar.

NO intentar fallback manual. NO escribir markdown a mano. NO degradar features.
```

Fase 4 lo inyecta en los renders de `cortex_workspace.py`:
- `render_subagent_documenter()`
- `render_subagent_explorer()`
- `render_subagent_implementer()`
- `render_cortex_sync_skill()`
- `render_cortex_sddwork_skill()`

---

## 6. Handoff formal

```yaml
agent: fase-2-health-check
status: completed
artifacts_produced:
  - cortex/mcp/server.py (tool cortex_ping, _ping_text, _register_error,
    _error_history, _startup_time, hook en handle_call_tool)
  - tests/unit/mcp/test_ping.py (14 tests)
  - docs/architecture/mcp-server-resilience.md (Capa 5 + seccion 3.1)
  - docs/multi-ide-mcp-hardening/FASE-2-REALIZACION.md (este documento)
verified_claims:
  - "14 tests nuevos del ping pasando"
  - "120 tests preexistentes sin regresion (134 totales)"
  - "Latencia p99 <50ms validada por test"
  - "last_error_seen sanitizado (truncado, sin traceback)"
  - "buffer rolling respeta maxlen=10"
  - "3 estados (ok/degraded/starting) reproducibles"
  - "Linter ruff verde"
unverified_claims: []
contradicted_claims: []
context_for_next:
  - "Fase 3 puede empezar; canonical_tools.py puede incluir cortex_ping como
    tool MCP estandar"
  - "Fase 4 debe inyectar el bloque pre-flight check (ver seccion 5) en
    los renders de cortex_workspace.py"
  - "Fase 5 puede empezar en paralelo con Fase 3/4; el cleanup del delegate
    no afecta el ping"
suggested_adr: false
```
