"""Deterministic auto-remediation engine for CI/CD, GitOps, and supply-chain findings."""

import re
from typing import Any

from ai_devsecops_agent.models import (
    Finding,
    RemediationBundle,
    RemediationSuggestion,
    ReviewResult,
    SuggestedPatch,
)

# Minimum confidence to return remediation; "low" with no template returns None
_MIN_CONFIDENCE = "low"

# Snippet prefix to label examples (do not apply verbatim)
_SNIPPET_LABEL = "# EXAMPLE - adjust for your environment; do not apply verbatim\n"

# Registry: finding_id -> RemediationSuggestion template (without applies_to_finding_id)
# Optional keys: title, limitations (list)
_REMEDIATION_REGISTRY: dict[str, dict[str, Any]] = {
    # --- Plaintext secrets ---
    "pipeline-001": {
        "title": "Replace plaintext secrets with CI/CD variables",
        "summary": "Remove plaintext secrets; use CI/CD secret variables or vault",
        "rationale": "Hardcoded credentials can be exfiltrated via repo access, logs, or artifact leaks. Use masked variables or a secrets manager.",
        "limitations": ["Requires org-specific secret store configuration; cannot auto-edit files."],
        "steps": [
            "Remove the plaintext value from the pipeline/config file.",
            "Add the secret to GitLab CI/CD variables (masked), GitHub Actions secrets, or HashiCorp Vault.",
            "Reference via variable: ${API_KEY} or ${{ secrets.API_KEY }}.",
        ],
        "snippet": "# Example (GitLab):\nvariables:\n  API_KEY: $CI_JOB_TOKEN  # Set in CI/CD settings\n# Example (GitHub): ${{ secrets.API_KEY }}",
        "patch": None,
        "confidence": "high",
        "notes": "Organization-specific: configure your vault or CI/CD secret store.",
        "is_organization_specific": True,
    },
    "policy-no_plaintext_secrets": {
        "summary": "Remove plaintext secrets; use CI/CD secret variables or vault",
        "rationale": "Hardcoded credentials violate policy and increase breach risk.",
        "steps": [
            "Remove the plaintext value from the file.",
            "Store in your organization's approved secret store.",
            "Reference via CI/CD variable or secrets API.",
        ],
        "snippet": "# Use variable: ${SECRET_TOKEN} or ${{ secrets.SECRET_TOKEN }}",
        "patch": None,
        "confidence": "high",
        "notes": None,
        "is_organization_specific": True,
    },
    # --- Missing SBOM ---
    "pipeline-003": {
        "summary": "Add an SBOM generation step to the pipeline",
        "rationale": "SBOM enables supply chain visibility, vulnerability scanning, and compliance evidence.",
        "steps": [
            "Add a job or step that runs syft, cyclonedx-cli, or similar.",
            "Output SPDX or CycloneDX JSON.",
            "Retain the artifact (upload-artifact, artifacts.paths) for audit.",
        ],
        "snippet": "# Example (GitHub Actions):\n- name: Generate SBOM\n  run: syft . -o cyclonedx-json > sbom.json\n- uses: actions/upload-artifact@v4\n  with:\n    name: sbom\n    path: sbom.json",
        "patch": None,
        "confidence": "high",
        "notes": "Example uses syft; adjust for your toolchain.",
        "is_organization_specific": False,
    },
    "sbom-001": {
        "summary": "Add SBOM generation step",
        "rationale": "SBOM is required for supply chain visibility and compliance.",
        "steps": [
            "Add a step to generate SBOM (e.g. syft, cyclonedx).",
            "Publish or archive the artifact.",
        ],
        "snippet": "- name: Generate SBOM\n  run: syft . -o cyclonedx-json > sbom.json",
        "patch": None,
        "confidence": "high",
        "notes": None,
        "is_organization_specific": False,
    },
    # --- Unpinned container image ---
    "pipeline-002": {
        "title": "Pin container images by digest",
        "summary": "Pin container images by digest",
        "limitations": ["Digest must be resolved manually; patch shows pattern only."],
        "rationale": "Unpinned images (e.g. :latest) can change without notice, breaking builds or introducing vulnerabilities.",
        "steps": [
            "Resolve the image to a specific digest: docker pull image:tag && docker inspect --format='{{.RepoDigests}}'.",
            "Replace image:tag with image@sha256:... in the pipeline.",
        ],
        "snippet": "# Before: image: alpine:latest\n# After: image: alpine@sha256:c0e9560cda118f9ec63ddefb4a173a2b2a0347082d7dff7dc14236e73a05ce6f",
        "patch": None,
        "confidence": "high",
        "notes": "Digest values are example; resolve for your image.",
        "is_organization_specific": False,
    },
    # --- Unpinned GitHub Action ---
    "github-001": {
        "summary": "Pin GitHub Actions by full commit SHA",
        "rationale": "Tag-based pins (@v1, @v2) can be moved; SHA pins are immutable.",
        "steps": [
            "Look up the action's latest commit SHA (e.g. from GitHub).",
            "Replace uses: owner/repo@v1 with uses: owner/repo@<full-40-char-sha>.",
        ],
        "snippet": "# Before: uses: actions/checkout@v4\n# After: uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11",
        "patch": None,
        "confidence": "high",
        "notes": "Use Dependabot for action updates.",
        "is_organization_specific": False,
    },
    # --- Risky Argo CD automated sync ---
    "gitops-001": {
        "summary": "Use manual sync for production or restrict automated sync",
        "rationale": "Automated sync with prune/selfHeal can overwrite local changes and bypass approval gates.",
        "steps": [
            "For production: remove syncPolicy.automated or set to manual sync.",
            "Or restrict prune/selfHeal to non-production namespaces.",
            "Pair with GitOps Promoter or environment protection for promotion.",
        ],
        "snippet": "# For production, prefer manual sync:\nsyncPolicy: {}  # Remove automated block\n# Or: automated:\n#   prune: false\n#   selfHeal: false",
        "patch": None,
        "confidence": "high",
        "notes": "Organization-specific: align with your promotion model.",
        "is_organization_specific": True,
    },
    "argo-001": {
        "title": "Restrict Argo CD automated sync",
        "summary": "Disable prune and selfHeal for production, or use manual sync",
        "limitations": ["Placement depends on your Argo Application structure."],
        "rationale": "Both prune and selfHeal together increase drift/override risk without explicit approval.",
        "steps": [
            "Set prune: false and selfHeal: false for production apps.",
            "Or remove automated sync entirely for prod.",
        ],
        "snippet": "syncPolicy:\n  automated:\n    prune: false\n    selfHeal: false",
        "patch": None,
        "confidence": "high",
        "notes": None,
        "is_organization_specific": False,
    },
    # --- Missing promotion / approval gate ---
    "pipeline-005": {
        "summary": "Add manual or environment approval for production deployments",
        "rationale": "Without a gate, changes deploy automatically and bypass human review.",
        "steps": [
            "Add when: manual to the deploy job (GitLab), or environment: production (GitHub).",
            "Configure required reviewers in GitLab/GitHub settings.",
        ],
        "snippet": "# GitLab:\ndeploy:\n  when: manual\n  environment: production\n# GitHub: add environment: production to deploy job",
        "patch": None,
        "confidence": "high",
        "notes": "Configure environment protection rules in your platform.",
        "is_organization_specific": True,
    },
    "cross-001": {
        "summary": "Add approval gate before deployment",
        "rationale": "Pipeline deploys without a visible gate; risky promotion flow.",
        "steps": [
            "Add when: manual (GitLab) or environment: production (GitHub) to the deploy job.",
            "Configure required reviewers.",
        ],
        "snippet": "deploy:\n  when: manual\n  environment: production",
        "patch": None,
        "confidence": "high",
        "notes": None,
        "is_organization_specific": True,
    },
    "cross-005": {
        "summary": "Add manual approval or environment gate between build and deploy",
        "rationale": "Continuous build-to-deploy without a gate bypasses review.",
        "steps": [
            "Split deploy into a separate job with when: manual or environment: production.",
            "Configure required reviewers.",
        ],
        "snippet": "deploy:\n  when: manual\n  environment: production",
        "patch": None,
        "confidence": "high",
        "notes": None,
        "is_organization_specific": True,
    },
    "github-006": {
        "summary": "Add environment: production to deploy job",
        "rationale": "Environment protection triggers required reviewers.",
        "steps": [
            "Add environment: production to the deploy job.",
            "Configure protection rules in GitHub repo settings.",
        ],
        "snippet": "deploy:\n  environment: production\n  steps:\n    - run: ...",
        "patch": None,
        "confidence": "high",
        "notes": None,
        "is_organization_specific": True,
    },
    # --- Missing provenance / signing ---
    "sbom-002": {
        "summary": "Add build provenance or artifact signing",
        "rationale": "Provenance and signing enable artifact traceability and tamper detection.",
        "steps": [
            "Add SLSA provenance generation (e.g. GitHub's built-in, or in-toto).",
            "Or add cosign/signing for critical artifacts.",
        ],
        "snippet": "# Example: cosign sign\n- name: Sign SBOM\n  run: cosign sign-blob sbom.json --output-signature sbom.sig",
        "patch": None,
        "confidence": "medium",
        "notes": "Requires key management; org-specific.",
        "is_organization_specific": True,
    },
    # --- Missing Kubernetes resource requests/limits ---
    "gitops-003": {
        "summary": "Add resource requests and limits to workload",
        "rationale": "Missing limits can lead to resource exhaustion and noisy-neighbor issues.",
        "steps": [
            "Add resources.requests and resources.limits to each container.",
            "Set memory and cpu based on observed usage.",
        ],
        "snippet": "resources:\n  requests:\n    memory: 256Mi\n    cpu: 100m\n  limits:\n    memory: 512Mi\n    cpu: 500m",
        "patch": None,
        "confidence": "high",
        "notes": "Adjust values for your workload.",
        "is_organization_specific": False,
    },
    # --- Additional coverage ---
    "gitlab-001": {
        "summary": "Add security scanning to GitLab pipeline",
        "rationale": "SAST, dependency scanning, and container scanning improve security posture.",
        "steps": [
            "Include GitLab security templates or add third-party tools (Trivy, Grype).",
        ],
        "snippet": "include:\n  - template: Security/SAST.gitlab-ci.yml",
        "patch": None,
        "confidence": "high",
        "notes": None,
        "is_organization_specific": False,
    },
    "gitlab-002": {
        "summary": "Retain build artifacts (SBOM, digests) for audit",
        "rationale": "Artifact retention supports traceability and compliance.",
        "steps": [
            "Add artifacts block to retain SBOM, image digests, or provenance.",
        ],
        "snippet": "artifacts:\n  paths:\n    - sbom.json\n  expire_in: 30 days",
        "patch": None,
        "confidence": "high",
        "notes": None,
        "is_organization_specific": False,
    },
    "github-002": {
        "summary": "Use least-privilege permissions",
        "rationale": "Broad permissions increase blast radius if workflow is compromised.",
        "steps": [
            "Replace permissions: write-all with specific scopes.",
            "Use contents: read, packages: write only if needed.",
        ],
        "snippet": "permissions:\n  contents: read\n  packages: write",
        "patch": None,
        "confidence": "high",
        "notes": None,
        "is_organization_specific": False,
    },
    "github-003": {
        "summary": "Avoid pull_request_target for deploy jobs",
        "rationale": "pull_request_target grants write access; combined with deploy increases risk.",
        "steps": [
            "Use push or workflow_dispatch for deploy jobs.",
            "Use environment protection for approval.",
        ],
        "snippet": "on:\n  push:\n    branches: [main]\n  workflow_dispatch:",
        "patch": None,
        "confidence": "high",
        "notes": None,
        "is_organization_specific": False,
    },
    "github-004": {
        "summary": "Retain SBOM or digests as artifacts before deploy",
        "rationale": "Artifact retention supports traceability.",
        "steps": [
            "Add actions/upload-artifact for SBOM, image digests, or attestations.",
        ],
        "snippet": "- uses: actions/upload-artifact@v4\n  with:\n    name: sbom\n    path: sbom.json",
        "patch": None,
        "confidence": "high",
        "notes": None,
        "is_organization_specific": False,
    },
    "github-005": {
        "summary": "Pin container image by digest",
        "rationale": "Tag-based pins can change; digest is immutable.",
        "steps": [
            "Resolve image to digest and use image@sha256:...",
        ],
        "snippet": "container: alpine@sha256:...",
        "patch": None,
        "confidence": "high",
        "notes": None,
        "is_organization_specific": False,
    },
    "gitops-002": {
        "summary": "Use explicit Argo CD AppProject",
        "rationale": "Default project has weak RBAC and namespace scoping.",
        "steps": [
            "Create an AppProject for the app.",
            "Set spec.project to the project name.",
        ],
        "snippet": "spec:\n  project: myapp-prod",
        "patch": None,
        "confidence": "high",
        "notes": "Organization-specific: create project in your Argo CD.",
        "is_organization_specific": True,
    },
    "gitops-005": {
        "title": "Set imagePullPolicy for mutable tags",
        "summary": "Use imagePullPolicy: Always when using mutable tags or :latest",
        "rationale": "IfNotPresent (default) can cache stale images; Always ensures fresh pull for mutable tags.",
        "steps": [
            "Add imagePullPolicy: Always to containers using :latest or mutable tags.",
            "Or pin by digest and use IfNotPresent.",
        ],
        "snippet": "containers:\n  - name: app\n    image: myapp:latest\n    imagePullPolicy: Always",
        "patch": None,
        "confidence": "high",
        "limitations": ["Placement depends on container structure."],
        "notes": "Prefer pinning by digest over Always.",
        "is_organization_specific": False,
    },
    "gitops-004": {
        "summary": "Add pod securityContext",
        "rationale": "securityContext (runAsNonRoot, etc.) reduces container escape risk.",
        "steps": [
            "Add securityContext to pod spec.",
        ],
        "snippet": "securityContext:\n  runAsNonRoot: true\n  runAsUser: 1000",
        "patch": None,
        "confidence": "high",
        "notes": None,
        "is_organization_specific": False,
    },
    "argo-002": {
        "summary": "Use tagged revision for production",
        "rationale": "HEAD on prod path has no promotion pin for traceability.",
        "steps": [
            "Use targetRevision: v1.2.3 or a GitOps promotion tag.",
        ],
        "snippet": "source:\n  targetRevision: v1.2.3",
        "patch": None,
        "confidence": "high",
        "notes": None,
        "is_organization_specific": False,
    },
    "cross-002": {
        "summary": "Use explicit AppProject and consider manual sync",
        "rationale": "Auto-sync with default project has weak governance.",
        "steps": [
            "Set spec.project to explicit AppProject.",
            "Consider manual sync for production.",
        ],
        "snippet": "spec:\n  project: myapp-prod",
        "patch": None,
        "confidence": "high",
        "notes": None,
        "is_organization_specific": True,
    },
    "cross-003": {
        "summary": "Add SBOM/provenance step before GitOps delivery",
        "rationale": "Artifact reaches GitOps without traceability.",
        "steps": [
            "Add SBOM generation in pipeline before artifact promotion.",
        ],
        "snippet": "- name: Generate SBOM\n  run: syft . -o cyclonedx-json > sbom.json",
        "patch": None,
        "confidence": "high",
        "notes": None,
        "is_organization_specific": False,
    },
    "cross-004": {
        "summary": "Retain image digests and SBOM in pipeline artifacts",
        "rationale": "Deployment references images but pipeline does not retain digests.",
        "steps": [
            "Add artifact retention for SBOM and image digests.",
        ],
        "snippet": "artifacts:\n  paths:\n    - sbom.json\n    - image-digest.txt",
        "patch": None,
        "confidence": "high",
        "notes": None,
        "is_organization_specific": False,
    },
    "cross-006": {
        "summary": "Use least-privilege permissions and environment protection",
        "rationale": "Broad permissions with direct deploy increases risk.",
        "steps": [
            "Narrow permissions.",
            "Add environment protection for deploy.",
        ],
        "snippet": "permissions:\n  contents: read\n  packages: write",
        "patch": None,
        "confidence": "high",
        "notes": None,
        "is_organization_specific": False,
    },
    "pipeline-004": {
        "summary": "Prefer built-in steps or well-defined scripts",
        "rationale": "Raw script blocks with curl and variables can introduce injection risk.",
        "steps": [
            "Replace inline scripts with dedicated scripts or built-in steps.",
            "Avoid unchecked user input in scripts.",
        ],
        "snippet": "script:\n  - ./scripts/validate.sh",
        "patch": None,
        "confidence": "medium",
        "notes": None,
        "is_organization_specific": False,
    },
    "gitlab-003": {
        "summary": "Use npm ci or yarn with lockfile",
        "rationale": "Lockfile ensures reproducible builds.",
        "steps": [
            "Use npm ci or yarn install --frozen-lockfile.",
            "Commit package-lock.json or yarn.lock.",
        ],
        "snippet": "script:\n  - npm ci",
        "patch": None,
        "confidence": "high",
        "notes": None,
        "is_organization_specific": False,
    },
    "policy-require_sbom": {
        "summary": "Add SBOM generation step",
        "rationale": "Policy requires SBOM for supply chain visibility.",
        "steps": [
            "Add syft, cyclonedx, or similar step.",
            "Retain artifact.",
        ],
        "snippet": "- name: Generate SBOM\n  run: syft . -o cyclonedx-json > sbom.json",
        "patch": None,
        "confidence": "high",
        "notes": None,
        "is_organization_specific": False,
    },
    "policy-require_artifact_traceability": {
        "summary": "Add artifact retention and provenance tracking",
        "rationale": "Artifact traceability (digest, SBOM, provenance) supports audit and compliance.",
        "steps": [
            "Add artifacts block or upload-artifact to retain SBOM, digests, or attestations.",
            "Include image digest in deploy or artifact metadata.",
        ],
        "snippet": "# GitLab:\nartifacts:\n  paths:\n    - sbom.json\n    - image-digest.txt\n# GitHub:\n- uses: actions/upload-artifact@v4\n  with:\n    name: sbom\n    path: sbom.json",
        "patch": None,
        "confidence": "high",
        "notes": None,
        "is_organization_specific": False,
    },
    "policy-require_audit_logging_evidence": {
        "summary": "Add audit or logging evidence for deployments",
        "rationale": "Deployment actions must be auditable for compliance and incident response.",
        "steps": [
            "Add environment: production (GitHub) or environment: name (GitLab) to deploy jobs.",
            "Ensure CI logs are retained; consider structured logging.",
        ],
        "snippet": "deploy:\n  environment: production\n  script:\n    - echo 'Deploying to production'",
        "patch": None,
        "confidence": "medium",
        "notes": "Configure log retention in your platform.",
        "is_organization_specific": True,
    },
    "policy-require_signed_artifacts": {
        "summary": "Add artifact signing (e.g. cosign)",
        "rationale": "Signed artifacts enable tamper detection and supply chain integrity.",
        "steps": [
            "Add cosign sign step for container images or SBOM.",
            "Verify signatures before deploy.",
        ],
        "snippet": "- name: Sign image\n  run: cosign sign --key cosign.key $IMAGE",
        "patch": None,
        "confidence": "high",
        "notes": "Requires key management; organization-specific.",
        "is_organization_specific": True,
    },
    "policy-require_manual_promotion_gate": {
        "summary": "Add manual or environment approval for production",
        "rationale": "Policy requires explicit approval before production deployment.",
        "steps": [
            "Add when: manual (GitLab) or environment: production (GitHub) to deploy job.",
            "Configure required reviewers in platform settings.",
        ],
        "snippet": "deploy:\n  when: manual\n  environment: production",
        "patch": None,
        "confidence": "high",
        "notes": "Configure environment protection rules.",
        "is_organization_specific": True,
    },
    "policy-require_pinned_pipeline_dependencies": {
        "summary": "Pin images and actions by digest or SHA",
        "rationale": "Unpinned dependencies can change without notice.",
        "steps": [
            "Replace image:tag with image@sha256:... for containers.",
            "Replace uses: owner/repo@v1 with uses: owner/repo@<full-sha> for GitHub Actions.",
        ],
        "snippet": "# Before: image: alpine:latest\n# After: image: alpine@sha256:...",
        "patch": None,
        "confidence": "high",
        "notes": None,
        "is_organization_specific": False,
    },
}


