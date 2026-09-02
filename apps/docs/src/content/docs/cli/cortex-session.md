---
title: cortex session
description: Gestión integral de sesiones de desarrollo, checkpoints, diffs, tareas y consolidación con finish.
---

El subárbol `cortex session` gestiona el ciclo de vida de las sesiones de trabajo en Cortex, garantizando trazabilidad total de lo que un agente de IA diseña e implementa.

---

## Subcomandos Disponibles

```text
Usage: cortex session <COMMAND>

Commands:
  current     Muestra la sesión activa actualmente
  list        Lista todas las sesiones registradas
  show        Muestra los detalles completos de una sesión
  diff        Muestra el diff de cambios de código asociados a la sesión
  switch      Cambia la sesión activa
  checkpoint  Registra un punto de control intermedio
  abandon     Abandona una sesión activa o específica
  watch       Monitorea en vivo el estado y eventos de la sesión
  tui         Abre la vista de sesiones en la interfaz TUI
```

---

## Detalle de Subcomandos

### 1. `cortex session current`
Muestra el resumen de la sesión actualmente abierta.

```bash
cortex session current
```
Salida en tabla o texto con: ID de sesión, estado (`open`), tiempo transcurrido, autor, número de checkpoints y lista de tareas en progreso.

---

### 2. `cortex session list`
Lista las sesiones registradas en el almacén `.cortex/sessions/`.

```bash
cortex session list [OPCIONES]
```

**Opciones:**
* `--status <open|closed|handoff|abandoned>`: Filtra por estado de sesión.
* `--limit <N>`: Limita la cantidad de resultados mostrados.
* `--json`: Emite el array de sesiones en formato JSON estructurado.

---

### 3. `cortex session show [SESSION_ID]`
Muestra el desglose detallado de una sesión específica (o la activa si se omite el ID).

```bash
cortex session show sess_20260902_183000_cortex
cortex session show --json
```

---

### 4. `cortex session checkpoint`
Registra un punto de control en el historial de la sesión activa, vinculando los cambios en disco y notas de progreso.

```bash
cortex session checkpoint --source manual --note "Completada refactorización de scoring.rs"
```

**Valores válidos de `--source`:**
`cortex-sync`, `cortex-SDDwork`, `cortex-code-explorer`, `cortex-code-implementer`, `cortex-code-designer`, `user-skill`, `ide-hook`, `manual`, `ci-bot`.

---

### 5. `cortex session diff`
Calcula y muestra el `git diff` de los archivos modificados desde el inicio de la sesión.

```bash
cortex session diff
```

---

### 6. `cortex session switch <SESSION_ID>`
Cambia la sesión activa a otra existente previamente abierta o en estado de handoff.

```bash
cortex session switch sess_20260901_101500_auth
```

---

### 7. `cortex finish` / `cortex finish-session`
Cierra la sesión activa de forma formal, consolidando la evidencia de trabajo, actualizando las tareas y generando una nota de handoff o resumen en el Vault.

```bash
cortex finish --intent auto
cortex finish --intent handoff --reason "Paso de contexto al turno de la tarde"
```

**Opciones de `--intent`:** `auto` (default), `abandon`, `handoff`.
