"""Console-friendly summary from ReviewResult."""

from ai_devsecops_agent.models import ReviewResult, Severity


def render_console(result: ReviewResult) -> str:
    """Short terminal-friendly summary."""
    lines = [
        "=== DevSecOps Policy Review ===",
        "",
        f"Verdict: {result.verdict.value.upper().replace('_', ' ')}",
        "",
        result.summary,
        "",
        "Findings by severity:",
    ]
    for sev in (Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO):
        count = sum(1 for f in result.findings if f.severity == sev)
        if count > 0:
            lines.append(f"  {sev.value}: {count}")
    lines.append("")
    if result.findings:
        lines.append("Top findings:")
        for f in result.findings[:5]:
            lines.append(f"  - [{f.severity.value}] {f.title} ({f.id})")
    lines.append("")
    lines.append("Run with --output markdown or --output json for full report.")
    return "\n".join(lines)
