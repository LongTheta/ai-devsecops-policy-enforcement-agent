# AI DevSecOps Policy Enforcement Agent

**An AI-assisted DevSecOps policy enforcement framework for CI/CD, GitOps, and compliance-aware platform delivery.**

This project analyzes CI/CD pipelines (GitLab CI, GitHub Actions), Kubernetes and Argo CD manifests, and supply chain controls to identify security, compliance, and GitOps risks. It produces structured findings, actionable remediation suggestions, PR/MR-ready review comments, and pass/warn/fail verdicts. The system is file-based and MVP-friendly, with clean abstractions for future live API integrations.

---

## Table of contents

- [Why it matters](#why-it-matters)
- [Who it is for](#who-it-is-for)
- [What it does](#what-it-does)
- [Quick start](#quick-start)
- [CLI commands](#cli-commands)
- [Supported analysis](#supported-analysis)
- [Policy model](#policy-model)
- [PR/MR comment generation](#prmr-comment-generation)
- [Auto-remediation engine](#auto-remediation-engine)
- [Project structure](#project-structure)
- [Documentation](#documentation)
- [Disclaimer](#disclaimer)

---

## Why it matters

- **Consistency** – Apply the same policy and risk model across pipelines and GitOps configs.
- **Compliance awareness** – Map findings to broad NIST-style control families (AC, AU, CM, IA, IR, RA, SA, SC, SI) to support engineering review and audit prep—without overclaiming formal compliance.
- **Automation** – Run in CI or locally to gate merges and deployments on policy and security posture.
- **Actionable remediation** – Get concrete suggestions, step-by-step guidance, example snippets, and patch-style diffs—not just “something is wrong.”

---

## Who it is for

- **Platform and DevSecOps engineers** – Standardize pipeline and GitOps reviews; enforce supply chain and governance rules.
- **Security and compliance teams** – Use control-family mappings and reports for evidence and prioritization (with the caveat that mappings are for engineering review, not formal determination).
- **Developers** – Run the agent on MR/PR or locally to fix issues before review.

---

## What it does

1. **Analyzes** CI/CD pipelines (`.gitlab-ci.yml`, `.github/workflows/*.yml`), Argo CD Applications, and Kubernetes manifests.
2. **Detects** plaintext secrets, unpinned images/actions, missing SBOM/provenance, risky permissions, missing approval gates, Argo sync risks, missing resource limits, and cross-system governance gaps.
3. **Produces** a combined verdict (pass / pass_with_warnings / fail) and findings grouped by CI/CD, GitOps, and cross-system.
4. **Generates** Markdown, JSON, or console reports; PR/MR-ready comments; and remediation suggestions with optional patch-style diffs.

---

## Repository

- **GitHub:** [https://github.com/LongTheta/ai-devsecops-policy-enforcement-agent](https://github.com/LongTheta/ai-devsecops-policy-enforcement-agent)
- **GitLab:** [https://gitlab.com/cathcampbell/ai-devsecops-policy-enforcement-agent](https://gitlab.com/cathcampbell/ai-devsecops-policy-enforcement-agent)

---

## Quick start

```bash
git clone https://github.com/LongTheta/ai-devsecops-policy-enforcement-agent.git
cd ai-devsecops-policy-enforcement-agent
pip install -e ".[dev]"
```

**Run a review (GitLab + Argo CD):**
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

**Run a review (GitHub Actions + Argo CD):**
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

**Generate PR/MR comments:**
```bash
python -m ai_devsecops_agent.cli comments \
  --pipeline .github/workflows/ci.yml \
  --gitops k8s/argo-app.yaml \
  --type summary \
  --format github \
  --out pr-comment.md
```

**Get remediation suggestions with patches:**
```bash
python -m ai_devsecops_agent.cli remediate \
  --pipeline .gitlab-ci.yml \
  --gitops k8s/argo-app.yaml \
  --include-patch \
  --out remediations.md
```

---

## CLI commands

### `review` – Run policy review

Runs the full analysis pipeline and produces a report.

| Option | Description |
|--------|-------------|
| `--platform`, `-p` | `gitlab`, `github`, or `local` |
| `--pipeline` | Path to CI/CD pipeline file |
| `--gitops` | Path(s) to Argo CD Application manifests (repeatable) |
| `--manifests` | Path(s) to supporting K8s manifests (repeatable) |
| `--policy` | Path to policy YAML (default: `policies/default.yaml`) |
| `--output`, `-o` | `markdown`, `json`, or `console` |
| `--out` | Write report to file |
| `--repo`, `--branch`, `--compliance` | Context for reporting |

**Exit code:** `0` for pass / pass_with_warnings, `1` for fail.

### `comments` – Generate PR/MR review comments

Converts findings into developer-friendly comments for GitHub PRs or GitLab MRs.

| Option | Description |
|--------|-------------|
| `--type`, `-t` | `summary`, `grouped`, or `individual` |
| `--format`, `-f` | `github`, `gitlab`, or `generic` |
| `--group-by` | `severity` or `category` (for grouped type) |
| `--out` | Write comments to file |

### `remediate` – Output remediation suggestions

Produces actionable fix guidance with summary, rationale, steps, example snippet, and optional patch-style diff.

| Option | Description |
|--------|-------------|
| `--include-patch` | Include patch-style diff suggestions |
| `--out` | Write suggestions to file |

---

## Supported analysis

| Type | What is checked |
|------|-----------------|
| **GitLab CI** | Stages/jobs, plaintext secrets, unpinned images, SBOM/provenance, security scanning, artifact retention, approval gates |
| **GitHub Actions** | Action pinning (tag vs SHA), permissions hardening, `pull_request_target` risk, secret usage, artifact handling, environment protection |
| **GitOps / K8s** | Argo CD Applications (sync policy, prune/selfHeal, project scoping), Deployments (resource limits, securityContext) |
| **Cross-system** | CI-to-GitOps governance gaps: no approval gate before deploy, Argo auto-sync with weak governance, missing traceability, risky promotion flow |
| **SBOM / supply chain** | Presence of SBOM generation, provenance, or signing steps |
| **Compliance mapping** | Findings mapped to NIST-style control families (AC, AU, CM, IA, IR, RA, SA, SC, SI); explicitly not formal compliance |
| **Policy enforcement** | Configurable YAML policies: no plaintext secrets, require SBOM, pinned deps, manual promotion gate, audit evidence |

---

## Policy model

Policies live in `policies/*.yaml`. Each policy has rules with `id`, `name`, `description`, `severity`, `category`, `enabled`, and optional `config`.

**Example rules:**
- `no_plaintext_secrets` – Fail on hardcoded credentials or API keys
- `require_sbom` – Require an SBOM or provenance step
- `require_pinned_pipeline_dependencies` – Prefer digests/SHAs over tags
- `require_manual_promotion_gate` – Expect manual/approval for production
- `require_audit_logging_evidence` – Deployment and promotion should be auditable

See [docs/POLICY-MODEL.md](docs/POLICY-MODEL.md) and `policies/default.yaml`, `policies/fedramp-moderate.yaml`, `policies/supply-chain-baseline.yaml`.

---

## PR/MR comment generation

The agent turns findings into developer-friendly review comments:

- **Summary comment** – Verdict, findings count by severity, top remediations
- **Individual finding comments** – Title, severity, category, why it matters, suggested fix, example snippet
- **Grouped comments** – Findings grouped by severity or category

Output formats: `github`, `gitlab`, `generic` (markdown).

---

## Auto-remediation engine

The engine generates deterministic remediation guidance for common findings:

- **RemediationSuggestion** – `summary`, `rationale`, `steps`, `snippet`, optional `patch`, `confidence`, `notes`, `is_organization_specific`
- **SuggestedPatch** – Patch-style unified diff for applicable findings

**Supported finding types:** plaintext secrets, missing SBOM, unpinned container image, unpinned GitHub Action, risky Argo CD sync, missing promotion gate, missing provenance/signing, missing K8s resource limits.

**Output:** Each remediation includes why the fix matters, step-by-step guidance, example (labeled as example), and optional patch-style diff. Organization-specific fixes are marked.

---

## Project structure

```
ai-devsecops-policy-enforcement-agent/
├── src/ai_devsecops_agent/
│   ├── models.py           # Core models (Finding, Remediation, ReviewResult, etc.)
│   ├── cli.py              # CLI: review, comments, remediate
│   ├── analyzers/          # Pipeline, GitOps, SBOM, cross-system, compliance
│   ├── workflows/          # Review orchestration
│   ├── policies/           # Policy loader
│   ├── reporting/          # Markdown, JSON, console
│   ├── review_comments/    # PR/MR comment generation
│   ├── remediation/       # Auto-remediation engine
│   └── integrations/      # Stubs for GitLab, GitHub, Argo CD
├── policies/               # Policy YAML files
├── examples/               # Example pipelines, manifests, reports
├── docs/                   # Architecture, components, workflows, etc.
└── tests/
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [docs/README.md](docs/README.md) | Documentation index |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | High-level architecture and data flow |
| [docs/COMPONENTS.md](docs/COMPONENTS.md) | **Detailed reference for each component** – models, CLI, analyzers, workflows, policies, reporting, review comments, remediation engine, integrations |
| [docs/WORKFLOWS.md](docs/WORKFLOWS.md) | GitLab + Argo and GitHub + Argo workflows |
| [docs/POLICY-MODEL.md](docs/POLICY-MODEL.md) | Policy structure and rules |
| [docs/INTEGRATIONS.md](docs/INTEGRATIONS.md) | Current and future integrations |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Roadmap and future work |

---

## Example output

**Console:**
```
=== DevSecOps Policy Review ===

Verdict: FAIL

Review failed: 1 critical, 2 high finding(s). Address these before merge or deployment.

Findings by severity:
  critical: 1
  high: 2
  ...
```

**Markdown** – Full report with Executive Summary, Verdict, Findings by Group (GitHub Actions, GitLab/CI/CD, Argo CD/GitOps, Cross-System), Policy Results, Compliance Considerations, Recommended Remediations, Next Steps. See [examples/sample-output.md](examples/sample-output.md).

**JSON** – Structured result for CI or dashboards. See [examples/sample-output.json](examples/sample-output.json).

---

## Disclaimer

**Compliance mappings in this tool are for engineering review and prioritization only.** They are not formal compliance determinations, attestations, or certifications. Control-family mappings (e.g. AC, AU, CM, IA, IR, RA, SA, SC, SI) are indicative and should be validated by your compliance or security team. Use findings and remediations to improve posture; rely on your organization's formal compliance process for official determinations.

---

## License

Use under your organization's terms. Contribute via MR/PR.
