# Integrations

## Current

- **CLI** – Local file-based review; pipeline and GitOps paths point to files on disk.
- **Policy YAML** – Loaded from path; no remote policy server.

## Implemented (MVP)

| Integration | Module | Purpose |
|-------------|--------|---------|
| **GitLab** | `integrations/gitlab.py` | `fetch_file_content()`, `fetch_pipeline_from_mr()`, `post_mr_comment()` |
| **GitHub** | `integrations/github.py` | `fetch_file_content()`, `fetch_pipeline_from_pr()`, `post_pr_comment()` |

## Stubbed (future)

| Integration | Module | Purpose |
|-------------|--------|---------|
| **GitLab** | `integrations/gitlab.py` | Line-level diff comments |
| **GitHub** | `integrations/github.py` | PR check / status API |
| **Argo CD** | `integrations/argo.py` | Fetch Application spec and sync status; enrich context for GitOps review |

## Environment

- `GITLAB_URL`, `GITLAB_TOKEN` – For GitLab API (when implemented).
- `GITHUB_TOKEN` – For GitHub API (when implemented).
- Argo CD server URL and auth TBD.

## MCP / API

Future versions may expose:

- **MCP server** – Tools/resources for “review this path” or “review MR/PR” for use in Claude, VS Code MCP, or other MCP clients.
- **REST API** – POST `/review` with pipeline/manifest payload; return JSON report for CI or dashboards.

---

## Related docs

- [COMPONENTS.md](COMPONENTS.md) – Detailed component reference, including integrations stubs
