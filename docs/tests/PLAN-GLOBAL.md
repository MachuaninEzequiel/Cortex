# Plan Global — Testing E2E & Integridad de Cortex

**Documento maestro:** `docs/tests/PLAN-GLOBAL.md`  
**Fecha:** 2026-05-08  
**Estado:** Planificación detallada — listo para ejecución  
**Versión del producto bajo test:** Cortex `v0.3.0+` (Release 2.5 / Enterprise)

---

## 1. Resumen Ejecutivo

Este plan define la estrategia completa para llevar Cortex a un estado de **confianza operativa** antes de entregarlo a usuarios beta. No se trata de reemplazar los tests unitarios e integración existentes, sino de **cubrir la brecha crítica** que hoy existe entre "los componentes funcionan aislados" y "un usuario nuevo puede instalar y usar Cortex sin errores básicos".

La brecha actual es severa:
- `tests/e2e/` existe físicamente pero solo contiene `__init__.py`.
- Los tests de integración del setup mockean `AgentMemory`, por lo que no validan la indexación real de embeddings ONNX ni la persistencia de ChromaDB.
- No hay validación de que los artefactos generados (workflows YAML, skills Markdown, configs Pi) sean coherentes entre sí.
- No hay pruebas que simulen un proyecto "externo" (Vite, Python package) sobre el cual se instala Cortex.

Este plan resuelve esas brechas en **tres fases ordenadas y acumulativas**.

---

## 2. Alcance y Límites

### Dentro del alcance
- Tests E2E con pytest que ejecuten la CLI real como subprocess.
- Validación de filesystem, archivos generados, YAML parseable, y Pydantic-válido.
- Validación de consistencia entre CLI, skills, Pi config, y MCP tools.
- Fixtures de proyectos prefabricados (vacío, Vite, Python package, legacy).
- Smoke test en Docker para validar instalación desde cero.

### Fuera del alcance
- Tests de performance o carga (no se mide latencia ni throughput).
- Tests de UI visual (WebGraph se testea solo por endpoints HTTP, no por Selenium).
- Tests que requieran API keys de OpenAI/Anthropic (se usan backends `onnx` y `none`).
- Tests que requieran GitHub real (se simulan con `git init` local).

---

## 3. Arquitectura del Plan

```
docs/tests/
├── PLAN-GLOBAL.md       ← Este archivo: visión, dependencias, progreso
├── FASE-1.md            ← "No podemos romper lo básico" (E2E Scenario Runner)
├── FASE-2.md            ← "Consistencia del ecosistema" (Artefactos + Pi + YAML)
└── FASE-3.md            ← "El usuario real en su entorno real" (Fixtures + Docker)

tests/
├── conftest.py          ← Existente — se extiende con fixtures nuevas
├── e2e/
│   ├── __init__.py      ← Existente
│   ├── scenarios/       ← NUEVO: tests de escenarios completos
│   │   ├── test_setup_basic.py
│   │   ├── test_setup_full.py
│   │   ├── test_enterprise_setup.py
│   │   ├── test_memory_lifecycle.py
│   │   └── test_pr_devsecdocops.py
│   ├── fixtures/        ← NUEVO: proyectos prefabricados
│   │   ├── empty-project/
│   │   ├── vite-react-project/
│   │   ├── python-package/
│   │   └── legacy-cortex-project/
│   └── test_artefact_integrity.py   ← NUEVO: validación de artefactos
└── smoke/
    └── Dockerfile.smoke   ← NUEVO (referenciado desde FASE-3)
```

---

## 4. Reglas de Ejecución

1. **Una fase a la vez.** No avanzar a la siguiente sin cerrar el gate de salida de la actual.
2. **Cada task se verifica con su checklist.** Si el checklist pasa, la task está done.
3. **El gate de salida de la fase = todos los checklists de sus tasks + los criterios de DoD del documento de fase.**
4. **Si una task bloquea, documentar el bloqueo en la task y no avanzar de fase.**
5. **Cada task se commitea en su propia rama** `tests/fase-N-task-M-descripcion`.
6. **Los tests nuevos deben pasar en CI** antes de mergear la fase.
7. **No se modifica código de producción** salvo que sea estrictamente necesario para hacer testeable un componente (documentar la justificación en la task).

---

