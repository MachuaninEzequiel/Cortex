---
title: Gobernanza y Configuración Organizacional (org.yaml)
description: Modelos de gobernanza empresarial, presets de organización y retención de memoria en Cortex.
---

El módulo **Enterprise y Gobernanza** de Cortex ([`cortex-enterprise`](file:///home/chucho/Cortex/rust/crates/cortex-enterprise)) permite a equipos de ingeniería y organizaciones estructurar el flujo de aprobación del conocimiento generado por agentes de IA.

---

## Archivo `.cortex/org.yaml`

El archivo `.cortex/org.yaml` define las políticas organizacionales que rigen el repositorio:

```yaml
version: "1.0"
org_id: "acme-corporation"
project_name: "cortex-core"
preset: "small-company" # solo-dev | small-company | enterprise

governance:
  review_required: true        # Requiere revisión humana antes de promover notas
  auto_promote_specs: false    # Si las specs se promueven automáticamente al cerrarse
  retention_days: 180          # Días de retención para memoria episódica
  allowed_reviewers:
    - "lead-architect"
    - "tech-lead"

vault:
  enterprise_vault_path: "/shared/vault/acme-org"
  sync_on_startup: true
```

---

## Presets de Gobernanza

1. **`solo-dev`:**
   * Cero fricción.
   * Auto-promoción de notas aceptadas.
   * Sin cola de revisión obligatoria.
2. **`small-company`:**
   * Recomendado para equipos de 2 a 20 desarrolladores.
   * Las decisiones arquitectónicas (ADRs) y cambios de contratos entran en cola de revisión (`status: draft`).
3. **`enterprise`:**
   * Control estricto.
   * Audit trail obligatorio en cada cambio de estado.
   * Firma de revisor requerida en la cola de promoción.
   * Separación explícita entre Vault local de proyecto y Vault empresarial compartido.

---

## Verificación con `cortex org-config`

Para inspeccionar la configuración resuelta en el entorno actual:

```bash
cortex org-config
cortex org-config --json
```
