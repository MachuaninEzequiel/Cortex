---
title: Plan 05 — Materialización en Pi Coding Agent (caso especial)
status: ✅ CERRADA (2026-05-14)
phase: 2 (depende de Plan 01 y 02)
implementacion: ../implementacion/05-ide-pi.md
---

# Plan 05 — Materialización en Pi Coding Agent

**Pi es el caso más complejo** porque tiene su propio bundle (`cortex-pi/`) con 9 agents (los 3 compartidos + 4 Pi-only: sync, SDDwork, security-auditor, test-verifier), `agent-chain.yaml` declarativo, `teams.yaml`, extensions TypeScript y un justfile como entry point.

## Modelo mental de Pi

| Concepto Cortex | Pi lo llama | Path |
|-----------------|-------------|------|
| Skill primario | "Agent" (separado) | `.pi/agents/cortex-sync.md`, `.pi/agents/cortex-SDDwork.md` |
| Subagent | "Agent" (mismo dir) | `.pi/agents/cortex-code-explorer.md`, `implementer`, `documenter` |
| Agents Pi-only | "Agent" extra | `.pi/agents/cortex-security-auditor.md`, `cortex-test-verifier.md` |
| Herramienta MCP | "MCP server" via pipx-bin | `.pi/mcp.json::cortex` con env `CORTEX_CONFIG_PATH` |
| Skills (capacidades reusables) | "Skill" | `.pi/skills/cortex-{vault,python,testing}.md`, `obsidian-index.md` |
| Delegación declarativa | `agent-chain.yaml` | `.pi/agents/agent-chain.yaml` |
| Composición de teams | `teams.yaml` | `.pi/agents/teams.yaml` |
| Damage control | `damage-control-rules.yaml` | `.pi/damage-control-rules.yaml` |
| Theme | `themes/cortex-dark.json` | `.pi/themes/` |
| Extensions TS | `extensions/*.ts` | `.pi/extensions/` |

**Particularidad clave:** los 3 subagents compartidos (explorer, implementer, documenter) coexisten en `.cortex/subagents/` (canonical) **y** en `cortex-pi/.pi/agents/` (Pi bundle). Hay riesgo de drift documentado en Olas 0-4.

## Cómo se sincroniza canonical → Pi

`cortex inject --ide pi` ejecuta `PiAdapter.inject_profiles` que **copia recursivamente todo `cortex-pi/`** al `project_root`. Eso significa:

- Los 9 agents en `cortex-pi/.pi/agents/*.md` van al proyecto.
- `teams.yaml`, `agent-chain.yaml`, `damage-control-rules.yaml` van al proyecto.
- Extensions, skills, themes van al proyecto.

**No** copia desde `.cortex/subagents/` — copia desde el bundle paralelo. **Esto es la deuda crítica que cubre el ítem #5 del roadmap 0.5.x.**

## Cambios específicos a Pi

### Cambio 1 — Pi sync mechanism (el más importante)

**Sin esto, los 8 cambios canonical no llegan a Pi.**

El ítem #5 del roadmap 0.5.x (ver `docs/roadmap/post-adopters.md`) describe agregar `PiAdapter.sync_canonical_subagents(project_root)` que copia los 3 subagents compartidos desde `.cortex/subagents/` → `cortex-pi/.pi/agents/`. Y un flag CLI `cortex inject --ide pi --sync-canonical`.

**Decisión:** este cambio se promueve **dentro del scope de Tripartita Refinada** porque sin él, los cambios canonical de Plan 01 NO llegan a Pi.

### Archivos a tocar

- `cortex/ide/adapters/pi.py`:
  - Agregar método `sync_canonical_subagents(project_root: Path) -> list[Path]`.
  - Modificar `inject_profiles` para que **antes de copiar `cortex-pi/`**, ejecute `sync_canonical_subagents` que regenera `cortex-pi/.pi/agents/{explorer,implementer,documenter}.md` desde `.cortex/subagents/`.
