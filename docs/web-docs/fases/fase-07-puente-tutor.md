---
title: Fase 07 — Puente Docs ↔ Tutor (la integración crítica)
doc_type: phase
phase: 7
status: pending
depends_on: [phase-06]
unlocks: [phase-08]
estimated_duration: 9 días-persona
priority: critical
---

# Fase 07 — Puente Docs ↔ Tutor

> **Esta es la fase más distintiva del proyecto.** La que materializa la consigna del usuario: *"el usuario tenga dos alternativas, entrar a la web o bien preguntarle al tutor".*
>
> Pre-requisitos: leer [`03-integracion-tutor.md`](../03-integracion-tutor.md) en detalle antes de comenzar.

## Objetivo

Conectar el sitio de documentación con el `cortex tutor` existente de modo que:

1. La **fuente de verdad** del contenido sea **única** (`apps/docs/content/`).
2. El tutor CLI consume **exactamente el mismo contenido** que la web.
3. El usuario pueda preguntar `cortex tutor ask "..."` y obtener respuestas del docs oficial.
4. El sistema de tópicos del TUI (`cortex tutor`) cargue dinámicamente desde el vault sincronizado.
5. Todo funcione offline (post-sync), respetando la naturaleza del tutor.

## Entregables

1. **Tarball pipeline** — `cortex-docs-{version}.tar.gz` publicado en cada release.
2. **Comando `cortex docs-sync`** — descarga e indexa el docs.
3. **Comando `cortex tutor ask`** — pregunta libre al docs sincronizado.
4. **Refactor de `cortex/tutor/topics/`** — carga dinámica desde vault.
5. **Extensión de `cortex hint --from-docs`** — recomendaciones basadas en docs.
6. **Tests E2E** del flujo completo: docs publica → user sync → user ask → respuesta correcta.
7. **Documentación** dentro del propio docs sobre `cortex docs-sync` y `cortex tutor ask`.

## Sub-fases

### Fase 7.1 — Tarball pipeline (1.5 días)

#### Script de generación

`apps/docs/scripts/generate-tarball.ts`:

- [ ] Lee todas las páginas de `src/content/docs/`.
- [ ] Para cada idioma (`es`, `en`):
  - Copia `.md`/`.mdx` a `dist-tarball/{lang}/content/`.
  - Convierte MDX → MD plano cuando sea posible (preservando frontmatter).
  - Para componentes custom (`<CommandReference>`), inyecta el render textual.
- [ ] Genera `dist-tarball/{lang}/index.json` con:
  ```json
  {
    "schema_version": 1,
    "cortex_version_compatibility": ">=0.5.0",
    "generated_at": "2026-05-14T...",
    "lang": "es",
    "total_pages": 156,
    "sections": [...],
    "pages": [
      { "slug": "...", "title": "...", "summary": "...", "tags": [...], "section": "...", "path": "content/..." }
    ]
  }
  ```
- [ ] Empaqueta como `cortex-docs-{lang}-{version}.tar.gz`.
- [ ] Verifica integridad: checksum SHA256.

#### CI workflow

`.github/workflows/docs-tarball.yml`:

- [ ] Trigger: tag `docs-v*`.
- [ ] Build site + generate tarballs (es + en).
- [ ] Crear GitHub release con tarballs como assets.
- [ ] Notificar a `cortex-docs-mcp-server` (webhook) para re-indexar.

#### Estructura del tarball

```
cortex-docs-es-0.5.0.tar.gz
├── index.json                         ← Metadata maestra
├── schema-version                     ← "1"
├── content/
│   ├── getting-started/
│   │   ├── index.md
│   │   ├── installation.md
│   │   ├── first-session.md
│   │   └── ...
│   ├── concepts/
│   ├── guides/
│   ├── cli/
│   ├── mcp/
│   ├── ide/
│   ├── autopilot/
│   ├── enterprise/
│   ├── tutorials/
│   └── reference/
└── assets/
    └── (referencias relativas)
```

