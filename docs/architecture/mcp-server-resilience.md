# MCP Server Resilience — contrato y arquitectura defensiva

**Estado:** Vigente desde Fase 1 del plan `docs/multi-ide-mcp-hardening/` (2026-05-15).
**Aplica a:** `cortex/mcp/server.py` + `cortex/mcp/_subprocess.py` + `cortex/embedders/onnx.py`.

---

## 1. Invariante

> El MCP server debe responder **siempre** que el IDE este abierto en un proyecto con Cortex instalado. Bajo cualquier carga (concurrente, payload grande, subprocess colgado, modelo cargando, pipe stderr saturado), el server siempre devuelve una respuesta dentro del timeout configurado del tool — aunque la respuesta sea un error estructurado.

Esto es la consigna firmada por el creador para el plan multi-IDE. No hay degradacion gracil: o el server responde con datos, o responde con un error claro. **Nunca cuelga.**

---

## 2. Las capas defensivas

El server se compone de 4 capas defensivas (Fase 1) + 1 capa de observabilidad (Capa 5, Fase 2). Cada capa puede fallar y el resto sigue funcionando.

### Capa 1 — Aislar el transport del trabajo

**Que protege contra:** un handler bloqueante (subprocess sin timeout, carga de modelo, IO masivo) congela el event loop async del server. Sin esta capa, el handler dispatch sincrono dentro de `handle_call_tool` puede bloquearse esperando datos de un subprocess colgado, y el server entero deja de responder a otros tools mientras espera.

**Como funciona:**

- `__init__` crea un `concurrent.futures.ThreadPoolExecutor(max_workers=4)` (configurable via env `CORTEX_MCP_MAX_WORKERS`).
- `handle_call_tool` (async) corre `_dispatch_tool_sync` en un thread del executor:

  ```python
  result_text = await asyncio.wait_for(
      loop.run_in_executor(self._executor, self._dispatch_tool_sync, name, arguments),
      timeout=self._TOOL_TIMEOUTS.get(name, self._TOOL_TIMEOUT_DEFAULT),
  )
  ```

- Tabla `_TOOL_TIMEOUTS` (class-level) define overrides por tool:
  | Tool | Timeout |
  |---|---|
  | (default) | 30 s |
  | `cortex_search_vector` | 60 s (primera invocacion carga ONNX) |
  | `cortex_sync_vault` | 120 s (indexacion masiva de disco) |
- Si excede el timeout: `asyncio.TimeoutError` se captura y devuelve un mensaje estructurado al cliente. El thread queda libre cuando el subprocess termina naturalmente; el server NO espera.

**Tests:** `tests/unit/mcp/test_dispatcher_timeout.py`.

### Capa 2 — Logging exclusivo a archivo en modo stdio

**Que protege contra:** el bug exacto del incidente del 2026-05-15. En modo stdio (el unico transport del MCP actualmente), `logging.StreamHandler(sys.stderr)` bloquea por contrapresion del pipe stderr si Claude Code (u otro cliente) no lo drena rapido.

**Como funciona:**

- `__init__` configura `logging.basicConfig` con `handlers=[FileHandler(log_file)]` por defecto. NO `StreamHandler(sys.stderr)`.
- Escape hatch para debugging: `CORTEX_MCP_LOG_TO_STDERR=1` agrega el handler stderr. Solo el valor literal `"1"` lo activa (whitelist estricta).

**Tests:** `tests/unit/mcp/test_logging_stdio.py`.

### Capa 3 — Defensive subprocess

**Que protege contra:** subprocesos que se cuelgan (git lock, antivirus de Windows escaneando `.git/`, comando inexistente, permisos), y procesos zombie en Windows que retienen handles del pipe MCP cuando el padre muere.

**Como funciona:**

