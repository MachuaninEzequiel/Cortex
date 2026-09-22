# cortex/action_engine/metrics.py

## Qué tiene adentro

- **Ruta de código:** `cortex/action_engine/metrics.py` (62 líneas).
- **Módulo Python:** `cortex.action_engine.metrics`.
- **Docstring del módulo:** Métrica de éxito del dueño (Obra 05 Fase E, plan §3.6).
- **Clases definidas:**
  - `MetricasMotor`
- **Funciones de módulo:**
  - `calcular_metricas(log)`

## Para qué sirve

Métrica de éxito del dueño (Obra 05 Fase E, plan §3.6).

Definición registrada para la medición de adopción:

- ``pct_motor`` = ejecuciones decididas por el motor (auto-ok, ``via=auto``)
  sobre el total de ejecuciones reales (no dry-run).
- Target declarado por el dueño: abrir el menú de acciones <1 vez por día
  de trabajo activo ⇒ proxy medible hoy: ``pct_motor`` alto con volumen
  estable de ejecuciones y ``dias_con_interaccion`` bajo.

La ventana de observación se abre con la adopción; el cierre se registra
en ESTADO-ACTUAL.md tras ≥2 semanas de uso real.

## Relaciones

### Recibe de

- `cortex.action_engine.store` (ActionLog)
- Dependencias externas/stdlib: `__future__`, `dataclasses`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 62.

---
Fuente: código de `cortex/action_engine/metrics.py` (AST + grafo de imports internos). No se usó documentación previa.
