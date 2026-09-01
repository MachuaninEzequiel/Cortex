# Obra 08 Stream A — Modo COMPOSED y Skills Expertas — Plan de Implementación

> **Para workers agénticos:** SKILL REQUERIDA: usar `superpowers:subagent-driven-development` (recomendado) o `superpowers:executing-plans` para implementar este plan tarea por tarea. Los pasos usan sintaxis de checkbox (`- [ ]`).
> **Spec:** `docs/transformacion/13-MODO-COMPOSED-Y-SKILLS-EXPERTAS.md` (el plan argumenta desde la spec; ejecutores leen ambos).

**Goal:** Implementar el 4º modo de sesión COMPOSED (checkpoints con fase + barra de calidad por fase + documenter enriquecido) y reestructurar las skills de Cortex a thin-SKILL.md + references/ de craft, con la familia de referencia `composed` instalable.

**Architecture:** Extensión aditiva del dominio de sesiones de `cortex-app` (campo opcional + función pura de inferencia + gates puros), templates de skills en `cortex-setup` (SSoT con test include_str == disco), subcomando `setup composed` en `cortex-cli`, acción nueva en `cortex-actions`.

**Tech Stack:** Rust (workspace existente), serde/serde_yaml, ratatui NO (no se toca UI), minijinja (templates existentes), tests cargo por crate.

**Spec:** `docs/transformacion/13-MODO-COMPOSED-Y-SKILLS-EXPERTAS.md`

## Global Constraints

- **Rust-first, oráculo congelado:** NO tocar `cortex/` (Python), `tests/` (Python), `pyproject.toml`, ni el oráculo 2552 tests. Los cambios de schema son SOLO Rust con divergencia declarada.
- **Cero deps nuevas:** workspace Cargo.lock append-only; sin `cargo add` de paquetes nuevos.
- **`#![forbid(unsafe_code)]`** en toda lógica nueva (patrón vigente de cortex-app).
- **WIP P8d/TUI vigente:** NO tocar `rust/crates/cortex-tui/` ni `rust/crates/cortex-setup/src/ide/**`. Solo se tocan templates de skills (fuera de ide/).
- **Verificación:** cada task termina con `cargo test -p <crate>` verde; clippy `-D warnings` y `cargo fmt` limpios; suite workspace sin regresión.
- **Commits:** Conventional en español, scope `feat|fix|docs|chore(obra08 streamA ...)`; un commit por task; mensajes densos con evidencia.
- **Compatibilidad:** emisores sin `phase` ⇒ comportamiento byte-idéntico al actual (tabla de combinaciones en tests).
- **Gate por commit:** el cierre de cada task ES un gate; los gates nombrados (G-A1…) referencian los de la spec §9.

---

### Task A1: CheckpointPhase + campo `phase` en Checkpoint (G-A1a)

**Files:**
- Modify: `rust/crates/cortex-app/src/session/mod.rs` (o donde viva `Checkpoint`/`SessionMode` — confirmar en Step 1)
- Test: `rust/crates/cortex-app/tests/phase_schema.rs` (nuevo)

**Interfaces:**
- Consumes: struct `Checkpoint` existente (immutable, serde, sesión YAML).
- Produces:
  ```rust
  #[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, serde::Serialize, serde::Deserialize)]
  #[serde(rename_all = "snake_case")]
  pub enum CheckpointPhase { Grill, Spec, Plan, Implement, Review, Close }

  impl CheckpointPhase {
      pub fn as_str(&self) -> &'static str;      // "grill" | "spec" | "plan" | "implement" | "review" | "close"
      pub fn parse(s: &str) -> Option<CheckpointPhase>;
  }
  // y en Checkpoint:
  #[serde(default, skip_serializing_if = "Option::is_none")]
  pub phase: Option<CheckpointPhase>,            // NUEVO campo opcional
  ```
  (Los tasks posteriores consumen `CheckpointPhase` y `Checkpoint::phase` con estas firmas.)

- [ ] **Step 1: Confirmar la ubicación exacta del tipo Checkpoint**

Run:
```bash
cd /home/chucho/Cortex
rg -n "pub struct Checkpoint" rust/crates/cortex-app/src/
rg -n "pub enum SessionMode" rust/crates/cortex-app/src/
```
Expected: localizar `Checkpoint` y `SessionMode` (probablemente `session/mod.rs`). Si viven en otro módulo (ej. `models.rs`), usá ESA ruta para todo el plan. Reportá la ruta en el commit.

- [ ] **Step 2: Escribir el test que falla**

