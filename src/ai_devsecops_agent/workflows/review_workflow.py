"""Orchestrate pipeline, GitOps, SBOM, and compliance analysis and produce ReviewResult."""

from pathlib import Path

from ai_devsecops_agent.analyzers import (
    analyze_cross_system,
    analyze_gitops,
    analyze_pipeline,
    analyze_sbom,
)
from ai_devsecops_agent.analyzers.compliance_mapper import enrich_findings_with_controls
from ai_devsecops_agent.models import (
    Finding,
    Platform,
    ReviewContext,
    ReviewRequest,
    ReviewResult,
    Severity,
    Verdict,
)
from ai_devsecops_agent.policies.loader import load_policy_set


def run_review(request: ReviewRequest) -> ReviewResult:
    """Run full review: pipeline, GitOps, SBOM, policy, then compute verdict and reports."""
    context = request.context
    all_findings: list[Finding] = []

    policy_path = request.policy_path or "policies/default.yaml"
    policy_set = load_policy_set(policy_path)

    # Pipeline
    if request.pipeline_path:
        path = Path(request.pipeline_path)
        if path.exists():
            content = path.read_text(encoding="utf-8")
            all_findings.extend(analyze_pipeline(
                content=content,
                path=request.pipeline_path,
                policy_path=policy_path,
            ))
            all_findings.extend(analyze_sbom(content=content, path=request.pipeline_path))

    # GitOps / Argo CD Application manifests
    for p in request.gitops_paths:
        path = Path(p)
        if path.exists():
            all_findings.extend(analyze_gitops(path=path))

    # Supporting K8s manifests (Deployments, etc.)
    manifest_contents: list[str] = []
    manifest_paths_list: list[str] = []
    for p in request.manifest_paths:
        path = Path(p)
        if path.exists():
            manifest_contents.append(path.read_text(encoding="utf-8"))
            manifest_paths_list.append(str(p))
            all_findings.extend(analyze_gitops(path=path))

    # Extra paths as pipeline or generic
    for p in request.extra_paths:
        path = Path(p)
        if path.exists():
            content = path.read_text(encoding="utf-8")
            if ".gitlab-ci" in p or ".github" in p or "workflows" in p or "pipeline" in p.lower():
                all_findings.extend(analyze_pipeline(content=content, path=p, policy_path=policy_path))
                all_findings.extend(analyze_sbom(content=content, path=p))
            else:
                all_findings.extend(analyze_gitops(content=content, path=p))
                manifest_contents.append(content)
                manifest_paths_list.append(p)

    # Cross-system analysis when pipeline + GitOps present
    pipeline_content: str | None = None
    argo_content: str | None = None
    argo_path: str | None = None
    if request.pipeline_path:
        path = Path(request.pipeline_path)
        if path.exists():
            pipeline_content = path.read_text(encoding="utf-8")
    for p in request.gitops_paths:
        path = Path(p)
        if path.exists() and "argo" in p.lower():
            argo_content = path.read_text(encoding="utf-8")
            argo_path = str(p)
            break
    if not argo_content and request.gitops_paths:
        path = Path(request.gitops_paths[0])
        if path.exists():
            argo_content = path.read_text(encoding="utf-8")
            argo_path = str(request.gitops_paths[0])

    if pipeline_content or argo_content:
        all_findings.extend(analyze_cross_system(
            pipeline_content=pipeline_content,
            pipeline_path=request.pipeline_path,
            argo_content=argo_content,
            argo_path=argo_path,
            manifest_contents=manifest_contents if manifest_contents else None,
            manifest_paths=manifest_paths_list if manifest_paths_list else None,
        ))

    # Assign finding_group from source_analyzer or platform when missing
    for f in all_findings:
        if f.finding_group is None:
            if f.source_analyzer == "cross_system_analyzer":
                f.finding_group = "cross_system"
            elif f.source_analyzer == "gitops_analyzer":
                f.finding_group = "gitops"
            elif context.platform == Platform.GITHUB:
                f.finding_group = "github_actions"
            else:
                f.finding_group = "ci_cd"

    # Enrich with compliance mappings
    all_findings = enrich_findings_with_controls(all_findings)

    # Policy results (which rules ran)
    policy_results = [{"rule_id": r.id, "name": r.name, "enabled": r.enabled} for r in policy_set.rules]

    # Verdict
    verdict, summary = _compute_verdict_and_summary(all_findings, context)

    # Compliance considerations (from control families present)
    control_families = set()
    for f in all_findings:
        for cf in f.control_families:
            control_families.add(cf.control_family)
    compliance_considerations = [
        f"Findings map to control families: {', '.join(sorted(control_families))}. "
        "These mappings support engineering review and are not formal compliance determinations."
    ]
    if not control_families:
        compliance_considerations = ["No control family mappings applied."]

    # Recommended remediations
    recommended_remediations = []
    for f in all_findings:
        if f.remediation_summary and f.remediation_summary not in recommended_remediations:
            recommended_remediations.append(f.remediation_summary)
        if f.remediation and f.remediation.summary and f.remediation.summary not in recommended_remediations:
            recommended_remediations.append(f.remediation.summary)

    # Next steps
    next_steps = []
    if verdict == Verdict.FAIL:
        next_steps.append("Address critical and high findings before merge or deployment.")
    if any(f.severity == Severity.MEDIUM for f in all_findings):
        next_steps.append("Review medium-severity findings and plan remediation.")
    next_steps.append("Re-run the agent after changes to verify verdict.")

    return ReviewResult(
        verdict=verdict,
        summary=summary,
        findings=all_findings,
        policy_results=policy_results,
        compliance_considerations=compliance_considerations,
        recommended_remediations=recommended_remediations[:20],
        next_steps=next_steps,
        context=context,
        metadata={"policy_set": policy_set.name, "total_findings": len(all_findings)},
    )


def _compute_verdict_and_summary(
    findings: list[Finding],
    context: ReviewContext,
) -> tuple[Verdict, str]:
    """Compute pass / pass_with_warnings / fail and executive summary."""
    critical = sum(1 for f in findings if f.severity == Severity.CRITICAL)
    high = sum(1 for f in findings if f.severity == Severity.HIGH)
    medium = sum(1 for f in findings if f.severity == Severity.MEDIUM)
    low = sum(1 for f in findings if f.severity == Severity.LOW)
    info = sum(1 for f in findings if f.severity == Severity.INFO)

    if critical > 0 or high > 0:
        verdict = Verdict.FAIL
        summary = (
            f"Review failed: {critical} critical, {high} high finding(s). "
            "Address these before merge or deployment."
        )
    elif medium > 0 or low > 0:
        verdict = Verdict.PASS_WITH_WARNINGS
        summary = (
            f"Review passed with warnings: {medium} medium, {low} low, {info} info finding(s). "
            "Consider remediating before production."
        )
    else:
        verdict = Verdict.PASS
        summary = "No significant findings. Review passed."

    return verdict, summary
