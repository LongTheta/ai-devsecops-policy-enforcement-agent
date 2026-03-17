# AI DevSecOps Policy Enforcement Agent

**AI-powered DevSecOps agent that analyzes CI/CD pipelines and GitOps workflows to enforce security, compliance, and supply chain policies with actionable remediation guidance.**

---

## Why This Exists

Modern delivery pipelines are fast — but often lack:

- **Consistent security enforcement** across teams and repos
- **Supply chain visibility** (SBOM, provenance, signing)
- **Compliance-aware controls** for audit and governance
- **Clear promotion and governance boundaries** between environments

Most tools **detect issues** and **generate reports**.

❌ But they don't **enforce decisions** or **help developers fix problems**.

---

## What This Project Does

This project turns DevSecOps policies into **automated, enforceable decisions** across:

- **CI/CD pipelines** (GitLab CI, GitHub Actions)
- **GitOps workflows** (Argo CD)
- **Kubernetes manifests**
- **Supply chain security** (SBOM, provenance, signing)

---

## Core Capabilities

### Pipeline Analysis

- Detect insecure CI/CD patterns (plaintext secrets, risky scripts)
- Identify missing controls (SBOM, approvals, signing)
- Flag unpinned dependencies and unsafe practices

### GitOps / Argo CD Analysis

- Evaluate sync policies and drift risk
- Identify unsafe automation patterns (prune, selfHeal)
- Detect weak promotion and environment separation

### Policy Enforcement

- YAML-based policy engine
- Supports supply chain, security, and compliance-aware rules

**Verdicts:** ✅ Pass | ⚠️ Pass with warnings | ❌ Fail

### Compliance-Aware Mapping

Maps findings to control families such as:

- AC (Access Control) · AU (Audit & Accountability) · CM (Configuration Management)
- IA (Identification & Authentication) · SC (System Communications Protection) · SI (System Integrity)

> ⚠️ Supports engineering analysis — not formal compliance certification

### Auto-Remediation

- Suggests fixes for common issues
- Step-by-step guidance, YAML snippets, patch-style diffs

```diff
- image: node:latest
+ image: node@sha256:...
```

### PR / MR Review Comments

Generates developer-friendly review comments for GitHub PRs and GitLab MRs:

```
❌ Missing SBOM Generation Step

Severity: High | Category: Supply Chain

Why this matters:
This pipeline does not generate an SBOM, reducing artifact traceability.

Suggested fix:
Add a step using Syft or similar tooling to generate an SBOM artifact.
```

---

## Architecture

```
Analyzers → Policy Engine → Compliance Mapping → Remediation → Reporting
```

| Component | Purpose |
|-----------|---------|
| **Pipeline analyzer** | GitLab CI, GitHub Actions patterns |
| **GitOps analyzer** | Argo CD, K8s manifests |
| **SBOM analyzer** | Supply chain visibility |
| **Cross-system analyzer** | CI↔GitOps governance gaps |
| **Policy engine** | YAML-based enforcement |
| **Reporting** | Markdown, JSON, SARIF, console, PR/MR comments |

---

## Quick Start

```bash
git clone https://github.com/LongTheta/ai-devsecops-policy-enforcement-agent.git
cd ai-devsecops-policy-enforcement-agent
pip install -e ".[dev]"
```

**Run a review (with CI/CD artifacts):**

```bash
ai-devsecops-agent review \
  --platform github \
  --pipeline .github/workflows/ci.yml \
  --gitops k8s/argo-application.yaml \
  --policy policies/default.yaml \
  --artifact-dir artifacts/
```

**Run a review (GitLab):**

```bash
ai-devsecops-agent review \
  --platform gitlab \
  --pipeline examples/insecure-gitlab-argo-flow/.gitlab-ci.yml \
  --gitops examples/insecure-gitlab-argo-flow/argo-application.yaml \
  --manifests examples/insecure-gitlab-argo-flow/deployment.yaml \
  --policy policies/fedramp-moderate.yaml \
  --output markdown \
  --out report.md
```

**Generate PR/MR comments:**

```bash
ai-devsecops-agent comments \
  --pipeline examples/insecure-gitlab-ci.yml \
  --gitops examples/insecure-argo-application.yaml \
  --type grouped \
  --format github \
  --out pr-comment.md
```

