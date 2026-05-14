---
title: Taxonomía de Contenido — Cortex Docs
doc_type: reference
status: draft
parent: README.md
---

# Taxonomía de Contenido

Este documento define **cómo se escribe**, **cómo se etiqueta** y **cómo se valida** cada documento dentro del docs site. Es el **contrato** que une al consumidor humano (web) con el consumidor maquinal (tutor + búsqueda semántica).

## 1. DocTypes

Inspirados en el módulo `cortex/documentation/` (canónico — ver `docs/canonical-documentation/`):

| `doc_type` | Diátaxis | Propósito | Ejemplo |
| --- | --- | --- | --- |
| `tutorial` | Tutorials | Aprender haciendo, paso a paso, con outcome verificable | `getting-started/first-session.md` |
| `how-to` | How-to | Resolver un problema concreto | `guides/configure-enterprise.md` |
| `reference` | Reference | Información técnica precisa, look-up | `cli/memory/search.md` |
| `explanation` | Explanation | Comprender el "por qué" o "cómo funciona" | `concepts/rrf-retrieval.md` |
| `glossary` | Reference | Definiciones de términos | `concepts/glossary.md` |
| `index` | — | Landing de sección con cards | `cli/overview.md` |
| `changelog` | Reference | Historial de versiones | `reference/changelog.md` |

## 2. Frontmatter — schema canónico

Todo archivo `.md` o `.mdx` declara frontmatter YAML al principio:

```yaml
---
title: "Cortex search — Búsqueda híbrida en la memoria"
doc_type: reference
summary: |
  Reference del comando `cortex search`: sintaxis, flags, ejemplos y
  comportamiento por scope.
slug: cli/memory/search
section: cli
parent: cli/memory
order: 30
audience: [developer, integrator]
tags: [search, memory, rrf, retrieval, hybrid, cli]
cli_commands: [cortex search]
mcp_tools: [cortex_search]
since_version: "0.1.0"
last_review: 2026-05-14
status: stable          # draft | preview | stable | deprecated
deprecated_in: null
replaced_by: null
contributors: [MachuaninEzequiel]
related: [cli/memory/context, cli/memory/stats, concepts/rrf-retrieval]
edit_url: https://github.com/cortex/web/edit/main/apps/docs/content/cli/memory/search.md
---
```

### 2.1 Campos requeridos

| Campo | Tipo | Validación | Notas |
| --- | --- | --- | --- |
| `title` | string | 5-100 chars | Aparece en `<title>`, sidebar, search |
| `doc_type` | enum | Lista en §1 | Determina layout y campos extra requeridos |
| `summary` | string | 80-300 chars | Mostrado en cards, search snippets, ingestado por tutor |
| `slug` | string | kebab-case, sin `/leading` | URL final = `/{lang}/{slug}` |
| `section` | string | Una de las secciones top-level | Para breadcrumbs |
| `audience` | array | Subset de `[developer, integrator, enterprise, contributor]` | Para filtrado |
| `tags` | array | 3-10 strings, kebab-case | Para search y related |
| `since_version` | string | SemVer | Mostrado como VersionBadge |
| `last_review` | date | ISO 8601 | CI alerta si > 6 meses |
| `status` | enum | `draft \| preview \| stable \| deprecated` | Controla publicación |
| `edit_url` | url | URL absoluta | Botón "Editar en GitHub" |

### 2.2 Campos por DocType

**`reference` (comando CLI)**:

| Campo extra | Tipo | Notas |
| --- | --- | --- |
| `cli_commands` | array | Comandos cubiertos en esta página |
| `flags_documented` | array | Flags que aparecen en la página (validable contra `cortex --help`) |

**`reference` (MCP tool)**:

| Campo extra | Tipo | Notas |
| --- | --- | --- |
| `mcp_tools` | array | Nombres exactos de tools MCP |
| `tool_input_schema` | inline JSON | Schema del input (validable contra MCP server) |
| `tool_output_schema` | inline JSON | Schema del output |

