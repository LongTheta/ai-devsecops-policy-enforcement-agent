"""Cross-system analyzer: CI/CD to GitOps governance gaps, traceability, and promotion risks."""

from pathlib import Path
from typing import Any

import yaml

from ai_devsecops_agent.models import Finding, Remediation, Severity


def analyze_cross_system(
    pipeline_content: str | None = None,
    pipeline_path: str | None = None,
    argo_content: str | None = None,
    argo_path: str | None = None,
    manifest_contents: list[str] | None = None,
    manifest_paths: list[str] | None = None,
) -> list[Finding]:
    """
    Analyze CI/CD and GitOps configs together for governance gaps:
    - Pipeline deploys but no approval gate
    - Argo auto-sync with weak governance
    - No artifact traceability between pipeline and deployment
    - No SBOM/provenance before GitOps delivery
    - Risky promotion flow from build to deployment
    """
    findings: list[Finding] = []
    finding_group = "cross_system"

    pipeline_text = pipeline_content
    if pipeline_text is None and pipeline_path:
        pipeline_text = Path(pipeline_path).read_text(encoding="utf-8")
    pipeline_path_str = pipeline_path or "pipeline"

    argo_text = argo_content
    argo_data: dict[str, Any] | None = None
    if argo_text is None and argo_path:
        argo_text = Path(argo_path).read_text(encoding="utf-8")
    if argo_text:
        try:
            argo_data = yaml.safe_load(argo_text)
        except Exception:
            argo_data = None
    argo_path_str = argo_path or "argo-application"

    manifests = manifest_contents or []
    manifest_paths_list = manifest_paths or [f"manifest-{i}" for i in range(len(manifests))]

    # --- Cross-check: pipeline deploys but no approval gate ---
    if pipeline_text:
        pipeline_lower = pipeline_text.lower()
        has_deploy = any(
            x in pipeline_lower
            for x in ("deploy", "kubectl", "helm", "apply", "argo", "gitops")
        )
        has_approval = any(
            x in pipeline_lower
            for x in (
                "manual", "when: manual", "approval", "gate",
                "environment:", "environment: production", "environment: prod",
            )
        )
        if has_deploy and not has_approval:
            findings.append(Finding(
                id="cross-001",
                title="Pipeline deploys without visible approval gate",
                severity=Severity.HIGH,
                category="governance",
                description="Pipeline appears to deploy but no manual or approval gate was detected; risky promotion flow.",
                evidence=_snippet(pipeline_text, 4),
                impacted_files=[pipeline_path_str],
                remediation_summary="Add when: manual or environment approval for production deployments.",
                source_analyzer="cross_system_analyzer",
                finding_group=finding_group,
            ))

    # --- Cross-check: Argo auto-sync with weak governance signals ---
    if argo_data and _is_argo_application(argo_data):
        spec = argo_data.get("spec", {}) or {}
        sync_policy = spec.get("syncPolicy", {}) or {}
        automated = sync_policy.get("automated")
        project = spec.get("project", "default")

        if automated and (not project or project == "default"):
            findings.append(Finding(
                id="cross-002",
                title="Argo auto-sync enabled with default project",
                severity=Severity.MEDIUM,
                category="governance",
                description="Automated sync is enabled with default or missing project; weak RBAC and namespace scoping.",
                evidence=f"project: {project}, automated: {automated}",
                impacted_files=[argo_path_str],
                remediation_summary="Use explicit AppProject and consider manual sync for production.",
                source_analyzer="cross_system_analyzer",
                finding_group=finding_group,
            ))

    # --- Cross-check: No SBOM/provenance before GitOps delivery ---
    if pipeline_text and argo_data:
        pipeline_lower = pipeline_text.lower()
        has_sbom = any(
            kw in pipeline_lower
            for kw in ("sbom", "syft", "cyclonedx", "provenance", "attestation", "slsa")
        )
        if not has_sbom:
            findings.append(Finding(
                id="cross-003",
                title="No SBOM or provenance generation before GitOps delivery",
                severity=Severity.MEDIUM,
                category="supply_chain",
                description="Pipeline does not generate SBOM or provenance before artifact reaches GitOps; limits traceability.",
                evidence=_snippet(pipeline_text, 3),
                impacted_files=[pipeline_path_str, argo_path_str],
                remediation_summary="Add SBOM/provenance step in pipeline before artifact promotion to GitOps.",
                source_analyzer="cross_system_analyzer",
                finding_group=finding_group,
            ))

    # --- Cross-check: No obvious artifact traceability from pipeline to deployment ---
    if pipeline_text and manifests:
        pipeline_lower = pipeline_text.lower()
        has_artifact_ref = any(
            x in pipeline_lower
            for x in ("artifacts", "digest", "sha256", "sbom", "provenance")
        )
        manifest_images = _extract_images_from_manifests(manifests)
        if manifest_images and not has_artifact_ref:
            findings.append(Finding(
                id="cross-004",
                title="No obvious artifact traceability between pipeline and deployment",
                severity=Severity.MEDIUM,
                category="traceability",
                description="Deployment references images but pipeline does not retain digests or SBOM for audit.",
                evidence=f"Images in manifests: {list(manifest_images)[:3]}",
                impacted_files=[pipeline_path_str] + manifest_paths_list[:2],
                remediation_summary="Retain image digests and SBOM in pipeline artifacts; reference in GitOps.",
                remediation=Remediation(
                    summary="Add artifact retention",
                    snippet="# Add artifact with digest and SBOM before deploy",
                ),
                source_analyzer="cross_system_analyzer",
                finding_group=finding_group,
            ))

    # --- Cross-check: Broad permissions with direct deployment (GitHub Actions) ---
    if pipeline_text and argo_data:
        pipeline_lower = pipeline_text.lower()
        has_deploy = any(
            x in pipeline_lower
            for x in ("deploy", "kubectl", "helm", "apply")
        )
        has_broad_perms = (
            "permissions:" in pipeline_lower
            and ("write-all" in pipeline_lower or " permissions: all" in pipeline_lower)
        )
        if has_deploy and has_broad_perms:
            findings.append(Finding(
                id="cross-006",
                title="Broad workflow permissions with direct deployment path",
                severity=Severity.MEDIUM,
                category="governance",
                description="Workflow has broad permissions and deploys; increases risk if compromised.",
                evidence=_snippet(pipeline_text, 4),
                impacted_files=[pipeline_path_str],
                remediation_summary="Use least-privilege permissions and environment protection for deploy jobs.",
                source_analyzer="cross_system_analyzer",
                finding_group=finding_group,
            ))

    # --- Cross-check: Risky promotion flow (build -> deploy without gates) ---
    if pipeline_text and argo_data:
        pipeline_lower = pipeline_text.lower()
        has_build = any(x in pipeline_lower for x in ("build", "docker", "image"))
        has_deploy = any(
            x in pipeline_lower
            for x in ("deploy", "kubectl", "helm", "apply")
        )
        has_gate = any(
            x in pipeline_lower
            for x in ("manual", "when: manual", "approval", "gate")
        )
        if has_build and has_deploy and not has_gate:
            findings.append(Finding(
                id="cross-005",
                title="Risky promotion flow: build to deploy without gate",
                severity=Severity.HIGH,
                category="governance",
                description="Pipeline builds and deploys in continuous flow; no approval gate between build and deployment.",
                evidence=_snippet(pipeline_text, 5),
                impacted_files=[pipeline_path_str],
                remediation_summary="Add manual approval or environment gate between build and deploy stages.",
                source_analyzer="cross_system_analyzer",
                finding_group=finding_group,
            ))

    return findings


def _is_argo_application(data: dict[str, Any]) -> bool:
    kind = (data.get("kind") or "").lower()
    api = data.get("apiVersion", "")
    return kind == "application" or "argoproj.io" in api


def _snippet(content: str, lines: int) -> str:
    return "\n".join(content.strip().splitlines()[:lines])


def _extract_images_from_manifests(contents: list[str]) -> set[str]:
    images: set[str] = set()
    for c in contents:
        try:
            data = yaml.safe_load(c)
        except Exception:
            continue
        if not data or not isinstance(data, dict):
            continue
        spec = data.get("spec", {}) or {}
        template = spec.get("template", {}) or {}
        pod_spec = template.get("spec", {}) or {}
        for container in pod_spec.get("containers") or []:
            if isinstance(container, dict) and container.get("image"):
                images.add(container["image"])
    return images
