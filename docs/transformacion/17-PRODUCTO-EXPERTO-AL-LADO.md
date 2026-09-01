# 17 · Producto: el experto al lado (no el que codea)

> **QUÉ CONSTRUIMOS.** A partir del 29 de agosto de 2026 este archivo es
> la definición de producto. El [16](16-DEUDA-REAL-Y-NORTE-DE-PULIDO.md)
> sigue mandando sobre *qué es teatro vs real* en el árbol. **La deuda
> residual del 16 no se ataca ahora**: queda anotada. Se desarrolla
> esto.
>
> Donde el norte del 16 choque con este archivo (sidecar como default,
> inyectar texto al agente, `finish` desde el Companion), **gana este
> archivo**.
>
> Cerrado en conversación con el dueño el 2026-08-29.
> Rama `feature/transformacion-2026-08` · commits locales, sin push.

---

## 1. El problema (por qué existe este producto)

Cortex, en Python y ahora en Rust, tiene demasiadas piezas: decenas de
comandos, MCP, sesiones, vault, skills, doctor, Action Engine, setup.
Los usuarios nuevos no entienden el mapa. Los que lo entienden no lo
usan bien. Si todo anda “perfecto” y la gente no lo usa, **el producto
fracasó**.

El fallo no es falta de features. Es que Cortex exige que el humano se
vuelva experto en Cortex.

La búsqueda: **toda funcionalidad de Cortex es agnóstica al usuario.**
No se aprende un comando. No se recita un flujo. Se trabaja; Cortex
está al lado, consulta el proyecto, recomienda, y vos elegís.

De ahí salieron tres ideas que ahora son **una sola**:

1. **Action Engine** — propone, nunca dispara solo. Vos siempre elegís.
2. **Liquid (LFM local)** — experto de Cortex y de *este* repo, en RAM
   solo mientras consultás, fuera de RAM cuando dejás de consultar.
3. **Herdr** — terminal con mouse, el experto al lado del agente que
   codea (`pi`, `agy`, Codex…), TUI que dé gusto tener abierta.

---

## 2. El producto en una frase

**Cortex Companion es el experto local del proyecto: una barra viva
abajo en Herdr que te dice qué está pasando ahora, te arma el próximo
prompt para copiarle al agente que codea, y te deja hablar con Liquid
cuando querés entender o preguntar. No codea. No cierra sesiones. No
le pega al agente. No tenés que aprender Cortex.**

---

## 3. Decisiones cerradas (no reabrir)

| # | Decisión | Implicancia |
|---|---|---|
| D1 | **Default = HUD abajo ~25%.** Sidecar y overlay existen como *atajos*, no como tres productos. | El agente que codea se queda con casi toda la pantalla. Cortex es presencia, no competencia. |
| D2 | Liquid **explica y opera Cortex solo dentro de una consulta** (tools de lectura para armar la respuesta). | No es un operador del trabajo. Es un experto al que le preguntás. |
| D3 | Liquid / Companion **nunca cierran una sesión.** Eso es del agente que codea (skills/MCP). | `finish` / `abandon` / `close` no existen como acción del Companion. |
| D4 | Liquid **nunca inyecta** texto al pane del agente. Recomienda prompts; el usuario **copia y pega**. | Muere `herdr pane send-text` como feature de producto. Botón **Copiar**. |
| D5 | Action Engine **solo propone**. Nunca auto-ejecuta. | Cero magia a espaldas. Agnóstico ≠ autónomo. |
| D6 | Si el usuario **Aprueba** una propuesta del Engine, corre higiene de Cortex **fuera del ciclo de sesión**: reindex, validar docs, doctor, remember, prune. Nunca checkpoint / finish / abandon / close. | Aprobar hace algo útil. No toca el trabajo del agente. |
| D7 | Logo voxel **vivo**: idle sutil (respiración/glow) = Liquid **no** está en RAM. Se despierta = Liquid **cargado**. Al dejar de consultar, se duerme y **descarga** el modelo. | La animación es estado, no adorno. |
| D8 | Mouse-first en Herdr. Cero obligación de saber un comando. El CLI sigue existiendo para power users y CI. | La TUI no enseña la CLI. |
| D9 | Una sola app, tres layouts. No tres binarios-concepto. | `CompanionMode` en el estado. Atajos cambian layout. |
| D10 | Deuda del doc 16: **diferida.** Solo se toca lo que este producto necesita para ser real (Aprobar que ejecute higiene, HUD que no mienta, hit-test, branding). | No empezamos el inventario residual. |

