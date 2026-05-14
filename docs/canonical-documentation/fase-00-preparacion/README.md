# Fase 00 - Preparacion

**Fuente:** `docs/canonical-documentation/README.md`
**Estado:** Completada (2026-05-14) - ver [`REALIZACION.md`](REALIZACION.md)
**Esfuerzo estimado:** 0.5 dia (real: ~1 hora)
**Riesgo:** bajo
**Dependencias:** ninguna

---

## 1. Objetivo

Crear el scaffolding del modulo `cortex/documentation/`, helpers compartidos (fingerprint, slug, YAML safe), inventario del estado actual, y configuracion base. No introduce comportamiento que altere el sistema actual.

Esta fase establece los cimientos para que las siguientes 12 fases puedan construir encima sin redescubrir constantes ni utilities.

---

## 2. Archivos a crear

```text
cortex/documentation/
    __init__.py
    errors.py
    common.py                # helpers: slugify, fingerprint, yaml_dump_safe
    inventory.py             # NUEVO: escaneo del vault para diagnostico

tests/unit/documentation/
    __init__.py
    test_common.py
    test_inventory.py
    test_errors.py

docs/canonical-documentation/fase-00-preparacion/
    REALIZACION.md           # se completa AL FINAL de ejecutar la fase
```

---

## 3. Responsabilidades

### `errors.py`

Errores base de la jerarquia del modulo.

```python
class DocumentationError(Exception):
    """Base error for cortex.documentation."""

class SchemaValidationError(DocumentationError):
    """Frontmatter does not validate against schema."""

class UnknownDocTypeError(DocumentationError):
    """doc_type value is not in DocType enum."""

class RoutingError(DocumentationError):
    """RouteSpec resolution or path rendering failed."""

class DuplicateDocumentError(DocumentationError):
    """Document already exists at target path and overwrite=False."""

class TemplateRenderError(DocumentationError):
    """Jinja2 template render failed."""
```

### `common.py`

Helpers compartidos por todas las fases.

```python
def slugify(value: str) -> str:
    """Convert a string to a filesystem-safe slug.

    - Lowercase
    - Strip non-alphanumeric except dash and space
    - Replace spaces/underscores with dash
    - Collapse repeated dashes
    """


def compute_fingerprint(content: str) -> str:
    """SHA-256 hex digest of content. 64 chars."""


def yaml_dump_safe(data: dict) -> str:
    """Dump dict to YAML with safe defaults.

    - default_flow_style=False
    - allow_unicode=True
    - sort_keys=False (preserve insertion order)
    """


def yaml_load_safe(text: str) -> dict:
    """Parse YAML safely. Returns empty dict for empty input."""


def parse_frontmatter_lenient(path: Path) -> dict:
    """Parse frontmatter without strict schema validation.

    Returns the raw dict. Used by migration tooling.
    Returns empty dict if no frontmatter present.
    """


def split_frontmatter_and_body(content: str) -> tuple[str, str]:
    """Split markdown content into (frontmatter_yaml, body).

    If no frontmatter, returns ("", content).
    """


def has_frontmatter(content: str) -> bool:
    """True if content starts with '---\n...\n---'."""
```

### `inventory.py`

Escanea el vault actual para diagnostico. Sirve a la migracion y a metricas.

```python
@dataclass
class VaultInventory:
    total_files: int
    by_subfolder: dict[str, int]
    with_frontmatter: int
    without_frontmatter: int
    with_schema_version_1: int
    classifiable: int          # path matches a known DocType
    unclassifiable: list[str]  # paths
    legacy_frontmatter_keys: dict[str, int]  # key -> count


def inventory_vault(vault_path: Path) -> VaultInventory:
    """Scan vault and produce inventory."""


def classify_path(path: Path, vault_root: Path) -> str | None:
    """Return inferred doc_type slug or None.

    Mapping:
        sessions/  -> 'session'
        decisions/<ADR-*>  -> 'adr'
        decisions/<other>  -> 'decision'
        runbooks/  -> 'runbook'
        incidents/  -> 'incident'
        postmortems/  -> 'postmortem'
        architecture/  -> 'architecture'
        specs/  -> 'spec'
        hu/  -> 'hu'
        changelog/  -> 'changelog'
        glossary/  -> 'glossary'
        handoffs/  -> 'handoff'
        else  -> None
    """
```

### `__init__.py`

Expone la API publica del modulo.

