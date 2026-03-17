# Pipeline Review Prompt

Use this prompt when invoking an LLM to assist with CI/CD pipeline review.

## Instructions

Analyze the provided CI/CD pipeline configuration and identify:

1. **Secrets and credentials** – Any hardcoded secrets, API keys, or tokens.
2. **Supply chain** – Unpinned images, actions, or dependencies; missing SBOM/provenance.
3. **Governance** – Missing approval gates, manual steps for production, or audit trail.
4. **Safe scripting** – Unsafe use of script blocks, inline curl with variables, or injection risks.

Respond with structured findings: severity, category, description, evidence snippet, and remediation suggestion.

## Input

- Pipeline content (YAML or similar)
- Platform: GitLab CI, GitHub Actions, or other
- Policy set name (optional)

## Output

- List of findings with id, title, severity, category, description, evidence, remediation_summary.
