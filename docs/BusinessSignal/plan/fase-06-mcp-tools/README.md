# Fase 6 - MCP Tools

**Fuente:** `docs/BusinessSignal/plan/README.md`
**Estado:** Pendiente de ejecucion

## Introduccion

Permite que agentes consulten senales via MCP sin leer todo el vault. Al terminar, documentar en `REALIZACION.md`.

## Reglas para agentes

- Las MCP tools deben delegar a un service central, no duplicar logica.
- No romper tools MCP existentes.
- Respuestas compactas con presupuesto bajo.

## Archivos a crear

```text
cortex/business_signal/surfaces/mcp_tools.py
tests/unit/business_signal/test_mcp_tools.py
```

## Archivo a tocar

```text
cortex/mcp/server.py — importar y registrar tools
```

## Tools

### `cortex_business_signals`

Devuelve senales activas compactas para el agente.

Input: `project_root` (opcional).
Output: Lista de senales con title, type, confidence, score, recommended_actions. Sin evidencia completa para mantener tokens bajos.

Uso sugerido: al iniciar tarea compleja, antes de planificar feature, antes de cerrar fase.

### `cortex_explain_business_signal`

Input: `signal_id`.
Output: Evidencia completa, score_breakdown, documentos recomendados.

### `cortex_record_signal_feedback`

Input: `signal_id`, `feedback` (useful|not_useful|false_positive|acted_on|ignored), `note` (opcional).
Output: Confirmacion.

## Checklist

- [ ] Tools aparecen en `list_tools`.
- [ ] `cortex_business_signals` devuelve texto compacto.
- [ ] `cortex_explain_business_signal` devuelve evidencia.
- [ ] `cortex_record_signal_feedback` registra feedback.
- [ ] Errores se manejan sin romper el MCP server.
- [ ] Tools existentes siguen funcionando (regresion).

## Gate de salida

- `pytest tests/unit/business_signal/test_mcp_tools.py` pasa.
- MCP server lista todas las tools anteriores + las nuevas.

---
