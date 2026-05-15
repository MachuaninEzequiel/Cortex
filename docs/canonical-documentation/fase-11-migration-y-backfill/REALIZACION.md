# Fase 11 - Migration y Backfill - Realizacion

**Fecha de cierre:** 2026-05-14
**Esfuerzo real:** ~1 hora
**Estado:** Completado (vault real migrado)
**Dependencias cumplidas:** Fases 01-04

---

## 1. Resumen

Se implemento el pipeline de migracion idempotente que backfila el vault
existente al schema canonico, junto con un sistema de backups tar.gz para
permitir rollback.

Tres componentes nuevos:

1. **`cortex/documentation/backup.py`**: `create_backup` /
   `restore_backup` / `list_backups` para snapshots tar.gz reproducibles
   antes de cualquier operacion destructiva.

2. **`cortex/documentation/migration.py`**: `migrate_vault` que escanea
   recursivamente, infiere DocType por path, construye frontmatter
   canonico con fallbacks (mtime para fechas, type-specific extras por
   DocType) y aplica el cambio. Preserva campos legacy bajo prefijo
   `legacy_<name>` cuando no encajan en el schema.

3. **CLI `cortex docs migrate|validate|restore|list-backups`** en
   `cortex/cli/docs_migrate.py` con dry-run obligatorio por default.

Migracion real del vault de Cortex: **16/19 notas migradas, 3 quedaron
unclassifiable** (archivos en la raiz del vault sin subfolder canonico).
Documentado en Fase 13 bloque E.

---

## 2. Archivos creados / modificados

```text
Nuevos:
    cortex/documentation/backup.py             # 65 LOC
    cortex/documentation/migration.py          # 380 LOC
    cortex/cli/docs_migrate.py                 # 130 LOC: 4 subcomandos
    tests/unit/documentation/test_backup.py    # 8 tests
    tests/unit/documentation/test_migration.py # 18 tests

Modificados:
    cortex/cli/docs_subcommand.py    # +4 subcomandos: migrate/validate/restore/list-backups
```

---

## 3. Decisiones tomadas durante implementacion

### 3.1 Idempotencia via `schema_version=1` check

Si una nota ya tiene `schema_version: 1` y `doc_type: <slug>` validos, se
salta. `--force` re-migra. Esto permite ejecutar `cortex docs migrate`
repetidamente sin riesgo.

### 3.2 Backup automatico por default en `--apply`

Antes de cualquier escritura `--apply`, se crea un tar.gz del vault
completo en `<vault.parent>/.cortex/backups/vault-<timestamp>.tar.gz`.
Permite rollback rapido si algo sale mal.

Flag `--no-backup` para skip explicito (CI environments controlados).

### 3.3 Status legacy mapping

Algunos status legacy no son canonicos. Mapeos:
- SESSION: `"generated"` -> `"completed"`, `"fallback"` -> `"fallback"`.
- HU: `"imported"` -> `"backlog"`, `"in_progress"` -> `"in-progress"`.

El resto del valor legacy se preserva en `legacy_status` si no encaja.

### 3.4 `created_at` con fallback en cascada

1. Campo `created_at` del frontmatter legacy (si parseable).
2. Campo `date` legacy.
3. mtime del archivo.
4. `now()` (caso patologico).

`updated_at` sigue la misma cascada, garantizando `updated_at >= created_at`.

### 3.5 Backup excluido del scan

El walker ignora `<vault>/.cortex/backups/` y `<vault>/_archived/` para no
re-migrar notas archivadas ni los backups mismos.

### 3.6 Validacion separada del migrate

`validate_vault` es un comando independiente. Razon: tras `migrate`,
queremos verificar que el resultado pasa el schema; mantener los dos
flujos separados facilita el iterative debugging.

---

## 4. Migracion del vault real de Cortex

```bash
$ python -m cortex.cli.main docs migrate
# DRY-RUN
- Total scanned: 19
- Migrated: 16
- Unclassifiable: 3 (architecture.md, auth.md, getting_started.md en raiz)

$ python -m cortex.cli.main docs migrate --apply
- Migrated: 16
- Backup: vault-2026-05-14T174930Z.tar.gz

$ python -m cortex.cli.main docs validate
- Total notes: 19
- Valid: 16
- Invalid: 3 (los mismos 3 raiz que quedaron unclassifiable)
```

Las 3 notas raiz se documentan en Fase 13 bloque E como pendientes de
decision manual.

---

## 5. Tests ejecutados

```text
tests/unit/documentation/test_backup.py        8 passed
tests/unit/documentation/test_migration.py    18 passed
---
Fase 11 nuevos:                               26 passed
Suite global:                               1307 passed, 6 skipped, 0 fallas
```

---

## 6. Coverage

```text
cortex/documentation/backup.py         100%
cortex/documentation/migration.py      ~93%
cortex/cli/docs_migrate.py             ~85% (paths CLI defensive)
```

---

## 7. Checklist final

- [x] `cortex/documentation/migration.py` con `migrate_vault`, `validate_vault`, `format_report`
- [x] `cortex/documentation/backup.py` con `create_backup`/`restore_backup`/`list_backups`
- [x] CLI `cortex docs migrate --apply/--report-only/--force/--no-backup`
- [x] CLI `cortex docs validate`
- [x] CLI `cortex docs restore`
- [x] CLI `cortex docs list-backups`
- [x] Tests >= 20 (26 implementados)
- [x] Vault real de Cortex migrado y validado
- [x] 3 archivos raiz resueltos (Fase 13 cirugia `32aa2e9`): eliminados + 3 historicos distintos migrados a `docs/` -> `cortex docs validate --all` reporta `Invalid: 0`

---

## 8. Pendientes / Backlog

1. **Bloque E**: decidir destino de `architecture.md`, `auth.md`,
   `getting_started.md` en la raiz del vault de Cortex.

2. **Flags `--vault-scope=enterprise --project-id=foo`** en el CLI para
   migrar directamente al vault enterprise. Hoy el codigo soporta
   `vault_scope` en el schema pero el CLI default es `local`.

---

## 9. Proximos pasos

Fase 12 (Cleanup) actualiza el setup orchestrator a las 12 carpetas
canonicas y elimina deuda legacy.
