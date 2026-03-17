# Auto-Fix Examples

Demonstrates the policy-aware auto-fix flow: review → suggest → patch.

## Example Flow

```bash
# 1. Run review (produces findings)
ai-devsecops-agent review \
  --pipeline insecure-pipeline-for-autofix.yml \
  --gitops insecure-argo-for-autofix.yaml \
  --manifests insecure-for-autofix.yaml \
  --artifact-dir artifacts

# 2. Suggest fixes (no file changes)
ai-devsecops-agent auto-fix \
  --input artifacts/review-result.json \
  --mode suggest

# 3. Write patched copies to output directory
ai-devsecops-agent auto-fix \
  --input artifacts/review-result.json \
  --mode patch \
  --output-dir artifacts/fixes

# 4. Apply safe fixes to originals (creates backups)
ai-devsecops-agent auto-fix \
  --pipeline insecure-pipeline-for-autofix.yml \
  --gitops insecure-argo-for-autofix.yaml \
  --manifests insecure-for-autofix.yaml \
  --mode apply \
  --only-safe
```

## Files

| File | Issues | Fixable |
|------|--------|---------|
| `insecure-for-autofix.yaml` | Missing resource limits | `add_resource_limits` |
| `insecure-argo-for-autofix.yaml` | Risky prune/selfHeal | `disable_risky_argo_autosync` |
| `insecure-pipeline-for-autofix.yml` | Unpinned action, no SBOM | `pin_github_action` (suggest), `add_sbom_step` |

## Safe to Auto-Apply

- `add_resource_limits` – deterministic
- `disable_risky_argo_autosync` – deterministic
- `add_sbom_step` – deterministic template

## Suggest Only

- `pin_container_image` – requires digest resolution
- `pin_github_action` – requires SHA lookup
