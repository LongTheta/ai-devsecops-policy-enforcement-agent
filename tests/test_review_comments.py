"""Tests for review comment generation."""

from ai_devsecops_agent.models import Finding, Remediation, ReviewResult, Severity, Verdict
from ai_devsecops_agent.review_comments import (
    render_finding_comment,
    render_grouped_comments,
    render_summary_comment,
)


def test_render_summary_comment():
    result = ReviewResult(
        verdict=Verdict.FAIL,
        summary="Review failed: 1 high finding.",
        findings=[
            Finding(
                id="pipeline-002",
                title="Unpinned image",
                severity=Severity.HIGH,
                category="supply_chain",
                description="Image uses :latest.",
            ),
        ],
    )
    out = render_summary_comment(result)
    assert "DevSecOps Policy Review" in out
    assert "FAIL" in out
    assert "high" in out.lower()
    assert "Unpinned" in out or "1" in out


def test_render_finding_comment():
    f = Finding(
        id="pipeline-003",
        title="Missing SBOM Generation Step",
        severity=Severity.HIGH,
        category="supply_chain",
        description="This pipeline does not generate an SBOM.",
        remediation_summary="Add a build step that generates SBOM.",
        remediation=Remediation(
            summary="Add SBOM",
            snippet="- name: Generate SBOM\n  run: syft . -o cyclonedx-json > sbom.json",
        ),
    )
    out = render_finding_comment(f)
    assert "Missing SBOM" in out
    assert "High" in out
    assert "Why this matters" in out
    assert "Suggested fix" in out
    assert "syft" in out
    assert "```yaml" in out


def test_render_grouped_comments():
    result = ReviewResult(
        verdict=Verdict.PASS_WITH_WARNINGS,
        summary="Some warnings.",
        findings=[
            Finding(
                id="pipeline-002",
                title="Unpinned",
                severity=Severity.HIGH,
                category="supply_chain",
                description="Unpinned image.",
            ),
            Finding(
                id="gitops-001",
                title="Auto sync",
                severity=Severity.MEDIUM,
                category="gitops",
                description="Automated sync enabled.",
            ),
        ],
    )
    out = render_grouped_comments(result, group_by="severity")
    assert "HIGH" in out
    assert "MEDIUM" in out
    assert "Unpinned" in out
    assert "Auto sync" in out
