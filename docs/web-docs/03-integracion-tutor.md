---
title: Integración Docs ↔ Tutor — Arquitectura crítica
doc_type: explanation
status: draft
parent: README.md
priority: critical
---

# Integración Docs ↔ Tutor

> **Este documento describe la decisión arquitectónica más distintiva del proyecto docs.**
> Cualquier desviación de este diseño debe debatirse antes de implementarse.

## 1. Por qué este documento existe

El usuario solicita explícitamente:

> *"La idea es que esta web de documentación esté hecha y pueda ser utilizada mediante el tutor de cortex (ya implementado pero básico), la idea final es que el usuario tenga dos alternativas, entrar a la web o bien preguntarle al tutor y que tenga la última información de la documentación actualizada."*

Esto requiere que el `cortex tutor` (CLI offline) **consuma exactamente la misma fuente de verdad** que el sitio web. No copias, no exports manuales: **un solo content/, dos consumidores**.

## 2. Estado actual del tutor

(Resumen del análisis del repo — fuente: `cortex/tutor/` + `docs/tutor/PLAN-TUTOR-HINT.md`)

### 2.1 Componentes existentes

| Componente | Archivo | Función |
| --- | --- | --- |
| TUI engine | `cortex/tutor/engine.py` | Renderiza menú interactivo con `rich` |
| Hint engine | `cortex/tutor/hint.py` | Detecta estado del proyecto, emite tip contextual |
| 7 tópicos hard-coded | `cortex/tutor/topics/*.py` | Cada uno es una clase Python con strings rich-formateados |
| Comando CLI | `cortex/cli/main.py` (`tutor`, `hint`) | Expone TUI |

### 2.2 Limitaciones actuales

1. **Contenido estático** en clases Python — cualquier cambio en docs requiere modificar `.py`.
2. **No hay search dentro del tutor** — no podés preguntar `cortex tutor ask "X"`.
3. **No consume docs externos** — el `guide_path` apunta a archivos en `docs/guides/` pero el tutor no los lee.
4. **No hay versionamiento** — el contenido del tutor no se sincroniza con versiones de Cortex.

### 2.3 Lo que ya funciona y debemos preservar

- ✅ El comando `cortex tutor` con menú interactivo offline.
- ✅ El comando `cortex hint` con detección de estado.
- ✅ La arquitectura de **tópicos como objetos** (`TutorTopic` protocol).
- ✅ Renderizado terminal con `rich`.

## 3. Modelo objetivo

```
┌─────────────────────────────────────────────────────────────────┐
│                  cortex-web/apps/docs/content/                  │
│  (Markdown + frontmatter — fuente única de verdad)              │
└──────────────────┬──────────────────────────┬───────────────────┘
                   │                          │
                   │ Build (Astro)            │ Pipeline `cortex docs-sync`
                   ▼                          ▼
┌─────────────────────────────────┐  ┌────────────────────────────────┐
│  docs.cortex.dev                │  │  vault/cortex-docs/            │
│  (sitio web estático)           │  │  (mirror local en vault del    │
│                                 │  │   usuario, con índice ChromaDB)│
│  Consumidor: humano vía browser │  │                                │
│                                 │  │  Consumidor: cortex tutor      │
└─────────────────────────────────┘  └────────────────────────────────┘
```

## 4. Arquitectura propuesta

### 4.1 Capas

**Capa 1 — Fuente única**

- Directorio `apps/docs/content/` en el repo `cortex-web`.
- Markdown con frontmatter canónico (ver [`02-taxonomia-contenido.md`](02-taxonomia-contenido.md)).
- Publicado como paquete npm `@cortex/docs-content` con cada release.

**Capa 2 — Distribución dual**

- **Web**: Astro Starlight builds estáticos en `docs.cortex.dev`.
- **Tutor**: comando nuevo `cortex docs-sync` que descarga el paquete versionado y lo mirror-ea al vault local del usuario.

**Capa 3 — Indexación**

