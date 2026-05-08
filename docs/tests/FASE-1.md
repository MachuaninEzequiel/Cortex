# FASE 1 — "No podemos romper lo básico"

**Documento padre:** `docs/tests/PLAN-GLOBAL.md`  
**Fecha:** 2026-05-08  
**Estado:** Planificación detallada — listo para ejecución  
**Semáforo:** 🔴 Rojo (bloqueante para beta)

---

## 1. Resumen Ejecutivo

Esta fase implementa el **E2E Scenario Runner** con pytest. El objetivo es cubrir los flujos que un usuario beta tocará en sus primeros 5 minutos con Cortex. Si alguno de estos flujos falla, la experiencia beta se rompe irremediablemente.

Los 5 escenarios críticos son:
1. **Setup básico** (`cortex setup agent --git-depth 5 --ide pi` → `cortex doctor`)
2. **Setup full** (`cortex setup full --git-depth 5`)
3. **Setup enterprise non-interactive** (`cortex setup enterprise --preset small-company --non-interactive` → `cortex memory-report`)
4. **Ciclo de vida de memoria** (`cortex remember` → `cortex search` → `cortex sync-vault`)
5. **Pipeline PR/DevSecDocOps** (`cortex pr-context full`)

---

## 2. Gate de Entrada

- [ ] El PLAN-GLOBAL está aprobado y commiteado en `main`.
- [ ] Los tests unitarios e integración existentes pasan (`pytest tests/unit tests/integration`).
- [ ] `cortex` está instalado editable en el entorno de desarrollo (`pip install -e ".[dev]"`).

---

## 3. Gate de Salida (Definition of Done)

- [ ] Los 6 archivos de test en `tests/e2e/scenarios/` y el job de CI existen y pasan.
- [ ] Los helpers `tests/e2e/helpers.py` existen y son usados por al menos 3 tests.
- [ ] Las fixtures de pytest en `tests/e2e/conftest.py` existen y funcionan.
- [ ] `pytest tests/e2e/scenarios/ -m e2e` pasa en local.
- [ ] `pytest tests/e2e/scenarios/ -m e2e` pasa en CI (job de GitHub Actions creado en TASK 1-6).
- [ ] Los tests E2E están marcados con `@pytest.mark.e2e`.
- [ ] Los tests no escriben nunca fuera de `tmp_path`.
- [ ] Se documenta en `tests/e2e/README.md` cómo correr los tests E2E.

---

## 4. Estructura de Archivos

```
tests/
├── conftest.py                          ← MODIFICAR: agregar markers
├── e2e/
│   ├── __init__.py                      ← EXISTENTE
│   ├── conftest.py                      ← NUEVO: fixtures neutrales (sin autouse de install)
│   ├── helpers.py                       ← NUEVO
│   ├── README.md                        ← NUEVO
│   ├── scenarios/
│   │   ├── __init__.py                  ← NUEVO: necesario para imports entre módulos
│   │   ├── conftest.py                  ← NUEVO: cortex_install autouse=True (solo aquí)
│   │   ├── test_setup_basic.py
│   │   ├── test_setup_full.py
│   │   ├── test_enterprise_setup.py
│   │   ├── test_memory_lifecycle.py
│   │   └── test_pr_devsecdocops.py
│   └── test_artefact_integrity.py       ← NUEVO (FASE 2): NO necesita cortex instalado
```

---

## 5. Tasks Detalladas

---

### TASK 1-1 — Infraestructura del Scenario Runner

**Fase:** FASE 1  
**Dependencias:** Ninguna  
**Rama:** `tests/fase-1-task-1-scenario-runner-infrastructure`

#### Objetivo
Crear la infraestructura compartida que todos los tests E2E usaran: helpers, fixtures, markers, y utilidades de validación.

#### Archivos a crear/modificar
- `pyproject.toml` — agregar markers pytest
- `tests/e2e/conftest.py` — crear (fixtures neutrales: `e2e_project_dir`, `isolated_git_repo`, `cortex_install` no-autouse)
- `tests/e2e/scenarios/__init__.py` — crear (archivo vacío, habilita imports entre módulos)
- `tests/e2e/scenarios/conftest.py` — crear (solo `cortex_install` autouse=True para escenarios)
- `tests/e2e/helpers.py` — crear
- `tests/e2e/README.md` — crear

