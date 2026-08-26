# Progreso BAJA DEFINITIVA — RUTA 1, MITAD B (ide ×4 + docs ×4)

> Registro ÚNICO de la MITAD B del paquete "BAJA DEFINITIVA — RUTA 1"
> (`docs/transformacion/PROMPT-BAJA-DEFINITIVA-RUTA1.md`), post-Obra 07
> (cierre `02f6daf`). Territorio SOLO le mode de la matriz MITAD B:
> `cortex-cli/src/commands/ide_cmd.rs`, `docs_cmd.rs`,
> `cortex-services/src/migration.rs` (list_backups/restore_backup),
> `cortex-app/src/semantic/routing.rs` (RouteSpec canónico),
> gate `bench/parity/cierre_leaves_b_golden.py`, tests `t_lea_b_*`,
> registro propio. PROHIBIDO: `main.rs`/`commands/mod.rs` (paso 0,
> congelados), territorios de la MITAD A, `Cargo.toml`/`Cargo.lock`
> (cero deps nuevas — no hizo falta ninguna).

## Precondiciones de arranque

- ✅ R0: `pgrep -af "pytest|cargo|python"` → sin zombis.
- ✅ HEAD = `b529f35` (paso 0: scaffold dispatch ide/remember/forget — stubs
  devuelven `false` ⇒ passthrough idéntico al estado previo).
- ✅ Rama `feature/transformacion-2026-08`; oráculo baseline
  **2552 passed, 21 skipped, 0 failed, 0 errors** (Obra 07, `02f6daf`).
- ✅ Cargo tree limpio al arranque (`cargo check -p cortex-cli` OK).

## Divergencias de documento vs oráculo (resueltas a favor del oráculo)

1. El doc regente (B.1) dice "setup/remove: install adapters + hooks" —
   el oráculo `cortex/cli/ide.py::run_setup/run_remove` NO instala/desinstala
   hooks de sesión (solo `cortex.ide.inject` / `adapter.uninstall`). El gate
   es byte-parity contra el CLI REAL ⇒ se replicó el oráculo. La verificación
   de "artefactos escritos" queda cubierta por `ide status --ide pi`
   post-setup (detalle del hook justfile: "exists but no cortex recipes").
2. `ide list` del oráculo NO acepta `--project-root` (el brief lo lista
   como `list [--project-root] [--json]`). Se replicó el oráculo.
3. `docs list-backups` del oráculo NO tiene `--json`. Se replicó el oráculo
   (2 casos texto; sin inventar --json).
4. `--doc-type` inválido (routing-table): typer emite usage + panel rich con
   `Usage: python -m cortex.cli.main …` bajo `-m`. El gate invoca Python vía
   el console script `.venv/bin/cortex` (mismo app typer, programa "cortex")
   y el nativo replica el panel typer (width 80, título " Error " izquierdo)
   ⇒ paridad byte-a-byte. Documentado arriba en el gate.

## RED → GREEN (test Rust primero, servicios reales + fixtures tmp)

### Tests añadidos (cortex-cli/tests, naming `t_lea_b_*`)

