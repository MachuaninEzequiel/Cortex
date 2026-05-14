# Fase 02 - Routing Table

**Fuente:** `docs/canonical-documentation/README.md`
**Estado:** Completada (2026-05-14) - ver [`REALIZACION.md`](REALIZACION.md)
**Esfuerzo estimado:** 0.5 dia (real: ~1 hora)
**Riesgo:** bajo
**Dependencias:** Fase 01

---

## 1. Objetivo

Implementar la **Capa 3 (Routing canonico)**:
- `RouteSpec` dataclass.
- Tabla `DOC_TYPE_ROUTING` con 12 entradas.
- Operaciones publicas: `resolve_route`, `render_filename`, `resolve_target_path`.
- CLI helper `cortex docs routing-table` para inspeccion.

No incluye los writers (Fase 03) ni los templates (Fase 03).

---

## 2. Archivos a crear

```text
cortex/documentation/
    routing.py               # RouteSpec + DOC_TYPE_ROUTING + helpers

cortex/cli/
    docs_subcommand.py       # NUEVO: subcomando 'cortex docs ...' (skeleton)

tests/unit/documentation/
    test_routing.py
    test_routing_cli.py
```

---

## 3. Responsabilidades

### `routing.py`

Contenido completo en `docs/canonical-documentation/routing-table.md`. Resumen:

```python
@dataclass(frozen=True)
class RouteSpec:
    doc_type: DocType
    subfolder: str
    filename_template: str
    template_path: Path
    writer: Callable | None = None  # None hasta Fase 03
    indexer: str = "auto"
    promotable: bool = False
    promotion_mode: str = "as-is"
    enterprise_subfolder: str | None = None
    retrieval_boost_per_intent: dict[str, float] = field(default_factory=dict)
    chunking_enabled: bool = True
    chunking_min_words: int = 500
    chunking_boundary: str = "h2"
    webgraph_color: str = "gray"
    webgraph_shape: str = "rectangle"
    requires_review_before_publish: bool = False
    auto_expire_days: int = 0


DOC_TYPE_ROUTING: dict[DocType, RouteSpec] = { ... 12 entries ... }


def resolve_route(doc_type: DocType) -> RouteSpec:
    """Get route. Raises UnknownDocTypeError if missing."""


def render_filename(spec: RouteSpec, context: dict) -> str:
    """Render filename_template with context dict.

    Raises RoutingError if a placeholder is unresolved.
    """


def resolve_target_path(
    spec: RouteSpec,
    context: dict,
    vault_root: Path,
    vault_scope: str = "local",
    project_id: str | None = None,
) -> Path:
    """Resolve full target path.

    For vault_scope='local': uses spec.subfolder.
    For vault_scope='enterprise': uses spec.enterprise_subfolder with project_id sub.

    Raises RoutingError if enterprise without enterprise_subfolder or project_id.
    """


def list_all_routes() -> list[RouteSpec]:
    """Return all RouteSpecs from DOC_TYPE_ROUTING."""


def routes_by_subfolder() -> dict[str, list[RouteSpec]]:
    """Inverse: subfolder -> list of RouteSpecs (decisions has 2: ADR + DECISION)."""
```

Notas:
- `writer` queda como `None` en esta fase; se asigna en Fase 03.
- `template_path` apunta a archivos `.md.j2` que aun no existen; los tests usan paths sin validar existencia hasta Fase 03.

### `cortex/cli/docs_subcommand.py`

Skeleton del subcomando `cortex docs`:

```python
import typer

app = typer.Typer(help="Documentation system commands.")


@app.command()
def routing_table(
    doc_type: str | None = typer.Option(None, "--doc-type"),
    json_output: bool = typer.Option(False, "--json"),
):
    """Print the routing table."""
    from cortex.documentation.routing import list_all_routes, resolve_route
    if doc_type:
        spec = resolve_route(DocType(doc_type))
        # imprimir spec
    else:
        for spec in list_all_routes():
            # imprimir cada uno
            ...


@app.command()
def schema(doc_type: str):
    """Print schema for a doc_type. (Fase 01 lo provee)."""
    ...


# Otros comandos (validate, scaffold, migrate, etc) en fases posteriores.
```

Registrar en `cortex/cli/main.py`:

```python
from cortex.cli.docs_subcommand import app as docs_app
app.add_typer(docs_app, name="docs")
```

---

