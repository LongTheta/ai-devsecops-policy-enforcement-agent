# AI DevSecOps Policy Enforcement Agent

**A workflow-integrated policy enforcement engine for CI/CD and GitOps.** Deterministic analysis, compliance-aware rules, and reviewable auto-fix. DevSecOps and GitOps aware — not a prototype.

---

## What Works Today

This is a **working system** — not a framework or concept. Concrete capabilities implemented and verified:

| Capability | Status |
|------------|--------|
| Analyze GitLab CI and GitHub Actions pipelines | ✅ |
| Analyze Argo CD applications and Kubernetes manifests | ✅ |
| Enforce policy rules (security, supply chain, compliance-aware) | ✅ |
| Generate structured outputs (Markdown, JSON, SARIF, artifacts) | ✅ |
| Generate PR/MR review comments (GitHub/GitLab formats) | ✅ |
| Generate deterministic remediation suggestions | ✅ |
| Auto-fix: suggest mode | ✅ |
| Auto-fix: patch mode (write to output dir) | ✅ |
| Auto-fix: apply mode (safe fixes only, with backups) | ✅ |
| Verdict and severity breakdown (pass / fail / warnings) | ✅ |
| Risk scoring (severity counts, critical/high/medium/low) | ✅ |
| Remote fetch of pipeline from PR/MR | ✅ |

See [docs/ROADMAP.md](docs/ROADMAP.md) for full list.

---

## Quick Start (60 seconds)

```bash
git clone https://github.com/LongTheta/ai-devsecops-policy-enforcement-agent.git
cd ai-devsecops-policy-enforcement-agent
pip install -e .
```

```bash
python -m ai_devsecops_agent.cli review \
  --platform gitlab \
  --pipeline examples/insecure-gitlab-ci.yml \
  --gitops examples/insecure-argo-application.yaml \
  --policy policies/default.yaml \
  --artifact-dir artifacts
```

**Outputs:** `artifacts/review-result.json`, `artifacts/policy-summary.json`, `artifacts/report.md`, `artifacts/comments.json`, `artifacts/remediations.json`.

---

## 2-Minute Demo

### Step 1 — Run review

```bash
python -m ai_devsecops_agent.cli review-all \
  --platform gitlab \
  --pipeline examples/insecure-gitlab-ci.yml \
  --gitops examples/insecure-argo-application.yaml \
  --policy policies/fedramp-moderate.yaml \
  --artifact-dir artifacts/
```

*(For local files, `review-all` works like `review`. Add `--output markdown --out report.md` to write a report file.)*

```bash
# Full flow (pipeline + GitOps + manifests):
python -m ai_devsecops_agent.cli review \
  --platform gitlab \
  --pipeline examples/insecure-gitlab-argo-flow/.gitlab-ci.yml \
  --gitops examples/insecure-gitlab-argo-flow/argo-application.yaml \
  --manifests examples/insecure-gitlab-argo-flow/deployment.yaml \
  --policy policies/fedramp-moderate.yaml \
  --include-comments \
  --include-remediations \
  --output markdown \
  --out report.md \
  --artifact-dir artifacts/
```

### Step 2 — Inspect output

- **Findings** — plaintext secrets, unpinned images, missing SBOM, risky Argo sync
- **Verdict** — FAIL / PASS WITH WARNINGS / PASS
- **Severity breakdown** — critical, high, medium, low (in `artifacts/policy-summary.json`)
- **Comments** — `artifacts/comments.json`, `artifacts/github-comments.json`, or `artifacts/gitlab-comments.json`
- **Remediation artifacts** — `artifacts/remediations.json`

### Step 3 — Run auto-fix

```bash
python -m ai_devsecops_agent.cli auto-fix \
  --input artifacts/review-result.json \
  --mode suggest
```

### Step 4 — Show a diff

Example output:

```diff
- image: node:latest
+ image: node:18.17.0

- uses: actions/checkout@v4
+ uses: actions/checkout@<full-40-char-sha>
```

Or run `--mode patch --output-dir artifacts/fixes` to write patched copies.

---

## Demo Repositories

These repos are used or planned to validate the engine in real pipeline workflows:

| Repository | Purpose |
|------------|---------|
| **demo-gitlab-argo-insecure-app** | GitLab CI + Argo CD + Kubernetes example with intentional security and policy violations. Demonstrates pipeline enforcement, findings, remediation, and artifacts. |
| **demo-github-argo-insecure-app** | GitHub Actions + Argo CD example. Demonstrates cross-platform support and PR workflow integration. |
| **demo-supply-chain-broken-build** | Example missing SBOM, provenance, and signing. Demonstrates supply chain policy enforcement. |
| **demo-fixed-vs-broken** | Side-by-side insecure vs remediated configurations. Demonstrates auto-fix and improvement validation. |

**Built-in examples** in this repo (same validation strategy):

- `examples/insecure-gitlab-argo-flow/` — GitLab CI + Argo CD + K8s
- `examples/insecure-github-argo-flow/` — GitHub Actions + Argo CD
- `examples/autofix/` — Auto-fix targets (unpinned actions, missing SBOM, risky Argo sync, missing resource limits)

---

## Example Outputs

| File | Demonstrates |
|------|--------------|
| [examples/sample-output.md](examples/sample-output.md) | Full Markdown report with findings, verdict, compliance mappings |
| [examples/sample-output.json](examples/sample-output.json) | Structured JSON output |
| [examples/github-review-comments.md](examples/github-review-comments.md) | PR-ready comment format (GitHub) |
| [examples/gitlab-review-comments.md](examples/gitlab-review-comments.md) | MR-ready comment format (GitLab) |
| [examples/remediation-output.md](examples/remediation-output.md) | Step-by-step remediation with patches |
| `artifacts/review-result.json` | Produced by `review --artifact-dir`; input for `auto-fix --input` |

---

## Implemented vs Planned

| Capability | Status |
|------------|--------|
| Pipeline analysis | ✅ Implemented |
| GitOps / Argo analysis | ✅ Implemented |
| Policy enforcement | ✅ Implemented |
| Remediation suggestions | ✅ Implemented |
| Auto-fix (suggest / patch / apply) | ✅ Implemented for safe subset |
| PR/MR comment generation | ✅ Implemented |
| Risk scoring (severity breakdown) | ✅ Implemented |
| Live PR/MR posting | 🚧 Partial / Optional (requires `GITHUB_TOKEN` or `GITLAB_TOKEN`) |
| Auto-fix commit bot | 🚧 Planned |
| Compliance evidence generation | 🚧 Planned |

---

## How This Fits in a CI/CD Pipeline

1. **Run review** — `review` or `review-all` in CI (GitHub Actions, GitLab CI)
2. **Generate artifacts** — Markdown, JSON, comments, remediations
3. **Fail on policy violations** — Exit code 1 when verdict is FAIL
4. **Surface PR/MR comments** — Use `comments` or post from artifacts
5. **Optionally run auto-fix** — `auto-fix --mode suggest` or `--mode patch` for reviewable fixes

See [.github/workflows/policy-review.yml](.github/workflows/policy-review.yml) and [docs/WORKFLOW-INTEGRATION.md](docs/WORKFLOW-INTEGRATION.md).

---

## Architecture (High-Level)

```
Analyzers → Policy Engine → Risk Scoring → Remediation → Auto-Fix → Reporting → Workflow Integration
```

| Component | Purpose |
|-----------|---------|
| **Pipeline analyzer** | GitLab CI, GitHub Actions patterns |
| **GitOps analyzer** | Argo CD, K8s manifests |
| **SBOM analyzer** | Supply chain visibility |
| **Cross-system analyzer** | CI↔GitOps governance gaps |
| **Policy engine** | YAML-based enforcement |
| **Auto-fix engine** | Deterministic, policy-aware config patches |
| **Reporting** | Markdown, JSON, SARIF, console, PR/MR comments |

---

## Why This Exists

Modern delivery pipelines are fast — but often lack:

- **Consistent security enforcement** across teams and repos
- **Supply chain visibility** (SBOM, provenance, signing)
- **Compliance-aware controls** for audit and governance
- **Clear promotion and governance boundaries** between environments

Most tools **detect issues** and **generate reports**. This system **enforces decisions** and **helps developers fix problems** with deterministic, reviewable auto-fix.

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
- Supply chain, security, and compliance-aware rules