Crear `rust/crates/cortex-app/tests/phase_schema.rs`:
```rust
use cortex_app::session::{Checkpoint, CheckpointPhase};

fn base_checkpoint() -> Checkpoint {
    // Usá el constructor/estructura real del Checkpoint existente:
    // mirá los tests de session existentes (rg "Checkpoint" rust/crates/cortex-app/src/session/)
    // y cloná el patrón de construcción que usan (struct literal o constructor de test).
}

#[test]
fn phase_roundtrip_yaml() {
    let cps = [CheckpointPhase::Grill, CheckpointPhase::Spec, CheckpointPhase::Plan,
               CheckpointPhase::Implement, CheckpointPhase::Review, CheckpointPhase::Close];
    for p in cps {
        let mut cp = base_checkpoint();
        cp.phase = Some(p);
        let yaml = serde_yaml::to_string(&cp).unwrap();
        let back: Checkpoint = serde_yaml::from_str(&yaml).unwrap();
        assert_eq!(back.phase, Some(p), "roundtrip perdió fase {p:?}");
        assert_eq!(p.as_str().parse::<CheckpointPhase>(), Some(p));
    }
}

#[test]
fn no_phase_backward_compat() {
    // YAML de un checkpoint legado SIN campo phase (fixture literal):
    let yaml = "<copiar 1 checkpoint YAML real existente de .cortex/sessions/*.yaml o de fixtures de tests>";
    let cp: Checkpoint = serde_yaml::from_str(yaml).unwrap();
    assert_eq!(cp.phase, None);
}

#[test]
fn invalid_phase_string_rejected() {
    assert_eq!(CheckpointPhase::parse("asdf"), None);
    assert_eq!(CheckpointPhase::parse(""), None);
}
```
Nota: si `Checkpoint` tiene campos privados y no hay constructor público de test, los tests viven dentro del crate (módulo `#[cfg(test)]` en el archivo del tipo) siguiendo el patrón de tests de unidad existente. Adaptá la ubicación del test a lo que exista (unit vs integration), NO inventes constructores públicos nuevos sin necesidad.

- [ ] **Step 3: Correr el test y verificar que falla**

Run: `cargo test -p cortex-app phase_schema` (o el target del módulo de test).
Expected: FAIL de compilación: `CheckpointPhase` no existe / campo `phase` no existe.

- [ ] **Step 4: Implementar el mínimo**

En el archivo del tipo:
- Agregar enum `CheckpointPhase` con `as_str()` y `parse()` (tabla match exhaustiva; `parse` case-sensitive en minúsculas, igual que otros parsers del repo).
- Agregar campo `#[serde(default, skip_serializing_if = "Option::is_none")] pub phase: Option<CheckpointPhase>` al `Checkpoint`.
- Ajustar constructores/exhaustividad de match en el crate (el compilador los señala).

- [ ] **Step 5: Verificar verde + suite + clippy + fmt**

Run:
```bash
cargo test -p cortex-app
cargo clippy -p cortex-app -- -D warnings
cargo fmt --check
cargo test --workspace 2>&1 | tail -3
```
Expected: PASS en los tests nuevos; workspace sin regresión (el tail muestra conteo; si el workspace global falla por WIP ajeno documentado en `progress.md`, verificá los crates tocados y reportalo; el oráculo Python NO se corre).

- [ ] **Step 6: Commit**

```bash
git add rust/crates/cortex-app/src rust/crates/cortex-app/tests
git commit -m "feat(obra08 streamA schema): CheckpointPhase + campo phase opcional en Checkpoint (G-A1a) — roundtrip YAML x6 fases, backward-compat sin phase, parse inválida rechazada; oráculo Python intacto"
```

---

### Task A2: infer_mode → COMPOSED (G-A1b)

**Files:**
- Modify: donde viva `infer_mode` (buscar `infer_mode` en `rust/crates/cortex-app/src/`)
- Test: mismos archivos de tests de infer_mode existentes + casos nuevos

**Interfaces:**
- Consumes: `CheckpointPhase` (Task A1), enum `SessionMode` existente y su `infer_mode`.
- Produces: `SessionMode::Composed` (serializa `"composed"`); `infer_mode(checkpoints: &[Checkpoint]) -> SessionMode` con la prioridad de la spec §4 (1 sin checkpoints→BYO, 2 todos ci-bot→CI_REVIEW, 3 ∃phase→COMPOSED, 4 todos cortex-*→MANAGED, 5 resto→OBSERVED). Firma exacta = la firma existente de `infer_mode` (extendela, no la renombres).

- [ ] **Step 1: Escribir los tests que fallan**

Agregar al archivo de tests de infer_mode existente (tabla-driven):
```rust
#[test]
fn infer_mode_composed_when_any_phase() {
    // mezcla: un checkpoint cortex-SDDwork SIN phase + uno user-skill CON phase=implement
    let cps = vec![cp("cortex-SDDwork", None), cp("user-skill", Some(CheckpointPhase::Implement)), cp("ide-hook", None)];
    assert_eq!(infer_mode(&cps), SessionMode::Composed);
}

#[test]
fn infer_mode_composed_wins_over_all_cortex() {
    // todos cortex-* pero uno con phase → COMPOSED (no MANAGED)
    let cps = vec![cp("cortex-sync", Some(CheckpointPhase::Spec)), cp("cortex-SDDwork", None)];
    assert_eq!(infer_mode(&cps), SessionMode::Composed);
}

#[test]
fn infer_mode_backward_compat_sin_phase() {
    // sin phase: las combinaciones actuales dan los modos actuales
    let all_cortex = vec![cp("cortex-sync", None), cp("cortex-SDDwork", None)];
    assert_eq!(infer_mode(&all_cortex), SessionMode::Managed);
    let mixed = vec![cp("cortex-SDDwork", None), cp("ide-hook", None)];
    assert_eq!(infer_mode(&mixed), SessionMode::Observed);
    let none = vec![];
    assert_eq!(infer_mode(&none), SessionMode::Byo);
    let ci = vec![cp("ci-bot", None), cp("ci-bot", None)];
    assert_eq!(infer_mode(&ci), SessionMode::CiReview);
}
```
(Adaptá `cp(...)` al constructor real de Checkpoint usado en ese archivo de tests.)