**`tutorial`**:

| Campo extra | Tipo | Notas |
| --- | --- | --- |
| `prerequisites` | array | Páginas que deben leerse antes |
| `time_estimate_minutes` | integer | Para mostrar "~ 10 min read" |
| `outcome` | string | Qué logrará el lector al terminar |

**`how-to`**:

| Campo extra | Tipo | Notas |
| --- | --- | --- |
| `problem` | string | "Cómo X" |
| `prerequisites` | array | |

**`explanation`**:

| Campo extra | Tipo | Notas |
| --- | --- | --- |
| `related_concepts` | array | |

**`deprecated`**:

| Campo extra | Tipo | Notas |
| --- | --- | --- |
| `deprecated_in` | string | versión |
| `replaced_by` | string | slug de la página reemplazo |

### 2.3 Schema en código

`apps/docs/src/content/_schemas/doc.ts`:

```ts
import { z } from 'astro:content';

const baseSchema = z.object({
  title: z.string().min(5).max(100),
  doc_type: z.enum(['tutorial', 'how-to', 'reference', 'explanation', 'glossary', 'index', 'changelog']),
  summary: z.string().min(80).max(300),
  slug: z.string().regex(/^[a-z0-9-/]+$/),
  section: z.string(),
  audience: z.array(z.enum(['developer', 'integrator', 'enterprise', 'contributor'])),
  tags: z.array(z.string().regex(/^[a-z0-9-]+$/)).min(3).max(10),
  since_version: z.string().regex(/^\d+\.\d+\.\d+$/),
  last_review: z.coerce.date(),
  status: z.enum(['draft', 'preview', 'stable', 'deprecated']),
  edit_url: z.string().url(),
  // ...
});

export const docSchema = baseSchema.refine(/* refinement por doc_type */);
```

CI valida en cada PR — schema-fail = build-fail.

## 3. Naming conventions

| Tipo | Convención | Ejemplo |
| --- | --- | --- |
| Archivos | kebab-case, `.md` | `org-yaml-reference.md` |
| Slugs | kebab-case con `/` | `enterprise/org-yaml-reference` |
| Tags | kebab-case, singular | `memory`, `enterprise`, `cli` |
| IDs de heading | auto-generados de slugified text | `## Crear una spec` → `#crear-una-spec` |
| Cross-refs | uso de `[[slug]]` o link relativo | `[buscar en memoria](../cli/memory/search.md)` |

## 4. Tono y estilo

### 4.1 Voz

- **Segunda persona ("tú/vos")**, no impersonal.
- **Voseo argentino** sutil en ES ("podés", "creá").
- **Direct address** en EN: "you create", "you run".

### 4.2 Tiempos verbales

- **Imperativo** en how-tos: "Ejecutá", "Abrí", "Pegá".
- **Presente** en reference y explanation.
- **Pasado** solo para changelogs.

### 4.3 Reglas

1. Frases ≤ 25 palabras.
2. Párrafos ≤ 5 líneas.
3. Code blocks con `lang` siempre declarado.
4. Filenames en code blocks con `title="..."`.
5. Headings: H1 único = `# title`, H2 son secciones lógicas, H3 son subdivisiones, H4 son detalle.
6. No emojis decorativos en headings; ✅/❌ aceptables en tablas comparativas.
7. Capitalización: "title case" en headings EN, "Sentence case" en headings ES.
8. Code-inline para nombres de archivos, comandos cortos, flags, paths.
9. Mayúsculas: `YAML`, `JSON`, `URL`, `API`, `CLI` (no `yaml`, `json`...).
10. Prohibido `puede que`, `podríamos`, `de alguna manera`. Decir las cosas con claridad.

### 4.4 Ejemplos requeridos

- Cada reference tiene **≥ 1 ejemplo ejecutable**.
- Cada how-to termina con **bloque "Verificación"** mostrando cómo confirmar éxito.
- Cada tutorial tiene **outcome al inicio** y **resumen al final**.

