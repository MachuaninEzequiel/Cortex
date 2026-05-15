# FASE 1 — MCP server defensivo (4 capas)

**Semaforo:** Rojo (toca el invariante critico "MCP siempre disponible").
**Pre-requisitos:** Fase 0 cerrada (en particular seccion 4 de `INVENTARIO.md`).
**Bloquea:** Fase 2.

---

## Objetivo

Refactorizar `cortex/mcp/server.py` y dependencias para que el MCP server **no pueda colgarse** mientras el IDE este abierto. La condicion de exito es: ante cualquier carga (concurrente, payload grande, subprocess colgado, modelo ONNX cargando, pipe stderr saturado), el server **siempre responde** dentro del timeout configurado del tool, aunque la respuesta sea un error estructurado.

Este es el invariante que el creador definio: **el MCP server debe funcionar siempre que el IDE este abierto en un proyecto con Cortex instalado.** Sin esta fase, el resto del plan no resuelve el problema raiz.

---

## Las 4 capas

### Capa 1 — Aislar el transport (stdio) del trabajo

**Problema actual:** `mcp.server.stdio.stdio_server` tiene un loop async que procesa requests serialmente. Si una tool call bloquea (subprocess sin timeout, lock, IO grande), el read del stdio se atasca y el cliente percibe el server como muerto.

**Solucion:** Las implementaciones de tool no bloquean el loop. Cada tool call se delega a un `concurrent.futures.ThreadPoolExecutor` con timeout enforced, y el resultado se devuelve al loop async via `asyncio.wait_for(loop.run_in_executor(...), timeout=N)`.

- Timeout default: 30s (configurable por tool).
- Tools que ya saben que pueden tardar (ej. `cortex_search_vector` con ONNX cargando) declaran timeout propio mas largo.
- Si timeout: el handler MCP devuelve un error estructurado (no propaga exception).

### Capa 2 — Logging exclusivo a archivo en modo stdio

**Problema actual:** `cortex/mcp/server.py:50-57` configura `logging.basicConfig` con `StreamHandler(sys.stderr)`. En Windows, si Claude Code no drena rapido el pipe stderr del subproceso MCP, el siguiente `logger.info(...)` se bloquea por contrapresion del pipe — y bloquea el handler async entero.

**Solucion:** En modo `--stdio`, los handlers de logging van **solo a archivo** (`logs/mcp_calls_<timestamp>.log`). stderr queda libre para que el harness MCP lo use como canal de error opcional sin riesgo de bloqueo. En modo no-stdio (HTTP, debug), se mantiene stderr como hoy.

### Capa 3 — Defensive subprocess

**Problema actual:** `cortex_verify_session_claims` (linea 942) ejecuta `subprocess.run(["git", "diff", "--unified=0", base, "--"], timeout=10)` sin validar que `base` exista, y sin manejo especifico de Windows zombies.

**Solucion:**
- **Pre-validacion**: antes del `git diff`, ejecutar `git rev-parse --verify <base>` con timeout 2s. Si la rama no existe, devolver error claro inmediatamente.
- **Windows-safe**: `subprocess.run` con `creationflags=subprocess.CREATE_NEW_PROCESS_GROUP` (solo en Windows) para que matar el padre no deje hijos colgados con handles del pipe MCP.
- **Excepciones envueltas**: capturar `FileNotFoundError`, `TimeoutExpired`, `PermissionError`, `OSError` y devolver `Result` estructurado. NUNCA propagar al handler MCP.
- **Mismo patron** aplicado a TODOS los sites de subprocess que Fase 0 detecte en `INVENTARIO.md` seccion 4.

### Capa 4 — Lazy + cached + locked en operaciones costosas

**Problema actual:** `cortex_search_vector` carga modelos ONNX en el primer hit. Sin lock, dos requests concurrentes pueden disparar dos cargas en paralelo (memoria duplicada, tiempo duplicado, race condition al cachear).

