---
title: Layout del Workspace y Configuración
description: Descubrimiento de layouts, estructura de .cortex/ y jerarquía de configuración con Serde.
---

Cortex implementa un sistema flexible de **descubrimiento de espacios de trabajo** en el crate [`cortex-workspace`](file:///home/chucho/Cortex/rust/crates/cortex-workspace) y deserialización tipada estricta con Serde en [`cortex-config`](file:///home/chucho/Cortex/rust/crates/cortex-config).

---

## Estructura del Directorio `.cortex`

Cuando Cortex se inicializa en un repositorio, genera el siguiente árbol de configuración y estado:

```text
mi-proyecto/
├── .cortex/
│   ├── config.yaml          ← Configuración principal del proyecto
│   ├── workspace.yaml       ← Definición del espacio de trabajo y roots
│   ├── org.yaml             ← Políticas de gobernanza y enterprise (opcional)
│   ├── memory/              ← Almacén episódico JSONL
│   │   ├── events.jsonl
│   │   └── vectors.bin      ← Caché de vectores binario (schema v2)
│   ├── sessions/            ← Registros de sesiones activas e históricas
│   └── vault/               ← Memoria semántica (Markdown)
└── src/                     ← Código fuente de su proyecto
```

---

## Archivos de Configuración

### 1. `.cortex/config.yaml`
Controla el comportamiento de los motores de búsqueda, inferencia y proveedores de modelos:

```yaml
episodic:
  persist_dir: "memory"
  collection_name: "cortex_episodic"
  embedding_model: "all-MiniLM-L6-v2"
  embedding_backend: onnx
  namespace_mode: project # project | branch | custom
  namespace_value: ""

semantic:
  vault_path: "vault"

retrieval:
  top_k: 5
  episodic_weight: 1.0
  semantic_weight: 1.0

llm:
  provider: none # none | openai | anthropic | ollama
  model: ""

integrations:
  jira:
    enabled: false
    base_url: "https://mi-empresa.atlassian.net"
    email_env: "JIRA_EMAIL"
    token_env: "JIRA_API_TOKEN"

documenter:
  default_mode: auto # auto | interactive
```

### 2. `.cortex/workspace.yaml`
Define la raíz del repositorio y las rutas relativas para el vault y la memoria:

```yaml
version: "2.0"
repo_root: "."
vault_dir: ".cortex/vault"
memory_dir: ".cortex/memory"
sessions_dir: ".cortex/sessions"
```

### 3. `.cortex/org.yaml` (Enterprise)
Configura las políticas organizacionales de equipo, niveles de auditoría y reglas de promoción de conocimiento:

```yaml
version: "1.0"
org_id: "acme-corp"
project_name: "cortex-core"
preset: "small-company" # solo-dev | small-company | enterprise
governance:
  review_required: true
  auto_promote_specs: false
  retention_days: 90
```

---

## Descubrimiento Automático del Layout

Al invocar cualquier comando de la CLI o herramienta MCP, [`cortex-workspace::WorkspaceLayout::discover`](file:///home/chucho/Cortex/rust/crates/cortex-workspace) busca recursivamente hacia arriba desde el directorio de trabajo actual (`cwd`) hasta encontrar el archivo `.cortex/workspace.yaml` o `.cortex/config.yaml`, garantizando que los comandos puedan ejecutarse desde cualquier subdirectorio dentro del proyecto sin perder el contexto.