- `cortex/cli/main.py` — agregar flag `--sync-canonical` a `cortex inject` (default `True` para Pi, no relevante para otros IDEs).
- `tests/unit/test_ide_adapters.py` — test del sync.

### Plan

1. **Método `sync_canonical_subagents`** en `pi.py`:
   ```python
   _SHARED_AGENTS = (
       "cortex-code-explorer.md",
       "cortex-code-implementer.md",
       "cortex-documenter.md",
   )

   def sync_canonical_subagents(self, project_root: Path) -> list[Path]:
       """Mirror .cortex/subagents/ → cortex-pi/.pi/agents/ for the 3 shared agents.

       Run BEFORE inject_profiles copies cortex-pi/ to the project root, so
       the project receives the latest canonical content even if cortex-pi/
       was last edited weeks ago.

       Idempotent. Returns the paths overwritten in cortex-pi/.
       """
       from cortex.workspace.layout import WorkspaceLayout
       layout = WorkspaceLayout.discover(project_root)
       canonical_dir = layout.subagents_dir
       if not canonical_dir.is_dir():
           return []
       pkg_root = Path(__file__).resolve().parent.parent.parent.parent
       pi_bundle_agents = pkg_root / "cortex-pi" / ".pi" / "agents"
       pi_bundle_agents.mkdir(parents=True, exist_ok=True)

       overwritten: list[Path] = []
       for name in _SHARED_AGENTS:
           src = canonical_dir / name
           if not src.exists():
               continue
           dst = pi_bundle_agents / name
           dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
           overwritten.append(dst)
       return overwritten
   ```

2. **Modificar `inject_profiles`:**
   ```python
   def inject_profiles(self, project_root: Path, prompts: dict[str, str] | None = None) -> list[str]:
       # NEW: ensure the bundle has the latest canonical content first.
       self.sync_canonical_subagents(project_root)
       # ... resto del código existente que copia cortex-pi/ → project_root
   ```

3. **CLI flag** (opcional, default ya cubierto por `inject_profiles`):
   ```python
   # En cortex/cli/main.py::inject (top-level cortex inject)
   @app.command(name="inject")
   def inject(
       ide: str = ...,
       sync_canonical: bool = typer.Option(
           True,
           "--sync-canonical/--no-sync-canonical",
           help="(Pi only) Re-sync the 3 shared subagents from .cortex/subagents/. Default: enabled.",
       ),
   ) -> None:
       ...
       if ide == "pi" and not sync_canonical:
           # User explicitly opted out; skip the sync, do raw copy.
           ...
       else:
           # default path: sync before inject
           ...
   ```

4. **Tests:**
   ```python
   def test_pi_sync_canonical_overwrites_bundle(tmp_path):
       """Editing .cortex/subagents/cortex-documenter.md and calling
       sync_canonical_subagents must update cortex-pi/.pi/agents/."""
       canonical = tmp_path / ".cortex" / "subagents"
       canonical.mkdir(parents=True)
       (canonical / "cortex-documenter.md").write_text(
           "# NEW CONTENT — Tripartita Refinada\nVerification Gate enforced.",
           encoding="utf-8",
       )

       adapter = get_adapter("pi")
       overwritten = adapter.sync_canonical_subagents(tmp_path)

       assert len(overwritten) >= 1
       # Verify bundle now has the new content
       pkg_root = Path(__file__).resolve().parent.parent.parent.parent
       bundle_doc = pkg_root / "cortex-pi" / ".pi" / "agents" / "cortex-documenter.md"
       assert "NEW CONTENT — Tripartita Refinada" in bundle_doc.read_text(encoding="utf-8")
   ```

   ⚠ **Cuidado:** este test MODIFICA `cortex-pi/.pi/agents/` del repo Cortex en sí (porque escribe al bundle real). Hay que **mockear o restaurar** post-test. Sugerencia: usar `tmp_path` para el canonical pero mockear `pkg_root` con monkeypatch.

### Cambio 2 — Agents Pi-only (sync, SDDwork, security-auditor, test-verifier) heredan los cambios de Plan 01