#### Implementación paso a paso

**Paso 1 — Registrar markers en pyproject.toml**

Bajo `[tool.pytest.ini_options]`, agregar:
```toml
markers = [
    "e2e: marks tests as end-to-end (deselect with '-m not e2e')",
    "smoke: marks tests as smoke tests (slow, run nightly)",
    "artefact: marks tests as artefact integrity checks",
    "slow: marks tests as slow (ONNX real o red, excluir en CI rápido)",
]
```

**Paso 2 — Crear tests/e2e/helpers.py**

Funciones requeridas:
- `run_cortex(cwd, *args, check=True, timeout=60, env=None) -> CompletedProcess`
  - Siempre setea `CORTEX_ENV=sandbox` en env.
  - Usa `sys.executable` para invocar cortex como modulo si el binario no esta disponible.
  - Ejemplo: primero intenta `cortex` en PATH; si falla, usa `python -m cortex.cli.main`.
  - Captura stdout y stderr como texto.
  - Si `check=True` y returncode != 0, lanza `subprocess.CalledProcessError`.
- `assert_valid_config_yaml(path: Path) -> None`
  - Lee YAML con `yaml.safe_load`.
  - Valida con `CortexConfig.model_validate`.
  - Si falla, raise AssertionError con el mensaje de Pydantic.
- `assert_valid_org_yaml(path: Path) -> None`
  - Similar pero con `EnterpriseOrgConfig.model_validate`.
- `count_chroma_documents(persist_dir: Path, collection_name="cortex_episodic") -> int`
  - Importa `chromadb` (ya es dependencia del proyecto).
  - **IMPORTANTE:** Usar la API moderna: `chromadb.PersistentClient(path=str(persist_dir))`.
  - NO usar `chromadb.Client(Settings(persist_directory=...))` — es la API deprecada de ChromaDB < 0.4, incompatible con `>=0.5`.
  - Obtiene o crea la collection con `client.get_or_create_collection(collection_name)` y retorna `collection.count()`.
  - Si la coleccion no existe o el directorio está vacío, retorna 0 (no lanzar excepcion).
- `assert_vault_has_documents(vault_path: Path, min_count: int = 1) -> None`
  - Lista `vault_path.rglob("*.md")`.
  - Si la cantidad es menor a `min_count`, raise AssertionError.

**Paso 3 — Crear tests/e2e/conftest.py** (fixtures neutrales, sin autouse de instalación)

Este archivo define fixtures que son útiles para TODOS los tests de `tests/e2e/`, incluyendo los tests de artefactos (FASE 2) que **no necesitan que cortex esté instalado**. Por eso, `cortex_install` es NO-autouse aquí.

Fixtures requeridas:
- `e2e_project_dir(tmp_path: Path, monkeypatch) -> Path`
  - Crea `tmp_path / "project"`.
  - Setea `CORTEX_ENV=sandbox` via `monkeypatch.setenv`.
  - Cambia el working dir al project con `monkeypatch.chdir`.
  - Retorna el path del proyecto.
- `isolated_git_repo(e2e_project_dir: Path) -> Path`
  - Ejecuta `git init` en `e2e_project_dir`.
  - Configura `user.name` y `user.email`.
  - **Crea un commit vacío inicial: `git commit --allow-empty -m "init"`.**
  - Esto es **obligatorio** (no opcional) para que `--git-depth 5` no falle cuando no existen commits en el repo.
  - Retorna el mismo path.
- `cortex_install()` (session-scoped, **autouse=False** — declarar explícitamente solo donde se necesite)
  - Verifica que `cortex --version` funcione.
  - Si falla, llama `pytest.skip("cortex not installed")`.
  - **NO es autouse** porque los tests de artefactos de FASE 2 no necesitan cortex instalado.
  - Los tests que ejecuten `run_cortex()` deben declararla explícitamente como argumento.

**Paso 3b — Crear tests/e2e/scenarios/conftest.py** (autouse de instalación solo para escenarios)

Este archivo existe únicamente para activar `cortex_install` como autouse dentro del subdirectorio `scenarios/`. Al estar en `scenarios/conftest.py`, su scope de autouse se limita a los tests de ese directorio sin afectar `test_artefact_integrity.py`.

