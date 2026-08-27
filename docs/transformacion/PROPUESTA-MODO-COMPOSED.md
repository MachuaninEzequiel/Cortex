# PROPUESTA — MODO 4 (COMPOSED): la capa flexible del middle

> Documento de desarrollo · NO es una obra en ejecución todavía.
> Estado: PROPUESTA para discusión del dueño.
> Fuentes: código real de Cortex (session models, documenter, SDDwork,
> doc 02), investigación primaria de `mattpocock/skills` (2026-08-27,
> ~238k stars), y la metodología `obra/superpowers` (local, usada en esta
> misma sesión). Todo lo afirmado de esos repos fue verificado contra el
> contenido real.

## 0. Resumen ejecutivo

Cortex tiene hoy **tres modos de middle** (Managed / Observed / BYO),
inferidos al cierre desde el set de checkpoints. Los tres quedaron
desactualizados respecto a cómo se desarrolla software con agentes en 2026:
el estándar de la industria es la **skill composable** (SKILL.md), los
flujos son **cadenas de skills invocadas por el humano o por el modelo**, y
el valor ya no está en "el agente ejecuta un plan" sino en "el humano
compone un flujo con piezas chicas y adaptables".

Esta propuesta define un **cuarto modo, COMPOSED** ("compuesto"): el middle
ya no es una skill orquestadora de Cortex (Managed), ni hooks del IDE
(Observed), ni ausencia de registro (BYO) — es **cualquier cadena de skills
externas** (mattpocock-style, superpowers-style, propias del usuario) que
emite checkpoints **enriquecidos con fase**, y Cortex lo reconoce, lo
registra y lo documenta sin imponer el proceso.

Fuentes de la mezcla:
- De **mattpocock/skills**: skills chicas y componibles, invocación
  user/model-invoked, trayectoria idea→ship, tickets comme unidad de
  contexto descartable, lenguaje compartido (CONTEXT.md + ADRs), code
  review de dos ejes en paralelo, categorías engineering/productivity.
- De **obra/superpowers**: disciplina por fases (brainstorm → plan →
  execute → review → finish), TDD como ley, verificación con evidencia
  antes de declarar listo, rulings en vez de estancamientos, ledger de
  decisiones.
- De **Cortex** (lo que ya existe): la Session como contrato, checkpoints
  con verified/unverified claims, verification hooks al cierre, el
  documenter como reconstructor, y el Action Engine como sugeridor.

El modo COMPOSED **no es un nuevo orquestador**: es un **contrato de
entrada** (qué checkpoint emite una skill para que Cortex la entienda) +
un **conjunto de skills de referencia** (que el usuario puede instalar,
editar o ignorar) + el **reconocimiento en infer_mode** + el **enriquecido
del documenter** para el cierre. El usuario trae su flujo; Cortex lo
acompaña.

---

## 1. Estado actual: los tres modos y su desactualización

### 1.1 Cómo funcionan hoy (código real)

`cortex/session/models.py:86-93` define `SessionMode`, y
`cortex/session/service.py:492-509` `infer_mode`:

- Sin checkpoints → `BYO` (el documenter reconstruye desde git diff).
- Todos `ci-bot` → `CI_REVIEW` (Fase 07 L3).
- Todos de agentes Cortex (`cortex-sync`, `cortex-SDDwork`,
  `cortex-code-*`) → `MANAGED`.
- Cualquier otra mezcla (ide-hook, user-skill, manual) → `OBSERVED`.

El **Modo Managed** está implementado por `cortex-SDDwork.md` (skill
orquestadora instalada por setup): pre-flight contra la sesión abierta,
FAST TRACK (1-2 archivos, un checkpoint) vs DEEP TRACK (delega a
explorer/designer/implementer, cada uno con su propio checkpoint y
`cortex_review_checkpoint` como gate entre pasos). El contrato entre
subagentes es la Session (cero YAML inline).

El **Modo Observed** vive en `cortex/session/hooks/` (HookAdapter:
git-hook o ide-event) — el IDE emite checkpoints `ide-hook`.

