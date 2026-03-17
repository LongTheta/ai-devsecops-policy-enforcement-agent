## DevSecOps Policy Review – Findings

**Verdict:** FAIL

### CRITICAL

#### Possible plaintext secret or credential (`pipeline-001`)

- **Category:** secrets
- **Description:** Pipeline content appears to contain hardcoded credentials, API keys, or tokens.
- **Suggested fix:** Use secret variables, vault, or managed secrets; never commit secrets.

Example:
```yaml
# Example (GitLab):
variables:
  API_KEY: $CI_JOB_TOKEN  # Set in CI/CD settings
# Example (GitHub): ${{ secrets.API_KEY }}
```

#### No plaintext secrets (`policy-no_plaintext_secrets`)

- **Category:** secrets
- **Description:** No hardcoded credentials; use vault or managed secrets.

Example:
```yaml
# Use variable: ${SECRET_TOKEN} or ${{ secrets.SECRET_TOKEN }}
```

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

#### Unsafe script or inline execution (`pipeline-004`)

- **Category:** pipeline
- **Description:** Pipeline contains raw script blocks or inline curl that can introduce injection or supply chain risk.
- **Suggested fix:** Prefer built-in steps or well-defined scripts; avoid unchecked user input in scripts.

Example:
```yaml
script:
  - ./scripts/validate.sh
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

#### No security scanning step in GitLab pipeline (`gitlab-001`)

- **Category:** ci_cd
- **Description:** GitLab pipeline does not include SAST, dependency scanning, or container scanning.
- **Suggested fix:** Add security scanning templates (e.g. sast, dependency_scanning) or third-party tools.

Example:
```yaml
include:
  - template: Security/SAST.gitlab-ci.yml
```

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

#### Deploy stage without artifact retention for traceability (`gitlab-002`)

- **Category:** ci_cd
- **Description:** Pipeline appears to deploy but does not retain build artifacts (SBOM, digests) for audit.
- **Suggested fix:** Add artifacts retention for SBOM, image digests, or provenance before deploy.

Example:
```yaml
artifacts:
  paths:
    - sbom.json
  expire_in: 30 days
```