# Migration Guide - Plan de Migracion del Vault Actual

**Documento:** plan completo de migracion del vault existente al nuevo schema
**Audiencia:** implementadores, operadores de vault
**Estado:** especificacion normativa

---

## 1. Objetivos

1. **Idempotencia:** re-ejecutar la migracion no rompe ni duplica.
2. **Reversibilidad:** poder volver al estado previo si algo sale mal.
3. **Dry-run obligatorio:** ver diffs antes de escribir.
4. **Preservacion de datos:** ningun campo legacy se borra.
5. **Reporte completo:** mostrar exactamente que cambio.

---

## 2. Estado actual del vault de Cortex

Antes de empezar, snapshot del vault de Cortex (proyecto base):

```bash
$ cortex docs status
Total notas: ~25 (entre vault local del proyecto)
Distribucion estimada:
  sessions/: 13 archivos (active)
  decisions/: 1 archivo (ADR-001)
  incidents/: 1 archivo
  architecture/: 1 archivo
  hu/: 0 archivos
  runbooks/: 0 archivos
  specs/: 0 archivos
  changelog/: 0 archivos
```

Tras migracion: todas las notas deben validar el schema nuevo.

---

## 3. Comando `cortex docs migrate`

### 3.1 Sintaxis

```bash
# Dry-run (default, no escribe)
$ cortex docs migrate

# Aplicar cambios
$ cortex docs migrate --apply

# Solo un subdirectorio
$ cortex docs migrate --path vault/sessions/

# Forzar re-migracion (peligroso)
$ cortex docs migrate --apply --force

# Solo reporte
$ cortex docs migrate --report-only

# Output a archivo
$ cortex docs migrate --output migration-report.md
```

### 3.2 Flags

| Flag | Default | Comportamiento |
|---|---|---|
| `--apply` | `false` | Si `true`, escribe cambios; si `false`, dry-run |
| `--path` | `vault/` | Subdirectorio a migrar |
| `--force` | `false` | Re-migra notas ya migradas (id por presencia de `schema_version`) |
| `--report-only` | `false` | Solo genera reporte sin tocar nada |
| `--output` | stdout | Path para guardar reporte |
| `--vault-scope` | `local` | `local` o `enterprise` |
| `--project-id` | `null` | Necesario si `vault-scope=enterprise` |
| `--strict` | `false` | Si `true`, falla en notas que no pueden migrar |
| `--preserve-legacy` | `true` | Mantener campos legacy con prefijo `legacy_` |

### 3.3 Ejemplos

```bash
# Ver que pasaria
$ cortex docs migrate
> 25 notas escaneadas
> 22 migrables
> 3 requieren atencion manual:
>   - vault/CONTEXT.md (no es un doc_type valido)
>   - vault/notes/random.md (sin patron de carpeta reconocible)
>   - vault/architecture/release-2-known-weaknesses.md (frontmatter conflictivo)

# Aplicar
$ cortex docs migrate --apply
> 22 notas migradas exitosamente
> 3 saltadas (ver reporte)
> Reporte: migration-2026-05-14.md

# Validar resultado
$ cortex docs validate --all
> 22/25 notas validan correctamente.
> Drift: 12%
```

---

## 4. Algoritmo de migracion

### 4.1 Paso 1: Inventario

```python
def inventory(vault_path: Path) -> InventoryResult:
    """Scan vault, classify notes."""
    result = InventoryResult()
    for md_file in vault_path.rglob("*.md"):
        result.add(classify_note(md_file))
    return result


def classify_note(path: Path) -> NoteClassification:
    """Determine if note needs migration."""
    fm = parse_frontmatter_lenient(path)

    if fm.get("schema_version") == 1:
        return NoteClassification.ALREADY_MIGRATED

    inferred = doc_type_from_path(path)
    if inferred is None:
        return NoteClassification.UNCLASSIFIABLE

    return NoteClassification(
        doc_type=inferred,
        legacy_fm=fm,
        path=path,
        action="migrate",
    )
```

### 4.2 Paso 2: Diff por nota

Para cada nota a migrar:

```python
def compute_diff(classification: NoteClassification) -> NoteDiff:
    """Compute frontmatter diff."""
    legacy = classification.legacy_fm
    new = build_new_frontmatter(classification)
    return NoteDiff(
        path=classification.path,
        legacy_fm=legacy,
        new_fm=new,
        body_unchanged=True,
    )
```

### 4.3 Paso 3: Construccion del nuevo frontmatter

