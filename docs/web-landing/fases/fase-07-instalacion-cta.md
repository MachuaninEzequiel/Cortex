---
title: Fase 07 — Instalación, CTAs y comunidad
doc_type: phase
phase: 7
status: pending
depends_on: [phase-06]
unlocks: [phase-08]
estimated_duration: 4 días-persona
---

# Fase 07 — Instalación, CTAs y comunidad

## Objetivo

Construir las secciones finales: `#instalacion`, `#comunidad`, **página `/enterprise` completa**, y todos los **CTAs cross-section**.

## Entregables

1. **Sección `#instalacion`** con wizard de instalación interactivo.
2. **Sección `#comunidad`** con cards finales.
3. **Página `/enterprise`** completa.
4. **Formulario Enterprise** funcional.
5. **CTAs cross-section** (header sticky behavior, scroll-to-top, etc.).
6. **Página `/changelog`** funcional (render del CHANGELOG.md del repo).

## Tareas detalladas

### 7.1 Sección Instalación (2 días)

`src/sections/Install.astro`:

- [ ] Eyebrow + H2 (copy en `03-estrategia-contenido.md` §3.9).
- [ ] Bloque principal: **3 pasos** con code blocks.
- [ ] **Selector de IDE** (tabs) que cambia el comando del paso 3.

#### Componente `<InstallWizard>`

Isla React `src/components/islands/InstallWizard.tsx`:

- 3 steps visibles secuencialmente, con número grande a la izquierda y bloque de código a la derecha.
- Cada bloque tiene botón **"Copiar"** que copia al clipboard y dispara evento `install_copy`.
- Toast confirmación "¡Copiado!".

#### Step 1 — Instalar Cortex

```bash
# Recomendado (global, vía pipx)
pipx install cortex-memory

# Alternativa (en .venv del proyecto)
pip install cortex-memory
```

Toggle ente pipx y pip.

#### Step 2 — Inicializar

```bash
cd mi-proyecto
cortex setup full
```

Caption: "Crea el workspace `.cortex/` con vault, memoria, skills y CI."

#### Step 3 — Conectar IDE

Tabs:

| Tab | Comando |
| --- | --- |
| Claude Code | `cortex inject --ide claude-code` |
| Cursor | `cortex inject --ide cursor` |
| Pi | `cortex inject --ide pi` + `npm install -g @mariozechner/pi-coding-agent` |
| VSCode + Cline | Crear `.vscode/mcp.json` (con snippet) |
| OpenCode | `cortex inject --ide opencode` |
| Codex | `cortex inject --ide codex` |

Cada tab muestra:

- [ ] Comando principal.
- [ ] Screenshot pequeño de "cómo se ve en tu IDE después".
- [ ] Link a docs específicas: `docs.cortex.dev/ide-{slug}`.

#### Pre-requisitos collapsible

`<details>` con:

- Python 3.10+
- Git
- pipx (recomendado)
- Plataformas soportadas: Windows, macOS, Linux

#### Microcopy final

> ¿Vienes de una organización regulada? Mirá [Cortex Enterprise →](/enterprise)

### 7.2 Sección Comunidad (0.5 día)

`src/sections/Community.astro`:

- [ ] Eyebrow "Open source, en serio" + H2.
- [ ] Body breve.
- [ ] 3 cards finales en grid:

| Card | Icono | Body | CTA |
| --- | --- | --- | --- |
| GitHub | `Star` | "Apoyá el proyecto" | `[Estrella en GitHub →]` |
| Docs | `BookOpen` | "Quickstart + referencia" | `[Leé la documentación →]` |
| Enterprise | `Building` | "Equipos y compliance" | `[Hablá con el equipo →]` |

### 7.3 Página `/enterprise` (1 día)

`src/pages/enterprise.astro`:

Estructura:

1. **Hero enterprise** — copy específico, visual de topología.
2. **Topología corporativa** — visualización de `org.yaml`.
3. **Pipeline de promoción** — diagrama animado candidate → reviewed → promoted.
4. **Retention policies** — tabla por doctype.
5. **Compliance y seguridad** — security model summary + link a threat-model.md.
6. **Formulario** "Hablar con el equipo".

#### Reutilización

- [ ] El visual de topología puede reutilizarse del Pilar 4 (`EnterpriseTopologyViz`) con props distintos.
- [ ] Las tablas siguen el sistema de diseño establecido.

