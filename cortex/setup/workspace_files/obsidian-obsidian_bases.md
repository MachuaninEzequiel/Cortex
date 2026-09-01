---
name: obsidian-bases
description: Creación y edición de vistas de base de datos (.base).
---
# Obsidian Bases
Usa esta guía para crear trackers, tablas y vistas dinámicas.

## Estructura .base (YAML)
```yaml
filters: 'file.hasTag("task") && status != "done"'
views:
  - type: table
    name: "Dashboard"
    order: [file.name, status, priority]
    summaries: { priority: Average }
```

## Operadores y Funciones
- **Filtros**: `==`, `!=`, `>`, `<`, `&&`, `||`, `!`.
- **Fechas**: `today()`, `now()`, `date("YYYY-MM-DD")`.
- **Duraciones**: `(due - today()).days`.
- **Propiedades**: `file.name`, `file.mtime`, `file.size`, `file.tags`.
