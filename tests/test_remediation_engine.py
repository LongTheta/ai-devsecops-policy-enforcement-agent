"""Tests for the auto-remediation engine."""

from ai_devsecops_agent.models import Finding, Severity
from ai_devsecops_agent.remediation.engine import generate_patch, generate_remediation


def test_generate_remediation_plaintext_secrets():
    f = Finding(
        id="pipeline-001",
        title="Plaintext secret",
        severity=Severity.CRITICAL,
        category="secrets",
        description="Hardcoded API key.",
    )
    rem = generate_remediation(f)
    assert rem is not None
    assert rem.applies_to_finding_id == "pipeline-001"
    assert "secret" in rem.summary.lower()
    assert rem.rationale
    assert len(rem.steps) >= 2
    assert rem.snippet
    assert rem.confidence in ("high", "medium", "low")
    assert rem.is_organization_specific is True


def test_generate_remediation_sbom():
    f = Finding(
        id="pipeline-003",
        title="Missing SBOM",
        severity=Severity.MEDIUM,
        category="supply_chain",
        description="No SBOM step.",
    )
    rem = generate_remediation(f)
    assert rem is not None
    assert "SBOM" in rem.summary
    assert rem.steps
    assert "syft" in rem.snippet.lower()


def test_generate_remediation_unpinned_image():
    f = Finding(
        id="pipeline-002",
        title="Unpinned image",
        severity=Severity.HIGH,
        category="supply_chain",
        description="Image uses :latest.",
        evidence="image: node:latest",
    )
    rem = generate_remediation(f)
    assert rem is not None
    assert "digest" in rem.summary.lower() or "pin" in rem.summary.lower()
    assert rem.patch is not None
    assert "node:latest" in rem.patch
    assert "-" in rem.patch and "+" in rem.patch


def test_generate_remediation_k8s_resources():
    f = Finding(
        id="gitops-003",
        title="Missing resource limits",
        severity=Severity.MEDIUM,
        category="gitops",
        description="No limits.",
    )
    rem = generate_remediation(f)
    assert rem is not None
    assert "resource" in rem.summary.lower()
    assert rem.patch is not None
    assert "limits" in rem.patch


def test_generate_remediation_policy_artifact_traceability():
    f = Finding(
        id="policy-require_artifact_traceability",
        title="Artifact traceability",
        severity=Severity.MEDIUM,
        category="supply_chain",
        description="No artifact provenance.",
    )
    rem = generate_remediation(f)
    assert rem is not None
    assert "artifact" in rem.summary.lower() or "traceability" in rem.summary.lower()
    assert rem.steps
    assert rem.snippet


def test_generate_remediation_unknown_finding():
    f = Finding(
        id="unknown-999",
        title="Unknown",
        severity=Severity.LOW,
        category="other",
        description="No template.",
    )
    rem = generate_remediation(f)
    assert rem is None


def test_generate_patch():
    f = Finding(
        id="github-002",
        title="Broad permissions",
        severity=Severity.MEDIUM,
        category="permissions",
        description="write-all",
        evidence="permissions: write-all",
    )
    patch = generate_patch(f)
    assert patch is not None
    assert patch.applies_to_finding_id == "github-002"
    assert "write-all" in patch.diff
    assert patch.confidence


def test_generate_remediation_category_fallback():
    """Unknown finding ID with known category gets generic remediation."""
    f = Finding(
        id="custom-secret-001",
        title="Custom secret finding",
        severity=Severity.HIGH,
        category="secrets",
        description="Found a secret.",
    )
    rem = generate_remediation(f)
    assert rem is not None
    assert rem.applies_to_finding_id == "custom-secret-001"
    assert "secret" in rem.summary.lower()
    assert rem.confidence == "low"


def test_generate_remediation_has_title_and_limitations():
    """Remediation includes title and limitations when in template."""
    f = Finding(
        id="pipeline-001",
        title="Plaintext secret",
        severity=Severity.CRITICAL,
        category="secrets",
        description="Hardcoded key.",
    )
    rem = generate_remediation(f)
    assert rem is not None
    assert rem.title is not None
    assert "plaintext" in rem.title.lower() or "secret" in rem.title.lower()
    assert len(rem.limitations) >= 1


def test_generate_remediation_bundle():
    """RemediationBundle aggregates remediations and patches."""
    from ai_devsecops_agent.models import ReviewResult, Verdict
    from ai_devsecops_agent.remediation.engine import generate_remediation_bundle

    result = ReviewResult(
        verdict=Verdict.FAIL,
        summary="Failed",
        findings=[
            Finding(
                id="pipeline-002",
                title="Unpinned image",
                severity=Severity.HIGH,
                category="supply_chain",
                description="Image uses :latest",
                evidence="image: node:latest",
            ),
            Finding(
                id="gitops-003",
                title="Missing limits",
                severity=Severity.MEDIUM,
                category="gitops",
                description="No limits",
            ),
        ],
    )
    bundle = generate_remediation_bundle(result)
    assert bundle.finding_count == 2
    assert bundle.remediation_count >= 1
    assert bundle.patch_count >= 1
    assert len(bundle.limitations) >= 1
