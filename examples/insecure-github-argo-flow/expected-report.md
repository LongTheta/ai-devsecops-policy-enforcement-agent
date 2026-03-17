# DevSecOps Policy Review Report

## 1. Executive Summary

Review failed: 0 critical, 2 high finding(s). Address these before merge or deployment.

**Verdict:** FAIL

---

## 2. Verdict

- **FAIL**

---

## 3. Findings by Group

### GitHub Actions

*Findings from workflow YAML, permissions, actions, and supply chain.*

#### HIGH

**1. Unpinned container image or action** (`pipeline-002`)

- **Category:** supply_chain
- **Description:** Pipeline uses an image or action without a digest or explicit tag; increases supply chain risk.
- **Evidence:**
```
# Insecure GitHub Actions + Argo CD flow – for testing cross-system review
# Issues: unpinned actions, no SBOM, no environment protection, direct deploy
```
- **Impacted files:** examples/insecure-github-argo-flow/github-actions.yml
- **Remediation:** Pin images by digest; pin actions by full commit SHA.
- **Control families (engineering review only):**
  - SA: System and services acquisition – supply chain and SBOM
  - SI: System and information integrity – software integrity and provenance

**2. pull_request_target with deployment risk** (`github-003`)

- **Category:** permissions
- **Description:** pull_request_target runs with write access to repo; combined with deploy steps increases risk.
- **Evidence:**
```
# Insecure GitHub Actions + Argo CD flow – for testing cross-system review
# Issues: unpinned actions, no SBOM, no environment protection, direct deploy

name: CI/CD
on:
```
- **Impacted files:** examples/insecure-github-argo-flow/github-actions.yml
- **Remediation:** Avoid pull_request_target for deploy jobs; use push/workflow_dispatch with environment protection.
- **Control families (engineering review only):**
  - SI: High/critical finding may affect system and information integrity.

#### MEDIUM

**1. Action pinned by tag instead of full SHA** (`github-001`)

- **Category:** supply_chain
- **Description:** GitHub Actions uses @v1, @v2, etc.; pin by full commit SHA for supply chain integrity.
- **Evidence:**
```
# Insecure GitHub Actions + Argo CD flow – for testing cross-system review
# Issues: unpinned actions, no SBOM, no environment protection, direct deploy

name: CI/CD
```
- **Impacted files:** examples/insecure-github-argo-flow/github-actions.yml
- **Remediation:** Pin actions with @<full-40-char-sha> or use Dependabot for action updates.
- **Control families (engineering review only):**
  - SA: System and services acquisition – supply chain and SBOM
  - SI: System and information integrity – software integrity and provenance

**2. Broad workflow permissions** (`github-002`)

- **Category:** permissions
- **Description:** Workflow uses write-all or all permissions; increases blast radius.
- **Evidence:**
```
{'permissions': 'write-all'}
```
- **Impacted files:** examples/insecure-github-argo-flow/github-actions.yml
- **Remediation:** Use least-privilege permissions: contents: read, packages: write only if needed.

#### INFO

**1. Deploy job without artifact retention for traceability** (`github-004`)

- **Category:** supply_chain
- **Description:** Workflow deploys but does not retain SBOM, digests, or provenance as artifacts.
- **Evidence:**
```
# Insecure GitHub Actions + Argo CD flow – for testing cross-system review
# Issues: unpinned actions, no SBOM, no environment protection, direct deploy

name: CI/CD
```
- **Impacted files:** examples/insecure-github-argo-flow/github-actions.yml
- **Remediation:** Add actions/upload-artifact for SBOM, image digests, or attestations before deploy.
- **Control families (engineering review only):**
  - SA: System and services acquisition – supply chain and SBOM
  - SI: System and information integrity – software integrity and provenance


### Argo CD / GitOps

*Findings from Argo CD Application and Kubernetes manifests.*

#### MEDIUM

**1. Automated sync enabled** (`gitops-001`)

- **Category:** gitops
- **Description:** Argo CD Application has automated sync; ensure this is intended and promotion gates exist elsewhere.
- **Evidence:**
```
{'prune': True, 'selfHeal': True}
```
- **Impacted files:** examples\insecure-github-argo-flow\argo-application.yaml
- **Remediation:** Use manual sync for production or pair with GitOps Promoter approval gates.
- **Control families (engineering review only):**
  - CM: Configuration management – baseline and change control
  - AU: Audit and accountability – deployment traceability

**2. Automated prune and selfHeal both enabled** (`argo-001`)

- **Category:** gitops
- **Description:** Both prune and selfHeal are enabled; local changes can be overwritten without explicit approval.
- **Evidence:**
```
prune: True, selfHeal: True
```
- **Impacted files:** examples\insecure-github-argo-flow\argo-application.yaml
- **Remediation:** Consider manual sync for production or restrict prune/selfHeal to non-prod.
- **Control families (engineering review only):**
  - CM: Configuration management – baseline and change control
  - AU: Audit and accountability – deployment traceability