- [ ] **Step 2: Correr y verificar que falla**

Run: `cargo test -p cortex-app <target_de_infer_mode>`
Expected: FAIL — `SessionMode::Composed` no existe / casos nuevos dan MANAGED u OBSERVED.

- [ ] **Step 3: Implementar**

- Agregar variante `Composed` al enum `SessionMode` con serialización snake_case (`composed`).
- Extender `infer_mode` con la regla 3 (∃ `phase.is_some()` ⇒ `Composed`) en la posición de prioridad correcta (entres CI_REVIEW y MANAGED).
- Ajustar exhaustividad de matches sobre `SessionMode` en el crate.

- [ ] **Step 4: Verificar verde + suite + clippy + fmt**

Run: `cargo test -p cortex-app && cargo clippy -p cortex-app -- -D warnings && cargo fmt --check && cargo test --workspace 2>&1 | tail -3`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add rust/crates/cortex-app/src
git commit -m "feat(obra08 streamA infer): SessionMode::Composed — infer_mode con fase gana a MANAGED, backward-compat tabla completa (G-A1b); serialize 'composed'"
```

---

### Task A3: Barra de calidad por fase (G-A2)

**Files:**
- Modify: `rust/crates/cortex-app/src/session/quality_gates.rs` (y su test)
- Test: tests de quality_gates existentes + nuevos

**Interfaces:**
- Consumes: `CheckpointPhase` (A1), struct `Checkpoint` (fields `phase`, `verified_claims`, `unverified_claims`, `artifacts_touched`, `note` — nombres reales del struct).
- Produces:
  ```rust
  pub enum PhaseGateOutcome { Pass, Warn(String), Redelegate(String) }

  // Función pura: aplica el gate de la fase; None si el checkpoint no tiene fase.
  pub fn check_phase_gate(cp: &Checkpoint) -> Option<PhaseGateOutcome>
  ```
  Reglas de la spec §3: `grill`→Pass sin gate; `spec`→≥1 verified_claim >10 chars; `plan`→≥1 artifact_touched; `implement`→artifacts_touched no vacío + ≥1 verified_claim >10 chars; `review`→≥1 verified_claim >10 chars; `close`→no aplica aquí (depende de la sesión, se valida en A5). Falla ⇒ `Warn` salvo `implement` sin evidencia ⇒ `Redelegate` (severidad igual al mecanismo actual).

- [ ] **Step 1: Escribir los tests que fallan**

En el archivo de tests de quality_gates:
```rust
#[test]
fn phase_gate_spec_needs_evidence() {
    let cp = cp_with_phase(CheckpointPhase::Spec, claims = vec!["ok"], artifacts = vec![]);
    assert!(matches!(check_phase_gate(&cp), Some(PhaseGateOutcome::Warn(_)))); // claim <= 10 chars
    let cp_good = cp_with_phase(CheckpointPhase::Spec, claims = vec!["validé la spec contra el código real"], artifacts = vec![]);
    assert_eq!(check_phase_gate(&cp_good), Some(PhaseGateOutcome::Pass));
}

#[test]
fn phase_gate_implement_redelegates_without_evidence() {
    let cp = cp_with_phase(CheckpointPhase::Implement, claims = vec![], artifacts = vec!["x.rs"]);
    assert!(matches!(check_phase_gate(&cp), Some(PhaseGateOutcome::Redelegate(_))));
    let cp_good = cp_with_phase(CheckpointPhase::Implement, claims = vec!["test rojo-verde en x.rs"], artifacts = vec!["x.rs"]);
    assert_eq!(check_phase_gate(&cp_good), Some(PhaseGateOutcome::Pass));
}

#[test]
fn phase_gate_none_returns_none() {
    let cp = cp_with_phase(?? NO — sin fase);
    assert_eq!(check_phase_gate(&cp), None); // emisores legados intactos
}
```
(Adaptá a los helpers del archivo de tests existente; claim >10 chars es condición: `claim.chars().count() > 10`.)

- [ ] **Step 2: Correr y verificar que falla**

Run: `cargo test -p cortex-app quality_gates` — FAIL: `check_phase_gate` no existe.

- [ ] **Step 3: Implementar**

Implementar `check_phase_gate` como función pura (IF sin I/O). Integrarla en el flujo de review de checkpoint existente SOLO cuando `cp.phase.is_some()` (la pipeline actual de 2 etapas no cambia para el resto).

- [ ] **Step 4: Verificar verde + suite + clippy + fmt**

Run: `cargo test -p cortex-app && cargo clippy -p cortex-app -- -D warnings && cargo fmt --check`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add rust/crates/cortex-app/src/session/quality_gates.rs
git commit -m "feat(obra08 streamA gates): barra de calidad por fase — spec/plan/implement/review con evidencia, None intacto (G-A2); implement sin evidencia redelegates"
```

