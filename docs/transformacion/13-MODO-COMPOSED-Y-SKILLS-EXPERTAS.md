# 13 — MODO COMPOSED Y SKILLS EXPERTAS (Obra 08, stream A)

> Estado: RESUELTO por obra 08 stream A (2026-08-28) — ver `ESTADO-ACTUAL.md` §"Obra 08 — Stream A" y `HANDOFF.md` §8.
> (aprobada por el dueño 2026-08-27)
> Reemplaza a `PROPUESTA-MODO-COMPOSED.md` (que queda como fuente de investigación).
> Obra 08 = dos streams: A (este doc) + B (`14-HERDR-COMPANION.md`).
> Regla rectora: **agregar, casi nunca cambiar**.

## 0. Por qué y para qué

Tres modos (Managed / Observed / BYO) quedaron desactualizados respecto a
cómo se desarrolla con agentes en 2026: el estándar es la **skill
composable** (SKILL.md), los flujos son **cadenas de skills** invocadas por
el humano o el modelo, y el valor está en que **el humano compone** con
piezas chicas, no en que el agente ejecute un plan fijo.

Problemas concretos que resuelve esta obra:

1. **Las skills de Cortex cumplen su función pero no aportan rasgo experto.**
   Son manuales de procedimiento (144-305 líneas de gobernanza). El craft
   (qué pregunta un experto, qué significa "bien hecho" aquí) no existe en
   ellas, y **alargarlas no sirve**: carga el contexto del agente con
   material que solo se necesita en la fase activa.
2. **El ciclo sync → SDDwork → documenter es rígido.** sync (pre-flight) y
   documenter (cierre verificable) son el spine de valor; SDDwork (el medio)
   es el reemplazable: el usuario trae su propio flujo y Cortex debe
   acompañarlo, no orquestarlo.
3. **BYO agrega fricción.** Hoy = "hacé lo que quieras y acordate de cerrar
   a mano"; la reconstrucción pierde decisiones y razones. COMPOSED registra
   solo, con fases visibles, y el documenter enriquece la nota.

## 1. Decisiones de base (firmadas por el dueño 2026-08-27)

1. **Rust-first, oráculo congelado.** Los cambios de schema se hacen SOLO en
   Rust (`cortex-app`). El oráculo Python (2552 tests, deprecado) no se toca:
   usa sus propios fixtures y no lee sesiones con `phase`, por lo que no
   rompe. Toda extensión nueva se documenta como **divergencia declarada**
   (patrón vigente del repo: "divergencias implícitas documentadas").
2. **Reusar `source=user-skill` + `phase`** para checkpoints COMPOSED (sin
   source nuevo `composed-skill`): menos superficie; el phase ya distingue.
3. **Cierre soft.** El documenter registra WARNING si falta la fase `close`;
   bloquea el cierre `Closed` SOLO si la spec declara
   `require_close_phase: true`.
4. **Glossary soft.** Los términos canónicos de CONTEXT.md se documentan en
   la nota; no hay validación dura (fase 2 posible).
5. **Familia de referencia = skeleton mínimo** + documentación de cómo
   importar flujos mattpocock-style o superpowers-style.
6. **Nombre del modo: `composed`** (público en `session list --json`).

## 2. Contrato de fases (schema)

### 2.1 `CheckpointPhase`

```rust
// cortex-app/src/session/models.rs (espejo del Checkpoint existente)
#[derive(...)]
#[serde(rename_all = "snake_case")]
pub enum CheckpointPhase {
    Grill,      // aclarar requisitos / shared language
    Spec,       // escribir la spec (o ticket descompuesto)
    Plan,       // pasos bite-sized + verificación por paso
    Implement,  // código (con o sin TDD)
    Review,     // revisión (standards, spec, externa)
    Close,      // cierre / integración
}

// En Checkpoint (immutable, extra=forbid):
pub phase: Option<CheckpointPhase>,   // NUEVO campo opcional
```

Reglas:
- Campo **opcional** ⇒ cero impacto en emisores actuales (cortex-sync,
  cortex-SDDwork, ide-hook, manual, ci-bot) — todos siguen sin `phase`.
- Checkpoint CON `phase` ⇒ emisor es una skill COMPOSED.
- Validación dura: `phase` inválida ⇒ rechazo con mensaje claro en el
  servicio (`SessionService::checkpoint`) y en el handler MCP
  (`cortex_session_checkpoint`), patrón P6/P9. Nunca silencio.
- Round-trip: el campo sobrevive el storage YAML (serde, `sort_keys=False`
  como hoy) y la serialización `--json` de sesiones.

## 3. Barra de calidad por fase (el rasgo experto, sin contexto extra)

Extensión de `quality_gates.rs` (funciones puras, misma estructura de
etapas). El gate es la medida de calidad: **el skill no necesita decirle al
agente qué es calidad — el gate la mide**.