- En el vault local del usuario, los docs sincronizados son **indexados con `cortex index-docs`** (ya existe) → quedan disponibles via búsqueda híbrida RRF.

**Capa 4 — Consumo**

- **Web**: navegación + Pagefind + búsqueda semántica vía MCP.
- **Tutor**:
  - `cortex tutor` (existente) — menú TUI, ahora con tópicos cargados dinámicamente del vault sincronizado.
  - `cortex tutor ask "..."` (nuevo) — pregunta libre que hace RRF sobre el vault de docs y retorna párrafo + link.
  - `cortex hint` (existente) — ahora puede recomendar páginas específicas del docs basadas en estado.

## 5. Comando nuevo: `cortex docs-sync`

### 5.1 Diseño

```bash
# Sincroniza la documentación oficial de la versión instalada al vault local
cortex docs-sync

# Forzar versión específica
cortex docs-sync --version 0.5.0

# Sincronizar solo una sección
cortex docs-sync --section enterprise

# Listar versiones disponibles
cortex docs-sync --list

# Dónde se guarda
cortex docs-sync --where    # Print path
```

### 5.2 Comportamiento

1. Detecta versión de Cortex instalada (`cortex --version`).
2. Descarga `@cortex/docs-content@<version>` desde npm registry (o GitHub release tarball).
3. Extrae a `<workspace>/.cortex/vault/cortex-docs/`.
4. Llama internamente a `cortex index-docs` sobre ese subdirectorio.
5. Marca en `.cortex/workspace.yaml`:
   ```yaml
   docs_sync:
     version: 0.5.0
     synced_at: 2026-05-14T12:00:00Z
     path: cortex-docs/
   ```

### 5.3 Implementación

`cortex/docs_sync/`:

- `service.py` — `DocsSyncService.sync(version)`.
- `fetcher.py` — descarga del registro (npm o GitHub).
- `extractor.py` — extracción y validación de estructura.
- `indexer.py` — invoca `index-docs` sobre el path.

### 5.4 Sin internet

- Si no hay conexión:
  - Si ya hay docs sincronizados, usa los existentes.
  - Si no, falla con mensaje claro: "Sin docs locales. Conectate a internet o instalá manualmente desde `pip install cortex-docs`".

### 5.5 Distribución alternativa

Si no se publica como paquete npm, alternativa:

- **Tarball en GitHub releases**: `cortex-docs-0.5.0.tar.gz` adjunto a cada release.
- **Repo separado** clonable: `github.com/cortex/docs-content`.
- **Bundled con `cortex-memory`**: opcional via extra `pip install "cortex-memory[docs]"` (puede inflar paquete).

**Decisión recomendada**: GitHub release tarball — simple, sin nuevas dependencias.

## 6. Comando nuevo: `cortex tutor ask`

### 6.1 Diseño

```bash
cortex tutor ask "¿cómo configuro Enterprise?"
cortex tutor ask "diferencia entre observe y assist"
cortex tutor ask "qué es RRF" --format json
```

### 6.2 Comportamiento

1. Verifica que el vault tenga `cortex-docs/` sincronizado.
   - Si no, sugiere `cortex docs-sync`.
2. Hace búsqueda RRF híbrida sobre el vault de docs (scope: `local`, filter: `tags includes "docs"` o `vault_scope: cortex-docs`).
3. Retorna:
   - **Best match**: párrafo extraído + título de la página + link al docs web.
   - **Related**: 3-5 páginas relacionadas (top-k de la búsqueda).
4. Salida formato `rich` por default; `--format json` para parsing programático.

### 6.3 Ejemplo de output