---

### Task A4: Validación dura de `phase` en servicio y MCP (G-A1c)

**Files:**
- Modify: `rust/crates/cortex-app/src/session/service.rs` (método checkpoint) y el handler MCP equivalente (`rust/crates/cortex-mcp/src/handlers_*` — buscar `session_checkpoint`)
- Test: tests del service + del handler MCP

**Interfaces:**
- Consumes: `CheckpointPhase::parse` (A1), `SessionService::checkpoint` existente (encontrar firma real: probablemente recibe parámetros de checkpoint como strings/ActionCheckpointInput).
- Produces: comportamiento — cualquier `phase` string que no parsee ⇒ `Err` con mensaje exacto:
  `invalid phase '<x>'. Valid: grill, spec, plan, implement, review, close`
  (patrón de mensajes canónicos del repo; MCP devuelve el error como resultado de tool con marca de error, patrón existente).

- [ ] **Step 1: Escribir los tests que fallan**

- Service: `checkpoint` con `phase="asdf"` ⇒ `Err` con el mensaje exacto; `phase="review"` ⇒ Ok y el checkpoint queda con `phase=Some(Review)`.
- MCP handler: `cortex_session_checkpoint` con `phase` inválida ⇒ tool result de error con el mensaje; válida ⇒ herramienta normal.
(Usá los helpers de tests existentes de cada área; en MCP, el patrón de golden/backends inyectables ya existe.)

- [ ] **Step 2: Correr y verificar que falla**

Run: `cargo test -p cortex-app session` y `cargo test -p cortex-mcp` — FAIL: fase inválida aceptada (o campo ignorado).

- [ ] **Step 3: Implementar**

- En el service: parsear `phase` y rechazar inválidas ANTES de construir/append el checkpoint (validación dura, patrón P6/P9).
- En el handler MCP: el service ya rechaza; asegurar que el error se propaga como tool error (nunca panic, nunca silencio).

- [ ] **Step 4: Verificar verde + suite + clippy + fmt**

Run: `cargo test -p cortex-app && cargo test -p cortex-mcp && cargo clippy -p cortex-app -p cortex-mcp -- -D warnings && cargo fmt --check`
Expected: PASS; contrato MCP congelado intacto (goldens MCP sin recaptura).

- [ ] **Step 5: Commit**

```bash
git add rust/crates/cortex-app/src/session rust/crates/cortex-mcp/src
git commit -m "feat(obra08 streamA validate): phase inválida rechazada en service + MCP con mensaje canónico (G-A1c); goldens MCP intactos"
```

---

### Task A5: Documenter — línea de fases + evidencia por fase (G-A5a)

**Files:**
- Modify: `rust/crates/cortex-app/src/documenter/` (buscar donde se arma la nota de sesión / session note)
- Test: tests del documenter existentes + nuevos

**Interfaces:**
- Consumes: `CheckpointPhase` (A1), lista de checkpoints de la sesión.
- Produces:
  ```rust
  // "grill → spec → plan → implement → review → close"; None si no hay checkpoints con fase.
  pub fn phase_line(checkpoints: &[Checkpoint]) -> Option<String>

  // claims verificadas agrupadas por fase, en orden de fases; vacío si no hay fases.
  pub fn evidence_by_phase(checkpoints: &[Checkpoint]) -> Vec<(CheckpointPhase, Vec<String>)>
  ```
  La nota de sesión (solo en sesiones con ≥1 checkpoint con fase) incluye: sección `Fases: <línea>` + evidencia agrupada. Sesiones sin fase: salida byte-idéntica al actual (golden existente no se recaptura).

- [ ] **Step 1: Escribir los tests que fallan**

```rust
#[test]
fn phase_line_joins_in_order() {
    let cps = vec![cp(Spec), cp(Implement), cp(Review)];
    assert_eq!(phase_line(&cps), Some("spec → implement → review".to_string()));
    let none = vec![cp(None), cp(None)];
    assert_eq!(phase_line(&none), None);
}

#[test]
fn evidence_grouped_by_phase() {
    // cp spec con claim "a", cp review con claim "b" y "c"
    let ev = evidence_by_phase(&cps);
    assert_eq!(ev, vec![(CheckpointPhase::Spec, vec!["a".into()]), (CheckpointPhase::Review, vec!["b".into(), "c".into()])]);
}
```
Más un test de integración del documenter: para un set fijo de checkpoints con fases, la nota generada contiene la línea exacta `Fases: spec → implement` y las claims agrupadas (golden literal inline); para el mismo set SIN fases, la nota == la nota actual (comparar contra el golden existente del documenter).

- [ ] **Step 2: Correr y verificar que falla**

Run: `cargo test -p cortex-app documenter` — FAIL: funciones no existen / nota sin Fases.

- [ ] **Step 3: Implementar**

- `phase_line` y `evidence_by_phase` (función pura; orden de fases = orden de aparición en los checkpoints, duplicados colapsados preservando primera aparición; unión con " → ").
- En el generador de nota: si `phase_line(...).is_some()`, agregar la sección; el resto del flujo intacto.

- [ ] **Step 4: Verificar verde + suite + clippy + fmt**