---

## 4. Dos inteligencias (y por qué no se pisan)

Esto resuelve la contradicción “guiado todo el tiempo por Liquid” vs
“Liquid solo en RAM cuando consultás”.

```
┌─────────────────────────────────────────────────────────────────┐
│ SIEMPRE ENCENDIDO (barato, sin LLM, HUD visible)                │
│  Action Engine + estado del proyecto                            │
│  • qué sesión / fase / agente (idle|working)                    │
│  • próximo prompt recomendado  → [ Copiar ]                     │
│  • próxima higiene Cortex      → [ Aprobar ] [ Saltar ]         │
│  • logo dormido (respiración mínima)                            │
├─────────────────────────────────────────────────────────────────┤
│ BAJO DEMANDA (Liquid / LFM GGUF)                                │
│  El usuario abre consulta (click en preguntar / tipea)          │
│  • logo se despierta · modelo carga · RAM ocupada               │
│  • tools de LECTURA: search, context, session, stats, doctor,   │
│    next, vault, skills — para responder *este* proyecto *ahora* │
│  • recomienda acciones y prompts; no las ejecuta; no las pega   │
│  • al salir / idle timeout: descarga GGUF · logo se duerme      │
└─────────────────────────────────────────────────────────────────┘
```

**El guía permanente es el Engine + la situación del repo.**
**El experto conversacional es Liquid.** Uno no requiere al otro en RAM.

Liquid no reemplaza al Action Engine. El Engine no intenta parecer un
chat. Si el usuario no pregunta nunca, igual ve el HUD y puede copiar
el prompt y aprobar higiene.

---

## 5. Tres superficies, una default

Misma máquina de estados. Cambia el layout y el atajo.

| Superficie | Cuándo | Qué entra |
|---|---|---|
| **HUD abajo ~25%** | **Default.** Abrir Cortex en Herdr. | Situación + prompt copiable + 1 acción Engine + semilla de consulta. Logo compacto vivo (2–3 filas). |
| **Sidecar ~30% izq.** | Atajo cuando la consulta se alarga. | Lo mismo + historial de chat con Liquid + más cuerpo para la respuesta. |
| **Overlay / float** | Atajo de vistazo, se va con Esc. | HUD aún más denso; Esc **cierra** (sale de Cortex, no “back” vacío). |

Atajos: los define Herdr (`prefix+…`). El usuario no elige “qué producto
soy hoy” en un menú de onboarding.

Si una consulta empieza en el HUD y el usuario se queda hablando,
**no es obligatorio** auto-promover a sidecar. El HUD scrollea la
respuesta. Sidecar es quien quiere más aire.

---

## 6. Qué se ve (contenido; esto mata el dashboard)

Nada de tarjetas protagonistas “doctor OK / episódica 6 / semántica 0 /
abrí una sesión”. Eso es inventario. El HUD muestra **situación y
próximo paso humano**.

### 6.1 Jerarquía del HUD (de arriba hacia abajo)

1. **Presencia** — mark voxel vivo (compacto) + una línea:
   `proyecto · rama · sesión o “sin sesión” · fase COMPOSED si hay · agente idle/working`.
2. **Prompt para el agente que codea** — 2–4 líneas de instrucción
   recomendada *para este momento de este repo*. Botón **[ Copiar ]**.
   Si no hay una buena, el hueco dice por qué (sin sesión, sin spec,
   sin fase) en una línea, no un empty-state de onboarding.
3. **Higiene de Cortex** — una sola propuesta del Action Engine, si
   hay. **[ Aprobar ] [ Saltar ]**. Si no hay, no se inventa una tarjeta
   vacía.
4. **Consulta** — un campo “preguntale a Cortex” (una línea). Al
   enfocar o enviar, arranca Liquid (D7).

Menú / Sesiones / Brain como *pantallas destino* dejan de ser botones
grandes. Se llega por teclado de accesibilidad (`/` busca, `?` ayuda
corta) o desde una respuesta de Liquid (“abrí sesiones” → navega). El
90% del tiempo no hacen falta.

### 6.2 De dónde sale el prompt copiable (v1)

