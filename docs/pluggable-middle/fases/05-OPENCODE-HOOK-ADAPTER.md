# Fase 05 — Opencode IDE hook adapter

> **Estado:** ⏸ Pendiente · **Bloqueada por:** Fase 03 (la infraestructura `cortex.session.hooks` debe existir) · **Bloquea:** Nada · **Esfuerzo estimado:** ~1 semana

---

## 0. Metadatos

| Campo | Valor |
|---|---|
| Fase número | 05 |
| Nombre | Opencode IDE hook adapter |
| Versión del plan | 1.0 |
| Dependencias | Fase 03 cerrada (`cortex.session.hooks` con `HookAdapter`/`HookInstaller`/3 adapters). |
| Output principal | Cuarto adapter en `cortex/session/hooks/adapters/opencode.py` + bundled en `default_installer()`. |
| Breaking changes | Ninguno. Sólo agrega un IDE más; la API pública no cambia. |

---

## 1. Required Reading

### 1.1 Contexto del plan

- [`fases/README.md`](README.md) — Quality Charter.
- [`../ARQUITECTURA-PLUGGABLE-MIDDLE.md`](../ARQUITECTURA-PLUGGABLE-MIDDLE.md) §4.3 (modo Observed) y §10.5 (Autopilot fusion).
- [`fases/03-AUTOPILOT-FUSION.md`](03-AUTOPILOT-FUSION.md) tasks T3.6 a T3.10 — para entender el contrato `HookAdapter`.

### 1.2 Código existente que vas a tocar o necesitas conocer

Leé enteros:

- `cortex/session/hooks/installer.py` — el Protocol `HookAdapter` y el orquestador `HookInstaller`. Vas a registrar el adapter nuevo en `default_installer()`.
- Los 3 adapters bundled — los 3 patrones de install/uninstall que tu adapter debe seguir:
  - `cortex/session/hooks/adapters/claude_code.py` — patrón JSON (modifica `.claude/settings.json`).
  - `cortex/session/hooks/adapters/cursor.py` — patrón shell script con sentinel markers (`.git/hooks/post-commit`).
  - `cortex/session/hooks/adapters/pi.py` — patrón texto con markers (`justfile`).
- `cortex/cli/session.py` — subapp `hooks` (CLI). Si el adapter requiere argumentos extra (probablemente no), aquí se exponen.
- `tests/unit/session/hooks/test_claude_code.py` y `test_cursor.py` — patrones de tests a reproducir.

Leé bajo demanda:

- El doctor (`cortex/doctor.py::_validate_session_hooks`) detecta installs automáticamente vía `default_installer().status_all(target)`. Una vez registrado el adapter nuevo, el doctor lo reporta sin cambios adicionales.

### 1.3 Documentación externa (consultar)

- **Opencode hooks documentation:** investigar formato actual de hooks vía `WebFetch` antes de codear. Buscar específicamente:
  - Dónde vive el archivo de hooks (`.opencode/hooks.md`? `.opencode/hooks.json`? `~/.opencode/`?).
  - Qué eventos están disponibles (post-tool-use, post-edit, post-commit, session-end?).
  - Sintaxis exacta del hook (markdown con front-matter? JSON nativo? YAML?).
  - Si el hook puede ejecutar un comando shell o requiere un proceso largo-running.

> **Importante:** opencode tiene un ciclo de release rápido. Lo que sea cierto en 2026-05 puede no serlo en 2026-07. Antes de implementar, verificá la versión de opencode más reciente disponible (`opencode --version` si está instalado, o el GitHub repo del proyecto).

- **Pluggable Middle architecture §4.3** — el modo Observed: el hook **emite checkpoints**, no consume bootstrap context. La direccionalidad es IDE → Cortex, no al revés.

---

## 2. Goal

Al finalizar esta fase:

1. **Existe `cortex/session/hooks/adapters/opencode.py`** implementando el Protocol `HookAdapter`:
   - `name = "opencode"`.
   - `is_supported()` detecta si opencode está disponible (binary en PATH o config dir presente).
   - `install(target_dir)` instala un hook que invoca `cortex session checkpoint --source ide-hook --note "..."`.
   - `uninstall(target_dir)` remueve el hook sin afectar contenido de usuario.
   - `status(target_dir)` reporta install/uninstall correctamente.
