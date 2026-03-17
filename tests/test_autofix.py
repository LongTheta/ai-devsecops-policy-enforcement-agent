"""Tests for auto-fix engine, fixers, and patcher."""

import json
from pathlib import Path

import pytest

from ai_devsecops_agent.autofix.engine import run_autofix
from ai_devsecops_agent.autofix.models import AutoFixRequest, FixCandidate, SafetyLevel
from ai_devsecops_agent.autofix.patcher import (
    apply_patch_to_dict,
    create_backup,
    generate_diff,
    load_yaml,
)
from ai_devsecops_agent.autofix.fixers import (
    add_resource_limits_fixer,
    add_sbom_step_fixer,
    disable_risky_argo_autosync_fixer,
    pin_container_image_fixer,
    pin_github_action_fixer,
)
from ai_devsecops_agent.autofix.models import FilePatch, PatchOperation
from ai_devsecops_agent.models import Finding, Severity


# --- Patcher tests ---


def test_load_yaml(tmp_path):
    p = tmp_path / "test.yaml"
    p.write_text("a: 1\nb: 2")
    data, raw = load_yaml(p)
    assert data == {"a": 1, "b": 2}
    assert "a: 1" in raw


def test_apply_patch_to_dict_replace():
    data = {"spec": {"template": {"spec": {"containers": [{"name": "app", "image": "x:latest"}]}}}}
    patch = FilePatch(
        file_path="x",
        operation=PatchOperation.REPLACE,
        path="spec.template.spec.containers[0].resources",
        new_value={"requests": {"memory": "256Mi"}, "limits": {"memory": "512Mi"}},
    )
    result = apply_patch_to_dict(data, patch)
    c = result["spec"]["template"]["spec"]["containers"][0]
    assert "resources" in c
    assert c["resources"]["limits"]["memory"] == "512Mi"


def test_apply_patch_to_dict_argo_sync():
    data = {"spec": {"syncPolicy": {"automated": {"prune": True, "selfHeal": True}}}}
    patch = FilePatch(
        file_path="x",
        operation=PatchOperation.REPLACE,
        path="spec.syncPolicy.automated",
        new_value={"prune": False, "selfHeal": False},
    )
    result = apply_patch_to_dict(data, patch)
    auto = result["spec"]["syncPolicy"]["automated"]
    assert auto["prune"] is False
    assert auto["selfHeal"] is False


def test_generate_diff():
    a = "line1\nline2\nline3"
    b = "line1\nline2_modified\nline3"
    diff = generate_diff(a, b, "a.txt", "b.txt")
    assert "line2" in diff
    assert "---" in diff or "+++" in diff


def test_create_backup(tmp_path):
    f = tmp_path / "test.yaml"
    f.write_text("content")
    backup = create_backup(f)
    assert backup is not None
    assert Path(backup).exists()
    assert Path(backup).read_text() == "content"


# --- Fixer matching ---


def test_add_resource_limits_fixer_matches():
    finding = Finding(
        id="gitops-003",
        title="Missing resource limits",
        severity=Severity.MEDIUM,
        category="gitops",
        description="No limits",
        impacted_files=["deploy.yaml"],
    )
    content = """
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
        - name: app
          image: x:latest
"""
    import yaml
    data = yaml.safe_load(content)
    cand = add_resource_limits_fixer(finding, "deploy.yaml", content, data)
    assert cand is not None
    assert cand.fix_type == "add_resource_limits"
    assert cand.can_auto_apply is True
    assert cand.safety_level == SafetyLevel.SAFE


def test_disable_risky_argo_autosync_fixer_matches():
    finding = Finding(
        id="argo-001",
        title="Risky sync",
        severity=Severity.MEDIUM,
        category="gitops",
        description="prune and selfHeal",
        impacted_files=["app.yaml"],
    )
    content = """
spec:
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
"""
    import yaml
    data = yaml.safe_load(content)
    cand = disable_risky_argo_autosync_fixer(finding, "app.yaml", content, data)
    assert cand is not None
    assert cand.can_auto_apply is True
    assert "prune: false" in (cand.patched_content or "").lower()


def test_pin_github_action_fixer_suggest_only():
    finding = Finding(
        id="github-001",
        title="Unpinned action",
        severity=Severity.MEDIUM,
        category="supply_chain",
        description="Tag pin",
        impacted_files=["workflow.yml"],
    )
    content = "runs-on: ubuntu\nsteps:\n  - uses: actions/checkout@v4"
    cand = pin_github_action_fixer(finding, "workflow.yml", content, None)
    assert cand is not None
    assert cand.can_auto_apply is False
    assert cand.safety_level == SafetyLevel.SUGGEST_ONLY


