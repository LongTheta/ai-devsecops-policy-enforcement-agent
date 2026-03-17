#!/usr/bin/env bash
# 2–5 Minute Demo: AI DevSecOps Policy Enforcement Agent
# Use for: interviews, presentations, internal demos

set -e

# Use python -m if ai-devsecops-agent not in PATH
CLI="ai-devsecops-agent"
if ! command -v ai-devsecops-agent &>/dev/null; then
  CLI="python -m ai_devsecops_agent.cli"
fi

echo "=== AI DevSecOps Policy Enforcement Agent - Demo ==="
echo ""

# Step 1 - Show the problem
echo "Step 1: Insecure pipeline (missing SBOM, unpinned image, plaintext secret)..."
echo ""
cat examples/insecure-gitlab-ci.yml
echo ""
echo "👉 This looks normal, but it's missing key DevSecOps controls"
echo ""
read -p "Press Enter to continue..."

# Step 2 - Run review (with artifacts for auto-fix)
echo ""
echo "Step 2: Running policy review..."
echo ""
mkdir -p artifacts
$CLI review \
  --platform gitlab \
  --pipeline examples/insecure-gitlab-ci.yml \
  --gitops examples/insecure-argo-application.yaml \
  --policy policies/fedramp-moderate.yaml \
  --include-comments \
  --include-remediations \
  --output markdown \
  --out report.md \
  --artifact-dir artifacts || true

echo "Report written to report.md | Artifacts in artifacts/"
echo ""
read -p "Press Enter to continue..."

# Step 3 - Show output
echo ""
echo "Step 3: Review output (findings, verdict, severity)..."
echo ""
head -60 report.md
echo ""
echo "👉 Verdict, findings by severity, compliance mappings"
echo ""
read -p "Press Enter to continue..."

# Step 4 - Auto-fix suggest
echo ""
echo "Step 4: Auto-fix (suggest mode)..."
echo ""
if [ -f artifacts/review-result.json ]; then
  $CLI auto-fix --input artifacts/review-result.json --mode suggest 2>/dev/null | head -50 || true
  echo ""
  echo "👉 Deterministic, reviewable patches — suggest | patch | apply"
else
  $CLI remediate --pipeline examples/insecure-gitlab-ci.yml --gitops examples/insecure-argo-application.yaml --include-patch 2>/dev/null | head -50 || true
  echo ""
  echo "👉 Remediation with patch-style diffs"
fi
echo ""
read -p "Press Enter to continue..."

# Step 5 - PR comments
echo ""
echo "Step 5: PR/MR review comments..."
echo ""
$CLI comments \
  --pipeline examples/insecure-gitlab-ci.yml \
  --gitops examples/insecure-argo-application.yaml \
  --policy policies/fedramp-moderate.yaml \
  --type summary \
  --format github 2>/dev/null || true
echo ""
echo "👉 Plugs into PR workflows (GitHub, GitLab)"
echo ""
echo "=== Demo complete ==="