**Get remediation suggestions with patches:**

```bash
ai-devsecops-agent remediate \
  --pipeline examples/insecure-gitlab-ci.yml \
  --gitops examples/insecure-argo-application.yaml \
  --include-patch \
  --out remediations.md
```

---

## Example Output

| Output | Path |
|--------|------|
| Full report (Markdown) | [examples/sample-output.md](examples/sample-output.md) |
| JSON report | [examples/sample-output.json](examples/sample-output.json) |
| GitHub PR comments | [examples/github-review-comments.md](examples/github-review-comments.md) |
| GitLab MR comments | [examples/gitlab-review-comments.md](examples/gitlab-review-comments.md) |
| Remediation suggestions | [examples/remediation-output.md](examples/remediation-output.md) |

## 5-Minute Demo

Run the interactive demo for interviews or presentations:

```bash
# Bash (Linux/macOS)
./scripts/demo.sh

# PowerShell (Windows)
./scripts/demo.ps1
```

Or follow the step-by-step guide: [docs/DEMO.md](docs/DEMO.md)

---

## Workflow Integration

The agent plugs into real CI/CD and PR/MR workflows:

- **Artifact generation** – `--artifact-dir` writes `review-result.json`, `policy-summary.json`, `comments.json`, `remediations.json`, `workflow-status.json`
- **GitHub Actions** – See [.github/workflows/policy-review.yml](.github/workflows/policy-review.yml)
- **GitLab CI** – See [examples/workflows/gitlab-policy-review.yml](examples/workflows/gitlab-policy-review.yml)
- **Post comments** – `comments --post` with `GITHUB_TOKEN` or `GITLAB_TOKEN`

See [docs/WORKFLOW-INTEGRATION.md](docs/WORKFLOW-INTEGRATION.md) for details.

---

## Example Use Cases

- 🔍 Review CI/CD pipelines before merge
- 🔐 Enforce supply chain policies
- ⚙️ Validate GitOps deployment safety
- 🧾 Generate compliance-aware reports
- 🛠 Suggest fixes for insecure configurations
- 💬 Post review comments to PRs/MRs (GitHub, GitLab)

---

## Design Principles

- **Policy-driven, not hardcoded** — Rules live in YAML
- **Deterministic first, AI-assisted second** — Predictable, auditable results
- **Separation of concerns** — Analyzers, policy, remediation, reporting
- **Extensible** — GitLab, GitHub, Argo CD integrations (fetch, post comments)
- **Compliance-aware but not compliance theater** — Engineering guidance, not certification

---

## Repository

- **GitHub:** [github.com/LongTheta/ai-devsecops-policy-enforcement-agent](https://github.com/LongTheta/ai-devsecops-policy-enforcement-agent)
- **GitLab:** [gitlab.com/cathcampbell/ai-devsecops-policy-enforcement-agent](https://gitlab.com/cathcampbell/ai-devsecops-policy-enforcement-agent)

---

## Roadmap

### Near-term

- [x] PR/MR API integration (post comments)
- [x] SARIF output for GitHub Advanced Security, GitLab SAST
- [ ] Unified `review-all` with remote fetch

### Mid-term

- [ ] SBOM MCP tool
- [ ] Evaluation history + trend tracking
- [ ] Observability (OTel / Logfire)

### Advanced

- [ ] Auto-fix commit bot
- [ ] Compliance evidence generator
- [ ] Drift detection across CI → GitOps → runtime

---

## CLI Reference

| Command | Purpose |
|---------|---------|
| `review` | Run full policy review; output Markdown, JSON, SARIF, or console |
| `comments` | Generate PR/MR review comments; optional `--post` to publish |
| `remediate` | Output remediation suggestions with optional patch-style diffs |

See `ai-devsecops-agent --help` and [docs/COMPONENTS.md](docs/COMPONENTS.md) for details.

---

## Disclaimer

This project provides **engineering guidance and policy enforcement support**. It is not a substitute for formal security audits or compliance certification.

---

## One-Liner

**Turn DevSecOps policies into enforceable, automated decisions across your delivery pipeline.**