| phase | Gate adicional (además de spec compliance + calidad actuales) |
|---|---|
| `grill` | sin gate extra (fase de conversación; aclarar ≠ producir) |
| `spec` | ≥1 `verified_claim` con >10 chars (la spec se leyó/revisó, no se copió) |
| `plan` | ≥1 `artifact_touched` (tickets/plan en disco) |
| `implement` | `artifacts_touched` no vacío + ≥1 `verified_claim` con evidencia >10 chars |
| `review` | ≥1 `verified_claim` con evidencia >10 chars (los 2 ejes estándar/spec dejan rastro) |
| `close` | existe al menos un checkpoint previo con fase distinta de `close` |

Resultado: `accept` / `warn` / `redelegate` según severidad, idéntico al
mecanismo actual. Con `phase: None` ⇒ comportamiento actual EXACTO (los
gates existentes no cambian).

## 4. infer_mode: cuarto modo

Prioridad en `SessionService::infer_mode` (orden exacto):

```text
1. sin checkpoints               → BYO
2. todos ci-bot                  → CI_REVIEW
3. ∃ checkpoint con phase        → COMPOSED
4. todos cortex-*                → MANAGED
5. resto (ide-hook/user-skill sin phase/manual) → OBSERVED
```

- `SessionMode::Composed` serializa como `"composed"` (session list --json).
- Si CUALQUIER checkpoint lleva `phase`, la sesión es COMPOSED aunque haya
  mezcla de agentes Cortex e ide-hooks en el camino: el usuario compuso un
  flujo con fases visibles.

## 5. Reestructura de las 3 skills actuales (thin + references/)

Patrón moderno de skills (mattpocock/ECC, ver
`investigacion-mattpocock-skills.md`): **el SKILL.md conserva el contrato**
(reglas de gobernanza, secuencia MCP obligatoria, límites) **~60-70% más
corto**; el craft vive en `references/` que el agente carga on-demand
cuando la fase lo necesita.

Templates en `cortex-setup` (SSoT, igual que hoy; instalación según setup
existente):

```
.cortex/skills/cortex-sync/
  SKILL.md                     — contrato: sync_ticket → CONTEXT.md → explorar → proposal → spec (~60 líneas)
  references/spec-craft.md     — preguntas de experto, trampas comunes, criterios de aceptación accionables
  references/proposal-craft.md — alternativas honestas: qué descartar y por qué
.cortex/skills/cortex-SDDwork/
  SKILL.md                     — contrato: pre-flight, fast/deep routing, emisión de checkpoint (~70 líneas)
  references/implement-craft.md — TDD, tamaño de cambio, revisión de diff propio, cuándo delegar
.cortex/skills/cortex-documenter/
  SKILL.md                     — contrato: reconstruct → verificación → nota (~60 líneas)
  references/close-craft.md    — qué hace una nota de cierre buena: claims verificables, placeholders prohibidos
```

Notas:
- La estructura de skill single-file → directorio puede requerir ajuste del
  instalador (verificar `HookInstaller`/setup_templates; si el instalador
  solo copia archivos, el cambio es copiar el dir completo).
- `--json`/salidas y contratos MCP NO cambian: solo cambia dónde vive el
  texto.

## 6. Familia de skills de referencia (`cortex setup composed`)

Instala bajo `.cortex/skills/composed/` 8 skills estándar (SKILL.md +
references/ + `agents/openai.yaml` para doble harness Claude Code/Codex):

| Skill | Invocación | Fase que emite | Contenido núcleo |
|---|---|---|---|
| `grill` | user-invoked | grill | aclarar requisitos, 5 whys, preguntas de experto |
| `to-spec` | user-invoked | spec | de conversación a spec con acceptance criteria |
| `to-tickets` | user-invoked | plan | descomposición en tickets = contexto descartable |
| `implement` | model-invoked | implement | implementar por ticket, claims con evidencia |
| `tdd` | model-invoked | implement | Iron Law: cero código sin test rojo primero |
| `diagnose` | model-invoked | implement | feedback loop antes de teorizar (bugfix) |
| `review` | user-invoked | review | dos ejes en paralelo: Standards + Spec |
| `glossary` | user-invoked | spec (solo si toca la spec) | CONTEXT.md: lenguaje compartido + ADRs |

Contrato de cada skill (lo que Cortex lee):
1. **Obligatorio**: emitir checkpoint con `phase` + `verified_claims` +
   `artifacts_touched` + `note` (handoff a la siguiente fase, ≤1 línea) al
   terminar su etapa.
2. **Opcional**: `cortex_review_checkpoint` (gate entre pasos),
   `cortex_context`, `cortex_search`.
3. User-invoked declaran `disable-model-invocation: true` (convención
   mattpocock). Model-invoked llevan descripciones ricas.
4. `glossary` es emisor opcional: si solo mantiene CONTEXT.md no emite
   checkpoint; si sus términos afectan la spec activa, emite `phase=spec`.
4. Skills de TERCEROS: mismas reglas — Cortex solo exige el contrato de
   checkpoint con fase.

Comando nuevo: `cortex setup composed` (instala la familia + escribe el
bloque `## Agent skills` en CLAUDE.md/AGENTS.md, reusando writers de
`cortex-setup`). Skeleton mínimo + `INSTALL-COMPOSED.md` (cómo importar
flujos externos).

