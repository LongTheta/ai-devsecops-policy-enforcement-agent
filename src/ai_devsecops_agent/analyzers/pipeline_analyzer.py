"""Analyze CI/CD pipeline files for security, supply chain, and policy issues."""

import re
from pathlib import Path
from typing import Any

import yaml

from ai_devsecops_agent.models import Finding, Remediation, Severity
from ai_devsecops_agent.policies.loader import load_policy_set


def analyze_pipeline(
    content: str | None = None,
    path: str | Path | None = None,
    policy_path: str | Path | None = None,
) -> list[Finding]:
    """Inspect CI/CD YAML for insecure patterns, missing controls, and policy violations."""
    if content is None and path is None:
        return []
    if content is None:
        content = Path(path).read_text(encoding="utf-8")
    path_str = str(path) if path else "pipeline"
    findings: list[Finding] = []

    # Normalize for GitLab vs GitHub style
    data: Any = None
    try:
        data = yaml.safe_load(content)
    except Exception:
        data = None

    is_gitlab = _is_gitlab_pipeline(content, data)
    is_github = _is_github_actions(content, data)
    finding_group = "github_actions" if is_github else "ci_cd"

    # --- Plaintext secrets / credentials ---
    if _has_plaintext_secret(content):
        findings.append(Finding(
            id="pipeline-001",
            title="Possible plaintext secret or credential",
            severity=Severity.CRITICAL,
            category="secrets",
            description="Pipeline content appears to contain hardcoded credentials, API keys, or tokens.",
            evidence=_snippet(content, 2),
            impacted_files=[path_str],
            remediation_summary="Use secret variables, vault, or managed secrets; never commit secrets.",
            remediation=Remediation(
                summary="Use CI/CD secret variables",
                description="Store secrets in GitLab CI/CD variables (masked), GitHub Actions secrets, or a vault.",
                snippet="# Use variable: ${SECRET_TOKEN} or ${{ secrets.SECRET_TOKEN }}",
            ),
            source_analyzer="pipeline_analyzer",
            finding_group=finding_group,
        ))

    # --- Unpinned image / action ---
    if _has_unpinned_image_or_action(content, data):
        findings.append(Finding(
            id="pipeline-002",
            title="Unpinned container image or action",
            severity=Severity.HIGH,
            category="supply_chain",
            description="Pipeline uses an image or action without a digest or explicit tag; increases supply chain risk.",
            evidence=_snippet(content, 2),
            impacted_files=[path_str],
            remediation_summary="Pin images by digest; pin actions by full commit SHA.",
            remediation=Remediation(
                summary="Pin by digest or SHA",
                snippet="image: alpine@sha256:...  # or actions/checkout@<full-sha>",
            ),
            source_analyzer="pipeline_analyzer",
            finding_group=finding_group,
        ))

    # --- Missing SBOM / provenance step ---
    if _missing_sbom_step(content, data):
        findings.append(Finding(
            id="pipeline-003",
            title="No SBOM or provenance generation step detected",
            severity=Severity.MEDIUM,
            category="supply_chain",
            description="Pipeline does not appear to generate SBOM or build provenance; reduces artifact traceability.",
            evidence=_snippet(content, 3),
            impacted_files=[path_str],
            remediation_summary="Add a job that generates SBOM (e.g. syft, cyclonedx) and/or attestations.",
            remediation=Remediation(
                summary="Add SBOM generation",
                snippet="# Add job: syft image:tag -o cyclonedx-json=sbom.json",
            ),
            source_analyzer="pipeline_analyzer",
            finding_group=finding_group,
        ))

    # --- Unsafe script / inline curl ---
    if _has_unsafe_script(content):
        findings.append(Finding(
            id="pipeline-004",
            title="Unsafe script or inline execution",
            severity=Severity.MEDIUM,
            category="pipeline",
            description="Pipeline contains raw script blocks or inline curl that can introduce injection or supply chain risk.",
            evidence=_snippet(content, 2),
            impacted_files=[path_str],
            remediation_summary="Prefer built-in steps or well-defined scripts; avoid unchecked user input in scripts.",
            source_analyzer="pipeline_analyzer",
            finding_group=finding_group,
        ))

    # --- Missing approval / manual gate ---
    if _missing_approval_gate(content, data):
        findings.append(Finding(
            id="pipeline-005",
            title="No manual or approval gate for production",
            severity=Severity.MEDIUM,
            category="governance",
            description="No explicit manual approval or gate was detected for production-like environments.",
            evidence=_snippet(content, 2),
            impacted_files=[path_str],
            remediation_summary="Add when: manual or environment approval for production deployments.",
            source_analyzer="pipeline_analyzer",
            finding_group=finding_group,
        ))

    # --- GitLab-specific checks ---
    if is_gitlab:
        findings.extend(_analyze_gitlab_specific(content, data, path_str))

    # --- GitHub Actions-specific checks ---
    if is_github:
        findings.extend(_analyze_github_actions_specific(content, data, path_str))

    # --- Policy-driven checks ---
    if policy_path:
        policy_set = load_policy_set(policy_path)
        for rule in policy_set.rules:
            if not rule.enabled:
                continue
            if rule.id == "no_plaintext_secrets" and _has_plaintext_secret(content):
                findings.append(Finding(
                    id=f"policy-{rule.id}",
                    title=rule.name,
                    severity=rule.severity,
                    category=rule.category,
                    description=rule.description or "Plaintext secrets detected.",
                    evidence=_snippet(content, 1),
                    impacted_files=[path_str],
                    policy_rule_id=rule.id,
                    source_analyzer="pipeline_analyzer",
                    finding_group=finding_group,
                ))
            if rule.id == "require_sbom" and _missing_sbom_step(content, data):
                findings.append(Finding(
                    id=f"policy-{rule.id}",
                    title=rule.name,
                    severity=rule.severity,
                    category=rule.category,
                    description=rule.description or "SBOM step not found.",
                    evidence=_snippet(content, 1),
                    impacted_files=[path_str],
                    policy_rule_id=rule.id,
                    source_analyzer="pipeline_analyzer",
                    finding_group=finding_group,
                ))
            if rule.id == "require_pinned_pipeline_dependencies" and _has_unpinned_image_or_action(content, data):
                findings.append(Finding(
                    id=f"policy-{rule.id}",
                    title=rule.name,
                    severity=rule.severity,
                    category=rule.category,
                    description=rule.description or "Unpinned images or actions detected.",
                    evidence=_snippet(content, 1),
                    impacted_files=[path_str],
                    policy_rule_id=rule.id,
                    source_analyzer="pipeline_analyzer",
                    finding_group=finding_group,
                ))
            if rule.id == "require_manual_promotion_gate" and _missing_approval_gate(content, data):
                findings.append(Finding(
                    id=f"policy-{rule.id}",
                    title=rule.name,
                    severity=rule.severity,
                    category=rule.category,
                    description=rule.description or "No manual or approval gate detected.",
                    evidence=_snippet(content, 1),
                    impacted_files=[path_str],
                    policy_rule_id=rule.id,
                    source_analyzer="pipeline_analyzer",
                    finding_group=finding_group,
                ))
            if rule.id == "require_artifact_traceability" and _missing_artifact_traceability(content):
                findings.append(Finding(
                    id=f"policy-{rule.id}",
                    title=rule.name,
                    severity=rule.severity,
                    category=rule.category,
                    description=rule.description or "No artifact provenance or attestation detected.",
                    evidence=_snippet(content, 1),
                    impacted_files=[path_str],
                    policy_rule_id=rule.id,
                    source_analyzer="pipeline_analyzer",
                    finding_group=finding_group,
                ))
            if rule.id == "require_audit_logging_evidence" and _missing_audit_evidence(content):
                findings.append(Finding(
                    id=f"policy-{rule.id}",
                    title=rule.name,
                    severity=rule.severity,
                    category=rule.category,
                    description=rule.description or "No audit or logging evidence for deployment.",
                    evidence=_snippet(content, 1),
                    impacted_files=[path_str],
                    policy_rule_id=rule.id,
                    source_analyzer="pipeline_analyzer",
                    finding_group=finding_group,
                ))
            if rule.id == "require_signed_artifacts" and _missing_signing(content):
                findings.append(Finding(
                    id=f"policy-{rule.id}",
                    title=rule.name,
                    severity=rule.severity,
                    category=rule.category,
                    description=rule.description or "No artifact signing (e.g. cosign) detected.",
                    evidence=_snippet(content, 1),
                    impacted_files=[path_str],
                    policy_rule_id=rule.id,
                    source_analyzer="pipeline_analyzer",
                    finding_group=finding_group,
                ))

    return findings