## 5. Dependencias entre Fases

```
FASE 1 ──→ FASE 2 ──→ FASE 3
(🔴 Rojo)   (🟡 Amarillo)  (🟢 Verde)
```

- **FASE 1** es prerequisito de FASE 2 porque la validación de artefactos (FASE 2) asume que los flujos básicos de setup (FASE 1) ya funcionan.
- **FASE 2** es prerequisito de FASE 3 porque el smoke test Docker (FASE 3) requiere que la consistencia de artefactos esté validada.
- **FASE 3** puede ejecutarse parcialmente en paralelo con FASE 2 si FASE 1 ya está cerrada, pero el gate de salida de FASE 3 requiere que FASE 2 esté cerrada.

---

## 6. Convención de Nombres de Ramas

```
tests/fase-1-task-1-scenario-runner-infrastructure
tests/fase-1-task-2-setup-basic-workflow
tests/fase-1-task-3-memory-lifecycle
tests/fase-1-task-4-enterprise-noninteractive
tests/fase-1-task-5-pr-devsecdocops
tests/fase-1-task-6-ci-integration
tests/fase-2-task-1-pi-consistency-tests
tests/fase-2-task-2-yaml-artefact-validation
tests/fase-2-task-3-skill-frontmatter-checks
tests/fase-2-task-4-mcp-tools-cli-alignment
tests/fase-3-task-1-project-fixtures
tests/fase-3-task-2-setup-on-vite-fixture
tests/fase-3-task-3-docker-smoke-test
```

---

## 7. Infraestructura Compartida

### 7.1 Fixtures de pytest (a crear en `tests/conftest.py` o `tests/e2e/conftest.py`)

| Fixture | Alcance | Descripción |
|---------|---------|-------------|
| `cli_runner` | session | Instancia de `typer.testing.CliRunner` para tests que no necesitan subprocess. |
| `e2e_project_dir` | function | `tmp_path` + `CORTEX_ENV=sandbox` + chdir temporal. |
| `cortex_install` | session | Verifica que `cortex` esté instalado en el entorno actual (`which cortex` o `python -m cortex.cli.main`). |
| `mock_embedder_session` | session | Reutiliza el `MockEmbedder` ya existente en `tests/conftest.py` (bag-of-words determinista). No crear uno nuevo — importar desde el conftest raíz para evitar divergencia. |
| `isolated_git_repo` | function | `tmp_path` con `git init` + `git config user.name/email`. |

### 7.2 Helpers compartidos (a crear en `tests/e2e/helpers.py`)

| Helper | Firma | Descripción |
|--------|-------|-------------|
| `run_cortex` | `(cwd: Path, *args: str, check=True, timeout=30) -> subprocess.CompletedProcess` | Ejecuta `cortex <args>` en `cwd` con `CORTEX_ENV=sandbox`. Captura stdout/stderr. |
| `assert_valid_config_yaml` | `(path: Path) -> None` | Parsea el YAML y valida contra `CortexConfig` de Pydantic. |
| `assert_valid_org_yaml` | `(path: Path) -> None` | Parsea el YAML y valida contra `EnterpriseOrgConfig`. |
| `copy_fixture_project` | `(fixture_name: str, dest: Path) -> Path` | Copia `tests/e2e/fixtures/<fixture_name>/` a `dest`. |
| `count_chroma_documents` | `(persist_dir: Path) -> int` | Abre ChromaDB con `chromadb.PersistentClient(path=str(persist_dir))` (API >= 0.5). Cuenta documentos en la collection default. Retorna 0 si no existe. |
| `assert_vault_has_documents` | `(vault_path: Path, min_count: int = 1) -> None` | Lista archivos `.md` recursivamente. |

### 7.3 Marcar tests E2E

Usar el marker de pytest:

```python
# pytest.ini o pyproject.toml
[tool.pytest.ini_options]
markers = [
    "e2e: marks tests as end-to-end (deselect with '-m not e2e')",
    "smoke: marks tests as smoke tests (slow, run nightly)",
    "artefact: marks tests as artefact integrity checks",
    "slow: marks tests as slow (ONNX real o red, excluir en CI rápido)",
]
```

Esto permite:
- Correr solo unitarios: `pytest -m "not e2e"`
- Correr solo E2E: `pytest -m e2e`
- Correr smoke: `pytest -m smoke`
- Excluir tests lentos: `pytest -m "not slow"`

