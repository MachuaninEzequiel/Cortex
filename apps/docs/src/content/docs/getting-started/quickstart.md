---
title: Inicio Rápido (5 Minutos)
description: Aprenda a inicializar Cortex en un proyecto, abrir una sesión con un agente de IA y almacenar conocimiento persistente.
---

Esta guía le permitirá configurar Cortex en su proyecto y realizar su primera sesión de trabajo asistida por memoria cognitiva.

---

## 1. Instalar el binario CLI de Cortex

Si dispone del entorno de desarrollo Rust instalado, instale `cortex-cli` directamente desde el workspace:

```bash
cargo install --path rust/crates/cortex-cli
```

Verifique la instalación:

```bash
cortex-cli --version
```

*(El comando creará el alias o binario ejecutable `cortex` / `cortex-cli`).*

---

## 2. Verificar el Entorno (`cortex doctor`)

Antes de comenzar, ejecute el diagnóstico nativo para asegurar que el sistema cumple con todos los requisitos locales:

```bash
cortex doctor
```

Salida esperada:
```text
[OK] rust_toolchain: Cargo y Rust runtime detectados
[OK] workspace_layout: Estructura de directorios válida
[OK] onnx_model: Modelo de embedding disponible
[OK] vault_permissions: Permisos de lectura/escritura en .cortex/
```

---

## 3. Inicializar Cortex en su Proyecto

Navegue a la raíz de su proyecto y ejecute:

```bash
cortex init
```

Este comando creará la estructura base `.cortex/`:
* `.cortex/config.yaml`: Configuración principal de modelos, retención y pesos de búsqueda.
* `.cortex/workspace.yaml`: Definición del layout del espacio de trabajo.
* `.cortex/vault/`: Directorio raíz para notas Markdown estructuradas (ADRs, arquitectura, etc.).
* `.cortex/memory/`: Almacén JSONL de memoria episódica.

---

## 4. Iniciar una Sesión de Trabajo

Cada vez que comience a trabajar en una nueva tarea o feature, inicie una sesión:

```bash
cortex session open --name "migracion-modulo-auth" --notes "Refactorización de tokens JWT a Rust"
```

Para consultar el estado de la sesión activa:

```bash
cortex session current
```

---

## 5. Recordar y Buscar Conocimiento

### Guardar un descubrimiento o nota rápida
Durante el desarrollo, puede persistir hallazgos técnicos inmediatamente:

```bash
cortex remember "El algoritmo de hashing de contraseñas usa Argon2id con 3 iteraciones y memoria de 64MB" --tag auth --tag seguridad
```

### Búsqueda cognitiva híbrida
Recupere información combinando búsqueda léxica (BM25) y semántica vectorial (ONNX):

```bash
cortex search "cuál es la configuración de hashing de contraseñas"
```

---

## 6. Cerrar la Sesión con Evidencia

Al finalizar la tarea, cierre la sesión para consolidar el historial y generar el resumen:

```bash
cortex finish --intent auto
```

---

## Siguientes Pasos

* Configure su IDE favorito con [`cortex ide setup`](/es/cli/cortex-ide/).
* Explore la interfaz visual de terminal ejecutando `cortex` sin argumentos ([TUI](/es/cli/cortex-tui/)).
* Conozca todas las [herramientas MCP disponibles para agentes](/es/mcp/overview/).