**Verdicts:** ✅ Pass | ⚠️ Pass with warnings | ❌ Fail

### Policy-Aware Auto-Fix

- **Deterministic, reviewable patches** for common CI/CD, GitOps, and K8s issues
- **Modes:** `suggest` (no changes) | `patch` (write to output dir) | `apply` (modify originals with backups)
- **Safety model:** `safe` | `review_required` | `suggest_only` per fix

### PR / MR Review Comments

Generates developer-friendly review comments for GitHub PRs and GitLab MRs. Can post live with `GITHUB_TOKEN` or `GITLAB_TOKEN`.

---

## Quick Commands

**Review (local files):**

```bash
python -m ai_devsecops_agent.cli review \
  --platform github \
  --pipeline .github/workflows/ci.yml \
  --gitops k8s/argo-application.yaml \
  --artifact-dir artifacts
```

**Review with remote fetch (PR/MR):**

```bash
# GitHub
python -m ai_devsecops_agent.cli review-all --owner org --repo repo --pr 42 --artifact-dir artifacts

# GitLab
python -m ai_devsecops_agent.cli review-all --project group/repo --mr 10 --artifact-dir artifacts
```

**Auto-fix:**

```bash
# Suggest (no file changes)
python -m ai_devsecops_agent.cli auto-fix --input artifacts/review-result.json --mode suggest

# Patch (write to output dir)
python -m ai_devsecops_agent.cli auto-fix --input artifacts/review-result.json --mode patch --output-dir artifacts/fixes

# Apply (safe fixes only, creates backups)
python -m ai_devsecops_agent.cli auto-fix --pipeline examples/autofix/insecure-pipeline-for-autofix.yml \
  --gitops examples/autofix/insecure-argo-for-autofix.yaml --manifests examples/autofix/insecure-for-autofix.yaml \
  --mode apply --only-safe
```

---

## 5-Minute Demo (Interactive)

```bash
# Bash (Linux/macOS)
./scripts/demo.sh

# PowerShell (Windows)
./scripts/demo.ps1
```

Step-by-step guide: [docs/DEMO.md](docs/DEMO.md)

---

## Workflow Integration

- **Artifact generation** — `--artifact-dir` writes `review-result.json`, `policy-summary.json`, `report.md`, `comments.json`, `remediations.json`, `workflow-status.json`
- **GitHub Actions** — [.github/workflows/policy-review.yml](.github/workflows/policy-review.yml)
- **GitLab CI** — [examples/workflows/gitlab-policy-review.yml](examples/workflows/gitlab-policy-review.yml)
- **Post comments** — `comments --post` with `GITHUB_TOKEN` or `GITLAB_TOKEN`

See [docs/WORKFLOW-INTEGRATION.md](docs/WORKFLOW-INTEGRATION.md).

---

## Design Principles

- **Policy-driven, not hardcoded** — Rules live in YAML
- **Deterministic first, AI-assisted where useful** — Predictable, auditable results
- **Workflow-integrated** — Drops into CI/CD pipelines
- **Reviewable and safe auto-fix** — No freeform rewriting

---

## CLI Reference

| Command | Purpose |
|---------|---------|
| `review` | Full policy review; Markdown, JSON, SARIF, artifacts |
| `review-all` | Review with optional remote fetch from PR/MR |
| `comments` | Generate PR/MR comments; optional `--post` |
| `remediate` | Remediation suggestions with patches |
| `auto-fix` | Generate or apply config patches (suggest \| patch \| apply) |

---

## Roadmap

- [x] PR/MR integration, SARIF, auto-fix, review-all
- [ ] SBOM MCP tool, evaluation history, observability
- [ ] Auto-fix commit bot, compliance evidence generator

See [docs/ROADMAP.md](docs/ROADMAP.md).

---

## Repository

- **GitHub:** [github.com/LongTheta/ai-devsecops-policy-enforcement-agent](https://github.com/LongTheta/ai-devsecops-policy-enforcement-agent)
- **GitLab:** [gitlab.com/cathcampbell/ai-devsecops-policy-enforcement-agent](https://gitlab.com/cathcampbell/ai-devsecops-policy-enforcement-agent)

---

## Disclaimer

This project provides **engineering guidance and policy enforcement support**. It is not a substitute for formal security audits or compliance certification.
