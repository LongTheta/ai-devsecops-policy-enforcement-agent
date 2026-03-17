"""Convert findings into developer-friendly PR/MR review comments."""

from typing import Literal

from ai_devsecops_agent.models import Finding, ReviewResult, Severity
from ai_devsecops_agent.remediation.suggestions import suggest_remediation


CommentFormat = Literal["github", "gitlab", "generic"]


def render_summary_comment(
    result: ReviewResult,
    format: CommentFormat = "generic",
) -> str:
    """Generate a summary comment for the entire review."""
    lines = [
        "## DevSecOps Policy Review",
        "",
        f"**Verdict:** {result.verdict.value.upper().replace('_', ' ')}",
        "",
        result.summary,
        "",
    ]

    if result.findings:
        by_sev = _count_by_severity(result.findings)
        lines.append("### Findings summary")
        lines.append("")
        for sev in (Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO):
            n = by_sev.get(sev, 0)
            if n > 0:
                lines.append(f"- **{sev.value}:** {n}")
        lines.append("")

    if result.recommended_remediations:
        lines.append("### Top remediations")
        lines.append("")
        for r in result.recommended_remediations[:5]:
            lines.append(f"- {r}")
        lines.append("")

    return _wrap_format(lines, format, "summary")


def render_finding_comment(
    finding: Finding,
    format: CommentFormat = "generic",
    include_evidence: bool = True,
    include_example: bool = True,
) -> str:
    """Generate a single finding comment in developer-friendly format."""
    lines = [
        f"### {finding.title}",
        "",
        f"**Severity:** {finding.severity.value.title()}",
        f"**Category:** {finding.category.replace('_', ' ').title()}",
        "",
        "**Why this matters:**",
        finding.description,
        "",
    ]

    fix = finding.remediation_summary
    if not fix and finding.remediation:
        fix = finding.remediation.summary
    if fix:
        lines.append("**Suggested fix:**")
        lines.append(fix)
        lines.append("")

    remediation = suggest_remediation(finding)
    if include_example and remediation and remediation.snippet:
        lines.append("**Example:**")
        lines.append("```yaml")
        lines.append(remediation.snippet.strip())
        lines.append("```")
        lines.append("")

    if include_evidence and finding.evidence:
        lines.append("**Evidence:**")
        lines.append("```")
        evidence = finding.evidence[:400] + ("..." if len(finding.evidence) > 400 else "")
        lines.append(evidence)
        lines.append("```")
        lines.append("")

    if finding.impacted_files:
        lines.append(f"**Impacted files:** {', '.join(finding.impacted_files)}")
        lines.append("")

    return _wrap_format(lines, format, "finding", finding_id=finding.id)


def render_all_finding_comments(
    result: ReviewResult,
    format: CommentFormat = "generic",
    include_evidence: bool = False,
) -> list[tuple[str, str]]:
    """
    Generate individual comments for each finding.
    Returns list of (file_path, comment_body) for API posting.
    """
    out: list[tuple[str, str]] = []
    for f in result.findings:
        body = render_finding_comment(f, format=format, include_evidence=include_evidence)
        path = f.impacted_files[0] if f.impacted_files else ""
        out.append((path, body))
    return out


def render_grouped_comments(
    result: ReviewResult,
    group_by: Literal["severity", "category"] = "severity",
    format: CommentFormat = "generic",
) -> str:
    """Generate grouped review comments by severity or category."""
    lines = [
        "## DevSecOps Policy Review – Findings",
        "",
        f"**Verdict:** {result.verdict.value.upper().replace('_', ' ')}",
        "",
    ]

    if group_by == "severity":
        for sev in (Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO):
            subset = [f for f in result.findings if f.severity == sev]
            if not subset:
                continue
            lines.append(f"### {sev.value.upper()}")
            lines.append("")
            for f in subset:
                lines.append(f"#### {f.title} (`{f.id}`)")
                lines.append("")
                lines.append(f"- **Category:** {f.category}")
                lines.append(f"- **Description:** {f.description}")
                if f.remediation_summary:
                    lines.append(f"- **Suggested fix:** {f.remediation_summary}")
                rem = suggest_remediation(f)
                if rem and rem.snippet:
                    lines.append("")
                    lines.append("Example:")
                    lines.append("```yaml")
                    lines.append(rem.snippet.strip())
                    lines.append("```")
                lines.append("")
    else:
        categories: dict[str, list[Finding]] = {}
        for f in result.findings:
            cat = f.category.replace("_", " ").title()
            categories.setdefault(cat, []).append(f)
        for cat in sorted(categories.keys()):
            subset = categories[cat]
            lines.append(f"### {cat}")
            lines.append("")
            for f in subset:
                lines.append(f"#### {f.title} (`{f.id}`) – {f.severity.value}")
                lines.append("")
                lines.append(f"- **Description:** {f.description}")
                if f.remediation_summary:
                    lines.append(f"- **Suggested fix:** {f.remediation_summary}")
                rem = suggest_remediation(f)
                if rem and rem.snippet:
                    lines.append("")
                    lines.append("Example:")
                    lines.append("```yaml")
                    lines.append(rem.snippet.strip())
                    lines.append("```")
                lines.append("")

    return _wrap_format(lines, format, "grouped")


def _count_by_severity(findings: list[Finding]) -> dict[Severity, int]:
    counts: dict[Severity, int] = {}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    return counts


def _wrap_format(
    lines: list[str],
    format: CommentFormat,
    comment_type: str,
    finding_id: str | None = None,
) -> str:
    """Apply platform-specific wrapping if needed."""
    body = "\n".join(lines).strip()

    if format == "github":
        # GitHub supports markdown; optional metadata for API
        return body

    if format == "gitlab":
        # GitLab supports markdown; optional metadata
        return body

    # generic = plain markdown
    return body
