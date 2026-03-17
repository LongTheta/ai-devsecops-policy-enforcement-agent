# Combined CI + GitOps Workflows

The agent supports **combined review** of CI/CD pipelines and Argo CD configurations to identify supply chain, promotion, security, and governance concerns across both systems.

## Supported flows

| Platform | Pipeline format | Example |
|----------|-----------------|---------|
| **GitLab + Argo** | `.gitlab-ci.yml` | `examples/insecure-gitlab-argo-flow/` |
| **GitHub + Argo** | `.github/workflows/*.yml` | `examples/insecure-github-argo-flow/` |

## What the combined review demonstrates

- **CI/CD findings** – Secrets, pinning, SBOM, permissions, approval gates
- **GitOps findings** – Sync policy, prune/selfHeal, project scoping, resource limits
- **Cross-system findings** – No approval gate before deploy, Argo auto-sync with weak governance, missing traceability, risky promotion flow

## Example commands

**GitLab + Argo CD:**
```bash
python -m ai_devsecops_agent.cli review \
  --platform gitlab \
  --pipeline examples/insecure-gitlab-argo-flow/.gitlab-ci.yml \
  --gitops examples/insecure-gitlab-argo-flow/argo-application.yaml \
  --manifests examples/insecure-gitlab-argo-flow/deployment.yaml \
  --policy policies/fedramp-moderate.yaml \
  --output markdown \
  --out report.md
```

**GitHub Actions + Argo CD:**
```bash
python -m ai_devsecops_agent.cli review \
  --platform github \
  --pipeline examples/insecure-github-argo-flow/github-actions.yml \
  --gitops examples/insecure-github-argo-flow/argo-application.yaml \
  --manifests examples/insecure-github-argo-flow/deployment.yaml \
  --policy policies/supply-chain-baseline.yaml \
  --output markdown \
  --out report.md
```

## Report structure

Reports group findings by:

- **GitHub Actions** – Workflow permissions, action pinning, `pull_request_target`, environment protection
- **GitLab / CI/CD** – Stages, jobs, SBOM, security scanning, artifact retention
- **Argo CD / GitOps** – Sync policy, project, prune/selfHeal, resource limits
- **Cross-System Governance Gaps** – CI-to-GitOps traceability, approval gates, promotion risks

## PR/MR comment generation

Use the `comments` command to generate review comments for GitHub or GitLab:

```bash
python -m ai_devsecops_agent.cli comments \
  --pipeline examples/insecure-github-argo-flow/github-actions.yml \
  --gitops examples/insecure-github-argo-flow/argo-application.yaml \
  --type summary \
  --format github \
  --out pr-comment.md
```

Comment types: `summary`, `grouped` (by severity or category), `individual`.

## Remediation suggestions

Use the `remediate` command for actionable fix guidance with patch-like snippets:

```bash
python -m ai_devsecops_agent.cli remediate \
  --pipeline .gitlab-ci.yml \
  --gitops k8s/argo-app.yaml \
  --out remediations.md
```

## Context fields

- `--platform` – `gitlab`, `github`, or `local`
- `--compliance` – e.g. `fedramp-moderate`, `supply-chain-baseline`
- `--repo`, `--branch` – Optional context for reporting

---

## Related docs

- [ARCHITECTURE.md](ARCHITECTURE.md) – High-level architecture
- [COMPONENTS.md](COMPONENTS.md) – Detailed component reference
