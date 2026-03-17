# Component Reference

This document explains each component of the AI DevSecOps Policy Enforcement Agent in detail.

---

## 1. Models (`models.py`)

Core Pydantic models used throughout the system.

### Enums

| Model | Purpose |
|-------|---------|
| **Severity** | `critical`, `high`, `medium`, `low`, `info` – finding severity |
| **Verdict** | `pass`, `pass_with_warnings`, `fail` – overall review outcome |
| **Platform** | `gitlab`, `github`, `local` – CI/CD platform context |

### Core models

| Model | Purpose |
|-------|---------|
| **Finding** | A single policy or security finding. Fields: `id`, `title`, `severity`, `category`, `description`, `evidence`, `impacted_files`, `control_families`, `remediation_summary`, `remediation`, `policy_rule_id`, `source_analyzer`, `finding_group` |
| **Remediation** | Simple suggested fix. Fields: `summary`, `description`, `snippet`, `reference_url` |
| **RemediationSuggestion** | Full remediation guidance. Fields: `id`, `applies_to_finding_id`, `summary`, `rationale`, `steps`, `snippet`, `patch`, `confidence`, `notes`, `is_organization_specific` |
| **SuggestedPatch** | Patch-style diff. Fields: `id`, `applies_to_finding_id`, `diff`, `description`, `confidence`, `notes` |
| **ComplianceMapping** | Maps a finding to NIST-style control families (AC, AU, CM, etc.). Fields: `control_family`, `control_id`, `rationale`, `note` |

### Policy models

| Model | Purpose |
|-------|---------|
| **PolicyRule** | Single rule from YAML. Fields: `id`, `name`, `description`, `severity`, `category`, `enabled`, `config` |
| **PolicySet** | Loaded policy. Fields: `name`, `description`, `rules` |

### Request/result models

| Model | Purpose |
|-------|---------|
| **ReviewContext** | Context for review. Fields: `platform`, `repository_name`, `branch`, `environment`, `compliance_mode`, `data_sensitivity`, etc. |
| **ReviewRequest** | Input to a review. Fields: `context`, `pipeline_path`, `gitops_paths`, `manifest_paths`, `policy_path`, `extra_paths` |
| **ReviewResult** | Output of a review. Fields: `verdict`, `summary`, `findings`, `policy_results`, `compliance_considerations`, `recommended_remediations`, `next_steps`, `context`, `metadata` |

---

## 2. CLI (`cli.py`)

Command-line interface built with Click.

| Command | Purpose |
|---------|---------|
| **review** | Run full policy review. Accepts pipeline, gitops, manifests, policy paths. Outputs markdown, JSON, or console. Exits 1 on fail verdict. |
| **comments** | Generate PR/MR review comments. Types: summary, grouped, individual. Formats: github, gitlab, generic. |
| **remediate** | Output remediation suggestions with summary, rationale, steps, example, optional patch. |

---

## 3. Analyzers (`analyzers/`)

Analyzers inspect files and return lists of `Finding` objects. Detection logic is separate from remediation.

### Pipeline analyzer (`pipeline_analyzer.py`)

Inspects CI/CD YAML (GitLab CI, GitHub Actions).

**Checks:**
- Plaintext secrets (pipeline-001)
- Unpinned images/actions (pipeline-002)
- Missing SBOM step (pipeline-003)
- Unsafe scripts (pipeline-004)
- Missing approval gate (pipeline-005)
- GitLab-specific: security scanning (gitlab-001), artifact retention (gitlab-002), lockfile (gitlab-003)
- GitHub-specific: action pinning (github-001), permissions (github-002), pull_request_target (github-003), artifact retention (github-004), container digest (github-005), environment protection (github-006)
- Policy-driven: no_plaintext_secrets, require_sbom

### GitOps analyzer (`gitops_analyzer.py`)

Inspects Kubernetes and Argo CD manifests.

**Checks:**
- Invalid YAML (gitops-000)
- Argo CD automated sync (gitops-001)
- Default/missing project (gitops-002)
- Missing resource limits (gitops-003)
- No pod securityContext (gitops-004)
- Argo-specific: prune+selfHeal (argo-001), prod path with HEAD (argo-002)

### SBOM analyzer (`sbom_analyzer.py`)

Rule-based detection of SBOM/provenance/signing presence in pipeline content.

**Checks:**
- No SBOM generation (sbom-001)
- No provenance or signing (sbom-002)

### Cross-system analyzer (`cross_system_analyzer.py`)

Analyzes pipeline and GitOps configs together for governance gaps.

**Checks:**
- Pipeline deploys without approval gate (cross-001)
- Argo auto-sync with default project (cross-002)
- No SBOM before GitOps delivery (cross-003)
- No artifact traceability (cross-004)
- Risky promotion flow (cross-005)
- Broad permissions with deploy (cross-006)

