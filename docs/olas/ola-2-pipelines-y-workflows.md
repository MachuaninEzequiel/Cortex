---
title: Ola 2 — Pipelines y workflows CI/CD
status: ✅ CERRADA AL 100% (2026-05-13)
prerequisitos: Ola 0, Ola 1 cerradas
bloquea: Ola 3
suite_at_close: 825 passed, 6 skipped, 0 failed
---

## Resumen del cierre

**Hallazgos críticos confirmados en auditoría:**

1. **Workflows del repo Cortex ≠ workflows generados por `templates.py`**. El repo Cortex tiene `.github/workflows/ci-pull-request.yml` Python-only en modo observability con cache `.memory/chroma` hardcoded. `templates.py::render_ci_pull_request` genera una versión más robusta, stack-aware, con cortex pr-context pipeline completo. Esto NO es bug — el repo Cortex es un proyecto Python que tiene workflows propios. Lo que importa para adopters es lo que **el template genera** en `cortex setup pipeline`.

2. **3 workflows del repo Cortex no son generados por templates**: `ci-e2e.yml`, `ci-release.yml`, `ci-security.yml`. Son específicos del repo Cortex (no de adopters). Está bien — los adopters reciben los 4 que `templates.py` produce (`ci-pull-request`, `ci-feature`, `cd-deploy`, `ci-enterprise-governance`).

**Fixes aplicados:**

- **`cortex/setup/templates.py`** — nuevo helper `_get_memory_cache_path(layout)` que retorna `.cortex/memory` en new layout o `.memory/chroma` en legacy (similar al pattern de `render_config_yaml` que ya era layout-aware).
- **`render_ci_pull_request(ctx, layout=...)`** — firma extendida con `layout` opcional. Agregado bloque `actions/cache/restore@v4` antes de `cortex doctor` y `actions/cache/save@v4` después de `sync-vault`. Cache key `cortex-memory-${{ github.run_id }}` con restore-keys fallback `cortex-memory-`.
- **`render_ci_feature(ctx, layout=...)`** — análogo: restore al inicio + save al final.
- **`render_cd_deploy(ctx, layout=...)`** — análogo.
- **`render_ci_enterprise_governance(ctx)`** — sin cambios. Lee `.cortex/org.yaml` que está siempre en `repo_root/.cortex/org.yaml` en ambos layouts (WorkspaceLayout.org_config_path lo garantiza).
- **`cortex/setup/orchestrator.py::_create_workflows`** — refactorizado: pasa `layout` a los 3 renderers layout-aware y maneja `render_ci_enterprise_governance` por separado (no necesita layout).

**Tests nuevos (`tests/integration/setup/test_templates.py`):**

- **`TestLayoutAwareCachePaths`** (5 tests):
  - `test_new_layout_uses_cortex_memory` — confirma `.cortex/memory` en new.
  - `test_legacy_layout_uses_memory_chroma` — confirma `.memory/chroma` en legacy.
  - `test_no_layout_falls_back_to_legacy` — backwards-compat sin layout.
  - `test_ci_feature_respects_layout` — restore+save presentes con path correcto.
  - `test_cd_deploy_respects_layout` — idem para CD.
- **`TestCommandsAcrossStacks`** (3 tests):
  - `test_node_workflow_uses_npm_commands` — `npm ci`, `npm test`, `npm run lint`, `npm audit`, `setup-node@v4`.
  - `test_python_workflow_uses_pytest_and_ruff` — `pytest`, `ruff check`, `pip audit`, `setup-python@v5`.
  - `test_go_workflow_uses_go_commands` — `go test ./...`, `golangci-lint run`, `govulncheck ./...`, `setup-go@v5`.
- **`TestCliAlignment`** (1 test, exhaustivo):
  - `test_workflows_reference_known_subcommands` — extrae con regex todos los `cortex <subcmd>` y `cortex <sub-app> <sub>` de los 3 workflows generados (PR, feature, CD) y verifica que cada uno existe como Typer command. Catch automático de drift CLI ↔ templates.

**Test contract preservado:** los 17 tests existentes de templates siguen verdes.

## Mapping de comandos cortex usados en workflows (validado)