El **Modo BYO** no requiere nada: el documenter sintetiza desde
git diff + checkpoints si los hubiera.

### 1.2 Por qué quedaron desactualizados

| Limitación | Modos afectados | Evidencia |
|---|---|---|
| **El flujo está incrustado en una skill de Cortex** (SDDwork). Externo a este repo, la skill es una pieza más; acá es EL middle. | Managed | SDDwork decide vías (fast/deep) — el usuario no puede mezclar su propio flujo con él |
| **Invocación rígida**: el orquestador manda a subagentes fijos. | Managed | Explorer/designer/implementer son roles internos; mattpocock demuestra que los roles deberían ser skills componibles |
| **Observed es pasivo**: registra lo que el IDE emite, sin fases, sin lenguaje compartido. | Observed | Los checkpoints ide-hook no llevan fase ni claims estructurados |
| **BYO no registra nada**: el cierre depende solo de git diff. | BYO | La reconstrucción pierde decisiones, alternativas descartadas, razones |
| **Los tres ignoran los artefactos modernos**: CONTEXT.md (lenguaje compartido), ADRs, tickets como unidades de contexto. | Todos | mattpocock: el lenguaje compartido es "la técnica más cool del repo"; los tickets que caben en una ventana de contexto son la unidad de trabajo |
| **Ninguno soporta skills de terceros como ciudadanos de primera clase**. | Todos | El estándar Agent Skills (SKILL.md) ya es transversal en Claude Code, Codex, Cursor… |

---

## 2. Fuente A — mattpocock/skills (verificado 2026-08-27)

Repositorio: `github.com/mattpocock/skills` — "Skills for Real Engineers.
Straight from my .agents directory." MIT, ~238.5k stars, última actividad
2026-08-24. 37 `SKILL.md` (25 "promoted": 18 engineering + 7 productivity;
4 misc; 8 in-progress). Cada skill con `agents/openai.yaml` para doble
harness (Claude Code + Codex). Distribuido como plugin oficial de Claude
Code + `skills.sh`.

### 2.1 El flujo idea→ship (del router `ask-matt`)

```
grill-with-docs ──► (CONTEXT.md + ADRs) ──► to-spec ──► to-tickets
                                                        │  (tracer-bullet
                                                        │   vertical slices
                                                        │   con blocking edges)
            ┌─────◄──────────── implement per ticket ◄──┘
            │        (contexto FRESCO por ticket; /clear entre tickets)
            └──────────── tdd (red→green por slice) → code-review
                          (dos ejes paralelos: Standards + Spec)
                          → commit → ship
```

On-ramps: `/triage` (issues que no creó el usuario), `/diagnosing-bugs`
(exige feedback loop que ya va en rojo antes de teorizar),
`/wayfinder` (mapa de decision-tickets para trabajo gigante/foggy).
Detours: `/prototype` (rama descartable pero fuente primaria),
`/handoff`, `/compact` en boundaries de fase.

### 2.2 Los 4 failure modes que motivan las skills (README)

1. **"The agent didn't do what I want"** → grilling (requirements sharpening).
2. **"The agent is way too verbose"** → shared language: CONTEXT.md
   glossary + ADRs ("la técnica más cool del repo").
3. **"The code doesn't work"** → feedback loops: TDD, static types,
   browser access, `diagnosing-bugs`.
4. **"We built a ball of mud"** → caring about design: `to-spec` quiz,
   `codebase-design` (deep modules, Ousterhout), `improve-codebase-architecture`.

### 2.3 Patrones de diseño de skills (los que COMPOSED adopta)

- **Invocación explícita**: user-invoked (`disable-model-invocation:
  true`, solo el humano teclea `/name`) vs model-invoked (descripciones
  ricas, el modelo las alcanza solo). Un user-invoked puede llamar a
  model-invoked; nunca al revés.
- **Composición por tool-call explícito**: "Call the Skill tool with
  `grilling`" — sin `/` (harness-neutral), una skill por call.
- **Tickets como unidad de contexto descartable**: un ticket = una
  ventana de contexto fresca; `clear` entre tickets; "smart zone"
  (~150k tokens) como límite operativo.
