# Testing Strategy - Estrategia de Tests por Capa

**Documento:** estrategia completa de tests
**Audiencia:** implementadores
**Estado:** especificacion normativa

---

## 1. Principios

1. **Cada archivo nuevo tiene test unitario correspondiente.** Sin excepciones.
2. **Cada capa tiene tests de integracion.** Capas individuales son testeables; el todo tambien.
3. **Cada fase tiene gate de tests.** Si no pasan, la fase no esta completa.
4. **Property-based tests donde aplican.** Hipotesis sobre invariantes (idempotencia, simetria) se testean con `hypothesis`.
5. **Performance tests en CI.** Cold start, hit rate, latencia: regresion se detecta automaticamente.
6. **Tests son documentacion ejecutable.** Un test bien nombrado explica el comportamiento esperado.

---

## 2. Niveles de test

### 2.1 Unit tests

**Ubicacion:** `tests/unit/documentation/`, `tests/unit/semantic/`, `tests/unit/context_enricher/`.

**Cobertura objetivo:** **>= 90%** del codigo nuevo, **>= 80%** del codigo modificado.

**Stack:** `pytest`, `pytest-cov`, `hypothesis` para property-based.

### 2.2 Integration tests

**Ubicacion:** `tests/integration/documentation/`.

**Cobertura:** flujos end-to-end de un writer (data -> persistencia -> indexacion -> retrieval).

**Stack:** `pytest` con fixtures que crean vault temporal.

### 2.3 E2E tests

**Ubicacion:** `tests/e2e/scenarios/`.

**Cobertura:** simulacion de uso real (agente IA escribiendo via MCP, retrieval inyectando contexto en prompt).

**Stack:** `pytest` con mocks de MCP server.

### 2.4 Performance tests

**Ubicacion:** `tests/performance/`.

**Cobertura:** cold start, latencia search, throughput de embedding.

**Stack:** `pytest-benchmark`.

### 2.5 Property tests

**Ubicacion:** integrados en unit/integration, marcados con `@hypothesis.given`.

**Cobertura:** invariantes (idempotencia, simetria, fingerprint determinism).

---

## 3. Tests por capa

### 3.1 Capa 1 - DocType

```python
# tests/unit/documentation/test_doc_type.py

def test_all_doc_types_have_string_value():
    for dt in DocType:
        assert isinstance(dt.value, str)
        assert len(dt.value) > 0

def test_doc_type_from_str_valid():
    assert doc_type_from_str("adr") == DocType.ADR

def test_doc_type_from_str_invalid():
    with pytest.raises(UnknownDocTypeError):
        doc_type_from_str("invalid")

def test_doc_type_from_path_session():
    assert doc_type_from_path(Path("vault/sessions/x.md")) == DocType.SESSION

def test_doc_type_from_path_adr():
    assert doc_type_from_path(Path("vault/decisions/ADR-007-x.md")) == DocType.ADR

def test_doc_type_from_path_decision_non_adr():
    assert doc_type_from_path(Path("vault/decisions/DEC-2026-x.md")) == DocType.DECISION

def test_doc_type_from_path_unknown_returns_none():
    assert doc_type_from_path(Path("vault/unknown/x.md")) is None

def test_promotable_doc_types_excludes_handoff_and_hu():
    promotable = promotable_doc_types()
    assert DocType.HANDOFF not in promotable
    assert DocType.HU not in promotable
    assert DocType.ADR in promotable

def test_doc_type_enum_count():
    """MVP es exactamente 12 tipos."""
    assert len(DocType) == 12
```

### 3.2 Capa 2 - Schema y validacion

