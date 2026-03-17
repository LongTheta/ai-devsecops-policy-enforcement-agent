"""Fixer for missing SBOM generation step."""

from __future__ import annotations

import re
from typing import Any

import yaml

from ai_devsecops_agent.autofix.models import Confidence, FixCandidate, SafetyLevel
from ai_devsecops_agent.models import Finding

SUPPORTED_IDS = ("pipeline-003", "sbom-001", "policy-require_sbom")


# Template for GitHub Actions
GITHUB_SBOM_STEPS = [
    {
        "name": "Generate SBOM",
        "run": "syft . -o cyclonedx-json=sbom.json",
    },
    {
        "name": "Upload SBOM",
        "uses": "actions/upload-artifact@v4",
        "with": {"name": "sbom", "path": "sbom.json"},
    },
]

# Template for GitLab CI
GITLAB_SBOM_SCRIPT = [
    "syft . -o cyclonedx-json=sbom.json",
    "echo 'SBOM generated'",
]

GITLAB_SBOM_ARTIFACTS = {"paths": ["sbom.json"], "expire_in": "30 days"}


def add_sbom_step_fixer(
    finding: Finding,
    file_path: str,
    content: str,
    data: dict[str, Any] | None,
) -> FixCandidate | None:
    """
    Add SBOM generation step to pipeline.
    Uses deterministic templates for GitHub Actions and GitLab CI.
    """
    if finding.id not in SUPPORTED_IDS:
        return None

    if not data:
        try:
            data = yaml.safe_load(content)
        except Exception:
            return None

    if not isinstance(data, dict):
        return None

    is_github = "jobs" in data or "runs-on:" in content or "uses:" in content
    is_gitlab = "stages" in data or any(k in data for k in ("build", "test", "deploy"))

    if is_github:
        return _github_sbom_fix(content, data, file_path, finding)
    if is_gitlab:
        return _gitlab_sbom_fix(content, data, file_path, finding)

    return None


def _github_sbom_fix(content: str, data: dict, file_path: str, finding: Finding) -> FixCandidate | None:
    """Add SBOM step to GitHub Actions workflow."""
    jobs = data.get("jobs") or {}
    if not jobs:
        return None

    # Find first build-like job
    build_job = None
    for name, job in jobs.items():
        if not isinstance(job, dict):
            continue
        steps = job.get("steps") or []
        if steps:
            build_job = (name, job)
            break

    if not build_job:
        return None

    job_name, job = build_job
    steps = list(job.get("steps") or [])

    # Build diff - insert before last step or at end
    new_steps = steps + GITHUB_SBOM_STEPS
    new_job = {**job, "steps": new_steps}
    new_jobs = {**jobs, job_name: new_job}
    new_data = {**data, "jobs": new_jobs}
    patched_content = yaml.dump(new_data, default_flow_style=False, allow_unicode=True, sort_keys=False)

    from ai_devsecops_agent.autofix.patcher import generate_diff

    diff = generate_diff(content, patched_content, file_path, file_path)

    snippet = yaml.dump(GITHUB_SBOM_STEPS, default_flow_style=False, allow_unicode=True)

    return FixCandidate(
        finding_id=finding.id,
        file_path=file_path,
        fix_type="add_sbom_step",
        title="Add SBOM generation step",
        description="Add syft-based SBOM generation and artifact upload to the build job.",
        confidence=Confidence.HIGH,
        safety_level=SafetyLevel.SAFE,
        can_auto_apply=True,
        requires_review=False,
        diff=diff,
        original_excerpt="(no SBOM step)",
        patched_excerpt=snippet,
        limitations=[
            "Requires syft in PATH (add actions/setup-syft or install step if needed)",
            "Template adds to first job with steps; adjust job placement if needed",
        ],
        rollback_notes="Remove the Generate SBOM and Upload SBOM steps from the workflow.",
        patched_content=patched_content,
    )


def _gitlab_sbom_fix(content: str, data: dict, file_path: str, finding: Finding) -> FixCandidate | None:
    """Add SBOM step to GitLab CI."""
    # Find build job
    build_job = None
    for key, val in data.items():
        if key in ("stages", "variables", "include", "default"):
            continue
        if isinstance(val, dict) and "script" in val:
            build_job = (key, val)
            break

    if not build_job:
        return None

    job_name, job = build_job
    script = job.get("script")
    if isinstance(script, str):
        script = [script]
    script = list(script or [])

    new_script = script + GITLAB_SBOM_SCRIPT
    new_job = {**job, "script": new_script, "artifacts": GITLAB_SBOM_ARTIFACTS}
    new_data = {**data, job_name: new_job}
    patched_content = yaml.dump(new_data, default_flow_style=False, allow_unicode=True, sort_keys=False)

    from ai_devsecops_agent.autofix.patcher import generate_diff

    diff = generate_diff(content, patched_content, file_path, file_path)

    snippet = yaml.dump({"script": GITLAB_SBOM_SCRIPT, "artifacts": GITLAB_SBOM_ARTIFACTS}, default_flow_style=False)

    return FixCandidate(
        finding_id=finding.id,
        file_path=file_path,
        fix_type="add_sbom_step",
        title="Add SBOM generation step",
        description="Add syft-based SBOM generation and artifact retention to the build job.",
        confidence=Confidence.HIGH,
        safety_level=SafetyLevel.SAFE,
        can_auto_apply=True,
        requires_review=False,
        diff=diff,
        original_excerpt="(no SBOM step)",
        patched_excerpt=snippet,
        limitations=[
            "Requires syft in CI image; add syft to image or install step",
            "Template adds to first job with script; adjust job placement if needed",
        ],
        rollback_notes="Remove SBOM script lines and artifacts block from the job.",
        patched_content=patched_content,
    )
