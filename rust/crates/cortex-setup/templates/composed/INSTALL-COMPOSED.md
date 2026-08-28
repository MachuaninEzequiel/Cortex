# INSTALL-COMPOSED — la familia de skills COMPOSED

Ocho skills de referencia que componen el **cuarto modo de sesion** de Cortex: el middle no lo orquesta Cortex, lo compones vos — una cadena de skills chicas que emiten checkpoints con `phase`. Cortex reconoce, registra y documenta.

```
grill → to-spec → to-tickets → implement (tdd | diagnose) → review → (cierre: /cortex-documenter o cortex finish-session)
 glossary acompana cuando el lenguaje lo pide
```

## Instalar

### Con el CLI (oficial, a partir de Obra 08 A11)

```bash
cortex setup composed            # en la raiz del proyecto destino
```

Copia la familia a `.cortex/skills/composed/` del proyecto (byte-exacta) y escribe el bloque `## Agent skills` en `CLAUDE.md`/`AGENTS.md` para que tu agente sepa que existen.

### Manual (standalone, antes de A11 o en un proyecto sin cortex-cli)

```bash
cp -r rust/crates/cortex-setup/templates/composed <proyecto>/.cortex/skills/composed
```

## Importar flujos externos

El modo COMPOSED no exige usar estas skills: **exige el contrato** (checkpoint con `phase`). Cualquier cadena vale:

- **mattpocock/skills** (`skills.sh` / plugin Claude Code): su flujo `grill-with-docs → to-spec → to-tickets → implement → code-review → ship` mapea 1:1 con las fases. Para que Cortex vea la cadena, envuelve cada paso con el checkpoint que indica el contrato de abajo (o copia el `SKILL.md` de la familia como wrapper: la skill externa hace el trabajo, el wrapper emite el checkpoint al terminar).
- **obra/superpowers**: `brainstorming → writing-plans → executing-plans → tdd → requesting-code-review → finishing-a-development-branch` — mismo principio: mapea brainstorming→`grill`/`spec`, writing-plans→`plan`, executing/tdd→`implement`, code-review→`review`, finishing→`close`.
- **Tus propias skills**: cualquiera que pueda emitir un `cortex_session_checkpoint` al terminar su etapa.

## Escribir una skill propia: el contrato

Para que Cortex reconozca tu cadena como COMPOSED, cada skill emite al terminar su etapa:

```json
cortex_session_checkpoint({
  "session_id": "<activa — ver cortex_session_status>",
  "source": "user-skill",
  "phase": "<grill|spec|plan|implement|review|close>",
  "verified_claims": ["<evidencia real: comando + resultado>"],
  "unverified_claims": ["<asumido, no probado>"],
  "artifacts_touched": ["<paths>"],
  "note": "<handoff a la siguiente fase, <=1 linea>"
})
```

Notas del contrato:

- `source: "user-skill"` es la forma de distinguir una skill tuya de un agente cortex (`cortex-*`) o de un ide-hook.
- `phase` **no esta en el inputSchema congelado** del server MCP: pasarlo igual como argumento extra; el servicio lo valida (fase invalida ⇒ rechazo explicito con la lista de fases validas).
- Los gates de fase exigen evidencia: `spec`/`review` piden un `verified_claims` de >10 chars; `plan`/`implement` piden `artifacts_touched`; `implement` sin evidencia ⇒ **redelegate**. Una skill cuyo checkpoint va a fallar el gate no es "registrable": arregla la evidencia, no el gate.
- Skills user-invoked declaran `disable-model-invocation: true` (Claude Code) y `policy.allow_implicit_invocation: false` en `agents/openai.yaml` (Codex). Las model-invoked omiten ambos y llevan `description` con disparadores ("Usar cuando...").

### Invocacion

- **User-invoked** (solo el humano): `grill`, `to-spec`, `to-tickets`, `review`, `glossary`.
- **Model-invoked** (el modelo las alcanza solas): `implement`, `tdd`, `diagnose`.
- Una skill user-invoked puede componer model-invoked ("Call the Skill tool with `tdd`"), nunca al reves.

## Cierre de la cadena

El cierre sigue siendo el de Cortex: `cortex finish-session` (o `/cortex-documenter`) corre los verification hooks de la spec y el documenter escribe la nota con la **linea de fases** (`grill → spec → plan → implement → review`). `require_close_phase: true` en la spec hace obligatorio el checkpoint `phase: close`.

## Verificacion rapida

```bash
cortex session list --json        # mode: "composed" si hay checkpoints con phase
cortex session show <id> --json   # detalle: modo + checkpoints con fase
```