```python
# tests/unit/documentation/test_schema_validation.py

def test_common_frontmatter_minimal_valid():
    fm = CommonFrontmatter(
        doc_type=DocType.SPEC,
        title="Test",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        status="draft",
        fingerprint="a"*64,
    )
    assert fm.schema_version == 1

def test_common_frontmatter_missing_doc_type_raises():
    with pytest.raises(SchemaValidationError):
        validate_frontmatter("title: foo\n")  # no doc_type

def test_common_frontmatter_invalid_status_raises():
    yaml = """
    doc_type: adr
    title: Test
    created_at: 2026-05-14T10:00:00Z
    updated_at: 2026-05-14T10:00:00Z
    status: invalid-status
    fingerprint: <64 chars hex>
    """
    with pytest.raises(SchemaValidationError):
        validate_frontmatter(yaml)

def test_enterprise_frontmatter_requires_owner():
    yaml = """
    doc_type: adr
    title: Test
    vault_scope: enterprise
    """  # missing owner, team, etc
    with pytest.raises(SchemaValidationError):
        validate_frontmatter(yaml)

def test_enterprise_frontmatter_full():
    """Valid enterprise frontmatter parses correctly."""
    # ... full enterprise frontmatter YAML
    fm = validate_frontmatter(yaml)
    assert isinstance(fm, EnterpriseFrontmatter)
    assert fm.owner == "ezequiel@cortex.ai"

def test_adr_frontmatter_validates_adr_number():
    """ADR requires adr_number >= 1."""

def test_incident_frontmatter_validates_severity():
    """severity must be in {low, medium, high, critical}."""

def test_updated_at_must_be_gte_created_at():
    """updated_at < created_at raises."""

def test_fingerprint_must_be_64_hex():
    """Fingerprint format strictly validated."""

@given(st.text(min_size=1, max_size=200))
def test_title_any_string_passes(title):
    """Any non-empty string is valid title."""
    # property-based test
```

### 3.3 Capa 3 - Routing

```python
# tests/unit/documentation/test_routing.py

def test_all_doc_types_in_routing_table():
    """Every DocType has an entry in DOC_TYPE_ROUTING."""
    for dt in DocType:
        assert dt in DOC_TYPE_ROUTING

def test_resolve_route_returns_correct_spec():
    spec = resolve_route(DocType.ADR)
    assert spec.doc_type == DocType.ADR
    assert spec.subfolder == "decisions"

def test_resolve_route_unknown_raises():
    # Bypass enum to simulate unknown
    with pytest.raises(UnknownDocTypeError):
        resolve_route(None)

def test_all_template_paths_exist():
    """Each route's template_path must exist on disk."""
    for spec in DOC_TYPE_ROUTING.values():
        assert spec.template_path.exists(), f"Missing template: {spec.template_path}"

def test_all_writers_are_callable():
    for spec in DOC_TYPE_ROUTING.values():
        assert callable(spec.writer)

def test_render_filename_adr():
    spec = resolve_route(DocType.ADR)
    name = render_filename(spec, {"number": 7, "slug": "foo"})
    assert name == "ADR-007-foo.md"

def test_render_filename_missing_placeholder():
    spec = resolve_route(DocType.ADR)
    with pytest.raises(RoutingError):
        render_filename(spec, {"slug": "foo"})  # missing number

def test_resolve_target_path_local():
    path = resolve_target_path(
        resolve_route(DocType.ADR),
        {"number": 7, "slug": "foo"},
        vault_root=Path("/tmp/vault"),
    )
    assert path == Path("/tmp/vault/decisions/ADR-007-foo.md")

def test_resolve_target_path_enterprise():
    path = resolve_target_path(
        resolve_route(DocType.ADR),
        {"number": 7, "slug": "foo"},
        vault_root=Path("/tmp/vault-enterprise"),
        vault_scope="enterprise",
        project_id="mi-proyecto",
    )
    assert path == Path("/tmp/vault-enterprise/decisions/mi-proyecto/ADR-007-foo.md")

def test_resolve_target_path_enterprise_without_project_id_raises():
    with pytest.raises(RoutingError):
        resolve_target_path(
            resolve_route(DocType.ADR),
            {"number": 7, "slug": "foo"},
            vault_root=Path("/tmp/vault"),
            vault_scope="enterprise",
            project_id=None,
        )

def test_glossary_no_project_namespacing():
    """Glossary's enterprise_subfolder has no {project_id}."""
    spec = resolve_route(DocType.GLOSSARY)
    assert "{project_id}" not in spec.enterprise_subfolder

def test_hu_not_promotable():
    """HU doesn't have enterprise_subfolder."""
    spec = resolve_route(DocType.HU)
    assert spec.enterprise_subfolder is None
    assert not spec.promotable
```

### 3.4 Capa 4 - Writers

Patron de tests por writer (aplicable a los 12):