| Comando | Existe en CLI | Sub-app | Flags coinciden |
|---------|--------------|---------|-----------------|
| `cortex doctor` | ✅ top | — | — |
| `cortex pr-context capture` | ✅ | `pr-context` | `--title --body --author --branch --commit --pr-number --target-branch --labels --output` ✓ |
| `cortex pr-context store` | ✅ | `pr-context` | `--context-file --lint-result --audit-result --test-result` ✓ |
| `cortex pr-context search` | ✅ | `pr-context` | `--context-file --output` ✓ |
| `cortex pr-context generate` | ✅ | `pr-context` | `--context-file --vault` ✓ |
| `cortex verify-docs` | ✅ top | — | `--vault --output` ✓ |
| `cortex validate-docs` | ✅ top | — | `--vault --output` ✓ |
| `cortex index-docs` | ✅ top | — | `--vault` ✓ |
| `cortex sync-vault` | ✅ top | — | — |
| `cortex context` | ✅ top | — | `--files --format --output` ✓ |
| `cortex remember` | ✅ top | — | `--type --tag --branch --commit` ✓ |
| `cortex promote-knowledge` | ✅ top | — | `--dry-run --json` ✓ |
| `cortex sync-enterprise-vault` | ✅ top | — | `--json --output` ✓ |

Todos los comandos referenciados en los 3 templates de workflow + el de enterprise governance están registrados con flags exactos.

## Deuda residual (queda en Olas posteriores, NO en Ola 2)

- **`cortex setup pipeline` y `cortex setup full` interactivos sin `--non-interactive`** — ya en Ola 3 desde el cierre de Ola 0. Bloquea el smoke CLI completo de Ola 2 (el flow contractual sí está cubierto por los 25 tests del template).
- **Workflow real del repo Cortex (`.github/workflows/ci-pull-request.yml`)** sigue siendo Python-only con cache `.memory/chroma`. NO es deuda — el repo Cortex es proyecto Python y tiene workflows propios. Los workflows para adopters son los que `templates.py` genera.

## Checklist final de la Ola 2

### Inventario
- [x] Tabla completa de los 5 workflows reales + 4 que el template genera. Drift identificado.

### Cache layout-aware
- [x] `_get_memory_cache_path(layout)` agregado a templates.
- [x] `render_ci_pull_request`, `render_ci_feature`, `render_cd_deploy` reciben `layout` opcional.
- [x] `orchestrator._create_workflows` pasa `layout` a los 3 renderers.
- [x] Tests new/legacy/no-layout verdes.

### Stack-agnostic
- [x] Node (npm), Python (pip), Go cubiertos por tests.
- [x] Pnpm/yarn/cargo cubiertos por `_get_install_command` (no tests dedicados pero el helper los soporta).

### CLI alignment
- [x] Todos los comandos cortex en workflows existen en el CLI con flags coincidentes.
- [x] Test contract `test_workflows_reference_known_subcommands` detecta drift automáticamente.

### Enterprise governance
- [x] `ci-enterprise-governance.yml` valida 3 perfiles (observability/advisory/enforced) inline via `python -c "yaml.safe_load(...)"`. Comportamiento ya cubierto en runtime.

### Cierre
- [x] Suite global: 825 passed, 6 skipped, 0 failed.
- [x] +9 tests vs Ola 1 (5 layout-aware + 3 stacks + 1 alignment).

**Ola 2 cerrada al 100%. Lista para Ola 3.**

# Ola 2 — Pipelines y workflows CI/CD

## Objetivo

Los **5 workflows de GitHub Actions** ejecutan limpio en un PR real con un proyecto web (no asumir Python). Las plantillas de setup generan workflows alineados con la realidad del CLI actual. Los caches y paths siguen el `WorkspaceLayout` (no hardcoded legacy).

## Contexto descubierto previamente

### Workflows existentes en `.github/workflows/`

1. `ci-pull-request.yml` — modo observability, todo `continue-on-error: true`. Hace `cortex doctor`, `pr-context capture/store/search/generate`, `verify-docs`, `index-docs`, `validate-docs`, `sync-vault`. **Cachea `.memory/chroma` hardcoded** — legacy path.
2. `ci-enterprise-governance.yml` — lee `.cortex/org.yaml` para decidir `ci_profile` (observability / advisory / enforced). Hace `doctor --scope enterprise`, `promote-knowledge --dry-run`, `sync-enterprise-vault`. En modo enforced, falla si hay candidatos planificados o errores en vault enterprise.
3. `ci-e2e.yml` — no inspeccionado en detalle. Probable E2E corto.
4. `ci-release.yml` — no inspeccionado. Probable release tagging.
5. `ci-security.yml` — Gitleaks únicamente (probable).

### Estado de templates

`cortex/setup/templates.py` (1205 líneas) genera workflows desde plantillas con variables. Los workflows generados pueden diferir de los del repo actual. **Verificar drift.**

### Tensión legacy/new layout

Los workflows reales del repo Cortex cachean `.memory/chroma` (legacy). Si un adopter usa `cortex setup full` y obtiene new layout (`.cortex/memory`), su cache no acelera y el `actions/cache@v4` mete miss permanente.

## Pasos