- `t_lea_b_ide.rs` (6): list json (11 adapters sorted por nombre), list
  texto (tabla rich), status --ide nope (error repr exacto, rc 2), setup sin
  --ide (rc 2 + tiers), setup pi real (bundle `.pi/`, justfile, "Setup
  complete…" + status hooks_detail post-setup) → remove pi real (8 entradas),
  status all json (config_checks + hooks_detail).
- `t_lea_b_docs.rs` (7): validate texto (Issues exacto), validate json
  (payload pretty exacto), list-backups vacío + con 1 backup (nombre+tamaño),
  restore nombre corto + ruta completa + inexistente (rc 1, "Backup not
  found: …"), routing-table texto (header + filas exactas),
  routing-table --doc-type adr --json (fields oráculo), doc_type inválido
  (rc 2 + usage + panel + mensaje), routing-table --json (13 types orden).

RED: los 13 tests fallaban contra los stubs (passthrough a CORTEX_BIN
inexistente, rc 127 / salida vacía). GREEN: implementación glue/portes —
evidencia: `cargo test -p cortex-cli --test t_lea_b_ide --test t_lea_b_docs`
→ **13 passed, 0 failed**.

### Portes/glue por familia (orden de implementación)

1. **`ide` ×4** (`ide_cmd.rs`): glue sobre `cortex_setup::ide` (adapters,
   prompts, IdeCtx) + `HookInstaller` (collect_status/lado hooks).
   - Registry nativo espejo de `cortex/ide/registry.py`: sorted por nombre,
     aliases, TARGET/COMMUNITY/EXPERIMENTAL, VALIDATED_IDES.
   - Errores EXACTOS: `Error: "Unknown IDE: 'nope'.\n  Target …"` (repr de
     KeyError: comillas + `\n` literales en UNA línea) y `--ide is required
     for \`cortex ide setup\` …` (rc 2 ambos).
   - Tabla rich byte-parity: portado del algoritmo `rich.table.Table`
     (HEAVY_HEAD, padding (0,1), overflow ellipsis): medida natural por
     columna (+2 padding), colapso proporcional a 80-(n+1), re-medida,
     word-wrap greedy + elipsis `raw[:w-1]+"…"`, justify left/center.
   - `setup`: `cortex_ide.inject` (inject_profiles + inject_mcp, orden pi =
     bundle verbatim); salida `[Cortex IDE] Injecting profiles for …` +
     `  [OK] …` + `✅ Setup complete for …`. `--dry-run` incluido.
   - `remove`: `adapter.uninstall(root)` + still_present/skipped;
     `Remove complete for {display}: {removed} entradas procesadas, {skipped}
     paths restantes.`
   - `status`: `collect_status` (config_checks/mcp/hooks) texto + JSON
     compacto `json.dumps(ensure_ascii=False)`; detalle texto `n/a` cuando no
     hay hook adapter (mismo `or` del oráculo).
2. **`docs validate`**: glue sobre `migration::validate_vault` + payload.
   Texto = `format_report` del oráculo (Vault/Total/Valid/Invalid/No
   frontmatter/Issues); JSON pretty `json.dumps(payload, indent=2)` con
   orden de claves del dict.
3. **`docs restore` / `docs list-backups`** (`migration.rs`): portes NUEVOS
   `list_backups` (glob `vault-*.tar.gz` sorted) y `restore_backup`
   (extracción `tar xzf`, patrón shell-out de `create_backup`; resolución
   del "top" desde `tar tzf`; guarda tar-slip espejo del oráculo). CLI:
   resolución por nombre corto (`backup in p.name`, último candidato) o ruta
   absoluta; errores `Backup not found: {name}` (rc 1) y `Restored: {path}`.
4. **`docs routing-table`** (`semantic/routing.rs`): `RouteSpec` COMPLETO
   (17 campos del dataclass, orden del `asdict`) + tabla canónica de los 13
   doc_types con writers vinculados (Fase 03/04 + Phase 09.B) y
   `template_path` = repo/cortex/documentation/templates/{value}.md.j2
   (mismo string absoluto de compilación que el oráculo). Texto = tabla fija
   `{:<14} {:<14} {:<38} {:<22} {:<8} {:<14}`; JSON pretty (single → objeto,
   all → array). `--doc-type` inválido → mensaje exacto
   `Unknown doc_type: 'bogus'. Valid: ['session', …, 'design']` en panel
   typer (stderr, rc 2).

## Gate propio (Nivel 2) — `bench/parity/cierre_leaves_b_golden.py`

Patrón de `cierre_cli_golden.py`; 25 casos reales (≥2 por subcomando):

- ide list (texto+json), ide setup sin --ide (err), ide status nope (err),
  ide status all (texto+json), ide status pi (texto+json pre-setup),
  ide setup pi real, ide status pi post-setup json, ide remove pi real.
- docs validate (texto+json issues; texto+json vault válido [valid-proj]),
  docs list-backups (vacío [no-backups] + con 2 backups), docs restore
  (nombre corto, ruta completa, inexistente), docs routing-table (texto all,
  --doc-type adr texto+json, json all, doc_type inválido).

Normalizaciones SOLO las pactadas: {{ROOT}}, {{TS}} (incluye variante
compacta de filename de backup `YYYY-MM-DDTHHMMSSZ`), {{SHA}}; las demás
({{ELAPSED}}/{{RUN}}/{{MEMID}}/scores) no aplican en esta mitad y no se
añadió ninguna normalización nueva.

Estabilidad del fixture (lecciones):
- Prefijo tmp corto (`cb_`): las celdas DETAIL de status se truncan con "…"
  y el root completo debe caber dentro de la ventana de 20 celdas para que
  {{ROOT}} normalice.
- `time.sleep(1.1)` entre los 2 `create_backup` del fixture: el nombre tiene
  resolución de 1s; sin sleep el orden lexicográfico del listado era
  no-determinista (colisión de timestamp).
- `os.utime` congelado en los archivos del vault: el .tar.gz embeleña mtime
  de los miembros ⇒ el tamaño listado (`{name}\t{size} bytes`) sería
  run-dependente si los mtimes variaran.

`build` → `golden_cierre_b.txt` (545 líneas); `verify` →
**byte-parity post-normalización 545 líneas, ✅ PARIDAD**

## Cold start (N=20 por subcomando, binario debug nativo)

| subcomando | avg (ms) | p50 (ms) | max (ms) |
|---|---|---|---|
| ide list | 4.2 | 4.1 | 6.2 |
| ide status (all) | 3.3 | 3.3 | 5.2 |
| ide setup (--ide faltante, err) | 2.5 | 2.6 | 3.0 |
| ide remove (--ide faltante, err) | 3.7 | 3.8 | 5.3 |
| docs validate | 6.2 | 6.4 | 7.5 |
| docs restore (inexistente, err) | 2.7 | 2.8 | 3.7 |
| docs list-backups | 2.7 | 2.7 | 3.2 |
| docs routing-table | 2.6 | 2.6 | 2.9 |

Todos « 100 ms (target del brief).

## Auditoría del passthrough restante (MITAD B)

- `cortex ide <subcomando desconocido>` ⇒ `false` ⇒ passthrough (Typer
  emite "No such command", paridad gratis).
- `cortex docs <subcomando desconocido>` ⇒ passthrough (idem).
- `cortex docs search`/`migrate` ya nativos (pre-Obra 07) — intactos.
- Leaves "de diseño" (NO ruta 1): webgraph serve/doctor, hu import,
  autopilot doctor/install/uninstall — fuera de alcance, no tocados.
- Divergencias deliberadas documentadas:
  1. `restore_backup` de un archivo vacío/unsafe: el oráculo lanza excepción
     (traceback); el nativo imprime un error limpio en stderr (rc 1).
  2. Panel de error typer replicado con geometría width 80 (no-TTY); bajo
     terminal real rica cambia el wrap — el gate corre piped como todo el
     patrón de gates.

## Verificación (R2 por niveles)

1. Nivel 1: `cargo fmt --all --check` ✅ · `cargo clippy -p cortex-cli
   --all-targets -- -D warnings` ✅ · `cargo test -p cortex-cli` ✅ (suite
   completa verde, incl. tests de la MITAD A tras su cierre).
2. Nivel 2: `cierre_leaves_b_golden.py build` ✅ + `verify` ✅ (545 líneas).
3. Nivel 3: suite Python completa bajo lock R3 una sola vez — ver reporte
   `task-b-report.md` (esperado 2552/21/0/0).