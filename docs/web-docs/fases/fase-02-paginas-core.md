---
title: Fase 02 — Páginas core (Getting started + Concepts + CLI Reference)
doc_type: phase
phase: 2
status: pending
depends_on: [phase-01]
unlocks: [phase-03]
estimated_duration: 7 días-persona
---

# Fase 02 — Páginas core

## Objetivo

Escribir las **páginas core** del docs: las que un usuario nuevo lee en sus primeros 30 minutos.

Cubre:

- **`/`** — Landing del docs (overview + cards).
- **`/getting-started/`** — Onboarding completo (Quickstart, Install, First Session, Connect IDE, Troubleshooting).
- **`/concepts/`** — Mental models (overview, hybrid-memory, RRF, tripartite, vault, episodic vs semantic, glossary).
- **`/cli/`** — Reference de TODOS los comandos CLI.

## Entregables

1. **`/index.mdx`** docs landing.
2. **5 páginas `/getting-started/`** completas.
3. **9 páginas `/concepts/`** completas.
4. **~35 páginas `/cli/`** (una por comando o grupo).
5. **Coverage 100% comandos** verificable por `pnpm check-cli-coverage`.

## Estructura `/getting-started/`

| Slug | Doctype | Outcome |
| --- | --- | --- |
| `getting-started/index` | index | Cards a los siguientes |
| `getting-started/installation` | tutorial | Cortex instalado y verificado con `cortex --version` |
| `getting-started/first-session` | tutorial | Primera spec creada y session guardada |
| `getting-started/connect-ide` | tutorial | MCP server conectado a tu IDE preferido |
| `getting-started/troubleshooting` | how-to | Resolución de issues comunes de setup |
| `getting-started/for-teams` | tutorial | Adopción organizacional inicial |

### Contenido detallado de cada página

#### `getting-started/installation.mdx`

Estructura:

1. **Prerequisitos** — Python 3.10+, Git, pipx opcional.
2. **Opción 1 — pipx (recomendado)** — bloque `data-runnable`.
3. **Opción 2 — pip + venv** — bloque alternativo.
4. **Verificación** — `cortex --version` + `cortex doctor`.
5. **Próximo paso** — link a `first-session`.

#### `getting-started/first-session.mdx`

Estructura:

1. **Intro** — qué vamos a lograr.
2. **Paso 1** — `cortex setup full` en un proyecto de prueba.
3. **Paso 2** — `cortex create-spec --title "Mi primera spec"`.
4. **Paso 3** — hacer cambio de código (placeholder).
5. **Paso 4** — `cortex save-session --title "..."`.
6. **Paso 5** — `cortex search "..."` muestra resultado.
7. **¿Qué pasó?** — explanation breve del flujo.

#### `getting-started/connect-ide.mdx`

Tabs por IDE:

```mdx
<Tabs>
  <Tab label="Claude Code">
    Ejecutá: `cortex inject --ide claude-code`
    ...
  </Tab>
  <Tab label="Cursor">...</Tab>
  ...
</Tabs>
```

#### `getting-started/troubleshooting.mdx`

How-to format con problemas frecuentes:

- `cortex: command not found` después de pipx install.
- `MCP server no responde` en IDE.
- `Doctor reporta workspace not found`.
- `chromadb falla a iniciar`.

## Estructura `/concepts/`

| Slug | Doctype | Tema |
| --- | --- | --- |
| `concepts/overview` | index | Overview con cards |
| `concepts/hybrid-memory` | explanation | Modelo de memoria híbrida |
| `concepts/rrf-retrieval` | explanation | RRF formula + adaptive weighting |
| `concepts/tripartite-cycle` | explanation | Sync → SDDwork → Documenter |
| `concepts/vault-structure` | explanation | Anatomía del vault |
| `concepts/episodic-vs-semantic` | explanation | Diferencia funcional |
| `concepts/enterprise-memory` | explanation | Capa enterprise |
| `concepts/workspace-layout-v2` | explanation | Layout v2 vs legacy |
| `concepts/glossary` | glossary | Términos canónicos |

### Foco en cada concepto

#### `concepts/rrf-retrieval.mdx`

Contenido:

1. **¿Qué es RRF?** — definición simple.
2. **Fórmula** — con KaTeX o imagen.
3. **Por qué RRF y no solo coseno** — explicación.
4. **Adaptive weighting** — detección de intención.
5. **Pesos por scope** — local/enterprise/all.
6. **Ejemplo numérico** — toy example.
7. **Implementación en Cortex** — link al código.

#### `concepts/tripartite-cycle.mdx`

Contenido:

1. **Los 3 roles**: Sync, SDDwork, Documenter — qué hace cada uno.
2. **Diagrama** del ciclo (reutilizar de landing).
3. **Handoff schema** — qué intercambian los agentes.
4. **Verification gates** — confidence labels.
5. **Cuándo se ejecuta vs autopilot**.
6. **Personalización**: cómo customizar cada rol vía skills/prompts.

#### `concepts/glossary.mdx`

50-100 términos en formato definition list:

```mdx
## Vault

Base de conocimiento Markdown estructurada con frontmatter YAML.
Compatible con Obsidian.

[Ver más en /concepts/vault-structure](../vault-structure)

## Memoria episódica

Memoria efímera vectorial almacenada en ChromaDB con embeddings ONNX.
Se usa para recuperar contexto reciente y tareas.

[Ver más en /concepts/episodic-vs-semantic](../episodic-vs-semantic)

...
```

## Estructura `/cli/`

Una página por comando o grupo, todas con `<CommandReference>` consistente.

