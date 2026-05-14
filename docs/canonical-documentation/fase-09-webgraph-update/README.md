# Fase 09 - Webgraph Update

**Fuente:** `docs/canonical-documentation/README.md`
**Estado:** Pendiente de ejecucion
**Esfuerzo estimado:** 1 dia
**Riesgo:** medio
**Dependencias:** Fase 01, Fase 02

---

## 1. Objetivo

Actualizar el webgraph para que:
- Nodos esten coloreados por `doc_type` segun `RouteSpec.webgraph_color`.
- Nodos tengan forma segun `RouteSpec.webgraph_shape`.
- Aristas distinguen por tipo (wiki-link, co-occurrence, typed graph).
- UI muestra leyenda visible.
- Filtros por DocType en la vista.

Esta fase hace VISIBLE la division en el webgraph, cumpliendo la motivacion original del usuario.

---

## 2. Archivos a tocar

```text
cortex/webgraph/
    semantic_source.py            # EXTENDIDO: incluir doc_type en nodos
    episodic_source.py            # EXTENDIDO: mismos campos
    builder.py                    # EXTENDIDO: tipar nodos por doc_type
    renderer.py                   # NUEVO o EXTENDIDO: color/shape config
    style.py                      # NUEVO: WebgraphStyle

cortex/webgraph/cache/
    # snapshots regeneran con doc_type metadata

cortex-pi/extensions/
    cortex-dashboard.ts           # EXTENDIDO: vista grupos por tipo

tests/unit/webgraph/
    test_semantic_source_doctype.py
    test_builder_typed_nodes.py
    test_style.py
```

---

## 3. Responsabilidades

### `style.py` (NUEVO)

```python
# cortex/webgraph/style.py
from dataclasses import dataclass
from cortex.documentation.doc_type import DocType
from cortex.documentation.routing import resolve_route


@dataclass(frozen=True)
class NodeStyle:
    color: str
    shape: str


def style_for_doc_type(doc_type: DocType | None) -> NodeStyle:
    """Get node style for a DocType. Returns default for None."""
    if doc_type is None:
        return NodeStyle(color="#cccccc", shape="ellipse")
    try:
        route = resolve_route(doc_type)
        return NodeStyle(color=route.webgraph_color, shape=route.webgraph_shape)
    except Exception:
        return NodeStyle(color="#cccccc", shape="ellipse")


EDGE_TYPES = {
    "wiki_link": {"color": "#666666", "style": "solid", "label": "links to"},
    "co_occurrence": {"color": "#aaaaaa", "style": "dashed", "label": "co-occurs"},
    "imports": {"color": "#88aaff", "style": "solid", "label": "imports"},
    "tested_by": {"color": "#88dd88", "style": "dotted", "label": "tested by"},
    "supersedes": {"color": "#dd6666", "style": "solid", "label": "supersedes"},
}
```

### Extension de nodos

```python
# cortex/webgraph/semantic_source.py - EXTENSION

def build_nodes(vault: VaultReader) -> list[dict]:
    nodes = []
    for rel_path, doc in vault.iter_documents():
        fm = doc.frontmatter or {}
        doc_type_str = fm.get("doc_type")
        doc_type = DocType(doc_type_str) if doc_type_str else None
        style = style_for_doc_type(doc_type)

        nodes.append({
            "id": rel_path,
            "label": doc.title,
            "doc_type": doc_type.value if doc_type else None,
            "status": fm.get("status"),
            "vault_scope": fm.get("vault_scope", "local"),
            "tags": fm.get("tags", []),
            "color": style.color,
            "shape": style.shape,
        })
    return nodes
```

### Aristas tipadas

```python
# cortex/webgraph/builder.py - EXTENSION

def build_edges(vault: VaultReader, episodic: EpisodicStore) -> list[dict]:
    edges = []
    # Wiki-links
    for rel_path, doc in vault.iter_documents():
        for link in doc.links:
            edges.append({
                "source": rel_path,
                "target": _resolve_link_target(link, vault),
                "type": "wiki_link",
                "color": EDGE_TYPES["wiki_link"]["color"],
                "style": EDGE_TYPES["wiki_link"]["style"],
            })

    # ADR supersedes
    for rel_path, doc in vault.iter_documents():
        fm = doc.frontmatter or {}
        if fm.get("doc_type") == "adr":
            for prev in fm.get("supersedes", []):
                edges.append({
                    "source": rel_path,
                    "target": f"decisions/{prev}.md",
                    "type": "supersedes",
                    ...
                })

    # Co-occurrence (existente)
    # Typed graph (existente)
    return edges
```