Run: `cargo test -p cortex-app && cargo clippy -p cortex-app -- -D warnings && cargo fmt --check && cargo test --workspace 2>&1 | tail -3`
Expected: PASS; goldens existentes del documenter sin recaptura.

- [ ] **Step 5: Commit**

```bash
git add rust/crates/cortex-app/src/documenter
git commit -m "feat(obra08 streamA documenter): línea de fases + evidencia por fase en la nota (G-A5a); sin fase = golden actual intacto"
```

---

### Task A6: Soft close — `require_close_phase` (G-A5b)

**Files:**
- Modify: loader de specs (`cortex-app/src/documenter/spec_loader.rs` o donde se parsee `verification_hooks`), doc verifier / generador de nota
- Test: tests del spec_loader + documenter

**Interfaces:**
- Consumes: `phase_line` (A5), `CheckpointPhase::Close`.
- Produces:
  - Spec: campo opcional `require_close_phase: bool` (default `false`) en frontmatter (leniente: YAML roto ⇒ default false, nunca falla — patrón existente).
  - Documenter: si `require_close_phase=true` y la sesión NO tiene checkpoint `phase=Close` ⇒ el cierre se marca con WARNING en la nota (soft, NO bloquea `Closed` — según spec §1.3 la palabra exacta es: "registra WARNING; bloquea solo con flag"). Con flag y sin fase close: la decisión de status pasa a `HANDOFF` (no CLOSED) — verificar contra spec: spec dice "bloquea el cierre Closed SOLO si la spec declara require_close_phase: true".

- [ ] **Step 1: Escribir los tests que fallan**

```rust
// spec_loader: frontmatter con require_close_phase: true ⇒ Some(true); ausente/roto ⇒ false (leniente)
// documenter: flag=true sin fase close ⇒ status HANDOFF + warning en nota;
//             flag=true con fase close ⇒ CLOSED normal;
//             flag=false sin close ⇒ CLOSED normal (comportamiento actual)
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `cargo test -p cortex-app` — FAIL.

- [ ] **Step 3: Implementar**

- Parse del flag en spec_loader (default false, leniente).
- En el flujo de decisión de status del documenter: consultar flag + `phase_line` contiene "close" ⇒ decidir HANDOFF con warning (y el warning en nota).

- [ ] **Step 4: Verificar verde + suite + clippy + fmt**

Run: `cargo test -p cortex-app && cargo clippy -p cortex-app -- -D warnings && cargo fmt --check`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add rust/crates/cortex-app/src
git commit -m "feat(obra08 streamA softclose): require_close_phase en spec — sin fase close ⇒ HANDOFF+warning solo con flag (G-A5b); default soft behavior actual"
```

---

### Task A7: Reestructura templates — `cortex-sync` (G-A3a)

**Files:**
- Modify: `rust/crates/cortex-setup/` — templates de skills (buscar dónde están hoy: `rg -l "cortex-sync" rust/crates/cortex-setup/`; probablemente templates/skills o código generador). NO tocar `src/ide/**`.
- Test: tests de setup existentes (patrón "copia embebida == disco") + nuevos

**Interfaces:**
- Consumes: mecanismo instalador existente de skills (si copia archivos planos, adaptarlo para copia de directorio — ver Step 3).
- Produces: template instalable de `cortex-sync` como DIRECTORIO:
  ```
  cortex-sync/SKILL.md                      (thin, ~60 líneas, contrato)
  cortex-sync/references/spec-craft.md      (craft: preguntas, trampas, criterios)
  cortex-sync/references/proposal-craft.md  (craft alternativas)
  ```
  Contrato del SKILL.md (contenido REAL, no placeholder): frontmatter exacto del actual (`name: cortex-sync`, `description: Cortex PRE-FLIGHT (Spec Creation Only). NO WRITE PERMISSIONS.`) + secciones: "MANDATORY FIRST STEP - NO EXCEPTIONS" (sync_ticket), Mision, Limites estrictos (write/edit/bash false), Pre-flight CONTEXT.md, Flujo obligatorio (pasos 1-3.5 con las llamadas MCP exactas del actual), "Salida" (spec persistida + handoff). Todo lo que hoy es regla de gobernanza se conserva; nada de craft en SKILL.md.
  `spec-craft.md` DEBE cubrir (contenido real): qué preguntas hacer antes de escribir una spec (objetivo medible, alcance, anti-objetivos), cómo contrastar con código real (glob→leer→citar líneas), trampas comunes (specs que describen solución en vez de problema, criterios de aceptación no verificables), ejemplo de acceptance criteria bueno vs malo (3 pares).
  `proposal-craft.md` DEBE cubrir: cuándo ofrecer alternativas, cómo escribir rejected_reason honesto (evidencia, no gusto), estructura de 1 resumen + 2-3 alternativas + riesgo.
- [ ] **Step 1: Escribir el test que falla**

Test en cortex-setup (patrón existente de templates): el template embebido de `cortex-sync` es un directorio con los 3 archivos, y la instalación produce esos archivos byte-idénticos al include_str! (adaptar el helper existente para árboles).

- [ ] **Step 2: Correr y verificar que falla**

