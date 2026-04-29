# Avance EPIC 6: Observabilidad y Reporting

## Documento

- Fecha inicio: 2026-04-29
- Estado: Implementado (validado localmente)
- Epic: `E6 - Observabilidad y reporting`
- Base: `EPIC 1-5` operativas; E6 consolida visibilidad sobre el motor de productización.

---

## Bitácora de implementación

### 2026-04-29 - Implementación E6-S1 (Reporte de memoria unificado)

- Se creó el servicio central `cortex/enterprise/reporting.py`.
- Implementación de `EnterpriseReportingService` para consolidar métricas de:
  - Volumen de archivos markdown por fuente (local vs enterprise).
  - Estado de validación (errores/warnings) extraídos de `doctor`.
  - Notas de diagnóstico rápido.
- Integración en CLI: Nuevo comando `cortex memory-report` con soporte para:
  - Scopes: `local`, `enterprise`, `all`.
  - Salida legible para humanos con formato estructurado.

### 2026-04-29 - Implementación E6-S2 (Visibilidad de Promotion Pipeline)

- Extensión de `EnterpriseReportingService` para consumir estados de `KnowledgePromotionService`.
- El reporte de memoria ahora incluye una sección de "Promotion" con:
  - Conteo de candidatos descubiertos y listos para promocionar.
  - Trazabilidad de los últimos 10 eventos (promociones, rechazos) con actor y timestamp.
  - Advertencias sobre configuración de registros (`records.jsonl`).

### 2026-04-29 - Implementación E6-S3 (Enriquecimiento y Filtrado en WebGraph)

- Se extendió `cortex/webgraph/service.py` con `_append_enterprise_nodes`.
- WebGraph ahora inyecta nodos institucionales (`enterprise_org`, `enterprise_project`, `enterprise_vault`) y relaciones de pertenencia.
- Se implementó `_filter_snapshot_by_scope` para permitir visualizaciones puramente locales o corporativas.
- Soporte para filtrado por scope integrado en `FederatedWebGraphService` para despliegues multi-proyecto.

### 2026-04-29 - Salida JSON y Automatización

- Se habilitó el flag `--json` en `cortex memory-report`.
- El esquema JSON es estable (basado en Pydantic) y permite la integración con pipelines de observabilidad externos o dashboards.
- Integración de resumen de salud de `doctor` directamente en el payload del reporte.

---

## Checklist EPIC 6

- [x] Crear servicio `cortex/enterprise/reporting.py`
- [x] Implementar comando `cortex memory-report` (CLI)
- [x] Implementar reporte de trazabilidad de promociones
- [x] Enriquecer WebGraph con nodos y relaciones enterprise
- [x] Implementar filtrado por `scope` en WebGraph
- [x] Soportar salida JSON estable para automatización
- [x] Agregar cobertura de tests unitarios para reporting

---

## Notas

### Comandos útiles

```bash
# Reporte completo de salud y promociones
cortex memory-report

# Reporte enfocado solo en el nivel corporativo
cortex memory-report --scope enterprise

# Exportar reporte a JSON para auditoría
cortex memory-report --json > report.json

# Generar WebGraph filtrado por scope local
cortex webgraph export --scope local
```

Este documento registra la finalización de la EPIC 6, dotando a Cortex de la visibilidad necesaria para operar memorias corporativas a escala de manera transparente y auditable.
