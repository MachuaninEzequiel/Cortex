from __future__ import annotations

from pathlib import Path

from cortex.enterprise.knowledge_promotion import PromotionRepository
from cortex.enterprise.promotion_models import PromotionRecord


def test_promotion_repository_appends_and_loads_latest(tmp_path: Path) -> None:
    records_path = tmp_path / "vault-enterprise" / ".cortex" / "promotion" / "records.jsonl"
    repo = PromotionRepository(records_path)

    r1 = PromotionRecord(
        origin_id="proj:specs/a.md",
        local_rel_path="specs/a.md",
        doc_type="spec",
        dest_rel_path="specs/proj/a.md",
        fingerprint="abc",
        status="reviewed",
    )
    repo.append(r1)

    r2 = PromotionRecord(
        origin_id="proj:specs/a.md",
        local_rel_path="specs/a.md",
        doc_type="spec",
        dest_rel_path="specs/proj/a.md",
        fingerprint="abc",
        status="promoted",
    )
    repo.append(r2)

    latest = repo.load_latest_by_origin_id()
    assert latest["proj:specs/a.md"].status == "promoted"
    assert latest["proj:specs/a.md"].fingerprint == "abc"