Run: `cargo test -p cortex-setup` — FAIL: template no existe como directorio.

- [ ] **Step 3: Implementar**

- Mover/crear el template `cortex-sync` como directorio con los 3 archivos (contenido real conforme al contrato de arriba; el SKILL.md thin conserva TODAS las reglas MCP del actual — comparar contra el instalado en `.cortex/skills/cortex-sync.md` del repo).
- Si el instalador copia archivos planos por nombre, extenderlo para copiar directorios completos (mantener byte-exactitud y el test include_str == disco).
- Actualizar la instalación real en `.cortex/skills/` NO es parte de este commit (se instala vía `cortex ide`/setup al final del stream; el test de instalación usa un dir temporal).

- [ ] **Step 4: Verificar verde + suite + clippy + fmt**

Run: `cargo test -p cortex-setup && cargo clippy -p cortex-setup -- -D warnings && cargo fmt --check`
Expected: PASS. Verificar que los tests de instalación existentes (no solo nuevos) sigan verdes.

- [ ] **Step 5: Commit**

```bash
git add rust/crates/cortex-setup
git commit -m "feat(obra08 streamA templates): cortex-sync thin + references/spec-craft + proposal-craft (G-A3a); instalación byte-exacta en árbol"
```

---

### Task A8: Reestructura templates — `cortex-SDDwork` (G-A3b)

**Files:**
- Modify: `rust/crates/cortex-setup/` (templates)
- Test: tests de setup existentes + nuevos

**Interfaces:**
- Consumes: instalador de árboles (A7).
- Produces: template instalable `cortex-SDDwork/SKILL.md` (thin ~70 líneas, contrato) + `references/implement-craft.md`.
  Contrato SKILL.md: frontmatter exacto actual + secciones actuales conservadas como CONTRATO: pre-flight (session activa, mensaje exacto "No active session..."), FAST TRACK (criterios 1-2 archivos, pasos, checkpoint con source="cortex-SDDwork"), DEEP TRACK (delegación y gate `cortex_review_checkpoint` entre pasos, criterios de cuándo), "NO emitas YAML".
  `implement-craft.md` DEBE cubrir: Iron Law TDD (test rojo primero) con ejemplo de ciclo, tamaño de cambio (commits atómicos, un gate por commit), revisión del diff propio antes de declarar (qué mirar: cambios fuera de scope, dead code, errores silenciosos), cuándo delegar a subagentes vs implementar directo, verificación con evidencia (comandos reales en claims).

- [ ] **Step 1: Escribir el test que falla** — igual patrón que A7 (existencia de árbol + byte-exactitud).

- [ ] **Step 2: Correr y verificar que falla** — `cargo test -p cortex-setup` FAIL.

- [ ] **Step 3: Implementar** — crear árbol con contenido real conforme al contrato; conservar TODAS las reglas/gobernanza del actual (comparar contra `.cortex/skills/cortex-SDDwork.md`).

- [ ] **Step 4: Verificar verde + suite + clippy + fmt**

Run: `cargo test -p cortex-setup && cargo clippy -p cortex-setup -- -D warnings && cargo fmt --check`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add rust/crates/cortex-setup
git commit -m "feat(obra08 streamA templates): cortex-SDDwork thin + references/implement-craft (G-A3b); contrato MCP intacto"
```

---

### Task A9: Reestructura templates — `cortex-documenter` (G-A3c)

**Files:**
- Modify: `rust/crates/cortex-setup/` (templates)
- Test: tests de setup existentes + nuevos

**Interfaces:**
- Consumes: instalador de árboles (A7).
- Produces: template `cortex-documenter/SKILL.md` (thin ~60 líneas, contrato) + `references/close-craft.md`.
  Contrato SKILL.md: frontmatter exacto + flujo actual conservado como contrato (reconstruct → verificación → nota; comandos MCP exactos).
  `close-craft.md` DEBE cubrir: qué es una claim verificable (evidencia observable vs opinión), placeholders prohibidos (tbd/todo/fixme/??? — el gate los marca), cómo escribir el handoff a la siguiente sesión (context_for_next útil), cuándo sugerir ADRs (señales: decidimos/chose/trade-off — el documenter ya las detecta), auditoría de la propia nota antes de cerrar.

- [ ] **Step 1: Escribir el test que falla** — patrón A7.

- [ ] **Step 2: Correr y verificar que falla** — `cargo test -p cortex-setup` FAIL.

- [ ] **Step 3: Implementar** — árbol con contenido real; conservar gobernanza del actual.

- [ ] **Step 4: Verificar verde + suite + clippy + fmt**

Run: `cargo test -p cortex-setup && cargo clippy -p cortex-setup -- -D warnings && cargo fmt --check`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add rust/crates/cortex-setup
git commit -m "feat(obra08 streamA templates): cortex-documenter thin + references/close-craft (G-A3c); contrato intacto"
```

---

### Task A10: Familia de referencia `composed` + INSTALL-COMPOSED.md (G-A4a)

**Files:**
- Modify: `rust/crates/cortex-setup/` (templates)
- Test: tests de setup