```
$ cortex tutor ask "¿cómo configuro Enterprise?"

  ───────────────────────────────────────────────────────────
   📘 Setup Enterprise — Cortex Docs · v0.5.0
  ───────────────────────────────────────────────────────────

  Cortex Enterprise se configura mediante `.cortex/org.yaml`, un
  archivo declarativo que define la topología corporativa. Podés
  usar un preset (small-company, multi-project-team, regulated-
  organization) o configurar custom. El wizard interactivo te
  guía:

      cortex setup enterprise

  ───────────────────────────────────────────────────────────
   📚 Páginas relacionadas
  ───────────────────────────────────────────────────────────
   1. /enterprise/org-yaml-reference         (score 0.91)
   2. /enterprise/presets                    (score 0.87)
   3. /enterprise/promotion-pipeline         (score 0.72)
   4. /enterprise/governance-profiles        (score 0.65)
   5. /guides/configure-enterprise           (score 0.58)

   🌐 Web: https://docs.cortex.dev/v0.5.0/enterprise/setup
```

### 6.4 Implementación

`cortex/tutor/ask.py`:

- `AskEngine.ask(query, format='rich')`.
- Usa `AgentMemory.retrieve()` con filtros.
- Renderiza con `rich` o serializa JSON.

## 7. Refactor del tutor TUI (tópicos dinámicos)

### 7.1 Estado actual

Hard-coded:

```python
class GettingStartedTopic(TutorTopic):
    @property
    def title(self): return "Primeros Pasos"
    def render(self, console): console.print("...")
```

### 7.2 Estado objetivo

```python
class MarkdownTopic(TutorTopic):
    def __init__(self, doc_path: Path, frontmatter: dict, body: str):
        self._meta = frontmatter
        self._body = body

    @property
    def title(self): return self._meta['title']
    @property
    def slug(self): return self._meta['slug']
    @property
    def guide_path(self): return f"https://docs.cortex.dev/{self.slug}"

    def render(self, console):
        # Render Markdown body con rich, truncado a ~25 líneas
        ...
```

Loader:

```python
def load_topics_from_vault(vault_path: Path) -> list[TutorTopic]:
    """Loads all docs marked with tag 'tutor-topic' or doc_type 'tutorial'."""
    docs_dir = vault_path / 'cortex-docs'
    topics = []
    for md_file in docs_dir.rglob('*.md'):
        fm, body = parse_markdown(md_file)
        if 'tutor-topic' in fm.get('tags', []) or fm.get('doc_type') == 'tutorial':
            topics.append(MarkdownTopic(md_file, fm, body))
    return sorted(topics, key=lambda t: fm.get('tutor_order', 99))
```

### 7.3 Frontmatter especial para tutor

Páginas que aparecen como tópicos del TUI tutor llevan:

```yaml
---
title: Primeros Pasos
doc_type: tutorial
tags: [getting-started, tutor-topic]
tutor:
  icon: "🚀"
  one_liner: "Cómo instalar y empezar"
  order: 1
  terminal_summary: |
    Renderizado optimizado para terminal — máximo 25 líneas.
    Usa rich markup permitido: [bold], [accent], [code].
---

# Primeros Pasos

(contenido completo, web)
```

El campo `tutor.terminal_summary` es **el render que ve el tutor TUI**. El body completo es lo que ve la web.

Si no hay `tutor.terminal_summary`, el tutor renderiza un summary autogenerado (primer párrafo + bullets de H2).

### 7.4 Backwards compatibility

- Los 7 tópicos hard-coded actuales (`getting_started.py`, etc.) se **mantienen como fallback** si el vault no tiene docs sincronizados.
- Cuando hay docs sincronizados, se usan los del vault preferentemente.
- Comando `cortex tutor --source builtin` fuerza uso de los hard-coded.

## 8. Comando nuevo: `cortex hint --from-docs`

`hint` actual sugiere comandos basados en estado del proyecto. Extender para:

```bash
cortex hint --from-docs    # Sugiere páginas del docs basadas en estado
```

Output:

```
   💡 Tu proyecto no tiene `.cortex/org.yaml`. ¿Necesitás Enterprise?
   
   Lee:
   → /enterprise/overview
   → /enterprise/setup
   → /guides/configure-enterprise
   
   O ejecutá: cortex setup enterprise
```

## 9. Pipeline de actualización

