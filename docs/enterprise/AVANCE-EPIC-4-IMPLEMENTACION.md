# Avance EPIC 4: Gobernanza y CI Enterprise

## Documento

- Fecha inicio: 2026-04-29
- Estado: Iniciado (Planificación)
- Epic: `E4 - Gobernanza y CI enterprise`
- Base: `EPIC 1` + `EPIC 2` + `EPIC 3` completadas

---

## Bitacora de implementacion

### 2026-04-29 - Inicialización

- Se creó la rama `feature/epic-4-governance-ci` basada en el final de EPIC 3.
- Se revisó el documento de planificación `docs/enterprise/PLAN-EPIC-4.md`.
- El objetivo inmediato es mapear el `ci_profile` (observability, advisory, enforced) a comportamientos reales en el pipeline.

### 2026-04-29 - E4-S2 (iniciado): Extensión de `doctor` con checks enterprise

- Se extendió `cortex/doctor.py` para que `doctor --scope enterprise|all` incluya checks adicionales cuando existe `vault-enterprise/`:
  - `enterprise_vault_validation_errors` / `enterprise_vault_validation_warnings`: validación markdown del enterprise vault.
  - `enterprise_promotion_allowed_doc_types`: fail si promotion está habilitado y `allowed_doc_types` queda vacío.
  - `enterprise_promotion_dir`: fail si no se puede crear/acceder a `vault-enterprise/.cortex/promotion/`.
  - `enterprise_promotion_records_presence`: warn si promotion está habilitado y aún no existen records (`records.jsonl`).
- Objetivo: que `doctor` exprese salud enterprise real, más allá de la existencia del vault.

### 2026-04-29 - E4-S3/E4-S4 (iniciado): Workflow enterprise + artefactos + enforcement

- Se creó el workflow oficial `.github/workflows/ci-enterprise-governance.yml` con:
  - resolución de `ci_profile` desde `.cortex/org.yaml` (fallback: `observability`)
  - ejecución de:
    - `cortex doctor --scope enterprise`
    - `cortex promote-knowledge --dry-run --json` → `.promotion-plan.json`
    - `cortex sync-enterprise-vault --json` → `.enterprise-doc-validation.json` + `.enterprise-sync.json`
  - upload de artefactos JSON para análisis humano/máquina
  - resumen humano en logs
  - enforcement final condicionado a `ci_profile=enforced`

### 2026-04-29 - E4-S3 (cerrado): Setup templates para workflow enterprise

- Se extendió `cortex/setup/templates.py` con `render_ci_enterprise_governance(...)` para generar el workflow enterprise desde `setup`.
- Se cableó el workflow en `cortex/setup/orchestrator.py` para que `cortex setup pipeline` y `cortex setup full` puedan crear:
  - `.github/workflows/ci-enterprise-governance.yml`
- Objetivo: evitar drift entre workflow real y el generado por templates.

### 2026-04-29 - Validación (tests)

- Tests agregados/actualizados:
  - `tests/unit/test_doctor_enterprise_governance.py`
  - `tests/unit/enterprise/test_enterprise_setup.py` (setup pipeline genera workflow enterprise)
- Suite ejecutada y passing:
  - `pytest tests/unit/test_doctor_enterprise_governance.py tests/unit/enterprise/test_enterprise_setup.py`
  - Resultado: `4 passed`

---

## Checklist EPIC 4

- [x] Rama de desarrollo creada
- [ ] Mapeo de perfiles de enforcement (E4-S1)
- [x] Extensión de `doctor` con checks enterprise (E4-S2)
- [x] Creación de workflows enterprise (E4-S3)
- [x] Implementación de reportes de estado CI (E4-S4)
- [x] Pruebas de render de templates y doctor

---

## Notas
Este epic transformará el pipeline de promoción en una operación gobernada y automatizable para entornos corporativos.