2. **El adapter está registrado en `cortex.session.hooks.installer.default_installer()`** — `cortex session hooks list` lo muestra; `cortex session hooks install --ide opencode` funciona.
3. **Tests unitarios** análogos a `test_claude_code.py`: install crea el archivo, preserva contenido existente, install idempotente, uninstall preciso (no afecta hooks de usuario), status correcto en cada estado.
4. **Doctor** reporta `opencode` en `_check_adapters` y `_check_hooks_installed` automáticamente (sin cambios al doctor).
5. **Documentación** actualizada:
   - `README.md` tabla de IDE hooks en §"Pluggable Middle".
   - `docs/architecture/session-primitive.md` §8 tabla de adapters.
   - `docs/pluggable-middle/MIGRATION-FROM-TRIPARTITO.md` tabla de FAQ (opencode pasa de ⏳ Roadmap a ✓ Nativo).

**Lo que NO se hace en esta fase:**

- ❌ NO se reescribe el contrato `HookAdapter` (Fase 03 lo cementó).
- ❌ NO se agregan eventos diferentes a "post-tool-use / file-modify" salvo que opencode los exponga naturalmente y el costo sea trivial.
- ❌ NO se adiciona soporte a otros IDEs (JetBrains, Codespaces, etc.) — esos son fases separadas.

---

## 3. Decisiones de diseño clave

### 3.1 ¿Qué evento de opencode dispara el checkpoint?

**Decisión inicial:** el evento post-edición de archivo (equivalente a `PostToolUse` en Claude Code). Si opencode también expone `post-commit` o `session-end`, evaluar si vale la pena emitir checkpoints adicionales en esos puntos.

**Regla:** un checkpoint por unidad de trabajo significativa, no por cada operación atómica. Igual que los otros adapters.

### 3.2 ¿Project-scoped o user-scoped?

**Decisión:** project-scoped (target_dir = repo root). Consistente con los otros 3 adapters. Si opencode requiere config user-scoped (`~/.opencode/`), documentar pero igual instalar project-scoped por default — el adapter podría aceptar un parámetro `--scope user|project` en una iteración futura, pero T5 no lo agrega.

### 3.3 ¿`is_supported()` chequea binary o config dir?

**Decisión:** `is_supported()` retorna `True` siempre, igual que los otros 3 adapters. El motivo: el adapter sólo manipula archivos de configuración; el binary de opencode es problema del usuario en invocación. Si en testing el binary no está, los tests de install/uninstall/status corren con tmp_path y no necesitan el binary.

Excepción: si la instalación física del hook **requiere** una invocación a `opencode ...` (e.g. para registrar el hook en su DB interna), entonces sí, `is_supported()` chequea `shutil.which("opencode") is not None`.

### 3.4 ¿Cómo evita que un re-install duplique el bloque?

**Decisión:** sentinel markers idénticos al patrón de `cursor.py` / `pi.py` para formatos texto, o un marker JSON `_cortex_managed: true` para formato JSON (patrón claude_code.py). Elegir según el formato real que opencode use.

### 3.5 Naming del adapter

**Decisión:** `name = "opencode"` (todo lowercase, sin guiones). Consistente con `"cursor"`, `"pi"`. (`"claude-code"` tiene guión porque "claude-code" es el nombre canónico del producto.)

---

## 4. Task Breakdown

### T5.1 — Investigación previa del formato de opencode

**Objetivo:** documentar el formato exacto de hooks que opencode soporta hoy.

**Acción:**
1. `WebFetch` sobre la documentación oficial de opencode (o el README del repo).
2. Si opencode está instalado localmente: `opencode --help`, `opencode hooks --help`, inspeccionar `.opencode/` en un proyecto pequeño.
3. Capturar:
   - Path canónico del archivo de hooks (e.g. `.opencode/hooks.md`).
   - Formato del archivo (markdown? JSON?).
   - Eventos disponibles (post-edit, post-commit, etc.).
   - Sintaxis para declarar un command-line hook.
   - Si soporta marcas de identificación / metadata.

**Output:** crear `docs/pluggable-middle/fases/_internal/opencode-hooks-research.md` con los hallazgos (3 a 5 párrafos + 1 ejemplo de hook). Es un working note privado, igual que `autopilot-audit.md`.

**Definition of Done T5.1:** documento creado; el ejecutor de T5.2 puede leerlo y saber exactamente qué escribir.

---

### T5.2 — Implementar `cortex/session/hooks/adapters/opencode.py`

**Objetivo:** adapter funcional según el Protocol `HookAdapter`.

