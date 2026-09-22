# cortex/enterprise/reporting.py

## Qué tiene adentro

- **Ruta de código:** `cortex/enterprise/reporting.py` (219 líneas).
- **Módulo Python:** `cortex.enterprise.reporting`.
- **Clases definidas:**
  - `PromotionEventSummary` (BaseModel)
  - `PromotionReport` (BaseModel)
  - `MemorySourceReport` (BaseModel)
  - `MemoryReportPayload` (BaseModel)
  - `EnterpriseReportingService`
    - Métodos públicos/especiales: `__init__`, `from_project_root`, `build_memory_report`
    - Métodos internos: `_local_source`, `_enterprise_source`, `_promotion_report`
- **Funciones de módulo:**
  - `_utc_now()`
  - `_doctor_to_payload(report)`
  - `_extract_check_count(checks, name)`
  - `_count_markdown_files(root)`
  - `_summarize_latest_events(latest_by_origin)`

## Para qué sirve

Define PromotionEventSummary, PromotionReport, MemorySourceReport, MemoryReportPayload, EnterpriseReportingService. No hay docstring de módulo; el propósito se infiere de las clases y métodos listados.

## Relaciones

### Recibe de

- `cortex.doctor` (DoctorCheck, DoctorReport, run_doctor)
- `cortex.enterprise.config` (discover_enterprise_config_path, load_enterprise_config)
- `cortex.enterprise.knowledge_promotion` (KnowledgePromotionService)
- `cortex.workspace.layout` (WorkspaceLayout)
- Dependencias externas/stdlib: `__future__`, `datetime`, `pathlib`, `typing`, `pydantic`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 219.

---
Fuente: código de `cortex/enterprise/reporting.py` (AST + grafo de imports internos). No se usó documentación previa.
