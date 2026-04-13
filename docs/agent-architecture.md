# Agent architecture in this repository

This codebase implements a **deterministic policy agent**: a fixed orchestration pipeline that analyzes CI/CD and GitOps inputs, applies rules, and emits structured results. It is not an open-ended LLM planner; behavior is repeatable and suitable for audit.

---

## Tool usage

In this codebase, “tools” denote **specialized analyzers and integrations** invoked by the workflow, rather than ad hoc model function calls.

| Kind | Role |
|------|------|
| **Pipeline analyzer** | Scans CI YAML (GitLab CI, GitHub Actions) for secrets, supply-chain gaps, platform-specific risks, and **policy-driven** checks when a policy file is supplied. |
| **GitOps analyzer** | Scans Argo CD and Kubernetes manifests for sync safety, resources, and related issues. |
| **SBOM analyzer** | Rule-based checks for SBOM/provenance patterns in pipeline content. |
| **Cross-system analyzer** | Relates pipeline and GitOps artifacts to flag governance gaps. |
| **Compliance mapper** | Enriches findings with control-family hints for reporting. |
| **CLI commands** | `review`, `review-all`, `comments`, `remediate`, `auto-fix`—each builds a `ReviewRequest` or consumes `review-result.json` and writes artifacts (Markdown, JSON, SARIF, PR/MR comments). |
| **Integrations** | Optional fetch of pipeline YAML from GitHub/GitLab for `review-all` and comment posting. |

The **workflow** (`run_review` in `workflows/review_workflow.py`) loads the policy set, runs the analyzers in sequence, groups findings, computes a verdict, and returns a `ReviewResult` for reporting and CI gates.

---

## Decision flow

1. **Input** — `ReviewRequest`: platform context, paths to pipeline / GitOps / manifests, and `policy_path`.
2. **Load policy** — `load_policy_set(policy_path)` so rule metadata and enablement are known for the run.
3. **Analyze** — Pipeline (and SBOM on the same file), GitOps for each path, then cross-system analysis when pipeline and GitOps content are available.
4. **Enrich** — Compliance mappings attached to findings; finding groups normalized for reporting.
5. **Decide** — `_compute_verdict_and_summary`: critical or high severity → **fail**; medium/low → **pass with warnings**; otherwise **pass**.
6. **Output** — `ReviewResult` (verdict, findings, `policy_results`, summaries). The CLI renders reports and, with `--artifact-dir`, writes `review-result.json`, `policy-summary.json`, and related files. **`review` / `review-all` exit with code 1 when verdict is fail**, so CI can block merges.

Remediation text and auto-fix are **downstream**: they consume findings and policy-aware templates; they do not change how findings are detected.

---

## Where validation happens

| Stage | What is validated |
|--------|-------------------|
| **Parse** | Pipeline and manifest YAML is loaded with safe parsing (`yaml.safe_load`). Unparseable input may skip structured checks but avoids arbitrary execution. |
| **Analysis** | Deterministic predicates (regex, structure, presence of steps) produce `Finding` objects with severity, category, and evidence snippets. |
| **Policy application** | For policy-driven pipeline rules, each YAML rule is skipped if `enabled: false`. Enabled rules use the **same detectors** as built-in checks but take **severity and copy from the policy rule** (`policy_rule_id` on the finding). |
| **Verdict** | Aggregated severities map to pass / pass_with_warnings / fail with no randomness. |
| **CI contract** | Exit code and `workflow-status.json` (when artifacts are written) encode pass/fail for automation. |
| **Auto-fix** | Fixers return `FixCandidate` objects; `apply` mode can create backups; `--only-safe` restricts to candidates marked auto-applicable. Optional `--rules` filters by fix type. |

There is no separate validator model. Quality is enforced through **implementation code**, **policy YAML**, and **fixed severity thresholds**.

---

## How actions are constrained by policy

- **Detection** — Policy YAML selects which **named rules** are evaluated and at what severity for pipeline policy findings. Disabled rules never emit policy-scoped findings.
- **Verdict** — The bar for **fail** is fixed in code (any critical or high finding). Policy shapes *what* gets reported and *label severity* for policy-backed findings, not arbitrary runtime branching.
- **Remediation** — The remediation engine maps finding IDs (including `policy-*`) to **templates** (guidance, optional snippets). Organization-specific items are flagged; not everything is auto-patchable.
- **Auto-fix** — Only registered fixers run; each fix has a **safety level** (e.g. safe vs suggest-only). `auto-fix --only-safe` applies only fixes allowed for unattended use. Suggest-only fixers (e.g. pinning without resolved digest) stay human-reviewed.

Policy defines **what must hold** for a compliant pipeline; the engine limits **what the tool may change** so guardrails are not bypassed.

---

## See also

- [ARCHITECTURE.md](ARCHITECTURE.md) — Data flow and component map  
- [POLICY-MODEL.md](POLICY-MODEL.md) — Policy YAML and rule IDs  
- [AUTOFIX.md](AUTOFIX.md) — Modes and safety model  
