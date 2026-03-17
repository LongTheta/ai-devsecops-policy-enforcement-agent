# Architecture

## Overview

The AI DevSecOps Policy Enforcement Agent is structured as a pipeline of **analyzers** fed by **policies** and **review context**, producing a **ReviewResult** that can be rendered as reports, PR/MR comments, or remediation suggestions.

```
┌─────────────────┐     ┌──────────────────────────────────────────────────────────┐
│  ReviewRequest  │────▶│  run_review()                                             │
│  + Context      │     │  • Load policy                                             │
└─────────────────┘     │  • Pipeline analyzer (secrets, SBOM, pins, gates)          │
                        │  • GitOps analyzer (Argo CD, K8s resources)                 │
                        │  • SBOM analyzer                                            │
                        │  • Cross-system analyzer (CI↔GitOps governance gaps)       │
                        │  • Compliance mapping                                       │
                        │  • Verdict                                                  │
                        └──────────────────────────────────────────────────────────┘
                                         │
                                         ▼
                        ┌──────────────────────────────────────────────────────────┐
                        │  ReviewResult                                             │
                        │  (verdict, summary, findings, policy_results, etc.)       │
                        └──────────────────────────────────────────────────────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    ▼                    ▼                    ▼
            ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
            │  Reporting   │    │   Review     │    │  Remediation │
            │  Markdown    │    │   Comments   │    │  Engine      │
            │  JSON        │    │   Summary    │    │  Remediation │
            │  Console     │    │   Grouped    │    │  Patch       │
            └──────────────┘    │   Individual │    └──────────────┘
                                └──────────────┘
```

## Components

| Component | Role |
|-----------|------|
| **models** | Pydantic models: Finding, Remediation, RemediationSuggestion, SuggestedPatch, PolicyRule, ReviewRequest, ReviewResult, Verdict |
| **policies/loader** | Load YAML policy sets and expose rules to analyzers |
| **analyzers/pipeline_analyzer** | Inspect CI/CD YAML for secrets, unpinned deps, SBOM, approval gates; GitLab- and GitHub Actions-specific checks |
| **analyzers/gitops_analyzer** | Inspect K8s/Argo CD manifests for sync policy, prune/selfHeal, project scoping, resources, securityContext |
| **analyzers/cross_system_analyzer** | Cross-check CI and GitOps for governance gaps, traceability, promotion risks |
| **analyzers/sbom_analyzer** | Rule-based SBOM/provenance/signing presence |
| **analyzers/compliance_mapper** | Map findings to broad NIST-style control families |
| **workflows/review_workflow** | Orchestrate analyzers, compute verdict, build ReviewResult |
| **reporting** | Markdown, JSON, console formatters |
| **review_comments** | PR/MR comment generation (summary, individual, grouped) |
| **remediation/engine** | Deterministic auto-remediation: RemediationSuggestion, SuggestedPatch |
| **integrations** | Stubs for GitLab, GitHub, Argo CD (future) |

**For detailed component documentation, see [COMPONENTS.md](COMPONENTS.md).**

## Data flow

1. **CLI** builds `ReviewRequest` (context, pipeline path, gitops paths, manifest paths, policy path).
2. **run_review** loads policy set, runs pipeline analyzer (and SBOM) on pipeline file, runs GitOps analyzer on each manifest path, runs cross-system analyzer when pipeline + GitOps present, assigns finding groups, enriches findings with compliance mappings, computes verdict and summary.
3. **Verdict**: fail if any critical/high; pass_with_warnings if medium/low; pass otherwise.
4. **Output**: Report (Markdown/JSON/console), comments, or remediation suggestions.

## Finding groups

Findings are grouped for reporting:

- **github_actions** – GitHub Actions workflow findings
- **ci_cd** – GitLab CI / generic pipeline findings
- **gitops** – Argo CD Application and Kubernetes manifest findings
- **cross_system** – CI-to-GitOps governance gaps

## Extensibility

- **New analyzers**: Implement a function `(content?, path?) -> list[Finding]` and call it from `review_workflow.run_review`.
- **New policy rules**: Add entries in policy YAML and handle rule id in pipeline_analyzer (or a dedicated policy evaluator).
- **New remediation templates**: Add entries to `_REMEDIATION_REGISTRY` in `remediation/engine.py`.
- **Integrations**: Replace stubs in `integrations/` with real API clients; inject context into `ReviewContext.integrations` or use to fetch pipeline/MR content.
