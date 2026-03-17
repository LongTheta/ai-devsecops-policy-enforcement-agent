# Roadmap

This document tracks implemented features, near-term goals, and future work for the AI DevSecOps Policy Enforcement Agent.

---

## Implemented

| Capability | Status | Notes |
|------------|--------|-------|
| Pipeline analysis | ✅ | GitLab CI, GitHub Actions |
| GitOps / Argo CD analysis | ✅ | Sync policy, resource limits, security context |
| SBOM analyzer | ✅ | Supply chain visibility |
| Cross-system analyzer | ✅ | CI↔GitOps governance gaps |
| Policy engine | ✅ | YAML-based rules |
| Compliance mapping | ✅ | Control families (AC, AU, CM, etc.) |
| Remediation suggestions | ✅ | Step-by-step, snippets, patches |
| Policy-aware auto-fix | ✅ | suggest \| patch \| apply modes |
| PR/MR comment posting | ✅ | GitHub, GitLab |
| Artifact generation | ✅ | review-result.json, comments.json, etc. |
| SARIF output | ✅ | GitHub Advanced Security, GitLab SAST |
| Remote fetch | ✅ | `fetch_pipeline_from_pr()`, `fetch_pipeline_from_mr()` |
| **review-all** | ✅ | Unified review with remote fetch from PR/MR |

---

## Near-Term

| Item | Status | Notes |
|------|--------|-------|
| ~~Unified review-all with remote fetch~~ | ✅ Done | `review-all --owner/--repo/--pr` or `--project/--mr` |

---

## Mid-Term

| Item | Status | Notes |
|------|--------|-------|
| SBOM MCP tool | 🔲 | MCP server for SBOM queries |
| Evaluation history + trend tracking | 🔲 | Store verdicts over time |
| Observability (OTel / Logfire) | 🔲 | Traces, metrics |

---

## Auto-Fix Future Work

| Item | Status | Notes |
|------|--------|-------|
| Digest resolution via Docker API | 🔲 | Optional; enables auto-apply for `pin_container_image` |
| GitHub Action SHA lookup via API | 🔲 | Optional; enables auto-apply for `pin_github_action` |
| Line-level diff comments | 🔲 | Post comments on specific lines in PR/MR |
| Auto-fix commit bot | 🔲 | Git-based apply (create branch, open PR) |
| Deduplicate fix candidates | 🔲 | Same fix for multiple findings (e.g. pin_github_action) |

---

## Advanced

| Item | Status | Notes |
|------|--------|-------|
| Auto-fix commit bot (Git-based apply) | 🔲 | Create branch, apply fixes, open PR |
| Compliance evidence generator | 🔲 | Structured evidence for audits |
| Drift detection | 🔲 | CI → GitOps → runtime consistency |

---

## Not Yet Implemented

| Capability | Notes |
|------------|-------|
| Line-level diff comments | Post comments on specific lines in PR/MR |
| PR/MR check status API | Set check status (e.g. "Policy: Fail") |
| Auto-fix commit bot | Git-based apply (create branch, open PR) |
| Digest/SHA resolution | Docker API for images; GitHub API for actions |

---

## How to Contribute

1. **Near-term** – Review-all is done; mid-term items are open.
2. **Auto-fix** – Digest/SHA resolution would require Docker/GitHub API clients.
3. **MCP** – SBOM tool would expose a Model Context Protocol server.

See [WORKFLOW-INTEGRATION.md](WORKFLOW-INTEGRATION.md) for integration details and [AUTOFIX.md](AUTOFIX.md) for auto-fix architecture.
