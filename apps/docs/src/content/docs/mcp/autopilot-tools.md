---
title: Herramientas MCP de Autopilot
description: cortex_autopilot_start, preflight, checkpoint, finish y status para supervisión autónoma.
---

Este conjunto de herramientas permite a los agentes operar bajo los protocolos de supervisión y seguridad de Autopilot.

---

## 1. `cortex_autopilot_start`
Inicia o adopta la sesión activa bajo un modo de supervisión de Autopilot.

* **Parámetros:**
  * `mode` (string, default `"assist"`): `observe`, `assist`, `autopilot`.
  * `policy_overrides` (objeto, opcional): Sobrescritura de políticas específicas de seguridad.

---

## 2. `cortex_autopilot_preflight`
Ejecuta una evaluación previa de riesgos ante una acción propuesta sin aplicar cambios reales.

* **Parámetros:**
  * `request` (string, opcional): Consulta o intención del usuario.
  * `files` (array de strings, opcional): Archivos que se planea modificar o eliminar.

---

## 3. `cortex_autopilot_checkpoint`
Registra un checkpoint en el ciclo de ejecución de autopilot.

* **Parámetros:**
  * `source` (string, default `"manual"`): Fuente del checkpoint (`cortex-SDDwork`, `ci-bot`, etc.).
  * `note` (string): Nota explicativa del paso realizado.

---

## 4. `cortex_autopilot_finish`
Finaliza la ejecución de autopilot, validando que se hayan cumplido todos los preflights y que no existan advertencias de seguridad pendientes.

* **Parámetros:**
  * `summary` (string, opcional): Resumen de los resultados obtenidos.

---

## 5. `cortex_autopilot_status`
Consulta el estado de las políticas de seguridad activas, modo de ejecución y advertencias emitidas.
