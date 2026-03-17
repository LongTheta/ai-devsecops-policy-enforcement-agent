# Documentation

## Overview

This folder contains documentation for the AI DevSecOps Policy Enforcement Agent.

## Documents

| Document | Description |
|----------|-------------|
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

- **Understanding the system** → [ARCHITECTURE.md](ARCHITECTURE.md)
- **Component details** → [COMPONENTS.md](COMPONENTS.md)
- **Running reviews** → [WORKFLOWS.md](WORKFLOWS.md)
- **CI/CD integration** → [WORKFLOW-INTEGRATION.md](WORKFLOW-INTEGRATION.md)
- **Configuring policies** → [POLICY-MODEL.md](POLICY-MODEL.md)
