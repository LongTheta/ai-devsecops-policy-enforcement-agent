"""Fixer for unpinned container images."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from ai_devsecops_agent.autofix.models import Confidence, FilePatch, FixCandidate, PatchOperation, SafetyLevel
from ai_devsecops_agent.models import Finding

# Cannot resolve digest without Docker API - suggest_only
SUPPORTED_IDS = ("pipeline-002", "github-005", "gitops-005", "policy-require_pinned_pipeline_dependencies")


def pin_container_image_fixer(
    finding: Finding,
    file_path: str,
    content: str,
    data: dict[str, Any] | None,
) -> FixCandidate | None:
    """
    Generate fix for unpinned container image.
    We cannot resolve digest without live Docker API, so this is suggest_only.
    Produces a template with placeholder for manual digest resolution.
    """
    if finding.id not in SUPPORTED_IDS:
        return None

    # Detect image reference from evidence or content
    image_match = None
    if finding.evidence:
        image_match = re.search(r"image:\s*([\w./\-:]+)", finding.evidence, re.IGNORECASE)
    if not image_match:
        image_match = re.search(r"image:\s*([\w./\-:]+)", content)
    if not image_match:
        return None

    image_ref = image_match.group(1).strip()
    if "@sha256:" in image_ref:
        return None  # Already pinned

    # Placeholder - user must resolve digest
    new_ref = image_ref.split(":")[0] + "@sha256:<resolve-digest>"
    if ":" in image_ref:
        base = image_ref.rsplit(":", 1)[0]
        new_ref = base + "@sha256:<resolve-digest>"

    diff = f"""- image: {image_ref}
+ image: {new_ref}"""

    return FixCandidate(
        finding_id=finding.id,
        file_path=file_path,
        fix_type="pin_container_image",
        title="Pin container image by digest",
        description="Replace tag with digest placeholder; resolve digest manually (docker pull && docker inspect).",
        confidence=Confidence.HIGH,
        safety_level=SafetyLevel.SUGGEST_ONLY,
        can_auto_apply=False,
        requires_review=True,
        diff=diff,
        original_excerpt=f"image: {image_ref}",
        patched_excerpt=f"image: {new_ref}",
        limitations=[
            "Digest must be resolved manually: docker pull <image> && docker inspect --format='{{{{.RepoDigests}}}}' <image>",
            "Placeholder @sha256:<resolve-digest> must be replaced with actual digest",
        ],
        rollback_notes="Revert to tag reference if needed.",
    )
