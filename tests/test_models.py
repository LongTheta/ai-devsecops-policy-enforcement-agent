"""Tests for core models."""

import pytest
from pydantic import ValidationError

from ai_devsecops_agent.models import (
    Finding,
    Remediation,
    ComplianceMapping,
    PolicyRule,
    PolicySet,
    ReviewContext,
    ReviewRequest,
    ReviewResult,
    Severity,
    Verdict,
    Platform,
)


def test_finding_minimal():
    f = Finding(id="t1", title="Test", category="secrets", description="A finding")
    assert f.severity == Severity.MEDIUM
    assert f.impacted_files == []
    assert f.control_families == []


def test_finding_with_remediation():
    r = Remediation(summary="Use secrets", snippet="env: SECRET")
    f = Finding(
        id="t2",
        title="Secret",
        category="secrets",
        description="Found secret",
        remediation=r,
    )
    assert f.remediation.summary == "Use secrets"


def test_compliance_mapping():
    c = ComplianceMapping(control_family="IA", rationale="Secrets", note="Not formal.")
    assert c.control_family == "IA"


def test_policy_rule():
    r = PolicyRule(id="no_secrets", name="No Secrets", severity=Severity.CRITICAL)
    assert r.enabled is True
    assert r.config == {}


def test_policy_set():
    s = PolicySet(name="default", rules=[
        PolicyRule(id="r1", name="R1"),
    ])
    assert len(s.rules) == 1
    assert s.rules[0].id == "r1"


def test_review_context_defaults():
    ctx = ReviewContext()
    assert ctx.platform == Platform.LOCAL
    assert ctx.compliance_mode == "default"


def test_review_request():
    req = ReviewRequest(
        pipeline_path=".gitlab-ci.yml",
        gitops_paths=["app.yaml"],
        policy_path="policies/default.yaml",
    )
    assert req.pipeline_path == ".gitlab-ci.yml"
    assert len(req.gitops_paths) == 1


def test_review_result():
    res = ReviewResult(
        verdict=Verdict.PASS_WITH_WARNINGS,
        summary="Some warnings",
        findings=[],
    )
    assert res.verdict == Verdict.PASS_WITH_WARNINGS
    assert res.policy_results == []
