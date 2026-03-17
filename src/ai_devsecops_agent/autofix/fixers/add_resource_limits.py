"""Fixer for missing Kubernetes resource requests/limits."""

from __future__ import annotations

from pathlib import Path
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

SUPPORTED_IDS = ("gitops-003",)

DEFAULT_RESOURCES = {
    "requests": {"memory": "256Mi", "cpu": "100m"},
    "limits": {"memory": "512Mi", "cpu": "500m"},
}


def add_resource_limits_fixer(
    finding: Finding,
    file_path: str,
    content: str,
    data: dict[str, Any] | None,
) -> FixCandidate | None:
    """
    Add resource requests and limits to containers missing them.
    Deterministic, safe to auto-apply.
    """
    if finding.id not in SUPPORTED_IDS:
        return None

    if not data:
        from ai_devsecops_agent.autofix.patcher import load_yaml
        data, _ = load_yaml(file_path)
    if not data:
        return None

    # Find containers without resources
    spec = data.get("spec", {}) or {}
    template = spec.get("template", {}) or {}
    pod_spec = template.get("spec", {}) or {}
    containers = pod_spec.get("containers") or []

    if not containers:
        return None

    patches: list[FilePatch] = []
    for i, c in enumerate(containers):
        if not isinstance(c, dict):
            continue
        if (c.get("resources") or {}).get("limits"):
            continue  # Already has limits
        path = f"spec.template.spec.containers[{i}].resources"
        patches.append(
            FilePatch(
                file_path=file_path,
                operation=PatchOperation.REPLACE,
                path=path,
                original_value=c.get("resources"),
                new_value=DEFAULT_RESOURCES,
                description=f"Add resource requests/limits to container {c.get('name', i)}",
            )
        )

    if not patches:
        return None

    # Generate patched content for diff
    patched = data
    for p in patches:
        patched = apply_patch_to_dict(patched, p)
    patched_content = yaml.dump(patched, default_flow_style=False, allow_unicode=True, sort_keys=False)
    diff = generate_diff(content, patched_content, file_path, file_path)
    return FixCandidate(
        finding_id=finding.id,
        file_path=file_path,
        fix_type="add_resource_limits",
        title="Add resource requests and limits",
        description="Add default resource requests and limits to prevent resource exhaustion.",
        confidence=Confidence.HIGH,
        safety_level=SafetyLevel.SAFE,
        can_auto_apply=True,
        requires_review=False,
        diff=diff,
        original_excerpt="(no resources block)",
        patched_excerpt=yaml.dump(DEFAULT_RESOURCES, default_flow_style=False),
        patches=patches,
        limitations=["Default values (256Mi/512Mi, 100m/500m) - adjust for your workload"],
        rollback_notes="Remove resources block or restore from backup.",
        patched_content=patched_content,
    )