```python
def build_new_frontmatter(classification: NoteClassification) -> dict:
    legacy = classification.legacy_fm
    doc_type = classification.doc_type

    # Campos comunes
    new = {
        "schema_version": 1,
        "doc_type": doc_type.value,
        "title": legacy.get("title", classification.path.stem),
        "created_at": _resolve_created_at(legacy),
        "updated_at": _resolve_updated_at(legacy),
        "tags": legacy.get("tags", []),
        "status": _resolve_status(legacy, doc_type),
        "links": _extract_wiki_links_from_body(classification.path),
        "vault_scope": "local",
        "fingerprint": _compute_fingerprint(classification.path),
    }

    # Campos por tipo
    if doc_type == DocType.SESSION:
        new["session_id"] = _resolve_session_id(legacy, classification.path)
        new["pr"] = legacy.get("pr")
        new["branch"] = legacy.get("branch")
        new["commit"] = legacy.get("commit")
    elif doc_type == DocType.ADR:
        new["adr_number"] = _extract_adr_number(classification.path.stem)
        new["supersedes"] = []
        new["superseded_by"] = None
        new["alternatives_considered"] = []
        new["acceptance_criteria_met"] = False
    elif doc_type == DocType.INCIDENT:
        new["incident_number"] = _extract_incident_number_or_assign(classification.path)
        new["severity"] = legacy.get("severity", "medium")
        new["opened_at"] = legacy.get("date") or _resolve_created_at(legacy)
        new["closed_at"] = None
        new["affected_services"] = []
    # ... etc por tipo

    # Preservar campos legacy
    for k, v in legacy.items():
        if k not in new and k not in _STANDARD_LEGACY_KEYS:
            new[f"legacy_{k}"] = v

    return new
```

### 4.4 Paso 4: Resolucion de campos

#### `_resolve_status`

```python
def _resolve_status(legacy: dict, doc_type: DocType) -> str:
    legacy_status = legacy.get("status")
    valid = VALID_STATUSES[doc_type]

    if legacy_status in valid:
        return legacy_status

    # Mapeos especiales
    if doc_type == DocType.SESSION:
        if legacy_status in {"fallback", "auto-draft"}:
            return legacy_status  # estos son validos
        return "completed"
    elif doc_type == DocType.ADR:
        if legacy_status == "accepted":
            return "accepted"
        return "proposed"
    # ... etc

    # Default al primero valido
    return next(iter(valid))
```

#### `_resolve_created_at` y `_resolve_updated_at`

```python
def _resolve_created_at(legacy: dict) -> str:
    """Try to find a sensible created_at from legacy fields."""
    if "date" in legacy:
        d = legacy["date"]
        if isinstance(d, str):
            # Try to parse
            try:
                dt = datetime.fromisoformat(d.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=UTC)
                return dt.isoformat()
            except ValueError:
                pass
        elif isinstance(d, datetime):
            return d.replace(tzinfo=UTC if d.tzinfo is None else d.tzinfo).isoformat()
    # Fallback: file mtime
    return datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat()


def _resolve_updated_at(legacy: dict) -> str:
    """Updated_at >= created_at."""
    if "updated_at" in legacy:
        return _resolve_created_at({"date": legacy["updated_at"]})
    return _resolve_created_at(legacy)  # mismo que created
```

#### `_extract_wiki_links_from_body`

```python
WIKI_LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")

def _extract_wiki_links_from_body(path: Path) -> list[str]:
    """Extract all unique wiki-links from the body."""
    content = path.read_text(encoding="utf-8")
    # Skip frontmatter
    body = _skip_frontmatter(content)
    return sorted(set(WIKI_LINK_RE.findall(body)))
```

#### `_compute_fingerprint`

```python
def _compute_fingerprint(path: Path) -> str:
    """sha256 of body (excluding frontmatter)."""
    content = path.read_text(encoding="utf-8")
    body = _skip_frontmatter(content)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()
```

### 4.5 Paso 5: Escritura

```python
def apply_migration(diff: NoteDiff) -> None:
    """Apply the diff: replace frontmatter, keep body."""
    content = diff.path.read_text(encoding="utf-8")
    body = _skip_frontmatter(content)

    new_yaml = yaml.safe_dump(
        diff.new_fm,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )
    new_content = "---\n" + new_yaml + "---\n\n" + body
    diff.path.write_text(new_content, encoding="utf-8")
```

Idempotencia: si `legacy_fm.schema_version == 1` ya, saltar (a menos que `--force`).

### 4.6 Paso 6: Reindexacion post-migracion

```python
def reindex_migrated(diffs: list[NoteDiff], vault: VaultReader) -> None:
    """Re-index migrated notes so chunks/vectors reflect new metadata."""
    for diff in diffs:
        rel_path = str(diff.path.relative_to(vault.path))
        vault.index_file(rel_path)
```

