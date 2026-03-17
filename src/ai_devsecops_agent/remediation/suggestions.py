"""Patch-like remediation suggestions for common finding IDs."""

from ai_devsecops_agent.models import Finding, Remediation
from ai_devsecops_agent.remediation.engine import generate_remediation

# Legacy snippet lookup for backward compatibility
REMEDIATION_SNIPPETS: dict[str, str] = {}


def get_remediation_snippet(finding_id: str) -> str | None:
    """Return a snippet for a known finding ID, or None. Uses engine when available."""
    # Engine provides full remediation; we return snippet only for legacy callers
    from ai_devsecops_agent.models import Finding, Severity

    dummy = Finding(
        id=finding_id,
        title="",
        severity=Severity.MEDIUM,
        category="",
        description="",
    )
    rem = generate_remediation(dummy)
    return rem.snippet if rem else None


def suggest_remediation(finding: Finding) -> Remediation | None:
    """
    Generate a remediation suggestion for a finding.
    Uses engine; returns Remediation for backward compatibility.
    """
    rem = generate_remediation(finding)
    if not rem:
        return finding.remediation

    return Remediation(
        summary=rem.summary,
        description=rem.rationale,
        snippet=rem.snippet,
    )