```python
# tests/unit/documentation/test_write_adr_note.py

def test_write_adr_minimal(tmp_path, fake_vault):
    data = ADRData(
        title="Test ADR",
        context="ctx",
        decision="dec",
        consequences="cons",
        alternatives_considered=["a", "b"],
        adr_number=1,
    )
    path = write_adr_note(data, vault=fake_vault)
    assert path.exists()
    content = path.read_text()
    assert "## Decision" in content
    assert "doc_type: adr" in content

def test_write_adr_full(tmp_path, fake_vault):
    """All optional fields populated."""

def test_write_adr_missing_required_raises(fake_vault):
    """Empty title raises."""
    with pytest.raises(SchemaValidationError):
        write_adr_note(ADRData(title=""), vault=fake_vault)

def test_write_adr_enterprise_requires_owner(fake_vault):
    """Enterprise scope without owner raises."""
    data = ADRData(title="t", context="c", decision="d", consequences="cs", adr_number=1)
    with pytest.raises(SchemaValidationError):
        write_adr_note(data, vault=fake_vault, vault_scope="enterprise")

def test_write_adr_indexes_file(fake_vault):
    """After write, vault has indexed the file."""
    data = ADRData(...)
    path = write_adr_note(data, vault=fake_vault)
    rel = str(path.relative_to(fake_vault.path))
    assert rel in fake_vault._index

def test_write_adr_fingerprint_deterministic():
    """Same input -> same fingerprint."""

def test_write_adr_naming_pattern():
    """Filename follows ADR-NNN-slug pattern."""

def test_write_adr_duplicate_raises():
    """Writing twice with same number raises DuplicateDocumentError."""

def test_write_adr_audit_trail_on_enterprise():
    """Enterprise write adds 'created' audit event."""

@given(adr_data_strategy())  # hypothesis
def test_write_adr_roundtrip(data, fake_vault):
    """Writing then reading produces equivalent frontmatter."""
    path = write_adr_note(data, vault=fake_vault)
    fm = parse_frontmatter(path)
    assert fm.title == data.title
```

Esquema repetido para cada uno de los 12 writers.

### 3.5 Capa 4 - Templates

```python
# tests/unit/documentation/templates/test_adr_template.py

def test_adr_template_minimal():
    body = render_template("adr.md.j2", {
        "title": "T", "context": "c", "decision": "d",
        "alternatives_considered": [], "consequences": "cs",
        "supersedes": [],
    })
    assert "## Decision" in body
    assert "## Context" in body
    assert "## Supersedes" not in body  # empty list -> section omitted

def test_adr_template_full():
    body = render_template("adr.md.j2", {
        ...
        "supersedes": ["ADR-003"],
    })
    assert "## Supersedes" in body
    assert "[[ADR-003]]" in body

def test_adr_template_empty_alternatives_renders():
    """No error rendering empty alternatives list."""

def test_adr_template_jinja_safety():
    """No XSS / template injection via title."""
```

12 templates x ~4 tests = 48 tests minimo.

### 3.6 Capa 5 - Chunker

```python
# tests/unit/semantic/test_chunker.py

def test_short_doc_single_chunk():
    chunks = chunk_document(
        title="T", content="short content under 500 words",
        doc_type=DocType.ADR, tags=[], parent_path="x.md",
    )
    assert len(chunks) == 1
    assert chunks[0].section_title == "T"

def test_long_doc_multiple_chunks_h2():
    """3 H2 -> 3 chunks."""

def test_no_h2_returns_single_chunk_even_if_long():
    """1000 words con solo H3 y boundary=h2 -> 1 chunk."""

def test_h3_boundary_splits():
    """boundary='h3' splits on H3."""

def test_overlap_includes_trailing_words():
    """overlap_words=10 inyecta 10 palabras del chunk anterior."""

def test_embedding_text_includes_doc_type():
    chunks = chunk_document(..., doc_type=DocType.RUNBOOK, ...)
    assert "runbook" in chunks[0].embedding_text

def test_chunk_id_unique():
    """All chunks of same doc have unique chunk_id."""

def test_empty_section_handled():
    """H2 with empty body produces empty-text chunk."""

def test_prefix_text_before_first_h2():
    """Text before first H2 becomes (prefix) chunk."""

@given(st.text(min_size=100, max_size=10000))
def test_chunk_document_always_returns_at_least_one(content):
    chunks = chunk_document(
        title="T", content=content, doc_type=DocType.SPEC,
        tags=[], parent_path="x.md",
    )
    assert len(chunks) >= 1
```

### 3.7 Capa 5 - Vector Cache

