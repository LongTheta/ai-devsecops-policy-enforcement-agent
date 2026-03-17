"""Generate SARIF 2.1.0 output for GitHub Advanced Security, GitLab SAST, and other tools."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from ai_devsecops_agent.models import ReviewResult, Severity

if TYPE_CHECKING:
    from ai_devsecops_agent.models import Finding

# SARIF level mapping
_SEVERITY_TO_LEVEL = {
    Severity.CRITICAL: "error",
    Severity.HIGH: "error",
    Severity.MEDIUM: "warning",
    Severity.LOW: "warning",
    Severity.INFO: "note",
}


def render_sarif(result: ReviewResult) -> str:
    """Produce SARIF 2.1.0 JSON for static analysis tool integration."""
    rules = _build_rules(result.findings)
    results = [_finding_to_sarif_result(f) for f in result.findings]
    artifacts = _build_artifacts(result.findings)

    run = {
        "tool": {
            "driver": {
                "name": "ai-devsecops-policy-enforcement-agent",
                "version": "0.1.0",
                "informationUri": "https://github.com/LongTheta/ai-devsecops-policy-enforcement-agent",
                "rules": rules,
            }
        },
        "results": results,
        "artifacts": artifacts,
    }

    sarif = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [run],
    }

    return json.dumps(sarif, indent=2)


def _build_rules(findings: list["Finding"]) -> list[dict]:
    """Build unique rules from findings."""
    seen: set[str] = set()
    rules = []
    for f in findings:
        if f.id in seen:
            continue
        seen.add(f.id)
        rules.append({
            "id": f.id,
            "name": f.title,
            "shortDescription": {"text": f.title},
            "fullDescription": {"text": f.description},
            "defaultConfiguration": {"level": _SEVERITY_TO_LEVEL.get(f.severity, "warning")},
            "properties": {"category": f.category},
        })
    return rules


def _finding_to_sarif_result(f: "Finding") -> dict:
    """Convert a Finding to SARIF result."""
    level = _SEVERITY_TO_LEVEL.get(f.severity, "warning")
    locations = []
    for uri in (f.impacted_files or [])[:5]:
        locations.append({
            "physicalLocation": {
                "artifactLocation": {"uri": uri},
            }
        })
    if not locations:
        locations = [{"physicalLocation": {"artifactLocation": {"uri": "unknown"}}}]

    result = {
        "ruleId": f.id,
        "level": level,
        "message": {"text": f"{f.title}: {f.description}"},
        "locations": locations,
    }
    if f.remediation_summary:
        result["message"]["text"] += f" Remediation: {f.remediation_summary}"
    return result


def _build_artifacts(findings: list["Finding"]) -> list[dict]:
    """Build artifact list from impacted files."""
    seen: set[str] = set()
    artifacts = []
    for f in findings:
        for uri in f.impacted_files or []:
            if uri not in seen:
                seen.add(uri)
                artifacts.append({"location": {"uri": uri}})
    return artifacts