### Fase 7.2 — Comando `cortex docs-sync` (2 días)

#### Implementación Python

`cortex/docs_sync/`:

```
cortex/docs_sync/
├── __init__.py
├── service.py          ← DocsSyncService
├── fetcher.py          ← Descarga tarball desde GitHub releases
├── extractor.py        ← Extrae y valida estructura
├── indexer.py          ← Invoca cortex index-docs
└── version.py          ← Resolución de versiones
```

#### API pública

```python
class DocsSyncService:
    def __init__(self, layout: WorkspaceLayout):
        self.layout = layout

    def sync(
        self,
        version: str | None = None,  # None = matching cortex version
        lang: str = 'es',
        force: bool = False,
    ) -> SyncResult:
        """Sync official docs to local vault."""

    def list_available_versions(self) -> list[str]:
        """List versions available in remote."""

    def status(self) -> SyncStatus:
        """Get info about last sync."""
```

#### CLI integration

`cortex/cli/main.py`:

```python
@app.command()
def docs_sync(
    version: Optional[str] = typer.Option(None, help="Specific version (default: matching cortex)"),
    lang: str = typer.Option("es", help="Language (es | en)"),
    force: bool = typer.Option(False, help="Re-download even if cached"),
    where: bool = typer.Option(False, help="Print sync path and exit"),
    list_versions: bool = typer.Option(False, "--list", help="List available versions"),
):
    """Sync official Cortex documentation to your local vault."""
    ...
```

#### Caché local

- [ ] Path: `~/.cache/cortex/docs/cortex-docs-{lang}-{version}.tar.gz`.
- [ ] Verificación SHA256 antes de usar caché.
- [ ] Compartido entre proyectos del mismo usuario.

#### Workspace metadata

`.cortex/workspace.yaml` se enriquece:

```yaml
layout_version: 2
docs_sync:
  version: 0.5.0
  lang: es
  synced_at: 2026-05-14T12:00:00Z
  path: cortex-docs/
  index_status: indexed
```

#### Tests

- [ ] Test unit: `DocsSyncService.sync()` con mocked fetcher.
- [ ] Test integration: tarball fixture → extract → verify structure.
- [ ] Test E2E: real sync (CI con mock GitHub release).

### Fase 7.3 — Comando `cortex tutor ask` (1.5 días)

#### Implementación

`cortex/tutor/ask.py`:

```python
class AskEngine:
    def __init__(self, memory: AgentMemory):
        self.memory = memory

    def ask(
        self,
        query: str,
        top_k: int = 5,
        format: Literal['rich', 'json', 'plain'] = 'rich',
    ) -> AskResult:
        """Ask a question to Cortex's official docs."""
        # 1. Verify docs are synced
        # 2. Retrieve with filter on cortex-docs scope
        # 3. Extract best chunk + related pages
        # 4. Format output
```

#### Output schema

```python
@dataclass
class AskResult:
    query: str
    best_match: Match | None
    related: list[Match]
    no_results: bool
    docs_version: str

@dataclass
class Match:
    title: str
    slug: str
    summary: str
    excerpt: str        # Chunk relevante
    score: float
    page_url: str       # https://docs.cortex.dev/...
```

#### Rendering en CLI

`rich`-based pretty print:

```
$ cortex tutor ask "¿cómo configuro retention policies?"

┌─────────────────────────────────────────────────────────────────┐
│ 📘 Retention Policies — Cortex Docs v0.5.0                       │
└─────────────────────────────────────────────────────────────────┘

  Las retention policies se configuran en .cortex/org.yaml dentro
  de la sección `governance.retention`. Cada doctype tiene su
  retención por defecto (sessions: 365d, decisions: 2555d, hu: 90d).
  Podés overridear:

      governance:
        retention:
          session: 730d
          adr: 3650d

  ...

  ─────────────────────────────────────
   📚 Páginas relacionadas
  ─────────────────────────────────────
   1. /enterprise/retention-policies         (score 0.94)
   2. /enterprise/org-yaml-reference         (score 0.81)
   3. /enterprise/compliance-guide           (score 0.72)
   4. /guides/audit-knowledge-promotion      (score 0.65)

   🌐 Web: https://docs.cortex.dev/v0.5.0/es/enterprise/retention-policies
```