```python
# tests/unit/semantic/test_vector_cache.py

def test_put_get_roundtrip(tmp_path):
    cache = VectorCache(tmp_path / "vectors")
    vec = np.random.rand(384).astype(np.float32)
    cache.put("fp1", "chunk1", vec)
    retrieved = cache.get("fp1")
    np.testing.assert_array_equal(retrieved, vec)

def test_miss_returns_none(tmp_path):
    cache = VectorCache(tmp_path / "vectors")
    assert cache.get("unknown") is None

def test_batch_put_get_consistent(tmp_path):
    """Batch ops match individual ops."""

def test_idempotent_put_no_growth(tmp_path):
    """Same fingerprint twice doesn't grow file."""

def test_invalidate(tmp_path):
    """Invalidate removes entry."""

def test_compact_reclaims_space(tmp_path):
    """Compact after invalidations reduces file size."""

def test_concurrent_reads(tmp_path):
    """Multiple readers via threading don't block."""

def test_atomic_writes_no_partial_state(tmp_path):
    """Process crash mid-write doesn't corrupt index."""

def test_persistence_across_restart(tmp_path):
    """Cache survives process restart."""

def test_schema_version_bump_invalidates_all(tmp_path):
    """Increasing schema_version invalidates all entries."""
```

### 3.8 Capa 6 - Filters

```python
# tests/unit/context_enricher/test_filters.py

def test_no_filters_passes_all():
    items = [_make_item(DocType.ADR), _make_item(DocType.RUNBOOK)]
    filtered = apply_filters(items, EnrichmentFilters())
    assert len(filtered) == 2

def test_doc_types_filter():
    items = [_make_item(DocType.ADR), _make_item(DocType.RUNBOOK)]
    filtered = apply_filters(items, EnrichmentFilters(doc_types=[DocType.ADR]))
    assert len(filtered) == 1
    assert filtered[0].doc_type == DocType.ADR

def test_strict_excludes_none_doc_type():
    items = [_make_item(None), _make_item(DocType.ADR)]
    filtered = apply_filters(
        items, EnrichmentFilters(doc_types=[DocType.ADR], strict=True)
    )
    assert len(filtered) == 1
    assert filtered[0].doc_type == DocType.ADR

def test_non_strict_keeps_none_doc_type():
    items = [_make_item(None), _make_item(DocType.ADR)]
    filtered = apply_filters(
        items, EnrichmentFilters(doc_types=[DocType.ADR], strict=False)
    )
    assert len(filtered) == 2

def test_tags_required_AND():
    """All required tags must match."""

def test_tags_any_of_OR():
    """Any of the tags is enough."""

def test_max_age_excludes_old():
    """Items older than max_age_days are excluded."""

def test_max_age_includes_no_date():
    """Items without date are not excluded by max_age."""

def test_vault_scope_local_only():
    """Only local items pass scope=local."""

def test_combined_filters_AND():
    """Multiple filters AND-composed."""
```

### 3.9 Capa 6 - Telemetria

```python
# tests/unit/context_enricher/test_telemetry.py

def test_record_enrichment_appends_jsonl(tmp_path):
    obs = PersistentObserver(tmp_path / "events.jsonl")
    ctx = _make_enriched_context()
    run_id = obs.record_enrichment(ctx, QueryIntent.SEMANTIC, None)
    assert (tmp_path / "events.jsonl").exists()
    events = [json.loads(l) for l in (tmp_path / "events.jsonl").read_text().splitlines()]
    assert events[0]["run_id"] == run_id

def test_record_citation_separate_event(tmp_path):
    """record_citation appends with different event_type."""

def test_aggregate_hit_rate(tmp_path):
    """aggregate() computes hit_rate correctly from events."""

def test_aggregate_by_type_breakdown(tmp_path):
    """aggregate breaks down by doc_type correctly."""

def test_telemetry_opt_out_via_config(tmp_path):
    """If disabled, no file written."""
```

---

## 4. Integration tests

### 4.1 Writer end-to-end

```python
# tests/integration/documentation/test_write_to_search.py

def test_write_adr_then_search(tmp_vault):
    """Write an ADR, then search retrieves it."""
    data = ADRData(title="ONNX backend", context="...", decision="adopt", ...)
    path = write_adr_note(data, vault=tmp_vault)

    results = tmp_vault.search("ONNX embedding", top_k=5)
    assert len(results) >= 1
    assert results[0].title == "ONNX backend"

def test_write_runbook_then_enrich(tmp_vault, enricher):
    """Write a runbook, then enricher includes it on relevant query."""
    write_runbook_note(RunbookData(title="Deploy procedure", ...), vault=tmp_vault)

    work = WorkContext(search_queries=["how to deploy"])
    ctx = enricher.enrich(work)
    runbook_items = [i for i in ctx.items if i.doc_type == DocType.RUNBOOK]
    assert len(runbook_items) >= 1
```

