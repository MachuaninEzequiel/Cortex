from __future__ import annotations

from pathlib import Path

import pytest

from cortex.enterprise.config import (
    build_enterprise_org_config,
    describe_enterprise_topology,
    load_enterprise_config,
    write_enterprise_config,
)


def test_build_enterprise_org_config_small_company_defaults() -> None:
    config = build_enterprise_org_config(project_name="Acme Platform")

    assert config.organization.slug == "acme-platform"
    assert config.organization.profile == "small-company"
    assert config.memory.enterprise_semantic_enabled is True
    assert config.memory.enterprise_episodic_enabled is False
    assert config.memory.project_memory_mode == "isolated"
    assert config.memory.retrieval_local_weight == 1.0
    assert config.memory.retrieval_enterprise_weight == 1.0
    assert config.governance.ci_profile == "advisory"


def test_load_enterprise_config_returns_none_when_missing(tmp_path: Path) -> None:
    assert load_enterprise_config(tmp_path) is None


def test_write_and_load_enterprise_config_roundtrip(tmp_path: Path) -> None:
    config = build_enterprise_org_config(project_name="Acme Platform", profile="multi-project-team")

    path = write_enterprise_config(tmp_path, config)
    loaded = load_enterprise_config(tmp_path, required=True)

    assert path.exists()
    assert loaded is not None
    assert loaded.organization.profile == "multi-project-team"
    assert loaded.resolve_enterprise_vault_path(tmp_path) == (tmp_path / "vault-enterprise").resolve()


def test_load_enterprise_config_rejects_invalid_cross_section_rules(tmp_path: Path) -> None:
    org_dir = tmp_path / ".cortex"
    org_dir.mkdir(parents=True)
    (org_dir / "org.yaml").write_text(
        "schema_version: 1\n"
        "organization:\n"
        "  name: Bad Org\n"
        "  profile: custom\n"
        "memory:\n"
        "  enterprise_semantic_enabled: false\n"
        "promotion:\n"
        "  enabled: true\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        load_enterprise_config(tmp_path, required=True)


def test_describe_enterprise_topology_mentions_project_only_when_missing() -> None:
    assert describe_enterprise_topology(None) == "project-only (no .cortex/org.yaml)"
