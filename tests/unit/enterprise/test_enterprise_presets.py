from __future__ import annotations

from pathlib import Path

import pytest

from cortex.setup.enterprise_presets import (
    load_org_config_overrides,
    resolve_enterprise_setup,
    validate_enterprise_preset,
)


def test_validate_enterprise_preset_accepts_known_profile() -> None:
    assert validate_enterprise_preset("small-company") == "small-company"


def test_validate_enterprise_preset_rejects_unknown_profile() -> None:
    with pytest.raises(ValueError):
        validate_enterprise_preset("unknown-profile")


def test_load_org_config_overrides_requires_mapping(tmp_path: Path) -> None:
    path = tmp_path / "org-overrides.yaml"
    path.write_text("- not-a-mapping\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_org_config_overrides(path)


def test_resolve_enterprise_setup_merges_overrides() -> None:
    result = resolve_enterprise_setup(
        project_name="Acme API",
        profile="small-company",
        overrides={"governance": {"ci_profile": "enforced"}},
    )
    assert result.profile == "small-company"
    assert result.overrides["governance"]["ci_profile"] == "enforced"
