# Roadmap

## Current (MVP)

- [x] Core models and policy loader
- [x] Pipeline analyzer (secrets, unpinned, SBOM, approval, script; GitLab and GitHub Actions specific)
- [x] GitOps analyzer (Argo CD sync, project, resources, securityContext)
- [x] Cross-system analyzer (CI↔GitOps governance gaps)
- [x] Compliance mapper (broad control families)
- [x] SBOM analyzer (presence of SBOM/provenance/signing)
- [x] Markdown, JSON, console reporting (findings grouped by GitHub Actions, GitLab, GitOps, cross-system)
- [x] CLI `review` command
- [x] CLI `comments` command (PR/MR comment generation)
- [x] CLI `remediate` command (auto-remediation with patch-style diffs)
- [x] Auto-remediation engine (RemediationSuggestion, SuggestedPatch)
- [x] Example pipelines and manifests (GitLab + Argo, GitHub + Argo)
- [x] Unit tests and GitHub Actions
- [x] SARIF output (`--output sarif`) for GitHub Advanced Security, GitLab SAST
- [x] Policy engine – Full evaluation of all policy rules (pinned deps, manual gate, artifact traceability, audit evidence, signed artifacts)
- [x] GitLab integration – Fetch file content and MR context from GitLab API
- [x] GitHub integration – Fetch file content and PR context from GitHub API

## Repository

- **GitHub:** [github.com/LongTheta/ai-devsecops-policy-enforcement-agent](https://github.com/LongTheta/ai-devsecops-policy-enforcement-agent)
- **GitLab:** [gitlab.com/cathcampbell/ai-devsecops-policy-enforcement-agent](https://gitlab.com/cathcampbell/ai-devsecops-policy-enforcement-agent)

## Next

- [x] **MR/PR comment posting** – `comments --post` with `--owner/--repo/--pr` (GitHub) or `--project/--mr` (GitLab)
- [ ] **Argo CD integration** – Read Application status and sync state for context
- [ ] **LLM-assisted review** – Optional pass: send pipeline/manifest + prompts to an LLM for additional findings and remediations
- [ ] **MCP server** – Expose agent as Model Context Protocol server for IDE/chat integrations

---

## Related docs

- [COMPONENTS.md](COMPONENTS.md) – Detailed component reference

## Later

- [ ] **Policy engine actions** – Configurable actions (block, warn, info) per rule
- [ ] **Custom rules** – User-defined rules (e.g. regex or script) in policy YAML
- [ ] **Dashboard** – Simple UI for running reviews and viewing history (optional)