- **Hard vs soft dependencies** (ADR-0001): skills que exigen setup
  previo (to-tickets/to-spec/triage) vs skills que solo referencian el
  lenguaje compartido (tdd/diagnosing-bugs).
- **Code review de dos ejes en paralelo** (Standards + Spec), reportes
  separados, sub-agentes independientes (contextos que no se contaminan).
- **Categorías**: engineering/ y productivity/ promoted; misc e
  in-progress fuera del plugin.
- **Refusals explícitos** (`.out-of-scope/`): qué NO hace, con razón.

---

## 3. Fuente B — obra/superpowers (local, usada en esta sesión)

Metodología de skills encadenadas, cada una con SKILL.md, frontmatter
(name/description/when-to-use), y un flujo por fases:

| Fase | Skill | Qué aporta |
|---|---|---|
| Inicio | `using-superpowers` | router: elegí la skill correcta antes de actuar |
| Diseño | `brainstorming` | explorar intención/requisitos ANTES de código |
| Plan | `writing-plans` | plan con pasos bite-sized y verificación por paso |
| Ejecución | `executing-plans` / `subagent-driven-development` | ejecutar el plan con checkpoints de revisión; ledger de rulings; fresh-subagent-por-tarea + task-review + fix-loop 5 rondas |
| Código | `test-driven-development` | Iron Law: cero código sin test que falle primero; red→green→refactor |
| Verificación | `verification-before-completion` | evidencia antes que aserciones: correr y mostrar |
| Revisión | `requesting-code-review` + `receiving-code-review` | revisión externa obligatoria antes de merge; objeciones con rigor técnico |
| Cierre | `finishing-a-development-branch` | integrar con verificación completa |
| Soportes | `using-git-worktrees`, `resolving-merge-conflicts` | aislamiento y conflicto |

Principios que COMPOSED toma prestados:

1. **El plan es un argumento, no un contrato**: se re-planifica contra la
   espec, con rulings registrados ("Rule, don't stall").
2. **La spec manda**: si plan y spec se contradicen, la spec gana.
3. **El ledger sobrevive a la compactación**: decisiones registradas en
   disco, no en memoria de sesión.
4. **Nunca fixes sin test**: TDD como ley, no como sugerencia.
5. **Revisión por cada tarea**: implementer + task-reviewer + fix loop con
   tope de 5 rondas y adjudicación explícita (nunca descartes silencioso).
6. **Skills chicas, de una sola responsabilidad**, consignadas en markdown
   legible por humanos y modelos (misma forma que mattpocock).

Diferencia clave con mattpocock: superpowers es más prescriptivo en el
**proceso** (plan → tdd → review), mattpocock es más prescriptivo en la
**forma de las skills** (invocación, composición). COMPOSED toma el
proceso de superpowers como **flujo de referencia opcional** y la forma de
mattpocock como **convención obligatoria** de las skills que Cortex
entiende.

---

## 4. La propuesta: MODO COMPOSED

### 4.1 Definición

> **COMPOSED** = el middle es una **cadena de skills externas** (instaladas
> o propias del usuario) que emiten checkpoints enriquecidos con **fase**.
> Cortex no orquesta: reconoce, registra y documenta. El usuario compone;
> la Session es el contrato; el cierre sigue siendo verificable.

No reemplaza a los otros tres: los cuatro conviven y `infer_mode` los
distingue por el origen y la forma de los checkpoints.

### 4.2 El contrato de entrada: Checkpoint con fase

Extender el schema inmutable `Checkpoint` con un campo nuevo opcional:

```python
class CheckpointPhase(StrEnum):
    GRILL = "grill"            # aclarar requisitos / shared language
    SPEC = "spec"              # escribir la spec (o ticket descompuesto)
    PLAN = "plan"              # pasos bite-sized + verificación por paso
    IMPLEMENT = "implement"    # código (con o sin TDD)
    REVIEW = "review"          # revisión (standards, spec, externa)
    CLOSE = "close"            # cierre / integración

# En Checkpoint (extra="forbid" ...):
phase: CheckpointPhase | None = None   # NUEVO campo opcional
```

