"""Registry mapping finding IDs to fixers."""

from typing import Callable

from ai_devsecops_agent.autofix.fixers import (
    add_resource_limits_fixer,
    add_sbom_step_fixer,
    disable_risky_argo_autosync_fixer,
    pin_container_image_fixer,
    pin_github_action_fixer,
)
from ai_devsecops_agent.models import Finding

from ai_devsecops_agent.autofix.models import FixCandidate

FixerFunc = Callable[[Finding, str, str, dict | None], FixCandidate | None]

# finding_id -> list of fixers (some findings may match multiple fixers; first successful wins)
FIXER_REGISTRY: dict[str, list[FixerFunc]] = {
    "pipeline-002": [pin_github_action_fixer, pin_container_image_fixer],
    "pipeline-003": [add_sbom_step_fixer],
    "github-001": [pin_github_action_fixer],
    "github-005": [pin_container_image_fixer],
    "gitops-001": [disable_risky_argo_autosync_fixer],
    "gitops-003": [add_resource_limits_fixer],
    "gitops-005": [pin_container_image_fixer],
    "argo-001": [disable_risky_argo_autosync_fixer],
    "sbom-001": [add_sbom_step_fixer],
    "policy-require_sbom": [add_sbom_step_fixer],
    "policy-require_pinned_pipeline_dependencies": [pin_github_action_fixer, pin_container_image_fixer],
}


def get_fixers_for_finding(finding: Finding) -> list[FixerFunc]:
    """Return fixers that can handle this finding."""
    return FIXER_REGISTRY.get(finding.id, [])
