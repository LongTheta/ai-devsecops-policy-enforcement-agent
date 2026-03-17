"""Fixer for unpinned GitHub Actions."""

from __future__ import annotations

import re
from typing import Any

from ai_devsecops_agent.autofix.models import Confidence, FixCandidate, SafetyLevel
from ai_devsecops_agent.models import Finding

# Cannot resolve SHA without GitHub API - suggest_only
SUPPORTED_IDS = ("github-001", "pipeline-002", "policy-require_pinned_pipeline_dependencies")


def pin_github_action_fixer(
    finding: Finding,
    file_path: str,
    content: str,
    data: dict[str, Any] | None,
) -> FixCandidate | None:
    """
    Generate fix for unpinned GitHub Action.
    We cannot resolve SHA without live API, so suggest_only.
    Produces template with placeholder for manual SHA lookup.
    """
    if finding.id not in SUPPORTED_IDS:
        return None

    # Only apply to GitHub Actions workflows
    if "uses:" not in content or "runs-on:" not in content:
        return None

    # Find uses: owner/repo@v1 pattern
    match = re.search(r"uses:\s*([\w./\-]+)@(v[\d.]+)", content)
    if not match:
        return None

    action_ref = match.group(1)
    tag = match.group(2)
    new_ref = f"{action_ref}@<full-40-char-sha>"

    diff = f"""- uses: {action_ref}@{tag}
+ uses: {new_ref}"""

    return FixCandidate(
        finding_id=finding.id,
        file_path=file_path,
        fix_type="pin_github_action",
        title="Pin GitHub Action by full SHA",
        description="Replace tag pin with SHA placeholder; look up SHA from action repo (e.g. github.com/owner/repo/commits/main).",
        confidence=Confidence.HIGH,
        safety_level=SafetyLevel.SUGGEST_ONLY,
        can_auto_apply=False,
        requires_review=True,
        diff=diff,
        original_excerpt=f"uses: {action_ref}@{tag}",
        patched_excerpt=f"uses: {new_ref}",
        limitations=[
            "SHA must be resolved manually from GitHub (commits page or API)",
            "Use Dependabot for automated action updates",
        ],
        rollback_notes="Revert to tag reference if needed.",
    )