```python
import pytest

@pytest.fixture(scope="session", autouse=True)
def _require_cortex_installed(cortex_install):
    """Auto-activa la verificación de cortex para todos los tests de scenarios/.
    
    Los tests de artefactos (tests/e2e/test_artefact_integrity.py) no están bajo
    scenarios/ y no son afectados por este autouse.
    """
    pass  # cortex_install ya hace el skip si no está instalado
```

**Paso 3c — Crear tests/e2e/scenarios/__init__.py**

Archivo vacío. Necesario para que `from tests.e2e.scenarios import ...` funcione si algún helper necesita importar algo entre módulos.

> **Mejora C — Reutilizar MockEmbedder existente:**  
> El `tests/conftest.py` raíz ya tiene `MockEmbedder` implementado con bag-of-words determinista.  
> En `tests/e2e/conftest.py`, importar directamente: `from tests.conftest import MockEmbedder`  
> No crear una nueva implementación — reusar evita divergencia entre tests unitarios y E2E.

**Paso 4 — Crear tests/e2e/README.md**

Contenido minimo:
- Titulo: Cortex E2E Tests
- Como correr todos los E2E: `pytest tests/e2e/scenarios/ -m e2e -v`
- Como correr excluyendo E2E: `pytest -m "not e2e"`
- Como correr solo artefactos (sin cortex instalado): `pytest tests/e2e/test_artefact_integrity.py -m artefact -v`
- Como correr un escenario especifico: `pytest tests/e2e/scenarios/test_setup_basic.py -v`
- Requisitos para E2E: tener cortex instalado en el entorno (`pip install -e ".[dev]"`).
- Requisitos para artefactos: solo el repo clonado, sin instalación adicional.

#### Checklist de verificación
- [ ] `pyproject.toml` tiene los 4 markers definidos (`e2e`, `smoke`, `artefact`, `slow`).
- [ ] `tests/e2e/helpers.py` existe y cada funcion tiene docstring.
- [ ] `count_chroma_documents` usa `chromadb.PersistentClient(path=...)` (no la API deprecada).
- [ ] `tests/e2e/conftest.py` existe con `cortex_install` como **non-autouse**.
- [ ] `tests/e2e/scenarios/conftest.py` existe con el wrapper `_require_cortex_installed` autouse=True.
- [ ] `tests/e2e/scenarios/__init__.py` existe (puede estar vacío).
- [ ] `isolated_git_repo` crea un commit vacío inicial (`git commit --allow-empty -m "init"`).
- [ ] Verificar el scope: `pytest tests/e2e/test_artefact_integrity.py` NO requiere cortex instalado.
- [ ] Verificar el scope: `pytest tests/e2e/scenarios/` hace skip si cortex no está instalado.
- [ ] `run_cortex` funciona en el repo actual (ejecutar `run_cortex(Path.cwd(), "--version")` y verificar que retorne codigo 0).
- [ ] `assert_valid_config_yaml` valida correctamente un `config.yaml` generado por el setup.
- [ ] `count_chroma_documents` retorna 0 en un directorio vacio y no crashea.
- [ ] `MockEmbedder` importado desde `tests/conftest.py` (no duplicado).

---

### TASK 1-2 — Setup Básico y Setup Full

**Fase:** FASE 1  
**Dependencias:** TASK 1-1  
**Rama:** `tests/fase-1-task-2-setup-basic-workflow`

#### Objetivo
Testear los comandos `cortex setup agent` y `cortex setup full` en un proyecto vacio, validando que generen la estructura de archivos correcta y que `cortex doctor` apruebe el resultado.

> **ADVERTENCIA — P3 (Bug Crítico resuelto):** `cortex init` es un alias de `cortex setup agent` que lanza prompts interactivos bloqueantes (git-depth e IDE) si no se pasan por flags. NUNCA usar `cortex init` sin argumentos en tests E2E o el subprocess quedará colgado esperando input. Usar **siempre** `cortex setup agent --git-depth 5 --ide pi`.

