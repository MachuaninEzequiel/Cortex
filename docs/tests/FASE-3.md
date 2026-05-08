# FASE 3 — "El usuario real en su entorno real"

**Documento padre:** `docs/tests/PLAN-GLOBAL.md`  
**Fecha:** 2026-05-08  
**Estado:** Planificación detallada — listo para ejecución  
**Semáforo:** 🟢 Verde (complementaria; aporta confianza total pero no bloquea beta si falla)

---

## 1. Resumen Ejecutivo

Las FASES 1 y 2 validan que Cortex funcione en un entorno controlado con `tmp_path`. Pero un usuario beta no trabaja en un directorio vacío de pytest: trabaja en un proyecto Vite, un monorepo Python, o un legacy project que ya tiene archivos.

Esta fase introduce:
1. **Fixtures de proyectos prefabricados** — directorios estáticos que simulan proyectos reales sobre los cuales se instala Cortex.
2. **Tests parametrizados de setup sobre fixtures** — validar que `cortex setup full` y `cortex setup enterprise` funcionen correctamente independientemente del tipo de proyecto.
3. **Docker Smoke Test** — un contenedor limpio que instala Cortex desde cero y ejecuta el flujo completo de un usuario virgen.

---

## 2. Gate de Entrada

- [ ] FASE 1 cerrada.
- [ ] FASE 2 cerrada.
- [ ] Los helpers `copy_fixture_project` de FASE 1 funcionan.

---

## 3. Gate de Salida (Definition of Done)

- [ ] Los 4 fixtures de proyecto existen en `tests/e2e/fixtures/`.
- [ ] Los tests parametrizados de setup sobre fixtures pasan.
- [ ] El Dockerfile smoke existe y construye correctamente.
- [ ] El smoke test ejecuta sin errores (`docker build -f tests/smoke/Dockerfile.smoke .`).
- [ ] Se documenta en `tests/smoke/README.md` cómo correr el smoke test.

---

## 4. Estructura de Archivos

```
tests/
├── e2e/
│   ├── fixtures/                        ← NUEVO
│   │   ├── __init__.py
│   │   ├── empty-project/
│   │   │   └── .gitkeep
│   │   ├── vite-react-project/
│   │   │   ├── package.json
│   │   │   ├── vite.config.js
│   │   │   └── src/
│   │   │       └── main.jsx
│   │   ├── python-package/
│   │   │   ├── pyproject.toml
│   │   │   └── src/
│   │   │       └── mypkg/
│   │   │           └── __init__.py
│   │   └── legacy-cortex-project/
│   │       ├── config.yaml              ← config legacy (layout_version ausente o 1)
│   │       └── vault/
│   │           └── legacy_doc.md
│   └── scenarios/
│       └── test_setup_on_fixtures.py    ← NUEVO
└── smoke/
    ├── Dockerfile.smoke                 ← NUEVO
    ├── entrypoint.sh                    ← NUEVO
    └── README.md                        ← NUEVO
```

---

## 5. Tasks Detalladas

---

### TASK 3-1 — Crear Fixtures de Proyectos

**Fase:** FASE 3  
**Dependencias:** FASE 1 y 2 cerradas  
**Rama:** `tests/fase-3-task-1-project-fixtures`

#### Objetivo
Crear 4 directorios fixture que simulen distintos tipos de proyectos sobre los cuales un usuario instalaría Cortex. Estos fixtures deben ser **mínimos pero creíbles**: no necesitan compilar ni correr, solo necesitan los archivos suficientes para que `ProjectDetector` los identifique correctamente.

#### Archivos a crear

**A. `tests/e2e/fixtures/empty-project/`**

Contenido:
- `.gitkeep` (directorio vacío, no necesita más)

Propósito: Simular un directorio completamente vacío donde el usuario quiere empezar desde cero.

**B. `tests/e2e/fixtures/vite-react-project/`**

Contenido:
- `package.json`:
  ```json
  {
    "name": "vite-react-fixture",
    "private": true,
    "version": "0.0.0",
    "type": "module",
    "scripts": {
      "dev": "vite",
      "build": "vite build"
    },
    "dependencies": {
      "react": "^18.0.0",
      "react-dom": "^18.0.0"
    },
    "devDependencies": {
      "vite": "^5.0.0"
    }
  }
  ```