def _is_gitlab_pipeline(content: str, data: Any) -> bool:
    """Detect GitLab CI format (stages, jobs with image/script)."""
    if not content:
        return False
    content_lower = content.lower()
    if "stages:" in content_lower or ".gitlab-ci" in content_lower:
        return True
    if data and isinstance(data, dict):
        if "stages" in data or any(k in data for k in ("build", "test", "deploy")):
            return True
    return False


def _analyze_gitlab_specific(content: str, data: Any, path_str: str) -> list[Finding]:
    """GitLab CI-specific checks: security scanning, artifact handling, promotion signals."""
    findings: list[Finding] = []
    content_lower = content.lower()
    finding_group = "ci_cd"

    # Security scanning steps (SAST, dependency_scanning, container_scanning, secret_detection)
    security_keywords = [
        "sast", "dependency_scanning", "container_scanning", "secret_detection",
        "dast", "license_scanning", "license_compliance", "trivy", "grype",
    ]
    has_security_scan = any(kw in content_lower for kw in security_keywords)
    if not has_security_scan:
        findings.append(Finding(
            id="gitlab-001",
            title="No security scanning step in GitLab pipeline",
            severity=Severity.LOW,
            category="ci_cd",
            description="GitLab pipeline does not include SAST, dependency scanning, or container scanning.",
            evidence=_snippet(content, 5),
            impacted_files=[path_str],
            remediation_summary="Add security scanning templates (e.g. sast, dependency_scanning) or third-party tools.",
            source_analyzer="pipeline_analyzer",
            finding_group=finding_group,
        ))

    # Artifact traceability: deploy stage without artifacts from build
    has_deploy = "deploy" in content_lower or "kubectl" in content_lower or "helm" in content_lower
    has_artifacts = "artifacts:" in content_lower
    if has_deploy and not has_artifacts:
        findings.append(Finding(
            id="gitlab-002",
            title="Deploy stage without artifact retention for traceability",
            severity=Severity.INFO,
            category="ci_cd",
            description="Pipeline appears to deploy but does not retain build artifacts (SBOM, digests) for audit.",
            evidence=_snippet(content, 4),
            impacted_files=[path_str],
            remediation_summary="Add artifacts retention for SBOM, image digests, or provenance before deploy.",
            source_analyzer="pipeline_analyzer",
            finding_group=finding_group,
        ))

    # Dependency pinning: package managers without lockfile
    uses_npm = "npm" in content_lower or "yarn" in content_lower
    has_lockfile = "package-lock" in content_lower or "yarn.lock" in content_lower or "pnpm-lock" in content_lower
    if uses_npm and not has_lockfile:
        findings.append(Finding(
            id="gitlab-003",
            title="Dependency install without lockfile reference",
            severity=Severity.LOW,
            category="supply_chain",
            description="Pipeline uses npm/yarn but does not reference a lockfile for reproducible builds.",
            evidence=_snippet(content, 3),
            impacted_files=[path_str],
            remediation_summary="Use npm ci or yarn install --frozen-lockfile with committed lockfile.",
            source_analyzer="pipeline_analyzer",
            finding_group=finding_group,
        ))

    return findings


