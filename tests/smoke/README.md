# Cortex Smoke Test

Contenedor Docker que simula un usuario completamente nuevo en una máquina limpia.

## Requisitos

- Docker instalado

## Comandos

```bash
# Construir
docker build -f tests/smoke/Dockerfile.smoke -t cortex-smoke .

# Ejecutar
docker run --rm cortex-smoke
```

## Qué hace

1. Instala Cortex desde cero (`pip install -e ".[dev]"`)
2. Crea un proyecto de prueba
3. Ejecuta el flujo completo:
   - `cortex setup agent --git-depth 5 --ide pi`
   - `cortex doctor`
   - `cortex setup full --git-depth 5`
   - `cortex setup enterprise --preset small-company --non-interactive`
   - `cortex remember`
   - `cortex search`
   - `cortex memory-report --json`
   - `cortex pr-context capture`

## Interpretación de resultados

- Exit 0 = smoke pasó
- Cualquier otro exit = revisar logs

## Estado

⚠️ **Este smoke test fue creado pero NO validado localmente** porque Docker no está disponible en el entorno de desarrollo actual. Validar antes de release.