**Archivos a crear:**
- `cortex/session/hooks/adapters/opencode.py`

**Estructura esperada (esqueleto — adaptar al formato real de opencode):**

```python
"""cortex.session.hooks.adapters.opencode — Opencode IDE hook adapter.

Installs a Cortex-managed entry into opencode's hooks file (path and
format determined by T5.1 research note) so that every file-modification
event emits a checkpoint to the active Cortex session.
"""

from __future__ import annotations

from pathlib import Path
# ... json / shutil imports según formato

from cortex.session.hooks.installer import (
    HookStatus, InstallResult, UninstallResult,
)


CORTEX_MARKER = ...     # marker para identificar el bloque cortex-managed
OPENCODE_HOOKS_RELATIVE = Path(".opencode/hooks.md")   # ajustar según T5.1
HOOK_COMMAND = (
    "cortex session checkpoint --source ide-hook "
    "--note 'edit via opencode' >/dev/null 2>&1 || true"
)


class OpencodeHookAdapter:
    """Manage the Cortex hook entry inside opencode's config."""

    name = "opencode"

    def is_supported(self) -> bool:
        return True

    def install(self, target_dir: Path) -> InstallResult: ...
    def uninstall(self, target_dir: Path) -> UninstallResult: ...
    def status(self, target_dir: Path) -> HookStatus: ...

    # ── Internals ──────────────────────────────────────────────────
    @staticmethod
    def _hooks_path(target_dir: Path) -> Path:
        return Path(target_dir) / OPENCODE_HOOKS_RELATIVE
    # ... helpers según patrón claude_code / cursor / pi


__all__ = ["OpencodeHookAdapter", "CORTEX_MARKER", "HOOK_COMMAND"]
```

**Decisiones por reproducir desde los adapters existentes:**

- El hook command debe incluir `>/dev/null 2>&1 || true` (o equivalente) para no abortar opencode si Cortex falla.
- Install crea el archivo si no existe; si existe, agrega el bloque marker-delimited preservando contenido previo.
- Uninstall remueve sólo el bloque marker-delimited; si el archivo queda con sólo el shebang/header sin contenido, removerlo entero (igual que cursor.py).
- Status reporta `installed=True` si el marker está presente; `installed=False` en cualquier otro caso (incluyendo file missing o malformado).
- En install, marcar el archivo como ejecutable si es un shell script (igual que `cursor._ensure_executable`); skip en Windows.

**Tests obligatorios:** ver T5.3.

**Definition of Done T5.2:**

- Archivo creado con la clase y los 3 métodos.
- `mypy --strict --follow-imports=silent cortex/session/hooks/adapters/opencode.py` limpio.
- `ruff check cortex/session/hooks/adapters/opencode.py` limpio.

---

### T5.3 — Tests unitarios `tests/unit/session/hooks/test_opencode.py`

**Objetivo:** cobertura paralela a `test_claude_code.py` (formato JSON) o `test_cursor.py` (formato shell) según corresponda.

**Archivos a crear:**
- `tests/unit/session/hooks/test_opencode.py`

**Estructura mínima (10–12 tests):**

```python
class TestSupport:
    def test_is_supported_true(...): ...
    def test_name(...): ...

class TestInstall:
    def test_creates_hooks_file_when_absent(tmp_path): ...
    def test_appends_to_existing_user_hooks(tmp_path): ...
    def test_idempotent(tmp_path): ...    # 2x install → marker aparece 1 vez

class TestUninstall:
    def test_no_op_when_file_missing(tmp_path): ...
    def test_no_op_when_no_cortex_marker(tmp_path): ...
    def test_preserves_user_hooks(tmp_path): ...
    def test_removes_file_when_only_cortex_block(tmp_path): ...

class TestStatus:
    def test_file_missing(tmp_path): ...
    def test_present_after_install(tmp_path): ...
    def test_absent_after_uninstall(tmp_path): ...
    def test_malformed_input_reports_not_installed(tmp_path): ...
```

**Definition of Done T5.3:**

- 10+ tests, todos verdes con `pytest tests/unit/session/hooks/test_opencode.py --no-cov -q`.
- Sin warnings nuevos.

---

### T5.4 — Registrar el adapter en `default_installer()`

**Archivos a modificar:**
- `cortex/session/hooks/installer.py` — agregar `OpencodeHookAdapter` a la lista del `default_installer()`.

