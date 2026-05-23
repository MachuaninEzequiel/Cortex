"""Tests for :mod:`cortex.session.storage`.

Covers atomicity (tmp file does not survive), roundtrip exactness,
corrupted-file resilience, the active pointer lifecycle and edge cases.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from cortex.session import (
    Checkpoint,
    CheckpointSource,
    SessionMode,
    SessionRecord,
    SessionStatus,
)
from cortex.session.errors import (
    SessionAlreadyExists,
    SessionNotFound,
    SessionStorageCorrupted,
)
from cortex.session.storage import (
    ACTIVE_POINTER_FILENAME,
    SESSION_FILE_SUFFIX,
    SessionStorage,
)

VALID_SHA = "a" * 40


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def storage(tmp_path: Path) -> SessionStorage:
    return SessionStorage(tmp_path / "sessions")


def _make_open(session_id: str = "2026-05-16_demo") -> SessionRecord:
    return SessionRecord(
        session_id=session_id,
        spec_path=Path("vault/specs/demo.md"),
        spec_summary="demo",
        start_commit=VALID_SHA,
        start_branch="main",
        opened_at=datetime(2026, 5, 16, 10, tzinfo=UTC),
    )


def _make_closed(session_id: str = "2026-05-16_done") -> SessionRecord:
    return SessionRecord(
        session_id=session_id,
        spec_path=Path("vault/specs/done.md"),
        spec_summary="done",
        start_commit=VALID_SHA,
        start_branch="main",
        opened_at=datetime(2026, 5, 16, 10, tzinfo=UTC),
        status=SessionStatus.CLOSED,
        mode=SessionMode.BYO,
        closed_at=datetime(2026, 5, 16, 12, tzinfo=UTC),
        end_commit="b" * 40,
        documenter_decision=SessionStatus.CLOSED,
    )


# ---------------------------------------------------------------------------
# Save & load roundtrip
# ---------------------------------------------------------------------------


class TestSaveLoad:
    def test_save_creates_file_with_yaml_suffix(self, storage: SessionStorage) -> None:
        record = _make_open()
        path = storage.save(record)
        assert path.name == f"2026-05-16_demo{SESSION_FILE_SUFFIX}"
        assert path.is_file()

    def test_save_creates_parent_directory(self, tmp_path: Path) -> None:
        nested = tmp_path / "a" / "b" / "sessions"
        storage = SessionStorage(nested)
        storage.save(_make_open())
        assert nested.is_dir()

    def test_load_returns_equal_record_open(self, storage: SessionStorage) -> None:
        record = _make_open()
        storage.save(record)
        assert storage.load("2026-05-16_demo") == record

    def test_load_returns_equal_record_closed(self, storage: SessionStorage) -> None:
        record = _make_closed()
        storage.save(record)
        assert storage.load("2026-05-16_done") == record

    def test_load_preserves_checkpoints_and_verification(self, storage: SessionStorage) -> None:
        record = _make_open()
        record.checkpoints.append(
            Checkpoint(
                timestamp=datetime(2026, 5, 16, 10, 30, tzinfo=UTC),
                source=CheckpointSource.CORTEX_SDDWORK,
                verified_claims=["thing1", "thing2"],
                note="ok",
            )
        )
        storage.save(record)
        reloaded = storage.load("2026-05-16_demo")
        assert reloaded.checkpoints == record.checkpoints

    def test_save_overwrites_existing(self, storage: SessionStorage) -> None:
        record = _make_open()
        storage.save(record)
        record.spec_summary = "updated"
        storage.save(record)
        assert storage.load("2026-05-16_demo").spec_summary == "updated"

    def test_load_missing_raises_not_found(self, storage: SessionStorage) -> None:
        with pytest.raises(SessionNotFound):
            storage.load("2026-05-16_missing")

    def test_save_new_refuses_overwrite(self, storage: SessionStorage) -> None:
        storage.save(_make_open())
        with pytest.raises(SessionAlreadyExists):
            storage.save_new(_make_open())

    def test_save_new_creates_when_absent(self, storage: SessionStorage) -> None:
        path = storage.save_new(_make_open())
        assert path.is_file()


# ---------------------------------------------------------------------------
# Atomicity (no partial writes left behind)
# ---------------------------------------------------------------------------


class TestAtomicity:
    def test_save_does_not_leave_tmp_file(self, storage: SessionStorage) -> None:
        storage.save(_make_open())
        tmp_files = list(storage.root.glob("*.tmp"))
        assert tmp_files == []

    def test_consecutive_saves_do_not_corrupt(self, storage: SessionStorage) -> None:
        record = _make_open()
        for i in range(20):
            record.spec_summary = f"iteration {i}"
            storage.save(record)
        assert storage.load("2026-05-16_demo").spec_summary == "iteration 19"


# ---------------------------------------------------------------------------
# exists() and delete()
# ---------------------------------------------------------------------------


class TestExistsDelete:
    def test_exists_returns_false_when_dir_missing(self, tmp_path: Path) -> None:
        storage = SessionStorage(tmp_path / "nope")
        assert storage.exists("2026-05-16_x") is False

    def test_exists_true_after_save(self, storage: SessionStorage) -> None:
        storage.save(_make_open())
        assert storage.exists("2026-05-16_demo") is True

    def test_delete_removes_file(self, storage: SessionStorage) -> None:
        storage.save(_make_open())
        storage.delete("2026-05-16_demo")
        assert storage.exists("2026-05-16_demo") is False

    def test_delete_missing_raises(self, storage: SessionStorage) -> None:
        with pytest.raises(SessionNotFound):
            storage.delete("2026-05-16_missing")

    def test_delete_clears_active_pointer_if_pointed_there(self, storage: SessionStorage) -> None:
        storage.save(_make_open())
        storage.set_active_session_id("2026-05-16_demo")
        storage.delete("2026-05-16_demo")
        assert storage.get_active_session_id() is None

    def test_delete_keeps_active_pointer_when_pointing_elsewhere(
        self, storage: SessionStorage
    ) -> None:
        first = _make_open("2026-05-16_first")
        second = _make_open("2026-05-16_second")
        storage.save(first)
        storage.save(second)
        storage.set_active_session_id("2026-05-16_first")
        storage.delete("2026-05-16_second")
        assert storage.get_active_session_id() == "2026-05-16_first"


# ---------------------------------------------------------------------------
# list_all / list_by_status
# ---------------------------------------------------------------------------


class TestListing:
    def test_list_all_on_missing_dir_returns_empty(self, tmp_path: Path) -> None:
        storage = SessionStorage(tmp_path / "nope")
        assert storage.list_all() == []

    def test_list_all_returns_every_saved_record(self, storage: SessionStorage) -> None:
        storage.save(_make_open("2026-05-16_a"))
        storage.save(_make_open("2026-05-16_b"))
        storage.save(_make_closed("2026-05-16_c"))
        ids = sorted(r.session_id for r in storage.list_all())
        assert ids == ["2026-05-16_a", "2026-05-16_b", "2026-05-16_c"]

    def test_list_by_status_filters_correctly(self, storage: SessionStorage) -> None:
        storage.save(_make_open("2026-05-16_a"))
        storage.save(_make_open("2026-05-16_b"))
        storage.save(_make_closed("2026-05-16_c"))
        opens = storage.list_by_status(SessionStatus.OPEN)
        closeds = storage.list_by_status(SessionStatus.CLOSED)
        assert {r.session_id for r in opens} == {"2026-05-16_a", "2026-05-16_b"}
        assert {r.session_id for r in closeds} == {"2026-05-16_c"}

    def test_list_all_skips_corrupted_files(
        self, storage: SessionStorage, caplog: pytest.LogCaptureFixture
    ) -> None:
        storage.save(_make_open("2026-05-16_ok"))
        # Inject a corrupted YAML file directly.
        corrupted = storage.root / f"2026-05-16_bad{SESSION_FILE_SUFFIX}"
        corrupted.write_text("not: [valid", encoding="utf-8")
        with caplog.at_level(logging.WARNING, logger="cortex.session.storage"):
            records = storage.list_all()
        ids = [r.session_id for r in records]
        assert ids == ["2026-05-16_ok"]
        assert any("corrupted" in rec.message.lower() for rec in caplog.records)

    def test_list_all_skips_schema_violations(
        self, storage: SessionStorage, caplog: pytest.LogCaptureFixture
    ) -> None:
        # Valid YAML but missing required fields.
        bad = storage.root / f"2026-05-16_bad{SESSION_FILE_SUFFIX}"
        storage.root.mkdir(parents=True, exist_ok=True)
        bad.write_text(yaml.safe_dump({"session_id": "x"}), encoding="utf-8")
        with caplog.at_level(logging.WARNING, logger="cortex.session.storage"):
            records = storage.list_all()
        assert records == []
        assert caplog.records, "expected a warning for the malformed session"


# ---------------------------------------------------------------------------
# Active pointer
# ---------------------------------------------------------------------------


class TestActivePointer:
    def test_returns_none_when_pointer_absent(self, storage: SessionStorage) -> None:
        assert storage.get_active_session_id() is None

    def test_set_then_get(self, storage: SessionStorage) -> None:
        storage.set_active_session_id("2026-05-16_x")
        assert storage.get_active_session_id() == "2026-05-16_x"
        assert (storage.root / ACTIVE_POINTER_FILENAME).is_file()

    def test_set_to_none_clears(self, storage: SessionStorage) -> None:
        storage.set_active_session_id("2026-05-16_x")
        storage.set_active_session_id(None)
        assert storage.get_active_session_id() is None
        assert not (storage.root / ACTIVE_POINTER_FILENAME).exists()

    def test_set_to_none_is_idempotent(self, storage: SessionStorage) -> None:
        # Should not raise on repeated clears.
        storage.set_active_session_id(None)
        storage.set_active_session_id(None)
        assert storage.get_active_session_id() is None

    def test_overwriting_pointer(self, storage: SessionStorage) -> None:
        storage.set_active_session_id("2026-05-16_a")
        storage.set_active_session_id("2026-05-16_b")
        assert storage.get_active_session_id() == "2026-05-16_b"

    def test_empty_pointer_file_treated_as_unset(self, storage: SessionStorage) -> None:
        storage.set_active_session_id("2026-05-16_x")
        # Manually blank the file (simulating user editing).
        (storage.root / ACTIVE_POINTER_FILENAME).write_text("", encoding="utf-8")
        assert storage.get_active_session_id() is None


# ---------------------------------------------------------------------------
# Corrupted load path
# ---------------------------------------------------------------------------


class TestLoadCorrupted:
    def test_load_corrupted_yaml_raises(self, storage: SessionStorage) -> None:
        storage.root.mkdir(parents=True, exist_ok=True)
        path = storage.root / f"2026-05-16_bad{SESSION_FILE_SUFFIX}"
        path.write_text("not: [valid", encoding="utf-8")
        with pytest.raises(SessionStorageCorrupted, match="invalid YAML"):
            storage.load("2026-05-16_bad")

    def test_load_non_mapping_root_raises(self, storage: SessionStorage) -> None:
        storage.root.mkdir(parents=True, exist_ok=True)
        path = storage.root / f"2026-05-16_list{SESSION_FILE_SUFFIX}"
        path.write_text("- a\n- b\n", encoding="utf-8")
        with pytest.raises(SessionStorageCorrupted, match="mapping"):
            storage.load("2026-05-16_list")
