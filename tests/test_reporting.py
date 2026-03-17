"""Tests for report generation."""

from ai_devsecops_agent.models import Finding, ReviewResult, Severity, Verdict
from ai_devsecops_agent.reporting import render_console, render_json, render_markdown, render_sarif


def test_render_markdown():
    result = ReviewResult(
        verdict=Verdict.PASS,
        summary="All good",
        findings=[],
    )
    md = render_markdown(result)
    assert "# DevSecOps Policy Review Report" in md
    assert "PASS" in md
    assert "Executive Summary" in md


def test_render_json():
    result = ReviewResult(
        verdict=Verdict.FAIL,
        summary="Failed",
        findings=[
            Finding(id="f1", title="F1", category="secrets", description="D1"),
        ],
    )
    js = render_json(result)
    assert "fail" in js.lower()
    assert "f1" in js
    assert "findings" in js


def test_render_console():
    result = ReviewResult(
        verdict=Verdict.PASS_WITH_WARNINGS,
        summary="Warnings",
        findings=[
            Finding(id="f1", title="F1", severity=Severity.MEDIUM, category="x", description="D1"),
        ],
    )
    out = render_console(result)
    assert "PASS" in out.upper()
    assert "WARNING" in out.upper() or "warning" in out.lower()
    assert "medium" in out.lower()


def test_render_sarif():
    result = ReviewResult(
        verdict=Verdict.FAIL,
        summary="Failed",
        findings=[
            Finding(
                id="policy-require_sbom",
                title="Require SBOM",
                severity=Severity.HIGH,
                category="supply_chain",
                description="SBOM required",
                impacted_files=["ci.yml"],
            ),
        ],
    )
    sarif = render_sarif(result)
    assert '"$schema"' in sarif
    assert '"version": "2.1.0"' in sarif
    assert "policy-require_sbom" in sarif
    assert "Require SBOM" in sarif
    assert "ci.yml" in sarif
