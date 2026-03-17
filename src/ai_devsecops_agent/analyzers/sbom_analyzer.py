"""Analyze pipelines for SBOM, provenance, and supply chain controls."""

from pathlib import Path
from typing import Any

from ai_devsecops_agent.models import Finding, Severity


def analyze_sbom(
    content: str | None = None,
    path: str | Path | None = None,
    data: Any = None,
) -> list[Finding]:
    """
    Rule-based detection: SBOM generation step, provenance/attestation references.
    Does not parse SBOM contents; only checks for presence/absence of supply chain steps.
    """
    if content is None and path is None:
        return []
    if content is None:
        content = Path(path).read_text(encoding="utf-8")
    path_str = str(path) if path else "pipeline"
    findings: list[Finding] = []

    content_lower = content.lower()

    # Presence of SBOM/provenance
    has_sbom = any(kw in content_lower for kw in ("sbom", "syft", "cyclonedx", "trivy", "bom"))
    has_provenance = any(kw in content_lower for kw in ("provenance", "attestation", "slsa", "in-toto", "sigstore"))
    has_signing = any(kw in content_lower for kw in ("cosign", "sign", "signed", "signing"))

    # finding_group assigned by workflow based on platform (github_actions vs ci_cd)

    if not has_sbom:
        findings.append(Finding(
            id="sbom-001",
            title="No SBOM generation step detected",
            severity=Severity.MEDIUM,
            category="supply_chain",
            description="Pipeline does not appear to generate a Software Bill of Materials (SBOM).",
            evidence=content[:500] if len(content) > 500 else content,
            impacted_files=[path_str],
            remediation_summary="Add a step to generate SBOM (e.g. syft, cyclonedx) and publish or archive it.",
            source_analyzer="sbom_analyzer",
        ))

    if not has_provenance and not has_signing:
        findings.append(Finding(
            id="sbom-002",
            title="No build provenance or artifact signing detected",
            severity=Severity.LOW,
            category="supply_chain",
            description="No attestation or signing step was detected; artifact traceability may be limited.",
            evidence=content[:300] if len(content) > 300 else content,
            impacted_files=[path_str],
            remediation_summary="Consider adding SLSA provenance or cosign/signing for critical artifacts.",
            source_analyzer="sbom_analyzer",
        ))

    return findings
