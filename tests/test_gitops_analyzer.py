"""Tests for GitOps analyzer."""

from pathlib import Path

import pytest

from ai_devsecops_agent.analyzers.gitops_analyzer import analyze_gitops
from ai_devsecops_agent.models import Severity


def test_analyze_argo_automated():
    content = """
    apiVersion: argoproj.io/v1alpha1
    kind: Application
    spec:
      project: default
      syncPolicy:
        automated:
          prune: true
    """
    findings = analyze_gitops(content=content)
    assert len(findings) >= 1
    assert any("automated" in f.title.lower() or "sync" in f.title.lower() for f in findings)


def test_analyze_k8s_missing_limits():
    content = """
    apiVersion: apps/v1
    kind: Deployment
    spec:
      template:
        spec:
          containers:
            - name: app
              image: nginx:latest
    """
    findings = analyze_gitops(content=content)
    assert any("limit" in f.title.lower() or "resource" in f.title.lower() for f in findings)


def test_analyze_example_argo():
    path = Path("examples/insecure-argo-application.yaml")
    if not path.exists():
        pytest.skip("examples not found")
    findings = analyze_gitops(path=path)
    assert len(findings) >= 1