**Interfaces:**
- Consumes: instalador de árboles (A7).
- Produces: `composed/` con 8 skills (cada una: `SKILL.md` + `references/` donde aplique + `agents/openai.yaml`) + `INSTALL-COMPOSED.md`:
  `grill/`, `to-spec/`, `to-tickets/`, `implement/`, `tdd/`, `diagnose/`, `review/`, `glossary/`.
  Contrato de cada SKILL.md (contenido real, spec §6):
  - Frontmatter: `name`, `description` rica (model-invoked) o con `disable-model-invocation: true` (user-invoked), `when-to-use`.
  - Sección "checkpoint": cómo emitir el checkpoint con `phase` + `verified_claims` + `artifacts_touched` + `note` (≤1 línea) — con el comando/llamada MCP exacta (`cortex_session_checkpoint` con los args).
  - Fases por skill: grill→grill; to-spec→spec; to-tickets→plan; implement/tdd/diagnose→implement; review→review; glossary→spec (solo si toca la spec).
  - 2-3 pasos núcleo de la skill (contenido real de la técnica: grilling = preguntas de aclaración + 5 whys; to-spec = secciones spec + acceptance criteria verificables; to-tickets = tickets con verificación por paso; implement = por ticket con contexto fresco; tdd = Iron Law red→green; diagnose = feedback loop antes de teorizar; review = 2 ejes Standards+Spec en paralelo; glossary = términos canónicos + ADR).
  - `agents/openai.yaml`: espejo del SKILL.md para doble harness (patrón mattpocock: name/description/instructions).
  - `references/`: contenido craft específico donde el SKILL.md lo referencie (mínimo: implement/review/tdd).
  INSTALL-COMPOSED.md: cómo instalar la familia, cómo importar flujos externos (mattpocock via skills.sh, superpowers), cómo escribir una skill propia que cumpla el contrato.
- [ ] **Step 1: Escribir el test que falla** — el árbol `composed/` existe con exactamente los 8 dirs + INSTALL-COMPOSED.md, y cada skill tiene SKILL.md + agents/openai.yaml (assert de inventario); instalación byte-exacta.

- [ ] **Step 2: Correr y verificar que falla** — `cargo test -p cortex-setup` FAIL.

- [ ] **Step 3: Implementar** — crear los árboles con contenido real (el contenido técnica de cada skill: mínimo ~40-80 líneas de SKILL.md real, no esqueletos).

- [ ] **Step 4: Verificar verde + suite + clippy + fmt**

Run: `cargo test -p cortex-setup && cargo clippy -p cortex-setup -- -D warnings && cargo fmt --check`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add rust/crates/cortex-setup
git commit -m "feat(obra08 streamA composed): familia de 8 skills de referencia + INSTALL-COMPOSED.md (G-A4a); inventario + byte-exactitud testeados"
```

---

### Task A11: `cortex setup composed` (G-A4b)

**Files:**
- Modify: `rust/crates/cortex-cli/src/commands/setup_cmd.rs` (patrón del subcomando `agent` existente), `rust/crates/cortex-setup/` (si el instalador necesita un entrypoint)
- Test: tests de CLI existentes (`cli_commands_basic.rs` o el patrón de comandos setup)

**Interfaces:**
- Consumes: instalador de árboles (A7/A10).
- Produces: `cortex setup composed [--project-root]` — instala `composed/` en `.cortex/skills/composed/` y escribe el bloque `## Agent skills` en CLAUDE.md/AGENTS.md (reusando los writers existentes de cortex-setup — verificar qué writers hay; si no hay writer de bloque AGENTS, escribe el bloque append-only con marcadores, patrón del install de codex). Salida resumida estilo setup existente.

- [ ] **Step 1: Escribir el test que falla** — test de integración CLI: correr `setup composed` sobre un fixture project (patrón make_fixture_project) ⇒ `.cortex/skills/composed/grill/SKILL.md` existe y es byte-igual al template; AGENTS.md contiene el bloque. (Reusar helpers de tests CLI existentes.)

- [ ] **Step 2: Correr y verificar que falla** — FAIL: comando no existe.

- [ ] **Step 3: Implementar** — subcomando nuevo siguiendo el patrón exacto de `setup agent` (dispatch manual por primer token del setup_cmd: agregar "composed" al routing interno).

- [ ] **Step 4: Verificar verde + suite + clippy + fmt**