- `vite.config.js`:
  ```js
  import { defineConfig } from 'vite'
  import react from '@vitejs/plugin-react'
  export default defineConfig({ plugins: [react()] })
  ```
- `src/main.jsx`:
  ```jsx
  import React from 'react'
  import ReactDOM from 'react-dom/client'
  import App from './App'
  ReactDOM.createRoot(document.getElementById('root')).render(<App />)
  ```

Propósito: Simular un frontend moderno. El `ProjectDetector` debe identificarlo como proyecto Node/Vite.

**C. `tests/e2e/fixtures/python-package/`**

Contenido:
- `pyproject.toml`:
  ```toml
  [project]
  name = "python-fixture"
  version = "0.1.0"
  requires-python = ">=3.10"
  ```
- `src/mypkg/__init__.py`:
  ```python
  __version__ = "0.1.0"
  ```

Propósito: Simular un paquete Python. El `ProjectDetector` debe identificarlo como proyecto Python.

**D. `tests/e2e/fixtures/legacy-cortex-project/`**

Contenido:
- `config.yaml`:
  ```yaml
  episodic:
    persist_dir: .memory/chroma
    collection_name: cortex_episodic
    embedding_model: all-MiniLM-L6-v2
    embedding_backend: onnx
  semantic:
    vault_path: vault
  retrieval:
    top_k: 5
    episodic_weight: 1.0
    semantic_weight: 1.0
  llm:
    provider: none
    model: ""
  ```
- `vault/legacy_doc.md`:
  ```markdown
  ---
  tags: [legacy, test]
  ---
  # Legacy Document
  This project uses the legacy Cortex layout.
  ```

Propósito: Simular un proyecto que ya tenía Cortex en layout legacy. El `WorkspaceLayout.discover()` debe detectar el layout legacy y mantener compatibilidad.

#### Implementación paso a paso

1. Crear el directorio `tests/e2e/fixtures/`.
2. Crear cada fixture con los archivos listados arriba.
3. Crear `tests/e2e/fixtures/__init__.py` vacío.
4. Agregar un test sanity en `tests/e2e/scenarios/test_setup_on_fixtures.py` (o en un archivo temporal) que verifique que `copy_fixture_project` puede copiar cada fixture a `tmp_path` y que los archivos existen.
5. Actualizar `tests/e2e/helpers.py` si `copy_fixture_project` necesita ajustes (ej: manejar `.gitkeep`).

#### Checklist de verificación
- [ ] `tests/e2e/fixtures/empty-project/` existe.
- [ ] `tests/e2e/fixtures/vite-react-project/` existe con `package.json`, `vite.config.js`, `src/main.jsx`.
- [ ] `tests/e2e/fixtures/python-package/` existe con `pyproject.toml`, `src/mypkg/__init__.py`.
- [ ] `tests/e2e/fixtures/legacy-cortex-project/` existe con `config.yaml` y `vault/legacy_doc.md`.
- [ ] `copy_fixture_project` puede copiar cada fixture sin errores.
- [ ] Ningún fixture contiene `node_modules`, `__pycache__`, ni archivos binarios.

---

### TASK 3-2 — Tests Parametrizados de Setup sobre Fixtures

**Fase:** FASE 3  
**Dependencias:** TASK 3-1  
**Rama:** `tests/fase-3-task-2-setup-on-vite-fixture`

#### Objetivo
Crear tests parametrizados que ejecuten `cortex setup full` y `cortex setup enterprise` sobre cada uno de los 4 fixtures, validando que el resultado sea correcto según el contexto del proyecto.

#### Archivo a crear
- `tests/e2e/scenarios/test_setup_on_fixtures.py`

#### Implementación paso a paso

**TestSetupOnFixtures** (clase con `@pytest.mark.e2e`):

Metodos:

1. `test_setup_full_on_all_projects(self, fixture_name, tmp_path)`
   - Decorador: `@pytest.mark.parametrize("fixture_name", ["empty-project", "vite-react-project", "python-package", "legacy-cortex-project"])`
   - Para cada fixture:
     a. Copiar el fixture a `tmp_path / "project"`.
     b. Ejecutar `cortex setup full --git-depth 0` en ese directorio.
     c. Verificar returncode 0.
     d. Verificar que `.cortex/` exista.
     e. Verificar que `config.yaml` sea válido.
     f. Verificar que `.github/workflows/` exista (si el fixture no es legacy; en legacy verificar compatibilidad).

2. `test_setup_enterprise_on_all_projects(self, fixture_name, tmp_path)`
   - Similar al anterior pero ejecutando `cortex setup enterprise --preset small-company --non-interactive`.
   - Verificar que `.cortex/org.yaml` exista y sea válido en todos los casos.
   - Verificar que `.cortex/vault-enterprise/` exista.

3. `test_legacy_project_maintains_layout(self, tmp_path)`
   - Especifico para `legacy-cortex-project`.
   - Copiar el fixture.
   - Ejecutar `cortex setup full --git-depth 0`.
   - Verificar que el `config.yaml` legacy original NO haya sido sobreescrito sin backup (si el setup hace backup, verificar que exista).
   - Verificar que `vault/legacy_doc.md` siga existiendo.
   - Verificar que el layout detectado sea legacy o que haya migración documentada.

4. `test_doctor_passes_on_all_fixtures(self, fixture_name, tmp_path)`
   - Parametrizado sobre los 4 fixtures.
   - Copiar, ejecutar `cortex setup full`, luego `cortex doctor`.
   - Verificar returncode 0.

#### Checklist de verificación
- [ ] `test_setup_full_on_all_projects` pasa para los 4 fixtures.
- [ ] `test_setup_enterprise_on_all_projects` pasa para los 4 fixtures.
- [ ] `test_legacy_project_maintains_layout` confirma compatibilidad hacia atrás.
- [ ] `test_doctor_passes_on_all_fixtures` pasa para los 4 fixtures.
- [ ] Los tests son rápidos (sin instalación real de npm ni pip en los fixtures).

---

### TASK 3-3 — Docker Smoke Test

**Fase:** FASE 3  
**Dependencias:** TASK 3-2  
**Rama:** `tests/fase-3-task-3-docker-smoke-test`

#### Objetivo
Crear un Dockerfile y script de entrada que simulen a un usuario completamente nuevo en una máquina limpia. El contenedor debe instalar Cortex desde el código fuente actual y ejecutar un flujo mínimo de validación.

#### Archivos a crear

**A. `tests/smoke/Dockerfile.smoke`**

> **CORRECCIÓN P8:** El Dockerfile original tenía una inconsistencia de paths: `WORKDIR /app` pero el código en `/cortex-src` y el ENTRYPOINT apuntaba a `/app/entrypoint.sh` que nunca se copiaba allí. Usar el Dockerfile corregido a continuación:

```dockerfile
FROM python:3.11-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

# Copiar el repo completo (incluyendo .git/ para que git funcione)
COPY . /cortex-src

# Establecer workdir sobre el codigo fuente
WORKDIR /cortex-src

# Instalar Cortex en modo editable con dependencias de desarrollo
RUN pip install --no-cache-dir -e ".[dev]"

# Marcar el entrypoint como ejecutable
RUN chmod +x tests/smoke/entrypoint.sh

ENTRYPOINT ["tests/smoke/entrypoint.sh"]
```

**B. `tests/smoke/entrypoint.sh`**

Script bash que ejecute:
1. Activar `set -euo pipefail` al inicio para que cualquier fallo detenga el script.
2. Crear un proyecto de prueba: `mkdir /tmp/test-project && cd /tmp/test-project`
3. `git init && git config user.name "Smoke" && git config user.email "smoke@test.com"`
4. `cortex setup agent --git-depth 5 --ide pi`  ← **CORRECTO: evita prompts interactivos**
5. `cortex doctor`
6. `cortex setup full --git-depth 5`
7. `cortex setup enterprise --preset small-company --non-interactive`
8. `cortex remember "Smoke test memory" --tag smoke`
9. `cortex search "smoke test"`
10. `cortex memory-report --json`
11. `cortex pr-context capture --title "Smoke PR" --output /tmp/pr.json`
12. Verificar que `/tmp/pr.json` exista: `test -f /tmp/pr.json || exit 1`