Sin Liquid en RAM:

- Si hay sesión COMPOSED con `phase` → prompt de la skill craft de la
  **siguiente** fase (el texto que hoy vive en las skills thin+craft).
- Si hay sesión sin fase → prompt corto: “checkpoint de lo que
  acabás de hacer” **dirigido al agente**, no un comando Cortex.
- Si no hay sesión → prompt para que el *agente* abra/trabaje con las
  skills de Cortex (el humano no corre `cortex session …`).

Con Liquid en consulta: puede **reescribir** ese prompt (“hacelo más
estricto con el spec X”) y el botón Copiar toma la última versión.
Sigue sin inyectarlo.

---

## 7. Liquid — experto, no mascota y no piloto

### 7.1 Quién es

- Experto en **cómo funciona Cortex** (sesiones, vault, skills,
  COMPOSED, Action Engine, MCP).
- Experto en **este repo ahora**: memoria híbrida, sesión activa,
  spec, checkpoints, docs del vault.
- Habla el idioma del usuario (ES default, EN si el proyecto lo pide).
- Cero nube. GGUF local (LFM / Liquid), `llama.cpp`, feature ya
  prevista en `cortex-brain`.

### 7.2 Ciclo de memoria

1. HUD idle → **no hay modelo en RAM.** Logo dormido.
2. Usuario empieza consulta → load GGUF → logo despierto (animación de
   encendido, no un spinner genérico).
3. Turnos: router + tools de **lectura** in-process (el mapa que ya
   tiene el Companion, sin subprocess).
4. Idle de consulta (timeout corto, orden de minutos) **o** el usuario
   cierra la consulta → unload → logo se duerme.
5. Nunca se deja el modelo residente “por las dudas”.

La primera pregunta del día puede tardar (carga). El logo despierto
**es** esa espera. Eso alinea estética y sistema.

### 7.3 Qué puede hacer en una consulta

| Puede | No puede |
|---|---|
| Explicar cualquier pieza de Cortex | Cerrar / abandonar / finish de sesión |
| Buscar en vault y memoria de *este* proyecto | Inyectar texto al agente (send-text) |
| Decir en qué fase está y qué sigue | Checkpoint por su cuenta |
| Recomendar un prompt (el HUD lo copia) | Auto-ejecutar el Action Engine |
| Recomendar una higiene (“convendría reindex”) | Mentir que ejecutó algo |
| Usar tools de lectura: search, context, session current/list/detail, stats, doctor, next | Inventar estado que no leyó |

“Operar Cortex en consultas” = **usar las tools de lectura para no
alucinar**. No = mutar el trabajo.

### 7.4 Mutaciones

Única vía: click **Aprobar** en una propuesta del Action Engine (D6).
El chat nunca es un shell.

---

## 8. Action Engine — cara visible, manos cortas

Siempre encendido, siempre barato, siempre *opt-in*.

**Catálogo que el HUD puede mostrar y Aprobar (v1):**

- `vault.validate_docs`
- `vault.reindex`
- `learn.topic`
- `memory.prune`
- `knowledge.promote` (si hay enterprise)
- doctor / salud como acción de informe si hace falta

**Prohibido en el HUD, aunque existan en el catálogo interno:**

- `session.close_stale`
- `session.checkpoint_now`
- cualquier finish / abandon / close
- `setup.finish_bootstrap` e `ide.resync` (no son el día a día al lado
  del agente; viven en CLI / setup)

Saltar = skip del learner (cuando el learner se cablee; no es bloqueo
de v1 visual). Nunca = never. v1 puede persistir skip/never o no; el
producto no depende de eso para sentirse completo.

Aprobar **tiene que ejecutar de verdad** la higiene. Un Aprobar que
imprime “requiere fase P12” es el teatro del doc 16: si el HUD lo
muestra, el `run()` está cableado. Eso **sí** es trabajo de esta obra
(no es “deuda residual genérica”: es el botón del producto).

---

## 9. UX “no aprendas nada”

El usuario nuevo, el primer día:

1. Abre Herdr, su agente, y Cortex HUD abajo (un atajo / plugin).
2. Lee una línea de situación y un prompt. Copia. Pega en `pi`.
3. Si no entiende qué es una sesión, **pregunta en el campo**. Liquid
   carga, explica con datos de *este* repo, se duerme.