> **VERIFICACIóN PREVIA — P4:** Antes de hardcodear los asserts de estructura de `.cortex/`, ejecutar manualmente `cortex setup agent --git-depth 5 --ide pi` en un tmp dir y hacer `tree .cortex` para confirmar la estructura real generada por el orchestrator. Los asserts deben reflejar esa estructura real, no una asumida.

#### Archivos a crear
- `tests/e2e/scenarios/test_setup_basic.py`
- `tests/e2e/scenarios/test_setup_full.py`

#### Implementación paso a paso

**TestSetupBasic** (en `test_setup_basic.py`):

Clase de test con `@pytest.mark.e2e`.

Metodos:
1. `test_agent_setup_creates_workspace(self, e2e_project_dir)`
   - Ejecuta `cortex setup agent --git-depth 5 --ide pi` en `e2e_project_dir`.
   - Verifica que existan (estructura confirmada contra orchestrator real):
     - `.cortex/`
     - `.cortex/config.yaml`
     - `.cortex/vault/`
     - `.cortex/workspace.yaml` (con `layout_version: 2`)
     - `.cortex/AGENT.md`
   - Verifica que `config.yaml` sea valido con `assert_valid_config_yaml`.

2. `test_doctor_passes_after_agent_setup(self, e2e_project_dir)`
   - Precondicion: `cortex setup agent --git-depth 5 --ide pi` ya corrio.
   - Ejecuta `cortex doctor`.
   - Verifica que returncode sea 0.
   - Verifica que stdout contenga `[OK]` para las checks principales.

3. `test_doctor_strict_passes_after_agent_setup(self, e2e_project_dir)`
   - Precondicion: `cortex setup agent --git-depth 5 --ide pi` ya corrio.
   - Ejecuta `cortex doctor --strict`.
   - Verifica que returncode sea 0.
   - **Este test valida el criterio de aceptación global**: si falla, significa que hay warnings en el setup que deben corregirse antes de beta.

4. `test_agent_setup_is_idempotent(self, e2e_project_dir)`
   - Ejecuta `cortex setup agent --git-depth 5 --ide pi` dos veces.
   - Verifica que no falle la segunda vez (returncode 0).
   - Verifica que archivos existentes no se hayan sobreescrito (comparar contenido clave).

**TestSetupFull** (en `test_setup_full.py`):

Clase de test con `@pytest.mark.e2e`.

Metodos:
1. `test_full_setup_generates_workflows(self, isolated_git_repo)`
   - Precondicion: repo git inicializado.
   - Ejecuta `cortex setup full --git-depth 5`.
   - Verifica que existan:
     - `.github/workflows/ci-pull-request.yml`
     - `.github/workflows/ci-feature.yml`
     - `.github/workflows/cd-deploy.yml`
   - Verifica que cada workflow sea YAML parseable.

2. `test_full_setup_generates_scripts(self, isolated_git_repo)`
   - Verifica que exista `.cortex/scripts/devsecdocops.sh`.
   - Verifica que tenga permisos de ejecucion (en POSIX).

3. `test_full_setup_generates_skills(self, isolated_git_repo)`
   - Verifica que existan al menos:
     - `.cortex/skills/obsidian-markdown/SKILL.md`
     - `.cortex/skills/json-canvas/`
   - Verifica que los skills no esten vacios.

4. `test_full_setup_generates_agent_files(self, isolated_git_repo)`
   - Verifica que existan:
     - `.cortex/AGENT.md`
     - `.cortex/skills/cortex-sync.md`
     - `.cortex/skills/cortex-SDDwork.md`
     - `.cortex/subagents/cortex-documenter.md`

#### Checklist de verificación
- [ ] La estructura real de `.cortex/` fue verificada manualmente antes de implementar los asserts.
- [ ] `test_setup_basic.py` tiene los 4 metodos descritos (incluyendo `--strict`) y pasan.
- [ ] `test_setup_full.py` tiene los 4 metodos descritos y pasan.
- [ ] Ningún test usa `cortex init` sin argumentos — todos usan `cortex setup agent --git-depth 5 --ide pi`.
- [ ] Cada test usa `e2e_project_dir` o `isolated_git_repo` y no escribe fuera de `tmp_path`.
- [ ] `pytest tests/e2e/scenarios/test_setup_basic.py -v` pasa.
- [ ] `pytest tests/e2e/scenarios/test_setup_full.py -v` pasa.

