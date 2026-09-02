---
title: Herramientas MCP para Documentos, Specs y Diseños
description: cortex_create_spec, cortex_emit_proposal, cortex_write_doc y write_design_note_canonical.
---

Estas herramientas permiten a los agentes redactar y persistir documentación técnica canónica en el Vault sin inventar rutas ni romper los esquemas tipados.

---

## 1. `cortex_write_doc`

Escritor canónico genérico para cualquiera de los **11 DocTypes** soportados.

### Parámetros:
* **`doc_type`** (enum, requerido):
  `session`, `handoff`, `adr`, `decision`, `incident`, `postmortem`, `runbook`, `architecture`, `changelog`, `glossary`, `hu`.
* **`payload`** (objeto, requerido): Campos específicos para el `doc_type` elegido:
  * `adr` / `decision`: `title`, `context`, `decision`.
  * `incident`: `title`, `short_description`, `severity`.
  * `postmortem`: `title`, `incident_path`, `incident_number`, `root_cause`.
  * `runbook`: `title`, `runbook_kind`, `procedure`.
  * `architecture`: `title`, `summary`.
  * `changelog`: `title`, `version`.
  * `glossary`: `title`, `term`, `definition`.
  * `hu`: `title`, `external_id`, `source`.
* **`vault_scope`** (string, default `"local"`): `local` o `enterprise`.
* **`overwrite`** (bool, default `false`).

---

## 2. `cortex_create_spec`

Crea una especificación técnica formal bajo `vault/specs/`.

### Parámetros:
* `title` (string, requerido): Título de la spec.
* `summary` (string, requerido): Resumen del requerimiento.
* `scope` (string, requerido): Alcance y módulos afectados.
* `acceptance_criteria` (array de strings, requerido): Criterios de aceptación verificables.
* `technical_approach` (string, opcional): Enfoque técnico propuesto.
* `risks` (array de strings, opcional): Riesgos y mitigaciones.

---

## 3. `write_design_note_canonical`

Persiste un documento de diseño técnico de arquitectura bajo `vault/designs/`.

### Parámetros:
* `title` (string, requerido): Título del diseño.
* `session_id` (string, requerido): Sesión vinculada.
* `spec_path` (string, requerido): Ruta a la spec base.
* `architecture_decision` (string, requerido): Decisión arquitectónica adoptada.
* `data_model_changes` (array de strings): Cambios en el modelo de datos.
* `api_contracts` (array de strings): Contratos y endpoints nuevos o modificados.
* `test_plan` (array de strings): Plan de pruebas automatizadas.
* `status` (string, default `"draft"`): `draft`, `approved`, `superseded`.
