# 5-Minute Demo Script for AI DevSecOps Policy Enforcement Agent
# Use for: interviews, presentations, internal demos (Windows)

Write-Host "=== AI DevSecOps Policy Enforcement Agent - Demo ===" -ForegroundColor Cyan
Write-Host ""

# Step 1 - Show the problem
Write-Host "Step 1: Showing an insecure pipeline..." -ForegroundColor Yellow
Get-Content examples/insecure-gitlab-ci.yml
Write-Host ""
Write-Host "This looks normal, but it's missing key DevSecOps controls" -ForegroundColor Green
Read-Host "Press Enter to continue"

# Step 2 - Run the agent
Write-Host ""
Write-Host "Step 2: Running the agent..." -ForegroundColor Yellow
ai-devsecops-agent review `
  --platform gitlab `
  --pipeline examples/insecure-gitlab-ci.yml `
  --gitops examples/insecure-argo-application.yaml `
  --policy policies/fedramp-moderate.yaml `
  --output markdown `
  --out report.md
Write-Host "Report written to report.md"
Read-Host "Press Enter to continue"

# Step 3 - Show output
Write-Host ""
Write-Host "Step 3: Review output..." -ForegroundColor Yellow
Get-Content report.md
Write-Host ""
Write-Host "Walk through: missing SBOM, unpinned image, plaintext secret, policy verdict" -ForegroundColor Green
Read-Host "Press Enter to continue"

# Step 4 - Show remediation
Write-Host ""
Write-Host "Step 4: Remediation suggestions with patches..." -ForegroundColor Yellow
ai-devsecops-agent remediate `
  --pipeline examples/insecure-gitlab-ci.yml `
  --gitops examples/insecure-argo-application.yaml `
  --include-patch `
  --out remediations.md
Get-Content remediations.md | Select-Object -First 80
Write-Host ""
Write-Host "It doesn't just detect issues - it tells developers exactly how to fix them" -ForegroundColor Green
Read-Host "Press Enter to continue"

# Step 5 - Show PR comments
Write-Host ""
Write-Host "Step 5: PR/MR review comments..." -ForegroundColor Yellow
ai-devsecops-agent comments `
  --pipeline examples/insecure-gitlab-ci.yml `
  --gitops examples/insecure-argo-application.yaml `
  --policy policies/fedramp-moderate.yaml `
  --type summary `
  --format github
Write-Host ""
Write-Host "This can plug directly into PR workflows" -ForegroundColor Green
Write-Host ""
Write-Host "=== Demo complete ===" -ForegroundColor Cyan
