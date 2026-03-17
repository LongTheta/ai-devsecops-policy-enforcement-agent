# Workflow Integration

This document explains how the AI DevSecOps Policy Enforcement Agent fits into real CI/CD and PR/MR workflows.

---

## Overview

The agent is designed to participate in actual review and delivery flows:

- **GitHub pull requests** – Run on PR, produce artifacts, optionally post comments
- **GitLab merge requests** – Run on MR, produce artifacts, optionally post notes
- **CI/CD job execution** – Generate machine-consumable artifacts for gates and reporting
- **GitOps review flows** – Validate pipeline + Argo CD manifests before promotion

---

## What Is Implemented

| Capability | Status | Notes |
|------------|--------|-------|
| Artifact generation | ✅ | `review-result.json`, `policy-summary.json`, `comments.json`, `remediations.json`, `workflow-status.json` |
| Event context detection | ✅ | Auto-detects `GITHUB_*`, `CI_*` env vars |
| GitHub payload formatting | ✅ | `format_comment_payload()`, `format_review_payload()` |
| GitLab payload formatting | ✅ | `format_comment_payload()`, `format_review_payload()` |
| Post PR comment | ✅ | `post_pr_comment()` with `GITHUB_TOKEN` |
| Post MR comment | ✅ | `post_mr_comment()` with `GITLAB_TOKEN` |
| Fetch from PR/MR | ✅ | `fetch_pipeline_from_pr()`, `fetch_pipeline_from_mr()` |

---

## What Is Stubbed

| Capability | Status | Notes |
|------------|--------|-------|
| Line-level diff comments | 🔲 | Future: post comments on specific lines |
| PR/MR check status API | 🔲 | Future: set check status (e.g. "Policy: Fail") |
| Auto-fetch pipeline from PR | ✅ | Use `review-all --owner/--repo/--pr` |

---

## CI/CD Artifacts

When you run `review` with `--artifact-dir`:

```
artifacts/
├── review-result.json      # Full review output (findings, verdict, context)
├── policy-summary.json     # Verdict, counts by severity, summary
├── report.md               # Human-readable markdown report
├── comments.json           # PR/MR-ready comment bodies (summary, grouped)
├── github-comments.json    # GitHub-specific (when --platform github)
├── gitlab-comments.json    # GitLab-specific (when --platform gitlab)
├── remediations.json       # Remediation bundle with patches
└── workflow-status.json    # Status, exit_code, artifact list (for CI consumption)
```

### workflow-status.json

```json
{
  "status": "fail",
  "verdict": "fail",
  "summary": "Review failed: 1 critical, 2 high finding(s).",
  "finding_count": 5,
  "critical_count": 1,
  "high_count": 2,
  "exit_code": 1,
  "artifacts": [...]
}
```

Use `exit_code` or `status` to fail CI jobs.

---

## Unified Review Command

```bash
ai-devsecops-agent review \
  --platform github \
  --pipeline .github/workflows/ci.yml \
  --gitops k8s/argo-application.yaml \
  --policy policies/default.yaml \
  --include-comments \
  --include-remediations \
  --artifact-dir artifacts/
```

| Option | Description |
|--------|-------------|
| `--artifact-dir` | Write CI/CD artifacts to this directory |
| `--include-comments` | Include `comments.json` (default: true) |
| `--include-remediations` | Include `remediations.json` (default: true) |

---

## Auto-Fix

The agent can generate or apply safe config patches. See [AUTOFIX.md](AUTOFIX.md) for details.

```bash
ai-devsecops-agent auto-fix --input artifacts/review-result.json --mode patch --output-dir artifacts/fixes
```

---

## GitHub Actions Example

See [.github/workflows/policy-review.yml](../.github/workflows/policy-review.yml) and [examples/workflows/github-policy-review.yml](../examples/workflows/github-policy-review.yml).

Key steps:

1. Checkout, install agent
2. Run `review` with `--platform github` and `--artifact-dir artifacts`
3. Upload artifacts with `if: always()` (even on failure)
4. Fail job when verdict is `fail` via `if: steps.review.outcome == 'failure'`

For full GitHub workflow details, see [GITHUB-WORKFLOW.md](GITHUB-WORKFLOW.md).

---

## GitLab CI Example

See [.gitlab-ci.yml](../.gitlab-ci.yml) (policy-review job) and [examples/workflows/gitlab-policy-review.yml](../examples/workflows/gitlab-policy-review.yml).

Add a job that runs the agent with `--platform gitlab` and `--artifact-dir artifacts`. Use `artifacts: when: always` so artifacts are available even on failure.

For full GitLab workflow details, see [GITLAB-WORKFLOW.md](GITLAB-WORKFLOW.md).

---

## Posting Comments

To post the review as a PR/MR comment:

```bash
ai-devsecops-agent comments \
  --platform github \
  --pipeline .github/workflows/ci.yml \
  --gitops k8s/argo-app.yaml \
  --format github \
  --post \
  --owner myorg \
  --repo myrepo \
  --pr 42
```

Requires `GITHUB_TOKEN` (GitHub) or `GITLAB_TOKEN` (GitLab) with appropriate scopes.

---

## Event Context

When running in GitHub Actions or GitLab CI, the agent auto-detects:

| Source | Env vars |
|--------|----------|
| GitHub | `GITHUB_REPOSITORY`, `GITHUB_SHA`, `GITHUB_REF_NAME`, `GITHUB_ACTOR` |
| GitLab | `CI_PROJECT_PATH`, `CI_COMMIT_SHA`, `CI_COMMIT_REF_NAME`, `CI_MERGE_REQUEST_IID` |

This context is included in `workflow-status.json` for traceability.