> **NOTA:** NO usar `cortex init` en el smoke test. Es un alias que lanza prompts interactivos. Usar `cortex setup agent --git-depth 5 --ide pi` que es equivalente sin bloqueos.

**C. `tests/smoke/README.md`**

Documentación:
- Título: Cortex Smoke Test
- Requisitos: Docker instalado.
- Comando para construir: `docker build -f tests/smoke/Dockerfile.smoke -t cortex-smoke .`
- Comando para correr: `docker run --rm cortex-smoke`
- Qué hace: instala cortex desde cero y ejecuta flujo completo.
- Cómo interpretar resultados: si el contenedor termina con exit 0, el smoke pasó. Si termina con otro código, revisar los logs.

#### Implementación paso a paso

1. Crear directorio `tests/smoke/`.
2. **Crear `.dockerignore` en la raíz del repo** (si no existe) para reducir el contexto de build:
   ```
   # .dockerignore
   .venv/
   venv/
   node_modules/
   .pytest_cache/
   __pycache__/
   *.egg-info/
   .mypy_cache/
   .ruff_cache/
   dist/
   build/
   ```
   Sin este archivo, `COPY . /cortex-src` copiaría `.venv/` (que puede pesar cientos de MB) e innumerables artefactos innecesarios, haciendo el build exponencialmente más lento.
3. Crear `Dockerfile.smoke` con las instrucciones detalladas.
4. Crear `entrypoint.sh` con `set -euo pipefail` al inicio.
5. Crear `README.md`.
6. Probar localmente:
   ```bash
   docker build -f tests/smoke/Dockerfile.smoke -t cortex-smoke .
   docker run --rm cortex-smoke
   ```
7. Si falla, iterar. Documentar cualquier ajuste necesario en el Dockerfile.

#### Consideraciones importantes
- El `COPY . /cortex-src` copiará todo el repo, incluyendo `.git/`. Esto es necesario para que `cortex setup full` funcione correctamente con git. El `.dockerignore` mitiga el impacto excluyendo artefactos del entorno de desarrollo (`.venv/`, etc.).
- En CI (GitHub Actions), se puede agregar un job opcional que corra el smoke test.
- El `Dockerfile.smoke` en `tests/smoke/` no afecta builds de producción ya que no es el `Dockerfile` raíz.

#### Checklist de verificación
- [ ] `docker build` completa sin errores.
- [ ] `docker run` termina con exit code 0.
- [ ] Todos los comandos del flujo se ejecutan sin prompts interactivos.
- [ ] El output de `cortex memory-report --json` es JSON válido.
- [ ] `/tmp/pr.json` existe y contiene `"title": "Smoke PR"`.

---

## 6. Riesgos y Mitigaciones de la Fase

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| Docker no está disponible en la máquina del dev | Media | Bajo | Es un test complementario. Las FASES 1 y 2 son suficientes para beta. |
| El Dockerfile copia archivos innecesarios y es lento | Media | Bajo | Usar `.dockerignore` o copiar solo lo necesario (`cortex/`, `pyproject.toml`, `tests/smoke/`). |
| ONNX tarda mucho en inicializar dentro del contenedor | Media | Medio | El smoke test puede usar `CORTEX_ENV=sandbox` y mocks si es necesario, o aceptar el tiempo extra. |
| El fixture de Vite requiere `node` para ser realista | Baja | Medio | No se ejecuta `npm install`; solo se valida la estructura de archivos. |

---

## 7. Notas para el Agente Ejecutor

- Los fixtures deben ser **estáticos**: no generarlos dinámicamente en cada test. Deben commitearse al repo como archivos reales.
- Mantener los fixtures mínimos: un `package.json` de 20 líneas es suficiente; no incluir `node_modules` ni lockfiles.
- El Dockerfile smoke es la prueba de fuego final. Si no construye, no bloquea la FASE 3 como gate duro, pero debe documentarse el porqué.
- Al finalizar la fase, ejecutar `pytest tests/e2e/scenarios/test_setup_on_fixtures.py -v` y `docker build ...`.