# Category-based fallback for unknown finding IDs (generic guidance only)
_CATEGORY_FALLBACK: dict[str, dict[str, Any]] = {
    "secrets": {
        "title": "Address secret exposure",
        "summary": "Remove hardcoded secrets; use CI/CD variables or vault.",
        "rationale": "Secrets in config files can be exfiltrated.",
        "steps": ["Remove plaintext value.", "Store in approved secret store.", "Reference via variable."],
        "snippet": "# Use ${VAR} or ${{ secrets.VAR }}",
        "confidence": "low",
        "limitations": ["Generic guidance; org-specific implementation required."],
        "is_organization_specific": True,
    },
    "supply_chain": {
        "title": "Improve supply chain controls",
        "summary": "Add SBOM, pin dependencies, or add signing.",
        "rationale": "Supply chain visibility and integrity matter.",
        "steps": ["Review finding description.", "Add SBOM or pin by digest where applicable."],
        "snippet": "# Add syft/cyclonedx step or pin image@sha256:...",
        "confidence": "low",
        "limitations": ["Generic guidance; apply based on context."],
        "is_organization_specific": False,
    },
    "gitops": {
        "title": "Harden GitOps configuration",
        "summary": "Adjust sync policy, resources, or security context.",
        "rationale": "GitOps config affects deployment safety.",
        "steps": ["Review finding.", "Adjust syncPolicy, resources, or securityContext as needed."],
        "snippet": "# See finding description for specifics",
        "confidence": "low",
        "limitations": ["Generic guidance; apply based on manifest structure."],
        "is_organization_specific": False,
    },
}


