# Fase 11 - Migration y Backfill

**Fuente:** `docs/canonical-documentation/README.md`
**Estado:** Pendiente de ejecucion
**Esfuerzo estimado:** 1.5 dias
**Riesgo:** alto
**Dependencias:** Fases 01-04

---

## 1. Objetivo

Implementar el comando `cortex docs migrate` que:
1. Inventario del vault actual.
2. Clasificacion por path/contenido.
3. Generacion de nuevo frontmatter canonico.
4. Backfill idempotente con dry-run obligatorio.
5. Reporte completo de cambios.
6. Backup automatico antes de aplicar.
7. Migracion del vault de Cortex (proyecto base) como validacion final.

Detalle completo en `migration-guide.md`.

---

## 2. Archivos a crear

```text
cortex/documentation/
    migration.py                # NUEVO: migrate_vault, classify, build_frontmatter, apply

cortex/cli/
    docs_migrate.py             # NUEVO: cortex docs migrate command

cortex/documentation/
    backup.py                   # NUEVO: tar.gz backups

tests/unit/documentation/
    test_migration.py
    test_backup.py
    test_migration_dry_run.py

tests/integration/documentation/
    test_migration_e2e.py

tests/data/
    legacy_vault_fixture/       # vault legacy para tests
        sessions/
            2026-04-14_old-session.md
        decisions/
            ADR-001-old.md
        incidents/
            2026-04-15_old-incident.md
        random/
            unclassifiable.md
```

---

## 3. Responsabilidades

### `migration.py`

Algoritmo completo descrito en `migration-guide.md` seccion 4. Funciones clave:

```python
@dataclass
class MigrationResult:
    total_scanned: int
    migrated: list[Path]
    already_migrated: list[Path]
    unclassifiable: list[tuple[Path, str]]   # (path, reason)
    errors: list[tuple[Path, str]]


@dataclass
class NoteDiff:
    path: Path
    classification: str
    legacy_fm: dict
    new_fm: dict
    action: str   # "migrate" | "skip" | "unclassifiable"
    body_unchanged: bool = True


def migrate_vault(
    vault_path: Path,
    *,
    apply: bool = False,
    force: bool = False,
    path_filter: Path | None = None,
    vault_scope: str = "local",
    project_id: str | None = None,
    strict: bool = False,
    preserve_legacy: bool = True,
) -> MigrationResult:
    """Migrate a vault to the canonical schema."""

    # 1. Inventory
    inventory_result = inventory_vault(vault_path)

    # 2. Compute diffs
    diffs = [compute_diff(path) for path in iter_md_files(vault_path, path_filter)]

    # 3. If dry-run, return without writing
    if not apply:
        return _build_result(diffs, applied=False)

    # 4. Backup
    backup_path = create_backup(vault_path)

    # 5. Apply
    for diff in diffs:
        if diff.action == "migrate":
            try:
                apply_migration(diff, preserve_legacy=preserve_legacy)
            except Exception as e:
                # Log + collect in errors
                ...

    # 6. Reindex
    reindex_migrated_notes(...)

    return _build_result(diffs, applied=True, backup=backup_path)


def compute_diff(path: Path) -> NoteDiff:
    """Compute the diff for a single note."""
    legacy = parse_frontmatter_lenient(path)
    if legacy.get("schema_version") == 1:
        return NoteDiff(path=path, action="skip", ...)

    inferred = doc_type_from_path(path)
    if inferred is None:
        return NoteDiff(path=path, action="unclassifiable", ...)

    new_fm = build_new_frontmatter(path, legacy, inferred)
    return NoteDiff(path=path, classification=inferred.value,
                     legacy_fm=legacy, new_fm=new_fm, action="migrate")


def build_new_frontmatter(path: Path, legacy: dict, doc_type: DocType) -> dict:
    """Build new frontmatter from legacy + path inference."""
    # Common fields
    new = {
        "schema_version": 1,
        "doc_type": doc_type.value,
        "title": legacy.get("title", path.stem),
        "created_at": resolve_created_at(legacy, path),
        "updated_at": resolve_updated_at(legacy, path),
        "tags": legacy.get("tags", []),
        "status": resolve_status(legacy, doc_type),
        "links": extract_wiki_links_from_body(path),
        "vault_scope": "local",
        "fingerprint": compute_body_fingerprint(path),
    }
    # Type-specific
    new.update(type_specific_fields(legacy, doc_type, path))
    # Preserve legacy
    for k, v in legacy.items():
        if k not in new and k not in STANDARD_LEGACY_KEYS:
            new[f"legacy_{k}"] = v
    return new


def apply_migration(diff: NoteDiff, *, preserve_legacy: bool = True) -> None:
    """Write the new frontmatter, keep body."""
    content = diff.path.read_text(encoding="utf-8")
    body = split_frontmatter_and_body(content)[1]

    new_yaml = yaml_dump_safe(diff.new_fm)
    new_content = "---\n" + new_yaml + "---\n\n" + body
    diff.path.write_text(new_content, encoding="utf-8")
```

