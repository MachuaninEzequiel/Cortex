from __future__ import annotations

from typing import Any

import typer

from cortex.enterprise.config import list_enterprise_presets


def run_enterprise_wizard() -> tuple[str, dict[str, Any]]:
    typer.echo("🏢 Cortex Enterprise Setup Wizard")
    typer.echo("")
    presets = [p for p in list_enterprise_presets() if p != "custom"]
    for idx, preset in enumerate(presets, 1):
        typer.echo(f"  {idx}. {preset}")
    default_choice = "1"
    choice = typer.prompt("Select enterprise preset", default=default_choice)

    selected = presets[0]
    if choice.isdigit():
        index = int(choice) - 1
        if 0 <= index < len(presets):
            selected = presets[index]
    elif choice in presets:
        selected = choice

    org_name = typer.prompt("Organization name", default="")
    ci_profile = typer.prompt(
        "Governance CI profile (observability/advisory/enforced)",
        default="advisory",
    ).strip().lower()
    if ci_profile not in {"observability", "advisory", "enforced"}:
        ci_profile = "advisory"

    branch_isolation = typer.confirm("Enable branch isolation?", default=False)

    overrides: dict[str, Any] = {}
    if org_name:
        overrides["organization"] = {"name": org_name}
    overrides["governance"] = {"ci_profile": ci_profile}
    overrides["memory"] = {"branch_isolation_enabled": branch_isolation}
    return selected, overrides
