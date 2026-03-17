"""Load and parse policy YAML into PolicySet."""

from pathlib import Path

import yaml
from pydantic import ValidationError

from ai_devsecops_agent.models import PolicyRule, PolicySet, Severity


def load_policy_set(path: str | Path) -> PolicySet:
    """Load a policy YAML file into a PolicySet."""
    path = Path(path)
    if not path.exists():
        return PolicySet(name="empty", description="No policy file found", rules=[])

    raw = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw) or {}

    name = data.get("name", path.stem)
    description = data.get("description", "")
    rules_data = data.get("rules", [])

    rules: list[PolicyRule] = []
    for r in rules_data:
        if not isinstance(r, dict):
            continue
        try:
            severity_str = (r.get("severity") or "high").lower()
            severity = getattr(Severity, severity_str.upper(), Severity.HIGH)
            rule = PolicyRule(
                id=r.get("id", ""),
                name=r.get("name", r.get("id", "unnamed")),
                description=r.get("description", ""),
                severity=severity,
                category=r.get("category", "policy"),
                enabled=r.get("enabled", True),
                config=r.get("config", {}),
            )
            if rule.id and rule.enabled:
                rules.append(rule)
        except (ValidationError, TypeError):
            continue

    return PolicySet(name=name, description=description, rules=rules)
