"""Auto-remediation engine for common CI/CD, GitOps, and supply-chain findings."""

from ai_devsecops_agent.remediation.engine import (
    generate_patch,
    generate_remediation,
)
from ai_devsecops_agent.remediation.suggestions import (
    get_remediation_snippet,
    suggest_remediation,
)

__all__ = [
    "generate_remediation",
    "generate_patch",
    "get_remediation_snippet",
    "suggest_remediation",
]
