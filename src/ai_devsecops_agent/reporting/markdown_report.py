"""Generate Markdown report from ReviewResult."""

from ai_devsecops_agent.models import ReviewResult, Severity


def render_markdown(result: ReviewResult) -> str:
    """Produce a full Markdown report."""
    lines: list[str] = [
        "# DevSecOps Policy Review Report",
        "",
        "## 1. Executive Summary",
        "",
        result.summary,
        "",
        "**Verdict:** " + result.verdict.value.upper().replace("_", " "),
        "",
        "---",
        "",
        "## 2. Verdict",
        "",
        f"- **{result.verdict.value.upper().replace('_', ' ')}**",
        "",
        "---",
        "",
        "## 3. Findings by Group",
        "",
    ]

    groups = {
        "github_actions": ("GitHub Actions", "Findings from workflow YAML, permissions, actions, and supply chain."),
        "ci_cd": ("GitLab / CI/CD", "Findings from pipeline, stages, jobs, SBOM, and supply chain."),
        "gitops": ("Argo CD / GitOps", "Findings from Argo CD Application and Kubernetes manifests."),
        "cross_system": ("Cross-System Governance Gaps", "Findings spanning CI/CD and GitOps (traceability, promotion, gates)."),
    }
    for group_key, (group_title, group_desc) in groups.items():
        group_findings = [f for f in result.findings if f.finding_group == group_key]
        if not group_findings:
            continue
        lines.append(f"### {group_title}")
        lines.append("")
        lines.append(f"*{group_desc}*")
        lines.append("")
        for sev in (Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO):
            subset = [f for f in group_findings if f.severity == sev]
            if not subset:
                continue
            lines.append(f"#### {sev.value.upper()}")
            lines.append("")
            for i, f in enumerate(subset, 1):
                lines.append(f"**{i}. {f.title}** (`{f.id}`)")
                lines.append("")
                lines.append(f"- **Category:** {f.category}")
                lines.append(f"- **Description:** {f.description}")
                if f.evidence:
                    lines.append("- **Evidence:**")
                    lines.append("```")
                    lines.append(f.evidence[:500] + ("..." if len(f.evidence) > 500 else ""))
                    lines.append("```")
                if f.impacted_files:
                    lines.append(f"- **Impacted files:** {', '.join(f.impacted_files)}")
                if f.remediation_summary:
                    lines.append(f"- **Remediation:** {f.remediation_summary}")
                if f.control_families:
                    lines.append("- **Control families (engineering review only):**")
                    for cf in f.control_families:
                        lines.append(f"  - {cf.control_family}: {cf.rationale}")
                lines.append("")
        lines.append("")

    ungrouped = [f for f in result.findings if f.finding_group not in groups]
    if ungrouped:
        lines.append("### Other Findings")
        lines.append("")
        for i, f in enumerate(ungrouped, 1):
            lines.append(f"**{i}. {f.title}** (`{f.id}`)")
            lines.append("")
            lines.append(f"- **Category:** {f.category}")
            lines.append(f"- **Description:** {f.description}")
            if f.remediation_summary:
                lines.append(f"- **Remediation:** {f.remediation_summary}")
            lines.append("")

    lines.extend([
        "---",
        "",
        "## 4. Policy Results",
        "",
    ])
    for pr in result.policy_results:
        lines.append(f"- **{pr.get('name', pr.get('rule_id', ''))}** (enabled: {pr.get('enabled', True)})")
    lines.append("")

    lines.extend([
        "---",
        "",
        "## 5. Compliance Considerations",
        "",
    ])
    for c in result.compliance_considerations:
        lines.append(f"- {c}")
    lines.append("")

    lines.extend([
        "---",
        "",
        "## 6. Recommended Remediations",
        "",
    ])
    for r in result.recommended_remediations:
        lines.append(f"- {r}")
    lines.append("")

    lines.extend([
        "---",
        "",
        "## 7. Next Steps",
        "",
    ])
    for n in result.next_steps:
        lines.append(f"- {n}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*This report is for engineering guidance. Compliance mappings are not formal compliance determinations.*")
    lines.append("")

    return "\n".join(lines)