Reglas:
- **`extra="forbid"` hoy**: añadir el campo es un cambio de schema
  testado (nadie más puede mandar claves extra; el field nuevo es
  opcional ⇒ backward-compatible para todos los emisores actuales).
- Un checkpoint CON `phase` presente ⇒ emisor es una skill COMPOSED.
- El `source` se mantiene: `user-skill` (skills del usuario),
  `ide-hook` (si una skill del IDE lo emite), o un nuevo `composed-skill`
  opcional si querés distinguir skills certificadas de Cortex de las del
  usuario. **Decisión abierta 1** — ver §8.
- `note` pasa a ser el "handoff a la siguiente fase" (≤1 línea, ya es así).

### 4.3 infer_mode: cuarto modo

```python
# orden de prioridad en infer_mode:
# 1. sin checkpoints → BYO
# 2. todos ci-bot → CI_REVIEW
# 3. ∃ checkpoint con phase → COMPOSED
# 4. todos cortex-* → MANAGED
# 5. resto (ide-hook/user-skill sin phase/manual) → OBSERVED
```

- Si **cualquier** checkpoint lleva `phase`, la sesión es COMPOSED: el
  usuario compuso un flujo con fases visibles, aunque haya mezclado
  agentes Cortex e IDE hooks en el camino.
- El documenter, al ver `phase`, etiqueta la nota de sesión con la **línea
  de fases** (p. ej. `grill → spec → implement → review`) y puede exigir
  (si la spec lo declara) que `CLOSE` exista antes de `Closed` — **decisión
  abierta 2**.

### 4.4 El conjunto de skills de referencia (skills/ de Cortex)

Setup instala bajo `.cortex/skills/composed/` una **familia de skills de
referencia** que el usuario puede usar tal cual, editar o ignorar. Cada una
es un SKILL.md estándar + `agents/openai.yaml` (doble harness), siguiendo
la convención mattpocock:

```
.cortex/skills/composed/
  grill/          SKILL.md + agents/openai.yaml   # user-invoked
  to-spec/        SKILL.md + agents/openai.yaml   # user-invoked
  to-tickets/     SKILL.md + agents/openai.yaml   # user-invoked
  implement/      SKILL.md + agents/openai.yaml   # model-invoked
  review/         SKILL.md + agents/openai.yaml   # user-invoked (2 ejes)
  tdd/            SKILL.md + agents/openai.yaml   # model-invoked
  diagnose/       SKILL.md + agents/openai.yaml   # model-invoked
  glossary/       SKILL.md + agents/openai.yaml   # user-invoked (CONTEXT.md)
```

Contrato de cada skill (lo que Cortex lee):
1. **Obligatorio**: emitir checkpoint con `phase` + `verified_claims` +
   `artifacts_touched` + `note` al terminar su etapa.
2. **Opcional**: llamar a `cortex_review_checkpoint` (gate entre pasos),
   `cortex_context` (traer contexto), `cortex_search` (memoria).
3. Las skills user-invoked declaran `disable-model-invocation: true`
   (convención mattpocock); las model-invoked llevan descripciones ricas.

El usuario puede **traer sus propias skills** (mattpocock via `skills.sh`,
superpowers, o escritas a mano): Cortex solo exige el contrato de
checkpoint. `cortex setup composed` (nuevo subcomando) instala la familia
de referencia y escribe el bloque `## Agent skills` en CLAUDE.md/AGENTS.md.

### 4.5 Elementos tomados de cada fuente (tabla de mezcla)