def _is_github_actions(content: str, data: Any) -> bool:
    """Detect GitHub Actions workflow format (jobs, uses, runs-on)."""
    if not content:
        return False
    content_lower = content.lower()
    if "runs-on:" in content_lower or "uses:" in content_lower:
        return True
    if data and isinstance(data, dict):
        if "jobs" in data:
            return True
    return False


def _analyze_github_actions_specific(content: str, data: Any, path_str: str) -> list[Finding]:
    """GitHub Actions-specific checks: permissions, action pinning, pull_request_target, etc."""
    findings: list[Finding] = []
    content_lower = content.lower()
    finding_group = "github_actions"

    # Action pinning: uses @v1, @v2 without full SHA
    if re.search(r"uses:\s*[\w./-]+@v\d+", content) and not re.search(r"@[a-f0-9]{40}", content):
        findings.append(Finding(
            id="github-001",
            title="Action pinned by tag instead of full SHA",
            severity=Severity.MEDIUM,
            category="supply_chain",
            description="GitHub Actions uses @v1, @v2, etc.; pin by full commit SHA for supply chain integrity.",
            evidence=_snippet(content, 4),
            impacted_files=[path_str],
            remediation_summary="Pin actions with @<full-40-char-sha> or use Dependabot for action updates.",
            source_analyzer="pipeline_analyzer",
            finding_group=finding_group,
        ))

    # Broad permissions: permissions: write-all or missing (defaults to read)
    permissions = _extract_permissions(content, data)
    if permissions and permissions.get("permissions") in ("write-all", "all"):
        findings.append(Finding(
            id="github-002",
            title="Broad workflow permissions",
            severity=Severity.MEDIUM,
            category="permissions",
            description="Workflow uses write-all or all permissions; increases blast radius.",
            evidence=str(permissions),
            impacted_files=[path_str],
            remediation_summary="Use least-privilege permissions: contents: read, packages: write only if needed.",
            source_analyzer="pipeline_analyzer",
            finding_group=finding_group,
        ))

    # pull_request_target with deployment risk
    if "pull_request_target" in content_lower:
        has_deploy = any(x in content_lower for x in ("deploy", "kubectl", "helm", "apply", "push"))
        if has_deploy:
            findings.append(Finding(
                id="github-003",
                title="pull_request_target with deployment risk",
                severity=Severity.HIGH,
                category="permissions",
                description="pull_request_target runs with write access to repo; combined with deploy steps increases risk.",
                evidence=_snippet(content, 5),
                impacted_files=[path_str],
                remediation_summary="Avoid pull_request_target for deploy jobs; use push/workflow_dispatch with environment protection.",
                source_analyzer="pipeline_analyzer",
                finding_group=finding_group,
            ))

    # Secret usage: check for secrets. prefix (good) vs potential inline
    has_secrets_ref = "secrets." in content_lower or "secrets[" in content_lower
    has_plaintext = _has_plaintext_secret(content)
    if not has_secrets_ref and has_plaintext:
        pass  # Already covered by pipeline-001

    # Artifact handling: deploy without upload-artifact / artifact retention
    has_deploy = any(x in content_lower for x in ("deploy", "kubectl", "helm", "apply"))
    has_artifacts = "upload-artifact" in content_lower or "actions/upload-artifact" in content_lower
    if has_deploy and not has_artifacts:
        findings.append(Finding(
            id="github-004",
            title="Deploy job without artifact retention for traceability",
            severity=Severity.INFO,
            category="supply_chain",
            description="Workflow deploys but does not retain SBOM, digests, or provenance as artifacts.",
            evidence=_snippet(content, 4),
            impacted_files=[path_str],
            remediation_summary="Add actions/upload-artifact for SBOM, image digests, or attestations before deploy.",
            source_analyzer="pipeline_analyzer",
            finding_group=finding_group,
        ))

    # Dependency/image pinning: container: without digest
    if re.search(r"container:\s*[\w./-]+:[\w.-]+", content) and not re.search(r"@sha256:", content):
        findings.append(Finding(
            id="github-005",
            title="Container image without digest",
            severity=Severity.LOW,
            category="supply_chain",
            description="Job uses container: image:tag without @sha256 digest.",
            evidence=_snippet(content, 3),
            impacted_files=[path_str],
            remediation_summary="Pin container images by digest: image@sha256:...",
            source_analyzer="pipeline_analyzer",
            finding_group=finding_group,
        ))

    # No environment protection for deploy
    has_deploy = any(x in content_lower for x in ("deploy", "kubectl", "helm", "apply"))
    has_environment = "environment:" in content_lower
    if has_deploy and not has_environment:
        findings.append(Finding(
            id="github-006",
            title="Deploy job without environment protection",
            severity=Severity.MEDIUM,
            category="governance",
            description="Deploy job does not use environment: production; no approval gates or protection rules.",
            evidence=_snippet(content, 2),
            impacted_files=[path_str],
            remediation_summary="Add environment: production to deploy job for required reviewers.",
            source_analyzer="pipeline_analyzer",
            finding_group=finding_group,
        ))

    return findings


