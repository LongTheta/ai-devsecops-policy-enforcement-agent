"""Generate JSON report from ReviewResult."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from ai_devsecops_agent.models import ReviewResult

if TYPE_CHECKING:
    from ai_devsecops_agent.models import Finding


def render_json(result: ReviewResult) -> str:
    """Produce a JSON-serializable report."""
    findings_by_group = {
        "github_actions": [_finding_to_dict(f) for f in result.findings if f.finding_group == "github_actions"],
        "ci_cd": [_finding_to_dict(f) for f in result.findings if f.finding_group == "ci_cd"],
        "gitops": [_finding_to_dict(f) for f in result.findings if f.finding_group == "gitops"],
        "cross_system": [_finding_to_dict(f) for f in result.findings if f.finding_group == "cross_system"],
        "other": [_finding_to_dict(f) for f in result.findings if f.finding_group not in ("github_actions", "ci_cd", "gitops", "cross_system")],
    }
    data = {
        "verdict": result.verdict.value,
        "summary": result.summary,
        "findings": [_finding_to_dict(f) for f in result.findings],
        "findings_by_group": findings_by_group,
        "policy_results": result.policy_results,
        "compliance_considerations": result.compliance_considerations,
        "recommended_remediations": result.recommended_remediations,
        "next_steps": result.next_steps,
        "context": result.context.model_dump(),
        "metadata": result.metadata,
    }
    return json.dumps(data, indent=2)


def _finding_to_dict(f: "Finding") -> dict:
    d = f.model_dump()
    if f.remediation:
        d["remediation"] = f.remediation.model_dump()
    if f.control_families:
        d["control_families"] = [c.model_dump() for c in f.control_families]
    return d
