# rust/crates/cortex-actions/src/store.rs

## Qué tiene adentro

Puerto de `cortex/action_engine/store.py` (Obra 05 Fase B).  - `ActionLog`: registro append-only de ejecuciones en `.cortex/action_log.jsonl` — insumo del paso APRENDER. - `PreferencesStore`: supresiones y contadores aceptar/saltar/nunca por id en `.cortex/actions.yaml` — el motor aprende preferencias negativas y positivas (plan §3.5/§3.6).  FORMATO-COMPATIBLE byte-a-byte con los archivos que escribe Python: - action_log.jsonl: una línea JSON por ejecución (claves en orden de inserción del dict Python), `\n` final por entrada. - actions.yaml: `yaml.safe_dump({"acciones": …}, sort_keys=False,
Archivo de 428 líneas.
Símbolos públicos observados:
- `pub struct OrderedEntry`
- `pub struct ActionLog`
- `pub struct PreferencesStore`
- `pub struct PrefsEntrada`
Tests en el mismo archivo: `action_log_append_y_load_ordenado`, `preferences_skip_baja_accept_compensa_never_suprime`, `yaml_formato_compatible_python`, `yaml_roto_se_ignora`, `rotacion_de_log`

## Para qué sirve

Puerto de `cortex/action_engine/store.py` (Obra 05 Fase B).  - `ActionLog`: registro append-only de ejecuciones en `.cortex/action_log.jsonl` — insumo del paso APRENDER. - `PreferencesStore`: supresiones y contadores aceptar/saltar/nunca por id en `.cortex/actions.yaml` — el motor aprende preferencias negativas y positivas (plan §3.5/§3.6).  FORMATO-COMPATIBLE byte-a-byte con los archivos que escribe Python: - action_log.jsonl: una línea JSON por ejecución (claves en orden de inserción del dict Python), `\n` final por entrada. - actions.yaml: `yaml.safe_dump({"acciones": …}, sort_keys=False,

## Relaciones

### Recibe de

- `use crate::models::ahora_iso`
- Contexto de crate `cortex-actions`: cortex-app, cortex-enterprise, cortex-setup

### Envía a

- Crate `cortex-actions` envía hacia: cortex-cli next, cortex-companion, cortex-tui, .cortex/action_log.jsonl

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-actions/src/store.rs`.
