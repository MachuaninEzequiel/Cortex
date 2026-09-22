# rust/crates/cortex-brain-app/tests/eval_governance_model.rs

## Qué tiene adentro

Harness de Evaluación Empírica de Gobernanza y Tools (Obra 20 / Línea A).  Evalúa 20 escenarios de intención en lenguaje natural para verificar que el protocolo de herramientas de Cortex Brain (sesiones, auditoría, grafo, memoria) se despacha y procesa correctamente con cero alucinaciones.
Archivo de 317 líneas.
Tests en el mismo archivo: `eval_01_catalogo_contiene_todas_las_tools_de_gobernanza`, `eval_02_session_status_en_proyecto_sin_sesion`, `eval_03_session_status_en_proyecto_con_sesion_activa`, `eval_04_doctor_inspect_detecta_salud_y_anomalias`, `eval_05_webgraph_query_filtra_nodos_por_termino`, `eval_06_extractor_de_grafo_detecta_modulos_y_crates`, `eval_07_engine_ejecuta_scripted_con_session_status`, `eval_08_engine_ejecuta_scripted_con_doctor_inspect`, `eval_09_engine_intercepta_safe_action_session_checkpoint`, `eval_10_engine_intercepta_safe_action_session_finish`, `eval_11_engine_responde_conversacion_sin_tools`, `eval_12_vault_stats_cuenta_notas_correctamente`, `eval_13_webgraph_query_vacio_retorna_primeros_nodos`, `eval_14_tool_inexistente_se_reporta_sin_panico`, `eval_15_graph_payload_serializa_json_limpio`

## Para qué sirve

Harness de Evaluación Empírica de Gobernanza y Tools (Obra 20 / Línea A).  Evalúa 20 escenarios de intención en lenguaje natural para verificar que el protocolo de herramientas de Cortex Brain (sesiones, auditoría, grafo, memoria) se despacha y procesa correctamente con cero alucinaciones.

## Relaciones

### Recibe de

- `use cortex_brain_app::chat::{build_all_tools, dispatch_tool, BrainEngine, ToolCall}`
- `use cortex_brain_app::graph::{extract_project_graph, inspect_doctor_health, inspect_session_status}`
- Contexto de crate `cortex-brain-app`: cortex-brain, cortex-enterprise, cortex-workspace, tauri, apps/brain-ui dist

### Envía a

- Crate `cortex-brain-app` envía hacia: IPC unix socket, eventos Tauri, webview React

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-brain-app/tests/eval_governance_model.rs`.
