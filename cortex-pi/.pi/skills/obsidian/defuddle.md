---
name: defuddle
description: Extracción de Markdown limpio desde URLs usando Defuddle CLI.
---
# Defuddle CLI
Optimiza la lectura de documentación externa eliminando ruido (ads, nav, footer).

## Comandos
- **Parse básico**: `defuddle parse --md <URL>`
- **Guardar**: `defuddle parse --md <URL> -o doc.md`
- **Metadatos**: `defuddle parse -p title <URL>`

Usa esto siempre que el usuario provea una URL de un sitio web estándar para evitar saturar el contexto con HTML.
