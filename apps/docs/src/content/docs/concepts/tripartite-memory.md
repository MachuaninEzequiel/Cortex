---
title: Modelo de Memoria Tripartita
description: Cómo Cortex separa la memoria en tres dimensiones complementarias (Episódica, Semántica y Procedural) para optimizar el contexto de los agentes de IA.
---

Inspirado en la psicología cognitiva y la arquitectura cerebral humana, Cortex implementa el **modelo de memoria tripartita**. Esta separación permite a los agentes de IA acceder a la información precisa sin sobrecargar la ventana de contexto con datos redundantes.

---

## Comparativa de los Tres Tipos de Memoria

| Tipo | Pregunta que Responde | Formato de Almacenamiento | Persistencia | Comandos Asociados |
| :--- | :--- | :--- | :--- | :--- |
| **Episódica** | *¿Qué ocurrió y cuándo?* | JSON Lines (`.cortex/memory/*.jsonl`) | Temporal / Sesión | `cortex remember`, `cortex session` |
| **Semántica** | *¿Qué conceptos y reglas rigen el código?* | Markdown estructurado (`.cortex/vault/**/*.md`) | Permanente / Canónica | `cortex search`, `cortex docs` |
| **Procedural** | *¿Qué debemos hacer ahora?* | Reglas de decisión y métricas de acción | Dinámica / Runtime | `cortex next`, `cortex autopilot` |

---

## 1. Memoria Episódica (Eventos Temporales)

La memoria episódica registra los eventos cronológicos de las sesiones de trabajo del agente. Cada entrada contiene:
* **`id`**: Identificador único `mem_<timestamp>_<hash>`.
* **`timestamp`**: Fecha y hora UTC del registro.
* **`content`**: Texto descriptivo del descubrimiento o acción.
* **`type`**: Tipo de memoria (`general`, `decision`, `bugfix`, `refactor`, `discovery`).
* **`tags`**: Etiquetas temáticas.
* **`file_references`**: Archivos y líneas de código vinculadas al evento.
* **`embedding`**: Vector de 384 dimensiones generado localmente por ONNX.

```json
{
  "id": "mem_20260902_182045_a1b2",
  "created_at": "2026-09-02T18:20:45Z",
  "type": "discovery",
  "content": "El crate cortex-core no debe depender de pyo3 para mantener paridad pura offline",
  "tags": ["architecture", "invariants"],
  "files": ["rust/crates/cortex-core/src/lib.rs"]
}
```

---

## 2. Memoria Semántica (Conocimiento Canónico)

La memoria semántica está compuesta por el **Vault**, un árbol jerárquico de documentos Markdown enriquecidos con frontmatter YAML. Es la fuente de verdad que describe la arquitectura, las decisiones duraderas y los estándares del proyecto.

### DocTypes Canónicos
* **`adr`**: *Architectural Decision Record*. Decisiones fundamentales y su justificación.
* **`spec`**: Especificaciones funcionales y requisitos técnicos.
* **`design`**: Notas de diseño de arquitectura y contratos de API.
* **`handoff`**: Resumen estructurado para pasar el contexto entre diferentes agentes o entre un agente y un humano.
* **`runbook`**: Procedimientos operativos y pasos de despliegue/mantenimiento.
* **`incident` / `postmortem`**: Registro de fallos, análisis de causa raíz y acciones correctivas.
* **`glossary`**: Definición de términos técnicos y conceptos de dominio.

---

## 3. Memoria Procedural (ActionEngine)

La memoria procedural responde a la pregunta de cómo proceder ante un estado determinado. A través de [`cortex-actions`](file:///home/chucho/Cortex/rust/crates/cortex-actions), Cortex analiza:
1. El estado actual de la sesión (abierta, en progreso, tareas pendientes).
2. Los archivos modificados en el árbol de Git.
3. El historial de checkpoints previos.

A partir de esta información, el motor pondera las acciones disponibles en su catálogo (por ejemplo: *proponer spec*, *crear checkpoint*, *ejecutar verificación de tests*, *cerrar sesión*) y genera una recomendación priorizada mediante `cortex next`.