def _extract_permissions(content: str, data: Any) -> dict[str, Any] | None:
    """Extract top-level or job-level permissions."""
    if data and isinstance(data, dict):
        if "permissions" in data:
            return {"permissions": str(data.get("permissions"))}
        for job_name, job in (data.get("jobs") or {}).items():
            if isinstance(job, dict) and job.get("permissions"):
                return {"job": job_name, "permissions": str(job.get("permissions"))}
    if "permissions:" in content.lower() and ("write-all" in content.lower() or "all" in content.lower()):
        return {"permissions": "write-all"}
    return None


def _snippet(content: str, lines: int = 3) -> str:
    """Return first few lines as evidence snippet."""
    return "\n".join(content.strip().splitlines()[:lines])


def _has_plaintext_secret(content: str) -> bool:
    """Heuristic: likely plaintext secret patterns."""
    patterns = [
        r"(?i)password\s*[:=]\s*['\"]?[^\s'\"]+",
        r"(?i)api[_-]?key\s*[:=]\s*['\"]?[a-zA-Z0-9_\-]{20,}",
        r"(?i)secret\s*[:=]\s*['\"]?[a-zA-Z0-9_\-]{16,}",
        r"ghp_[a-zA-Z0-9]{36}",
        r"glpat-[a-zA-Z0-9\-]{20,}",
        r"AKIA[0-9A-Z]{16}",
    ]
    for p in patterns:
        if re.search(p, content):
            return True
    return False


