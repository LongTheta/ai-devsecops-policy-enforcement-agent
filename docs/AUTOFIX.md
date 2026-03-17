# Policy-Aware Auto-Fix

The auto-fix layer generates safe, reviewable configuration patches for common CI/CD, GitOps, and Kubernetes issues.

---

## What We Have

| Fix Type | Can Auto-Apply |
|----------|----------------|
| `add_resource_limits` | ✅ Yes |
| `disable_risky_argo_autosync` | ✅ Yes |
| `add_sbom_step` | ✅ Yes |
| `pin_container_image` | ❌ No (suggest only; needs digest) |
| `pin_github_action` | ❌ No (suggest only; needs SHA) |

**Modes:** `suggest` (no changes) | `patch` (write to output dir) | `apply` (only safe fixes, creates backups)

---

## Modes

| Mode | Behavior |
|------|----------|
| **suggest** | No file changes; output proposed fixes, snippets, and diffs |
| **patch** | Write patched copies to `--output-dir`; originals unchanged |
| **apply** | Modify originals; create backups first; only for safe, high-confidence fixes |

---

## Safety Model

Each fix includes:

| Field | Description |
|-------|-------------|
| `safety_level` | `safe` \| `review_required` \| `suggest_only` |
| `confidence` | `low` \| `medium` \| `high` |
| `can_auto_apply` | `true` only for safe, high-confidence fixes |
| `limitations` | Known caveats |
| `rollback_notes` | How to revert |

**Apply mode** only runs fixes with `can_auto_apply=True`. Use `--only-safe` to filter candidates to safe fixes only.

---

## Supported Fixes

| Fix Type | Finding IDs | Safety | Can Auto-Apply |
|----------|-------------|--------|----------------|
| `add_resource_limits` | gitops-003 | safe | ✅ |
| `disable_risky_argo_autosync` | gitops-001, argo-001 | safe | ✅ |
| `add_sbom_step` | pipeline-003, sbom-001, policy-require_sbom | safe | ✅ |
| `pin_container_image` | pipeline-002, github-005, gitops-005 | suggest_only | ❌ |
| `pin_github_action` | github-001, pipeline-002 | suggest_only | ❌ |

**Suggest-only** fixers require manual digest/SHA resolution (Docker API, GitHub API).

---

## CLI

```bash
# From pipeline/gitops/manifests (runs review first)
ai-devsecops-agent auto-fix \
  --platform github \
  --pipeline .github/workflows/ci.yml \
  --gitops k8s/argo-app.yaml \
  --manifests k8s/deployment.yaml \
  --mode suggest

# From review-result.json
ai-devsecops-agent auto-fix \
  --input artifacts/review-result.json \
  --mode patch \
  --output-dir artifacts/fixes

# Apply safe fixes to originals
ai-devsecops-agent auto-fix \
  --pipeline ci.yml \
  --gitops argo.yaml \
  --mode apply \
  --only-safe \
  --backup
```

| Option | Description |
|--------|-------------|
| `--mode` | suggest \| patch \| apply |
| `--only-safe` | Only include fixes with `can_auto_apply=True` |
| `--output-dir` | Required for patch mode |
| `--backup` | Create .bak backups before apply (default: true) |
| `--dry-run` | Show what would be done without writing |
| `--rules` | Restrict to specific fix types |
| `--out` | Write report to file |
| `--format` | markdown \| json |

---

## Example Flow

1. **Review** – Produce findings and artifacts
2. **Suggest** – See proposed fixes without changes
3. **Patch** – Write patched copies to output dir
4. **Apply** – Modify originals (only safe fixes)

See [examples/autofix/README.md](../examples/autofix/README.md) for full examples.

---

## Architecture

```
src/ai_devsecops_agent/autofix/
├── __init__.py
├── models.py
├── engine.py
├── registry.py
├── patcher.py
└── fixers/
    ├── pin_container_image.py
    ├── pin_github_action.py
    ├── add_resource_limits.py
    ├── disable_risky_argo_autosync.py
    └── add_sbom_step.py
```

---

## Future Work

See [ROADMAP.md](ROADMAP.md) for the full roadmap. Auto-fix–specific items:

- **Digest resolution via Docker API** – Enables auto-apply for `pin_container_image`
- **GitHub Action SHA lookup via API** – Enables auto-apply for `pin_github_action`
- **Line-level diff comments** – Post comments on specific lines in PR/MR
- **Auto-fix commit bot** – Git-based apply (create branch, open PR)
