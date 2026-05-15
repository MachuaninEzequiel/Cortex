# FASE 7 — Validacion end-to-end

**Semaforo:** Amarillo (toca todo el sistema integrado).
**Pre-requisitos:** Fases 1, 2, 3, 4, 5, 6 cerradas.
**Bloquea:** Nada (es la fase de cierre).

---

## Objetivo

Verificar empiricamente que el sistema completo, despues de las 6 fases anteriores, **resuelve el incidente original del 2026-05-15** y **no introduce regresiones** en el flujo del adopter.

Esta fase NO introduce features nuevos; valida que las anteriores funcionan integradas.

---

## Tasks

### Task 7.1 — Reproducir el incidente original con sistema actual

**Setup:**
- Proyecto limpio (puede ser un repo de prueba o un fixture: `tests/fixtures/incident-replay/`).
- Correr `cortex setup full --ide claude-code` (debe ser interactivo desde Fase 6, pero se acepta el flag para automatizar).

**Replay del incidente:**
1. Iniciar Claude Code en el proyecto.
2. Verificar que el MCP server arranca y responde a `cortex_ping` (Fase 2).
3. Crear ~10 archivos en `.cortex/vault/specs/phases/` (simulando el output de cortex-SDDwork).
4. Lanzar el subagente `cortex-documenter` con un prompt grande (similar al del incidente: ~5KB con 13 claims para verificar).
5. Mientras el subagente corre, ejecutar otro tool MCP en paralelo desde el agente principal (forzar concurrencia).
6. Observar:
   - El subagente debe escribir output incremental al task log (NO 0 bytes).
   - El MCP server debe seguir respondiendo a `cortex_ping` durante toda la operacion.
   - Si el subagente falla, debe ser con error claro y abortar — NO quedarse colgado 14 minutos.

**Criterio de exito:** el incidente NO se reproduce.

### Task 7.2 — Smoke test multi-IDE

Repetir un flujo basico (setup + invocar un subagente + persistir una sesion) en al menos dos IDEs:

| IDE | Comando de setup | Verificacion |
|---|---|---|
| claude_code | `cortex setup full --ide claude-code --non-interactive --git-depth 50` | `.claude/agents/*.md` generados; `cortex_ping` responde; subagente `cortex-documenter` ejecuta una tarea simple. |
| opencode | `cortex setup full --ide opencode --non-interactive --git-depth 50` | Archivos de opencode generados; `cortex_ping` responde; comando `opencode run --agent <path>` ejecuta una tarea simple. |

(Si Fase 4 documento que algun IDE adicional esta listo para smoke, agregarlo aqui.)

### Task 7.3 — Test de stress del MCP server

Forzar las condiciones que en el incidente original tumbaron al MCP:

- 50 invocaciones concurrentes de `cortex_search`.
- 10 invocaciones de `cortex_search_vector` (forzar carga de modelo en paralelo).
- Ejecutar `cortex_verify_session_claims` con base inexistente (debe responder rapido con error claro).
- Saturar el log con 100k entradas mientras se sirven requests.

**Criterio:** el MCP server NO crashea, NO se desconecta, sigue respondiendo a `cortex_ping`.

### Task 7.4 — Verificacion de cero deuda tecnica acumulada

Pasar el repo entero por:

```
grep -rE "TODO|FIXME|XXX|HACK" --include="*.py" cortex/ tests/ docs/multi-ide-mcp-hardening/
```

Comparar contra el conteo previo a Fase 0 (capturado durante el inventario). El delta debe ser **0** (cero TODOs nuevos introducidos por el plan).

```
grep -rE "cortex_delegate" --include="*.py" --include="*.md"
```

Debe devolver 0 resultados activos (solo posibles entradas en CHANGELOG historico).

### Task 7.5 — Documentar el postmortem y el cierre

**Archivo nuevo:** `docs/multi-ide-mcp-hardening/CIERRE.md`.

**Contenido:**
- Resumen del incidente original.
- Resumen de los cambios del plan (1 parrafo por fase).
- Evidencia de que el incidente no se reproduce (logs, screenshots, output del replay).
- Smoke tests pasados en cada IDE.
- Lista de TODOs / deuda tecnica preexistente que el plan **no toco** (si la hay), referenciando los `ARRASTRE-N.md` que cada fase pudo haber producido.
- Items para futuras fases: cualquier mejora identificada durante el plan pero **fuera de alcance** (deben tener nombre, justificacion y prioridad).

### Task 7.6 — Persistir sesion de cierre con Cortex (dogfooding)

