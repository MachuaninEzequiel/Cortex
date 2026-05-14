---
title: Visión, audiencias y objetivos — Cortex Docs
doc_type: explanation
status: draft
parent: README.md
---

# Visión, audiencias y objetivos

## 1. Visión

Construir el **sitio oficial de documentación de Cortex**, modelado a partir de la experiencia de [docs.claude.com/claude-code](https://docs.claude.com/en/docs/claude-code/overview), con una característica fundadora propia:

> **Una fuente, dos canales.**
> El mismo Markdown que renderiza el sitio web es consumido por el `cortex tutor` (CLI offline), de modo que cualquier desarrollador puede acceder a la documentación **desde el navegador** o **preguntándole al tutor en su terminal**, con resultados sincronizados.

Esto convierte a la documentación de Cortex en una **interfaz dual**: experiencia visual para descubrimiento (web) y experiencia conversacional para uso cotidiano (tutor en CLI o vía MCP).

## 2. Audiencias objetivo

### Persona A — Desarrollador adoptando Cortex ("Joaquín")

- **Contexto**: Lleva 1-7 días con Cortex instalado. Está aprendiendo qué hace cada comando.
- **Necesita**: Quickstart limpio, "how-to" para tareas comunes, conceptos básicos sin sobrecarga.
- **Path de éxito**: Quickstart → primera spec → primera session note → primer search.
- **Páginas críticas**: Quickstart, CLI Reference > `setup`, `create-spec`, `save-session`, `search`.

### Persona B — Desarrollador avanzado / integrador ("Lara")

- **Contexto**: Ya usa Cortex, ahora quiere integrar con CI/CD, conectar otro IDE, customizar pipeline.
- **Necesita**: Reference detallado, conceptos avanzados (RRF, intent detection), MCP protocol, custom modules.
- **Páginas críticas**: Architecture, MCP Reference, Pipeline modules, IDE integrations, Configuration reference.

### Persona C — Equipo Enterprise ("Daniel y Rocío")

- **Contexto**: Implementan Cortex a nivel organización; necesitan trazabilidad, compliance, governance.
- **Necesita**: Enterprise guide, `org.yaml` reference, promotion pipeline how-tos, retention policies, security model.
- **Páginas críticas**: Enterprise overview, `org.yaml` reference, Promotion workflows, Retention policies, Threat model.

### Persona D — El propio Cortex Tutor (audiencia maquinal)

- **Contexto**: El `cortex tutor` ingiere el contenido del site para responder preguntas del usuario en CLI.
- **Necesita**: Frontmatter estructurado, summary corto, tags consistentes, chunks digestibles, ejemplos ejecutables.
- **Criterio**: Cada página debe ser entendible **fuera de contexto** — el tutor puede traer un párrafo aislado y debe seguir teniendo sentido.

Esta persona maquinal es la **decisión arquitectónica más distintiva** del proyecto y está cubierta en detalle en [`03-integracion-tutor.md`](03-integracion-tutor.md).

## 3. Jobs-to-be-done (JTBD)

| Cuando el usuario… | Quiere… | Para que… |
| --- | --- | --- |
| Acaba de instalar Cortex | Encontrar 5 comandos esenciales en 60 segundos | Sentir que ya está produciendo |
| Falla un comando | Encontrar la página exacta del error/parámetro | Desbloquearse en < 5 min |
| Va a integrar nuevo IDE | Encontrar la guía paso a paso de ese IDE | Hacerlo solo, sin tickets |
| Va a evaluar Enterprise | Encontrar `org.yaml` reference + presets | Definir su topología |
| Pregunta al tutor "¿cómo hago X?" | El tutor responda con el contenido del docs | Ahorrarse abrir el navegador |
| Está leyendo el CHANGELOG | Encontrar la página de la feature nueva | Empezar a usarla rápido |

## 4. Objetivos del producto

### Objetivos primarios (medibles)

1. **Tasa de auto-servicio**: ≥ 80% de preguntas sobre Cortex deben resolverse mediante el docs (vs. abrir un issue o preguntar en Discord).
2. **Tutor accuracy**: ≥ 85% de las preguntas hechas al `cortex tutor ask "..."` (nuevo subcomando) deben recuperar contenido relevante con score ≥ 0.7.
3. **Time-to-first-success**: usuario nuevo logra ejecutar su primer `cortex save-session` exitoso en ≤ 10 minutos siguiendo Quickstart.
4. **Cobertura**: 100% de los comandos CLI documentados, 100% de las tools MCP documentadas, 100% de las opciones de `config.yaml` y `org.yaml` documentadas.
5. **Frescura**: el docs no diverge del código por más de 1 release menor — el CI bloquea si `cortex --help` lista un comando que no tiene página.

### Objetivos secundarios

- **SEO**: top 5 para queries específicas tipo `["cortex memory mcp"]`, `["cortex autopilot install"]`, `["cortex org.yaml"]`.
- **Adoptantes documentados**: galería de "Built with Cortex" con ≥ 3 casos en 6 meses.
- **Contributor velocity**: PRs externos a `cortex-web/apps/docs` ≥ 1/mes en 6 meses.

### No-objetivos

- **No es un blog.** No hay posts de opinión, news, o roadmap narrativo (eso vive en `docs/vision/` del repo principal).
- **No es marketing.** El tono es **técnico, neutral, preciso**. La parte de "vender" Cortex es la landing (`web-landing`).
- **No es un libro.** Cada página debe ser auto-contenida; nadie lee linealmente.

## 5. Métricas instrumentadas

Eventos a trackear:

| Evento | Disparador | Propiedad |
| --- | --- | --- |
| `docs_pageview` | Carga de página docs | path, lang, version |
| `docs_search_query` | Submit de búsqueda | query, results_count, lang |
| `docs_search_click` | Click en resultado de búsqueda | query, result_path, rank |
| `docs_search_no_result` | Búsqueda sin resultados | query, lang |
| `docs_404` | Visit a página inexistente | path, referrer |
| `docs_thumbs_up` | Click en "¿útil?" feedback positivo | path |
| `docs_thumbs_down` | Click en "¿útil?" feedback negativo | path |
| `docs_external_click` | Click en link externo | path, dest |
| `docs_copy_code` | Click en copy de code block | path, lang |
| `docs_version_switch` | Cambio de versión | from, to |
| `docs_lang_switch` | Cambio de idioma | from, to |
| `tutor_query` | `cortex tutor ask "..."` ejecutado | (telemetría local opcional) |

## 6. Criterios de éxito del proyecto

El **proyecto docs** se considera exitoso si, al final de la Fase 09:

- ✅ Cobertura: 100% comandos CLI, 100% MCP tools, 100% opciones de config.
- ✅ Search Pagefind funcionando (full-text) + Search semántico (vía Cortex MCP).
- ✅ `cortex tutor ask` operativo, consumiendo el mismo content/.
- ✅ Tema claro/oscuro, ES/EN, versionado funcional.
- ✅ Lighthouse Mobile ≥ 90 en homepage y top 5 páginas más visitadas.
- ✅ axe a11y verde.
- ✅ CI bloquea PRs con docs desactualizados, links rotos o snippets que no compilan.

## 7. Diferenciadores vs. otras docs técnicas

| Característica | Docs típicas | Cortex Docs |
| --- | --- | --- |
| Markdown source | Sí | Sí |
| Search full-text | Algunos | Sí (Pagefind) |
| Search semántico | Muy pocos | Sí (vía Cortex MCP) |
| Acceso CLI offline | Casi nadie | **Sí — `cortex tutor`** |
| Acceso vía agent IA | Vía MCP | **Native** — el propio Cortex MCP expone el docs |
| Versionado por release | Sí | Sí |
| Ejecución de snippets en CI | Algunos | Sí — `cortex doctor` valida ejemplos |
| Frontmatter como contrato | Pocos | Sí — schema versionado |
| Bilingue (ES + EN) | Algunos | Sí |

El **diferenciador #1** es el acceso por tutor offline: la misma información, dos canales.

## 8. Riesgos y mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
| --- | --- | --- | --- |
| Cortex evoluciona y docs queda atrás | Alta | Alto | CI custom que detecta divergencia entre `cortex --help` y páginas |
| Tutor responde con docs obsoleto | Media | Alto | Indexación bumpeada por versión; tutor declara qué versión de docs consume |
| Pagefind no escala con tamaño | Baja | Medio | Probado hasta 5k páginas; Cortex está lejos |
| i18n duplica esfuerzo de mantenimiento | Alta | Medio | EN traducción auto-asistida + revisión humana; mantener priority high para ES |
| Tutor tiene que ser refactor mayor para esto | Alta | Medio | Plan explícito en Fase 07 con backwards compat |
