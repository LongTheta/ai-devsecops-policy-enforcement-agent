# Documentation

## Overview

This folder contains documentation for the AI DevSecOps Policy Enforcement Agent.

## What We Have

| Area | Implemented |
|------|-------------|
| **Analysis** | Pipeline (GitLab CI, GitHub Actions), GitOps (Argo CD, K8s), SBOM, cross-system |
| **Policy** | YAML-based rules, verdict (pass/fail/warnings), compliance mapping |
| **Outputs** | Markdown, JSON, SARIF, artifacts (review-result.json, comments.json, remediations.json) |
| **Comments** | PR/MR comment generation (GitHub/GitLab formats); live posting with token |
| **Auto-fix** | suggest, patch, apply modes; 3 safe fixers (resource limits, Argo sync, SBOM); 2 suggest-only (pin image, pin action) |
| **Workflow** | Remote fetch from PR/MR (`review-all`), artifact generation, CI integration |

## What We Don't Have (Yet)

- Line-level diff comments
- PR/MR check status API
- Auto-fix commit bot (Git-based apply)
- Digest/SHA resolution for pin fixers (Docker/GitHub API)

## Documents

| Document | Description |
|----------|-------------|
| [system-thinking.md](system-thinking.md) | **System model** (policy / orchestration / memory), operational design, evaluation, failure modes |
| [ARCHITECTURE.md](ARCHITECTURE.md) | High-level architecture, data flow, and component overview |
| [COMPONENTS.md](COMPONENTS.md) | **Detailed reference for each component** – models, CLI, analyzers, workflows, policies, reporting, review comments, remediation engine, integrations |
| [WORKFLOWS.md](WORKFLOWS.md) | GitLab + Argo and GitHub + Argo combined workflows; report structure; comment and remediation commands |
| [POLICY-MODEL.md](POLICY-MODEL.md) | Policy YAML structure, rule fields, built-in rule IDs, verdict logic |
| [INTEGRATIONS.md](INTEGRATIONS.md) | Current (file-based) and future (GitLab, GitHub, Argo CD API) integrations |
| [WORKFLOW-INTEGRATION.md](WORKFLOW-INTEGRATION.md) | **CI/CD integration** – artifacts, GitHub Actions, GitLab CI, posting comments |
| [GITLAB-WORKFLOW.md](GITLAB-WORKFLOW.md) | **GitLab-specific** – CI job, artifacts, MR comments, pass/fail |
| [GITHUB-WORKFLOW.md](GITHUB-WORKFLOW.md) | **GitHub-specific** – Actions workflow, artifacts, PR comments |
| [AUTOFIX.md](AUTOFIX.md) | Policy-aware auto-fix – suggest, patch, apply modes |
| [ROADMAP.md](ROADMAP.md) | **Roadmap** – implemented, near-term, mid-term, future work |

## Quick links

- **System model & operations** → [system-thinking.md](system-thinking.md)
- **Understanding the system** → [ARCHITECTURE.md](ARCHITECTURE.md)
- **Component details** → [COMPONENTS.md](COMPONENTS.md)
- **Running reviews** → [WORKFLOWS.md](WORKFLOWS.md)
- **CI/CD integration** → [WORKFLOW-INTEGRATION.md](WORKFLOW-INTEGRATION.md)
- **Configuring policies** → [POLICY-MODEL.md](POLICY-MODEL.md)
