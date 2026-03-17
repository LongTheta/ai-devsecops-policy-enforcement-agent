"""Core Pydantic models for review requests, findings, policies, and results."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Finding severity."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Verdict(str, Enum):
    """Overall review verdict."""

    PASS = "pass"
    PASS_WITH_WARNINGS = "pass_with_warnings"
    FAIL = "fail"


class Platform(str, Enum):
    """CI/CD or hosting platform."""

    GITLAB = "gitlab"
    GITHUB = "github"
    LOCAL = "local"


class ComplianceMapping(BaseModel):
    """Mapping of a finding to broad control families (for engineering review only)."""

    control_family: str = Field(description="e.g. AC, AU, CM, IA, IR, RA, SA, SC, SI")
    control_id: str | None = Field(default=None, description="Optional specific control ID")
    rationale: str = Field(description="Brief rationale for the mapping")
    note: str = Field(
        default="This mapping supports engineering review and is not a formal compliance determination."
    )


class Remediation(BaseModel):
    """Suggested fix for a finding."""

    summary: str = Field(description="Short remediation summary")
    description: str | None = Field(default=None, description="Detailed steps or explanation")
    snippet: str | None = Field(default=None, description="Example fixed snippet or patch")
    reference_url: str | None = Field(default=None)


class SuggestedPatch(BaseModel):
    """Patch-style suggestion (unified diff) for a finding."""

    id: str = Field(description="Unique patch suggestion ID")
    applies_to_finding_id: str = Field(description="Finding ID this patch addresses")
    diff: str = Field(description="Unified diff content")
    description: str = Field(description="What this patch changes")
    confidence: str = Field(
        default="medium",
        description="Confidence level: high, medium, low",
    )
    notes: str | None = Field(default=None, description="Caveats or org-specific notes")


class RemediationSuggestion(BaseModel):
    """Full remediation guidance for a finding."""

    id: str = Field(description="Unique remediation suggestion ID")
    applies_to_finding_id: str = Field(description="Finding ID this applies to")
    summary: str = Field(description="Short remediation summary")
    rationale: str = Field(description="Why this fix matters")
    steps: list[str] = Field(default_factory=list, description="Step-by-step guidance")
    snippet: str | None = Field(default=None, description="Example snippet (labeled as example)")
    patch: str | None = Field(default=None, description="Optional unified diff suggestion")
    confidence: str = Field(
        default="medium",
        description="Confidence level: high, medium, low",
    )
    notes: str | None = Field(default=None, description="Caveats or org-specific notes")
    is_organization_specific: bool = Field(
        default=False,
        description="True if fix requires org-specific config (vault, registry, etc.)",
    )


class Finding(BaseModel):
    """A single policy or security finding."""

    id: str = Field(description="Unique finding ID")
    title: str = Field(description="Short title")
    severity: Severity = Field(default=Severity.MEDIUM)
    category: str = Field(description="e.g. secrets, supply_chain, gitops, compliance")
    description: str = Field(description="What was found")
    evidence: str | None = Field(default=None, description="Relevant snippet or evidence")
    impacted_files: list[str] = Field(default_factory=list)
    control_families: list[ComplianceMapping] = Field(default_factory=list)
    remediation_summary: str | None = Field(default=None)
    remediation: Remediation | None = Field(default=None)
    policy_rule_id: str | None = Field(default=None, description="Triggering policy rule if any")
    source_analyzer: str = Field(default="", description="e.g. pipeline_analyzer, gitops_analyzer")
    finding_group: str | None = Field(
        default=None,
        description="Group for reporting: ci_cd, gitops, cross_system",
    )


class PolicyRule(BaseModel):
    """A single policy rule (from YAML)."""

    id: str = Field(description="Rule identifier")
    name: str = Field(description="Human-readable name")
    description: str = Field(default="")
    severity: Severity = Field(default=Severity.HIGH)
    category: str = Field(default="policy")
    enabled: bool = Field(default=True)
    config: dict[str, Any] = Field(default_factory=dict)


class PolicySet(BaseModel):
    """Loaded policy set from YAML."""

    name: str = Field(default="default")
    description: str = Field(default="")
    rules: list[PolicyRule] = Field(default_factory=list)


class ReviewContext(BaseModel):
    """Context for the review (platform, repo, compliance mode, etc.)."""

    platform: Platform = Field(default=Platform.LOCAL)
    repository_name: str | None = Field(default=None)
    branch: str | None = Field(default=None)
    environment: str | None = Field(default=None)
    hosting_model: str | None = Field(default=None)
    compliance_mode: str = Field(default="default")
    data_sensitivity: str | None = Field(default=None)
    deployment_model: str | None = Field(default=None)
    gitops_tool: str | None = Field(default=None, description="e.g. argocd, flux")
    integrations: dict[str, Any] = Field(default_factory=dict)


class ReviewRequest(BaseModel):
    """Input to a full review."""

    context: ReviewContext = Field(default_factory=ReviewContext)
    pipeline_path: str | None = Field(default=None, description="Path to CI/CD pipeline file")
    gitops_paths: list[str] = Field(default_factory=list, description="Paths to Argo CD Application manifests")
    manifest_paths: list[str] = Field(
        default_factory=list,
        description="Paths to supporting K8s manifests (Deployments, etc.)",
    )
    policy_path: str | None = Field(default=None)
    extra_paths: list[str] = Field(default_factory=list)


class ReviewResult(BaseModel):
    """Result of a full review."""

    verdict: Verdict = Field(description="pass | pass_with_warnings | fail")
    summary: str = Field(default="", description="Executive summary")
    findings: list[Finding] = Field(default_factory=list)
    policy_results: list[dict[str, Any]] = Field(default_factory=list)
    compliance_considerations: list[str] = Field(default_factory=list)
    recommended_remediations: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    context: ReviewContext = Field(default_factory=ReviewContext)
    metadata: dict[str, Any] = Field(default_factory=dict)