**Cambio mínimo:**

```python
def default_installer() -> HookInstaller:
    from cortex.session.hooks.adapters.claude_code import ClaudeCodeHookAdapter
    from cortex.session.hooks.adapters.cursor import CursorGitHookAdapter
    from cortex.session.hooks.adapters.opencode import OpencodeHookAdapter   # ← NEW
    from cortex.session.hooks.adapters.pi import PiHookAdapter

    return HookInstaller(
        [
            ClaudeCodeHookAdapter(),
            CursorGitHookAdapter(),
            OpencodeHookAdapter(),                                            # ← NEW
            PiHookAdapter(),
        ]
    )
```

**Verificación:**

- Actualizar `tests/unit/session/hooks/test_installer.py::TestDefaultInstaller::test_bundled_adapters_present` para incluir `"opencode"` en el set esperado.
- `cortex session hooks list --json` debe ahora mostrar 4 adapters.

**Definition of Done T5.4:** test `test_bundled_adapters_present` actualizado y verde.

---

### T5.5 — CLI `cortex session hooks install --ide opencode`

**Archivos a modificar:**
- `tests/unit/cli/test_session_hooks_cli.py` — agregar tests para `opencode`.

**Sin cambios necesarios al CLI propiamente dicho** — el subapp `hooks` ya enruta por nombre genérico vía `HookInstaller.install(ide, target)`. Solo confirmar que `opencode` está en la lista que el CLI presenta.

**Tests a agregar:**

```python
def test_install_opencode(runner, git_repo): ...
def test_status_opencode_after_install(runner, git_repo): ...
def test_uninstall_opencode_after_install(runner, git_repo): ...
```

**Definition of Done T5.5:** los 3 tests CLI pasan.

---

### T5.6 — (Opcional pero recomendado) E2E

**Archivos a crear o modificar:**
- `tests/e2e/test_observed_flow.py` — agregar un escenario que use opencode si el binary está disponible.

**Estructura:**

```python
@pytest.mark.skipif(not shutil.which("opencode"), reason="opencode binary not on PATH")
class TestObservedFlowOpencode:
    def test_install_then_simulated_edit_creates_checkpoint(observed_repo):
        """Install opencode adapter; simulate edit; expect IDE_HOOK checkpoint."""
        ...
```

> **Nota:** si la activación del hook por opencode requiere ejecutar un comando opencode real (no es un git-post-commit auto-disparado), este test puede ser muy difícil de automatizar. En ese caso, **omitir T5.6** y limitarse a unit tests. El E2E para opencode puede hacerse manualmente al cierre.

**Definition of Done T5.6:**

- Si es viable: escenario E2E verde (o skipped donde corresponda).
- Si no es viable: documentar en el Progress Log que el E2E es manual.

---

### T5.7 — Actualizar documentación

**Archivos a modificar:**

1. `README.md` — tabla de IDE hooks en §"Pluggable Middle" (sección "IDE hooks para el modo Observed"). Cambiar la fila `opencode` de `⏳ Roadmap` a `✓ Nativo`.

2. `docs/architecture/session-primitive.md` §8 — agregar `opencode` a la tabla de adapters bundled.

3. `docs/pluggable-middle/MIGRATION-FROM-TRIPARTITO.md` §8 FAQ (si hay referencia a opencode).

4. `docs/pluggable-middle/README.md` — marcar Fase 05 como ✅ con el Output.

**Definition of Done T5.7:** docs actualizadas, `grep -r "opencode" docs/` confirma que no hay referencias a "Roadmap" o "no soportado" obsoletas.

---

## 5. Cross-cutting concerns

### 5.1 Reglas anti-error preservadas

- Hooks NUNCA deben abortar la operación del IDE — `|| true` o try/except defensivo siempre.
- Install idempotente (re-run = no-op si ya está instalado).
- Uninstall quirúrgico (preserva contenido de usuario).
- Sentinel markers únicos (`# >>> cortex-session-hook >>>` o `_cortex_managed: true` JSON) para identificación.

### 5.2 Plataforma

- chmod sólo en Unix; en Windows skip con try/except `OSError` (igual que `cursor._ensure_executable`).
- Path separators: usar `Path` y `as_posix()` cuando necesario. Tests verifican con `replace("\\", "/")`.

### 5.3 Performance

- El hook command debe ejecutar en <100ms. `cortex session checkpoint` con CWD=repo es rápido (no abre AgentMemory).

