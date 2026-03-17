"""Tests for review workflow."""

from pathlib import Path

import pytest

from ai_devsecops_agent.models import Platform, ReviewContext, ReviewRequest, Verdict
from ai_devsecops_agent.workflows.review_workflow import run_review


def test_run_review_no_paths():
    req = ReviewRequest(context=ReviewContext(platform=Platform.LOCAL))
    result = run_review(req)
    assert result.verdict in ("pass", "pass_with_warnings", "fail")
    assert result.summary
    assert isinstance(result.findings, list)


def test_run_review_with_example_pipeline():
    path = Path("examples/insecure-gitlab-ci.yml")
    if not path.exists():
        pytest.skip("examples not found")
    req = ReviewRequest(
        context=ReviewContext(platform=Platform.LOCAL),
        pipeline_path=str(path),
        policy_path="policies/default.yaml",
    )
    result = run_review(req)
    assert len(result.findings) >= 1
    assert result.verdict in (Verdict.FAIL, Verdict.PASS_WITH_WARNINGS)


def test_run_review_with_example_argo():
    path = Path("examples/insecure-argo-application.yaml")
    if not path.exists():
        pytest.skip("examples not found")
    req = ReviewRequest(
        context=ReviewContext(platform=Platform.LOCAL),
        gitops_paths=[str(path)],
        policy_path="policies/default.yaml",
    )
    result = run_review(req)
    assert len(result.findings) >= 1
