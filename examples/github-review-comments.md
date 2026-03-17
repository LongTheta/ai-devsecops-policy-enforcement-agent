## DevSecOps Policy Review – Findings

**Verdict:** FAIL

### HIGH

#### Unpinned container image or action (`pipeline-002`)

- **Category:** supply_chain
- **Description:** Pipeline uses an image or action without a digest or explicit tag; increases supply chain risk.
- **Suggested fix:** Pin images by digest; pin actions by full commit SHA.

Example:
```yaml
# Before: image: alpine:latest
# After: image: alpine@sha256:c0e9560cda118f9ec63ddefb4a173a2b2a0347082d7dff7dc14236e73a05ce6f
```

#### Pinned pipeline dependencies (`policy-require_pinned_pipeline_dependencies`)

- **Category:** supply_chain
- **Description:** All images and actions must be pinned by digest or SHA.

Example:
```yaml
# Before: image: alpine:latest
# After: image: alpine@sha256:...
```

#### Require signed artifacts (`policy-require_signed_artifacts`)

- **Category:** supply_chain
- **Description:** Critical artifacts should be signed (e.g. cosign).

Example:
```yaml
- name: Sign image
  run: cosign sign --key cosign.key $IMAGE
```

### MEDIUM

#### Action pinned by tag instead of full SHA (`github-001`)

- **Category:** supply_chain
- **Description:** GitHub Actions uses @v1, @v2, etc.; pin by full commit SHA for supply chain integrity.
- **Suggested fix:** Pin actions with @<full-40-char-sha> or use Dependabot for action updates.

Example:
```yaml
# Before: uses: actions/checkout@v4
# After: uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11
```

#### Deploy job without environment protection (`github-006`)

- **Category:** governance
- **Description:** Deploy job does not use environment: production; no approval gates or protection rules.
- **Suggested fix:** Add environment: production to deploy job for required reviewers.

Example:
```yaml
deploy:
  environment: production
  steps:
    - run: ...
```

#### Audit logging evidence (`policy-require_audit_logging_evidence`)

- **Category:** governance
- **Description:** Deployment and change actions must be auditable.

Example:
```yaml
deploy:
  environment: production
  script:
    - echo 'Deploying to production'
```

#### Automated sync enabled (`gitops-001`)

- **Category:** gitops
- **Description:** Argo CD Application has automated sync; ensure this is intended and promotion gates exist elsewhere.
- **Suggested fix:** Use manual sync for production or pair with GitOps Promoter approval gates.

Example:
```yaml
# For production, prefer manual sync:
syncPolicy: {}  # Remove automated block
# Or: automated:
#   prune: false
#   selfHeal: false
```

#### Automated prune and selfHeal both enabled (`argo-001`)

- **Category:** gitops
- **Description:** Both prune and selfHeal are enabled; local changes can be overwritten without explicit approval.
- **Suggested fix:** Consider manual sync for production or restrict prune/selfHeal to non-prod.

Example:
```yaml
syncPolicy:
  automated:
    prune: false
    selfHeal: false
```

#### Production-like path with HEAD revision (`argo-002`)

- **Category:** gitops
- **Description:** Application targets production-like path/namespace but uses HEAD; no promotion pin for traceability.
- **Suggested fix:** Use tagged revision or GitOps promotion (e.g. kustomize overlay, tagged ref) for prod.

Example:
```yaml
source:
  targetRevision: v1.2.3
```

#### Argo auto-sync enabled with default project (`cross-002`)

- **Category:** governance
- **Description:** Automated sync is enabled with default or missing project; weak RBAC and namespace scoping.
- **Suggested fix:** Use explicit AppProject and consider manual sync for production.

Example:
```yaml
spec:
  project: myapp-prod
```

### LOW

#### No build provenance or artifact signing detected (`sbom-002`)

- **Category:** supply_chain
- **Description:** No attestation or signing step was detected; artifact traceability may be limited.
- **Suggested fix:** Consider adding SLSA provenance or cosign/signing for critical artifacts.

Example:
```yaml
# Example: cosign sign
- name: Sign SBOM
  run: cosign sign-blob sbom.json --output-signature sbom.sig
```

#### Default or missing Argo CD project (`gitops-002`)

- **Category:** gitops
- **Description:** Application uses default project; consider explicit AppProject for RBAC and namespace scoping.

Example:
```yaml
spec:
  project: myapp-prod
```

### INFO

#### Deploy job without artifact retention for traceability (`github-004`)

- **Category:** supply_chain
- **Description:** Workflow deploys but does not retain SBOM, digests, or provenance as artifacts.
- **Suggested fix:** Add actions/upload-artifact for SBOM, image digests, or attestations before deploy.

Example:
```yaml
- uses: actions/upload-artifact@v4
  with:
    name: sbom
    path: sbom.json
```