def _has_unpinned_image_or_action(content: str, data: Any) -> bool:
    """Detect :latest or action without @sha."""
    if re.search(r"image:\s*[\w./-]+:latest", content, re.IGNORECASE):
        return True
    if re.search(r"uses:\s*[\w./-]+@v\d+", content) and not re.search(r"@[a-f0-9]{40}", content):
        return True
    if data and isinstance(data, dict):
        for key in ("image", "services", "default"):
            _traverse_for_unpinned(data, key, findings_ref := [])
            if findings_ref:
                return True
    return False


def _traverse_for_unpinned(obj: Any, key: str, out: list[bool]) -> None:
    """Traverse dict/list for image/key and check for latest."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key and isinstance(v, str) and ("latest" in v.lower() or not "@sha256:" in v):
                out.append(True)
            _traverse_for_unpinned(v, key, out)
    elif isinstance(obj, list):
        for i in obj:
            _traverse_for_unpinned(i, key, out)


def _missing_sbom_step(content: str, data: Any) -> bool:
    """Detect absence of SBOM/provenance keywords."""
    content_lower = content.lower()
    sbom_keywords = ["sbom", "syft", "cyclonedx", "provenance", "attestation", "slsa", "in-toto"]
    if any(kw in content_lower for kw in sbom_keywords):
        return False
    return True


def _has_unsafe_script(content: str) -> bool:
    """Simple heuristic: script block or curl with variable."""
    if re.search(r"script:\s*[-|\n]", content) or re.search(r"run:\s*[-|\n]", content):
        if "curl" in content.lower() and "$" in content:
            return True
    return bool(re.search(r"curl\s+.*\$\{", content))


def _missing_artifact_traceability(content: str) -> bool:
    """Detect absence of artifact provenance, attestation, or digest retention."""
    content_lower = content.lower()
    traceability_keywords = ["artifacts", "digest", "sha256", "sbom", "provenance", "attestation", "upload-artifact"]
    return not any(kw in content_lower for kw in traceability_keywords)


def _missing_signing(content: str) -> bool:
    """Detect absence of artifact signing (cosign, sign, etc.)."""
    content_lower = content.lower()
    signing_keywords = ["cosign", "sign", "signed", "signing", "sigstore"]
    return not any(kw in content_lower for kw in signing_keywords)


def _missing_audit_evidence(content: str) -> bool:
    """Detect absence of audit or logging signals for deployment."""
    content_lower = content.lower()
    has_deploy = any(x in content_lower for x in ("deploy", "kubectl", "helm", "apply"))
    if not has_deploy:
        return False
    audit_keywords = ["environment:", "audit", "log", "trace", "evidence"]
    return not any(kw in content_lower for kw in audit_keywords)


def _missing_approval_gate(content: str, data: Any) -> bool:
    """Detect absence of when:manual, environment approval, or GitHub environment protection."""
    content_lower = content.lower()
    if "manual" in content_lower or "when: manual" in content_lower:
        return False
    # GitHub: environment: production triggers protection rules
    if "environment:" in content_lower and ("production" in content_lower or "prod" in content_lower):
        return False
    return "approval" not in content_lower and "gate" not in content_lower