### `backup.py`

```python
# cortex/documentation/backup.py
import tarfile
from pathlib import Path
from datetime import datetime, UTC


def create_backup(vault_path: Path, backups_dir: Path | None = None) -> Path:
    """Create tar.gz backup of vault. Returns backup path."""
    backups_dir = backups_dir or (vault_path.parent / ".cortex" / "backups")
    backups_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H%M%SZ")
    backup_name = f"vault-{timestamp}.tar.gz"
    backup_path = backups_dir / backup_name
    with tarfile.open(backup_path, "w:gz") as tar:
        tar.add(vault_path, arcname=vault_path.name)
    return backup_path


def restore_backup(backup_path: Path, target_path: Path) -> None:
    """Restore vault from backup."""
    with tarfile.open(backup_path, "r:gz") as tar:
        tar.extractall(target_path.parent)


def list_backups(backups_dir: Path) -> list[Path]:
    """List available backups, sorted by date."""
    return sorted(backups_dir.glob("vault-*.tar.gz"))
```

### CLI `cortex docs migrate`

```python
# cortex/cli/docs_migrate.py
import typer
from pathlib import Path

app = typer.Typer()


@app.command()
def migrate(
    apply: bool = typer.Option(False, "--apply"),
    path: Path = typer.Option(Path("vault"), "--path"),
    force: bool = typer.Option(False, "--force"),
    vault_scope: str = typer.Option("local", "--vault-scope"),
    project_id: str | None = typer.Option(None, "--project-id"),
    report_only: bool = typer.Option(False, "--report-only"),
    output: Path | None = typer.Option(None, "--output"),
    strict: bool = typer.Option(False, "--strict"),
):
    """Migrate vault to canonical schema."""
    from cortex.documentation.migration import migrate_vault, format_report

    result = migrate_vault(
        path, apply=apply, force=force,
        vault_scope=vault_scope, project_id=project_id, strict=strict,
    )

    report = format_report(result, applied=apply)
    if output:
        output.write_text(report, encoding="utf-8")
    else:
        typer.echo(report)
```

Registrar como subcommando de `cortex docs`:

```python
from cortex.cli.docs_migrate import app as migrate_app
docs_app.add_typer(migrate_app, name="migrate")
```

### CLI `cortex docs restore`

```python
@app.command()
def restore(
    backup: str = typer.Option(..., "--backup"),
    target: Path = typer.Option(Path("vault"), "--target"),
):
    """Restore vault from backup."""
```

### CLI `cortex docs validate`

```python
@app.command()
def validate(
    all_files: bool = typer.Option(False, "--all"),
    path: Path | None = typer.Option(None, "--path"),
):
    """Validate vault frontmatter against schema."""
    # iterar, validar cada nota, reportar drift
```

---

## 4. Casos especiales

### CONTEXT.md -> Glossary entries

```python
def migrate_context_md(context_path: Path, vault_path: Path) -> list[Path]:
    """Split CONTEXT.md into individual glossary entries."""
    content = context_path.read_text(encoding="utf-8")
    sections = parse_h2_sections(content)

    created = []
    for section_title, body in sections:
        term_slug = slugify(section_title)
        target = vault_path / "glossary" / f"{term_slug}.md"
        target.parent.mkdir(parents=True, exist_ok=True)

        # Write con write_glossary_entry o equivalente
        data = GlossaryEntryData(
            term=section_title,
            title=section_title,
            definition=body,
            ...
        )
        target = write_glossary_entry(data, vault=vault)
        created.append(target)

    # Backup CONTEXT.md
    context_path.rename(context_path.with_suffix(".legacy.md"))
    return created
```

### Notas sin frontmatter

`parse_frontmatter_lenient` retorna `{}`. La logica de migracion infiere todo:
- `created_at` desde mtime.
- `title` desde filename slug.
- `status` desde primer valido del tipo.
- `tags` = `[]`.

---

## 5. Tests

### `test_migration.py` (>= 12)

```python
def test_compute_diff_already_migrated_returns_skip()
def test_compute_diff_unclassifiable_path()
def test_compute_diff_session_legacy_to_canonical()
def test_compute_diff_adr_legacy_to_canonical()
def test_build_new_frontmatter_includes_all_required()
def test_build_new_frontmatter_preserves_legacy_fields()
def test_resolve_created_at_from_date()
def test_resolve_created_at_from_mtime_fallback()
def test_resolve_status_maps_valid()
def test_resolve_status_defaults_when_invalid()
def test_extract_wiki_links_from_body()
def test_apply_migration_writes_new_yaml()
def test_apply_migration_preserves_body()
```

### `test_backup.py` (>= 5)

```python
def test_create_backup_tar_gz()
def test_backup_filename_timestamped()
def test_list_backups_sorted()
def test_restore_recovers_original()
def test_backup_idempotent_naming()
```

### `test_migration_dry_run.py` (>= 5)