def _generate_patch_for_finding(finding: Finding) -> str | None:
    """Generate a patch-style diff when we can infer the fix from evidence or template."""

    # Argo CD syncPolicy - generic patch
    if finding.id == "argo-001":
        return """   syncPolicy:
     automated:
-      prune: true
-      selfHeal: true
+      prune: false
+      selfHeal: false"""

    # K8s resources - generic patch, no evidence needed
    if finding.id == "gitops-003":
        return """       containers:
         - name: app
+          resources:
+            requests:
+              memory: 256Mi
+              cpu: 100m
+            limits:
+              memory: 512Mi
+              cpu: 500m"""

    # Permissions - generic patch
    if finding.id == "github-002":
        return """- permissions: write-all
+ permissions:
+   contents: read
+   packages: write"""

    if not finding.evidence:
        return None

    # Unpinned image: image: x:latest -> image: x@sha256:...
    if finding.id in ("pipeline-002", "github-005"):
        match = re.search(r"image:\s*([\w./-]+):latest", finding.evidence, re.IGNORECASE)
        if match:
            img = match.group(1)
            return f"""- image: {img}:latest
+ image: {img}@sha256:<resolve-digest>"""
        match = re.search(r"image:\s*([\w./-]+)", finding.evidence)
        if match:
            img = match.group(1)
            return f"""- image: {img}
+ image: {img}@sha256:<resolve-digest>"""

    # Unpinned action: uses: x@v1 -> uses: x@sha
    if finding.id == "github-001":
        match = re.search(r"uses:\s*([\w./-]+)@v[\d.]+", finding.evidence)
        if match:
            action = match.group(1)
            return f"""- uses: {action}@v4
+ uses: {action}@<full-40-char-sha>"""

    # imagePullPolicy: add Always when using mutable tags
    if finding.id == "gitops-005":
        return """         - name: app
+          imagePullPolicy: Always
            image: myapp:latest"""

    return None


