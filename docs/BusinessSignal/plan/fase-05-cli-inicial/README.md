# Fase 5 - CLI Inicial

**Fuente:** `docs/BusinessSignal/plan/README.md`
**Estado:** Pendiente de ejecucion

## Introduccion

Expone senales al usuario via CLI sin alterar comandos existentes. Al terminar, documentar en `REALIZACION.md`.

## Reglas para agentes

- No toques el CLI existente salvo `app.add_typer(signals_app, name="signals")`.
- No toques el MCP server en esta fase.
- Todos los comandos deben aceptar `--project-root`.
- Salida `--json` debe ser estable para CI.

## Archivos a crear

```text
cortex/business_signal/cli.py
cortex/business_signal/surfaces/__init__.py
cortex/business_signal/surfaces/cli_presenter.py
tests/unit/business_signal/test_cli.py
```

## Archivo a tocar

```text
cortex/cli/main.py — solo agregar: app.add_typer(signals_app, name="signals")
```

## Comandos

### `cortex signals`

Lista senales activas del proyecto actual.

Salida humana:
```text
Business Signals for project: client-mobile-redesign

1. Historical Project Analogy [high] ⚠️ advisory
   Similar to: client-portal-v1
   Score: 0.78
   Evidence: 14/20 recent work items
   Action: Review ADR-004 and incident-2025-09-auth-refresh

No more active signals.
```

### `cortex signals --json`

Salida JSON array de BusinessSignal serializado.

### `cortex signals explain <signal-id>`

Muestra evidencia detallada: metricas, documentos, hits, score breakdown, acciones.

### `cortex signals dismiss <signal-id> --reason "..."`

Marca senal como dismissed con razon obligatoria.

### `cortex signals feedback <signal-id> --useful|--not-useful|--false-positive`

Registra feedback.

### `cortex signals doctor`

Valida estado de BusinessSignal:
- Config cargada o defaults.
- Telemetria habilitada.
- Cantidad de eventos capturados.
- Detectores cargados.
- Senales activas.
- Warnings de retencion.

## Checklist

- [ ] `cortex signals` lista senales activas.
- [ ] `cortex signals --json` devuelve JSON estable.
- [ ] `cortex signals explain <id>` muestra evidencia.
- [ ] `cortex signals dismiss <id> --reason` marca dismissed.
- [ ] `cortex signals feedback <id> --useful` registra feedback.
- [ ] `cortex signals doctor` valida estado sin modificar archivos.
- [ ] Todos aceptan `--project-root`.
- [ ] El CLI viejo sigue pasando sus tests.
- [ ] Si no hay senales, muestra mensaje claro.
- [ ] Si BusinessSignal no esta habilitado, muestra mensaje instructivo.

## Gate de salida

- `pytest tests/unit/business_signal/test_cli.py` pasa.
- `pytest tests/unit/cli/test_main.py` pasa (regresion).
- `cortex signals --json` funciona en repo sin eventos.

---