## 7. Documenter y Action Engine (enriquecidos)

### 7.1 Documenter COMPOSED

- Lee checkpoints con `phase` y arma la **línea de fases** para la nota:
  `grill → spec → plan → implement → review`.
- Agrupa `verified_claims` **por fase** en la sección de evidencia.
- Si hubo fase `glossary` (o CONTEXT.md): documenta términos canónicos en la
  nota (soft, decisión 1.4).
- **Soft close** (decisión 1.3): sin fase `close` ⇒ WARNING en la nota;
  bloquea solo con `require_close_phase: true` en la spec.
- Sesiones sin `phase`: flujo actual EXACTO (reconstructor, git diff).

### 7.2 Action Engine: siguiente fase

`cortex next`: si la sesión activa tiene última fase, una acción nueva
`suggest_next_phase` propone la siguiente (`implement` → "¿revisar?").
Reusa el scheduler existente (score/costo/reversibilidad), catalogo v1 → 11
acciones. Barato, NO bloqueante.

## 8. Error handling y compatibilidad

- Emisores sin fase: todo igual (gate G-A1 lo garantiza con la tabla
  completa de combinaciones de sources × fase).
- `phase` inválida: rechazo explícito con mensaje exacto (servicio + MCP).
- YAML de sesiones con `phase`: legible por el sistema actual; backward
  compatible (campo opcional).
- Skills de terceros malformadas: la validación dura del checkpoint las
  rechaza con mensaje claro (patrón P6/P9, nunca paridad fingida).

## 9. Verificación (gates estilo Obra 07 — un gate por commit)

| Gate | Contenido | Criterio de pase |
|---|---|---|
| G-A1 | Schema `phase` + round-trip storage + `infer_mode` tabla completa | tests tabla combinaciones (con/sin fase × sources) verdes; suite cargo `-p cortex-app` + workspace sin regresión; oráculo Python intacto (no se toca) |
| G-A2 | Barra de calidad por fase | casos accept/warn/redelegate por cada fase (6 fases × 3 desenlaces); `phase: None` ⇒ comportamiento actual byte-idéntico |
| G-A3 | Reestructura skill templates + instalación | templates thin + references son SSoT; instalación produce los archivos byte-exactos (test include_str == disco, patrón existente) |
| G-A4 | `cortex setup composed` end-to-end | 8 skills + AGENTS.md block escritos byte-exactos; skeleton + INSTALL-COMPOSED.md presentes |
| G-A5 | Documenter línea de fases | golden: nota con línea de fases exacta para un set dado de checkpoints con fase; nota sin fase == golden actual |
| G-A6 | `next` sugiere siguiente fase + docs | acción presente con scheduler; cold start sin regresión (N=20); ESTADO-ACTUAL/HANDOFF/13 resuelto |

Cierre de paquete (convención del repo): (a) metadatos completos, (b)
red/green de tests nuevos, (c) gates build+verify PASS, (d) oráculo
2552/21/0/0 bajo lock (no re-corrido si nada dependiente cambió),
(e) cold start N=20, (f) revisión Approved, (g) registro en docs.

## 10. Estimación y archivos tocados

~800–1.200 LOC Rust + templates + gates. Cero deps nuevas.

| Ámbito | Archivos |
|---|---|
| Schema | `cortex-app/src/session/models.rs` (CheckpointPhase + campo), serialización |
| Infer | `cortex-app/src/session/service.rs` + tests |
| Gates | `cortex-app/src/session/quality_gates.rs` + tests |
| Templates | `cortex-setup` (templates skills ×3 reestructuradas + familia composed/ ×8 + INSTALL-COMPOSED.md) |
| CLI | `cortex-cli` (subcomando `setup composed`) |
| Documenter | `cortex-app/src/documenter/*` (línea de fases + evidencia por fase) |
| Actions | `cortex-actions` (acción `suggest_next_phase`) |

## 11. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Ruptura de schema (extra=forbid / immutabilidad) | campo opcional + tests de compat; emisores actuales intactos |
| COMPOSED canibaliza Managed | Managed sigue siendo default sin flujo propio; COMPOSED es opt-in explícito |
| Skills de terceros malformadas | validación dura en servicio/MCP con mensaje claro |
| Instalador no soporta skills en directorio | verificar `setup_templates`/instalador; ajuste quirúrgico si copia solo archivos |
| El documenter pierde riqueza sin git | ya reconstruye desde checkpoints (gitless); COMPOSED suma fases ⇒ más rico, no menos |
| Oráculo Python lee una sesión con phase | no ocurre (fixtures propios); si ocurriera, divergencia declarada + fixture congelado |

## 12. Qué NO cambia

- La Session y el Checkpoint base (immutabilidad, sources cerrados).
- El reconstructor del documenter (sigue funcionando para BYO).
- El Modo Managed (SDDwork): camino recomendado sin flujo propio.
- El Action Engine existente (categorías, scheduler, learning, feedback).
- Ningún gate vigente P1–P12 requiere recaptura.