---

### TASK 1-3 — Ciclo de Vida de Memoria

**Fase:** FASE 1  
**Dependencias:** TASK 1-1  
**Rama:** `tests/fase-1-task-3-memory-lifecycle`

#### Objetivo
Testear que la memoria episodica y semantica funcionen end-to-end: recordar, buscar, y sincronizar el vault.

#### Archivo a crear
- `tests/e2e/scenarios/test_memory_lifecycle.py`

#### Implementación paso a paso

**TestMemoryLifecycle** (clase con `@pytest.mark.e2e`):

Metodos:
1. `test_remember_creates_episodic_entry(self, e2e_project_dir)`
   - Precondicion: `cortex setup agent --git-depth 5 --ide pi` ejecutado.
   - Ejecuta: `cortex remember "Test content about authentication" --tag auth --tag test`
   - Verifica que returncode sea 0.
   - Verifica que stdout contenga un ID tipo `mem_`.
   - Opcional: verificar que ChromaDB tenga 1 documento con `count_chroma_documents`.

2. `test_search_finds_remembered_content(self, e2e_project_dir)`
   - Precondicion: `cortex remember` ya ejecutado con contenido sobre "authentication".
   - Ejecuta: `cortex search "authentication" --top-k 5`
   - Verifica que returncode sea 0.
   - Verifica que stdout contenga el contenido recordado o el ID de memoria.

3. `test_sync_vault_indexes_markdown(self, e2e_project_dir)`
   - Precondicion: `cortex setup agent --git-depth 5 --ide pi` ejecutado.
   - Crear un archivo markdown manualmente en `.cortex/vault/sessions/test.md` con frontmatter:
     ```yaml
     ---
     tags: [test, session]
     timestamp: "2026-05-08T00:00:00"
     ---
     # Test Session
     Content about testing strategies.
     ```
   - Ejecuta: `cortex sync-vault`
   - Verifica que returncode sea 0.
   - Verifica que stdout indique que indexo al menos 1 documento.
   - Verifica que `count_chroma_documents` haya aumentado.

4. `test_search_finds_vault_content(self, e2e_project_dir)`
   - Precondicion: `cortex sync-vault` ya ejecutado con el markdown de testing.
   - Ejecuta: `cortex search "testing strategies"`
   - Verifica que stdout contenga "Test Session" o una referencia al vault.

#### Nota sobre mocks
- Para evitar lentitud de ONNX en cada test, estos tests pueden mockear el embedder usando `monkeypatch` en `conftest.py` a nivel de modulo.
- Alternativa: marcar con `@pytest.mark.slow` y usar ONNX real. Recomendacion: usar mock para velocidad, pero tener un test opcional con ONNX real marcado `slow`.

#### Checklist de verificación
- [ ] Los 4 metodos de `test_memory_lifecycle.py` pasan.
- [ ] `cortex remember` retorna un ID de memoria valido.
- [ ] `cortex search` encuentra contenido tanto episodico como semantico.
- [ ] `cortex sync-vault` indexa markdown del vault.
- [ ] Los tests son rapidos (< 5s cada uno) gracias al mock del embedder.

---

### TASK 1-4 — Setup Enterprise Non-Interactive

**Fase:** FASE 1  
**Dependencias:** TASK 1-1  
**Rama:** `tests/fase-1-task-4-enterprise-noninteractive`

#### Objetivo
Testear que `cortex setup enterprise` funcione en modo no-interactivo para todos los presets, y que `cortex memory-report` y `cortex doctor --scope enterprise` validen la configuracion generada.

#### Archivo a crear
- `tests/e2e/scenarios/test_enterprise_setup.py`

#### Implementación paso a paso

**TestEnterpriseSetup** (clase con `@pytest.mark.e2e`):

Metodos:
1. `test_enterprise_setup_small_company(self, e2e_project_dir)`
   - Ejecuta `cortex setup agent --git-depth 5 --ide pi` primero (prerrequisito de base).
   - Luego ejecuta: `cortex setup enterprise --preset small-company --non-interactive`
   - Verifica returncode 0.
   - Verifica que exista `.cortex/org.yaml`.
   - Verifica que `org.yaml` sea valido con `assert_valid_org_yaml`.
   - Verifica que exista `.cortex/vault-enterprise/`.

