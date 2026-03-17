"""Generate CI/CD-consumable artifacts from review results."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from ai_devsecops_agent.models import (
    ReviewArtifact,
    ReviewEventContext,
    ReviewResult,
    Severity,
    Verdict,
    WorkflowIntegrationResult,
)
from ai_devsecops_agent.remediation.engine import generate_remediation_bundle
from ai_devsecops_agent.review_comments import render_grouped_comments, render_summary_comment

if TYPE_CHECKING:
    pass


def _result_to_review_dict(result: ReviewResult) -> dict:
    """Serialize ReviewResult for review-result.json."""
    findings = [f.model_dump(mode="json") for f in result.findings]
    return {
        "verdict": result.verdict.value,
        "summary": result.summary,
        "findings": findings,
        "policy_results": result.policy_results,
        "compliance_considerations": result.compliance_considerations,
        "recommended_remediations": result.recommended_remediations,
        "next_steps": result.next_steps,
        "context": result.context.model_dump(mode="json"),
        "metadata": result.metadata,
    }


def _result_to_policy_summary(result: ReviewResult) -> dict:
    """Serialize policy summary for policy-summary.json."""
    by_sev = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for f in result.findings:
        by_sev[f.severity.value] = by_sev.get(f.severity.value, 0) + 1
    return {
        "verdict": result.verdict.value,
        "status": result.verdict.value,
        "finding_count": len(result.findings),
        "by_severity": by_sev,
        "policy_set": result.metadata.get("policy_set", "default"),
        "summary": result.summary,
    }


def _result_to_comments_dict(result: ReviewResult, platform: str = "github") -> dict:
    """Serialize comments payload for comments.json."""
    format_type = "github" if platform == "github" else "gitlab" if platform == "gitlab" else "generic"
    summary = render_summary_comment(result, format=format_type)
    grouped = render_grouped_comments(result, group_by="severity", format=format_type)
    return {
        "platform": platform,
        "summary_body": summary,
        "grouped_body": grouped,
        "ready_for_post": True,
    }


def write_artifacts(
    result: ReviewResult,
    artifact_dir: Path,
    *,
    include_comments: bool = True,
    include_remediations: bool = True,
    platform: str = "local",
    report_markdown: str | None = None,
) -> list[ReviewArtifact]:
    """
    Write CI/CD artifacts to artifact_dir.
    Returns list of artifacts written.
    """
    artifact_dir = Path(artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifacts: list[ReviewArtifact] = []

    # review-result.json
    review_path = artifact_dir / "review-result.json"
    review_path.write_text(
        json.dumps(_result_to_review_dict(result), indent=2),
        encoding="utf-8",
    )
    artifacts.append(ReviewArtifact(name="review-result.json", path=str(review_path.relative_to(artifact_dir))))

    # policy-summary.json
    policy_path = artifact_dir / "policy-summary.json"
    policy_path.write_text(
        json.dumps(_result_to_policy_summary(result), indent=2),
        encoding="utf-8",
    )
    artifacts.append(ReviewArtifact(name="policy-summary.json", path=str(policy_path.relative_to(artifact_dir))))

    # report.md (for human-readable output in CI)
    if report_markdown:
        report_path = artifact_dir / "report.md"
        report_path.write_text(report_markdown, encoding="utf-8")
        artifacts.append(ReviewArtifact(name="report.md", path=str(report_path.relative_to(artifact_dir))))

    if include_comments:
        comments_data = _result_to_comments_dict(result, platform=platform)
        comments_path = artifact_dir / "comments.json"
        comments_path.write_text(json.dumps(comments_data, indent=2), encoding="utf-8")
        artifacts.append(ReviewArtifact(name="comments.json", path=str(comments_path.relative_to(artifact_dir))))

        # Platform-specific comment files
        if platform == "github":
            github_data = _result_to_comments_dict(result, platform="github")
            github_path = artifact_dir / "github-comments.json"
            github_path.write_text(json.dumps(github_data, indent=2), encoding="utf-8")
            artifacts.append(ReviewArtifact(name="github-comments.json", path=str(github_path.relative_to(artifact_dir))))
        elif platform == "gitlab":
            gitlab_data = _result_to_comments_dict(result, platform="gitlab")
            gitlab_path = artifact_dir / "gitlab-comments.json"
            gitlab_path.write_text(json.dumps(gitlab_data, indent=2), encoding="utf-8")
            artifacts.append(ReviewArtifact(name="gitlab-comments.json", path=str(gitlab_path.relative_to(artifact_dir))))

    if include_remediations:
        bundle = generate_remediation_bundle(result)
        remed_path = artifact_dir / "remediations.json"
        remed_path.write_text(
            json.dumps(bundle.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        artifacts.append(ReviewArtifact(name="remediations.json", path=str(remed_path.relative_to(artifact_dir))))

    return artifacts


def workflow_integration_result(
    result: ReviewResult,
    artifacts: list[ReviewArtifact],
    event_context: ReviewEventContext | None = None,
) -> WorkflowIntegrationResult:
    """Build WorkflowIntegrationResult for CI consumption."""
    critical = sum(1 for f in result.findings if f.severity == Severity.CRITICAL)
    high = sum(1 for f in result.findings if f.severity == Severity.HIGH)
    exit_code = 1 if result.verdict == Verdict.FAIL else 0
    return WorkflowIntegrationResult(
        status=result.verdict.value,
        verdict=result.verdict.value,
        summary=result.summary,
        finding_count=len(result.findings),
        critical_count=critical,
        high_count=high,
        artifacts=artifacts,
        event_context=event_context,
        exit_code=exit_code,
    )