---

## 8. Progreso Global

| Fase | Nombre | Semáforo | Estado | Tasks | Hechas |
|------|--------|----------|--------|-------|--------|
| FASE 1 | E2E Scenario Runner | 🔴 Rojo | ✅ COMPLETADA | 6 | 6 |
| FASE 2 | Consistencia del Ecosistema | 🟡 Amarillo | ✅ COMPLETADA | 4 | 4 |
| FASE 3 | Usuario Real + Docker | 🟢 Verde | ✅ COMPLETADA* | 3 | 3 |

**Total: 13 tasks**

\* FASE 3: Docker smoke test creado pero no validado localmente (Docker no disponible).

---

## 9. Cómo Leer y Usar Este Plan

1. Abrir el documento `FASE-N.md` correspondiente a la fase actual.
2. Verificar que el gate de entrada se cumple (FASE anterior cerrada, o es la FASE 1).
3. Ejecutar las tasks en orden numérico.
4. Para cada task: leer su objetivo, crear la rama, implementar paso a paso, verificar el checklist.
5. Al terminar cada task, commitear, pushear, y tachar el checklist en el documento.
6. Al terminar todas las tasks de una fase, ejecutar `pytest` completo y verificar el gate de salida.
7. Si el gate de salida pasa, marcar la fase como ✅ en este PLAN-GLOBAL y avanzar.

---

## 10. Criterios de Aceptación Global (Producto)

Antes de declarar "Cortex listo para beta", se debe cumplir:

- [ ] Todos los tests unitarios existentes siguen pasando.
- [ ] Todos los tests de integración existentes siguen pasando.
- [ ] Todos los tests E2E de FASE 1 pasan en local.
- [ ] Todos los tests de artefactos de FASE 2 pasan en local.
- [ ] El smoke test Docker de FASE 3 pasa en local.
- [ ] La suite completa pasa en CI (GitHub Actions) — job dedicado en `.github/workflows/`.
- [ ] `cortex doctor --strict` pasa tras ejecutar `cortex setup agent --git-depth 5 --ide pi`.
- [ ] `cortex setup enterprise --preset small-company --non-interactive` + `cortex memory-report --json` producen JSON válido con claves `project_root`, `enterprise_enabled`, `sources`, `promotion`.
- [ ] No hay prompts interactivos bloqueantes en los flujos documentados como "non-interactive".
- [ ] El job de CI E2E pasa en la rama `main` sin intervención manual.

---

## 11. Riesgos Globales y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| ONNX/ChromaDB tarda mucho en inicializar en tests E2E | Media | Alto | Usar `MockEmbedder` por defecto en E2E. Solo un test parametrizado opcional usa ONNX real (marcado `slow`). |
| `subprocess` es flaky en Windows vs Linux | Media | Medio | Helper `run_cortex` normaliza paths, usa `shell=False`, y setea `CORTEX_ENV=sandbox`. |
| Los tests E2E ensucian el repo real | Baja | Alto | Cada test usa `tmp_path` aislado + `monkeypatch.chdir`. Nunca escribir en `Path.cwd()` del repo. |
| El plan crece en scope durante la ejecución | Alta | Medio | Cualquier task nueva se documenta como "descubierta en ejecución" y se evalúa si entra en la fase actual o en backlog. |
| Docker no está disponible en CI o local del dev | Media | Bajo | FASE 3 es complementaria. Si Docker no corre, los tests pytest de FASE 1 y 2 ya dan cobertura suficiente. |

---

## 12. Glosario

| Término | Significado |
|---------|-------------|
| **E2E** | End-to-end: test que ejecuta la CLI como un usuario real, sin mocks internos. |
| **Scenario Runner** | Patrón donde cada test describe un escenario de usuario completo (Given → When → Then). |
| **Fixture (proyecto)** | Directorio prefabricado que simula un tipo de proyecto (Vite, Python, etc.). |
| **Smoke test** | Test rápido que verifica que el sistema "enciende" sin errores fatales. |
| **Gate de salida** | Checklist que debe pasarse para considerar una fase terminada. |
| **Task** | Unidad mínima de trabajo dentro de una fase, con checklist propio. |
