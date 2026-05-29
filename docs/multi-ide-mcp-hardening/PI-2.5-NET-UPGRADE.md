# Pi 2.5+net — Upgrade del bundle (mayo 2026)

Reemplazo del bundle `cortex-pi/` por la versión **2.5+net** entregada
en `cortex-pi-2.5-net (1).zip`, más los cambios mínimos en Cortex para
que la nueva extensión `cortex-net.ts` opere out-of-the-box.

> Este doc es complementario a `cortex-pi/CHANGES.md` (changelog del
> propio bundle, lo trajo el zip) y a `cortex-pi/ADAPTER_CONTRACT.md`
> (lo que el bundle espera del adapter Python). Cuando todo esté en
> producción, esos dos `.md` se eliminan del bundle — son docs hacia
> Cortex, no para el adopter.

---

## 1. Qué cambió en el bundle

Reemplazo verbatim del directorio `cortex-pi/`. Diff respecto a 2.5
(pre-net):

| Categoría | Cantidad | Detalle |
|---|---:|---|
| Idénticos byte-a-byte | 3 | skills `cortex-python`, `cortex-testing`, `obsidian-index` |
| Modificados | 32 | la mayoría de agents, extensions, `settings.json`, `system.md`, `justfile`, `AGENTS.md`, `README.md` |
| Nuevos | 3 + 1 dir | `cortex-net.ts` (50KB), `ADAPTER_CONTRACT.md`, `CHANGES.md`, `.pi/agents/cortex-net/` (dir vacío) |
| Eliminados | 1 | `.pi/extensions/justfile` (sus recetas están en el `justfile` de raíz, ahora consolidado con nuevas recetas `cortex-net`) |

Cambios semánticos clave (ver `cortex-pi/CHANGES.md` para detalle):

- **`cortex-net.ts`** — extensión nueva que implementa un protocolo
  peer-to-peer entre los agents del medio + el documenter. 5 tools:
  `cortex_net_list`, `cortex_net_send`, `cortex_net_get`,
  `cortex_net_await`, `cortex_net_transcript`.
- **`cortex-security-auditor` / `cortex-test-verifier`** — migraron de
  YAML AgentHandoff a `cortex_session_checkpoint` (mismo contrato que
  cortex-SDDwork desde Phase 02).
- **`agent-chain.yaml`** — marcado como FALLBACK puro para IDEs sin
  cortex-net. Se eliminaron las claves `validate_handoff` y
  `expected_input_agent` (el contrato real son los checkpoints).
- **`cortex-documenter`** — dos modos: observer in-flight (escucha la
  red durante toda la sesión) + closing anchor (cierre con criterio
  editorial, sin cambios).
- **`cortex-code-{designer,explorer,implementer}`** — frontmatter
  agrega `cortex_net_*` tools + sección "Uso de cortex-net".

Cinco archivos que `CHANGES.md` declaró como INTACTAS pero cuyo hash
cambió (`cortex-tools.ts`, `cortex-mcp.ts`, `system-select.ts`,
`damage-control.ts`, `damage-control-rules.yaml`) se asumieron como
**solo normalización de EOL/whitespace**. Si en algún momento aparece
un bug de runtime en alguno de ellos, conviene comparar contra la
versión pre-net guardada en git.

## 2. Cambios en el código de Cortex

El `ADAPTER_CONTRACT.md` del bundle deja claro que el adapter Python
**casi no necesita tocarse** — `cortex-net.ts` resuelve el session_id y
el rol dinámicamente desde el filesystem y los hooks de Pi. Lo único
que cortex-net espera por contrato es leer
`<workspace>/.cortex/session.lock` con el `session_id` activo en texto
plano. Cambios aplicados:

### 2.1 `cortex/session/service.py` — escritura del lock

- Método nuevo `SessionService._write_session_lock(session_id | None)`:
  - `str` → escribe `<repo_root>/.cortex/session.lock` con el id +
    newline LF (`write_bytes` para evitar la traducción CRLF de
    Windows; `cortex-net.ts` hace `.trim()` igualmente).
  - `None` → borra el archivo si existe.
  - Best-effort: si `OSError` (p.ej. `.cortex/` no se puede crear), se
    loggea en debug y se sigue. El lock es presentación, NO SSoT.
- Llamadas:
  - `open()` — tras `set_active_session_id`, escribe el lock con el id
    de la session recién abierta (incluyendo el path de idempotencia
    que retorna una sesión existente).
  - `set_active()` — actualiza el lock con la nueva activa.
  - `close()` — si la cerrada era la activa, limpia el lock junto al
    pointer del storage.

### 2.2 `cortex/documenter/reconstruction.py` — filtro defensivo

El documenter recorre el git diff de la sesión y cualquier archivo
suelto en `.cortex/` aparecería como `out_of_scope_file`. Para evitar
fugas del lock al output:

