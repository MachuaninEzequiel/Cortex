# Pipeline — Módulos Custom

## Concepto

Cada stage del pipeline de Cortex ejecuta una **herramienta externa** (linter, test runner, scanner de seguridad). Estas herramientas son **intercambiables**: podés reemplazar las defaults por las que use tu equipo.

---

## Herramientas por defecto

| Stage | Default | Lenguaje |
| --- | --- | --- |
| Security | `npm audit` | JavaScript/Node |
| Lint | `ruff check .` | Python |
| Test | `pytest` | Python |
| Documentation | `cortex verify-docs` | Agnóstico |

---

## Cómo cambiar un módulo

Editá el campo `tool` del stage correspondiente en `config.yaml`:

### Ejemplo: Proyecto JavaScript con ESLint + Jest

```yaml
pipeline:
  stages:
    security:
      enabled: true
      block_on_failure: true
      tool: "npm audit --audit-level=moderate"
    lint:
      enabled: true
      block_on_failure: true
      tool: "npx eslint . --max-warnings 0"
    test:
      enabled: true
      block_on_failure: true
      tool: "npx jest --ci --coverage"
    documentation:
      enabled: true
      block_on_failure: false
      tool: "cortex verify-docs"
```

### Ejemplo: Proyecto Go

```yaml
pipeline:
  stages:
    security:
      enabled: true
      tool: "gosec ./..."
    lint:
      enabled: true
      tool: "golangci-lint run"
    test:
      enabled: true
      tool: "go test ./... -v -cover"
    documentation:
      enabled: true
      block_on_failure: false
      tool: "cortex verify-docs"
```

### Ejemplo: Proyecto Python con Pylint

```yaml
pipeline:
  stages:
    lint:
      enabled: true
      tool: "pylint cortex/ --fail-under=8.0"
    test:
      enabled: true
      tool: "pytest --cov=cortex --cov-fail-under=80"
```

---

## Deshabilitar un stage

Si no necesitás un stage, simplemente deshabilitalo:

```yaml
pipeline:
  stages:
    security:
      enabled: false    # No ejecutar security checks
```

---

## Usar scripts propios

Podés apuntar a un script custom en vez de una herramienta instalada:

```yaml
pipeline:
  stages:
    security:
      tool: "bash scripts/security-scan.sh"
    lint:
      tool: "python scripts/custom-linter.py"
```

El único requisito es que el script retorne **exit code 0** en éxito y **exit code != 0** en fallo.

---

## `abort_early`

Si `abort_early: true` (default), el pipeline se detiene en el primer stage que falle. Si es `false`, ejecuta todos los stages y reporta todos los fallos al final.

```yaml
pipeline:
  abort_early: false   # Ejecutar todos los stages aunque alguno falle
```

---

## Regenerar workflows

Después de cambiar la configuración, regenerá los workflows de CI:

```bash
cortex setup pipeline
```

Esto actualiza los archivos en `.github/workflows/` con tu nueva configuración.

---

## Siguiente lectura

- **Pipeline base**: [pipeline-setup.md](pipeline-setup.md)
- **Estructura del vault**: [vault-structure.md](vault-structure.md)
