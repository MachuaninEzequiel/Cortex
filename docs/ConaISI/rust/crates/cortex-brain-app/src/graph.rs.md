# rust/crates/cortex-brain-app/src/graph.rs

## Qué tiene adentro

Extractores locales (sin servidor webgraph):

- `GraphNode` / `GraphEdge` / `ProjectGraphPayload`
- `extract_project_graph`: nodo raíz; crates en `rust/crates`; apps en `apps/`; specs (`vault/specs`, `docs/specs`, `specs`); ADRs (`vault/adrs`, `docs/adrs`, nombres ADR/SESSION/PLAN)
- `SessionStatusPayload` + `inspect_session_status` lee `.cortex/sessions/`
- `DoctorCheck` / `DoctorReportPayload` + `inspect_doctor_health`
- `NodeHighlightEvent`

## Para qué sirve

Modales WebGraph y Doctor de la UI Tauri, y fallback de `execute_cortex_tool` (session/doctor).

## Relaciones

### Recibe de

- árbol del `project_root` en disco

### Envía a

- commands `get_project_graph`, `get_session_status`, `run_doctor_inspect`

### Notas de implementación observadas en el código

Este grafo es un scan de carpetas, distinto del `cortex-webgraph-server` (wikilinks + embeddings).