```python
def test_dry_run_no_writes()
def test_dry_run_reports_planned_changes()
def test_dry_run_count_matches_apply()
def test_dry_run_handles_unclassifiable()
def test_dry_run_with_path_filter()
```

### `test_migration_e2e.py` (>= 5)

```python
def test_migrate_legacy_vault_fixture(legacy_vault):
    """Full migration of legacy_vault_fixture works."""
    result = migrate_vault(legacy_vault, apply=True)
    assert len(result.migrated) > 0
    assert len(result.errors) == 0

def test_migrate_idempotent(legacy_vault):
    """Running twice is no-op the second time."""
    migrate_vault(legacy_vault, apply=True)
    result2 = migrate_vault(legacy_vault, apply=True)
    assert len(result2.migrated) == 0
    assert len(result2.already_migrated) > 0

def test_post_migration_validates(legacy_vault):
    """All migrated notes validate."""
    migrate_vault(legacy_vault, apply=True)
    for md in legacy_vault.rglob("*.md"):
        validate_path_frontmatter(md)  # no raise

def test_context_md_splits_to_glossary(legacy_vault_with_context):
    """CONTEXT.md becomes glossary entries."""

def test_backup_created_on_apply(legacy_vault):
    """Backup exists after --apply."""
```

---

## 6. Migracion del vault de Cortex

Tras los tests con fixtures, migrar el vault de Cortex en si (validacion final):

```bash
# 1. Backup manual (paranoid)
$ git stash
$ tar czf /tmp/vault-pre-migration.tar.gz vault/

# 2. Dry-run
$ cortex docs migrate
> 25 notas escaneadas
> 22 migrables
> 3 requieren atencion manual

# 3. Review diff
$ cortex docs migrate --output migration-plan.md
$ cat migration-plan.md

# 4. Apply
$ cortex docs migrate --apply
> Backup creado: .cortex/backups/vault-2026-05-14T100000Z.tar.gz
> 22 notas migradas
> Reporte: migration-2026-05-14.md

# 5. Validate
$ cortex docs validate --all
> 22/22 notas migradas validan.
> 3 notas no migradas (review manual).

# 6. Commit
$ git add vault/
$ git commit -m "feat(docs): migrate vault to canonical schema"
```

---

## 7. Checklist

- [ ] `cortex/documentation/migration.py` con `migrate_vault`, `compute_diff`, `apply_migration`
- [ ] `cortex/documentation/backup.py` con `create_backup`, `restore_backup`
- [ ] CLI `cortex docs migrate` con flags
- [ ] CLI `cortex docs restore`
- [ ] CLI `cortex docs validate --all`
- [ ] Fixture `tests/data/legacy_vault_fixture/`
- [ ] Tests >= 27
- [ ] Coverage >= 90%
- [ ] Migracion del vault de Cortex aplicada y validada

---

## 8. Gate de salida

- `pytest tests/unit/documentation/test_migration.py tests/integration/documentation/test_migration_e2e.py` pasa al 100%.
- Migracion del vault de Cortex completa: `cortex docs validate --all` reporta 0% drift en notas migradas.
- Backup creado y verificable.
- `REALIZACION.md` documentado incluyendo diff del vault real.

---

## 9. Riesgos y mitigaciones

| Riesgo | Mitigacion |
|---|---|
| Backup no existe en algun escenario | Force create antes de cualquier apply |
| Migracion borra campos legacy | preserve_legacy=true default; tests verifican |
| Idempotencia rota | Test e2e ejecuta dos veces |
| Status inferido erroneo | Default conservador (mas restrictivo); reportar |
| created_at del futuro o pasado raro | Sanity check: clamp a [1970, now+1day] |
| Reindexacion post-migracion lenta | Batch + cache (Fase 06) |
| Notas con body que parece frontmatter (triple-dash) | YAML parser robusto detecta el cierre correcto |
| CONTEXT.md sin H2 estructura clara | Fallback: single glossary entry con todo el contenido; reportar |
| Reporte muy grande | Truncar diff por nota; full diff en archivo separado |
| Migracion del vault real falla parcial | Restore desde backup; investigar; reintentar |

---

## 10. Notas para agentes implementadores

1. **Dry-run sin tocar disco SIEMPRE.** Hash before/after debe ser identico.
2. **Backup automatico antes de apply.** Sin excepcion.
3. **Idempotencia es contractual.** Tests verifican.
4. **Reporte detallado.** Por nota: que cambio, que se preservo, por que.
5. **`preserve_legacy=true` default.** Recuperabilidad.
6. **Sanity checks en datos:** datetime valido, fingerprint format, etc.
7. **Errors no abortan.** Skip + report, no crash.
8. **El vault de Cortex es el primer cliente real.** Test del worst case.

---

## 11. Referencias

- `docs/canonical-documentation/migration-guide.md` - especificacion completa
- `docs/canonical-documentation/data-model.md` - schemas esperados
- `docs/canonical-documentation/frontmatter-schema.md` - frontmatter target
- `cortex/documentation/common.py` (Fase 00) - helpers
- `cortex/documentation/inventory.py` (Fase 00) - inventory
