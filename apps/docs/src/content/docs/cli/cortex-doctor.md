---
title: cortex doctor
description: Referencia completa de argumentos y comportamiento del comando cortex doctor.
---

El comando `cortex doctor` valida los prerrequisitos del entorno de ejecución de Cortex, la integridad del espacio de trabajo y el estado de las políticas de gobernanza.

---

## Sintaxis

```bash
cortex doctor [OPCIONES]
```

---

## Opciones Disponibles

```text
Usage: cortex doctor [OPTIONS]

Options:
      --project-root <PROJECT_ROOT>  Ruta absoluta al proyecto (donde reside .cortex/)
      --strict                       Falla con rc=1 si hay advertencias (warnings)
      --scope <SCOPE>                Alcance: project, enterprise, o all [default: project]
  -h, --help                         Muestra la ayuda
```

---

## Opciones de `--scope`

* **`project` (Predeterminado):** Verifica la configuración local del proyecto, existencia de `.cortex/config.yaml`, disponibilidad del modelo ONNX local, permisos de lectura y escritura en `.cortex/vault` y `.cortex/memory`, y estado del storage de sesiones.
* **`enterprise`:** Verifica la configuración de `.cortex/org.yaml`, coherencia del identificador de organización, colas de revisión de conocimiento pendientes, y políticas de retención.
* **`all`:** Ejecuta el conjunto completo de validaciones tanto de nivel de proyecto como organizacionales.

---

## Ejemplos de Invocación

### 1. Chequeo Rápido de Proyecto
```bash
cortex doctor
```

### 2. Validación Estricta para CI
```bash
cortex doctor --strict --scope all
```

### 3. Diagnóstico en un Directorio Específico
```bash
cortex doctor --project-root /home/usuario/proyectos/mi-app
```