```
1. Dev escribe Markdown en cortex-web/apps/docs/content/
2. PR merged → CI build:
   a. Genera site estático → deploys a docs.cortex.dev
   b. Genera tarball cortex-docs-x.y.z.tar.gz → publica en GitHub release
3. Usuario corre `cortex docs-sync`:
   a. Descarga tarball matching version
   b. Extrae a vault/cortex-docs/
   c. Invoca cortex index-docs sobre el path
4. Usuario corre `cortex tutor` o `cortex tutor ask` → consume el índice
```

## 10. Contratos críticos

| Contrato | Definición | Quien lo valida |
| --- | --- | --- |
| Frontmatter schema | Ver [`02-taxonomia-contenido.md`](02-taxonomia-contenido.md) | CI del docs (Zod) + `cortex index-docs` validator |
| Tarball structure | Plain `content/` con todos los `.md` + `index.json` raíz | CI publish + DocsSyncService.extractor |
| `index.json` | Lista de todos los docs con metadata | Generado en build |
| API DocsSyncService | `sync(version=None) -> SyncResult` | Tests unitarios |
| API AskEngine | `ask(query, format='rich') -> AskResult` | Tests unitarios |
| MCP tool `cortex_docs_ask` (futuro) | Exposición del AskEngine via MCP | Tests integración MCP |

## 11. Riesgos arquitectónicos

| Riesgo | Probabilidad | Impacto | Mitigación |
| --- | --- | --- | --- |
| Tarball cambia formato y rompe DocsSync | Media | Alto | Schema versionado en `index.json`; tests breaking compatibility |
| Vault del usuario crece mucho con docs | Baja | Bajo | Docs ocupa < 5MB típicamente |
| Usuario tiene Cortex vX, instala docs vY incompatibles | Media | Medio | `docs-sync` valida `requires_cortex_version` del tarball |
| Tutor en CLI no puede renderizar markdown complejo | Alta | Medio | Subset rendering: solo headings, paragraphs, code, lists, callouts |
| RRF retrieve devuelve párrafo aislado sin contexto | Alta | Medio | Cada chunk lleva metadata de la página padre; tutor muestra título antes |
| Performance del index para vault con miles de chunks | Baja | Bajo | Docs Cortex tiene < 200 páginas estimadas; ChromaDB maneja eso |

## 12. Decisiones pendientes

| # | Decisión | Estado |
| --- | --- | --- |
| D1 | Tarball vs npm vs git submodule para distribución | **Recomendado: tarball GitHub release** |
| D2 | `cortex docs-sync` corre auto al instalar? | Sugerencia: opt-in; banner en `cortex setup` |
| D3 | Caché de tarballs (un solo download para múltiples proyectos) | Sí, en `~/.cache/cortex/docs/` |
| D4 | Exposición vía MCP del docs (tool nuevo `cortex_docs_ask`) | V1.1 — no bloqueante para V1 |
| D5 | i18n: vault sincroniza solo idioma elegido? | Sí, configurable en `cortex docs-sync --lang en` |

## 13. Integración con MCP (futuro V1.1)

Una vez `AskEngine` funciona, exponer como MCP tool:

```python
@tool
def cortex_docs_ask(query: str, top_k: int = 5) -> AskResult:
    """Ask a question to Cortex's official documentation."""
    return ask_engine.ask(query, top_k=top_k)
```

Esto permite que **cualquier agente IA** (Claude Code, Cursor, Pi) pregunte al docs de Cortex vía MCP, no solo el tutor CLI.

## 14. Plan de implementación

Cubierto en detalle en [`fases/fase-07-puente-tutor.md`](fases/fase-07-puente-tutor.md). Resumen:

1. **Fase 07.1**: Crear `cortex docs-sync` command + tarball pipeline.
2. **Fase 07.2**: Crear `cortex tutor ask` command.
3. **Fase 07.3**: Refactor tópicos del tutor TUI para cargar dinámicamente.
4. **Fase 07.4**: Extender `cortex hint` con `--from-docs`.
5. **Fase 07.5**: Tests E2E del flujo completo.