Los 4 agents Pi-only **no** existen en `.cortex/subagents/`. Hay que editarlos directamente en `cortex-pi/.pi/agents/`. Sus cambios para Tripartita Refinada:

- **`cortex-sync.md`**: agregar Pre-flight CONTEXT.md + Anti-rationalization sync + Contrato de Salida.
- **`cortex-SDDwork.md`**: Anti-rationalization SDDwork + Contrato de Salida + reglas para validar handoffs entre subagents (invocar `cortex_validate_handoff`).
- **`cortex-security-auditor.md`**: Contrato de Salida específico (verified_claims sobre vulnerabilidades).
- **`cortex-test-verifier.md`**: Contrato de Salida específico (verified_claims sobre cobertura + tests passing).

### Archivos a tocar

- `cortex-pi/.pi/agents/cortex-sync.md`
- `cortex-pi/.pi/agents/cortex-SDDwork.md`
- `cortex-pi/.pi/agents/cortex-security-auditor.md`
- `cortex-pi/.pi/agents/cortex-test-verifier.md`

### Plan

Para cada uno, agregar al final:

```markdown
## Contrato de Salida (Output Obligatorio)

Al finalizar tu trabajo, tu último mensaje debe ser un bloque YAML conforme
al schema `cortex.handoff.AgentHandoff`. Validá con `cortex_validate_handoff`
antes de pasar el handoff al siguiente agente del agent-chain.

\`\`\`yaml
agent: cortex-<este-agente>  # explorer, implementer, documenter, etc.
status: complete | partial | blocked
verified_claims:
  - "..."
unverified_claims:
  - "..."
artifacts_produced:
  - path: <ruta>
    action: created | modified | deleted | renamed
context_for_next:
  - "..."
suggested_adr: false
\`\`\`

## Anti-Rationalization Signals (específico a este rol)

| Pensamiento | Realidad | Acción |
|-------------|----------|--------|
| ... (específico al rol) | ... | ... |
```

Para `cortex-SDDwork` específicamente, agregar:

```markdown
## Validación de handoffs (orquestador)

Cuando un subagent (explorer, implementer, documenter, security-auditor,
test-verifier) entrega su YAML handoff, invocá `cortex_validate_handoff`
con `expected_agent=<nombre>` antes de pasarlo al siguiente del chain.

Si la validación falla:
- Status `blocked`: detén el chain, reporta al usuario.
- Status `partial`: continuá pero marcá explícitamente en el handoff
  del próximo agent que el anterior quedó incompleto.
```

### Cambio 3 — `agent-chain.yaml` validation hooks

El archivo `cortex-pi/.pi/agents/agent-chain.yaml` define las cadenas (sddwork, hotfix, refactor). Hay que asegurar que entre cada paso del chain Pi invoca `cortex_validate_handoff` con el `expected_agent` del paso siguiente.

### Archivos a tocar

- `cortex-pi/.pi/agents/agent-chain.yaml` — agregar `validation:` key por step si Pi lo soporta. Si no lo soporta, documentar en el SDDwork.md que el orquestador debe invocarlo manualmente.

### Plan

Leer la estructura actual de `agent-chain.yaml`. Si tiene formato:

```yaml
sddwork:
  - cortex-sync
  - cortex-SDDwork
  - cortex-code-explorer
  - cortex-code-implementer
  - cortex-security-auditor
  - cortex-test-verifier
  - cortex-documenter
```

Cambiar a:

```yaml
sddwork:
  steps:
    - name: cortex-sync
      validate_handoff: false  # primer paso no recibe handoff
    - name: cortex-SDDwork
      validate_handoff: true
      expected_input_agent: cortex-sync
    - name: cortex-code-explorer
      validate_handoff: true
      expected_input_agent: cortex-SDDwork
    # ... etc
```

Si Pi no soporta la key `validate_handoff`, dejar el formato actual + documentar en SDDwork que el chain runtime hace la validación.

### Cambio 4 — `damage-control-rules.yaml` actualizado

`.pi/damage-control-rules.yaml` (Pi-specific) tiene reglas de seguridad. Si en Tripartita Refinada introducimos validación de handoffs, agregar regla:

```yaml
rules:
  - id: handoff-malformed
    severity: block
    description: |
      If a subagent's handoff YAML fails cortex_validate_handoff,
      the chain MUST stop. Do not pass corrupted handoffs downstream.
```

### Cambio 5 — Skills CONTEXT.md aware

El skill `cortex-pi/.pi/skills/cortex-vault.md` (que interactúa con vault) debe mencionar CONTEXT.md como referencia. Agregar sección "CONTEXT.md awareness" igual que en `cortex-sync.md`.

### Archivos a tocar

- `cortex-pi/.pi/skills/cortex-vault.md`

## Smoke por IDE

### Test manual

1. Crear repo limpio `/tmp/pi-smoke`.
2. `cortex setup full --non-interactive --git-depth 1 --ide pi`.
3. Verificar `.pi/agents/`:

| Archivo | Marcador esperado |
|---------|-------------------|
| `.pi/agents/cortex-sync.md` | "Pre-flight: cargar CONTEXT.md", "Anti-rationalization", "Contrato de Salida" |
| `.pi/agents/cortex-SDDwork.md` | "Anti-rationalization", "Contrato de Salida", "Validación de handoffs" |
| `.pi/agents/cortex-code-explorer.md` | "Anti-rationalization", "Contrato de Salida" |
| `.pi/agents/cortex-code-implementer.md` | "Anti-rationalization", "Contrato de Salida" |
| `.pi/agents/cortex-documenter.md` | "HIGH-SIGNAL", "VERIFICATION GATE", "Modo Handoff", "3 criterios", "Contrato de Salida" |
| `.pi/agents/cortex-security-auditor.md` | "Contrato de Salida" |
| `.pi/agents/cortex-test-verifier.md` | "Contrato de Salida" |
| `.pi/mcp.json` | cortex MCP server con env `CORTEX_CONFIG_PATH` |
| `.pi/damage-control-rules.yaml` | "handoff-malformed" rule |

## Checklist Plan 05 (Pi)

- [x] `PiAdapter.sync_canonical_subagents` implementado.
- [x] `inject_profiles` llama `sync_canonical_subagents` antes de copiar el bundle (default `sync_canonical=True`).
- [x] Flag CLI `--sync-canonical / --no-sync-canonical` agregado (default True para Pi, ignorado por otros adapters).
- [x] 5 tests `TestPiSyncCanonicalSubagents` verdes (overwrite, no-canonical, partial, default invokes sync, opt-out skips sync) + 1 test CLI del flag — todos con bundle fake / monkeypatch del default path para no tocar el bundle real del repo.
- [x] `cortex-pi/.pi/agents/cortex-sync.md` actualizado (Pre-flight CONTEXT.md, Anti-rationalization, Contrato YAML).
- [x] `cortex-pi/.pi/agents/cortex-SDDwork.md` actualizado (Anti-rationalization, Contrato YAML, Validación de handoffs).
- [x] `cortex-pi/.pi/agents/cortex-security-auditor.md` actualizado (Anti-rationalization, Contrato YAML).
- [x] `cortex-pi/.pi/agents/cortex-test-verifier.md` actualizado (Anti-rationalization, Contrato YAML).
- [x] `agent-chain.yaml` con `validate_handoff` + `expected_input_agent` keys por step en los 3 chains (sddwork, hotfix, refactor).
- [x] `damage-control-rules.yaml` con sección `handoffRules` (3 reglas: malformed, status-mismatch, context-overflow).
- [x] `.pi/skills/cortex-vault/SKILL.md` con sección CONTEXT.md awareness + confidence labels.
- [x] `docs/guides/ide-pi.md` actualizado con sección "Tripartita Refinada (0.5.0)" describiendo los 5 cambios.
- [ ] Smoke manual completo: marcadores presentes en los 9 archivos. **(Pendiente del usuario — `cortex inject --ide pi` en repo limpio.)**

**Plan 05 cerrado al 100% de items automatizables. Smoke manual queda como verificación opcional del usuario antes del release de 0.5.0.**