| Elemento | Fuente | Cómo entra en COMPOSED |
|---|---|---|
| SKILL.md + agents/openai.yaml (doble harness) | mattpocock | formato estándar de la familia de referencia |
| User-invoked vs model-invoked | mattpocock | flag obligatorio en frontmatter de cada skill de referencia |
| Composición por tool-call explícito | mattpocock | "Call the Skill tool with `X`" en el cuerpo de las skills |
| Tickets = contexto descartable | mattpocock | skill `to-tickets`; cada implement arranca fresco (precedente: superpowers usa worktrees por tarea) |
| Lenguaje compartido CONTEXT.md + ADRs | mattpocock (y cortex-sync ya lee CONTEXT.md) | skill `glossary`; el documenter valida términos canónicos en la nota |
| Code review 2 ejes paralelos | mattpocock | skill `review` emitida con phase=review; dos sub-invocaciones estándar/ spec |
| TDD como ley | superpowers | skill `tdd` de referencia con Iron Law; no obligatorio fuera de la skill |
| Plan como argumento + rulings | superpowers | skill `to-tickets` produce tickets con verificación por paso; ledger en `.scratch/<feature>/` |
| Revisión externa antes de merge | superpowers | `review`/`close`; verification hooks de la spec corren en finish |
| Evidencia antes que aserciones | superpowers/cortex | los verify hooks ya existen; la fase CLOSE lo refuerza |
| Ledger que sobrevive la compactación | superpowers | ticktes/decisiones en `.scratch/<feature>/issues/` (patrón mattpocock) + Session |
| Verificación por niveles (fmt→gates→suite) | superpowers/cortex | skills de referencia lo documentan; el documenter lo refleja en la nota |
| 4 failure modes → skills | mattpocock | la familia de referencia cubre grill/lenguaje/tdd/diseño |

### 4.6 Cierre y documentación (documenter COMPOSED)

El documenter, en vez de solo reconstruir desde diff:
- Lee los checkpoints con fase y arma la **línea de fases** para la nota.
- Junta `verified_claims` por fase en la sección de evidencia.
- Si hubo `glossary`: valida que la nota use términos canónicos de
  CONTEXT.md (decisión abierta 3: hard vs soft).
- El resto del flujo de cierre (reconstruct → create_args → nota → ADRs)
  queda igual: la sesión COMPOSED se cierra con `cortex finish-session`.

### 4.7 Qué NO cambia

- **La Session y el Checkpoint base** (immutabilidad, sources cerrados).
- **El documenter reconstructor**: sigue funcionando para BYO.
- **El Modo Managed (SDDwork)**: sigue siendo el camino recomendado sin
  flujo propio; COMPOSED es el camino cuando el usuario trae uno.
- **El Action Engine**: `cortex next` puede sugerir la SIGUIENTE FASE
  (p. ej. "la sesión está en implement; siguiente: review") leyendo la
  última fase — mejora pequeña y opcional.

### 4.8 Lo que se construye (inventario)

| # | Pieza | Archivo/ámbito | Tipo |
|---|---|---|---|
| 1 | `CheckpointPhase` + campo `phase` en Checkpoint | `cortex/session/models.py` + espejo Rust `cortex-app/src/session/` | cambio de schema (tested, backward-compatible) |
| 2 | `infer_mode` → COMPOSED | `cortex/session/service.py` + Rust | lógica + tests |
| 3 | `SessionMode.COMPOSED` + serialización | models + gate de paridad | enum + tests |
| 4 | Familia de skills de referencia | templates en `cortex-setup` (`.cortex/skills/composed/`) | templates + instalador |
| 5 | `cortex setup composed` (o `cortex skills install composed`) | CLI setup | comando nuevo |
| 6 | Documenter: línea de fases + evidencia por fase | documenter persistencia | enriquecido de nota |
| 7 | (Opcional) `cortex next` sugiere siguiente fase | Action Engine | mejora |
| 8 | Gates: paridad de `infer_mode`, round-trip de fase, nota con línea de fases, instalación de skills | bench/parity + tests | gates |

---

## 5. El flujo completo (escenario)

```
# Usuario con su propio flujo (mattpocock-style):
cortex setup composed              # instala la familia de referencia (o trae las suyas)
cortex session current             # abre sesión (cortex-sync sigue siendo pre-flight)

# La sesión arranca spec-driven como siempre;
# el middle lo compone el usuario:
/grill   → emite checkpoint phase=grill  (+ CONTEXT.md/ADR si aplica)
/to-spec → emite checkpoint phase=spec
/to-tick → emite checkpoint phase=plan   (tickets en .scratch/<feat>/issues/)
/implement → por ticket, con /tdd:
            emite checkpoint phase=implement (verified_claims por slice)
/review  → emite checkpoint phase=review  (dos ejes; llama review_checkpoint)
cortex finish-session               # verification hooks + documenter

# Al cierre:
#   session list --json  →  mode: "composed"
#   nota de sesión       →  línea de fases: grill → spec → plan → implement → review
#   evidencia            →  claims agregados por fase
```

