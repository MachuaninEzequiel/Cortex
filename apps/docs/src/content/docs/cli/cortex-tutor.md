---
title: cortex tutor & cortex hint
description: Guía interactiva offline y asistencia contextual sin consumo de tokens.
---

Los comandos `cortex tutor` y `cortex hint` ofrecen asistencia técnica, guías didácticas y recordatorios contextuales **directamente desde el binario nativo de Cortex, con cero tokens consumidos y 100% offline** ([`cortex-tutor`](file:///home/chucho/Cortex/rust/crates/cortex-tutor)).

---

## `cortex tutor`

Despliega una enciclopedia interactiva de conceptos, guías y patrones arquitectónicos de Cortex:

```bash
cortex tutor [TOPIC]
```

### 1. Menú Interactivo (Sin Argumentos)
Al ejecutar `cortex tutor`, se abre un selector de tópicos guiado:

```text
🧠 Tutor de Cortex — Guía de Aprendizaje (Zero Tokens)

Seleccione un tema:
1. Arquitectura y Modelo Tripartito
2. Flujo de Sesiones y Checkpoints
3. Uso del Protocolo MCP
4. Búsqueda Híbrida RRF y Vault
5. Buenas Prácticas para Agentes de IA
q. Salir
> 
```

### 2. Consulta Directa por Slug de Tópico
Es posible acceder directamente a cualquier lección técnica indicando su identificador:

```bash
cortex tutor pipeline
cortex tutor vault
cortex tutor mcp
cortex tutor enterprise
```

---

## `cortex hint`

El comando `cortex hint` analiza rápidamente el estado del repositorio y emite un consejo contextual en una sola línea.

```bash
cortex hint
```

### Ejemplos de Salida:
* Si no hay sesión activa:
  ```text
  💡 Tip: No tienes una sesión activa. Inicia una con `cortex session open --name <nombre>` para registrar tu progreso.
  ```
* Si hay cambios sin checkpoint:
  ```text
  💡 Tip: Tienes 6 archivos modificados. Ejecuta `cortex session checkpoint` para capturar este hito.
  ```
* Si la spec está lista:
  ```text
  💡 Tip: Revisa la spec activa antes de codificar ejecutando `cortex docs search --doc-type spec`.
  ```

---

## Filosofía: Zero Tokens, Zero Latency

A diferencia de los asistentes que requieren consultar a un LLM para responder preguntas frecuentes sobre el propio framework, `cortex tutor` y `cortex hint` residen compilados dentro del binario Rust. Esto permite aprender a utilizar Cortex sin gastar cuota de API ni esperar respuestas remotas.
