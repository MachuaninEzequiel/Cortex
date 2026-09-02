---
title: cortex_ping (Health Check)
description: Verificación de salud y disponibilidad del servidor MCP en menos de 50 milisegundos.
---

La herramienta `cortex_ping` permite a los agentes de IA verificar la disponibilidad y estado operativo del servidor MCP de Cortex de forma casi instantánea antes de proceder con operaciones costosas.

---

## Definición del Esquema

* **Nombre:** `cortex_ping`
* **Latencia objetivo:** &lt; 50 ms (ejecución 100% en memoria en Rust).
* **Parámetros de Entrada (`inputSchema`):** Ninguno.

```json
{
  "type": "object",
  "properties": {},
  "required": []
}
```

---

## Respuesta Emitida

Devuelve un objeto JSON estructurado con el estado actual del servidor:

```json
{
  "status": "ok",
  "version": "2.2",
  "uptime_seconds": 1420,
  "indices_loaded": true,
  "models_loaded": true,
  "last_error_seen": null
}
```

---

## Directriz para Agentes

> **Regla de Oro:** Si `cortex_ping` devuelve `status != "ok"`, el agente **DEBE abortar** la operación informando claramente al usuario el motivo del fallo. No debe intentar degradar las funcionalidades ni realizar fallbacks manuales silenciosos.