### 4.2 Routing integration

```python
def test_writer_uses_routing_table(tmp_vault):
    """Writer respects RouteSpec subfolder."""
    write_adr_note(ADRData(title="X", ...), vault=tmp_vault)
    decisions_dir = tmp_vault.path / "decisions"
    assert any(f.name.startswith("ADR-") for f in decisions_dir.iterdir())

def test_enterprise_writer_uses_enterprise_subfolder(tmp_vault):
    """Enterprise scope uses enterprise_subfolder."""
    write_adr_note(
        ADRData(title="X", owner="a@b.com", team="t", ...),
        vault=tmp_vault, vault_scope="enterprise", project_id="proj",
    )
    proj_dir = tmp_vault.path / "decisions" / "proj"
    assert any(f.name.startswith("ADR-") for f in proj_dir.iterdir())
```

### 4.3 Vectorization integration

```python
def test_chunker_with_real_vault(tmp_vault):
    """Long doc gets chunked, retrievable by section."""

def test_vector_cache_persists_across_restart(tmp_vault):
    """Restart vault, cache hits don't trigger re-embedding."""
```

### 4.4 Migration integration

```python
def test_migration_dry_run_no_writes(tmp_vault_legacy):
    """Dry-run produces diffs, doesn't modify files."""

def test_migration_idempotent(tmp_vault_legacy):
    """Running migrate twice doesn't change anything after the first."""

def test_migration_preserves_legacy_fields(tmp_vault_legacy):
    """legacy_date preserved after migration."""
```

---

## 5. E2E tests

```python
# tests/e2e/scenarios/test_documenter_flow.py

def test_agent_writes_session_via_mcp(mcp_server, fake_agent):
    """Agent invokes cortex_save_session, frontmatter is canonical."""

def test_agent_searches_with_filter(mcp_server, fake_agent):
    """Agent invokes cortex_search with doc_types filter."""

def test_full_session_with_telemetry(mcp_server, fake_agent, vault):
    """End-to-end: agent works, writes session, telemetry persisted."""

def test_promotion_to_enterprise(local_vault, enterprise_vault):
    """Promotion copies note with enterprise frontmatter."""
```

---

## 6. Performance tests

```python
# tests/performance/test_cold_start.py

@pytest.mark.benchmark
def test_cold_start_1000_notes_with_cache(benchmark, vault_1000_notes):
    """Cold start time with valid cache."""
    def cold_start():
        vault = VaultReader(vault_1000_notes.path)
        vault.search("test")
    benchmark(cold_start)
    assert benchmark.stats["mean"] < 0.1  # 100ms

@pytest.mark.benchmark
def test_cold_start_1000_notes_no_cache(benchmark, vault_1000_notes_no_cache):
    """Cold start time without cache (worst case)."""
    benchmark(cold_start)
    assert benchmark.stats["mean"] < 10.0  # 10s

# tests/performance/test_retrieval_latency.py

@pytest.mark.benchmark
def test_enrich_latency_p95(benchmark, vault_with_data, enricher):
    """Enrichment latency."""
    work = WorkContext(...)
    benchmark(lambda: enricher.enrich(work))
    assert benchmark.stats["p95"] < 0.5  # 500ms
```

---

## 7. Property-based tests

```python
# tests/property/test_writer_invariants.py
from hypothesis import given, strategies as st

@given(
    title=st.text(min_size=1, max_size=200),
    context=st.text(min_size=1, max_size=2000),
    decision=st.text(min_size=1, max_size=2000),
)
def test_adr_roundtrip_preserves_fields(title, context, decision):
    """Write ADR, read frontmatter, fields preserved."""
    data = ADRData(title=title, context=context, decision=decision, ...)
    path = write_adr_note(data, vault=fake_vault)
    fm = parse_frontmatter(path)
    assert fm.title == title

@given(content=st.text(min_size=100, max_size=10000))
def test_chunker_always_returns_chunks(content):
    """Any non-empty content produces at least one chunk."""
    chunks = chunk_document(title="T", content=content, ...)
    assert len(chunks) >= 1

@given(content=st.text(min_size=1, max_size=10000))
def test_fingerprint_deterministic(content):
    """Same content -> same fingerprint."""
    assert sha256(content) == sha256(content)
```

