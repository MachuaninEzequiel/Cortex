# cortex/action_engine/learning.py

## Qué tiene adentro

- **Ruta de código:** `cortex/action_engine/learning.py` (27 líneas).
- **Módulo Python:** `cortex.action_engine.learning`.
- **Docstring del módulo:** Paso APRENDER v0 del ActionEngine (plan §3.6).
- **Clases definidas:**
  - `Learner`
    - Métodos públicos/especiales: `__init__`, `registrar_decision`, `suprimida`, `multiplicador`

## Para qué sirve

Paso APRENDER v0 del ActionEngine (plan §3.6).

Bucle mínimo: cada decisión (accept/skip/never) se persiste en
``.cortex/actions.yaml`` y ajusta el score futuro vía
``PreferencesStore.penalizacion_skips``. El registro crudo de ejecuciones
vive en action_log.jsonl; el agregado mensual llega en fases posteriores.

## Relaciones

### Recibe de

- `cortex.action_engine.store` (PreferencesStore)
- Dependencias externas/stdlib: `__future__`

### Envía a

- `cortex.tui.core`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 27.
Docstrings de símbolos públicos:
- `Learner.registrar_decision`: accept | skip | never — persiste y ajusta prioridad futura.

---
Fuente: código de `cortex/action_engine/learning.py` (AST + grafo de imports internos). No se usó documentación previa.
