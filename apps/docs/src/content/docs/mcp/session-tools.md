---
title: Herramientas MCP de Sesiones y Tareas
description: cortex_session_open, cortex_session_checkpoint, cortex_session_task_list, cortex_session_task_update y finish.
---

Las herramientas de sesión permiten a los LLMs autogestionar su ciclo de trabajo, reportar tareas granulares y registrar hitos de avance.

---

## 1. `cortex_session_open`
Abre una nueva sesión de desarrollo si no existe una activa.

* **Parámetros:**
  * `name` (string, requerido): Nombre descriptivo de la sesión.
  * `notes` (string, opcional): Contexto o meta general de la sesión.
  * `tags` (array de strings, opcional): Etiquetas temáticas.

---

## 2. `cortex_session_checkpoint`
Registra un punto de control intermedio.

* **Parámetros:**
  * `note` (string, requerido): Descripción del progreso o hito alcanzado.
  * `source` (string, requerido): Fuente del checkpoint. Valores permitidos:
    `cortex-sync`, `cortex-SDDwork`, `cortex-code-explorer`, `cortex-code-implementer`, `cortex-code-designer`, `user-skill`, `ide-hook`, `manual`, `ci-bot`.
  * `files` (array de strings, opcional): Archivos modificados en este paso.

---

## 3. `cortex_session_task_list`
Consulta la lista ordenada de tareas asociadas a la sesión activa (o a una sesión específica).

* **Parámetros:**
  * `session_id` (string, opcional): ID de la sesión (por defecto: sesión activa).
  * `status` (string, opcional): Filtrar por `pending`, `in-progress`, `done`, `skipped`, `blocked`.

---

## 4. `cortex_session_task_update`
Actualiza el estado de una tarea granular dentro de la sesión.

* **Parámetros:**
  * `task_id` (string, requerido): ID de la tarea a modificar.
  * `status` (string, requerido): `pending`, `in-progress`, `done`, `skipped`, `blocked`.
  * `notes` (string, opcional): Comentarios o detalles de la resolución.

---

## 5. `cortex_finish_session`
Consolida el trabajo de la sesión, valida que las tareas requeridas estén concluidas y genera el resumen de cierre.

* **Parámetros:**
  * `session_id` (string, opcional): ID de la sesión a cerrar.
  * `intent` (string, opcional, default: `"auto"`): `auto`, `handoff`, `abandon`.
  * `reason` (string, opcional): Justificación del cierre.
