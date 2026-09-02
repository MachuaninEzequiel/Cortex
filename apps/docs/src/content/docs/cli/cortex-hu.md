---
title: cortex hu (Historias de Usuario y Tracking)
description: Importación, seguimiento y sincronización de Historias de Usuario (HU) y tickets de Jira en Cortex.
---

El comando `cortex hu` gestiona la importación y trazabilidad de **Historias de Usuario (HU)** y tickets de desarrollo dentro del Vault de Cortex.

---

## Subcomandos

```text
Usage: cortex hu <COMMAND>

Commands:
  import  Importa una historia de usuario desde Jira o archivo local
  list    Lista todas las historias de usuario registradas
  show    Muestra los detalles y criterios de aceptación de una HU
  sync    Sincroniza el estado de las historias de usuario con el proveedor externo
```

---

## Detalle de Subcomandos

### 1. `cortex hu import <ITEM_ID>`
Importa una historia de usuario y la transforma en una nota estructurada dentro de `.cortex/vault/hu/`.

```bash
cortex hu import PROJ-123
```

Si la integración con Jira está configurada en `.cortex/config.yaml`, Cortex consulta el proveedor, convierte el contenido estructurado (ADF / Atlassian Document Format) a Markdown estándar y extrae:
* Título y descripción.
* Criterios de aceptación.
* Estimación y épica asociada.
* Identificador externo y enlaces.

---

### 2. `cortex hu list`
Lista todas las historias de usuario presentes en el Vault con su estado actual (`todo`, `in-progress`, `done`, `blocked`).

```bash
cortex hu list
```

---

### 3. `cortex hu show <ITEM_ID>`
Muestra el desglose completo de una historia de usuario específica:

```bash
cortex hu show PROJ-123
```

---

## Configuración de Jira en `config.yaml`

Para habilitar la sincronización directa con Atlassian Jira:

```yaml
integrations:
  jira:
    enabled: true
    base_url: "https://mi-empresa.atlassian.net"
    email_env: "JIRA_EMAIL"
    token_env: "JIRA_API_TOKEN"
```

Asegúrese de definir las variables de entorno correspondientes antes de ejecutar la importación:

```bash
export JIRA_EMAIL="desarrollador@empresa.com"
export JIRA_API_TOKEN="tu_api_token_de_jira"
```