**3. Production-like path with HEAD revision** (`argo-002`)

- **Category:** gitops
- **Description:** Application targets production-like path/namespace but uses HEAD; no promotion pin for traceability.
- **Evidence:**
```
path: k8s/overlays/prod, namespace: myapp, targetRevision: HEAD
```
- **Impacted files:** examples\insecure-github-argo-flow\argo-application.yaml
- **Remediation:** Use tagged revision or GitOps promotion (e.g. kustomize overlay, tagged ref) for prod.
- **Control families (engineering review only):**
  - CM: Configuration management – baseline and change control
  - AU: Audit and accountability – deployment traceability

**4. No pod security context** (`gitops-004`)

- **Category:** gitops
- **Description:** Pod spec does not set securityContext (e.g. runAsNonRoot, readOnlyRootFilesystem).
- **Impacted files:** examples\insecure-github-argo-flow\deployment.yaml
- **Control families (engineering review only):**
  - CM: Configuration management – baseline and change control
  - AU: Audit and accountability – deployment traceability

**5. Missing resource limits** (`gitops-003`)

- **Category:** gitops
- **Description:** Workload does not specify resource limits; can lead to resource exhaustion.
- **Evidence:**
```
{
"replicas": 2,
"template": {
"spec": {
"containers": [
{
"name": "app",
"image": "myapp:latest",
"ports": [
{
"containerPort": 8080
}
]
}
]
}
}
}
```
- **Impacted files:** examples\insecure-github-argo-flow\deployment.yaml
- **Control families (engineering review only):**
  - CM: Configuration management – baseline and change control
  - AU: Audit and accountability – deployment traceability

#### LOW

**1. Default or missing Argo CD project** (`gitops-002`)

- **Category:** gitops
- **Description:** Application uses default project; consider explicit AppProject for RBAC and namespace scoping.
- **Evidence:**
```
project: 'default'
```
- **Impacted files:** examples\insecure-github-argo-flow\argo-application.yaml
- **Control families (engineering review only):**
  - CM: Configuration management – baseline and change control
  - AU: Audit and accountability – deployment traceability


### Cross-System Governance Gaps

*Findings spanning CI/CD and GitOps (traceability, promotion, gates).*

#### MEDIUM

**1. Argo auto-sync enabled with default project** (`cross-002`)

- **Category:** governance
- **Description:** Automated sync is enabled with default or missing project; weak RBAC and namespace scoping.
- **Evidence:**
```
project: default, automated: {'prune': True, 'selfHeal': True}
```
- **Impacted files:** examples/insecure-github-argo-flow/argo-application.yaml
- **Remediation:** Use explicit AppProject and consider manual sync for production.
- **Control families (engineering review only):**
  - CM: Configuration management – change approval and promotion gates
  - RA: Risk assessment – deployment risk and approvals

**2. Broad workflow permissions with direct deployment path** (`cross-006`)

- **Category:** governance
- **Description:** Workflow has broad permissions and deploys; increases risk if compromised.
- **Evidence:**
```
# Insecure GitHub Actions + Argo CD flow – for testing cross-system review
# Issues: unpinned actions, no SBOM, no environment protection, direct deploy

name: CI/CD
```
- **Impacted files:** examples/insecure-github-argo-flow/github-actions.yml
- **Remediation:** Use least-privilege permissions and environment protection for deploy jobs.
- **Control families (engineering review only):**
  - CM: Configuration management – change approval and promotion gates
  - RA: Risk assessment – deployment risk and approvals


---

## 4. Policy Results

- **Require SBOM** (enabled: True)
- **Pinned pipeline dependencies** (enabled: True)
- **Artifact traceability** (enabled: True)

---

## 5. Compliance Considerations

- Findings map to control families: AU, CM, RA, SA, SI. These mappings support engineering review and are not formal compliance determinations.

---

## 6. Recommended Remediations

- Pin images by digest; pin actions by full commit SHA.
- Pin by digest or SHA
- Pin actions with @<full-40-char-sha> or use Dependabot for action updates.
- Use least-privilege permissions: contents: read, packages: write only if needed.
- Avoid pull_request_target for deploy jobs; use push/workflow_dispatch with environment protection.
- Add actions/upload-artifact for SBOM, image digests, or attestations before deploy.
- Use manual sync for production or pair with GitOps Promoter approval gates.
- Consider manual sync for production or restrict prune/selfHeal to non-prod.
- Use tagged revision or GitOps promotion (e.g. kustomize overlay, tagged ref) for prod.
- Add securityContext
- Add resources.limits
- Use explicit AppProject and consider manual sync for production.
- Use least-privilege permissions and environment protection for deploy jobs.

---

## 7. Next Steps

- Address critical and high findings before merge or deployment.
- Review medium-severity findings and plan remediation.
- Re-run the agent after changes to verify verdict.

---

*This report is for engineering guidance. Compliance mappings are not formal compliance determinations.*
