# Deep Review — Setup / Workspace / Infra (subsistema 11)

> Reconstruido desde la revisión del subagente rev-setup-workspace-infra (entregado por mensajes por límite de turno).
> Alcance: cortex/setup/**, cortex/workspace/layout.py, config.yaml, pyproject.toml, requirements.txt, scripts/, templates/, .github/workflows, mapa de tests/.

## Hallazgos

1. **BUG** — cold_start.py `_get_git_commits` (~L196-235): el parser de `git log --format="%H|%an|%ai|%s" --name-only` es frágil. Detecta "nuevo commit" solo si la línea contiene "|" y current_commit is None; un mensaje con "|" o líneas de archivo con "|" corrompen el parseo. Ramas elif (`line.startswith("commit ")`) son código muerto. Commits sin archivos se descartan silenciosamente.
2. **BUG potencial** — cold_start.py layer2_git_history: `files=commit.get('files', [])[:10]` puede recibir un string si el parser falló; `_chunk_commits_by_time` compara fechas string asumiendo orden cronológico (roto con --reverse/rebase). Clasificación por keywords ("fix","add","new") es muy ruidosa.
3. **RIESGO** — orchestrator.py run() L96-105: el guard anti-walk-up fuerza WorkspaceLayout.from_repo_root cuando discover() encuentra un padre, pero NO re-ejecuta detector.detect(); ctx.layout queda parcheado a mano.
4. **INCONSISTENCIA** — templates.py render_config_yaml (L36-77): con OPENAI_API_KEY seteada genera llm.provider=openai PERO embedding_backend queda "onnx" siempre; no hay ruta para elegir openai embeddings. WorkspaceLayout usado en anotaciones sin importarlo.
5. **DUPLICACIÓN MASIVA** — cortex_workspace.py (1670 líneas): skills/subagents completos como strings embebidos; comentarios admiten sincronización manual "byte-identical" con .cortex/ sin test que la garantice. Se duplica además contra cortex-pi/.pi/skills/.
6. **DUPLICACIÓN** — templates.py DEVSECDOCSOPS_SCRIPT vs scripts/devsecdocops.sh: mismo script bash dos veces, ya divergidos.
7. **WORKFLOW GENERADO CON GATE DURÍSIMO** — templates.py render_ci_pull_request: gates finales exit 1 si outcome != success con steps continue-on-error:true; `cortex validate-docs` SIN continue-on-error puede romper el pipeline del adopter por un doc inválido. Hardcodea "vault" como --vault incluso en new layout.
8. **BUG LAYOUT** — workflows generados usan rutas legacy ("vault") en verify-docs/validate-docs; en new layout apuntan a vault inexistente en raíz (_get_memory_cache_path sí es layout-aware).
9. **requirements.txt CONTRADICE pyproject.toml**: requirements instala sentence-transformers>=3.0 como core (~2.5 GB PyTorch) mientras pyproject lo movió al extra [local] con ONNX default. Instalar vía requirements.txt descarga 2.5 GB innecesarios.
10. **DETECTOR** — detector.py: _detect_python ignora pyproject.toml (project_name = root.name); no detecta poetry/uv/pipenv; _detect_go chequea "(root/'go_test.go').exists()" — archivo inexistente, debería ser "*_test.go" (L172-173). CI detection ambigua si coexisten GitHub Actions y gitlab-ci.
11. **LAYOUT** — layout.py SÓLIDO: discover() con 4 estrategias, dual new/legacy via is_legacy_layout. Deudas: flag privado _force_new= sin efecto real; Case 3 legacy puede matchear repo con solo .cortex/.git; workspace.yaml corrupto tragado silenciosamente (except: pass L137-141).
12. **ORQUESTADOR** — idempotencia consistente salvo _create_enterprise_org_config(force=True) que SOBRESCRIBE org.yaml sin backup. dry_run solo implementado para enterprise; `setup full/pipeline/webgraph --dry-run` acepta el flag Y LO IGNORA (main.py hace `del dry_run` explícito). [Coincide con hallazgo del subsistema CLI.]
13. **COLD START** — run_cold_start(): buen diseño de 3 capas; pero layer1 ingesta TODOS los *.md del vault sin límite (vault grande = miles de memories en Chroma en un solo setup).
14. **TESTS** — tests/integration/setup cubre detector/orchestrator/templates/cortex_workspace; test_cold_start_perf existe; NO hay tests del parser git log ni de enterprise_wizard. ci-release tiene twine upload COMENTADO (release no publica).

## Salud: 7/10
Arquitectura clara (WorkspaceLayout como single source of truth de paths es la decisión correcta), idempotencia cuidada, tests de integración decentes.

## Orden sugerido para cambio grande
1. Extraer skills/subagents embebidos a archivos de datos + test de byte-equality contra .cortex/.
2. Parametrizar vault path en templates de workflows generados (layout-aware).
3. Endurecer parser git log de cold_start + tests.
4. Alinear requirements.txt con pyproject.toml.