```python
from cortex.documentation.errors import (
    DocumentationError,
    SchemaValidationError,
    UnknownDocTypeError,
    RoutingError,
    DuplicateDocumentError,
    TemplateRenderError,
)
from cortex.documentation.common import (
    slugify,
    compute_fingerprint,
    yaml_dump_safe,
    yaml_load_safe,
    parse_frontmatter_lenient,
    split_frontmatter_and_body,
    has_frontmatter,
)
from cortex.documentation.inventory import (
    inventory_vault,
    classify_path,
    VaultInventory,
)

__all__ = [
    "DocumentationError",
    "SchemaValidationError",
    "UnknownDocTypeError",
    "RoutingError",
    "DuplicateDocumentError",
    "TemplateRenderError",
    "slugify",
    "compute_fingerprint",
    "yaml_dump_safe",
    "yaml_load_safe",
    "parse_frontmatter_lenient",
    "split_frontmatter_and_body",
    "has_frontmatter",
    "inventory_vault",
    "classify_path",
    "VaultInventory",
]
```

---

## 4. Criterios de diseno

- **No importar de `cortex.semantic`** ni de `cortex.context_enricher` (separacion de capas).
- **No depender de pydantic** (eso entra en Fase 01).
- **Funciones puras** donde se pueda: `slugify`, `compute_fingerprint`, `yaml_dump_safe`.
- **Sin side effects en imports.** El modulo se importa sin tocar disco.

---

## 5. Tests obligatorios

```python
# tests/unit/documentation/test_common.py

def test_slugify_basic():
    assert slugify("Hello World") == "hello-world"

def test_slugify_special_chars():
    assert slugify("Hello! World? Foo&Bar") == "hello-world-foobar"

def test_slugify_unicode():
    assert slugify("Cafe & Sueño") == "cafe-sueno"  # acentos removidos

def test_slugify_empty_returns_dash():
    assert slugify("") == ""

def test_slugify_only_special_chars():
    assert slugify("!@#$%") == ""

def test_compute_fingerprint_deterministic():
    fp1 = compute_fingerprint("test content")
    fp2 = compute_fingerprint("test content")
    assert fp1 == fp2
    assert len(fp1) == 64

def test_compute_fingerprint_different_content():
    fp1 = compute_fingerprint("a")
    fp2 = compute_fingerprint("b")
    assert fp1 != fp2

def test_compute_fingerprint_handles_unicode():
    fp = compute_fingerprint("Cafe ñu")
    assert len(fp) == 64

def test_yaml_dump_safe_basic():
    out = yaml_dump_safe({"title": "Foo", "tags": ["a", "b"]})
    assert "title: Foo" in out
    assert "- a" in out

def test_yaml_dump_safe_preserves_order():
    """Insertion order preserved in output."""
    out = yaml_dump_safe({"z": 1, "a": 2, "m": 3})
    lines = out.strip().split("\n")
    assert lines[0].startswith("z:")
    assert lines[1].startswith("a:")
    assert lines[2].startswith("m:")

def test_yaml_load_safe_empty():
    assert yaml_load_safe("") == {}
    assert yaml_load_safe("   ") == {}

def test_yaml_load_safe_basic():
    assert yaml_load_safe("title: Foo\ntags: [a, b]") == {"title": "Foo", "tags": ["a", "b"]}

def test_split_frontmatter_basic():
    content = "---\ntitle: Foo\n---\nBody"
    fm, body = split_frontmatter_and_body(content)
    assert "title: Foo" in fm
    assert body.strip() == "Body"

def test_split_frontmatter_none():
    fm, body = split_frontmatter_and_body("Just body")
    assert fm == ""
    assert body == "Just body"

def test_has_frontmatter_true():
    assert has_frontmatter("---\nkey: val\n---\nbody")

def test_has_frontmatter_false():
    assert not has_frontmatter("Just body")

def test_parse_frontmatter_lenient_handles_malformed(tmp_path):
    """Returns empty dict if YAML is malformed."""
    p = tmp_path / "bad.md"
    p.write_text("---\nbad yaml: [\n---\nbody")
    assert parse_frontmatter_lenient(p) == {}


# tests/unit/documentation/test_inventory.py

def test_inventory_empty_vault(tmp_path):
    inv = inventory_vault(tmp_path)
    assert inv.total_files == 0

def test_inventory_counts_md_files(tmp_vault_with_notes):
    inv = inventory_vault(tmp_vault_with_notes)
    assert inv.total_files == 5

def test_inventory_groups_by_subfolder(tmp_vault_with_notes):
    inv = inventory_vault(tmp_vault_with_notes)
    assert inv.by_subfolder["sessions"] == 3
    assert inv.by_subfolder["decisions"] == 2

def test_classify_path_session():
    p = Path("/v/vault/sessions/2026-01-01_foo.md")
    assert classify_path(p, Path("/v/vault")) == "session"

def test_classify_path_adr():
    p = Path("/v/vault/decisions/ADR-007-foo.md")
    assert classify_path(p, Path("/v/vault")) == "adr"

def test_classify_path_decision_non_adr():
    p = Path("/v/vault/decisions/DEC-2026-05-14-foo.md")
    assert classify_path(p, Path("/v/vault")) == "decision"

def test_classify_path_unknown_returns_none():
    p = Path("/v/vault/random/x.md")
    assert classify_path(p, Path("/v/vault")) is None

def test_inventory_marks_unclassifiable(tmp_vault_with_random):
    inv = inventory_vault(tmp_vault_with_random)
    assert len(inv.unclassifiable) > 0


# tests/unit/documentation/test_errors.py

def test_errors_inherit_from_documentation_error():
    assert issubclass(SchemaValidationError, DocumentationError)
    assert issubclass(UnknownDocTypeError, DocumentationError)
    assert issubclass(RoutingError, DocumentationError)
    assert issubclass(DuplicateDocumentError, DocumentationError)
    assert issubclass(TemplateRenderError, DocumentationError)

def test_errors_can_be_raised_and_caught():
    with pytest.raises(SchemaValidationError):
        raise SchemaValidationError("test")
```