## 5. Ejecutabilidad de snippets

### 5.1 Convención

Code blocks con flag `data-runnable` o `<CodeBlock runnable>` son **probados en CI**:

````markdown
```bash data-runnable
cortex search "auth jwt" --top-k 3
```
````

CI:

1. Extrae todos los bloques runnable.
2. Crea entorno limpio con Cortex instalado.
3. Inicializa proyecto de fixtures.
4. Ejecuta cada bloque.
5. Si exit code != 0, build falla.

### 5.2 Marcadores especiales

- `data-runnable`: ejecutar en CI.
- `data-output-of="<id>"`: este bloque es el output esperado del comando con id `id`.
- `data-skip-ci`: no ejecutar (para ejemplos pedagógicos).

## 6. Cross-referencing

### 6.1 Tipos de cross-ref

| Tipo | Sintaxis | Render |
| --- | --- | --- |
| Wiki-link a otra página | `[[slug]]` | Pre-procesado a link normal |
| Markdown link relativo | `[texto](../path.md)` | Link normal con validación |
| Reference link a comando | `<RefCli>cortex search</RefCli>` | Link tipado con tooltip |
| Reference link a MCP tool | `<RefMcp>cortex_search</RefMcp>` | Link tipado |
| Anchor en misma página | `[texto](#heading-id)` | Link normal |
| Link a Cortex GitHub | `[texto](github://path)` | Helper: expande a URL completa |

### 6.2 Validación

- CI corre `linkcheck` (markdown-link-check o custom) en todos los `.md`.
- Links rotos = build-fail.

## 7. Imágenes y assets

| Ruta | Uso |
| --- | --- |
| `apps/docs/public/img/<section>/` | Imágenes por sección |
| `apps/docs/public/diagrams/` | Diagramas SVG (idealmente, no PNG) |
| `apps/docs/public/screenshots/` | Screenshots de UI |
| `apps/docs/src/components/Diagrams/` | Diagramas como componentes React (mejor que SVG estático) |

Reglas:

- **Alt text obligatorio**.
- **Formato preferente**: SVG > AVIF > WebP > PNG.
- **Captions**: usar `<Figure>` con `<Caption>` no `<img alt>` para descripciones largas.
- **Versiones light/dark**: usar `<ThemeImage>` con `src-light` y `src-dark`.

## 8. Glosario y términos canónicos

`/concepts/glossary.md` define **términos oficiales** que aparecen en todo el docs:

| Término | Definición |
| --- | --- |
| Vault | Base de conocimiento Markdown estructurada |
| Memoria episódica | ... |
| ... | ... |

Cualquier término en el body del docs puede envolverse en `<Term>vault</Term>` para mostrar tooltip con la definición del glosario.

## 9. Estados de la página (status)

| Status | Significado | Visibilidad |
| --- | --- | --- |
| `draft` | En escritura | Visible solo en preview deploys |
| `preview` | Lista para review | Visible en producción con banner "Preview" |
| `stable` | Publicada | Visible normal |
| `deprecated` | Reemplazada | Visible con banner + link a reemplazo |

## 10. Validaciones automatizadas

`apps/docs/scripts/validate-content.ts` corre en CI:

- ✅ Schema frontmatter (Zod).
- ✅ Slugs únicos cross-content.
- ✅ Tags conocidos (lint contra `tags-allowlist.ts`).
- ✅ `since_version` ≤ versión actual de Cortex.
- ✅ `last_review` < 6 meses para `status: stable`.
- ✅ Comandos CLI mencionados existen en `cortex --help` (parseado).
- ✅ MCP tools mencionadas existen en MCP server schema.
- ✅ Links internos resuelven.
- ✅ Imágenes referenciadas existen.
- ✅ Snippets `data-runnable` ejecutan limpio.

Build-fail si cualquiera falla.
