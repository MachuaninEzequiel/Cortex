# Obra 02 — Estándar único de CLIs/IDEs

> Estado: PLANIFICACIÓN · Origen: deep-review 2026-08 (docs/reviews/2026-08-deep-review/10-enterprise-ide-mcp.md, 2-cli.md)
> Alcance: `cortex/ide/**`, `cortex/session/hooks/**`, comandos IDE/MCP de `cortex/cli/main.py` y `cortex/cli/session.py`.
> Regla: toda tarea ejecutable lleva checkbox; se marca `[x]` recién verificada con comando + salida.

## Requisitos duros del dueño

- HOY cada CLI tenía su forma. TODAS deben usar el mismo estándar: mismos comandos, misma instalación, sin importar cuál sea.
- Uninstall NUNCA destructivo: solo borra lo que Cortex creó (marcado o inventariado).
- Inyección sobre archivos del usuario SIEMPRE con marcadores BEGIN/END (patrón codex).
- `project_root` explícito en toda operación; nada depende de `Path.cwd()`.

## Criterio de entrada (gate)

- [ ] TRAMO 0 cerrado (suite verde, deps pinned) según Obra 01 / ESTADO-ACTUAL.md.
- [ ] Bugs #3 (pi uninstall), #6 (cwd), #8 (CLAUDE.md pisado) del top-10 reproducidos en tests de caracterización ANTES de tocarlos.

## Sección 1 — Matriz actual (estado 2026-08)

### 1.1 Dos subsistemas que se superponen

Hoy existen DOS capas de instalación por IDE con contratos distintos:

| Capa | Módulo | Contrato | Comandos hoy |
|---|---|---|---|
| Perfiles + MCP | `cortex/ide/` | ABC `IDEAdapter` (base.py): `name`, `display_name`, `get_config_paths()`, `inject_profiles(project_root, prompts)`, `inject_mcp(project_root)`, `detect_installation()`, `validate()`, `uninstall()` (sin args), `needs_wsl_shielding()` | `cortex inject --ide X`, `cortex install-ide --ide X` (deprecated alias), `cortex uninstall-ide --ide X`, `cortex sync-ide --ide X` |
| Hooks de sesión (Observed mode) | `cortex/session/hooks/` | Protocol `HookAdapter`: `name`, `is_supported()`, `install(target_dir)` → `InstallResult`, `uninstall(target_dir)` → `UninstallResult`, `status(target_dir)` → `HookStatus` | `cortex session hooks list/install/uninstall/status --ide X` |

La capa hooks YA tiene las semánticas correctas (target_dir explícito, resultados tipados, status, idempotencia documentada). La capa ide NO. El estándar nuevo generaliza el contrato de hooks a toda la capa ide.

### 1.2 Matriz IDE × mecanismo (capa `cortex/ide/`)

Mecanismo de perfiles: `markdown-con-marcadores` = patrón codex; `write_text-completo` = pisa el archivo; `copia-bundle` = árbol propio.

