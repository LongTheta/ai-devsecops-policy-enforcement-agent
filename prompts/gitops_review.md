# GitOps Review Prompt

Use this prompt when invoking an LLM to assist with Kubernetes/Argo CD manifest review.

## Instructions

Analyze the provided GitOps/Kubernetes manifests and identify:

1. **Sync and automation** – Automated sync without gates; drift risk.
2. **Scoping** – Default or overly broad project/namespace; RBAC concerns.
3. **Workload security** – Missing resource limits, securityContext, or unsafe settings.
4. **Promotion** – Missing promotion boundaries or environment separation.

Respond with structured findings: severity, category, description, evidence, remediation.

## Input

- Manifest content (YAML)
- Tool: Argo CD Application, raw K8s, Helm values, Kustomize overlay
- Environment: dev, staging, production

## Output

- List of findings with id, title, severity, category, description, evidence, remediation_summary.