Usar el propio MCP server (que acaba de ser refactorizado) para persistir la sesion final del plan via `cortex_save_session`:

- title: "Cierre del plan multi-IDE & MCP hardening"
- spec_summary: parrafo breve referenciando `docs/multi-ide-mcp-hardening/README.md`.
- changes_made: lista de archivos modificados (de las 6 fases).
- key_decisions: las 6 decisiones arquitecturales (una por fase).
- next_steps: items diferidos a futuras fases.

Este dogfooding valida que el sistema funciona end-to-end y que la persistencia hace lo que dice.

### Task 7.7 — Doctor command (si aplica)

Si existe `cortex doctor`, verificar que detecta el estado saludable del MCP server post-cambios. Si no existe, evaluar agregarlo como item de plan futuro (no es alcance de este plan).

---

## Archivos involucrados

- Nuevos:
  - `docs/multi-ide-mcp-hardening/CIERRE.md`
  - Posiblemente `tests/integration/test_incident_replay.py` (si se decide congelar el replay como test automatico).
- Modificados: ninguno (esta fase no cambia codigo de produccion).

---

## Criterios de aceptacion

- [ ] El incidente del 2026-05-15 NO se reproduce (Task 7.1).
- [ ] Smoke test pasa en al menos 2 IDEs (Task 7.2).
- [ ] El MCP server resiste el stress test (Task 7.3).
- [ ] CERO TODOs nuevos introducidos por el plan (Task 7.4).
- [ ] CERO referencias activas a `cortex_delegate_*` (Task 7.4).
- [ ] `CIERRE.md` esta cerrado y aprobado por el creador (Task 7.5).
- [ ] La sesion de cierre se persistio via `cortex_save_session` exitosamente (Task 7.6).

---

## Gate de cero deuda tecnica

- [ ] Cualquier TODO descubierto durante la validacion E2E que NO sea responsabilidad de este plan se documenta en `CIERRE.md` con nombre, justificacion y prioridad.
- [ ] Si Task 7.1 detecta que el incidente parcialmente se reproduce: NO se cierra la fase. Se vuelve a la fase responsable (Fase 1, 2 o 4 segun la causa) y se itera.
- [ ] Si Task 7.2 falla en algun IDE soportado: NO se cierra la fase. Se vuelve a Fase 4 y se corrige el adapter responsable.
- [ ] La fase NO se cierra con "casi todo OK; este detalle queda para despues". O esta TODO verde, o se reabre la fase responsable.
- [ ] El `CIERRE.md` documenta el plan futuro de mejoras (Doctor, etc.) PERO no se acepta como ESTE plan. Cualquier mejora identificada va a un plan separado.

---

## Riesgos y mitigaciones

| Riesgo | Mitigacion |
|---|---|
| El incidente se reproduce parcialmente: ej. el subagente NO se cuelga, pero el MCP server tiene latencia degradada bajo carga | Iterar Fase 1 (revisar Capa 3 dispatcher / Capa 4 ONNX) hasta que el stress test pase. NO considerar la fase cerrada. |
| El smoke test en opencode falla porque el adapter de opencode tiene un bug que Fase 4 no detecto | Volver a Fase 4 Task 4.3 (refactorizar adapter), no parchear en Fase 7. |
| Surge un caso de uso inesperado que el plan no contemplo (ej. un IDE soporta delegacion via gRPC) | Documentar en `CIERRE.md` como item para plan futuro. NO meterlo en este plan. |
| Los test de stress son flakey en CI por hardware | Marcar como `@pytest.mark.slow` y correr solo en pipeline de release, no en cada PR. Documentar la decision. |

---

## Estimacion

1-2 sesiones. Mucho del tiempo es validacion manual (smoke tests en cada IDE).

---

## Handoff de cierre del plan

```yaml
agent: fase-7-validacion-e2e
status: completed
artifacts_produced:
  - docs/multi-ide-mcp-hardening/CIERRE.md
  - tests/integration/test_incident_replay.py (opcional)
verified_claims:
  - "Incidente del 2026-05-15 no se reproduce"
  - "Smoke test multi-IDE pasa en claude_code y opencode (minimo)"
  - "MCP server resiste stress test"
  - "Cero TODOs nuevos introducidos por el plan"
  - "Cero referencias activas a cortex_delegate_*"
context_for_next:
  - "Plan multi-IDE & MCP hardening cerrado. Mejoras adicionales identificadas (si las hay) listadas en CIERRE.md como items para futuros planes."
```