#### CLI integration

```python
@app.command()
def tutor_ask(
    query: str = typer.Argument(...),
    top_k: int = typer.Option(5),
    format: str = typer.Option("rich"),
):
    """Ask a question to Cortex's official documentation."""
```

Registrado como subcomando `cortex tutor ask` (parte del Typer subcommand `tutor`).

#### Tests

- [ ] Test unit AskEngine con vault fixture indexado.
- [ ] Test E2E: sync → ask → respuesta tiene score > 0.5.

### Fase 7.4 — Refactor tópicos dinámicos (2 días)

#### Diseño

Detallado en [`03-integracion-tutor.md`](../03-integracion-tutor.md) §7.

Pasos:

- [ ] Crear `cortex/tutor/topics/markdown_topic.py` con `MarkdownTopic` class.
- [ ] Crear `cortex/tutor/topics/loader.py`:
  ```python
  def load_topics_from_vault(layout: WorkspaceLayout) -> list[TutorTopic]:
      """Load topics from synced docs vault."""
  ```
- [ ] Modificar `cortex/tutor/engine.py`:
  - Default: cargar dinámico desde vault si está sincronizado.
  - Fallback: tópicos hard-coded existentes.
  - Flag `--source builtin` para forzar hard-coded.

#### Frontmatter para tópicos del TUI

Páginas marcadas:

```yaml
tags: [..., tutor-topic]
tutor:
  icon: "🚀"
  one_liner: "Cómo instalar y empezar"
  order: 1
  terminal_summary: |
    Multiline rich-formatted summary
    for terminal rendering (≤25 lines).
```

#### Renderizado terminal

`MarkdownTopic.render(console)`:

- [ ] Si hay `tutor.terminal_summary` en frontmatter → renderiza ese campo.
- [ ] Si no → renderiza primer párrafo + bullets de H2 + link "Leer completo en docs.cortex.dev/...".

#### Páginas que se marcan como `tutor-topic` (V1)

Los 7 tópicos originales tienen su equivalente:

| Tópico original | Página docs equivalente |
| --- | --- |
| Primeros Pasos | `/getting-started/index` |
| Comandos Esenciales | `/cli/overview` |
| Flujo de Trabajo | `/concepts/tripartite-cycle` |
| Pipeline CI/CD | `/concepts/pipeline-overview` |
| Vault y Documentación | `/concepts/vault-structure` |
| Enterprise Memory | `/enterprise/overview` |
| IDE + MCP | `/ide/overview` |

Cada una agrega frontmatter `tutor.terminal_summary` con la versión condensada.

#### Backwards compatibility

- [ ] Si vault no tiene docs sincronizados → usa hard-coded.
- [ ] Hard-coded permanece como **safety net**, no se elimina V1.

### Fase 7.5 — `cortex hint --from-docs` (0.5 día)

Extender hint engine:

```python
@app.command()
def hint(
    from_docs: bool = typer.Option(False, "--from-docs", help="Suggest docs pages"),
):
    """Show contextual hint based on project state."""
    if from_docs:
        # Detect state, look up matching docs pages
        ...
```

Output ejemplo:

```
💡 Tu proyecto tiene 12 documentos pero no tiene .cortex/org.yaml.
   Probablemente necesites Enterprise.

   Leé:
   → /enterprise/overview
   → /enterprise/quickstart

   O ejecutá: cortex setup enterprise
```

### Fase 7.6 — Tests E2E (0.5 día)

`tests/e2e/test_docs_tutor_integration.py`:

