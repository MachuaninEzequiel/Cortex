# Plan de Acción: EPIC 3 - Promotion Pipeline de Conocimiento

## Documento

- Fecha: 2026-04-29
- Proyecto: `Cortex`
- Epic objetivo: `E3 - Promotion pipeline`
- Estado: **Planificación + Implementación V1 completada**
- Dependencia: `EPIC 2 completada`

---

## 1. Resumen Ejecutivo

Con el retrieval multi-nivel (EPIC 2) ya operativo, Cortex puede consultar tanto la memoria local del proyecto como la memoria corporativa. El siguiente paso lógico es habilitar el flujo inverso: permitir que el conocimiento valioso generado localmente sea **promovido** a la memoria institucional de forma gobernada, auditable y segura.

---

## 2. Objetivo de la EPIC 3

Formalizar el proceso de promoción de conocimiento (Vault Local -> Vault Enterprise), definiendo:
- Qué documentos son candidatos a promoción.
- Cómo se gestionan los estados de revisión (`draft`, `candidate`, `promoted`).
- Cómo se ejecuta la promoción física (copia/mirror) manteniendo la trazabilidad.

---

## 3. Definition of Done (Propuesto)

- [x] Existe un pipeline oficial de promoción implementado en `cortex/enterprise/`.
- [x] Se pueden identificar documentos promovibles mediante reglas configurables.
- [x] El comando `cortex promote-knowledge` permite previsualizar y ejecutar la promoción.
- [x] Se mantiene la trazabilidad (metadata de origen, fecha, autor) en el vault destino.
- [x] Soporte para promoción manual y asistida (CI-driven): outputs JSON + exit codes aptos CI (EPIC 4 profundiza gobernanza).
- [x] Tests que cubren el ciclo de vida de promoción.

---

## 4. Historias Técnicas Iniciales

### E3-S1: Definir modelo de datos de promoción
Diseñar los estados y la metadata necesaria para trazar un documento desde que es detectado como candidato hasta que es institucionalizado.

### E3-S2: Implementar motor de reglas de promovibilidad
Crear lógica que filtre documentos del vault local basados en extensión, ubicación, tags o metadatos específicos definidos en `org.yaml`.

### E3-S3: Comandos CLI de gestión
Implementar comandos para listar candidatos, revisar estado y ejecutar el push hacia el vault enterprise.

---

## 5. Entregables implementados (V1)

- Modelos: `cortex/enterprise/promotion_models.py`
- Servicio: `cortex/enterprise/knowledge_promotion.py`
- CLI:
  - `cortex review-knowledge`
  - `cortex promote-knowledge` (dry-run default; `--apply` para ejecutar)
  - `cortex sync-enterprise-vault` (validate + index de `vault-enterprise/`)
- Persistencia audit:
  - `vault-enterprise/.cortex/promotion/records.jsonl` (append-only)
- Tests:
  - `tests/unit/enterprise/test_promotion_rules.py`
  - `tests/unit/enterprise/test_promotion_records.py`
  - `tests/integration/enterprise/test_promotion_e2e.py`

---

## 6. Próximos Pasos Inmediatos

1. Crear `cortex/enterprise/promotion_models.py`.
2. Crear `docs/enterprise/AVANCE-EPIC-3-IMPLEMENTACION.md`.
3. Iniciar el relevamiento de `doc_validator.py` para integrar checks de promoción.
