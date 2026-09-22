# cortex/action_engine/store.py

## Qué tiene adentro

- **Ruta de código:** `cortex/action_engine/store.py` (135 líneas).
- **Módulo Python:** `cortex.action_engine.store`.
- **Docstring del módulo:** Persistencia del ActionEngine (Obra 05 Fase B).
- **Clases definidas:**
  - `ActionLog`
    - JSONL append-only: {id, ts, trigger, dry_run, ok, message, duration_ms}.
    - Métodos públicos/especiales: `__init__`, `path`, `append`, `load`
    - Métodos internos: `_rotar_si_corresponde`
  - `PreferencesStore`
    - Preferencias por acción en YAML::
    - Métodos públicos/especiales: `__init__`, `path`, `registrar`, `nunca_mas`, `penalizacion_skips`
    - Métodos internos: `_load`, `_guardar`
- **Constantes / símbolos de módulo:** `_LOG_ROTADO`

## Para qué sirve

Persistencia del ActionEngine (Obra 05 Fase B).

- ``ActionLog``: registro append-only de ejecuciones en
  ``.cortex/action_log.jsonl`` — insumo del paso APRENDER.
- ``PreferencesStore``: supresiones y contadores aceptar/saltar/nunca por
  id en ``.cortex/actions.yaml`` — el motor aprende preferencias negativas
  y positivas (plan §3.5/§3.6).

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `json`, `logging`, `yaml`, `__future__`, `pathlib`

### Envía a

- `cortex.action_engine`
- `cortex.action_engine.learning`
- `cortex.action_engine.metrics`
- `cortex.action_engine.runner`
- `cortex.action_engine.scheduler`
- `cortex.tui.core`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 135.
Docstrings de símbolos públicos:
- `PreferencesStore.registrar`: Registra 'accept' | 'skip' | 'never' para una acción.
- `PreferencesStore.penalizacion_skips`: Score multiplier v0: -15% por skip consecutivo (mínimo 0.4).

---
Fuente: código de `cortex/action_engine/store.py` (AST + grafo de imports internos). No se usó documentación previa.