---

## 6. Fixtures de test

```python
# tests/unit/documentation/conftest.py

@pytest.fixture
def tmp_vault_with_notes(tmp_path):
    """Create a vault with 5 notes across categories."""
    vault = tmp_path / "vault"
    (vault / "sessions").mkdir(parents=True)
    (vault / "decisions").mkdir(parents=True)
    for i in range(3):
        (vault / "sessions" / f"2026-04-{10+i:02d}_foo-{i}.md").write_text("body")
    for i in range(2):
        (vault / "decisions" / f"ADR-00{i+1}-foo.md").write_text("body")
    return vault


@pytest.fixture
def tmp_vault_with_random(tmp_path):
    vault = tmp_path / "vault"
    (vault / "random").mkdir(parents=True)
    (vault / "random" / "x.md").write_text("body")
    return vault
```

---

## 7. Checklist

- [x] `cortex/documentation/__init__.py` exporta API publica
- [x] `cortex/documentation/errors.py` define jerarquia de errores
- [x] `cortex/documentation/common.py` con 7 helpers
- [x] `cortex/documentation/inventory.py` con `inventory_vault` y `classify_path`
- [x] `tests/unit/documentation/test_common.py` >= 15 tests (25 implementados)
- [x] `tests/unit/documentation/test_inventory.py` >= 8 tests (14 implementados)
- [x] `tests/unit/documentation/test_errors.py` >= 2 tests (2 implementados)
- [x] Coverage del modulo `cortex/documentation/` >= 95% (96%)
- [x] `from cortex.documentation import *` no rompe
- [x] `pytest tests/unit/documentation` pasa al 100% (41/41)

---

## 8. Gate de salida

- `pytest tests/unit/documentation` pasa al 100%.
- Coverage >= 95% en `cortex/documentation/`.
- Modulo se importa sin side effects (`from cortex.documentation import *` no toca disco).
- Documento `REALIZACION.md` en esta carpeta con resumen de lo implementado.

---

## 9. Notas para agentes implementadores

1. **No anticipar Fase 01.** No crear `doc_type.py` ni schemas pydantic aqui.
2. **Funciones puras donde sea posible.** Facilita property-based tests.
3. **Tests primero.** Implementar test, luego funcion.
4. **Reusar `yaml.safe_dump`/`yaml.safe_load`** de PyYAML; no escribir parser custom.
5. **`slugify` debe manejar unicode correctamente.** Usar `unicodedata.normalize`.
6. **`compute_fingerprint` siempre sobre el body sin frontmatter.** Documentar en docstring.

---

## 10. Referencias

- `docs/canonical-documentation/data-model.md` - DocType y schemas (Fase 01)
- `docs/canonical-documentation/architecture.md` - Capa 1 y Capa 2
- `docs/canonical-documentation/migration-guide.md` - usa `inventory_vault` y `classify_path`