def test_add_sbom_step_fixer_github():
    finding = Finding(
        id="pipeline-003",
        title="No SBOM",
        severity=Severity.MEDIUM,
        category="supply_chain",
        description="Missing SBOM",
        impacted_files=["ci.yml"],
    )
    content = """
name: CI
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo build
"""
    import yaml
    data = yaml.safe_load(content)
    cand = add_sbom_step_fixer(finding, "ci.yml", content, data)
    assert cand is not None
    assert cand.can_auto_apply is True
    assert "syft" in (cand.patched_content or "")


def test_unsupported_finding_returns_none():
    finding = Finding(
        id="pipeline-001",
        title="Plaintext secret",
        severity=Severity.CRITICAL,
        category="secrets",
        description="Secret",
        impacted_files=["x.yml"],
    )
    cand = add_resource_limits_fixer(finding, "x.yml", "x: 1", {})
    assert cand is None


# --- Engine: suggest mode ---


def test_run_autofix_suggest_mode(tmp_path):
    deploy = tmp_path / "deploy.yaml"
    deploy.write_text("""
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
        - name: app
          image: x:latest
""")
    finding = Finding(
        id="gitops-003",
        title="Missing limits",
        severity=Severity.MEDIUM,
        category="gitops",
        description="No limits",
        impacted_files=[str(deploy)],
    )
    request = AutoFixRequest(mode="suggest", only_safe=False)
    result = run_autofix(request, findings=[finding])
    assert result.mode == "suggest"
    assert result.candidate_count >= 1
    assert result.applied_count == 0


# --- Engine: patch mode ---


def test_run_autofix_patch_mode(tmp_path):
    deploy = tmp_path / "deploy.yaml"
    deploy.write_text("""
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
        - name: app
          image: x:latest
""")
    finding = Finding(
        id="gitops-003",
        title="Missing limits",
        severity=Severity.MEDIUM,
        category="gitops",
        description="No limits",
        impacted_files=[str(deploy)],
    )
    out_dir = tmp_path / "fixes"
    request = AutoFixRequest(mode="patch", output_dir=str(out_dir), only_safe=False)
    result = run_autofix(request, findings=[finding])
    assert result.applied_count >= 1
    patched = out_dir / "deploy.yaml"
    assert patched.exists()
    assert "resources" in patched.read_text()


# --- Engine: apply mode safety ---


def test_run_autofix_apply_only_safe(tmp_path):
    workflow = tmp_path / "ci.yml"
    workflow.write_text("jobs:\n  build:\n    steps:\n      - uses: actions/checkout@v4")
    finding = Finding(
        id="github-001",
        title="Unpinned",
        severity=Severity.MEDIUM,
        category="supply_chain",
        description="Tag",
        impacted_files=[str(workflow)],
    )
    request = AutoFixRequest(mode="apply", only_safe=True, backup=False, dry_run=False)
    result = run_autofix(request, findings=[finding])
    # github-001 is suggest_only, so with only_safe it should be skipped
    assert result.applied_count == 0


def test_run_autofix_apply_creates_backup(tmp_path):
    deploy = tmp_path / "deploy.yaml"
    deploy.write_text("""
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
        - name: app
          image: x:latest
""")
    finding = Finding(
        id="gitops-003",
        title="Missing limits",
        severity=Severity.MEDIUM,
        category="gitops",
        description="No limits",
        impacted_files=[str(deploy)],
    )
    request = AutoFixRequest(mode="apply", backup=True, dry_run=False)
    result = run_autofix(request, findings=[finding])
    assert result.applied_count >= 1
    assert len(result.backup_created) >= 1
    assert (tmp_path / "deploy.yaml.bak").exists()


# --- Input from review-result.json ---


def test_run_autofix_from_review_result(tmp_path):
    deploy = tmp_path / "deploy.yaml"
    deploy.write_text("""
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
        - name: app
          image: x:latest
""")
    review_result = {
        "verdict": "pass_with_warnings",
        "summary": "x",
        "findings": [
            {
                "id": "gitops-003",
                "title": "Missing limits",
                "severity": "medium",
                "category": "gitops",
                "description": "No limits",
                "impacted_files": [str(deploy)],
                "evidence": None,
                "control_families": [],
                "remediation_summary": None,
                "remediation": None,
                "policy_rule_id": None,
                "source_analyzer": "gitops_analyzer",
                "finding_group": "gitops",
            }
        ],
        "policy_results": [],
        "compliance_considerations": [],
        "recommended_remediations": [],
        "next_steps": [],
        "context": {},
        "metadata": {},
    }
    review_path = tmp_path / "review-result.json"
    review_path.write_text(json.dumps(review_result))

    out_dir = tmp_path / "fixes"
    request = AutoFixRequest(
        mode="patch",
        input_path=str(review_path),
        output_dir=str(out_dir),
    )
    result = run_autofix(request)
    assert result.finding_count == 1
    assert result.candidate_count >= 1