### 4.7 Paso 7: Reporte

```markdown
# Migration Report - 2026-05-14T10:00:00Z

## Summary

- Vault path: `vault/`
- Total notes scanned: 25
- Migrated: 22
- Skipped (already migrated): 0
- Unclassifiable: 3
- Errors: 0

## Migrated notes

### vault/sessions/2026-04-14_feat-add-login.md

**Action:** migrated to schema_version=1, doc_type=SESSION
**Changes:**
- `date` -> `created_at`, `updated_at`
- `tags` preserved
- `pr`, `author`, `branch`, `commit` preserved
- `session_id` extracted from filename
- `legacy_author` retained (no canonical equivalent)

### vault/decisions/ADR-001-hybrid-search-fusion.md

**Action:** migrated to schema_version=1, doc_type=ADR
**Changes:**
- `status: accepted` preserved
- `adr_number=1` extracted from filename
- `supersedes=[]` (default)
- ...

## Unclassifiable notes

These require manual action.

### vault/CONTEXT.md

**Reason:** No directory pattern matches.
**Suggested action:** split into glossary entries (`vault/glossary/<term>.md`).

### vault/notes/random.md

**Reason:** `vault/notes/` not in routing table.
**Suggested action:** classify and move to correct subfolder, or delete.

### vault/architecture/release-2-known-weaknesses.md

**Reason:** frontmatter has conflicting fields.
**Suggested action:** review manually.
```

---

## 5. Casos especiales

### 5.1 `CONTEXT.md` -> Glossary entries

`CONTEXT.md` es un archivo monolitico con muchos terminos. Migracion:

1. Parse del markdown para identificar headers H2 (un termino por seccion).
2. Crear `vault/glossary/<term-slug>.md` por cada seccion.
3. Frontmatter de cada entry:
   ```yaml
   doc_type: glossary
   term: <header text>
   definition: <body de la seccion>
   ```
4. Backup de `CONTEXT.md` original como `CONTEXT.legacy.md`.

### 5.2 Carpeta `vault/changelog/` vacia

Si vacia, eliminar. Si tiene content, asignar `doc_type=changelog` y migrar.

### 5.3 `architecture.md` (raiz del vault) vs `vault/architecture/*.md`

Caso ambiguo. Decision:
- Si esta en raiz: mover a `vault/architecture/main.md`.
- Si esta en `vault/architecture/`: dejar.

### 5.4 Notas con frontmatter `doc_type` ya seteado

Saltar (idempotencia).

### 5.5 Notas con frontmatter malformado

Reportar como `UNCLASSIFIABLE`. Sugerir review manual.

### 5.6 Notas sin frontmatter

Inferir todo desde path + body. Frontmatter nuevo se prepende.

---

## 6. Rollback

### 6.1 Backup automatico

Antes de aplicar:

```bash
$ cortex docs migrate --apply
> Creating backup: .cortex/backups/vault-2026-05-14T10:00:00Z.tar.gz
> Backup size: 2.3 MB
> Proceeding with migration...
```

### 6.2 Restore

```bash
$ cortex docs restore --backup 2026-05-14T10:00:00Z
> Restoring vault from .cortex/backups/vault-2026-05-14T10:00:00Z.tar.gz
> 25 notes restored
> Cache invalidated (.cortex_index.json removed)
```

### 6.3 Rollback parcial

Si solo un subset migro mal:

```bash
$ cortex docs restore --backup 2026-05-14T10:00:00Z --path vault/sessions/
> Restoring only sessions/...
```

---

## 7. Migracion a enterprise

### 7.1 Promocion bulk inicial

Cuando una organizacion empieza a usar vault enterprise:

```bash
$ cortex enterprise migrate-from-local \
    --vault-source vault/ \
    --vault-target ./vault-enterprise/ \
    --project-id mi-proyecto \
    --owner-default ezequiel@cortex.ai \
    --team-default cortex-core \
    --classification-default internal \
    --dry-run
```

Hace todo lo que `docs migrate` mas:
- Agrega `owner`, `team`, `classification`, `retention_days`.
- Mueve a subfolder con `{project_id}`.
- Inicializa `audit_trail` con evento `promoted`.

### 7.2 Verificacion post-migracion

```bash
$ cortex enterprise verify
> Vault: vault-enterprise/
> Total notas: 22
> Con governance fields completos: 22/22 (100%)
> Audit trails iniciados: 22/22 (100%)
> Retention policies aplicadas: 22/22 (100%)
```

---

## 8. Comandos auxiliares

### 8.1 `cortex docs schema <doc-type>`