- Helper unico `cortex.mcp._subprocess.safe_run(cmd, cwd, timeout, env)`:
  - **Nunca propaga exceptions** — siempre devuelve `Result(ok, stdout, stderr, returncode, error)`.
  - Captura `TimeoutExpired`, `FileNotFoundError`, `PermissionError`, `OSError`.
  - En Windows: `creationflags=CREATE_NEW_PROCESS_GROUP` para que matar el padre no deje hijos zombie con handles del pipe stdio.
- Helper auxiliar `git_branch_exists(branch, cwd)` para pre-validacion barata (~100ms) antes de invocar `git diff <branch>` (que es 10-100x mas caro). Usado en `_verify_session_claims_text`.

**Tests:** `tests/unit/mcp/test_safe_subprocess.py`.

### Capa 5 (Fase 2) — Health-check `cortex_ping`

**Que protege contra:** un cliente que gasta tiempo y contexto en un tool MCP costoso (`cortex_search_vector`, `cortex_save_session`) cuando el server esta en estado degradado y va a fallar de todas formas. Sin un health-check rapido, el cliente solo se entera del fallo despues de esperar el timeout completo.

**Como funciona:**

- Nuevo tool MCP `cortex_ping` con `inputSchema` vacio (no requiere argumentos).
- Timeout corto: 5 segundos (fail-fast).
- Latencia objetivo: <50ms p99. Verificado en CI con test parametrizado.
- Devuelve JSON estructurado con: `status`, `version`, `uptime_seconds`, `indices_loaded`, `models_loaded`, `last_error_seen`.

**Estados del `status`:**

| Valor | Significado | Cuando |
|---|---|---|
| `starting` | Server arranco hace muy poco | `uptime_seconds < 2.0` (configurable) |
| `degraded` | Hay errores recientes en el rolling buffer | Tras grace period y `len(_error_history) > 0` |
| `ok` | Todo verde | Tras grace period y sin errores recientes |

**Tracking de errores (`_error_history`):**

- `collections.deque(maxlen=10)` — buffer circular de los ultimos 10 errores.
- Poblado automaticamente por `handle_call_tool` cuando captura timeout o exception.
- Cada entry tiene `tool`, `timestamp` (ISO), `error` (mensaje sanitizado).
- Mensaje **truncado a 200 caracteres** para evitar acumular tracebacks con paths sensibles.
- Sin persistencia: reinicio del server limpia la cola.

**Contrato con los agentes (lectura prescriptiva):**

> Cuando un agente Cortex (cortex-documenter, cortex-code-explorer, cortex-code-implementer) arranca, debe invocar `cortex_ping` como primera operacion. Si la respuesta no es `status: ok`, **abortar la operacion** con error claro al usuario:
>
> > El MCP server de Cortex no esta disponible (status: <status>; last_error: <error>). Reinicia el IDE o ejecuta `cortex doctor` para diagnosticar.
>
> NO intentar fallback manual. NO escribir markdown a mano. NO degradar features.

La materializacion de este contrato en los prompts canonicos se hace en Fase 4 (al refactorizar los adapters).

**Tests:** `tests/unit/mcp/test_ping.py` (14 tests: estructura JSON, version, uptime, los 3 states, last_error_seen y truncamiento, maxlen del buffer, models_loaded, latencia p99 <50ms, dispatch via `_dispatch_tool_sync`).

### Capa 4 — ONNX lazy + cached + locked

**Que protege contra:** dos requests concurrentes a `cortex_search_vector` cuando el modelo aun no esta cargado disparan **dos cargas paralelas** del modelo (~10 MB cada una). Esto es race condition en la inicializacion interna de chromadb y duplica memoria.

**Como funciona:**

- `cortex.embedders.onnx.OnnxEmbedder` usa double-check locking:
  - Class-level `_load_lock: threading.Lock` compartido entre instancias.
  - Class-level `_onnx_fn: Any` cachea el resultado.
  - Fast path: si `_onnx_fn` ya esta, devolverlo sin tomar el lock.
  - Slow path: lock + re-check + cargar si todavia None.
- El singleton class-level garantiza que aun cuando multiples adapters/services creen sus propios `OnnxEmbedder`, solo UNA carga total del modelo ocurre por proceso.

