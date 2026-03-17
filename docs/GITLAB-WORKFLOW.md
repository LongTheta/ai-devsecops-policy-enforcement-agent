# GitLab Workflow Integration

How to run the AI DevSecOps Policy Enforcement Agent in GitLab CI and MR workflows.

---

## Quick Start

Add a policy review job to your `.gitlab-ci.yml`:

```yaml
policy-review:
  stage: test
  image: python:3.10-slim
  before_script:
    - pip install -e .
  script:
    - mkdir -p artifacts
    - |
      ai-devsecops-agent review \
        --platform gitlab \
        --pipeline .gitlab-ci.yml \
        --gitops k8s/argo-application.yaml \
        --policy policies/default.yaml \
        --output markdown \
        --out artifacts/report.md \
        --artifact-dir artifacts
  artifacts:
    when: always
    paths:
      - artifacts/
    expire_in: 7 days
```

---

## Artifacts Produced

When `--platform gitlab` and `--artifact-dir` are used:

| Artifact | Description |
|----------|-------------|
| `review-result.json` | Full review output (findings, verdict, context) |
| `policy-summary.json` | Verdict, counts by severity, summary |
| `gitlab-comments.json` | MR-ready comment bodies (summary, grouped) for posting |
| `report.md` | Human-readable markdown report |
| `remediations.json` | Remediation bundle with patches |
| `workflow-status.json` | Status, exit_code (for CI consumption) |

### gitlab-comments.json

Structure for MR note posting:

```json
{
  "platform": "gitlab",
  "summary_body": "## DevSecOps Policy Review\n\n**Verdict:** FAIL\n...",
  "grouped_body": "## DevSecOps Policy Review – Findings\n...",
  "ready_for_post": true
}
```

Use `summary_body` or `grouped_body` with `post_mr_comment(project_id, mr_iid, body)`.

---

## Policy-Based Pass/Fail

- **Pass** – Exit code 0.
- **Pass with warnings** – Exit code 0.
- **Fail** – Exit code 1 (critical or high findings).

The job fails when the agent exits 1. Set `allow_failure: false` (default) to fail the pipeline on policy failure.

---

## Posting MR Comments

To post the review as an MR note (requires `GITLAB_TOKEN`):

```bash
ai-devsecops-agent comments \
  --platform gitlab \
  --pipeline .gitlab-ci.yml \
  --gitops k8s/argo-app.yaml \
  --format gitlab \
  --post \
  --project $CI_PROJECT_PATH \
  --mr $CI_MERGE_REQUEST_IID
```

Or use the artifact and API directly:

```bash
# In a CI job with GITLAB_TOKEN
BODY=$(jq -r '.summary_body' artifacts/gitlab-comments.json)
# POST to /projects/:id/merge_requests/:mr_iid/notes with body
```

---

## Example: This Repo

See [.gitlab-ci.yml](../.gitlab-ci.yml) for the `policy-review` job used in this repository.

---

## What We Have

- Policy review job in GitLab CI
- Artifact retention (review-result.json, report.md, gitlab-comments.json)
- Policy-based pass/fail (allow_failure: false)
- Post MR comment (`comments --post` with `GITLAB_TOKEN`)
- Fetch pipeline from MR (`review-all --project/--mr`)

## What We Don't Have (Yet)

- Line-level diff comments
- MR check status API
