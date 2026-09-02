---
title: Revisión y Promoción de Conocimiento
description: cortex review-knowledge y cortex promote-knowledge para el control de calidad del Vault.
---

Cuando los agentes de IA generan notas de arquitectura, ADRs o especificaciones bajo un perfil empresarial, estos documentos ingresan en estado preliminar (`status: draft`). Cortex provee comandos para revisar, aprobar, rechazar y promover este conocimiento al Vault definitivo.

---

## `cortex review-knowledge`

Gestiona la cola de notas pendientes de revisión técnica.

```bash
cortex review-knowledge <COMMAND>
```

### Subcomandos:

#### 1. `cortex review-knowledge pending`
Lista las notas en borrador que aguardan revisión:
```bash
cortex review-knowledge pending
cortex review-knowledge pending --doc-type adr --json
```

#### 2. `cortex review-knowledge approve <PATH>`
Aprueba una nota, cambia su estado a `status: accepted` y registra la entrada correspondiente en el `audit_trail`:
```bash
cortex review-knowledge approve "vault/adrs/005-nueva-db.md" \
  --reviewer "ezequiel" \
  --rationale "Aprobado tras discusión de arquitectura del 2 de Septiembre"
```

#### 3. `cortex review-knowledge reject <PATH>`
Rechaza una propuesta técnica indicando el motivo:
```bash
cortex review-knowledge reject "vault/adrs/006-propuesta-invalida.md" \
  --reviewer "ezequiel" \
  --reason "Duplica la funcionalidad ya existente en el módulo de scoring"
```

---

## `cortex promote-knowledge`

Mueve o sincroniza las notas aprobadas desde el Vault local del proyecto hacia el **Vault empresarial compartido**:

```bash
cortex promote-knowledge [OPCIONES]
```

### Opciones:
* `--dry-run` (Predeterminado `true`): Muestra el plan de promoción sin mover archivos.
* `--apply`: Ejecuta la promoción de los documentos aprobados.
* `--actor <USER>`: Nombre del usuario o agente que ejecuta la promoción para el registro de auditoría.
* `--json`: Emite el plan y resultados en formato JSON.

### Ejemplo de Aplicación:
```bash
cortex promote-knowledge --apply --actor "ci-pipeline"
```
