"""Tests for EpisodicMemoryStore."""

from datetime import datetime


def test_add_memory(episodic_store):
    entry = episodic_store.add(
        content="Fixed login refresh token bug",
        memory_type="bugfix",
        tags=["auth", "login"],
        files=["auth.ts"],
    )
    assert entry.id.startswith("mem_")
    assert entry.memory_type == "bugfix"
    assert "auth" in entry.tags
    assert episodic_store.count() == 1


def test_delete_memory(episodic_store):
    entry = episodic_store.add(content="Temporary memory")
    assert episodic_store.count() == 1
    ok = episodic_store.delete(entry.id)
    assert ok is True
    assert episodic_store.count() == 0


def test_delete_nonexistent(episodic_store):
    ok = episodic_store.delete("mem_doesnotexist")
    assert ok is False


def test_search_empty_store(episodic_store):
    results = episodic_store.search("anything")
    assert results == []


def test_add_and_search(episodic_store):
    episodic_store.add(
        content="Deployed new auth middleware",
        memory_type="deployment",
        tags=["auth"],
    )
    episodic_store.add(content="Wrote unit tests for payment module", memory_type="testing")

    results = episodic_store.search("auth middleware", top_k=1)
    assert len(results) == 1
    assert results[0].entry.memory_type == "deployment"


def test_timestamp_preserved_on_retrieval(episodic_store):
    """Timestamps must survive serialization round-trip."""
    entry = episodic_store.add(content="Important event", memory_type="event")
    original_ts = entry.timestamp

    # Search returns a deserialized MemoryEntry
    results = episodic_store.search("important")
    assert len(results) == 1
    retrieved_ts = results[0].entry.timestamp

    assert retrieved_ts == original_ts
    assert isinstance(retrieved_ts, datetime)
    assert retrieved_ts.tzinfo is not None


def test_metadata_round_trip_preserves_entities_and_extra_fields(episodic_store):
    episodic_store.add(
        content="def login_user(token):\n    return token",
        memory_type="bugfix",
        extra_metadata={"ticket": "DX-1"},
    )

    results = episodic_store.search("login_user")

    assert len(results) == 1
    metadata = results[0].entry.metadata
    assert metadata["ticket"] == "DX-1"
    assert "login_user" in metadata["entities"]["function"]


def test_search_by_entity_returns_matching_memories(episodic_store):
    episodic_store.add(
        content="def login_user(token):\n    return token",
        memory_type="bugfix",
        files=["auth.py"],
    )
    episodic_store.add(
        content="def charge_card(amount):\n    return amount",
        memory_type="feature",
        files=["payments.py"],
    )

    results = episodic_store.search_by_entity("function", "login_user")

    assert len(results) == 1
    assert results[0].entry.files == ["auth.py"]


# ---------------------------------------------------------------------------
# Entity round-trip — comprehensive coverage of all 8 entity types
# ---------------------------------------------------------------------------
# Regression of release-2-known-weaknesses.md #1.
# Contract: every entity type that ``_extract_entities`` recognises must
# survive serialize → deserialize and be searchable via ``search_by_entity``.


import pytest


@pytest.mark.parametrize(
    ("entity_type", "expected_value", "content"),
    [
        ("function", "login_user", "def login_user(token):\n    return token"),
        ("class", "AuthMiddleware", "class AuthMiddleware:\n    pass"),
        (
            "endpoint",
            "/api/users",
            "@app.get('/api/users')\ndef list_users():\n    return []",
        ),
        (
            "config_key",
            "DATABASE_URL",
            "import os\nos.environ['DATABASE_URL']",
        ),
        (
            "dependency",
            "pathlib",
            "from pathlib import Path\nimport pathlib",
        ),
        ("variable", "user_token", "const user_token = getToken();"),
        ("constant", "MAX_RETRIES", "const MAX_RETRIES = 5;"),
    ],
)
def test_entity_round_trip_by_type(episodic_store, entity_type, expected_value, content):
    """Every entity type must survive serialize → deserialize."""
    episodic_store.add(content=content, memory_type="test")

    # 1. Round-trip via metadata: every entry retrieved via list_entries()
    #    must still carry the entity dict in metadata.
    entries = episodic_store.list_entries()
    assert entries, "No entries listed after add"
    entities = entries[0].metadata.get("entities", {})
    assert entity_type in entities, (
        f"Entity type {entity_type!r} missing after round-trip; "
        f"got keys: {sorted(entities.keys())}"
    )
    assert expected_value in entities[entity_type], (
        f"Value {expected_value!r} not found in {entity_type}; "
        f"got: {entities[entity_type]}"
    )

    # 2. search_by_entity must locate the memory by its entity index.
    hits = episodic_store.search_by_entity(entity_type, expected_value)
    assert hits, f"search_by_entity({entity_type}, {expected_value}) returned []"


def test_entity_round_trip_preserves_multiple_types_in_one_memory(episodic_store):
    """A memory with several entity types must keep all of them after round-trip."""
    content = (
        "from auth import login_user\n"
        "class AuthMiddleware:\n"
        "    pass\n"
        "@app.post('/api/login')\n"
        "def login_user(token):\n"
        "    return token\n"
    )
    episodic_store.add(content=content, memory_type="feature")

    entries = episodic_store.list_entries()
    assert entries, "Memory not retrievable after add"
    entities = entries[0].metadata.get("entities", {})

    assert "function" in entities and "login_user" in entities["function"]
    assert "class" in entities and "AuthMiddleware" in entities["class"]
    assert "endpoint" in entities and "/api/login" in entities["endpoint"]
    assert "dependency" in entities and "auth" in entities["dependency"]


def test_entity_round_trip_preserves_extra_metadata_alongside(episodic_store):
    """Entities and user-supplied extra_metadata must coexist after round-trip."""
    episodic_store.add(
        content="def charge_card(amount):\n    return amount",
        memory_type="feature",
        extra_metadata={"ticket": "PAY-42", "branch": "feature/billing"},
    )

    entries = episodic_store.list_entries()
    assert entries
    metadata = entries[0].metadata
    assert metadata["ticket"] == "PAY-42"
    assert metadata["branch"] == "feature/billing"
    assert "function" in metadata["entities"]
    assert "charge_card" in metadata["entities"]["function"]


def test_search_by_entity_filters_strictly(episodic_store):
    """``search_by_entity`` must not return unrelated memories."""
    episodic_store.add(
        content="class PaymentService:\n    pass", memory_type="feature"
    )
    episodic_store.add(
        content="class AuthService:\n    pass", memory_type="feature"
    )

    results = episodic_store.search_by_entity("class", "PaymentService")
    assert len(results) == 1
    assert "PaymentService" in results[0].entry.content
    assert "AuthService" not in results[0].entry.content
