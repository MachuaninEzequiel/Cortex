---
title: cortex next (Motor de Acciones Sugeridas)
description: Cómo el ActionEngine nativo en cortex-actions evalúa el contexto del repositorio y propone la siguiente mejor acción.
---

El comando `cortex next` invoca el **ActionEngine** nativo ([`cortex-actions`](file:///home/chucho/Cortex/rust/crates/cortex-actions)), un motor procedural que analiza el estado del repositorio, las tareas pendientes y los cambios de Git para responder a la pregunta: ***¿Cuál es la siguiente mejor acción técnica a realizar?***

---

## Sintaxis

```bash
cortex next [OPCIONES]
```

---

## Opciones Disponibles

```text
Usage: cortex next [OPTIONS]

Options:
      --all               Muestra todas las acciones candidatas evaluadas
      --json              Emite la propuesta en formato JSON estructurado
      --explain-why-not   Explica por qué otras acciones fueron descartadas
      --stats             Muestra métricas de aceptación y tiempos de inferencia
      --tui               Abre la pantalla de aprobación de acciones en Ratatui
      --project-root <P>  Ruta absoluta a la raíz del proyecto
  -h, --help              Muestra la ayuda
```

---

## Catálogo de Acciones Evaluadas por el Motor

El Scheduler de Cortex evalúa continuamente condiciones como:

1. **`ProposeSpec`:** Si se detecta un requerimiento nuevo o cambios amplios sin una spec asociada en `vault/specs/`.
2. **`CreateCheckpoint`:** Si han transcurrido más de N modificaciones de archivos o 30 minutos sin registrar un checkpoint en la sesión.
3. **`RunVerification`:** Si se han completado tareas de código pero no se han corrido los tests asociados.
4. **`EmitDesignNote`:** Si se están tocando contratos de API o modelos de datos transversales.
5. **`HandoffReview`:** Si la sesión actual contiene múltiples tareas finalizadas y se recomienda consolidar evidencia antes de cambiar de turno.

---

## Ejemplos de Uso

### 1. Invocación Estándar
```bash
cortex next
```

Salida típica:
```text
🧠 Acción recomendada: [CreateCheckpoint] (Confianza: 0.88)
Razón: Se modificaron 4 archivos en 'rust/crates/cortex-core/' sin checkpoint registrado en la última hora.
Comando sugerido: cortex session checkpoint --note "Refactorización de store v2"
```

### 2. Explicabilidad con `--explain-why-not`
```bash
cortex next --explain-why-not
```

Salida:
```text
[Seleccionada] CreateCheckpoint (Score: 0.88)
[Descartada]   ProposeSpec (Score: 0.20) — Razón: Ya existe una spec activa en 'vault/specs/spec-012.md'.
[Descartada]   FinishSession (Score: 0.05) — Razón: Hay 2 tareas pendientes en la sesión actual.
```

### 3. Aprobación Visual con `--tui`
```bash
cortex next --tui
```
Despliega la pantalla interactiva de Ratatui donde el desarrollador puede presionar <kbd>Enter</kbd> para ejecutar automáticamente la acción sugerida o <kbd>d</kbd> para descartarla y calibrar las preferencias locales.