**Tests:** `tests/unit/semantic/test_onnx_embedder_concurrent.py`.

---

## 3. Contrato de tool calls visto desde el cliente

Despues de Fase 1, todo cliente MCP ve este contrato:

1. **Cada tool call tiene un timeout maximo.** Si excede, recibe un `TextContent` con mensaje:
   `"❌ Tool '<name>' excedio el timeout (<N>s). El handler quedo bloqueado — el server continua operando."`
2. **Cada tool call que falla devuelve un mensaje de error estructurado.** No hay propagacion de exceptions al cliente.
3. **El server permanece responsivo** aun cuando un tool especifico esta tardando — el cliente puede invocar otros tools en paralelo.
4. **Tools desconocidos** devuelven `"Herramienta desconocida: <name>"` (no crashean).

---

## 3.1 Health-check (Capa 5 — Fase 2)

Adicional al contrato basico de tools: el cliente debe invocar `cortex_ping` antes de operaciones costosas. El ping responde en <50ms con un JSON estructurado:

```json
{
  "status": "ok" | "degraded" | "starting",
  "version": "2.2",
  "uptime_seconds": 123.456,
  "indices_loaded": true,
  "models_loaded": ["onnx-embeddings"],
  "last_error_seen": {
    "tool": "cortex_search_vector",
    "timestamp": "2026-05-15T15:30:42",
    "error": "timeout after 60.0s"
  }
}
```

Si `status != "ok"`, el cliente DEBE abortar con error claro al usuario. NO intentar fallback manual. NO degradar features.

## 4. Configuracion via variables de entorno

| Variable | Default | Efecto |
|---|---|---|
| `CORTEX_MCP_MAX_WORKERS` | `4` | Tamaño del ThreadPoolExecutor. Minimo 1. |
| `CORTEX_MCP_LOG_TO_STDERR` | (unset) | Si `"1"`, agrega `StreamHandler(sys.stderr)` al logging. Util para debug local. |

---

## 5. Bugs no cubiertos por estas capas

Documentados explicitamente para que las fases futuras los aborden:

- **Reinicio automatico del MCP server tras crash**: si el proceso `cortex mcp-server --stdio` muere (OOM, kill -9), no se reinicia automaticamente. El cliente debe re-conectar. La Capa 5 (`cortex_ping`) permite a los agentes detectar esto y reportar al usuario.
- **Persistencia de tracking de errores**: `last_error_seen` (Capa 5) vive solo en memoria. Reinicio del server limpia la cola. Trade-off aceptado: el tracking es para diagnostico inmediato, no para auditoria historica (esa va al `mcp_calls_*.log`).
- **Distribucion del executor entre tools**: 4 workers compartidos por todos los tools. Si 4 requests lentos saturan, el 5to espera en la cola — pero con `asyncio.wait_for` no se cuelga indefinidamente, recibe timeout.

---

## 6. Referencia rapida de archivos

| Componente | Archivo |
|---|---|
| Server principal | `cortex/mcp/server.py` |
| Defensive subprocess helper | `cortex/mcp/_subprocess.py` |
| ONNX embedder con lock | `cortex/embedders/onnx.py` |
| Tests del logging stdio | `tests/unit/mcp/test_logging_stdio.py` |
| Tests del defensive subprocess | `tests/unit/mcp/test_safe_subprocess.py` |
| Tests del dispatcher con executor | `tests/unit/mcp/test_dispatcher_timeout.py` |
| Tests del ONNX concurrent load | `tests/unit/semantic/test_onnx_embedder_concurrent.py` |
| Tests de cortex_ping y last_error_seen | `tests/unit/mcp/test_ping.py` |
| Plan que origino las 4 capas defensivas | `docs/multi-ide-mcp-hardening/FASE-1-mcp-defensivo.md` |
| Plan que origino la Capa 5 (ping) | `docs/multi-ide-mcp-hardening/FASE-2-health-check.md` |