## 4. Tests obligatorios

### `test_routing.py`

```python
def test_all_doc_types_in_routing_table()  # los 12
def test_resolve_route_returns_correct_spec()
def test_resolve_route_unknown_raises()
def test_render_filename_adr()
def test_render_filename_session()
def test_render_filename_missing_placeholder_raises()
def test_render_filename_extra_placeholders_ignored()
def test_resolve_target_path_local()
def test_resolve_target_path_enterprise()
def test_resolve_target_path_enterprise_without_project_id_raises()
def test_resolve_target_path_enterprise_no_enterprise_subfolder_raises()
def test_glossary_no_project_namespacing_in_enterprise()
def test_hu_not_promotable()
def test_handoff_not_promotable()
def test_list_all_routes_returns_12()
def test_routes_by_subfolder_groups_correctly()
def test_decisions_subfolder_has_adr_and_decision()
def test_retrieval_boost_per_intent_present_for_adr()
```

### `test_routing_cli.py`

```python
def test_cli_routing_table_prints_all()
def test_cli_routing_table_filters_by_doc_type()
def test_cli_routing_table_json_output()
```

---

## 5. Criterios de diseno

- **`RouteSpec` es frozen.** Tabla immutable.
- **Writers en `None` por ahora.** Se asignan en Fase 03 mediante reasignacion explicita.
- **`template_path` puede no existir aun.** Tests no validan existencia hasta Fase 03.
- **`render_filename` usa `str.format`,** no Jinja.
- **`resolve_target_path` no crea directorios.** Solo computa el path.

---

## 6. Validacion estatica

Test que verifica que toda DocType tiene entrada:

```python
def test_all_doc_types_in_routing_table():
    missing = [dt for dt in DocType if dt not in DOC_TYPE_ROUTING]
    assert not missing, f"Missing routes for: {missing}"
```

Test que verifica nombres de subfolder unicos (salvo `decisions/`):

```python
def test_subfolders_mostly_unique():
    subfolders = [spec.subfolder for spec in DOC_TYPE_ROUTING.values()]
    duplicates = [s for s in subfolders if subfolders.count(s) > 1]
    # solo 'decisions' debe duplicar (ADR + DECISION)
    assert set(duplicates) == {"decisions"}
```

---

## 7. Checklist

- [x] `cortex/documentation/routing.py` con `RouteSpec`, tabla, y helpers
- [x] Tabla `DOC_TYPE_ROUTING` con 12 entradas
- [x] `cortex/cli/docs_subcommand.py` con `routing-table` subcomando
- [x] Registracion en `cortex/cli/main.py`
- [x] `tests/unit/documentation/test_routing.py` >= 18 tests (32 implementados)
- [x] `tests/unit/documentation/test_routing_cli.py` >= 3 tests (4 implementados)
- [x] Coverage >= 90% (99%)
- [x] `cortex docs routing-table` funciona en CLI

---

## 8. Gate de salida

- `pytest tests/unit/documentation/test_routing.py tests/unit/documentation/test_routing_cli.py` pasa al 100%.
- `cortex docs routing-table` muestra los 12 tipos.
- `cortex docs routing-table --doc-type adr --json` retorna JSON valido.
- Test estatico verifica que TODOS los DocType tienen entrada.
- `REALIZACION.md` documentado.

---

## 9. Riesgos y mitigaciones

| Riesgo | Mitigacion |
|---|---|
| Writer = None confunde a tests | Tests aceptan None; Fase 03 los asigna |
| Template_path apunta a archivos no existentes | Tests no chequean existencia hasta Fase 03 |
| Tabla crece a mas de 12 sin coordinar | Test estatico cuenta exacto 12 |
| CLI rompe comando existente | Subcomando aislado bajo `docs`; cero impacto en root |

---

## 10. Notas para agentes implementadores

1. **No agregar logica condicional sobre DocType.** Todo va en la tabla.
2. **`writer=None` por ahora.** Es legal.
3. **No crear archivos `.md.j2`.** Eso es Fase 03.
4. **Tests deben verificar TODOS los DocType.** No solo un par.
5. **`cortex docs` subcomando se crea limpio.** Aun no tiene mucho contenido; ira creciendo.

---

## 11. Referencias

- `docs/canonical-documentation/routing-table.md` - tabla completa con todos los campos
- `docs/canonical-documentation/architecture.md` - Capa 3