### Grupos

| Grupo | Slug | Comandos |
| --- | --- | --- |
| Overview | `cli/overview` | Cards a todos los grupos |
| Setup | `cli/setup/...` | `setup agent`, `setup pipeline`, `setup full`, `setup webgraph`, `setup enterprise`, `init` |
| Memory | `cli/memory/...` | `search`, `remember`, `forget`, `context`, `stats`, `sync-vault` |
| Governance | `cli/governance/...` | `create-spec`, `save-session`, `verify-docs`, `validate-docs`, `index-docs` |
| Enterprise | `cli/enterprise/...` | `org-config`, `promote-knowledge`, `review-knowledge`, `sync-enterprise-vault`, `memory-report` |
| Autopilot | `cli/autopilot/...` | `start`, `preflight`, `checkpoint`, `finish`, `status`, `doctor`, `report`, `cleanup`, `install`, `uninstall` |
| IDE/MCP | `cli/ide-mcp/...` | `inject`, `sync-ide`, `install-skills`, `mcp-server`, `mcp-serve` |
| Webgraph | `cli/webgraph/...` | `serve`, `export`, `setup` |
| Tutor | `cli/tutor/...` | `tutor`, `hint`, `ask`, `docs-sync` |
| Tooling | `cli/tooling/...` | `doctor`, `agent-guidelines` |
| Work items | `cli/workitems/...` | `hu import/list/show` |
| PR Context | `cli/pr-context/...` | `pr-context capture/store/search/generate/full` |

### Plantilla de página de comando

```mdx
---
title: cortex search
doc_type: reference
summary: Búsqueda híbrida en la memoria con fusión RRF y scope configurable.
section: cli
audience: [developer, integrator]
tags: [search, memory, rrf, retrieval, cli]
cli_commands: [cortex search]
since_version: 0.1.0
last_review: 2026-05-14
status: stable
related: [cli/memory/context, cli/memory/stats, concepts/rrf-retrieval]
---

<CommandReference command="cortex search" syntax="cortex search QUERY [OPTIONS]" since="0.1.0" />

Busca en la memoria híbrida (episódica + semántica + enterprise) con fusión RRF.

## Sinopsis

```bash
cortex search QUERY [OPTIONS]
```

## Flags

<CommandFlag name="--scope" type="string" default="all" choices="local,enterprise,all">
Alcance de la búsqueda.
</CommandFlag>

<CommandFlag name="--top-k" type="int" default="10">
Número máximo de resultados.
</CommandFlag>

<CommandFlag name="--format" type="string" default="rich" choices="rich,json,compact">
Formato de salida.
</CommandFlag>

## Ejemplos

<CommandExample title="Búsqueda básica">
```bash data-runnable
cortex search "JWT refresh tokens"
```
</CommandExample>

<CommandExample title="Búsqueda solo enterprise, JSON">
```bash data-runnable
cortex search "ADR auth" --scope enterprise --format json
```
</CommandExample>

## Cómo funciona

Internamente:

1. Tokeniza la query y la embebe con ONNX (~1ms).
2. Busca en paralelo en episódico, semántico y enterprise.
3. Aplica Reciprocal Rank Fusion con pesos adaptativos.
4. Devuelve top-k unificado.

Ver [Concepts > RRF Retrieval](../../concepts/rrf-retrieval) para detalle.

## Errores comunes

- `Workspace not found` → ejecutá `cortex setup full` primero.
- `No memories yet` → primero `cortex save-session` algo.
```

### Validación de coverage

`apps/docs/scripts/check-cli-coverage.ts`:

1. Ejecuta `cortex --help` y parsea comandos.
2. Lista frontmatters de páginas `/cli/` (lee `cli_commands`).
3. Diff: warning por cada comando sin página.
4. Exit non-zero si gap > threshold.

## Tareas detalladas

### 2.1 Landing del docs (0.5 día)

- [ ] `src/content/docs/es/index.mdx` con hero + cards.
- [ ] Mismo para `en/`.

### 2.2 Getting started — 5 páginas (1.5 días)

- [ ] Index + Installation + First session + Connect IDE + Troubleshooting + For teams.
- [ ] Cada uno con `data-runnable` blocks.
- [ ] CI valida que blocks corren.

### 2.3 Concepts — 9 páginas (2 días)

- [ ] Overview con cards.
- [ ] 8 conceptos con explicación clara, ejemplos, diagramas.
- [ ] Glossary con 50+ términos.

### 2.4 CLI — ~35 páginas (3 días)

- [ ] Overview con cards.
- [ ] Páginas por grupo o comando.
- [ ] Plantilla consistente.
- [ ] Coverage check pasa al final.

## Criterios de aceptación

- ✅ Coverage CLI ≥ 95% (los comandos faltantes son edge cases marcados).
- ✅ Coverage concepts: los 9 conceptos cubiertos.
- ✅ Coverage getting-started: los 6 archivos completos.
- ✅ Linkcheck verde.
- ✅ Build pasa.
- ✅ `data-runnable` blocks ejecutan limpio.
- ✅ Tutorial getting-started completo en 30 min para usuario fresh.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| Muchas páginas a escribir = burnout | Templates fuertes + escritura en batches |
| CLI cambia mientras se documenta | Pin versión 0.5.0 como target; cambios futuros se documentan en cada release |
| Coverage script tiene falsos positivos | Allowlist en `_meta/cli-coverage-allowlist.json` |

## Siguiente fase

→ [Fase 03 — Módulos profundos](fase-03-modulos-profundos.md)