Y el mismo mecanismo sirve para un flujo superpowers-style:
`brainstorm → writing-plans → subagent-driven-development → tdd →
requesting-code-review → finishing-a-development-branch` — cada skill de
la cadena emite su checkpoint con fase; Cortex documenta sin intervenir.

---

## 6. Verificación y gates

1. **Paridad de infer_mode**: tabla completa de combinaciones de sources
   (con/sin phase) → mode esperado; gate byte-parity vs Python.
2. **Round-trip de fase**: checkpoints con fase sobreviven storage YAML
   (Python + Rust).
3. **Nota con línea de fases**: documenter emite la línea exacta para un
   set dado de checkpoints (golden).
4. **Instalación de skills**: `setup composed` escribe los SKILL.md +
   openai.yaml byte-exactos (templates congeladas).
5. **Backward-compat**: sesiones existentes sin fase siguen infiriendo
   Managed/Observed/BYO/CI_REVIEW igual que hoy (gate 1 cubre).
6. Suite Python completa (oráculo) + workspace cargo verdes.

---

## 7. Plan de implementación (orden sugerido)

| Fase | Contenido | Gate |
|---|---|---|
| 1 | Schema: `CheckpointPhase` + campo `phase` (Python y Rust) + tests | round-trip + suite |
| 2 | `infer_mode` COMPOSED + `SessionMode.COMPOSED` + serialización | paridad tabla combinaciones |
| 3 | Templates de la familia de skills + instalador `setup composed` | templates byte-exactas |
| 4 | Documenter: línea de fases + evidencia por fase | golden nota |
| 5 | (Opcional) `next` sugiere siguiente fase | gate next |
| 6 | Docs: ESTADO-ACTUAL + HANDOFF + este documento → resuelto | — |

Tamaño estimado: ~600-900 LOC + templates + gates. No requiere deps
nuevas (todo nativo existe). Compatible con la arquitectura actual: es
una extensión de schema y lógica, no una reescritura.

---

## 8. Decisiones abiertas para el dueño

1. **`source` nuevo `composed-skill`** vs reusar `user-skill` para los
   checkpoints COMPOSED. (Recomendado: reusar `user-skill` + `phase`;
   menos superficie, el phase ya distingue.)
2. **¿El documenter exige la fase `close`** para marcar `Closed`, si la
   spec lo declara? (Recomendado: soft — lo registra como warning, no
   bloquea; bloquea solo con flag en spec `require_close_phase: true`.)
3. **Lenguaje compartido**: ¿validar términos canónicos de CONTEXT.md en
   la nota (hard) o solo documentarlos (soft)? (Recomendado: soft.)
4. **¿`setup composed` instala por defecto** la familia mattpocock-style,
   superpowers-style, o solo un skeleton mínimo? (Recomendado: skeleton
   mínimo + documentación de cómo importar cualquiera de los dos.)
5. **Nombre**: `composed` (recomendado) vs `flex` vs `guided` — el valor
   del enum es público en `session list --json`.

---

## 9. Riesgos

| Riesgo | Mitigación |
|---|---|
| Ruptura de schema (extra=forbid) | campo opcional + tests de compat; nunca romper emisores actuales |
| Skills de terceros emiten checkpoints malformados | validación dura del MCP/server: `phase` inválida → rechazo con mensaje claro |
| COMPOSED canibaliza Managed | Managed sigue siendo el default sin flujo propio; COMPOSED es opt-in explícito |
| Doble fuente de verdad (skills en .cortex vs repo) | mismas reglas que ide-manifest: templates son SSoT, instalación copia + manifest |
| El documenter pierde riqueza sin git | ya reconstruye desde checkpoints (gitless); COMPOSED suma fases → más rico, no menos |