4. Si Cortex le pide reindex, Aprobar o Saltar. Nunca un comando.

No hay tutorial de 27 familias. No hay “el menú anti-olvido” como
puerta de entrada (el menú puede quedar como power, no como Home).

El CLI nativo no se borra. Se vuelve *implementation detail* para CI,
skills del agente que codea, y quien quiera. El humano frente a Herdr
no lo necesita.

---

## 9b. Mock visual (contrato para clonar)

No es Cortex todavía. Es la foto de v1:

- Interactivo (logo que respira, Idle / Consulta, Copiar):
  `assets/hud-v1/index.html`
- Grilla exacta a replicar en ratatui:
  `assets/hud-v1/GRID.md` (100×10, rects, paleta, copy)
- Stills: `assets/hud-v1/idle.png` y `awake.png`

Si el HTML y el GRID divergen, gana el GRID. La TUI se implementa contra el GRID, no “parecido”.

## 10. Estética: que dé gusto dejarlo abierto

Contrato visual (el branding voxel menta **ya elegido**, ahora bien
hecho):

- Paleta del PNG (bosque `#03522E`, menta `#8FDCB0`), no neón
  `#34D399`. El mock de HUD usa esa paleta. `palette.rs` se alinea
  cuando se pinte la TUI, no antes.
- HUD: columna izquierda = isotipo **completo** + wordmark, separados
  de los diálogos (ver `assets/hud-v1/GRID.md`). No recortar el mark
  a 3 filas ni mezclarlo con el texto.
- Pocas cajas. Casi ningún `Borders::ALL`. Jerarquía por peso, color
  menta, una línea divisoria si hace falta.
- Cero emoji como arquitectura.
- Mouse: hover en Copiar / Aprobar / campo de consulta. Click = la
  acción. Scroll de la respuesta.
- Animación del logo: idle ≤ 1 ciclo lento (respiración / glow de
  caras superiores ICE). Wake = las caras se encienden al cargar.
  Sleep = se apagan al descargar. Presupuesto de render del frame
  sigue siendo bajo (orden 50 ms). `NO_COLOR` / reduced-motion →
  estático, despierto=mark a plena ICE, dormido=mark DEEP.
- El logo **no** es un splash permanente. En 25% de alto, 2–3 filas
  de half-block. Si no entra, un glifo de 1 fila con el glow.

Esto es deliberadamente opuesto al screenshot actual: logo enorme,
cuatro botones, cuatro tarjetas, agente aplastado.

---

## 11. Qué no es este producto

- No es el agente que codea. No reemplaza `pi` / `agy` / Codex.
- No es un dashboard de telemetría.
- No es un help de la CLI.
- No es un copiloto que escribe en la terminal del otro.
- No es un orquestador que cierra el trabajo por vos.
- No es Liquid residente 24/7.
- No es tres apps Herdr distintas.
- No es el plan del doc 16 “inyectar / finish desde Companion /
  sidecar 30% default”. Eso quedó descartado acá.

---

## 12. Un día (escenario)

08:40 — Herdr. `pi` a pantalla casi completa. HUD Cortex abajo:
mark dormido, `cortex-demo · feature/… · sesión open · fase plan · pi working`.
Prompt: *“descomponé el plan en tickets según la spec de auth; no
toques fuera de `src/auth`”*. [ Copiar ].

08:41 — pega en `pi`. Sigue codeando. HUD sin molestar. Logo duerme.

09:10 — `pi idle`. El prompt cambia a algo de la fase implement.
Copia otra vez.

09:40 — no recuerda si ya hay ADR de JWT. Tipea en el campo: “hay una
decisión de jwt?”. Logo despierta (carga). Liquid busca el vault,
contesta con el path. Se queda 2 minutos. Cierra la consulta / idle.
Logo duerme, RAM libre.

10:00 — Engine propone “validar docs del vault”. [ Aprobar ]. Corre
DocValidator. No tocó la sesión.

Nunca escribió `cortex`. Nunca le pegó Cortex a `pi`. Nunca cerró la
sesión desde el HUD: cuando el trabajo termina, `pi` (skill
documenter / COMPOSED close) cierra. Cortex acompañó.

---

## 13. Alcance: v1 vs después (ampliamos sin diluir)

### v1 (esto se construye ahora)