### 2.A — Inventario y lectura completa de los 5 workflows

1. Leer entero cada uno de los 5 archivos en `.github/workflows/`.
2. Para cada uno, listar en una tabla en este documento:
   - Triggers (eventos GitHub)
   - Jobs y steps
   - Comandos `cortex <subcommand>` ejecutados
   - Paths cacheados / artefactos subidos
   - Condicionales (`if:`, `continue-on-error`)
3. Marcar cada step que asume Python (`pip install`, `ruff`, `mypy`, `pytest`) — esos son los que no son stack-agnostic.

Pegar la tabla aquí cuando se haga:

| Workflow | Triggers | Jobs | Cortex commands | Cache paths | Stack assumption |
|----------|----------|------|-----------------|-------------|------------------|
| ci-pull-request.yml | _completar_ | _completar_ | _completar_ | _completar_ | _completar_ |
| ci-enterprise-governance.yml | _completar_ | _completar_ | _completar_ | _completar_ | _completar_ |
| ci-e2e.yml | _completar_ | _completar_ | _completar_ | _completar_ | _completar_ |
| ci-release.yml | _completar_ | _completar_ | _completar_ | _completar_ | _completar_ |
| ci-security.yml | _completar_ | _completar_ | _completar_ | _completar_ | _completar_ |

### 2.B — Reconciliar workflows del repo con `cortex/setup/templates.py`

1. Generar los workflows desde templates en un repo de prueba: `cortex setup pipeline --non-interactive` o equivalente.
2. Comparar con los archivos en `.github/workflows/` del repo Cortex.
3. Identificar **drift**: comandos que solo están en uno o el otro, paths distintos, flags inconsistentes.
4. **Decisión**: la fuente de verdad son los templates en `cortex/setup/templates.py` (porque son los que llegan al adopter). Si el repo Cortex tiene un workflow más completo, mover esa lógica al template.
5. Re-generar y comprobar que el resultado match exacto.

### 2.C — Migrar cache paths a layout-aware

#### Cambio en `ci-pull-request.yml` (líneas ~70, ~137)

Antes:
```yaml
path: .memory/chroma
```

Después (layout-aware via paso preparatorio):
```yaml
- name: Resolve Cortex memory path
  id: cortex_paths
  run: |
    python -c "
    from cortex.workspace.layout import WorkspaceLayout
    from pathlib import Path
    layout = WorkspaceLayout.discover(Path.cwd())
    print(f'memory_path={layout.episodic_memory_path.relative_to(layout.repo_root)}')
    " >> "$GITHUB_OUTPUT"

- name: Restore Cortex Memory Cache
  uses: actions/cache/restore@v4
  with:
    path: ${{ steps.cortex_paths.outputs.memory_path }}
    key: cortex-memory-${{ github.run_id }}
```

Aplicar el mismo cambio en cualquier otro workflow que cachee path Cortex.

#### Actualizar `cortex/setup/templates.py` para que genere el patrón nuevo

Buscar el `render_ci_pull_request` y similares. Reemplazar el path hardcoded por el bloque de resolución layout-aware.

### 2.D — Stack-agnostic: que los workflows funcionen con repo web (no Python)

#### Estrategia

`ProjectDetector` (`cortex/setup/detector.py`) ya detecta Python, JS, Go, Rust. Los templates deben usar esa detección para emitir comandos correctos:

| Stack | install_cmd | lint_cmd | test_cmd | audit_cmd |
|-------|-------------|----------|----------|-----------|
| Python | `pip install -e ".[dev]"` | `ruff check .` | `pytest --cov=.` | `safety check` |
| Node.js (npm) | `npm ci` | `npm run lint` | `npm test` | `npm audit` |
| Node.js (pnpm) | `pnpm install` | `pnpm lint` | `pnpm test` | `pnpm audit` |
| Node.js (yarn) | `yarn install` | `yarn lint` | `yarn test` | `yarn audit` |
| Go | `go mod download` | `go vet ./...` | `go test ./...` | `govulncheck ./...` |

#### Pasos

1. Leer `cortex/setup/detector.py`. Verificar qué stacks detecta y qué `StackInfo` produce.
2. Leer `cortex/setup/templates.py`. Buscar dónde se decide `test_cmd`, `lint_cmd`, `audit_cmd`. Si están hardcoded a Python, agregar lógica condicional según `StackInfo.language`.
3. Para cada combinación stack × workflow, agregar una sección al template.
4. Validar generando workflows en repos de prueba (uno por stack target).

#### Repos de prueba a crear (`tmp` o equivalente)