```bash
$ cortex docs schema adr
# imprime ADRFrontmatter schema
```

### 8.2 `cortex docs scaffold <doc-type>`

```bash
$ cortex docs scaffold adr > new-adr.md
# crea template con frontmatter pre-poblado
```

### 8.3 `cortex docs validate <path>`

```bash
$ cortex docs validate vault/decisions/ADR-007-foo.md
> OK: validates against ADRFrontmatter
```

### 8.4 `cortex docs convert`

```bash
$ cortex docs convert vault/notes/random.md --to architecture --dry-run
# preview de migracion de un archivo especifico a un doc_type forzado
```

---

## 9. Tests de migracion

```python
# tests/integration/documentation/test_migration.py

def test_migration_dry_run_no_writes(legacy_vault):
    """Dry-run doesn't modify files."""
    initial_hashes = {f: hash(f.read_bytes()) for f in legacy_vault.rglob("*.md")}
    migrate(legacy_vault, apply=False)
    final_hashes = {f: hash(f.read_bytes()) for f in legacy_vault.rglob("*.md")}
    assert initial_hashes == final_hashes

def test_migration_apply_changes_files(legacy_vault):
    """Apply writes new frontmatter."""

def test_migration_idempotent(legacy_vault):
    """Running twice -> second run is no-op."""

def test_migration_preserves_body(legacy_vault):
    """Body content unchanged after migration."""

def test_migration_preserves_legacy_fields(legacy_vault):
    """legacy_pr field retained."""

def test_migration_handles_no_frontmatter(legacy_vault_no_fm):
    """Notes without frontmatter get one prepended."""

def test_migration_classifies_by_path(legacy_vault):
    """Path-based classification correct."""

def test_migration_reports_unclassifiable(legacy_vault_with_random):
    """Random files reported as UNCLASSIFIABLE."""

def test_migration_reindexes_after(legacy_vault):
    """After migration, vault index is fresh."""

def test_migration_creates_backup(legacy_vault):
    """Backup file exists after apply."""
```

---

## 10. Riesgos y mitigaciones

| Riesgo | Mitigacion |
|---|---|
| Migracion borra campos legacy desconocidos | `--preserve-legacy=true` default; campos van con prefijo `legacy_` |
| Re-ejecucion duplica | Idempotencia via `schema_version` check |
| Bug en migracion corrompe vault | Backup automatico antes de cada apply |
| Notas unclassifiable bloquean | Reportar y saltar, no abortar |
| `created_at` inferido equivocado | Fallback en cascada: date -> mtime; reportar source |
| Embedding cache desactualizado tras migracion | Reindexacion automatica al final |
| Frontmatter conflictivo no resoluble | Reportar para review manual |
| Body con triple-dash falsa | Skip frontmatter parser robusto (`yaml.SafeLoader`) |
| Migration de vault gigante OOM | Stream-based, no load all in memory |

---

## 11. Performance

| Operacion | Esperado |
|---|---|
| Migration dry-run 1000 notas | < 5s |
| Migration apply 1000 notas | < 30s (con re-index) |
| Migration apply 10000 notas | < 5 min |
| Backup tar.gz 1000 notas | < 10s |
| Restore 1000 notas | < 20s |

---

## 12. Plan de adopcion

### 12.1 Pre-Fase 11

- Codigo de migracion implementado y testeado.
- Backups verificados.
- Dry-run en vaults de prueba (legacy fixtures).

### 12.2 Fase 11 sobre vault de Cortex

1. Snapshot del vault actual (`git stash` + tar backup).
2. `cortex docs migrate --report-only`: ver scope.
3. `cortex docs migrate`: dry-run.
4. Review del diff.
5. `cortex docs migrate --apply`: aplicar.
6. `cortex docs validate --all`: verificar 0% drift.
7. `git diff vault/`: inspeccionar cambios.
8. Commit con mensaje "feat(docs): migrate vault to canonical schema".

### 12.3 Post-Fase 11

- Documenter agente actualizado solo escribe schema nuevo.
- Hook pre-commit valida frontmatter.
- Carpetas muertas eliminadas (Fase 12).

---

## 13. Decisiones clave

1. **Dry-run default, apply explicito:** evitar accidentes.
2. **Backup automatico:** siempre, no opcional.
3. **Idempotencia via `schema_version`:** simple, robusta.
4. **Preserve legacy fields:** sin perder datos, audibles.
5. **Reportar unclassifiable, no abortar:** progreso parcial es valido.
6. **Reindexacion automatica al final:** consistencia garantizada.
7. **Comando separado para enterprise:** logica adicional no contamina el local.