2. `test_enterprise_setup_multi_project_team(self, e2e_project_dir)`
   - Similar al anterior pero con `--preset multi-project-team`.
   - Verifica que `org.yaml` contenga `profile: multi-project-team`.

3. `test_enterprise_setup_regulated_organization(self, e2e_project_dir)`
   - Similar con `--preset regulated-organization`.
   - Verifica que `branch_isolation_enabled: true` este presente en la config.

4. `test_memory_report_after_enterprise_setup(self, e2e_project_dir)`
   - Precondicion: enterprise setup ya ejecutado.
   - Ejecuta: `cortex memory-report --json`
   - Verifica returncode 0.
   - Captura stdout y parsea como JSON.
   - **IMPORTANTE (P2):** Verificar las claves reales ejecutando este comando manualmente antes de implementar el test. Las claves esperadas (a confirmar) son:
     - `project_root`
     - `enterprise_enabled`
     - `sources` (lista)
     - `promotion` (objeto)
   - Si el modelo Pydantic usa nombres distintos, actualizar los asserts.

5. `test_doctor_enterprise_scope(self, e2e_project_dir)`
   - Precondicion: enterprise setup ejecutado.
   - Ejecuta: `cortex doctor --scope enterprise`
   - Verifica returncode 0.
   - Verifica que stdout contenga checks de enterprise (vault-enterprise, org.yaml, etc.).

#### Checklist de verificación
- [ ] Las claves reales de `cortex memory-report --json` fueron verificadas manualmente antes de implementar.
- [ ] Los 5 metodos pasan.
- [ ] Cada preset genera un `org.yaml` Pydantic-valido.
- [ ] `cortex memory-report --json` produce JSON parseable con la estructura esperada.
- [ ] `cortex doctor --scope enterprise` no reporta FAIL en un proyecto sano.

---

### TASK 1-5 — Pipeline PR / DevSecDocOps

**Fase:** FASE 1  
**Dependencias:** TASK 1-1  
**Rama:** `tests/fase-1-task-5-pr-devsecdocops`

#### Objetivo
Testear el comando `cortex pr-context full` end-to-end, validando que genere documentacion en el vault y persista metadata en memoria episodica.

#### Archivo a crear
- `tests/e2e/scenarios/test_pr_devsecdocops.py`

#### Implementación paso a paso

**TestPrDevSecDocOps** (clase con `@pytest.mark.e2e`):

Metodos:
1. `test_pr_context_full_generates_docs(self, e2e_project_dir)`
   - Precondicion: `cortex setup agent --git-depth 5 --ide pi` ejecutado.
   - Ejecuta:
     ```
     cortex pr-context full \
       --title "Test PR" \
       --body "Testing the DevSecDocOps pipeline" \
       --author "tester" \
       --branch "feature/test" \
       --commit "abc123" \
       --pr-number 42 \
       --vault .cortex/vault
     ```
   - Verifica returncode 0.
   - Verifica que se hayan generado documentos en `.cortex/vault/` (usar `assert_vault_has_documents`).
   - Verifica que stdout contenga "DevSecDocOps pipeline complete".

2. `test_pr_context_full_stores_in_memory(self, e2e_project_dir)`
   - Precondicion: `cortex setup agent --git-depth 5 --ide pi` y `cortex pr-context full` ya ejecutados.
   - Ejecuta: `cortex search "Test PR"`
   - Verifica que stdout contenga referencia al PR #42 o al autor "tester".

3. `test_pr_context_capture_standalone(self, e2e_project_dir)`
   - Ejecuta solo `cortex pr-context capture --title "Standalone" --output .pr-context.json`.
   - Verifica que `.pr-context.json` exista y sea JSON parseable.
   - Verifica que contenga `"title": "Standalone"`.

#### Checklist de verificación
- [ ] Los 3 metodos pasan.
- [ ] `cortex pr-context full` genera documentos en el vault.
- [ ] `cortex search` encuentra el PR almacenado.
- [ ] `cortex pr-context capture` genera JSON valido.

---

### TASK 1-6 — Integración CI (GitHub Actions)