- Constante module-level `_CORTEX_INTERNAL_PATHS = {".cortex/session.lock"}`
  y helper `_is_cortex_internal_path(path)`.
- Aplicado a `files_verified_by_git`, `files_declared_only` y
  `files_touched` **antes** del scope cross-check, así
  `in_scope/out_of_scope/unimplemented` y los outputs del documenter
  quedan consistentes en ambos branches (git-aware y gitless).

### 2.3 `cortex/git_policy.py` — `.gitignore` por default

Agregada la entrada `.cortex/session.lock` a
`NEW_LAYOUT_GITIGNORE_PATTERNS` **y** `LEGACY_GITIGNORE_PATTERNS`
(en legacy `.cortex/` también existe para skills/subagents). El
filtro del documenter es defensivo igual; el gitignore evita que el
lock contamine `git status`.

## 3. Tests añadidos / actualizados

- **`tests/unit/session/test_service.py::TestSessionLockFile`** (5 tests):
  open escribe, close borra, set_active actualiza, formato `<id>\n`
  literal cross-platform, comportamiento best-effort si `.cortex/` no
  se puede crear.
- **`tests/unit/test_ide_adapters.py::TestPiBundleHasTripartitaRefinada`** —
  actualizada al nuevo contrato del bundle 2.5+net:
  - Solo `cortex-sync` retiene `Contrato de Salida` + YAML AgentHandoff.
  - `cortex-security-auditor` y `cortex-test-verifier` deben emitir
    `cortex_session_checkpoint` y declarar la prohibición explícita de
    YAML AgentHandoff.
  - `agent-chain.yaml` debe estar marcado FALLBACK y NO contener
    `validate_handoff` ni `expected_input_agent`.
  - `cortex-net.ts` debe existir en el bundle y referenciar
    `session.lock` + `CORTEX_SESSION_ID`.

## 4. Decisiones diferidas (no en este patch)

Listadas para retomar más adelante. Ninguna bloquea el funcionamiento
de la nueva versión.

- **Filtrar `ADAPTER_CONTRACT.md` y `CHANGES.md` del copy del adapter**:
  hoy el adapter copia todo el bundle al proyecto del adopter, por lo
  que esos dos docs aterrizan en la raíz del adopter. El plan es
  eliminarlos del bundle una vez confirmado el upgrade en producción
  (decisión del owner). Mientras tanto, son inofensivos.
- **`.pi/agents/cortex-net/` (dir vacío)** — viaja al proyecto del
  adopter. Probable placeholder; se mantiene hasta primera prueba.
- **`.pi/.bundle-version`** (recomendado por `ADAPTER_CONTRACT` §3.2) —
  marker de versión para detectar drift. No implementado: el adapter
  no escribe contenido más allá del bundle, y el bundle no lo trae
  embebido. Se puede agregar como archivo estático en el bundle o
  como escritura del adapter cuando haga falta diagnóstico.
- **`cortex-code-designer.md` ya estaba en `_SHARED_SUBAGENTS`** (Phase
  09.B) y se renderiza desde `cortex_workspace.py`. El contract lo
  pedía como "opcional"; en este repo ya está hecho.

## 5. Deuda preexistente que no toca este patch

Detectada al correr la suite completa; **no se introdujo en este
upgrade**, viene de antes y se confirma con un baseline limpio:

- `tests/unit/session/test_service.py::TestOpen::test_open_duplicate_id_appends_counter` —
  espera el comportamiento pre-idempotencia de `SessionService.open()`
  (incident 2026-05-22). El test no se actualizó cuando se introdujo
  el guardrail anti-ghost-sessions.
- `tests/unit/mcp/test_ping.py::test_ping_returns_valid_json` —
  baseline rojo (motivo no investigado aquí).
- `tests/unit/ide/test_adapters_phase4.py::test_canonical_skill_files_in_disk_match_renders` —
  baseline rojo, compara sha en disco vs `render_*()`.

## 6. TODOs heredados del `CHANGES.md` del bundle

Listados en `cortex-pi/CHANGES.md` § "TODOs para vos antes de release".
Algunos quedaron cubiertos por este patch:

- [x] **`CORTEX_SESSION_ID` resoluble por Pi sin wrapper** — cubierto
      vía `.cortex/session.lock`; ya no hace falta wrapper de CLI.
- [ ] Smoke tests dedicados en `tests/test_adapter_pi.py` con los 5
      checks del contract (los que importan ya viven en
      `tests/unit/test_ide_adapters.py::TestPiBundleHasTripartitaRefinada`).
- [ ] Decidir backward-compat del contract entre 1.5 y 2.0.
- [ ] Actualizar el README principal de Cortex mencionando que el
      setup con Pi instala 2.5+net.
- [ ] `.base` view en el Vault con telemetría de inbounds observados
      por el documenter.
