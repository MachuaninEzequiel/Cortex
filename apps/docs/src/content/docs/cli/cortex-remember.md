---
title: cortex remember & cortex forget
description: Guardado rápido e invalidación de eventos en la memoria episódica de Cortex.
---

Los comandos `cortex remember` y `cortex forget` permiten a humanos y agentes registrar o invalidar información atómica en la memoria episódica de forma instantánea.

---

## `cortex remember`

Persiste un evento en la memoria episódica (`.cortex/memory/`), generando automáticamente su embedding vectorial con ONNX:

```bash
cortex remember <CONTENIDO> [OPCIONES]
```

### Opciones de `cortex remember`

| Flag | Tipo | Descripción | Default |
| :--- | :---: | :--- | :---: |
| `-t, --type` | `string` | Categoría del evento (`general`, `decision`, `bugfix`, `refactor`, `discovery`). | `general` |
| `--tag` | `string` | Etiqueta temática (repetible para múltiples tags). | `[]` |
| `--file` | `string` | Archivo fuente relacionado con el descubrimiento (repetible). | `[]` |
| `--branch` | `string` | Rama de Git asociada al evento. | Rama actual |
| `--repo` | `string` | Nombre del repositorio. | Auto-detectado |
| `--commit` | `string` | Hash del commit de referencia. | HEAD |
| `-s, --summarize` | `bool` | Genera un resumen conciso antes de persistir (si hay LLM configurado). | `false` |

### Ejemplos:

#### 1. Registro Técnico Rápido
```bash
cortex remember "La tabla de tokens expira cada 15 minutos en Redis" --tag redis --tag auth
```

#### 2. Vinculación de un Archivo y Tipo de Decisión
```bash
cortex remember "Optamos por ureq en lugar de reqwest para evitar dependencias async innecesarias en descargas" \
  --type decision \
  --tag rust \
  --tag dependencies \
  --file rust/crates/cortex-core/Cargo.toml
```

---

## `cortex forget`

Invalida o elimina un registro episódico por su identificador único (`mem_*`):

```bash
cortex forget <MEMORY_ID>
```

### Ejemplo:
```bash
cortex forget mem_20260515_142010_e3f1
```

Salida:
```text
✅ Memoria episódica 'mem_20260515_142010_e3f1' eliminada correctamente.
```