**Fase:** FASE 1  
**Dependencias:** TASK 1-2, 1-3, 1-4, 1-5 (todas las tasks de escenarios terminadas)  
**Rama:** `tests/fase-1-task-6-ci-integration`

#### Objetivo
Garantizar que la suite E2E corra en CI de forma automática en cada PR y push a `main`. Sin este job, los tests solo existen localmente y no dan garantía de integración continua.

#### Archivos a crear/modificar
- `.github/workflows/ci-e2e.yml` — job dedicado para los tests E2E

#### Implementación paso a paso

**Paso 1 — Crear `.github/workflows/ci-e2e.yml`**

```yaml
name: CI - E2E Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  e2e:
    name: End-to-End Tests
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install Cortex (editable + dev deps)
        run: pip install -e ".[dev]"

      - name: Run E2E tests
        run: pytest tests/e2e/scenarios/ -m e2e --tb=short -q
        env:
          CORTEX_ENV: sandbox

      - name: Run Artefact Integrity tests
        run: pytest tests/e2e/test_artefact_integrity.py -m artefact --tb=short -q
        env:
          CORTEX_ENV: sandbox
```

**Paso 2 — Verificar que el job excluye tests `slow`**
- Los tests marcados `@pytest.mark.slow` no corren en CI con el comando de arriba.
- Para habilitarlos en un job nocturno, crear un workflow separado con `pytest -m slow`.

**Paso 3 — Verificar que el job falla si cualquier test E2E falla**
- Si `pytest` retorna != 0, el job debe fallar y bloquear el merge.

#### Checklist de verificación
- [ ] `.github/workflows/ci-e2e.yml` existe y el workflow es YAML válido.
- [ ] El job corre en cada PR y push a `main` sin intervención manual.
- [ ] El job falla si algún test E2E falla.
- [ ] El job excluye tests `slow` (no hay timeout en CI por ONNX real).
- [ ] Los tests `artefact` de FASE 2 también corren en el mismo job (preparación para FASE 2).

## 6. Riesgos y Mitigaciones de la Fase

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| ChromaDB lock entre tests paralelos | Media | Alto | Cada test usa `tmp_path` distinto; ChromaDB no comparte persist_dir. |
| ONNX embedder tarda >30s en inicializar | Media | Alto | Mock del embedder en todos los tests salvo uno opcional marcado `slow`. |
| `cortex setup agent` pide git-depth o IDE de forma interactiva | Baja | Alto | **RESUELTO:** Usar siempre `--git-depth 5 --ide pi`. Nunca llamar `cortex init` sin argumentos en tests. |
| `cortex setup full` pide git-depth interactivo | Baja | Alto | Usar `--git-depth 5` en todos los tests de setup full. |
| Windows: paths con backslash rompen asserts | Media | Medio | Usar `Path` en todos los asserts; no comparar strings crudos de path. |
| `subprocess` no encuentra el binario `cortex` | Baja | Alto | `run_cortex` debe fallback a `python -m cortex.cli.main`. |
| API de ChromaDB deprecada | Baja | Alto | **RESUELTO:** Usar `chromadb.PersistentClient(path=...)` — compatible con `>=0.5`. |

---

## 7. Notas para el Agente Ejecutor

- Al implementar, seguir estrictamente el orden de tasks: 1-1 → 1-2 → 1-3 → 1-4 → 1-5 → 1-6.
- TASK 1-1 es la base: si no funciona, ninguna otra task puede avanzar.
- **NUNCA usar `cortex init` sin argumentos en tests E2E.** Siempre usar `cortex setup agent --git-depth 5 --ide pi` para evitar prompts interactivos bloqueantes.
- **NUNCA usar `cortex setup full` sin `--git-depth 5`.** Tiene el mismo problema de prompt interactivo.
- No modificar código de produccion salvo que sea absolutamente necesario (documentar en el mensaje de commit).
- Si un test requiere un fix en produccion, crear una task adicional `tests/fase-1-task-X-fix-descripcion` y documentarla.
- Al finalizar cada task, actualizar el checklist en este documento con `[x]`.
- Al finalizar la fase, ejecutar `pytest tests/e2e/scenarios/ -m e2e --tb=short` y verificar que todo pase local y en CI.
