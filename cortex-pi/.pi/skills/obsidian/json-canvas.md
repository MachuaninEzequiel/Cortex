---
name: json-canvas
description: Creación de mapas mentales y diagramas visuales (.canvas).
---
# JSON Canvas
Guía para generar lienzos visuales compatibles con Obsidian Canvas.

## Estructura .canvas (JSON)
```json
{
  "nodes": [
    { "id": "hex16", "type": "text", "x": 0, "y": 0, "width": 400, "height": 200, "text": "Contenido" }
  ],
  "edges": [
    { "id": "hex16", "fromNode": "id1", "toNode": "id2", "toEnd": "arrow" }
  ]
}
```
## Reglas
- IDs: 16 caracteres hexadecimales aleatorios.
- Tipos: `text`, `file`, `link`, `group`.
- Espaciado: Deja 50-100px entre nodos.
