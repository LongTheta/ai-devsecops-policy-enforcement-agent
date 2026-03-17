# GitHub Workflow Integration

How to run the AI DevSecOps Policy Enforcement Agent in GitHub Actions and PR workflows.

---

## Quick Start

Add a policy review workflow to `.github/workflows/`:

```yaml
name: Policy Review

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

jobs:
  policy-review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.10"

      - name: Install agent
        run: pip install -e .

      - name: Run policy review
        id: review
        run: |
          mkdir -p artifacts
          ai-devsecops-agent review \
            --platform github \
            --pipeline .github/workflows/ci.yml \
            --gitops k8s/argo-application.yaml \
            --policy policies/default.yaml \
            --output markdown \
            --out artifacts/report.md \
            --artifact-dir artifacts
        continue-on-error: true

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: policy-review-artifacts
          path: artifacts/

      - name: Fail on policy failure
        if: steps.review.outcome == 'failure'
        run: exit 1
```

---

## Artifacts Produced

When `--platform github` and `--artifact-dir` are used:

| Artifact | Description |
|----------|-------------|
| `review-result.json` | Full review output (findings, verdict, context) |
| `policy-summary.json` | Verdict, counts by severity, summary |
| `github-comments.json` | PR-ready comment bodies (summary, grouped) for posting |
| `report.md` | Human-readable markdown report |
| `remediations.json` | Remediation bundle with patches |
| `workflow-status.json` | Status, exit_code (for CI consumption) |

### github-comments.json

Structure for PR comment posting:

```json
{
  "platform": "github",
  "summary_body": "## DevSecOps Policy Review\n\n**Verdict:** FAIL\n...",
  "grouped_body": "## DevSecOps Policy Review – Findings\n...",
  "ready_for_post": true
}
```

Use `summary_body` or `grouped_body` with `post_pr_comment(owner, repo, pr_number, body)`.

---

## Policy-Based Pass/Fail

- **Pass** – Exit code 0.
- **Pass with warnings** – Exit code 0.
- **Fail** – Exit code 1 (critical or high findings).

The job fails when the agent exits 1. Use `continue-on-error: true` on the review step, then `if: steps.review.outcome == 'failure'` to fail the job while still uploading artifacts.

---

## Posting PR Comments

To post the review as a PR comment (requires `GITHUB_TOKEN`):

```bash
ai-devsecops-agent comments \
  --platform github \
  --pipeline .github/workflows/ci.yml \
  --gitops k8s/argo-app.yaml \
  --format github \
  --post \
  --owner ${{ github.repository_owner }} \
  --repo ${{ github.event.repository.name }} \
  --pr ${{ github.event.pull_request.number }}
```

Or use the artifact and API directly:

```yaml
# In a workflow step with GITHUB_TOKEN
- name: Post PR comment
  run: |
    BODY=$(jq -r '.summary_body' artifacts/github-comments.json)
    # POST to /repos/{owner}/{repo}/issues/{pr_number}/comments with body
```

---

## Example: This Repo

See [.github/workflows/policy-review.yml](../.github/workflows/policy-review.yml) for the policy review workflow used in this repository.

---

## What Is Stubbed

| Capability | Status |
|------------|--------|
| Post PR comment from CI | ✅ Implemented (`comments --post`) |
| Line-level review comments | 🔲 Stubbed |
| PR check status API | 🔲 Stubbed |
| Auto-fetch pipeline from PR | ✅ Use `review-all --owner/--repo/--pr` |
