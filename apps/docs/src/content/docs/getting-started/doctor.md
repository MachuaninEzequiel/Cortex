---
title: Diagnóstico del Sistema con Doctor
description: Cómo utilizar cortex doctor para validar prerrequisitos, estado de gobernanza y salud del workspace.
---

El comando `cortex doctor` es la herramienta canónica de validación y auditoría de Cortex. Permite verificar que el entorno local, las dependencias de modelos, la configuración y los esquemas de gobernanza se encuentren en perfecto estado de funcionamiento.

---

## Ejecución Básica

```bash
cortex doctor
```

El verificador ejecutará una batería de comprobaciones en serie y emitirá un informe detallado:

```text
[OK] cargo_installed: Cargo toolchain is accessible
[OK] project_layout: .cortex layout discovered at /path/to/project
[OK] config_yaml: .cortex/config.yaml is valid
[OK] onnx_model: Embedding model is available
[OK] vault_readable: Vault notes readable (12 notes discovered)
[OK] session_storage: Session storage initialized
```

---

## Opciones y Flags de `cortex doctor`

| Flag | Tipo | Descripción | Default |
| :--- | :---: | :--- | :---: |
| `--scope` | `string` | Alcance de la validación: `project`, `enterprise`, o `all`. | `project` |
| `--strict` | `bool` | Falla con código de salida `rc=1` ante advertencias (`[WARN]`), no solo ante errores duros (`[FAIL]`). | `false` |
| `--project-root` | `path` | Ruta absoluta a la raíz del proyecto a diagnosticar. | Directorio actual (`cwd`) |

### Ejemplos de Uso

#### 1. Diagnóstico en Modo Estricto para Pipelines de CI
```bash
cortex doctor --strict
```
Si cualquier check produce un `[WARN]` o `[FAIL]`, el proceso terminará con código de retorno no-cero, bloqueando commits o merges inválidos.

#### 2. Validación de Políticas Enterprise
```bash
cortex doctor --scope enterprise
```
Valida la integridad de `.cortex/org.yaml`, las reglas de retención de memoria, la firma de auditoría de los revisores y los permisos del vault compartido.

#### 3. Diagnóstico de un Proyecto Externo
```bash
cortex doctor --project-root /home/usuario/proyectos/mi-servicio
```

---

## Códigos de Severidad

* **`[OK]`**: El componente está completamente operativo y verificado.
* **`[INFO]`**: Mensaje informativo sobre la configuración activa.
* **`[WARN]`**: Advertencia no bloqueante (por ejemplo, un archivo de configuración opcional no presente o versión de modelo previa).
* **`[FAIL]`**: Error crítico que impide la operación normal de Cortex (permisos insuficientes, YAML con sintaxis inválida, etc.).
