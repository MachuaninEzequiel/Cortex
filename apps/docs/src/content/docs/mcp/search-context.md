---
title: Herramientas de Búsqueda y Contexto MCP
description: cortex_search, cortex_search_vector y cortex_context para recuperación de memoria en agentes.
---

Este conjunto de herramientas permite a los agentes recuperar información tanto del Vault semántico como de la memoria episódica.

---

## 1. `cortex_search`

Búsqueda rápida instantánea mediante coincidencia de palabras clave y filtros estructurales. No requiere carga de modelos ONNX y tiene tiempo de respuesta inferior a 5ms.

### Esquema de Entrada:
```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "Términos de búsqueda."
    },
    "limit": {
      "type": "integer",
      "default": 5
    },
    "doc_type": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Filtrar por DocType slug (adr, runbook, spec, etc.)."
    },
    "scope": {
      "type": "string",
      "enum": ["local", "enterprise", "all"],
      "default": "all"
    },
    "status": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Filtrar por status (draft, accepted, stable, etc.)."
    },
    "tags": {
      "type": "array",
      "items": { "type": "string" }
    },
    "max_age_days": {
      "type": "integer"
    },
    "strict": {
      "type": "boolean",
      "default": false
    }
  },
  "required": ["query"]
}
```

---

## 2. `cortex_search_vector`

Búsqueda semántica conceptual profunda. Carga el modelo de embeddings local para encontrar documentos conceptualmente afines aunque no compartan los mismos términos textuales.

### Esquema de Entrada:
```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "Consulta semántica conceptual."
    },
    "limit": {
      "type": "integer",
      "default": 5
    }
  },
  "required": ["query"]
}
```

---

## 3. `cortex_context`

Recupera un bloque de contexto pre-formateado y optimizado para ser inyectado directamente en el prompt del LLM, integrando notas del Vault y eventos relevantes de la sesión.

### Esquema de Entrada:
```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "Tema o tarea sobre la cual se necesita contexto."
    },
    "limit": {
      "type": "integer",
      "default": 5
    }
  },
  "required": ["query"]
}
```