### 5.4 Seguridad

- El comando instalado NO debe contener tokens ni paths privados — sólo `cortex session checkpoint ...`.

---

## 6. Completion Verification Commands

```bash
cd C:\Cortex

# 1. Tests del adapter nuevo
pytest tests/unit/session/hooks/test_opencode.py --no-cov -v
# expected: all green

# 2. Test del installer registry (debe incluir opencode)
pytest tests/unit/session/hooks/test_installer.py --no-cov -v
# expected: TestDefaultInstaller::test_bundled_adapters_present incluye 'opencode'

# 3. CLI funcional
cortex session hooks list
# expected: opencode aparece en la tabla con estado "—" (not installed)

# 4. mypy + ruff
mypy --strict --follow-imports=silent cortex/session/hooks/adapters/opencode.py
ruff check cortex/session/hooks/adapters/opencode.py tests/unit/session/hooks/test_opencode.py
# expected: clean

# 5. Suite completa sin regresiones
pytest tests/unit/ tests/integration/ tests/e2e/test_byo_flow.py tests/e2e/test_managed_flow.py tests/e2e/test_observed_flow.py tests/e2e/test_interactive_flow.py --no-cov --tb=no
# expected: 0 failed (el baseline pre-Fase 05 es 1743 passed; debería quedar en 1753+ passed)
```

---

## 7. Handoff to next phase

Al cerrar Fase 05:

### Artefactos producidos

| Artefacto | Path |
|---|---|
| Opencode adapter | `cortex/session/hooks/adapters/opencode.py` |
| Tests | `tests/unit/session/hooks/test_opencode.py` |
| Installer registry update | `cortex/session/hooks/installer.py::default_installer` |
| CLI test update | `tests/unit/cli/test_session_hooks_cli.py` |
| Docs actualizados | `README.md`, `docs/architecture/session-primitive.md` §8 |

### Lo que el resto del ecosistema puede asumir

- Cualquier flujo Observed que dependa de opencode ahora funciona automáticamente vía `cortex session hooks install --ide opencode`.
- `cortex doctor` reporta el estado de opencode sin cambios al doctor.

---

## 8. Progress Log

- [x] T5.1 — Investigación previa del formato de opencode (2026-05-17) — research note: [`_internal/opencode-hooks-research.md`](_internal/opencode-hooks-research.md).
- [x] T5.2 — Implementar `cortex/session/hooks/adapters/opencode.py` (2026-05-17) — patrón markdown-block estilo `cursor.py` con sentinel markers HTML-comment.
- [x] T5.3 — Tests unitarios `test_opencode.py` (2026-05-17) — 14 escenarios (install/uninstall/status/idempotencia/preservación de contenido de usuario).
- [x] T5.4 — Registrar adapter en `default_installer()` (2026-05-17) — `cortex session hooks list` ahora muestra los 4 bundled.
- [x] T5.5 — Tests CLI (3 escenarios opencode) (2026-05-17) — install/status/uninstall via CliRunner.
- [ ] T5.6 — (Opcional) E2E — saltado: opencode no instalado en el CI, los unit tests + CLI tests cubren el flujo completo.
- [x] T5.7 — Documentación (2026-05-17) — README + session-primitive.md §8 + CHANGELOG + Pluggable Middle README.
- [x] Completion Verification Commands pasan (2026-05-17)
- [x] Tabla `../README.md` actualizada ✅ (2026-05-17)
- [ ] Commit final (pendiente — esperando autorización del usuario al cierre de todas las fases)

---

## 9. Notas para el agente ejecutor

- **Investigá primero (T5.1).** Sin saber el formato real de hooks de opencode, el resto es adivinanza. Usá `WebFetch` o el binary local. Si el formato cambió desde la versión documentada, el plan original puede no aplicar — adapta el adapter sin desviarte del Protocol.
- **Copiá el patrón más cercano.** Si opencode usa JSON, copiar `claude_code.py`. Si usa shell, copiar `cursor.py`. Si usa texto-con-recipes (just), copiar `pi.py`. NO inventes un patrón nuevo.
- **El E2E es opcional.** Si automatizar la disparación del hook por opencode es complejo (requiere subprocess del binary + setup de un proyecto), saltátelo y documentá en el Progress Log que el E2E se hace manual al cierre.
- **No expandas el alcance.** Esta fase NO toca JetBrains, Codespaces, VSCode-nativo, etc. — son fases separadas.
