---
title: Visualizador WebGraph
description: Exploración interactiva del grafo de conocimiento con física de fuerzas (Force-Directed Graph).
---

El **Visualizador WebGraph** de CortexBrain transforma la base de conocimiento Markdown y la memoria episódica en un grafo interactivo navegable.

---

## Modos de Visualización

1. **Grafo 2D / 3D con Simulación de Fuerzas:**
   * Los nodos representan notas del Vault (`adrs`, `specs`, `designs`, `runbooks`) o eventos episódicos.
   * Las aristas representan enlaces explícitos (Markdown backlinks) y afinidad semántica calculada mediante la matriz de similitud coseno de los embeddings ONNX.
2. **Filtrado Dinámico:**
   * Filtrado por tipo de documento (`DocType`).
   * Filtrado por etiquetas (`tags`).
   * Umbral de similitud semántica configurable mediante un deslizador en tiempo real.
3. **Inspección de Nodos:**
   * Al hacer clic en cualquier nodo, se despliega el contenido completo de la nota renderizado con resaltado de sintaxis, metadatos YAML y lista de documentos conectados.
4. **Agrupamiento Conceptual (Clustering):**
   * Detección automática de comunidades de conocimiento para identificar módulos con alta cohesión o áreas de la arquitectura con acoplamiento técnico.
