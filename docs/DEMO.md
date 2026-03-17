# 2–5 Minute Demo

Use this for **interviews**, **presentations**, or **internal demos**.

**What this demo shows (all implemented):** policy review, verdict, artifacts, auto-fix suggest, and comment generation. See [README.md](README.md) for full "What We Have" / "What We Don't Have".

---

## Quick Run

```bash
# Bash (Linux/macOS)
./scripts/demo.sh

# PowerShell (Windows)
./scripts/demo.ps1
```

---

## 2-Minute Flow (Manual)

### Step 1 — Run review

```bash
pip install -e .
mkdir -p artifacts

python -m ai_devsecops_agent.cli review \
  --platform gitlab \
  --pipeline examples/insecure-gitlab-ci.yml \
  --gitops examples/insecure-argo-application.yaml \
  --policy policies/fedramp-moderate.yaml \
  --output markdown \
  --out report.md \
  --artifact-dir artifacts
```

### Step 2 — Show output

- **Findings** — plaintext secrets, unpinned images, missing SBOM
- **Verdict** — FAIL / PASS WITH WARNINGS / PASS
- **Severity breakdown** — critical, high, medium, low
- **Artifacts** — `review-result.json`, `comments.json`, `remediations.json`

```bash
head -60 report.md
```

### Step 3 — Auto-fix (suggest)

```bash
python -m ai_devsecops_agent.cli auto-fix \
  --input artifacts/review-result.json \
  --mode suggest
```

### Step 4 — Show diff

Example:

```diff
- image: alpine:latest
+ image: alpine@sha256:<resolve-digest>

- uses: actions/checkout@v4
+ uses: actions/checkout@<full-40-char-sha>
```

---

## 5-Minute Flow (Full)

1. **Show the problem** — `cat examples/insecure-gitlab-ci.yml`
2. **Run review** — as above
3. **Show output** — `cat report.md`
4. **Auto-fix suggest** — as above
5. **PR comments** — `python -m ai_devsecops_agent.cli comments --pipeline examples/insecure-gitlab-ci.yml --gitops examples/insecure-argo-application.yaml --type summary --format github`

---

## Framing

- **Don't say:** "AI tool"
- **Say:** "Policy enforcement engine with deterministic analysis and reviewable auto-fix"

---

## Close

> "This system bridges the gap between security policy and developer workflows — it enforces decisions and enables remediation across CI/CD and GitOps."