**Solucion:**
- `asyncio.Lock` (o `threading.Lock` si la carga es sincrona) alrededor de la inicializacion del modelo.
- Cache TTL para embeddings calculados con eviction policy (LRU bounded).
- Si la carga supera N segundos (configurable, default 60s), abortar la primera carga y devolver error temporal — no morir, no quedar inconsistente.
- Pre-warm opcional al startup del MCP server (`--warm-models` flag) para adopters que prefieren pagar el costo upfront.

---

## Tasks

### Task 1.1 — Logging a archivo en modo stdio

**Archivos:**
- `cortex/mcp/server.py` (modificar `__init__` y `run`).

**Cambios:**
- Detectar el modo (stdio vs http) al construir `CortexMCPServer`.
- En stdio: `handlers=[FileHandler(log_file)]` (sin StreamHandler).
- Mantener `StreamHandler(sys.stderr)` solo en modo http o si `CORTEX_MCP_LOG_TO_STDERR=1`.

**Tests:**
- `tests/unit/mcp/test_logging_stdio.py`: verificar que en modo stdio, escribir 10000 lineas de log no bloquea el handler async (test de stress con pipe stderr saturado simulado).

### Task 1.2 — Defensive subprocess

**Archivos:**
- `cortex/mcp/server.py` (todos los sites de subprocess detectados en Fase 0).
- Posible nuevo helper `cortex/mcp/_subprocess.py` con `safe_run(cmd, timeout, cwd) -> Result`.

**Cambios:**
- Helper `safe_run` que envuelve `subprocess.run`, aplica `CREATE_NEW_PROCESS_GROUP` en Windows, captura excepciones, devuelve `Result(ok: bool, stdout: str, stderr: str, error: str | None)`.
- Reemplazar todos los sites de subprocess por `safe_run`.
- En `_verify_session_claims_text`: pre-validar la rama base con `git rev-parse --verify`.

**Tests:**
- `tests/unit/mcp/test_safe_subprocess.py`: 
  - timeout devuelve Result con error y NO propaga.
  - Comando inexistente devuelve Result con error.
  - Branch inexistente en `_verify_session_claims_text` devuelve mensaje claro sin ejecutar el diff.
  - (Solo Windows en CI) verificar que el subprocess termina cleanly al timeout.

### Task 1.3 — ThreadPoolExecutor + timeout por tool

**Archivos:**
- `cortex/mcp/server.py` (envolver el dispatch de `handle_call_tool`).
- Posible nuevo `cortex/mcp/_dispatcher.py` con la logica de executor + timeout.

**Cambios:**
- `ThreadPoolExecutor(max_workers=4)` (configurable via env).
- Cada tool declara su `timeout_seconds` (default 30s, override por tool en una tabla).
- `handle_call_tool` envuelve la implementacion con `asyncio.wait_for(loop.run_in_executor(...), timeout=tool_timeout)`.
- Si timeout: devolver `TextContent` con mensaje estructurado (`status: timeout`, `tool: <name>`, `timeout_seconds: N`).

**Tests:**
- `tests/unit/mcp/test_dispatcher_timeout.py`:
  - Tool simulado que duerme N+5s devuelve timeout estructurado, no exception.
  - Tool exitoso pasa por el executor sin overhead funcional.
  - Concurrencia: 10 requests simultaneos no se serializan (latencia N+epsilon, no N*10).

### Task 1.4 — ONNX lazy + cached + locked

**Archivos:**
- `cortex/semantic/vector_cache.py` (la carga de modelo).
- Posible nuevo `cortex/semantic/_model_loader.py` con la abstraccion.

**Cambios:**
- `threading.Lock` (la carga es sincrona, no async) alrededor de la inicializacion.
- Cache LRU bounded para embeddings (max N entries, configurable).
- Pre-warm flag `--warm-models` en el CLI del MCP server.
- Timeout de carga (default 60s) — si excede, abortar y reportar error.

**Tests:**
- `tests/unit/semantic/test_model_loader_concurrent.py`:
  - 5 threads cargan en paralelo: solo se hace 1 carga real, las otras 4 esperan y reusan.
  - Cache LRU: superar el bound elimina la entrada mas vieja.

