---
title: Integración con Pi IDE y OpenCode
description: Conexión con Pi IDE (cortex-pi) y el entorno de desarrollo abierto OpenCode.
---

Cortex incluye adaptadores de primer nivel (**Target IDEs**) para **Pi IDE** y **OpenCode**.

---

## 1. Integración con Pi IDE (`cortex-pi`)

Pi IDE interactúa con Cortex mediante el módulo especializado `cortex-pi` ubicado en el repositorio.

### Configuración Automática
```bash
cortex ide setup pi
```

### Capacidades Habilitadas en Pi IDE:
* **Panel de Control Cortex Tools:** Panel lateral nativo que detecta la presencia del binario `cortex-cli` y muestra el estado de la sesión activa.
* **Barra de Estado de Memoria:** Indicador de eventos episódicos y notas en el Vault.
* **Acciones Rápidas en Paleta de Comandos:** Atajos para `cortex remember`, `cortex session checkpoint` y `cortex next`.

---

## 2. Integración con OpenCode

OpenCode es un entorno de desarrollo de código abierto orientado a agentes autónomos.

### Configuración
```bash
cortex ide setup opencode
```

La integración registra el runtime de Cortex como proveedor de contexto primario, permitiendo a los agentes de OpenCode almacenar automáticamente sus trazas de ejecución en la memoria episódica de Cortex.
