# FASE 2 — Health-check / heartbeat (`cortex_ping`)

**Semaforo:** Amarillo.
**Pre-requisitos:** Fase 1 cerrada.
**Bloquea:** Fase 4 (la inyeccion de pre-flight check en prompts canonicos).

---

## Objetivo

Exponer un tool MCP `cortex_ping` que permita a cualquier agente / subagente / IDE verificar **rapidamente** que el MCP server esta operativo antes de gastar tiempo y contexto en operaciones costosas.

Coherencia con principio rector #3 ("MCP debe funcionar siempre"): el heartbeat **no es para fallback**, es para **fail-fast diagnostico**. Si `cortex_ping` falla o timeoutea, el agente aborta con error claro al usuario; no degrada features ni intenta plan B manual.

---

## Tasks

### Task 2.1 — Implementar tool `cortex_ping`

**Archivo:** `cortex/mcp/server.py`.

**Contrato:**

```json
{
  "name": "cortex_ping",
  "description": "Health check rapido del MCP server. Devuelve estado, version, uptime y ultimo error visto. Latencia objetivo <50ms.",
  "inputSchema": {"type": "object", "properties": {}, "required": []}
}
```

**Respuesta:**

```json
{
  "status": "ok" | "degraded" | "starting",
  "version": "x.y.z",
  "uptime_seconds": 1234,
  "indices_loaded": true,
  "models_loaded": ["onnx-embeddings"],
  "last_error_seen": null | {
    "tool": "cortex_search_vector",
    "timestamp": "2026-05-15T12:34:56Z",
    "error": "ONNX model failed to load: missing dependency"
  }
}
```

- `status: ok` — todo verde.
- `status: degraded` — el server responde pero algun subsistema fallo (ej. ONNX no cargo).
- `status: starting` — el server arranco pero indices/modelos aun no estan disponibles.

### Task 2.2 — Tracking interno de `last_error_seen`

**Archivo:** `cortex/mcp/server.py` (state interno) + `cortex/mcp/_dispatcher.py` (donde se capturan los errores en Fase 1, Capa 3).

**Cambios:**
- Cuando el dispatcher captura una exception o timeout, registra el error en una estructura circular en memoria (`deque(maxlen=10)`).
- `cortex_ping` devuelve el ultimo error visto (mas reciente) si existe.
- El tracking es **interno al proceso del MCP server**, no se persiste a disco. Reinicio del server limpia la cola.

**Contrato del registro:**
```python
@dataclass
class TrackedError:
    tool: str
    timestamp: datetime
    error: str  # mensaje, sin traceback completo (privacidad)
```

### Task 2.3 — Latencia objetivo y test de performance

**Archivo:** `tests/unit/mcp/test_ping_performance.py`.

**Tests:**
- `test_ping_latency_under_50ms`: 100 invocaciones consecutivas, p99 < 50ms.
- `test_ping_under_load`: 50 requests concurrentes paralelos al ping mientras otros tools estan ejecutando — el ping mantiene latencia.
- `test_ping_during_degraded_state`: simular ONNX failure, verificar que `status: degraded` y `last_error_seen` populado.
- `test_ping_during_startup`: durante los primeros segundos del server, devuelve `status: starting`.

### Task 2.4 — Documentar contrato y uso recomendado

**Archivo:** `docs/architecture/mcp-server-resilience.md` (creado en Fase 1, ampliar).

**Contenido:**
- Seccion "Health check": describe el contrato de `cortex_ping`.
- Seccion "Pre-flight check pattern": explica que los agentes deberian invocar `cortex_ping` como primera operacion. Aclara explicitamente: si el ping falla, **abortar la operacion**, no continuar con fallback.

### Task 2.5 — Pre-flight check en prompts canonicos (preparar; aplicar en Fase 4)

**Esta fase NO toca los prompts canonicos** (eso es Fase 4). Pero deja documentado en `docs/multi-ide-mcp-hardening/FASE-2-health-check.md` el bloque que Fase 4 va a injectar:

```markdown
## Pre-flight check (obligatorio)

Antes de cualquier otra operacion, invocar `cortex_ping`. Si la respuesta no es `status: ok`, abortar la operacion con error claro al usuario:

> El MCP server de Cortex no esta disponible (status: <status>; last_error: <error>). Reinicia el IDE o ejecuta `cortex doctor` para diagnosticar.

NO intentar fallback manual. NO escribir markdown a mano. NO degradar features.
```

---

## Archivos involucrados

- Nuevos: ninguno (todo dentro de `cortex/mcp/server.py` y tests).
- Modificados:
  - `cortex/mcp/server.py` (agregar tool + state tracking).
  - `cortex/mcp/_dispatcher.py` (hook para registrar errores en `last_error_seen`).
  - `docs/architecture/mcp-server-resilience.md` (ampliar).
- Tests:
  - `tests/unit/mcp/test_ping_performance.py` (nuevo).
  - `tests/unit/mcp/test_ping_states.py` (nuevo).

---

## Criterios de aceptacion

- [ ] `cortex_ping` registrado en `handle_list_tools` y respondiendo.
- [ ] `last_error_seen` populado correctamente cuando el dispatcher captura una exception o timeout.
- [ ] Latencia p99 < 50ms verificada en CI.
- [ ] Estados `ok`, `degraded`, `starting` reproducibles en tests.
- [ ] Documentacion en `mcp-server-resilience.md` completa.
- [ ] Bloque pre-flight check documentado para uso en Fase 4.

---

## Gate de cero deuda tecnica

- [ ] CERO `TODO` agregados.
- [ ] El tracking de `last_error_seen` es la unica fuente de errores expuesta — no hay otra estructura paralela en el server.
- [ ] El test de latencia esta integrado al CI, no es un script suelto.
- [ ] La doc del pre-flight pattern es prescriptiva ("si falla, ABORTAR"), no sugerida.
- [ ] No se introducen flags de feature transitorios.
- [ ] El ping NO depende de subsistemas que pueden fallar (no carga modelos, no hace IO de red, no toca disco). Si una dependencia falla, `status: degraded` lo reporta — pero el ping en si responde.

---

## Riesgos y mitigaciones

| Riesgo | Mitigacion |
|---|---|
| `last_error_seen` expone informacion sensible (paths, secrets) | El error string se sanitiza antes de almacenar — solo el mensaje top-level, sin traceback ni argumentos. Test de no-leak con secret simulado. |
| El ping bajo carga termina serializando con otros tools y latencia degrada | Test de carga concurrente en CI. Si serializa: el dispatcher debe darle prioridad o un executor dedicado. |
| Agentes IGNORAN el pre-flight check y siguen sin chequear | Documentar explicitamente en el contrato del subagente; Fase 4 lo inyecta como primer paso obligatorio del prompt. |

---

## Estimacion

1 sesion. Es una capa fina sobre la infraestructura de Fase 1.

---

## Handoff a Fase 3 / Fase 4

```yaml
agent: fase-2-health-check
status: completed
artifacts_produced:
  - cortex/mcp/server.py (cortex_ping tool)
  - tests/unit/mcp/test_ping_performance.py
  - tests/unit/mcp/test_ping_states.py
  - docs/architecture/mcp-server-resilience.md (ampliado)
verified_claims:
  - "cortex_ping responde <50ms p99 bajo carga"
  - "last_error_seen tracking funciona y no leakea secrets"
context_for_next:
  - "Fase 4 debe inyectar el bloque pre-flight check en los prompts canonicos de cortex-documenter, cortex-code-explorer, cortex-code-implementer"
```
