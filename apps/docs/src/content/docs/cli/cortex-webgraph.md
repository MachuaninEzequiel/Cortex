---
title: cortex webgraph
description: Exportación de grafos de conocimiento y servidor web visual nativo en Axum.
---

El comando `cortex webgraph` gestiona la generación y visualización de **grafos de conocimiento semánticos** entre las notas del Vault y los eventos episódicos, utilizando el servidor web nativo de alta velocidad basado en Axum ([`cortex-webgraph-server`](file:///home/chucho/Cortex/rust/crates/cortex-webgraph-server)).

---

## Subcomandos

```text
Usage: cortex webgraph <COMMAND>

Commands:
  export  Exporta un snapshot del grafo en formato JSON
  serve   Inicia el servidor web nativo en Axum para visualizar el grafo
  doctor  Valida la conectividad y coherencia del grafo
```

---

## Detalle de Subcomandos

### 1. `cortex webgraph serve`
Inicia el servidor HTTP local y expone la interfaz visual interactiva del grafo en 2D/3D:

```bash
cortex webgraph serve [OPCIONES]
```

**Opciones:**
* `--host <HOST>`: Dirección IP a la que vincular el servidor (ej: `127.0.0.1` o `0.0.0.0`).
* `--port <PORT>`: Puerto TCP de escucha (por defecto: `8080` o asignado dinámicamente).
* `--no-open`: No abre automáticamente el navegador web predeterminado.
* `--project-root <PATH>`: Ruta al proyecto.

```bash
cortex webgraph serve --port 3000
# 🌐 Servidor WebGraph activo en http://127.0.0.1:3000
```

---

### 2. `cortex webgraph export`
Genera un snapshot estático del grafo en formato JSON para ser consumido por herramientas de visualización externa, pipelines de análisis o la app CortexBrain.

```bash
cortex webgraph export [MODE] [OPCIONES]
```

**Modos de Grafo (`[MODE]`):**
* `hybrid` (Predeterminado): Combina relaciones semánticas (similitud de notas) con enlaces explícitos y eventos episódicos.
* `semantic`: Solo enlaces conceptuales derivados de la matriz de similitud ONNX y backlinks de Markdown.
* `episodic`: Solo nodos de sesiones temporales y sus transiciones.

**Opciones:**
* `--output <PATH>`: Ruta del archivo JSON de salida (ej: `./graph-snapshot.json`).
* `--no-cache`: Fuerza la reconstrucción completa del grafo recalculando distancias $O(n^2)$ con Rayon.
* `--workspace-file <PATH>`: Archivo de federación de espacios de trabajo para multi-proyecto.

```bash
cortex webgraph export hybrid --output ./docs/graph.json
```
