"""Auto-fix implementations for policy findings."""

from ai_devsecops_agent.autofix.fixers.add_resource_limits import add_resource_limits_fixer
from ai_devsecops_agent.autofix.fixers.add_sbom_step import add_sbom_step_fixer
from ai_devsecops_agent.autofix.fixers.disable_risky_argo_autosync import disable_risky_argo_autosync_fixer
from ai_devsecops_agent.autofix.fixers.pin_container_image import pin_container_image_fixer
from ai_devsecops_agent.autofix.fixers.pin_github_action import pin_github_action_fixer

__all__ = [
    "add_resource_limits_fixer",
    "add_sbom_step_fixer",
    "disable_risky_argo_autosync_fixer",
    "pin_container_image_fixer",
    "pin_github_action_fixer",
]