- HUD default real (~25% abajo, geometría cierta, Esc en overlay cierra).
- Sidecar y overlay como atajos del **mismo** estado.
- Situación en una línea (sesión, fase si hay, agente Herdr si hay).
- Prompt copiable (clipboard) según §6.2.
- Action Engine: una propuesta, Aprobar ejecuta higiene real (D6).
- Consulta Liquid: load/unload, logo vivo = RAM, tools de lectura.
- Estética §10 en el HUD (y sidecar no vuelve al dashboard de cajas).
- Hit-test y teclas del layout actual, no las del Home 80×24.
- Spawn Herdr: default abre HUD; no miente “30%” sobre un pane al 80%.

### v1.1 (mismo producto, siguiente corte — no ahora)

- Prompt copiable escrito por Liquid (no solo template de fase).
- Learner skip/never persistido desde el HUD.
- Diff de la sesión visible en sidecar (el TUI ya sabe calcularlo).
- Aviso si el agente tocó paths fuera de la spec (guardrail).
- Paleta `Ctrl+K` de skills para armar el prompt a mano, sin CLI.

### Fuera (con ganas, no es este producto)

- Inyección al pane.
- Cerrar sesión desde Cortex.
- Auto-ejecutar el Engine.
- Fusionar `cortex-tui` y Companion.
- Borrar Python.
- Radar de guardrails como pieza de marketing antes del HUD v1.

---

## 14. Definición de hecho de v1

No hay “17-CIERRE” hasta que esto sea cierto **junto**:

1. Abrir Cortex en Herdr deja el **HUD abajo**; el agente sigue siendo
   el pane principal. Un atajo abre sidecar; otro overlay. Esc en
   overlay **sale**.
2. El HUD muestra situación + prompt + [ Copiar ]. Copiar pone el
   texto en el clipboard (test de integración o prueba manual
   documentada). **Ningún** `send-text` al agente.
3. Aprobar una higiene (`validate_docs` o `reindex` en fixture) **corre
   el servicio nativo**. No imprime “requiere fase P…”. No aparece
   finish/close/checkpoint como Aprobar.
4. Primera consulta carga Liquid (o el backend determinista si no hay
   GGUF: sigue siendo consulta, logo “despierto débil”). Cerrar /
   timeout descarga. El mark idle ≠ mark awake (assert de test o
   snapshot de dos estados).
5. El HUD no es el Home de cuatro tarjetas + cuatro botones. Snapshot
   TestBackend ~100×12: se lee prompt y Copiar; no se leen Menú /
   Sesiones / Doctor OK como protagonistas.
6. `cargo test -p cortex-companion` (+ actions si se cableó higiene)
   verde, clippy `-D warnings`, fmt. Hit-test del HUD cubierto.

---

## 15. Relación con el 16 y con el código de hoy

| El 16 decía | Este producto |
|---|---|
| Sidecar 30% default | HUD 25% default; sidecar atajo |
| Inyectar instrucción al agente | Copiar al clipboard |
| Companion puede cerrar sesión / `cortex finish` | Nunca. El agente que codea cierra |
| Aprobar = ejecutar (catálogo amplio) | Aprobar = solo higiene, y de verdad |
| Logo chico, menos cajas | Igual, más: logo = estado de RAM |
| Lotes 1–6 de deuda ya | Diferidos. Solo entra lo que v1 necesita |

Código de Obra 08 (máquina ELM, backend in-process, modal, brain
panel, plugin herdr) es **base**. El WIP del ciclo 15 (tres bins, HUD
pintado, copilot inject, doctor mentiroso) es **material de
desarme**, no diseño.

Brain standalone que hace subprocess al CLI: no es v1 del HUD. El HUD
habla in-process. El binario `cortex-brain` se toca solo si hace falta
para load/unload del GGUF.

---

## 16. Cómo sigue el desarrollo

1. Este documento queda cerrado como contrato.
2. Implementación = v1 del §13, contra gates del §14.
3. Cada commit local: un gate. Conventional en español. Sin push.
4. Si una duda de producto reaparece, se actualiza **este** archivo;
   no se decide en el chat y se pierde.

Contrato de implementación (cuando arranque, no antes): HUD verdadero
antes que sidecar bonito; Copiar antes que chat lindo; Aprobar-higiene
real antes que animación del logo; animación del logo junto con
load/unload, no como GIF suelto.
