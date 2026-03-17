# Remediation Generation Prompt

Use this prompt when generating remediation suggestions or patches.

## Instructions

For each finding, produce:

1. **Summary** – One-line remediation summary.
2. **Description** – Step-by-step guidance (optional).
3. **Snippet** – Example fixed YAML or code snippet (optional). Prefer minimal, safe examples.
4. **Reference** – Official doc or tool link (optional).

Keep remediations actionable and scoped. Do not generate secrets or real credentials.

## Input

- Finding (id, title, description, evidence, category)
- Platform (gitlab, github, k8s, argocd)

## Output

- remediation_summary, description, snippet, reference_url.
