---
name: obsidian-markdown
description: Sintaxis avanzada de Obsidian (Wikilinks, Embeds, Callouts, Properties).
---
# Obsidian Flavored Markdown
Usa esta guía para asegurar compatibilidad total con el Vault de Obsidian.

## Sintaxis Core
- **Wikilinks**: `[[Nombre de Nota]]` o `[[Nombre#Sección|Texto]]`.
- **Embeds**: `![[Nombre de Nota]]` o `![[imagen.png|300]]`.
- **Callouts**: 
  > [!type] Título
  > Contenido
  (Tipos: note, tip, warning, info, example, bug, success, failure, danger).

## Propiedades (YAML)
Siempre incluye frontmatter en nuevas notas:
```yaml
---
title: Nombre
tags: [tag1, tag2]
status: active
---
```
