---
title: Fase 06 — Casos de uso y comparativa
doc_type: phase
phase: 6
status: pending
depends_on: [phase-05]
unlocks: [phase-07]
estimated_duration: 3 días-persona
---

# Fase 06 — Casos de uso y comparativa

## Objetivo

Construir las secciones `#casos-de-uso` y `#comparativa`. Aquí el visitante **se ve a sí mismo** en una historia (caso de uso) y **valida la diferenciación** (comparativa).

## Entregables

1. **Sección `#casos-de-uso`** con 3 historias narrativas (una por persona del producto).
2. **Sección `#comparativa`** con tabla diferencial (Sin memoria / Memoria casera / Cortex).
3. **Modales con detalle** por caso (opcional).
4. **Animaciones de transición** "antes/después" entre estados.

## Tareas detalladas

### 6.1 Sección Casos de uso (1.5 días)

`src/sections/UseCases.astro`:

- [ ] Eyebrow + H2 (copy en `03-estrategia-contenido.md` §3.7).
- [ ] 3 cards en grid (1 col mobile, 1 col tablet, 3 col desktop).
- [ ] Cada card representa una **persona**: Lucía (Tech Lead), Mateo (Founder), Daniel (CTO).

#### Estructura de cada card

```tsx
type UseCaseCard = {
  persona: { name: string; role: string; avatar: string };
  scenario: { before: string; after: string };
  outcome: string;
  detailLink: string;
};
```

Visual:

```
┌────────────────────────────────────────┐
│ [Avatar]  Lucía — Tech Lead, 7 devs    │
│                                        │
│ ANTES                                  │
│ ┌────────────────────────────────┐    │
│ │ Cada PR es inconsistente,      │    │
│ │ los agentes olvidan decisiones │    │
│ └────────────────────────────────┘    │
│                                        │
│        ↓ con Cortex                    │
│                                        │
│ DESPUÉS                                │
│ ┌────────────────────────────────┐    │
│ │ Memoria del equipo, no de las  │    │
│ │ personas. PRs consistentes.    │    │
│ └────────────────────────────────┘    │
│                                        │
│ "Recuperé 8 horas/semana"              │
│                          [Ver caso →]  │
└────────────────────────────────────────┘
```

#### Avatares

- [ ] Ilustraciones custom o iconos abstractos (no fotos stock).
- [ ] Variantes claro/oscuro.

#### Animación

- [ ] Card entra con `y: 30 → 0` stagger 100ms.
- [ ] Sección "Antes → Después" tiene transición visual: el bloque "Antes" se desvanece y aparece "Después" con `scale 0.95 → 1`.
- [ ] Trigger: hover o auto-loop cada 5s.

### 6.2 Modales con detalle (0.5 día) — Opcional V1

Si `[Ver caso →]` se implementa:

- [ ] Modal centered (desktop) o bottom sheet (mobile).
- [ ] Contenido más extenso: 2-3 párrafos contando la historia, métricas concretas, comando CLI ejemplo, screenshot.
- [ ] Botón "Cerrar" + Esc.
- [ ] Focus trap.

> **Decisión V1**: dejar el botón sin acción o link a un blog post placeholder. Implementar modales en V1.1 si hay tiempo.

### 6.3 Sección Comparativa (1 día)

`src/sections/Comparison.astro`:

- [ ] Eyebrow + H2 (copy en `03-estrategia-contenido.md` §3.8).
- [ ] **Tabla comparativa** responsive.

#### Estructura tabla

| Característica | Sin memoria | Memoria casera | **Cortex** |
| --- | --- | --- | --- |
| Persistencia entre sesiones | ❌ | ⚠️ Manual | ✅ Automática |
| Búsqueda híbrida | ❌ | ⚠️ Uno solo | ✅ RRF |
| Trazabilidad de decisiones | ❌ | ❌ | ✅ Specs + sesiones |
| Integración IDE nativa | ❌ | ❌ | ✅ 6 IDEs vía MCP |
| Gobernanza enterprise | ❌ | ❌ | ✅ `org.yaml` |
| Promotion pipeline auditable | ❌ | ❌ | ✅ candidate → promoted |
| Tutor offline integrado | ❌ | ❌ | ✅ `cortex tutor` |
| Setup en | n/a | Días | **3 comandos** |

#### Diseño

- [ ] La columna "Cortex" tiene **bg-elevated** + border accent + label "Recomendado".
- [ ] Iconos: ❌ rojo muted, ⚠️ amarillo, ✅ verde accent.
- [ ] En mobile, la tabla se convierte en **3 cards stacked** (una por opción) con bullets.
- [ ] Hover en fila highlightea toda la fila.

#### Animación

- [ ] Filas entran en stagger 50ms al scroll-into-view.
- [ ] La columna Cortex tiene un sutil glow accent en el border.

### 6.4 Microcopy y tono

- [ ] Asegurar que las historias suenan **realistas, no de marketing**.
- [ ] Evitar frases tipo "transformó completamente nuestra organización" — usar concreto: "recuperé 8 horas/semana".
- [ ] Las cifras pueden ser estimaciones honestas etiquetadas como "estimado" en V1.

## Criterios de aceptación

- ✅ Cards de casos de uso se leen como historias reales, no marketing.
- ✅ La transición "Antes/Después" es clara visualmente.
- ✅ La tabla comparativa es legible en mobile (cards stacked).
- ✅ Iconos diferenciados de forma consistente.
- ✅ Lighthouse Performance se mantiene ≥ 90.
- ✅ A11y: tabla con `<caption>`, `<th scope="col/row">`.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| Casos de uso suenan ficticios | Etiquetar cifras como "estimado" o validar con testers reales |
| Tabla comparativa "huele a vendedor" | Mantener tono honesto: "Memoria casera puede funcionar para casos simples" |
| Mobile: tabla rota visualmente | Test temprano en iPhone SE; usar cards si falla |

## Siguiente fase

→ [Fase 07 — Instalación y CTA](fase-07-instalacion-cta.md)