def _get_template_for_finding(finding: Finding) -> dict[str, Any] | None:
    """Get remediation template by finding ID, or category fallback."""
    template = _REMEDIATION_REGISTRY.get(finding.id)
    if template:
        return template
    return _CATEGORY_FALLBACK.get(finding.category)


def generate_remediation(
    finding: Finding,
    *,
    min_confidence: str = _MIN_CONFIDENCE,
    use_category_fallback: bool = True,
) -> RemediationSuggestion | None:
    """
    Generate full remediation guidance for a finding.
    Uses deterministic rules/templates; no file editing.
    Returns None when no template and no category fallback, or confidence below threshold.
    """
    template = _REMEDIATION_REGISTRY.get(finding.id)
    if not template and use_category_fallback:
        template = _CATEGORY_FALLBACK.get(finding.category)
    if not template:
        return None

    confidence = template.get("confidence", "medium")
    conf_order = ("low", "medium", "high")
    try:
        c_idx = conf_order.index(confidence) if confidence in conf_order else 0
        m_idx = conf_order.index(min_confidence) if min_confidence in conf_order else 0
        if c_idx < m_idx:
            return None
    except ValueError:
        pass

    patch = template.get("patch")
    if patch is None:
        patch = _generate_patch_for_finding(finding)

    snippet = template.get("snippet")
    if snippet and not snippet.strip().startswith("# EXAMPLE"):
        snippet = _SNIPPET_LABEL + snippet

    limitations = list(template.get("limitations", []))
    if template.get("is_organization_specific"):
        limitations.append("Organization-specific implementation required.")

    return RemediationSuggestion(
        id=f"rem-{finding.id}",
        applies_to_finding_id=finding.id,
        title=template.get("title") or finding.title,
        summary=template["summary"],
        rationale=template["rationale"],
        steps=template.get("steps", []),
        snippet=snippet,
        patch=patch,
        confidence=confidence,
        limitations=limitations,
        notes=template.get("notes"),
        is_organization_specific=template.get("is_organization_specific", False),
    )


