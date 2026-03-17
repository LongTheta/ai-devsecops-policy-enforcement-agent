"""Fixer for risky Argo CD automated sync settings."""

from __future__ import annotations

from typing import Any

import yaml

from ai_devsecops_agent.autofix.models import (
    Confidence,
    FilePatch,
    FixCandidate,
    PatchOperation,
    SafetyLevel,
)
from ai_devsecops_agent.autofix.patcher import apply_patch_to_dict, generate_diff
from ai_devsecops_agent.models import Finding

SUPPORTED_IDS = ("gitops-001", "argo-001")


def disable_risky_argo_autosync_fixer(
    finding: Finding,
    file_path: str,
    content: str,
    data: dict[str, Any] | None,
) -> FixCandidate | None:
    """
    Disable prune and selfHeal in Argo CD syncPolicy.automated.
    Deterministic, safe to auto-apply.
    """
    if finding.id not in SUPPORTED_IDS:
        return None

    if not data:
        import yaml as y
        try:
            data = y.safe_load(content)
        except Exception:
            return None

    if not isinstance(data, dict):
        return None

    spec = data.get("spec", {}) or {}
    sync_policy = spec.get("syncPolicy", {}) or {}
    automated = sync_policy.get("automated")

    if not automated or not isinstance(automated, dict):
        return None

    # Only fix if prune or selfHeal is True
    prune = automated.get("prune", False)
    self_heal = automated.get("selfHeal", False)
    if not prune and not self_heal:
        return None

    new_automated = {**automated, "prune": False, "selfHeal": False}
    patch = FilePatch(
        file_path=file_path,
        operation=PatchOperation.REPLACE,
        path="spec.syncPolicy.automated",
        original_value=automated,
        new_value=new_automated,
        description="Set prune and selfHeal to false for safer sync",
    )

    patched = apply_patch_to_dict(data, patch)
    patched_content = yaml.dump(patched, default_flow_style=False, allow_unicode=True, sort_keys=False)
    diff = generate_diff(content, patched_content, file_path, file_path)

    return FixCandidate(
        finding_id=finding.id,
        file_path=file_path,
        fix_type="disable_risky_argo_autosync",
        title="Disable risky Argo CD automated sync",
        description="Set prune: false and selfHeal: false to reduce drift/override risk.",
        confidence=Confidence.HIGH,
        safety_level=SafetyLevel.SAFE,
        can_auto_apply=True,
        requires_review=False,
        diff=diff,
        original_excerpt=str(automated),
        patched_excerpt=yaml.dump(new_automated, default_flow_style=False),
        patches=[patch],
        limitations=["Consider manual sync for production instead of automated with prune/selfHeal disabled"],
        rollback_notes="Restore syncPolicy.automated from backup or set prune/selfHeal back to true.",
        patched_content=patched_content,
    )
