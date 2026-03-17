#!/usr/bin/env bash
# 5-Minute Demo Script for AI DevSecOps Policy Enforcement Agent
# Use for: interviews, presentations, internal demos

set -e

echo "=== AI DevSecOps Policy Enforcement Agent - Demo ==="
echo ""

# Step 1 - Show the problem
echo "Step 1: Showing an insecure pipeline..."
echo ""
cat examples/insecure-gitlab-ci.yml
echo ""
echo "👉 This looks normal, but it's missing key DevSecOps controls"
echo ""
read -p "Press Enter to continue..."

# Step 2 - Run the agent
echo ""
echo "Step 2: Running the agent..."
echo ""
ai-devsecops-agent review \
  --platform gitlab \
  --pipeline examples/insecure-gitlab-ci.yml \
  --gitops examples/insecure-argo-application.yaml \
  --policy policies/fedramp-moderate.yaml \
  --output markdown \
  --out report.md

echo "Report written to report.md"
echo ""
read -p "Press Enter to continue..."

# Step 3 - Show output
echo ""
echo "Step 3: Review output..."
echo ""
cat report.md
echo ""
echo "👉 Walk through: missing SBOM, unpinned image, plaintext secret, policy verdict"
echo ""
read -p "Press Enter to continue..."

# Step 4 - Show remediation
echo ""
echo "Step 4: Remediation suggestions with patches..."
echo ""
ai-devsecops-agent remediate \
  --pipeline examples/insecure-gitlab-ci.yml \
  --gitops examples/insecure-argo-application.yaml \
  --include-patch \
  --out remediations.md
cat remediations.md | head -80
echo ""
echo "👉 It doesn't just detect issues — it tells developers exactly how to fix them"
echo ""
read -p "Press Enter to continue..."

# Step 5 - Show PR comments
echo ""
echo "Step 5: PR/MR review comments..."
echo ""
ai-devsecops-agent comments \
  --pipeline examples/insecure-gitlab-ci.yml \
  --gitops examples/insecure-argo-application.yaml \
  --policy policies/fedramp-moderate.yaml \
  --type summary \
  --format github
echo ""
echo "👉 This can plug directly into PR workflows"
echo ""
echo "=== Demo complete ==="