def generate_patch(finding: Finding) -> SuggestedPatch | None:
    """Generate a patch-style suggestion for a finding."""
    rem = generate_remediation(finding)
    if not rem or not rem.patch:
        return None

    return SuggestedPatch(
        id=f"patch-{finding.id}",
        applies_to_finding_id=finding.id,
        diff=rem.patch,
        description=rem.summary,
        confidence=rem.confidence,
        notes=rem.notes,
    )


def generate_remediation_bundle(result: ReviewResult) -> RemediationBundle:
    """
    Generate a bundled remediation output for a full review result.
    Does not auto-edit files; outputs guidance and patches only.
    """
    remediations: list[RemediationSuggestion] = []
    patches: list[SuggestedPatch] = []
    limitations = [
        "No automatic file editing; apply changes manually.",
        "Snippets and patches are examples; adjust for your environment.",
    ]

    for finding in result.findings:
        rem = generate_remediation(finding)
        if rem:
            remediations.append(rem)
            if rem.patch:
                p = generate_patch(finding)
                if p:
                    patches.append(p)

    return RemediationBundle(
        id="remediation-bundle",
        finding_count=len(result.findings),
        remediation_count=len(remediations),
        patch_count=len(patches),
        remediations=remediations,
        patches=patches,
        limitations=limitations,
    )
