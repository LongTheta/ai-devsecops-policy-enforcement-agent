"""Map findings to broad control families (AC, AU, CM, IA, IR, RA, SA, SC, SI) for engineering review."""

from ai_devsecops_agent.models import ComplianceMapping, Finding

# Category / rule-id -> list of (family, rationale)
_CONTROL_HINTS: dict[str, list[tuple[str, str]]] = {
    "secrets": [
        ("IA", "Identity and access – secret management and credential handling"),
        ("SC", "System and communications – protection of sensitive data"),
    ],
    "supply_chain": [
        ("SA", "System and services acquisition – supply chain and SBOM"),
        ("SI", "System and information integrity – software integrity and provenance"),
    ],
    "gitops": [
        ("CM", "Configuration management – baseline and change control"),
        ("AU", "Audit and accountability – deployment traceability"),
    ],
    "governance": [
        ("CM", "Configuration management – change approval and promotion gates"),
        ("RA", "Risk assessment – deployment risk and approvals"),
    ],
    "pipeline": [
        ("SI", "System and information integrity – build and pipeline integrity"),
        ("SA", "System and services acquisition – development and build process"),
    ],
    "policy": [
        ("CM", "Configuration management – policy enforcement"),
        ("AU", "Audit and accountability – policy compliance evidence"),
    ],
}


def map_finding_to_controls(finding: Finding) -> list[ComplianceMapping]:
    """
    Map a finding to broad NIST-style control families.
    Mappings support engineering review and are not formal compliance determinations.
    """
    note = "This mapping supports engineering review and is not a formal compliance determination."
    out: list[ComplianceMapping] = []

    hints = _CONTROL_HINTS.get(finding.category, [])
    for family, rationale in hints:
        out.append(ComplianceMapping(
            control_family=family,
            control_id=None,
            rationale=rationale,
            note=note,
        ))

    # Severity-based hint: critical/high often touch IA, AU, SI
    if finding.severity.value in ("critical", "high") and not out:
        out.append(ComplianceMapping(
            control_family="SI",
            control_id=None,
            rationale="High/critical finding may affect system and information integrity.",
            note=note,
        ))

    return out


def enrich_findings_with_controls(findings: list[Finding]) -> list[Finding]:
    """Add control_families to findings that do not have them."""
    result: list[Finding] = []
    for f in findings:
        if not f.control_families:
            mappings = map_finding_to_controls(f)
            result.append(f.model_copy(update={"control_families": mappings}))
        else:
            result.append(f)
    return result