| IDE | Tier | Perfiles (mecanismo / destino) | MCP (destino) | Uninstall | Riesgo del review #10 |
|---|---|---|---|---|---|
| claude_code | target/validado | write_text COMPLETO sobre `CLAUDE.md`; skills en `.claude/skills/`; agents en `.claude/agents/` con traducción de tools (canonical_tools.py) | `.mcp.json` proyecto (`--project-root` absoluto) | default no-op del ABC (no implementado) | **#8**: pisa CLAUDE.md entero (backup sí, pero contenido del adopter desaparece del archivo activo). Sin uninstall real. |
| opencode | target/validado | JSON `opencode.json` con permission matrix (deep merge) | mismo archivo, deep merge | parcial | Mejor comportamiento JSON; sin marcadores (JSON no los necesita, pero falta inventario de claves escritas para remover solo las de Cortex). |
| pi | target/"validado" | COPIA verbatim del bundle `cortex-pi/` → `.pi/agents/` (sync_canonical neutralizado, bundle es SSoT propio) | dentro del bundle | **DESTRUCTIVO** | **#3 ✅**: `pi.uninstall()` borra `AGENTS.md`, `README.md`, `justfile`, `extensions/` completos sin marcadores ni backup (pi.py:243-256). Además `project_root=None` por defecto → no-op silencioso. Marcador legacy `_SHARED_AGENTS` mantenido solo por tests. |
| codex | target/validado | AGENTS.md CON MARCADORES `<!-- BEGIN/END CORTEX SECTION -->`; config.toml TOML con marcadores; trust por-path con marcadores en `~/.codex/config.toml` global | `.codex/config.toml` | correcto (por marcadores) | Patrón DE REFERENCIA. Bugs menores: `_global_has_foreign_trust` no desescapa comillas simples (#13); uninstall usa `Path.cwd()` (**#6 ✅**, codex.py:566). |
| cursor | community/validado | skills/subagents en `.cursor/` (write_text por archivo propio) | `~/.cursor/mcp.json` USER-level, deep merge | conservador pero **cwd-dependiente** | **#6 ✅**: uninstall usa `Path.cwd()` (cursor.py:290) vs inject que recibe project_root. `get_config_paths` contradictorio (comenta "project-level", devuelve `~/.cursor/*`) (#14). MCP en home ≠ perfiles en proyecto. |
| vscode | community/no validado | agents markdown en `.vscode/` y `.github/` (copilot) | `.vscode/mcp.json` con `${workspaceFolder}` | no implementado | **#15**: `${workspaceFolder}` rompe si VS Code abre subcarpeta (todos los demás fijan `--project-root` absoluto). |
| windsurf | community/no validado | write_text COMPLETO sobre `~/.codeium/windsurf/memories/CLAUDE.md` (global!) | `~/.codeium/windsurf/mcp_config.json` | no implementado | **#8**: mismo pisado de CLAUDE.md que claude_code, además a nivel global del usuario. |
| zed | experimental/no validado | settings JSON (deep merge) | `~/.zed/settings.json` | no implementado | boilerplate JSON repetido; sin uninstall. |
| antigravity | experimental/no validado | PISA `system_instructions` completo en `~/.gemini/settings.json` | idem | NO DEFINIDO | **#11**: reemplaza el campo entero, sin merge ni restauración; la clase ni siquiera define uninstall. |
| hermes | experimental/no validado | JSON merge best-effort | idem | no implementado | copia N del bloque JSON read-backup-merge-write. |
| claude_desktop | community/no validado | n/a (solo MCP) | `~/Library/Application Support/Claude/claude_desktop_config.json` (deep merge) | no implementado | copia N del mismo bloque; WSL shielding flag. |

### 1.3 Estado transversal (lo que NINGÚN adapter garantiza hoy)

- [x] VERIFICADO: `status()` no existe en la capa ide (solo `validate()` que chequea existencia de paths, y `detect_installation()` que mira dirs globales).
- [x] VERIFICADO: `uninstall()` del ABC no recibe argumentos; `ide/__init__.py:110` llama `adapter.uninstall()` sin project_root → cursor/codex caen a `Path.cwd()` (#6), pi defaultea None.
- [x] VERIFICADO: marcadores BEGIN/END existen SOLO en codex (AGENTS.md, TOML, trust). Nadie más los adoptó.
- [x] VERIFICADO: no hay tests de contrato: `tests/unit/ide/` tiene solo test_adapters_phase4 y test_canonical_tools; ningún test ejecuta inject+uninstall desde un cwd distinto al root (review #10 §6.4), ninguno verifica byte-equality ni remoción exacta de lo inyectado.
- [x] VERIFICADO: `--dry-run` fake en setup (review top-10 #4, cli/main.py:684) afecta también a la superficie IDE.
- [x] VERIFICADO: duplicación: ~5 copias del bloque JSON read-backup-merge-write (claude_desktop, windsurf, zed, antigravity, hermes) — review #10 §5.

### 1.4 Capa session/hooks (referencia positiva)

Adapters: claude_code, cursor (git post-commit), opencode, pi. Instalan artefactos chicos que llaman `cortex session checkpoint --source ide-hook`. Este contrato SÍ tiene: `target_dir` explícito, resultados tipados (`InstallResult/UninstallResult/HookStatus`), idempotencia documentada, `status`. Es la semántica a generalizar; NO se toca su comportamiento salvo renombres de comandos (Sección 3).

## Sección 2 — El contrato único (`IDEAdapterV2`)

### 2.1 Principios (no negociables)

1. **Un solo contrato** para perfiles, MCP y hooks de sesión. La capa `session/hooks` migra a este contrato; su Protocol actual queda como alias de compatibilidad durante la migración.
2. **Marcadores BEGIN/END obligatorios** para TODO archivo del usuario que Cortex toque y que admita comentarios/texto libre (markdown, TOML, YAML, shell). Formato canónico (tomado de codex.py:53-69):

   ```
   <!-- BEGIN CORTEX SECTION (auto-generated, do not edit) -->   ← markdown
   # BEGIN CORTEX MCP (auto-generated, do not edit)              ← TOML/YAML/shell
   ... contenido ...
   <!-- END CORTEX SECTION -->                                   / # END CORTEX MCP -->
   ```

   Reglas de los marcadores:
   - El par abre/cierra se identifica por regex con `re.escape`; el bloque completo se REEMPLAZA en re-inyección (idempotencia byte-equality).
   - Si el archivo existe sin marcadores, NUNCA se sobrescribe entero: se hace append del bloque al final con separador `

`, previa verificación de ausencia.
   - Uninstall = eliminar exactamente los bloques delimitados + limpiar separadores huérfanos. Si el archivo queda vacío o solo-contenido-de-Cortex Y Cortex lo creó desde cero, recién entonces se borra el archivo (ver 2.4).
   - Para JSON (sin comentarios): deep merge + **inventario de claves escritas** persistido (ver 2.5); uninstall remueve SOLO esas claves.
3. **`project_root` explícito en TODAS las firmas**: `inject/uninstall/status/install(project_root: Path)`. Prohibido `Path.cwd()` dentro de adapters. El CLI resuelve cwd→root una sola vez y valida que exista `config.yaml` (o falla con error claro).
4. **Uninstall solo borra lo de Cortex**: prohibido borrar archivos completos preexistentes (el bug pi #3). Regla: un path es "borrable" solo si (a) está bajo un directorio cuyo nombre crea Cortex (`.pi/agents/…`, `.claude/skills/cortex-*`), O (b) fue creado por Cortex y registrado en el manifest, O (c) está entre marcadores.
5. **Idempotencia total**: correr setup N veces produce el mismo resultado que una vez (byte-equality de archivos generados).
6. **Backup siempre antes de modificar** archivo existente (helper `_backup_file` ya existe, se mantiene).

### 2.2 Interfaz base obligatoria

```python
class IDEAdapterV2(ABC):
    name: str                      # id canónico, ej "codex"
    display_name: str
    tier: Literal["target", "community", "experimental"]
    validated: bool                # validado contra docs oficiales del IDE

    def capabilities(self) -> AdapterCapabilities:
        """Declaración estática de qué sabe hacer este IDE."""

    def detect(self) -> bool:
        """¿El IDE está instalado en esta máquina?"""

    def setup(self, project_root: Path, prompts: PromptBundle,
              dry_run: bool = False) -> SetupReport:
        """Instala/actualiza TODO (perfiles + MCP + trust). Idempotente.
        Reemplaza a inject_profiles+inject_mcp+inject_all."""

    def status(self, project_root: Path) -> StatusReport:
        """Estado real: qué instalado, versión del manifest, drift vs SSoT."""

    def remove(self, project_root: Path, dry_run: bool = False) -> RemoveReport:
        """Elimina EXACTAMENTE lo que Cortex creó. Reemplaza a uninstall()."""
```

- `SetupReport/StatusReport/RemoveReport`: dataclasses tipados (mismo espíritu que `InstallResult/UninstallResult/HookStatus` de hooks/installer.py), con lista de paths tocados, acción por path (`created|updated|unchanged|removed|skipped`) y mensaje.
- `dry_run=True` es OBLIGATORIO en la firma: reporta qué haría sin tocar nada. Corrige el bug top-10 #4 para toda la superficie IDE.
- `PromptBundle`: dataclass con los prompts canónicos leídos de `.cortex/{skills,subagents}/` vía WorkspaceLayout (prompts.py sigue siendo SSoT) + hash de contenido, para que `status()` pueda detectar drift.

### 2.3 Detección de capacidad (`AdapterCapabilities`)

Cada adapter declara qué mecanismo nativo soporta, y el orquestador decide:

```python
@dataclass(frozen=True)
class AdapterCapabilities:
    mcp_mode: Literal["native-json", "toml", "markdown-block", "unsupported"]
    profiles_mode: Literal["slash-skills", "agent-files", "json-config", "bundle-copy"]
    session_hooks: Literal["git-hook", "ide-event", "none"]   # hoy: git-hook (cursor), ide-event (claude_code/pi/opencode)
    scope: Literal["project", "user", "mixed"]
```

Degradación documentada y visible en `cortex ide status`:
- MCP nativo disponible → configurar nativo. No disponible → escribir instrucciones de arranque manual dentro de la sección marcada. Nunca silencio.
- Sin soporte de skills → degradar a single-file instructions con marcadores (patrón codex AGENTS.md).
- `capabilities()` alimenta la matriz de la Sección 4 y el output de `status`.

### 2.4 Garantías de uninstall (contrato duro)

1. Solo se eliminan: bloques entre marcadores Cortex; claves JSON inventariadas; archivos/dirs creados íntegramente por Cortex y listados en el manifest.
2. Archivo compartido (ej: AGENTS.md del adopter): nunca se elimina el archivo; solo se vacía la sección marcada. Si tras vaciar queda idéntico al estado pre-Cortex y el manifest dice "creado por Cortex", puede borrarse.
3. Todo `remove` corre primero en modo reporte interno y aplica; imprime cada path tocado.
4. Test obligatorio por adapter: setup → mutate archivos del usuario → remove → assert contenido-del-usuario intacto y cero rastros Cortex (Sección 5.3).

### 2.5 Manifest de instalación (nuevo)

`.cortex/ide-manifest.json` (por proyecto) registra por IDE: paths escritos, claves JSON añadidas, hash del contenido inyectado, timestamp, versión del formato. Es el complemento del inventario de marcadores para formatos sin comentarios y para saber qué crear Cortex. Lo escriben `setup` y lo consume `remove`/`status`. Vive DENTRO del proyecto (scope disjunto con otros docs).

## Sección 3 — Superficie CLI unificada

### 3.1 La superficie nueva

UNA familia de comandos para TODOS los IDEs (perfiles + MCP + hooks de sesión en un solo lugar):

```
cortex ide setup   [--ide <name>|--all] [--project-root R] [--dry-run] [--json] [--no-hooks]
cortex ide status  [--ide <name>]       [--project-root R] [--json]
cortex ide remove  [--ide <name>|--all] [--project-root R] [--dry-run] [--json] [--keep-hooks]
cortex ide list                                          [--json]
```

Semántica:
- `setup` = instalar/actualizar TODO para ese IDE: perfiles + MCP + trust (codex) + hook de sesión. Idempotente. Sin `--ide` → menú interactivo (como hoy `inject`). `--all` = solo tier target, con confirmación explícita (ya no "deprecated/experimental").
- `status` = por IDE: instalado/no, drift entre SSoT `.cortex/` y lo inyectado (compara hashes del manifest), capacidades y degradaciones activas.
- `remove` = uninstall seguro (contrato 2.4). Por defecto incluye hooks; `--keep-hooks` para dejar el modo Observed activo.
- `--ide` acepta nombres canónicos y alias existentes del registry (`claude`, `claude-code`, `code`, etc. — se mantiene `_ALIASES`).
- Salida: texto humano por defecto, `--json` uniforme (un solo sistema, no doble `--json/--format`; alineado con review #2 deuda 3).
- Exit codes: 0 ok, 1 error, 2 unknown-ide (con listado de tiers).

### 3.2 Mapeo viejo → nuevo

| Comando hoy | Problema (review #2 hallazgo 5) | Reemplazo |
|---|---|---|
| `cortex inject --ide X` | semántica ambigua ("inyectar qué?"), sin dry-run, sin status | `cortex ide setup --ide X` |
| `cortex inject` (sin --ide) | menú interactivo | `cortex ide setup` (mismo menú) |
| `cortex install-ide --ide X` / `--all` | alias deprecated con warning confuso; `--all` "experimental" | `cortex ide setup --ide X` / `--all` |
| `cortex uninstall-ide --ide X` / `--all` | sin project_root (#6), destructivo en pi (#3) | `cortex ide remove --ide X` |
| `cortex sync-ide --ide X --force` | duplica a inject (main.py:1991-2007 llama exactamente a inject); header autogen menciona este comando | ELIMINADO: `setup` ya es idempotente y re-sincroniza; el header pasa a decir `Regenerate: cortex ide setup --ide <name>` |
| `cortex session hooks install/uninstall/status/list --ide X` | segunda familia paralela con otra semántica de flags | `cortex ide setup/remove/status --ide X` (hooks incluidos). Los subcomandos quedan como wrappers ocultos durante deprecation |

### 3.3 Deprecation path

1. Fase A: agregar `cortex ide ...` junto a los viejos. Los viejos emiten: `Warning: 'cortex inject' is deprecated, use 'cortex ide setup --ide X'. Removal in vX.Y.` Funcionan idéntico (delegan al código nuevo).
2. Fase B: headers autogen y docs (`README`, onboarding, skills) actualizados a la superficie nueva.
3. Fase C (release siguiente a la adopción): los viejos pasan a hidden aliases que delegan con warning. No se borran hasta que el grep de docs/tests no muestre usuarios.
4. Tareas:

- [ ] Implementar subapp `cortex ide` (typer subapp, patrón `hooks_app` en cli/session.py:658).
- [ ] Convertir `inject/install-ide/sync-ide/uninstall-ide` en delegadores con warning.
- [ ] Actualizar header `_generate_autogen_header` (base.py) al nuevo comando.
- [ ] Actualizar docs de onboarding y skills canónicas que mencionan los comandos viejos.
- [ ] Test CLI: cada comando viejo produce el MISMO efecto observable que su reemplazo (test de paridad).

## Sección 4 — Matriz IDE objetivo (actual → estándar)

Cómo mapea cada adapter al contrato `IDEAdapterV2`. "Se elimina" = código/patrón que desaparece.

| IDE | capabilities() objetivo | Cambios concretos | Se elimina |
|---|---|---|---|
| claude_code | mcp: native-json · profiles: slash-skills · hooks: ide-event · scope: project | CLAUDE.md pasa a bloque marcado dentro del archivo existente (append si no hay marcadores); skills/agents quedan como archivos propios Cortex (borrables por nombre `cortex-*`); MCP `.mcp.json` con deep merge + manifest; se implementa `remove()` real | write_text completo de CLAUDE.md (#8); ABC uninstall no-op |
| opencode | mcp: native-json · profiles: json-config · hooks: ide-event · scope: project | Casi conforme ya: agregar manifest, status, dry_run, remove de claves inventariadas | nada estructural |
| pi | mcp: native-json (bundle) · profiles: bundle-copy · hooks: ide-event · scope: project | El bundle `cortex-pi/` sigue siendo SSoT propio (decisión firmada 2026-05-15), PERO `remove()` NUNCA toca AGENTS.md/README.md/justfile/extensions/: solo `.pi/` y entradas propias registradas en el bundle dir. Fix crítico #3 | el bloque destructivo pi.py:243-256 |
| codex | mcp: toml · profiles: markdown-block · hooks: git-hook→none (hoy sin hook) | Es la REFERENCIA: sus marcadores se generalizan a base.py como helpers estándar (`markdown_block`, `toml_block`). Fix menor: desescape single-quoted en trust check (#13); remove recibe project_root (#6) | marcadores privados duplicables → pasan a helpers compartidos |
| cursor | mcp: native-json (user) · profiles: slash-skills · hooks: git-hook · scope: mixed | remove recibe project_root (#6); documentar scope mixed en status; unificar get_config_paths con lo que realmente hace (#14) | Path.cwd() en uninstall |
| vscode | mcp: native-json · profiles: slash-skills · hooks: none · scope: project | `${workspaceFolder}` → `--project-root` absoluto como todos (#15) | delegación en variable del IDE |
| windsurf | mcp: native-json (user) · profiles: markdown-block (user) · hooks: none · scope: user | CLAUDE.md global pasa a bloque marcado (#8) | write_text completo global |
| zed | mcp: native-json (user) · profiles: json-config (user) · hooks: none · scope: user | migrar a helper compartido merge_json_config + manifest | boilerplate propio |
| antigravity | mcp: native-json (user) · profiles: json-config (user) · hooks: none · scope: user | `system_instructions` pasa a MERGE conservador (solo añadir claves Cortex) o a bloque separado; implementar remove que restaure (#11). Si el formato no permite coexistencia → adapter marca `mcp_mode: unsupported` y degrada explícito | reemplazo entero de system_instructions |
| hermes | mcp: native-json (user) · profiles: json-config (user) · hooks: none · scope: user | igual que zed | boilerplate propio |
| claude_desktop | mcp: native-json (user) · profiles: unsupported · hooks: none · scope: user | igual que zed; profiles_mode declarado unsupported | n/a |

Regla común: los ~5 bloques JSON read-backup-merge-write duplicados (review #10 §5) se extraen a UN helper de base.py: `merge_json_config(path, key, value)` / `remove_json_key(path, key)`, con backup y manifest integrados.

Mantenimiento de tiers: `TARGET_IDES`, `COMMUNITY_IDES`, `_EXPERIMENTAL_IDES`, `VALIDATED_IDES` (registry.py) se conservan; `tier` y `validated` pasan a ser atributos del adapter y registry queda solo con resolución de alias + descubrimiento.

### Tareas

- [ ] Extraer helpers de marcadores a base.py (`render_markdown_block`, `replace_markdown_block`, `strip_markdown_block`, equivalentes TOML/YAML/shell).
- [ ] Extraer `merge_json_config` / `remove_json_key`.
- [ ] Migrar claude_code y windsurf a bloques marcados.
- [ ] Reescribir pi.remove() no destructivo + test de preservación.
- [ ] Añadir project_root a todas las firmas remove/uninstall (#6).
- [ ] vscode: --project-root absoluto.
- [ ] antigravity: merge conservador + remove.
- [ ] Manifest `.cortex/ide-manifest.json`: escritura en setup, lectura en status/remove.

## Sección 5 — Plan de migración por fases + tests de contrato

### 5.1 Por qué hoy no hay tests de contrato

- `tests/unit/ide/` cubre solo adapters fase-4 y canonical_tools. No existe ningún test que ejecute setup→remove completo, ni desde un cwd distinto al project_root (review #10 §6.4), ni que verifique byte-equality de re-runs.
- La ABC no obliga a implementar uninstall/status → los tests no pueden exigir comportamiento uniforme porque el contrato no lo declara.
- El contenido inyectado incluye timestamp (`_generate_autogen_header`) → imposible comparar byte-equality sin congelar el reloj o sacarlo del hash.

### 5.2 Fases

**Fase 0 — Red de seguridad (sin cambiar comportamiento)**
- [ ] Tests de caracterización del estado ACTUAL: snapshot de archivos generados por cada adapter target en tmp dir; test inject+uninstall desde cwd ≠ root para codex/cursor/pi (deben fallar/reproducir bug #6/#3).
- [ ] Congelar timestamps: `_generate_autogen_header` acepta `now` inyectable (para byte-equality).

**Fase 1 — Helpers compartidos (base.py)**
- [ ] Marcadores BEGIN/END como helpers estándar + merge_json_config/remove_json_key + manifest writer/reader.
- [ ] Tests unitarios de helpers: idempotencia byte-equality, append-no-destructivo, remoción exacta.

**Fase 2 — Contrato V2 + migración de adapters**
- [ ] Definir `IDEAdapterV2` + dataclasses de reportes + capabilities.
- [ ] Migrar en orden: codex (trivial, ya cumple) → opencode → claude_code → pi (fix destructivo) → cursor (#6) → vscode/windsurf → zed/hermes/claude_desktop/antigravity.
- [ ] Cada adapter migra con su test de contrato verde antes de mergear el siguiente.
- [ ] `session/hooks` adopta las mismas dataclasses de reporte (o alias); sus comandos delegan a la superficie nueva.

**Fase 3 — Superficie CLI unificada + deprecation**
- [ ] Subapp `cortex ide` (Sección 3). Comandos viejos como delegadores con warning.
- [ ] Paridad CLI: mismo efecto observable viejo vs nuevo.
- [ ] Docs/skills actualizados.

**Fase 4 — Cierre**
- [ ] `--dry-run` real en toda la superficie IDE (y reportado al fix del top-10 #4).
- [ ] Gates de salida verificados (abajo).

### 5.3 Suite de tests de contrato (`tests/contract/ide/`)

Un solo parametrizado sobre TODOS los adapters registrados — ningún adapter escapa:

1. **test_setup_idempotent**: setup ×2 en tmp project → byte-equality de todos los archivos tocados (con timestamp congelado).
2. **test_remove_removes_only_cortex**: setup → escribir contenido del usuario EN los mismos archivos (dentro y fuera de marcadores) → remove → assert: contenido del usuario intacto, cero ocurrencias de marcadores Cortex, cero paths Cortex restantes según manifest.
3. **test_uninstall_never_touches_user_files**: crear AGENTS.md/README.md/justfile del usuario ANTES de setup → remove → siguen existiendo (mata el bug pi #3 para siempre).
4. **test_explicit_project_root**: ejecutar setup y remove con cwd = subdir arbitrario y project_root explícito → opera sobre project_root (mata #6).
5. **test_dry_run_touches_nothing**: dry_run=True → reporte correcto, mtime de todos los archivos sin cambios.
6. **test_status_reports_drift**: modificar `.cortex/skills/cortex-sync.md` después de setup → status reporta drift.
7. **test_manifest_roundtrip**: setup escribe manifest válido; remove lo consume; remove deja manifest vacío/actualizado.
8. **test_cli_parity**: cada comando deprecated produce el mismo resultado JSON que su reemplazo.

Criterio: estos tests corren en CI propio (gate) y son bloqueantes para cualquier PR que toque `cortex/ide/**`.

## Riesgos transversales

| Riesgo | Mitigación |
|---|---|
| Migración rompe installs existentes de adopters (archivos viejos sin marcadores) | setup V2 detecta contenido Cortex legacy (autogen header) y lo convierte a bloque marcado en una pasada; test de migración desde fixture de install v0.5 |
| Formatos nativos de IDEs cambian sin aviso (6/11 adapters no validados) | capabilities() declarado; adapters no validados quedan marcados en status; no bloquean el estándar |
| Doble escritura durante deprecation (comando viejo + nuevo tocan lo mismo) | ambos delegan al MISMO código V2 desde el día 1; paridad test |
| Manifest se desincroniza si el usuario borra archivos a mano | status() re-deriva estado real del disco, manifest es caché optimista no fuente de verdad para remove de bloques marcados |
| Alcance creep hacia refactor de server.py/MCP | EXPLÍCITAMENTE fuera de esta obra (es review #10 §7.1, otra tarea); esta obra solo cambia cómo los IDEs APUNTAN al server |

## Criterio de salida (gates)

- [ ] `pytest tests/contract/ide/` verde para los 11 adapters registrados.
- [ ] Test #3 (uninstall nunca borra archivos preexistentes del usuario) verde para pi específicamente.
- [ ] Test #4 (project_root explícito con cwd distinto) verde para TODOS.
- [ ] Grep: cero usos de `Path.cwd()` dentro de `cortex/ide/adapters/**`.
- [ ] Marcadores BEGIN/END presentes en todo archivo markdown/TOML/YAML que Cortex escriba sobre archivos compartidos (claude_code CLAUDE.md, windsurf, codex ya cumple).
- [ ] `cortex ide setup/status/remove/list` funcionan para cualquier IDE target con la MISMA sintaxis; comandos viejos emiten warning de deprecation.
- [ ] `--dry-run` funcional en setup y remove.
- [ ] Docs de onboarding actualizadas a la superficie nueva.
- [ ] Suite completa verde (gate TRAMO 0 sigue pasando).