### Snapshot JSON

```json
// .cortex/webgraph/cache/snapshot-semantic.json - formato extendido
{
  "nodes": [
    {
      "id": "decisions/ADR-007-onnx.md",
      "label": "ADR-007: Use ONNX",
      "doc_type": "adr",
      "status": "accepted",
      "vault_scope": "local",
      "tags": ["embedding", "performance"],
      "color": "#cc66ff",
      "shape": "hexagon"
    },
    ...
  ],
  "edges": [
    {
      "source": "decisions/ADR-007-onnx.md",
      "target": "architecture/embedding-architecture.md",
      "type": "wiki_link",
      "color": "#666666",
      "style": "solid"
    },
    ...
  ],
  "legend": {
    "doc_types": [
      {"type": "adr", "color": "#cc66ff", "shape": "hexagon"},
      {"type": "runbook", "color": "#66cccc", "shape": "rectangle"},
      ...
    ],
    "edge_types": [
      {"type": "wiki_link", "color": "#666666"},
      ...
    ]
  }
}
```

### UI (cortex-pi dashboard)

```typescript
// cortex-pi/extensions/cortex-dashboard.ts - EXTENSION

// Leyenda visible
// Filtros por doc_type
// Tooltip con metadata
```

---

## 4. Tests

```python
# tests/unit/webgraph/test_semantic_source_doctype.py

def test_node_includes_doc_type(tmp_vault):
    write_adr_note(ADRData(...), vault=tmp_vault)
    nodes = build_nodes(tmp_vault)
    adr_node = next(n for n in nodes if n["doc_type"] == "adr")
    assert adr_node["color"] == "#cc66ff"
    assert adr_node["shape"] == "hexagon"

def test_node_default_for_unknown_doc_type(tmp_vault):
    """Legacy notes without doc_type get gray."""

def test_legend_has_all_doc_types(tmp_vault):
    """Generated legend includes all 12 DocTypes."""


# tests/unit/webgraph/test_builder_typed_nodes.py

def test_supersedes_edge_created(tmp_vault):
    """ADR with supersedes field creates 'supersedes' edge."""

def test_wiki_links_extracted_as_edges(tmp_vault):
    """[[link]] in body becomes wiki_link edge."""

def test_edges_have_color_per_type():
    """All edge types have color in EDGE_TYPES."""


# tests/unit/webgraph/test_style.py

def test_style_for_all_doc_types():
    """Each DocType has a style."""

def test_style_unknown_doc_type_default():
    """None doc_type returns gray default."""
```

---

## 5. Checklist

- [ ] `cortex/webgraph/style.py` con `style_for_doc_type` y `EDGE_TYPES`
- [ ] `cortex/webgraph/semantic_source.py` extendido (doc_type, status en nodos)
- [ ] `cortex/webgraph/episodic_source.py` analogo
- [ ] `cortex/webgraph/builder.py` con aristas tipadas
- [ ] Snapshot JSON con leyenda
- [ ] cortex-pi dashboard extension (visual)
- [ ] Tests >= 8

---

## 6. Gate de salida

- `pytest tests/unit/webgraph` pasa al 100%.
- Snapshot JSON contiene `legend` con 12 doc_types.
- Visual smoke test: dashboard muestra colores diferenciados.
- `REALIZACION.md` documentado.

---

## 7. Riesgos y mitigaciones

| Riesgo | Mitigacion |
|---|---|
| Notas sin doc_type aparecen grises | Por diseno; visible incentivo a backfill |
| UI requiere cambio backend pero no se traduce a frontend | Esperar Fase 11 para vault migrado; UI ya soporta el formato extendido |
| Snapshot grande | OK; webgraph cache se invalida selectivamente |
| Colores poco contrastantes | Verificar accesibilidad WCAG en review |
| Edges proliferan (N**2 con co-occurrence) | Limite max edges en builder |

---

## 8. Notas para agentes implementadores

1. **Empezar por `style.py`.** Sin esto el resto no compila.
2. **Snapshot JSON compatible con UI actual.** Solo agregar campos, no romper.
3. **Tests visuales son smoke.** Capturar screenshot en PR review.
4. **EDGE_TYPES extensible.** Documentar para Fase futura.

---

## 9. Referencias

- `docs/canonical-documentation/routing-table.md` - webgraph_color, webgraph_shape
- `cortex/webgraph/semantic_source.py` - base
- `cortex-pi/extensions/cortex-dashboard.ts` - UI
