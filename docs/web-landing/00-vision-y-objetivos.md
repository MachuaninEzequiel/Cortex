---
title: Visión, audiencias y objetivos — Cortex Landing
doc_type: explanation
status: draft
parent: README.md
---

# Visión, audiencias y objetivos

## 1. Visión

Construir la **página de aterrizaje pública de Cortex** como una experiencia editorial-técnica moderna que comunique en menos de **60 segundos** la propuesta de valor del producto, y en menos de **5 minutos** entregue al visitante todo lo necesario para decidir si Cortex es para él/ella.

La landing **no enseña Cortex** (eso lo hace [`web-docs`](../web-docs/README.md)); **lo vende, lo muestra y lo seduce**. Es la pieza que abre la puerta.

> **Frase-norte de la página**: *"Cortex es la memoria corporativa y el sistema de gobernanza que los agentes de IA estaban esperando."*

## 2. Audiencias objetivo

Se priorizan tres personas, en este orden:

### Persona A — Tech Lead / Staff Engineer ("Lucía")

- **Contexto**: 5-12 años de experiencia, lidera 3-10 desarrolladores, está evaluando agentes IA en su organización.
- **Dolor real**: Sus desarrolladores usan Copilot/Cursor pero cada PR es inconsistente, los agentes olvidan decisiones arquitectónicas, y no hay forma de auditar qué decidió quién.
- **Lo que necesita ver en la landing**: gobernanza, trazabilidad, integración con Claude Code/Cursor, modelo tripartito, ejemplos reales de output.
- **CTA primario**: "Ver cómo funciona en 90 segundos" (demo embebida).
- **CTA secundario**: "Instalar y probar en mi proyecto" (link a Quickstart).

### Persona B — Indie Hacker / Founder Técnico ("Mateo")

- **Contexto**: Trabaja solo o con 1-2 cofundadores, usa Claude Code o Cursor a diario, su productividad depende del agente IA.
- **Dolor real**: Pierde 30 min al inicio de cada sesión re-explicando contexto al agente; las decisiones de la semana pasada se evaporaron.
- **Lo que necesita ver**: simplicidad de instalación, memoria persistente que "simplemente funciona", integración con su IDE preferido.
- **CTA primario**: "Instalación en 3 comandos" (copy-paste block).
- **CTA secundario**: "Ver vault de ejemplo" (galería).

### Persona C — Enterprise Architect / CTO ("Daniel")

- **Contexto**: Empresa de 50-500 personas, regulada o pre-regulada, debe convencer a Legal/Compliance de adoptar IA.
- **Dolor real**: Necesita gobernanza demostrable, retención de datos auditable, política multi-proyecto, soporte para compliance.
- **Lo que necesita ver**: sección Enterprise con `org.yaml`, retention policies, promotion pipeline, deployment on-prem, security model.
- **CTA primario**: "Hablar con el equipo" (formulario o email).
- **CTA secundario**: "Leer el manifiesto Enterprise" (link a doc).

> Persona D (académico / investigador) y persona E (DevRel / Educator) **no** son target primario en V1, pero el contenido no debe excluirlos.

## 3. Jobs-to-be-done (JTBD)

| Cuando el visitante… | Quiere… | Para que… |
| --- | --- | --- |
| Llega desde Twitter/HN | Entender qué es Cortex en 10 segundos | Decidir si merece otros 60 segundos |
| Llega desde un blog técnico | Ver arquitectura y ejemplos concretos | Validar que la solución es seria |
| Llega referido por un colega | Encontrar instalación rápida | Probar hoy mismo |
| Llega desde GitHub | Encontrar features detalladas | Compararlo con alternativas |
| Llega de búsqueda enterprise | Encontrar sección Enterprise + contacto | Iniciar evaluación formal |

## 4. Objetivos del producto-landing

### Objetivos primarios (medibles)

1. **Conversion to docs**: ≥ 35% de visitantes hace clic en algún link a `docs.cortex.dev` (web-docs).
2. **Conversion to install**: ≥ 12% copia el bloque de instalación (`pipx install...`).
3. **Engagement**: scroll-depth medio ≥ 65% en desktop, ≥ 50% en mobile.
4. **GitHub stars**: incremento ≥ 30% en los 30 días posteriores al lanzamiento (atribuible).
5. **Time-on-page**: ≥ 2:30 en sesiones que llegan a la sección "Arquitectura interactiva".

### Objetivos secundarios

- **Lead capture enterprise**: ≥ 5 leads cualificados/mes vía formulario "Hablar con el equipo".
- **SEO**: top 10 para `["cortex memory agent"]`, `["AI agent governance"]`, `["DevSecDocOps"]` en 90 días.
- **Citation**: aparecer en al menos 3 newsletters/blogs técnicos en el trimestre del lanzamiento.

### No-objetivos explícitos

- **No vendemos servicios**. No hay "contratá consultoría" en V1.
- **No es un sustituto del docs site**. La landing **no enseña** a usar Cortex; solo lo presenta.
- **No es un blog**. Habrá un link a blog si existe, pero no se publican posts ahí.
- **No requiere registro** para nada (excepto formulario enterprise).

## 5. Métricas instrumentadas

Eventos a trackear desde día 0 (ver [Fase 09](fases/fase-09-performance-seo-a11y.md) y [Fase 10](fases/fase-10-lanzamiento.md)):

| Evento | Disparador | Propiedad |
| --- | --- | --- |
| `pageview` | Carga de página | path, referrer, lang |
| `section_view` | Sección entra en viewport ≥ 50% | section_id, time_since_load |
| `cta_click` | Click en CTA primario/secundario | cta_id, destination |
| `install_copy` | Click en botón "copy" del install block | block_id |
| `demo_play` | Interacción con demo interactiva | demo_id |
| `arch_node_click` | Click en nodo del diagrama interactivo | node_id |
| `lang_switch` | Cambio de idioma | from, to |
| `theme_switch` | Cambio claro/oscuro | from, to |
| `enterprise_lead` | Submit form Enterprise | (sin PII en analytics) |

Stack analytics propuesto: **Plausible** (privacy-first, lightweight) + opcional **PostHog** para session replay si se cuenta con presupuesto.

## 6. Criterios de éxito del proyecto (no del producto)

El **proyecto landing** se considera exitoso si, al final de la Fase 10:

- ✅ Lighthouse (Mobile): Performance ≥ 90, Accessibility ≥ 95, Best Practices ≥ 95, SEO ≥ 95.
- ✅ Bundle JS inicial ≤ 100 KB gzipped (sin contar islas hidratadas lazy).
- ✅ TTI (Time to Interactive) ≤ 2.5s en 4G simulado.
- ✅ Zero errores en consola en producción.
- ✅ Cobertura de tests E2E ≥ 70% de paths críticos.
- ✅ Documentación interna completa (este plan + post-mortem post-launch).
- ✅ Plan de mantenimiento mensual definido.

## 7. Riesgos y mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
| --- | --- | --- | --- |
| Animaciones pesadas penalizan Lighthouse | Alta | Alto | Lazy-load, `prefers-reduced-motion`, presupuesto de animación por sección. |
| Demo WebGraph requiere backend en vivo | Media | Alto | Snapshot estático JSON exportado en build-time. |
| Copy en español aliena audiencia internacional | Media | Medio | i18n EN desde Fase 08, hreflang correcto. |
| Stack moderno desactualiza rápido | Media | Bajo | Astro + minimal islands; estabilidad ≥ 12 meses. |
| Cambios en branding tardíos | Baja | Alto | Aprobar identidad visual en Fase 00 con sign-off. |