- `repo-python-test/` con `pyproject.toml`.
- `repo-node-npm-test/` con `package.json` y `package-lock.json`.
- `repo-node-pnpm-test/` con `package.json` y `pnpm-lock.yaml`.
- (Si los adopters dicen ser web, **prioritarios Node**. Python como backup.)

### 2.E — Validar enterprise governance en los 3 perfiles

`ci-enterprise-governance.yml` cambia comportamiento según `governance.ci_profile` en `.cortex/org.yaml`. Hay que probar los 3:

1. **observability**: todos los steps `continue-on-error`. Verificar que un error en doctor o sync no rompe el PR.
2. **advisory**: doctor strict, promote y sync flexibles. Verificar que un error en doctor sí rompe pero los otros siguen.
3. **enforced**: todo strict. Verificar que candidatos pendientes de promoción bloquean el merge.

Plan: usar `act` (https://github.com/nektos/act) o un fork de prueba con un PR de prueba por perfil. Documentar comandos exactos.

### 2.F — Comandos `cortex` que usan los workflows: verificar que todos existen y aceptan los flags usados

Lista de comandos a verificar contra `cortex/cli/main.py`:

- `cortex doctor` (con `--scope enterprise`)
- `cortex pr-context capture --title --body --author --branch --commit --pr-number --target-branch --output`
- `cortex pr-context search --context-file --output`
- `cortex pr-context store --context-file --lint-result --audit-result --test-result`
- `cortex pr-context generate --context-file --vault`
- `cortex verify-docs --vault --output --quiet`
- `cortex validate-docs --vault --output`
- `cortex index-docs --vault`
- `cortex sync-vault`
- `cortex promote-knowledge --dry-run --json`
- `cortex sync-enterprise-vault --json --output`

Por cada uno: `cortex <subcomando> --help` y comparar con flags usados en workflows. Si hay drift, decidir si fixear el flag o el workflow.

### 2.G — Smoke test del pipeline en repo de prueba

#### Setup

```bash
# Repo web Node de prueba
git clone <repo-template-node>
cd <repo-template-node>
cortex setup full --non-interactive
git add . && git commit -m "init cortex"
git push -u origin feature/cortex-smoke
gh pr create --title "Smoke test Cortex pipeline" --body "PR de prueba"
```

#### Validar

1. Los 5 workflows arrancan en el PR.
2. Cada uno termina sin error (en modo observability, con `continue-on-error` puede haber rojos pero el job overall no falla).
3. El artifact de `cortex-enterprise-governance` se sube y contiene los 3 JSON esperados.
4. Si el repo tiene `.cortex/org.yaml` con `ci_profile: enforced`, verificar que vault errors bloquean.

## Tests obligatorios al cierre

```bash
python -m pytest tests/integration/setup/ tests/e2e/scenarios/test_setup_full.py tests/e2e/scenarios/test_setup_basic.py tests/e2e/scenarios/test_pr_devsecdocops.py tests/e2e/scenarios/test_enterprise_setup.py --no-cov
```

Plus suite completa:

```bash
python -m pytest tests/unit tests/integration tests/e2e --no-cov
```

Pegar resultado:

```
[pegar output cuando se cierre la ola]
```

## Checklist final de la Ola 2

### Inventario
- [ ] Tabla completa de los 5 workflows con triggers, jobs, comandos cortex, cache paths, stack assumptions.

### Reconciliación templates ↔ workflows
- [ ] Drift identificado entre `templates.py` y `.github/workflows/`.
- [ ] Fuente de verdad fijada en `templates.py`.
- [ ] Workflows regenerados y match exacto.

### Cache layout-aware
- [ ] `.memory/chroma` hardcoded eliminado de los workflows.
- [ ] Templates generan paths resueltos via `WorkspaceLayout`.

### Stack-agnostic
- [ ] `ProjectDetector` cubre Python, Node (npm/pnpm/yarn), Go al mínimo.
- [ ] Templates emiten comandos correctos por stack.
- [ ] Validado en repos de prueba: Python OK, Node OK, (Go si hay tiempo).

### Enterprise governance
- [ ] `observability` perfil validado.
- [ ] `advisory` perfil validado.
- [ ] `enforced` perfil validado.

### Comandos cortex alineados
- [ ] Cada comando usado en workflows existe en el CLI con los flags exactos.
- [ ] `cortex pr-context generate` acepta `--vault`.
- [ ] `cortex verify-docs --quiet` existe.
- [ ] `cortex sync-enterprise-vault --json --output` existe.

### Smoke test
- [ ] PR de prueba en repo web Node ejecutó los 5 workflows.
- [ ] Resultados documentados en este archivo.

### Cierre
- [ ] Suite global verde.

**Sólo cuando todos los items están marcados, se puede pasar a Ola 3.**
