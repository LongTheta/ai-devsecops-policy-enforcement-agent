"""Tests for pipeline analyzer."""

from pathlib import Path

import pytest

from ai_devsecops_agent.analyzers.pipeline_analyzer import analyze_pipeline
from ai_devsecops_agent.models import Severity


def test_analyze_plaintext_secret():
    content = """
    variables:
      API_KEY: "sk-live-1234567890abcdef1234567890"
    """
    findings = analyze_pipeline(content=content)
    critical = [f for f in findings if f.severity == Severity.CRITICAL]
    assert len(critical) >= 1
    assert any("secret" in f.title.lower() or "credential" in f.title.lower() for f in critical)


def test_analyze_safe_pipeline():
    content = """
    stages: [build]
    build:
      script: [echo hello]
    """
    findings = analyze_pipeline(content=content)
    # May have SBOM or other medium/low; should not have critical if no secret
    critical = [f for f in findings if f.severity == Severity.CRITICAL]
    assert len(critical) == 0


def test_analyze_example_gitlab_ci():
    path = Path("examples/insecure-gitlab-ci.yml")
    if not path.exists():
        pytest.skip("examples not found")
    findings = analyze_pipeline(path=path)
    assert len(findings) >= 1
    ids = [f.id for f in findings]
    assert "pipeline-001" in ids or any("policy-" in f.id for f in findings)


def test_analyze_require_artifact_traceability():
    """Pipeline without artifacts/digest/SBOM triggers policy-require_artifact_traceability."""
    content = """
    stages: [build]
    build:
      script: [echo hello]
    """
    findings = analyze_pipeline(content=content, policy_path="policies/default.yaml")
    ids = [f.id for f in findings]
    assert "policy-require_artifact_traceability" in ids


def test_analyze_require_audit_logging_evidence():
    """Pipeline with deploy but no audit keywords triggers policy-require_audit_logging_evidence."""
    content = """
    stages: [build, deploy]
    build:
      script: [echo build]
    deploy:
      script: [kubectl apply -f manifest.yaml]
    """
    findings = analyze_pipeline(content=content, policy_path="policies/default.yaml")
    ids = [f.id for f in findings]
    assert "policy-require_audit_logging_evidence" in ids


def test_analyze_require_signed_artifacts():
    """Pipeline without cosign/sign triggers policy-require_signed_artifacts (FedRAMP policy)."""
    content = """
    stages: [build]
    build:
      script: [docker build -t app .]
    """
    findings = analyze_pipeline(content=content, policy_path="policies/fedramp-moderate.yaml")
    ids = [f.id for f in findings]
    assert "policy-require_signed_artifacts" in ids
