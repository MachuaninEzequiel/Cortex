# Infraestructura de CI/CD: Cortex DevSecDocOps

Este documento describe la configuración de infraestructura necesaria para ejecutar el pipeline de Cortex en entornos de integración continua (GitHub Actions) y cómo se gestionan los estados específicos de CI.

## 1. Bypass de Validación de Entorno (Cortex Doctor)

El comando `cortex doctor` realiza validaciones profundas del entorno. En entornos locales, la ausencia del almacén de memoria episódica (`.memory/chroma/`) se considera un fallo crítico.

### Comportamiento en CI
Para evitar que el pipeline falle en ejecuciones limpias (donde la memoria todavía no ha sido restaurada o creada), el `doctor` detecta automáticamente si se encuentra en un entorno de **GitHub Actions** mediante la variable de entorno `GITHUB_ACTIONS=true`.

*   **Local**: Falta de `.memory/chroma/` -> `[FAIL]` (Exit Code 1).
*   **CI**: Falta de `.memory/chroma/` -> `[WARN]` (Sigue adelante).

No es necesario aplicar flags adicionales, el bypass es automático.

## 2. Captura de Estado de Documentación (Verify Docs)

El comando `cortex verify-docs` se utiliza en el pipeline para decidir si es necesario generar nueva documentación basada en el contexto del PR.

### Modo Silencioso (`--quiet`)
Por defecto, `verify-docs` emite mensajes amigables para humanos. Para su uso en scripts de CI, se debe utilizar el flag `--quiet` o `-q`.

```bash
# Uso recomendado en CI
HAS_DOCS=$(cortex verify-docs --vault vault --quiet)
```

Esto garantiza que la salida estándar (`stdout`) sea únicamente `true` o `false`, evitando errores de formato al capturar variables en GitHub Actions (`$GITHUB_OUTPUT`).

## 3. Configuración del Workflow

El archivo de configuración principal se encuentra en `.github/workflows/ci-pull-request.yml`. 

### Pasos Críticos:

1.  **Cortex - Doctor**: Valida que las dependencias y la configuración base (`config.yaml`) sean correctas.
2.  **Cortex - Verify Docs**: Determina si el agente ya incluyó documentación en el PR.
3.  **Cortex - Generate Documentation**: (Condicional) Solo se ejecuta si `has_agent_docs` es `false`.
4.  **Cortex - Validate Docs**: Realiza la validación final de estructura y frontmatter de todos los documentos en el `vault/`.

## 4. Troubleshooting de CI

### Error: `Invalid format 'false'`
Este error ocurre si se captura el output de `verify-docs` sin el flag `--quiet`. GitHub Actions no puede procesar el texto decorado multilínea como un valor simple.

### Error: `Cortex - Doctor [FAIL]`
Si el doctor falla en CI, generalmente se debe a:
-   Falta de `config.yaml` en la raíz.
-   Directorio `vault/` inexistente.
-   Inconsistencias graves en la configuración enterprise (`.cortex/org.yaml`).

---
*Documentación generada por Antigravity — 2026-04-27*
