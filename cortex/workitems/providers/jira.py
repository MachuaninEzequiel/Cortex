"""
cortex.workitems.providers.jira
-------------------------------
Read-only Jira provider for importing external work items into Cortex.
"""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from cortex.workitems.models import TrackedItem, WorkItemKind, WorkItemSource
from cortex.workitems.providers.base import WorkItemProvider


class JiraProvider(WorkItemProvider):
    """Read-only Jira Cloud/Server REST API provider."""

    def __init__(
        self,
        *,
        base_url: str = "",
        email: str = "",
        api_token: str = "",
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._email = email
        self._api_token = api_token

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> JiraProvider:
        jira_cfg = dict(config.get("integrations", {}).get("jira", {}))
        email_env = str(jira_cfg.get("email_env", "JIRA_EMAIL"))
        token_env = str(jira_cfg.get("token_env", "JIRA_API_TOKEN"))
        return cls(
            base_url=str(jira_cfg.get("base_url", "")).strip(),
            email=os.getenv(email_env, "").strip(),
            api_token=os.getenv(token_env, "").strip(),
        )

    def source_name(self) -> str:
        return "jira"

    def is_configured(self) -> bool:
        return bool(self._base_url and self._email and self._api_token)

    def get_item(self, external_id: str) -> TrackedItem:
        if not self.is_configured():
            raise RuntimeError("Jira provider is not configured.")

        issue_key = external_id.strip().upper()
        path = f"/rest/api/3/issue/{urllib.parse.quote(issue_key)}"
        issue = self._request_json(path)
        return self._to_tracked_item(issue)

    def _request_json(self, path: str) -> dict[str, Any]:
        token = base64.b64encode(f"{self._email}:{self._api_token}".encode("utf-8")).decode("ascii")
        request = urllib.request.Request(
            f"{self._base_url}{path}",
            headers={
                "Accept": "application/json",
                "Authorization": f"Basic {token}",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                payload = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Jira request failed: {exc.code} {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Jira connection failed: {exc.reason}") from exc

        data = json.loads(payload)
        if not isinstance(data, dict):
            raise RuntimeError("Unexpected Jira response payload.")
        return data

    def _to_tracked_item(self, issue: dict[str, Any]) -> TrackedItem:
        fields = issue.get("fields", {})
        issue_type = str(fields.get("issuetype", {}).get("name", "")).strip().lower()
        description = self._extract_description(fields.get("description"))
        acceptance = self._extract_acceptance_criteria(description)
        labels = [str(label) for label in fields.get("labels", []) if str(label).strip()]
        assignee = fields.get("assignee", {})
        status = fields.get("status", {})

        external_id = str(issue.get("key", "")).strip()
        return TrackedItem(
            id=external_id,
            external_id=external_id,
            source=WorkItemSource.JIRA,
            kind=self._map_kind(issue_type),
            title=str(fields.get("summary", "")).strip() or external_id,
            description=description,
            acceptance_criteria=acceptance,
            status=str(status.get("name", "")).strip() or None,
            labels=labels,
            assignee=str(assignee.get("displayName", "")).strip() or None,
            metadata={
                "issue_type": issue_type or None,
                "priority": str(fields.get("priority", {}).get("name", "")).strip() or None,
            },
            external_url=f"{self._base_url}/browse/{external_id}",
        )

    @staticmethod
    def _extract_description(value: Any) -> str:
        if isinstance(value, str):
            return value.strip()
        if not isinstance(value, dict):
            return ""
        return JiraProvider._flatten_adf(value).strip()

    @staticmethod
    def _flatten_adf(node: Any) -> str:
        if isinstance(node, str):
            return node
        if isinstance(node, list):
            return "".join(JiraProvider._flatten_adf(item) for item in node)
        if not isinstance(node, dict):
            return ""

        node_type = node.get("type")
        if node_type in {"paragraph", "heading"}:
            return JiraProvider._flatten_adf(node.get("content", [])) + "\n\n"
        if node_type == "text":
            return str(node.get("text", ""))
        if node_type == "bulletList":
            items = []
            for item in node.get("content", []):
                text = JiraProvider._flatten_adf(item).strip()
                if text:
                    items.append(f"- {text}")
            return "\n".join(items) + "\n"
        if node_type == "listItem":
            return JiraProvider._flatten_adf(node.get("content", []))
        return JiraProvider._flatten_adf(node.get("content", []))

    @staticmethod
    def _extract_acceptance_criteria(description: str) -> list[str]:
        criteria: list[str] = []
        for line in description.splitlines():
            stripped = line.strip()
            lowered = stripped.lower()
            if lowered.startswith("- ") or lowered.startswith("* ") or lowered.startswith("[ ] "):
                criteria.append(stripped.lstrip("-* ").strip())
        return criteria

    @staticmethod
    def _map_kind(issue_type: str) -> WorkItemKind:
        mapping = {
            "story": WorkItemKind.STORY,
            "user story": WorkItemKind.STORY,
            "task": WorkItemKind.TASK,
            "sub-task": WorkItemKind.TASK,
            "bug": WorkItemKind.BUG,
            "epic": WorkItemKind.EPIC,
            "incident": WorkItemKind.INCIDENT,
        }
        return mapping.get(issue_type, WorkItemKind.OTHER)