- [ ] Build tarball local.
- [ ] Mock GitHub release endpoint.
- [ ] `cortex docs-sync` → exit 0.
- [ ] `cortex tutor` (TUI) → mostrar tópicos desde vault.
- [ ] `cortex tutor ask "..."` → respuesta con score > 0.5.
- [ ] `cortex hint --from-docs` → output esperado.

### Fase 7.7 — Documentación dentro del docs (0.5 día)

- [ ] `/cli/tutor/docs-sync.mdx` — referencia del comando.
- [ ] `/cli/tutor/ask.mdx` — referencia.
- [ ] `/concepts/docs-tutor-bridge.mdx` — explanation de la arquitectura.
- [ ] `/guides/sync-docs-locally.mdx` — how-to.

## Criterios de aceptación

- ✅ Tarball se genera y publica en CI con cada release del docs.
- ✅ `cortex docs-sync` descarga, valida, extrae e indexa correctamente.
- ✅ `cortex tutor ask "X"` retorna resultados relevantes para queries básicas (test con 20 queries).
- ✅ `cortex tutor` (TUI) carga tópicos desde el vault sincronizado.
- ✅ Hard-coded fallback funciona si no hay sync.
- ✅ `cortex hint --from-docs` recomienda páginas según estado.
- ✅ Tests E2E verdes en CI.
- ✅ Documentación del feature dentro del propio docs.

## Validación de calidad

### Query bench

Lista de 20 queries con respuesta esperada:

| Query | Página esperada |
| --- | --- |
| "cómo instalo cortex" | `/getting-started/installation` |
| "qué es RRF" | `/concepts/rrf-retrieval` |
| "cómo configuro enterprise" | `/enterprise/quickstart` |
| "diferencia entre observe y assist" | `/autopilot/modes` |
| "promotion pipeline" | `/enterprise/promotion-pipeline` |
| "cortex_search tool" | `/mcp/tools/cortex_search` |
| "setup cursor" | `/ide/cursor` |
| "vault structure" | `/concepts/vault-structure` |
| ... | ... |

Test corre las 20 queries; ≥ 17 deben retornar la página esperada como #1 o #2.

## Riesgos y mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
| --- | --- | --- | --- |
| MDX components no renderizan en CLI | Alta | Medio | Convertir a Markdown plano en tarball; componentes complejos = excluded |
| Tarball es muy grande | Baja | Medio | Excluir assets binarios; comprimir |
| `cortex index-docs` falla con nuevo schema | Media | Alto | Tests de regresión en CI |
| Refactor tópicos rompe backwards compat | Media | Alto | Fallback hard-coded mantenido; flag explícito |
| Query bench: ≤ 17/20 pasa | Media | Medio | Tuning de RRF weights, fix de chunking |

## Cronograma

| Sub-fase | Días-persona |
| --- | --- |
| 7.1 Tarball pipeline | 1.5 |
| 7.2 docs-sync | 2 |
| 7.3 tutor ask | 1.5 |
| 7.4 Refactor tópicos | 2 |
| 7.5 hint --from-docs | 0.5 |
| 7.6 Tests E2E | 0.5 |
| 7.7 Doc del feature | 0.5 |
| Buffer | 0.5 |
| **Total** | **9** |

## Decisiones pendientes (a confirmar antes de empezar)

| # | Decisión | Recomendación |
| --- | --- | --- |
| D1 | Distribuir tarball como GH release | ✅ Confirmar |
| D2 | Schema versionado del tarball | ✅ `schema_version: 1` |
| D3 | Idiomas: descargar todos o uno? | Por defecto solo `lang` configurado; flag para todos |
| D4 | Cache compartido entre proyectos | Sí, en `~/.cache/cortex/docs/` |
| D5 | `cortex tutor ask` consume tokens si LLM enabled? | No por default; opcional `--summarize` con LLM |

## Siguiente fase

→ [Fase 08 — Versionado e i18n](fase-08-versionado-i18n.md)