#### Formulario Enterprise

`src/components/islands/EnterpriseForm.tsx`:

Campos:

| Campo | Tipo | Required |
| --- | --- | --- |
| Nombre completo | text | ✅ |
| Email corporativo | email | ✅ |
| Empresa | text | ✅ |
| Tamaño del equipo | select (1-10, 11-50, 51-200, 200+) | ✅ |
| Industria | select | optional |
| ¿Qué te interesa? | textarea | ✅ |
| Newsletter | checkbox | optional |

Validación con **Zod**:

```ts
const enterpriseLeadSchema = z.object({
  name: z.string().min(2).max(100),
  email: z.string().email(),
  company: z.string().min(2).max(100),
  team_size: z.enum(['1-10', '11-50', '51-200', '200+']),
  industry: z.string().optional(),
  message: z.string().min(20).max(1000),
  newsletter: z.boolean().optional(),
  turnstile: z.string(),  // anti-spam token
});
```

Backend:

- **Opción A**: Astro Action + Cloudflare Worker que envía a email vía Resend.
- **Opción B**: Formspree o similar.

**Decisión**: empezar con Formspree para no bloquear el lanzamiento. Migrar a Worker en V1.1.

Anti-spam:

- [ ] Cloudflare Turnstile (free, invisible).
- [ ] Honeypot field oculto.
- [ ] Rate limit por IP (Worker o Formspree).

Confirmación:

- [ ] Estado de éxito visible en línea (no redirect).
- [ ] Mensaje "Recibido. Te respondemos en menos de 48 horas."
- [ ] Email de confirmación al usuario (opcional V1.1).

### 7.4 Página `/changelog` (0.5 día)

`src/pages/changelog.astro`:

- [ ] Lee `CHANGELOG.md` del repo principal de Cortex (símbolo, git submodule, o URL fetch en build).
- [ ] Renderiza con Astro Markdown.
- [ ] Filtros: por versión, por tipo (feat/fix/docs/etc.).
- [ ] Toggle "ver solo breaking changes".

#### Pipeline de actualización

- [ ] En build, fetch `https://raw.githubusercontent.com/MachuaninEzequiel/Cortex/main/CHANGELOG.md`.
- [ ] Parse y render.
- [ ] Cache en build (no re-fetch por request).

### 7.5 CTAs cross-section (0.5 día)

#### Sticky CTA en header

- [ ] Botón `[Probar Cortex →]` visible siempre en header.
- [ ] En la sección `#instalacion`, se transforma o desaparece (ya estás ahí).

#### Scroll-to-top button

- [ ] Aparece cuando scrolled > 800px.
- [ ] Click hace scroll suave al top.
- [ ] Esconde en `prefers-reduced-motion` o usa scroll instantáneo.

#### Footer CTA repetido

- [ ] Banda final pre-footer: "¿Listo para empezar?" con 2 CTAs (Docs + Probar).

### 7.6 Analytics events

| Evento | Disparador |
| --- | --- |
| `install_copy` | Click en cualquier botón "Copiar" del wizard |
| `ide_tab_switch` | Cambio de tab en selector IDE |
| `enterprise_lead_view` | Visita a `/enterprise` |
| `enterprise_lead_submit` | Submit form (success) |
| `enterprise_lead_error` | Submit form (error) |
| `community_cta_click` | Click en cards finales |
| `scroll_to_top` | Click en botón scroll-to-top |

## Criterios de aceptación

- ✅ Wizard de instalación es claro y los comandos funcionan (verificado en máquina limpia).
- ✅ Selector de IDE cambia comandos correctamente.
- ✅ Toast de copia funciona.
- ✅ Página `/enterprise` se carga independiente y bien.
- ✅ Formulario enterprise envía correctamente y valida.
- ✅ Página `/changelog` renderiza CHANGELOG actual.
- ✅ Lighthouse Performance ≥ 90 en todas las páginas.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| Formulario spam abusivo | Turnstile + rate limit + honeypot |
| CHANGELOG cambia formato y rompe parser | Fetch en build; si falla, usar último cache |
| Comandos de instalación obsoletos al cambiar Cortex | Test en CI: extraer comandos del MD, ejecutar en Docker |

## Siguiente fase

→ [Fase 08 — Animaciones y pulido](fase-08-animaciones-pulido.md)
