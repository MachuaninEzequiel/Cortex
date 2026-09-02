---
title: cortex autopilot
description: Capa de decisión y ejecución autónoma para agentes de IA con modos observe, assist y autopilot.
---

El comando `cortex autopilot` opera la **capa de decisión y supervisión autónoma** de Cortex ([`cortex-autopilot`](file:///home/chucho/Cortex/rust/crates/cortex-autopilot)).

---

## Modos de Operación de Autopilot

Cortex define tres modos de autonomía estrictos:

1. **`observe` (Pasivo):** El agente y Cortex monitorizan el progreso sin intervenir en la ejecución de comandos ni requerir aprobaciones.
2. **`assist` (Copiloto / Predeterminado):** Cortex evalúa cada paso, emite advertencias ante cambios peligrosos o specs faltantes, y sugiere checkpoints intermedios.
3. **`autopilot` (Autónomo):** Cortex ejecuta validaciones automáticas antes de cada acción destructiva (preflight checks) y gestiona el flujo de trabajo de inicio a fin.

---

## Subcomandos

```text
Usage: cortex autopilot <COMMAND>

Commands:
  start       Adopta la sesión activa bajo el modo especificado
  preflight   Ejecuta el pipeline de detección en modo simulado (dry-run)
  checkpoint  Registra un punto de control con notas de intención
  finish      Finaliza la ejecución autónoma y verifica criterios de cierre
  status      Muestra el estado de la política activa y advertencias
  doctor      Verifica las reglas de seguridad y políticas de autopilot
```

---

## Detalle de Subcomandos

### 1. `cortex autopilot start`
```bash
cortex autopilot start --mode assist
cortex autopilot start --mode autopilot --json
```

### 2. `cortex autopilot preflight`
Ejecuta los detectores de riesgo de forma aislada sin modificar el estado de la sesión:
```bash
cortex autopilot preflight --request "Eliminar tablas de base de datos" --file "migrations/001.sql"
```

Salida:
```text
⚠️ [SAFETY WARNING] Operación clasificada como destructiva.
Se requiere aprobación explícita humana antes de continuar.
```

### 3. `cortex autopilot checkpoint`
Registra un checkpoint vinculado a la sesión de autopilot activa:
```bash
cortex autopilot checkpoint --source cortex-SDDwork --note "Completada fase de exploración"
```

### 4. `cortex autopilot status`
Consulta el estado de las políticas de seguridad y métricas del ciclo activo:
```bash
cortex autopilot status
```