---

## 8. Fixtures compartidas

```python
# tests/conftest.py - EXTENSION

@pytest.fixture
def tmp_vault(tmp_path):
    vault_path = tmp_path / "vault"
    vault_path.mkdir()
    return VaultReader(vault_path)

@pytest.fixture
def vault_1000_notes(tmp_path):
    """Pre-populated vault with 1000 notes for performance tests."""
    # ... seed con 1000 notas variadas

@pytest.fixture
def enricher(tmp_vault):
    episodic = create_test_episodic_store()
    return ContextEnricher(episodic=episodic, semantic=tmp_vault)

@pytest.fixture
def adr_data_factory():
    def _factory(**overrides):
        defaults = dict(title="T", context="c", decision="d", consequences="cs",
                        alternatives_considered=["a"], adr_number=1)
        defaults.update(overrides)
        return ADRData(**defaults)
    return _factory
```

---

## 9. CI integration

### 9.1 GitHub Actions

```yaml
# .github/workflows/canonical-docs.yml
name: Canonical Documentation Tests
on: [push, pull_request]
jobs:
  unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -e .[dev]
      - run: pytest tests/unit/documentation tests/unit/semantic tests/unit/context_enricher
      - run: pytest tests/integration/documentation
  perf:
    runs-on: ubuntu-latest
    steps:
      - run: pytest tests/performance --benchmark-compare-fail=mean:5%
  e2e:
    runs-on: ubuntu-latest
    steps:
      - run: pytest tests/e2e/scenarios
```

### 9.2 Coverage gate

```toml
# pyproject.toml
[tool.coverage.report]
fail_under = 90  # bloquea merge si coverage < 90%
```

### 9.3 Schema validation gate

```yaml
# pre-commit hook
- id: cortex-docs-validate
  name: Validate vault frontmatter
  entry: cortex docs validate --all
  files: ^vault/.*\.md$
```

---

## 10. Tests por fase - gates

Cada fase tiene un gate de tests obligatorio antes de mergear:

| Fase | Tests minimos |
|---|---|
| 00 | smoke test del modulo |
| 01 | 30 tests (DocType, schemas, validator) |
| 02 | 15 tests (routing) |
| 03 | 12 writers x 8 tests + 12 templates x 4 tests = 144 tests |
| 04 | 10 tests (migracion writers existentes) + tests existentes pasan |
| 05 | 12 tests telemetria + 3 integration |
| 06 | 10 tests cache + 2 performance |
| 07 | 9 tests chunker + 3 integration + 1 performance |
| 08 | 15 tests filters + 5 tests boost + 3 tests presenter grouped |
| 09 | 5 tests webgraph + visual smoke |
| 10 | 20 tests enterprise (frontmatter, audit, promotion, retention) |
| 11 | 15 tests migration + 3 integration + dry-run validation |
| 12 | smoke test global |

Total esperado: **~280 tests nuevos** + tests existentes pasando.

---

## 11. Anti-patrones a evitar

1. **Tests que solo importan modulos** (smoke).
2. **Tests que duplican el codigo bajo test** (assertion = implementation).
3. **Tests que dependen del orden** (usar fixtures con setup correcto).
4. **Tests no deterministicos** (mock time, randomness).
5. **Tests E2E que tardan minutos** (mock externals).
6. **Tests que testean libraries de terceros** (yaml.safe_load).
7. **Mocks excesivos** que ocultan que el codigo no se ejecuta.
8. **Asserts ambiguos** (`assert result` -> mejor `assert result.success`).

---

## 12. Decisiones clave

1. **Coverage 90% es gate, no objetivo:** sin coverage no se mergea.
2. **Performance tests en CI:** regresion detectada automaticamente.
3. **Property-based para invariantes:** roundtrip, idempotencia, determinism.
4. **Fixtures compartidas:** tmp_vault, enricher, factories.
5. **Tests son documentacion:** nombrar tests con comportamiento esperado, no implementacion.
6. **Cada writer tiene ~8 tests minimo:** minimal, full, validation, persistence, indexing, fingerprint, naming, audit_trail.
