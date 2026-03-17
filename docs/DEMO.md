# 5-Minute Demo Script

Use this for **interviews**, **presentations**, or **internal demos**.

---

## Setup

```bash
pip install -e ".[dev]"
# or: uv sync --all-extras
```

If using `uv` without global install, prefix commands with `uv run`:
```bash
uv run ai-devsecops-agent review ...
```

---

## Step 1 — Show the Problem

Open an insecure pipeline:

```bash
cat examples/insecure-gitlab-ci.yml
```

**Say:** *"This looks normal, but it's missing key DevSecOps controls"*

---

## Step 2 — Run the Agent

```bash
ai-devsecops-agent review \
  --platform gitlab \
  --pipeline examples/insecure-gitlab-ci.yml \
  --gitops examples/insecure-argo-application.yaml \
  --policy policies/fedramp-moderate.yaml \
  --output markdown \
  --out report.md
```

---

## Step 3 — Show Output

```bash
cat report.md
```

**Walk through:**
- 🔴 **Findings** — missing SBOM, unpinned image, plaintext secret
- 🟡 **Policy verdict** — FAIL or WARN
- 📋 **Compliance mappings** — control families (AC, AU, CM, etc.)

---

## Step 4 — Show Remediation

```bash
ai-devsecops-agent remediate \
  --pipeline examples/insecure-gitlab-ci.yml \
  --gitops examples/insecure-argo-application.yaml \
  --include-patch \
  --out remediations.md
cat remediations.md
```

**Highlight:**
```diff
- image: node:latest
+ image: node@sha256:...
```

**Say:** *"It doesn't just detect issues — it tells developers exactly how to fix them"*

---

## Step 5 — Show PR Comments

```bash
ai-devsecops-agent comments \
  --pipeline examples/insecure-gitlab-ci.yml \
  --gitops examples/insecure-argo-application.yaml \
  --policy policies/fedramp-moderate.yaml \
  --type grouped \
  --format github
```

Or view pre-generated examples:
```bash
cat examples/github-review-comments.md
cat examples/gitlab-review-comments.md
```

**Say:** *"This can plug directly into PR workflows"*

---

## Step 6 — Close Strong

**Say this:**

> "This system bridges the gap between security policy and developer workflows — it doesn't only detect issues, it enforces decisions and enables remediation across CI/CD and GitOps."

---

## Framing Tip

👉 **Don't say:** "AI tool"  
👉 **Say:** *"Policy enforcement engine with AI-assisted remediation"*

That framing is **way stronger**.
