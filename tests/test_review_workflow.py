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


def test_review_with_artifact_dir(tmp_path):
    """Review with --artifact-dir produces CI/CD artifacts."""
    from ai_devsecops_agent.workflows.artifacts import write_artifacts, workflow_integration_result

    path = Path("examples/insecure-gitlab-ci.yml")
    if not path.exists():
        pytest.skip("examples not found")
    req = ReviewRequest(
        context=ReviewContext(platform=Platform.LOCAL),
        pipeline_path=str(path),
        policy_path="policies/default.yaml",
    )
    result = run_review(req)
    artifacts = write_artifacts(result, tmp_path, include_comments=True, include_remediations=True)
    wf = workflow_integration_result(result, artifacts)
    assert (tmp_path / "review-result.json").exists()
    assert (tmp_path / "policy-summary.json").exists()
    assert (tmp_path / "comments.json").exists()
    assert (tmp_path / "remediations.json").exists()
    assert wf.status in ("pass", "pass_with_warnings", "fail")