### Task 1.5 — Documentacion del nuevo contrato

**Archivos:**
- Actualizar `cortex/mcp/server.py` docstring de `CortexMCPServer` con el modelo de defensive layers.
- Agregar seccion en `docs/architecture/` (si existe el folder; si no, crear `docs/architecture/mcp-server-resilience.md`).

---

## Criterios de aceptacion

- [ ] Las 4 capas implementadas con tests pasando.
- [ ] Smoke manual: arrancar `cortex mcp-server --stdio`, llamar `cortex_verify_session_claims` con base inexistente — recibe error claro en <2s.
- [ ] Smoke manual: llamar `cortex_search_vector` desde 5 clientes simultaneos — todos reciben respuesta, ninguno timeout.
- [ ] Stress test: log de 100k lineas durante operacion — el server sigue respondiendo.
- [ ] El incidente de drop completo del MCP del 2026-05-15 NO se reproduce con el server defensivo.

---

## Gate de cero deuda tecnica

- [ ] CERO `TODO` agregados.
- [ ] CERO sites de `subprocess.run` o `subprocess.Popen` directos en `cortex/mcp/`. Todos pasan por `safe_run`.
- [ ] CERO sites de `subprocess.run` o `Popen` en codigo MCP-adyacente sin timeout explicito.
- [ ] CERO logging a stderr en modo stdio.
- [ ] CERO carga de modelos sin lock.
- [ ] Tests cubren los 4 modos de fallo: timeout, subprocess crash, pipe saturado, carga concurrente.
- [ ] El refactor no introduce flags de feature transitorios. Si la nueva arquitectura es la correcta, es la unica.
- [ ] Documentacion (`mcp-server-resilience.md` u homologo) describe las 4 capas y los timeouts default.

---

## Riesgos y mitigaciones

| Riesgo | Mitigacion |
|---|---|
| El refactor introduce regresiones en tools que no se reescribieron pero comparten infraestructura | Tests de contrato para CADA tool expuesto, ejecutados antes de mergear. |
| El timeout default (30s) es muy bajo para alguna tool legitimamente lenta | Tabla por-tool con override; documentar como ajustar para casos especificos. |
| ThreadPoolExecutor con max_workers=4 es bottleneck en uso intensivo | Hacer configurable via `CORTEX_MCP_MAX_WORKERS`. Tests de carga para validar el default. |
| El lock de modelos serializa todas las cargas de embeddings | Verificar que el lock es solo en la INICIALIZACION del modelo, no en cada inferencia. La inferencia debe seguir siendo paralelizable. |
| El cambio de logging rompe tooling de debug actual | Mantener `CORTEX_MCP_LOG_TO_STDERR=1` env como escape hatch documentado. |

---

## Estimacion

3-4 sesiones serias. Es la fase mas grande del plan. Sub-tasks mapeables 1:1 a 4 ramas / 4 PRs si se prefiere granular.

---

## Handoff a Fase 2

```yaml
agent: fase-1-mcp-defensivo
status: completed
artifacts_produced:
  - cortex/mcp/server.py (refactored)
  - cortex/mcp/_subprocess.py (new helper)
  - cortex/mcp/_dispatcher.py (new helper)
  - cortex/semantic/_model_loader.py (new abstraction)
  - tests/unit/mcp/test_logging_stdio.py
  - tests/unit/mcp/test_safe_subprocess.py
  - tests/unit/mcp/test_dispatcher_timeout.py
  - tests/unit/semantic/test_model_loader_concurrent.py
  - docs/architecture/mcp-server-resilience.md
verified_claims:
  - "MCP server resiste pipe stderr saturado, subprocess colgado, carga concurrente, ONNX init"
  - "Incidente del 2026-05-15 no se reproduce con server defensivo"
context_for_next:
  - "Fase 2 (cortex_ping) ya tiene la infraestructura para responder rapido — el dispatcher de Capa 3 garantiza <50ms"
```
