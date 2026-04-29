# Avance EPIC 3: Promotion Pipeline de Conocimiento

## Documento

- Fecha inicio: 2026-04-29
- Estado: Iniciado (Planificación)
- Epic: `E3 - Promotion pipeline`
- Base: `EPIC 2 completada`

---

## Bitacora de implementacion

### 2026-04-29 - Inicialización

- Se creó la rama `feature/epic-3-knowledge-promotion` basada en el final de EPIC 2.
- Se redactó el documento inicial `docs/enterprise/PLAN-EPIC-3.md`.
- Estructura base lista para comenzar el desarrollo de modelos de promoción.

### 2026-04-29 - Implementación V1 (Promotion por copia + review obligatorio)

- Se implementó el modelo tipado de promoción en `cortex/enterprise/promotion_models.py`:
  - estados: `draft`, `candidate`, `reviewed`, `promoted`, `rejected`
  - candidatos con `origin_id`, `fingerprint`, destino y issues de validación
  - records append-only para auditabilidad
- Se implementó el servicio `cortex/enterprise/knowledge_promotion.py` con:
  - discovery de candidatos desde `vault/**/*.md` según `org.yaml` (`promotion.allowed_doc_types`)
  - default seguro: `sessions/` solo entra si el org lo habilita explícitamente
  - validación previa por `cortex/doc_validator.py` y bloqueo de review si hay errores
  - persistencia de records en `vault-enterprise/.cortex/promotion/records.jsonl`
  - promoción por **copia** con upsert de frontmatter de trazabilidad en el doc destino
  - idempotencia: skip si ya está promovido con el mismo fingerprint
- Se integró CLI en `cortex/cli/main.py`:
  - `cortex review-knowledge` (approve/reject) para pasar de `candidate` → `reviewed/rejected`
  - `cortex promote-knowledge` (dry-run default, `--apply`) para ejecutar promoción
  - `cortex sync-enterprise-vault` para validar + indexar `vault-enterprise/`
- Se agregaron tests nuevos:
  - unit: `tests/unit/enterprise/test_promotion_rules.py`, `test_promotion_records.py`
  - integration: `tests/integration/enterprise/test_promotion_e2e.py`
  - resultado local: `7 passed`

---

## Checklist EPIC 3

- [x] Rama de desarrollo creada
- [x] Plan de acción inicial redactado
- [x] Modelado de estados de promoción
- [x] Implementación de `knowledge_promotion.py`
- [x] Integración CLI
- [x] Pruebas de integración

---

## Notas
### Comandos útiles (V1)

```bash
# 1) Revisar un candidato (selector puede ser origin_id o ruta relativa del vault)
cortex review-knowledge "acme-api:specs/2026-01-01_auth.md" --approve --actor "alice"

# 2) Ver plan de promoción (no escribe nada)
cortex promote-knowledge --dry-run

# 3) Ejecutar promoción
cortex promote-knowledge --apply --actor "alice"

# 4) Validar e indexar el vault enterprise
cortex sync-enterprise-vault --strict-warnings
```

Este documento registra el progreso incremental de la promoción de conocimiento institucional.
