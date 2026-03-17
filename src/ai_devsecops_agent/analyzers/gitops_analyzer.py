"""Analyze Kubernetes and Argo CD manifests for GitOps and security concerns."""

import json
from pathlib import Path
from typing import Any

import yaml

from ai_devsecops_agent.models import Finding, Remediation, Severity


def analyze_gitops(
    content: str | None = None,
    path: str | Path | None = None,
) -> list[Finding]:
    """Inspect K8s/Argo CD YAML for drift risk, sync policy, and governance issues."""
    if content is None and path is None:
        return []
    if content is None:
        content = Path(path).read_text(encoding="utf-8")
    path_str = str(path) if path else "manifest"
    findings: list[Finding] = []

    finding_group = "gitops"

    try:
        data = yaml.safe_load(content)
    except Exception:
        return [Finding(
            id="gitops-000",
            title="Invalid YAML",
            severity=Severity.HIGH,
            category="gitops",
            description="Manifest could not be parsed as YAML.",
            impacted_files=[path_str],
            source_analyzer="gitops_analyzer",
            finding_group=finding_group,
        )]

    if not data or not isinstance(data, dict):
        return findings

    kind = (data.get("kind") or "").lower()
    api_version = data.get("apiVersion", "")

    # --- Argo CD Application ---
    if "argoproj.io" in api_version or kind == "application":
        findings.extend(_analyze_argo_application(data, path_str, finding_group))

    # --- Generic K8s (Deployment, etc.) ---
    if kind in ("deployment", "statefulset", "daemonset"):
        findings.extend(_analyze_workload(data, path_str, finding_group))

    # --- Common: resource limits missing ---
    if _missing_resource_limits(data):
        findings.append(Finding(
            id="gitops-003",
            title="Missing resource limits",
            severity=Severity.MEDIUM,
            category="gitops",
            description="Workload does not specify resource limits; can lead to resource exhaustion.",
            evidence=_evidence_snippet(data, "spec"),
            impacted_files=[path_str],
            remediation=Remediation(
                summary="Add resources.limits",
                snippet="resources:\n  limits:\n    memory: 512Mi\n    cpu: 500m",
            ),
            source_analyzer="gitops_analyzer",
            finding_group=finding_group,
        ))

    return findings


def _analyze_argo_application(data: dict[str, Any], path_str: str, finding_group: str) -> list[Finding]:
    findings: list[Finding] = []
    spec = data.get("spec", {}) or {}
    sync_policy = spec.get("syncPolicy", {}) or {}
    automated = sync_policy.get("automated") if isinstance(sync_policy, dict) else None

    if automated:
        prune = automated.get("prune", False) if isinstance(automated, dict) else False
        self_heal = automated.get("selfHeal", False) if isinstance(automated, dict) else False

        findings.append(Finding(
            id="gitops-001",
            title="Automated sync enabled",
            severity=Severity.MEDIUM,
            category="gitops",
            description="Argo CD Application has automated sync; ensure this is intended and promotion gates exist elsewhere.",
            evidence=str(automated),
            impacted_files=[path_str],
            remediation_summary="Use manual sync for production or pair with GitOps Promoter approval gates.",
            source_analyzer="gitops_analyzer",
            finding_group=finding_group,
        ))

        # Prune + selfHeal together increase drift/override risk
        if prune and self_heal:
            findings.append(Finding(
                id="argo-001",
                title="Automated prune and selfHeal both enabled",
                severity=Severity.MEDIUM,
                category="gitops",
                description="Both prune and selfHeal are enabled; local changes can be overwritten without explicit approval.",
                evidence=f"prune: {prune}, selfHeal: {self_heal}",
                impacted_files=[path_str],
                remediation_summary="Consider manual sync for production or restrict prune/selfHeal to non-prod.",
                source_analyzer="gitops_analyzer",
                finding_group=finding_group,
            ))

    project = spec.get("project", "")
    if not project or project == "default":
        findings.append(Finding(
            id="gitops-002",
            title="Default or missing Argo CD project",
            severity=Severity.LOW,
            category="gitops",
            description="Application uses default project; consider explicit AppProject for RBAC and namespace scoping.",
            evidence=f"project: {project!r}",
            impacted_files=[path_str],
            source_analyzer="gitops_analyzer",
            finding_group=finding_group,
        ))

    # Promotion environment separation: targetRevision HEAD on prod path
    source = spec.get("source", {}) or {}
    target_revision = source.get("targetRevision", "HEAD")
    path = source.get("path", "")
    dest = spec.get("destination", {}) or {}
    namespace = dest.get("namespace", "")

    prod_like = any(x in (path + namespace).lower() for x in ("prod", "production", "live"))
    if prod_like and (not target_revision or target_revision == "HEAD"):
        findings.append(Finding(
            id="argo-002",
            title="Production-like path with HEAD revision",
            severity=Severity.MEDIUM,
            category="gitops",
            description="Application targets production-like path/namespace but uses HEAD; no promotion pin for traceability.",
            evidence=f"path: {path}, namespace: {namespace}, targetRevision: {target_revision}",
            impacted_files=[path_str],
            remediation_summary="Use tagged revision or GitOps promotion (e.g. kustomize overlay, tagged ref) for prod.",
            source_analyzer="gitops_analyzer",
            finding_group=finding_group,
        ))

    return findings


def _analyze_workload(data: dict[str, Any], path_str: str, finding_group: str) -> list[Finding]:
    findings: list[Finding] = []
    spec = data.get("spec", {}) or {}
    template = spec.get("template", {}) or {}
    pod_spec = template.get("spec", {}) or {}

    # Security context
    if not pod_spec.get("securityContext"):
        findings.append(Finding(
            id="gitops-004",
            title="No pod security context",
            severity=Severity.MEDIUM,
            category="gitops",
            description="Pod spec does not set securityContext (e.g. runAsNonRoot, readOnlyRootFilesystem).",
            impacted_files=[path_str],
            remediation=Remediation(
                summary="Add securityContext",
                snippet="securityContext:\n  runAsNonRoot: true\n  runAsUser: 1000",
            ),
            source_analyzer="gitops_analyzer",
            finding_group=finding_group,
        ))

    return findings


def _missing_resource_limits(data: dict[str, Any]) -> bool:
    """Check spec.template.spec.containers[].resources.limits."""
    spec = data.get("spec", {}) or {}
    template = spec.get("template", {}) or {}
    pod_spec = template.get("spec", {}) or {}
    containers = pod_spec.get("containers") or []
    for c in containers:
        if not isinstance(c, dict):
            continue
        res = c.get("resources") or {}
        if not res.get("limits"):
            return True
    return False


def _evidence_snippet(data: dict[str, Any], key: str, max_chars: int = 200) -> str:
    """Short snippet of a key for evidence."""
    if key not in data:
        return ""
    try:
        s = json.dumps(data[key], indent=0)[:max_chars]
        return s + "..." if len(s) >= max_chars else s
    except Exception:
        return str(data[key])[:max_chars]