Run: `cargo test -p cortex-cli && cargo test -p cortex-setup && cargo clippy -p cortex-cli -p cortex-setup -- -D warnings && cargo fmt --check`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add rust/crates/cortex-cli rust/crates/cortex-setup
git commit -m "feat(obra08 streamA setup): cortex setup composed — instala familia + bloque Agent skills (G-A4b); fixture end-to-end verde"
```

---

### Task A12: Action Engine — `suggest_next_phase` (G-A6a)

**Files:**
- Modify: `rust/crates/cortex-actions/` (catalog + registry: buscar `build_default_registry`, `registry.rs`, `models.rs`)
- Test: tests de cortex-actions existentes (`scheduler`/`models`)

**Interfaces:**
- Consumes: `CheckpointPhase` (A1), sesión activa del contexto de acciones (ActionContext existente).
- Produces:
  ```rust
  // Siguiente fase sugerida; None en close.
  pub fn next_phase(p: CheckpointPhase) -> Option<CheckpointPhase>
  // grill→spec→plan→implement→review→close→None
  ```
  Acción nueva en el catálogo: `suggest_next_phase` — impacto bajo (categoria maintenance/learning según convención existente), costo instant, `reversible=true`, `auto_ok=true` (es solo un mensaje), precondición: sesión activa con última fase. Effect: mensaje "Sesión en implement → siguiente fase sugerida: review".

- [ ] **Step 1: Escribir los tests que fallan**

```rust
#[test]
fn next_phase_chain() {
    assert_eq!(next_phase(CheckpointPhase::Grill), Some(CheckpointPhase::Spec));
    assert_eq!(next_phase(CheckpointPhase::Review), Some(CheckpointPhase::Close));
    assert_eq!(next_phase(CheckpointPhase::Close), None);
}
// + test del registry: la acción existe con cost/reversible/auto_ok correctos;
// + test de scheduler: con sesión en implement, propose incluye suggest_next_phase.
```

- [ ] **Step 2: Correr y verificar que falla** — `cargo test -p cortex-actions` FAIL.

- [ ] **Step 3: Implementar** — `next_phase` pura + entrada de catálogo (siguiendo el patrón de las 10 acciones existentes, incl. precondición y effect).

- [ ] **Step 4: Verificar verde + suite + clippy + fmt**

Run: `cargo test -p cortex-actions && cargo clippy -p cortex-actions -- -D warnings && cargo fmt --check && cargo test --workspace 2>&1 | tail -3`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add rust/crates/cortex-actions
git commit -m "feat(obra08 streamA next): accion suggest_next_phase — cadena de fases + precondicion sesion activa (G-A6a); scheduler intacto"
```

---

### Task A13: Gate final del stream A — suite + cold start + docs (G-A6b)

**Files:**
- Modify: `docs/transformacion/ESTADO-ACTUAL.md`, `docs/transformacion/HANDOFF.md`, `docs/transformacion/13-MODO-COMPOSED-Y-SKILLS-EXPERTAS.md` (marcar resuelto)
- Test: corrida completa

**Interfaces:**
- Consumes: todas las tasks A1–A12.

- [ ] **Step 1: Suite completa**

Run: `cargo test --workspace 2>&1 | tail -3 && cargo clippy --workspace -- -D warnings && cargo fmt --check`
Expected: workspace verde (o solo WIP ajeno documentado); clippy/fmt limpios.

- [ ] **Step 2: Cold start N=20**

Correr el patrón de medición del repo (release si hay binario built; si no, documentar medición debug):
```bash
cd /home/chucho/Cortex && cargo build --release -p cortex-cli
for i in $(seq 1 20); do /usr/bin/time -f "%e" ./target/release/cortex setup composed --help >/dev/null 2>>/tmp/cold-a.txt; done
```
Expected: documentar mediana; sin regresión notable vs baseline (<100 ms objetivo para comandos livianos; cualquier comando onnx/memoria se mide honesto).

- [ ] **Step 3: Docs de cierre**

- ESTADO-ACTUAL.md: agregar sección Obra 08 stream A (features, gates G-A1…G-A6 PASS, divergencia declarada: schema phase es extensión nativa Rust-only).
- HANDOFF.md: actualizar §7 con el estado del stream A y la deuda restante si la hay.
- 13-…: marcar `> Estado: RESUELTO por obra 08 stream A (2026-08-27)`.

- [ ] **Step 4: Instalación real de las skills reestructuradas**

Correr el setup/ide existente que instala skills sobre el repo (el mecanismo que instaló `.cortex/skills/`) para reemplazar las 3 skills viejas por las thin+references, y `cortex setup composed` para la familia. Verificar con `ls .cortex/skills/`. (Si el mecanismo de instalación del repo mismo requiere el binario built: usar `./target/release/cortex`.)

- [ ] **Step 5: Commit**

```bash
git add docs/transformacion/ESTADO-ACTUAL.md docs/transformacion/HANDOFF.md docs/transformacion/13-MODO-COMPOSED-Y-SKILLS-EXPERTAS.md
git commit -m "docs(obra08 streamA): cierre — suite verde, cold start medido, docs de cierre, skills thin instaladas en el repo (G-A6b)"
```

---

## Self-Review (stream A)

- **Cobertura spec:** §2→A1, §3→A3, §4→A2, §5→A7-A9, §6→A10-A11, §7.1→A5-A6, §7.2→A12, §8→A1/A4, §9→gates A1-A13, §10→estimación (tasks), §11→A1/A4 mitigan, §12→intacto salvo install (A13 step 4). Sin huecos.
- **Tipos consistentes:** `CheckpointPhase` (A1) usado en A2/A3/A4/A5/A6/A12; `infer_mode` firma existente extendida (A2); `check_phase_gate` (A3) solo lo consume la pipeline de review; `phase_line`/`evidence_by_phase` (A5) consumidos por A6. `SessionMode::Composed` serializado "composed" (A2) es observable en `session list --json`.
- **Sin placeholders:** todo template especifica secciones + contenido real requerido; adaptaciones permitidas solo donde el plan indica "confirmar ubicación" con los greps exactos.