### Compliance mapper (`compliance_mapper.py`)

Maps findings to NIST-style control families (AC, AU, CM, IA, IR, RA, SA, SC, SI). Enriches findings with `control_families`. Explicitly not formal compliance.

---

## 4. Workflows (`workflows/review_workflow.py`)

Orchestrates the review pipeline.

**`run_review(request: ReviewRequest) -> ReviewResult`**

1. Load policy from `policy_path`
2. Run pipeline analyzer on pipeline file
3. Run SBOM analyzer on pipeline content
4. Run GitOps analyzer on each gitops and manifest path
5. Run cross-system analyzer when pipeline + GitOps present
6. Assign `finding_group` (github_actions, ci_cd, gitops, cross_system)
7. Enrich findings with compliance mappings
8. Compute verdict and summary
9. Build ReviewResult with recommended remediations and next steps

**Verdict logic:** fail if any critical/high; pass_with_warnings if medium/low; pass otherwise.

---

## 5. Policies (`policies/loader.py`)

**`load_policy_set(path) -> PolicySet`**

Loads YAML policy files. Returns PolicySet with rules. Skips invalid rules. Uses Severity.HIGH for unknown severity.

---

## 6. Reporting (`reporting/`)

Converts `ReviewResult` to output formats.

| Module | Function | Output |
|--------|----------|--------|
| **markdown_report** | `render_markdown(result)` | Full Markdown report with findings grouped by GitHub Actions, GitLab/CI/CD, Argo CD/GitOps, Cross-System |
| **json_report** | `render_json(result)` | JSON with verdict, summary, findings, findings_by_group, policy_results, compliance_considerations, etc. |
| **console_report** | `render_console(result)` | Compact console output: verdict, summary, severity counts, top findings |

---

## 7. Review comments (`review_comments/`)

Generates PR/MR-ready comments from findings.

| Function | Purpose |
|----------|---------|
| `render_summary_comment(result, format)` | Overall summary: verdict, findings by severity, top remediations |
| `render_finding_comment(finding, format, include_evidence, include_example)` | Single finding: title, severity, category, why it matters, suggested fix, example snippet |
| `render_grouped_comments(result, group_by, format)` | Findings grouped by severity or category |
| `render_all_finding_comments(result, format)` | List of (file_path, comment_body) for API posting |

**Formats:** `github`, `gitlab`, `generic` (markdown).

---

## 8. Remediation (`remediation/`)

### Engine (`engine.py`)

Deterministic auto-remediation. No file editing; generates guidance only.

| Function | Purpose |
|----------|---------|
| `generate_remediation(finding) -> RemediationSuggestion | None` | Full remediation: summary, rationale, steps, snippet, optional patch |
| `generate_patch(finding) -> SuggestedPatch | None` | Patch-style diff when applicable |

**Template registry:** Maps finding IDs to RemediationSuggestion templates. Covers 25+ finding types.

**Patch generation:** For some findings (e.g. unpinned image, permissions, K8s resources), generates unified diff from evidence or generic template.

### Suggestions (`suggestions.py`)

Backward-compatible wrapper for consumers expecting `Remediation`:

| Function | Purpose |
|----------|---------|
| `suggest_remediation(finding) -> Remediation | None` | Returns Remediation (summary, description, snippet) from engine |
| `get_remediation_snippet(finding_id) -> str | None` | Returns snippet only for legacy callers |

---

## 9. Integrations (`integrations/`)

Stubs for future live API integrations. Currently return `None`.

| Module | Function | Future purpose |
|--------|----------|----------------|
| **gitlab** | `get_merge_request_context(project_id, mr_iid)` | Fetch MR diff, pipeline YAML, project settings; post report as MR comment |
| **github** | `get_pull_request_context(owner, repo, pr_number)` | Fetch PR diff, workflow runs; post report as PR comment or check |
| **argo** | `get_application_context(server, app_name)` | Fetch Application spec and sync status; enrich GitOps context |

---

## 10. Config (`config.py`)

Utility functions for policy path, output format, output path, compliance mode, and API tokens. Used for configuration lookup; CLI options take precedence.

---

## Data flow summary

```
ReviewRequest
    │
    ▼
run_review()
    │
    ├─► load_policy_set()
    ├─► analyze_pipeline()
    ├─► analyze_sbom()
    ├─► analyze_gitops() [per path]
    ├─► analyze_cross_system()
    ├─► enrich_findings_with_controls()
    └─► _compute_verdict_and_summary()
    │
    ▼
ReviewResult
    │
    ├─► render_markdown() / render_json() / render_console()
    ├─► render_summary_comment() / render_finding_comment() / render_grouped_comments()
    └─► generate_remediation() / generate_patch()
```
