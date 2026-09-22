# rust/crates/cortex-brain/tests/tool_protocol.rs

## Qué tiene adentro

Protocolo TOOL del brain — backend falso scriptado (CI sin modelo).  Cubre el contrato de 6a5479f (auto-despacho con confirmación) pero testeable en librería: extracción de "TOOL: <nombre> <args>", separación de la respuesta, gate de confirmación inyectable y despacho real vía CLI. `ScriptedBackend` es el backend falso que CI usa para ejercitar el loop completo sin GGUF.
Archivo de 163 líneas.
Tests en el mismo archivo: `extrae_tool_simple_sin_args`, `extrae_tool_con_args`, `extrae_primera_linea_tool_si_hay_varias`, `sin_linea_tool_devuelve_none`, `tool_con_espacios_interiores_se_normaliza`, `confirmacion_acepta_variantes_si`, `confirmacion_rechaza_default_negativo`, `scripted_backend_entrega_respuestas_en_orden_y_luego_falla`, `flujo_completo_sugiere_confirma_y_despacha`, `flujo_completo_rechaza_y_no_despacha`, `flujo_tool_inexistente_nunca_despacha`, `respuesta_con_texto_y_tool_muestra_texto_sin_la_linea_tool`

## Para qué sirve

Protocolo TOOL del brain — backend falso scriptado (CI sin modelo).  Cubre el contrato de 6a5479f (auto-despacho con confirmación) pero testeable en librería: extracción de "TOOL: <nombre> <args>", separación de la respuesta, gate de confirmación inyectable y despacho real vía CLI. `ScriptedBackend` es el backend falso que CI usa para ejercitar el loop completo sin GGUF.

## Relaciones

### Recibe de

- `use cortex_brain::chat::{`
- `use cortex_brain::tools::build_tools`
- Contexto de crate `cortex-brain`: cortex-branding, ureq, llama-cpp-2 (feature), CLI cortex via Command

### Envía a

- Crate `cortex-brain` envía hacia: stdout, cortex-brain-app, cortex-companion

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-brain/tests/tool_protocol.rs`.
