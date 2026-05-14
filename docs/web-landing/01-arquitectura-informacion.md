---
title: Arquitectura de Información — Cortex Landing
doc_type: reference
status: draft
parent: README.md
---

# Arquitectura de Información

Este documento define **qué hay** en la landing, **en qué orden** y **con qué jerarquía**.

## 1. Site map

La landing es una **single-page application** con anchors profundos para cada sección, complementada por **3 páginas auxiliares**:

```
/                        ← Landing principal (single-page, ~10 secciones)
/enterprise              ← Página dedicada Enterprise
/changelog               ← Mirror del CHANGELOG.md formateado
/legal                   ← Privacy, terms, license
```

Cada sección dentro de `/` tiene **anchor explícito** (`/#hero`, `/#problema`, etc.) para que sea linkable.

## 2. Orden narrativo (single-page)

El orden no es arbitrario: sigue el **arco narrativo clásico** (problema → solución → demostración → adopción) ajustado al producto.

| # | Sección | Anchor | Propósito | Tiempo lectura |
| --- | --- | --- | --- | --- |
| 1 | Hero | `#hero` | Captura atención + propuesta de valor en una frase | 5s |
| 2 | Problema | `#problema` | Identificar dolor: amnesia de sesión, falta de gobernanza | 20s |
| 3 | Solución (overview) | `#solucion` | Cortex en una imagen: tripartito + memoria + governance | 30s |
| 4 | Arquitectura interactiva | `#arquitectura` | Diagrama explorable de los módulos | 60-120s |
| 5 | Pilares tecnológicos | `#pilares` | Memoria Híbrida RRF, Tripartito, Enterprise, Autopilot | 60s |
| 6 | Demos en vivo | `#demos` | WebGraph embebido + CLI animado + Autopilot replay | 90s |
| 7 | Casos de uso | `#casos-de-uso` | 3 personas con historias y "antes/después" | 45s |
| 8 | Comparativa | `#comparativa` | Cortex vs. "agente sin memoria" vs. "memoria casera" | 30s |
| 9 | Instalación | `#instalacion` | 3 pasos con copy-paste + IDE picker | 30s |
| 10 | Comunidad y siguiente paso | `#comunidad` | Links a docs, GitHub, Discord/contacto, footer | 15s |

Total estimado de scroll completo: **~7 minutos**.

## 3. Header y navegación

```
[Cortex logo]   Producto · Arquitectura · Enterprise · Docs · GitHub      [Probar Cortex →]
                                                              [🌐 ES/EN] [🌓 tema]
```

- **Sticky** con blur backdrop en scroll.
- **Cambia color** según sección (light en sección oscura, dark en sección clara).
- **Mobile**: hamburger → drawer lateral.

### Links del menú principal

| Link | Destino |
| --- | --- |
| Producto | `/#pilares` |
| Arquitectura | `/#arquitectura` |
| Enterprise | `/enterprise` |
| Docs | `https://docs.cortex.dev` ([`web-docs`](../web-docs/README.md)) |
| GitHub | `https://github.com/MachuaninEzequiel/Cortex` |
| CTA primario | `/#instalacion` |

## 4. Footer

```
Cortex — Memoria corporativa para agentes IA

PRODUCTO            RECURSOS              COMUNIDAD             LEGAL
Características     Docs                  GitHub                Privacy
Enterprise          Quickstart            Discord (?)           Términos
Changelog           CLI Reference         Contacto              Licencia (MIT)
Roadmap             Tutoriales            X / Twitter

© 2026 Cortex · v0.5.0 · Hecho con cariño en 🇦🇷
```

## 5. Página `/enterprise`

Página dedicada con su propia narrativa (Persona C):

| Sección | Contenido |
| --- | --- |
| Hero enterprise | Frase específica: "Gobernanza, retención y trazabilidad para tu organización" |
| Topología corporativa | Visualización del modelo `org.yaml` + presets |
| Pipeline de promoción | Diagrama: candidate → reviewed → promoted |
| Retention policies | Tabla con doctypes y retención por defecto |
| Compliance y seguridad | Security model, threat model, audit trail |
| Casos de adopción | (placeholder en V1) |
| Formulario contacto | "Hablar con el equipo" |

## 6. Página `/changelog`

Render del `CHANGELOG.md` del repo con:

- Filtro por versión.
- Toggle "ver solo breaking changes".
- Link a release notes en GitHub.

## 7. Página `/legal`

Tres anchors:

- `/legal#privacy` — Política de privacidad (analytics, cookies, formularios).
- `/legal#terms` — Términos de uso del sitio.
- `/legal#license` — Mención de licencia MIT del software.

## 8. CTAs (Call-to-Actions)

| CTA | Lugar | Acción | Conversión esperada |
| --- | --- | --- | --- |
| `[Probar Cortex →]` | Header (sticky) | Anchor a `#instalacion` | 8% |
| `[Ver cómo funciona →]` | Hero | Anchor a `#demos` | 25% |
| `[Leer la doc →]` | Hero secundario | Link a `docs.cortex.dev` | 18% |
| `[Explorar arquitectura ⇲]` | Fin de `#solucion` | Anchor a `#arquitectura` con autoplay tour | 12% |
| `[Copiar instalación 📋]` | Sección instalación | Copy + toast confirmación | 12% |
| `[Ver caso completo →]` | Cada tarjeta de caso de uso | Modal con detalle | 6% |
| `[Hablar con el equipo →]` | Sección Enterprise + footer | Form `/enterprise#contacto` | 1% |
| `[Ver en GitHub →]` | Múltiples lugares | Link GH (target _blank) | 15% |

## 9. Jerarquía visual

| Nivel | Uso |
| --- | --- |
| **H1** | Solo en hero. Tipo Display, >72px. |
| **H2** | Inicio de cada sección. Tipo Title, 40-56px. |
| **H3** | Subdivisiones dentro de una sección (ej. cada pilar). 28-32px. |
| **H4** | Cards y micro-secciones. 20-22px. |
| **Body** | 16-18px, line-height 1.6. |
| **Caption** | 13-14px, color secundario. |

## 10. Navegación lateral progresiva

Una **barra de progreso vertical** (right rail, desktop ≥1280px) muestra:

- Punto activo de la sección actual.
- Click en cualquier punto → scroll-to.
- Auto-hide en mobile y en `prefers-reduced-motion`.

## 11. Microcopy crítico

Frases que se repiten y deben estar centralizadas en `content/microcopy.{lang}.ts`:

| Key | ES | EN |
| --- | --- | --- |
| `cta.try` | Probar Cortex | Try Cortex |
| `cta.docs` | Leer la doc | Read the docs |
| `cta.copy` | Copiar | Copy |
| `cta.copied` | ¡Copiado! | Copied! |
| `cta.enterprise` | Hablar con el equipo | Talk to the team |
| `nav.product` | Producto | Product |
| `nav.architecture` | Arquitectura | Architecture |
| `nav.enterprise` | Enterprise | Enterprise |

## 12. Estados especiales

- **`prefers-reduced-motion: reduce`**: animaciones de scroll se reemplazan por fade-in instantáneo; demos en loop se pausan.
- **Sin JavaScript**: la landing **debe ser legible y navegable** sin JS (las islas Astro se hidratan progresivamente, pero el contenido base es SSR).
- **Sin conexión a Cortex backend**: la demo WebGraph cae a snapshot estático (ver Fase 05).
- **Idioma no soportado**: fallback a inglés con banner sugiriendo cambio.
