"""Tests for workflow artifact generation and integration."""

import json
from pathlib import Path

from ai_devsecops_agent.models import (
    Finding,
    ReviewArtifact,
    ReviewEventContext,
    ReviewResult,
    Severity,
    Verdict,
)
from ai_devsecops_agent.workflows.artifacts import (
    workflow_integration_result,
    write_artifacts,
)


def test_review_event_context():
    ctx = ReviewEventContext(
        platform="github",
        repo="owner/repo",
        branch="main",
        commit_sha="abc123",
        pr_or_mr_number=42,
        actor="bot",
        policy_mode="default",
    )
    d = ctx.model_dump()
    assert d["platform"] == "github"
    assert d["repo"] == "owner/repo"
    assert d["pr_or_mr_number"] == 42


def test_workflow_integration_result():
    result = ReviewResult(
        verdict=Verdict.FAIL,
        summary="Failed",
        findings=[
            Finding(id="f1", title="F1", severity=Severity.CRITICAL, category="x", description="D1"),
            Finding(id="f2", title="F2", severity=Severity.HIGH, category="x", description="D2"),
        ],
    )
    artifacts = [ReviewArtifact(name="review-result.json", path="review-result.json")]
    wf = workflow_integration_result(result, artifacts)
    assert wf.status == "fail"
    assert wf.exit_code == 1
    assert wf.critical_count == 1
    assert wf.high_count == 1
    assert wf.finding_count == 2
    assert len(wf.artifacts) == 1


def test_workflow_integration_result_pass():
    result = ReviewResult(verdict=Verdict.PASS, summary="OK", findings=[])
    wf = workflow_integration_result(result, [])
    assert wf.status == "pass"
    assert wf.exit_code == 0


def test_write_artifacts(tmp_path):
    result = ReviewResult(
        verdict=Verdict.PASS_WITH_WARNINGS,
        summary="Warnings",
        findings=[
            Finding(id="f1", title="F1", severity=Severity.MEDIUM, category="x", description="D1"),
        ],
    )
    artifacts = write_artifacts(
        result,
        tmp_path,
        include_comments=True,
        include_remediations=True,
        platform="github",
    )
    assert len(artifacts) >= 4
    assert (tmp_path / "review-result.json").exists()
    assert (tmp_path / "policy-summary.json").exists()
    assert (tmp_path / "comments.json").exists()
    assert (tmp_path / "remediations.json").exists()

    policy = json.loads((tmp_path / "policy-summary.json").read_text())
    assert policy["verdict"] == "pass_with_warnings"
    assert policy["finding_count"] == 1
    assert "by_severity" in policy

    comments = json.loads((tmp_path / "comments.json").read_text())
    assert comments["platform"] == "github"
    assert "summary_body" in comments
    assert "grouped_body" in comments


def test_write_artifacts_minimal(tmp_path):
    result = ReviewResult(verdict=Verdict.PASS, summary="OK", findings=[])
    artifacts = write_artifacts(
        result,
        tmp_path,
        include_comments=False,
        include_remediations=False,
    )
    assert len(artifacts) == 2
    assert not (tmp_path / "comments.json").exists()
    assert not (tmp_path / "remediations.json").exists()


def test_write_artifacts_github_platform(tmp_path):
    """When platform is github, github-comments.json and report.md are produced."""
    result = ReviewResult(
        verdict=Verdict.PASS_WITH_WARNINGS,
        summary="Warnings",
        findings=[
            Finding(id="f1", title="F1", severity=Severity.MEDIUM, category="x", description="D1"),
        ],
    )
    report_md = "# DevSecOps Policy Review\n\n**Verdict:** PASS WITH WARNINGS"
    artifacts = write_artifacts(
        result,
        tmp_path,
        include_comments=True,
        include_remediations=True,
        platform="github",
        report_markdown=report_md,
    )
    assert (tmp_path / "review-result.json").exists()
    assert (tmp_path / "report.md").exists()
    assert (tmp_path / "github-comments.json").exists()
    assert (tmp_path / "comments.json").exists()

    github_comments = json.loads((tmp_path / "github-comments.json").read_text())
    assert github_comments["platform"] == "github"
    assert "summary_body" in github_comments
    assert "grouped_body" in github_comments
    assert github_comments["ready_for_post"] is True

    assert (tmp_path / "report.md").read_text() == report_md


def test_write_artifacts_gitlab_platform(tmp_path):
    """When platform is gitlab, gitlab-comments.json and report.md are produced."""
    result = ReviewResult(
        verdict=Verdict.PASS_WITH_WARNINGS,
        summary="Warnings",
        findings=[
            Finding(id="f1", title="F1", severity=Severity.MEDIUM, category="x", description="D1"),
        ],
    )
    report_md = "# DevSecOps Policy Review\n\n**Verdict:** PASS WITH WARNINGS"
    artifacts = write_artifacts(
        result,
        tmp_path,
        include_comments=True,
        include_remediations=True,
        platform="gitlab",
        report_markdown=report_md,
    )
    assert (tmp_path / "review-result.json").exists()
    assert (tmp_path / "report.md").exists()
    assert (tmp_path / "gitlab-comments.json").exists()
    assert (tmp_path / "comments.json").exists()

    gitlab_comments = json.loads((tmp_path / "gitlab-comments.json").read_text())
    assert gitlab_comments["platform"] == "gitlab"
    assert "summary_body" in gitlab_comments
    assert "grouped_body" in gitlab_comments
    assert gitlab_comments["ready_for_post"] is True

    assert (tmp_path / "report.md").read_text() == report_md
