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
