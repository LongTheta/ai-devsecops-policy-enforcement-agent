# 2-5 Minute Demo: AI DevSecOps Policy Enforcement Agent
# Use for: interviews, presentations, internal demos (Windows)

# Prefer ai-devsecops-agent if in PATH, else python -m
$CLI = if (Get-Command ai-devsecops-agent -ErrorAction SilentlyContinue) { "ai-devsecops-agent" } else { "python -m ai_devsecops_agent.cli" }

Write-Host "=== AI DevSecOps Policy Enforcement Agent - Demo ===" -ForegroundColor Cyan
Write-Host ""

# Step 1 - Show the problem
Write-Host "Step 1: Insecure pipeline (missing SBOM, unpinned image, plaintext secret)..." -ForegroundColor Yellow
Get-Content examples/insecure-gitlab-ci.yml
Write-Host ""
Write-Host "This looks normal, but it's missing key DevSecOps controls" -ForegroundColor Green
Read-Host "Press Enter to continue"

# Step 2 - Run review
Write-Host ""
Write-Host "Step 2: Running policy review..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path artifacts | Out-Null
Invoke-Expression "$CLI review --platform gitlab --pipeline examples/insecure-gitlab-ci.yml --gitops examples/insecure-argo-application.yaml --policy policies/fedramp-moderate.yaml --output markdown --out report.md --artifact-dir artifacts" 2>$null
Write-Host "Report written to report.md | Artifacts in artifacts/"
Read-Host "Press Enter to continue"

# Step 3 - Show output
Write-Host ""
Write-Host "Step 3: Review output (findings, verdict, severity)..." -ForegroundColor Yellow
Get-Content report.md | Select-Object -First 60
Write-Host ""
Write-Host "Verdict, findings by severity, compliance mappings" -ForegroundColor Green
Read-Host "Press Enter to continue"

# Step 4 - Auto-fix suggest
Write-Host ""
Write-Host "Step 4: Auto-fix (suggest mode)..." -ForegroundColor Yellow
if (Test-Path artifacts/review-result.json) {
  & $CLI auto-fix --input artifacts/review-result.json --mode suggest 2>$null | Select-Object -First 50
  Write-Host ""
  Write-Host "Deterministic, reviewable patches - suggest | patch | apply" -ForegroundColor Green
} else {
  & $CLI remediate --pipeline examples/insecure-gitlab-ci.yml --gitops examples/insecure-argo-application.yaml --include-patch 2>$null | Select-Object -First 50
  Write-Host ""
  Write-Host "Remediation with patch-style diffs" -ForegroundColor Green
}
Read-Host "Press Enter to continue"

# Step 5 - PR comments
Write-Host ""
Write-Host "Step 5: PR/MR review comments..." -ForegroundColor Yellow
Invoke-Expression "$CLI comments --pipeline examples/insecure-gitlab-ci.yml --gitops examples/insecure-argo-application.yaml --policy policies/fedramp-moderate.yaml --type summary --format github" 2>$null
Write-Host ""
Write-Host "Plugs into PR workflows (GitHub, GitLab)" -ForegroundColor Green
Write-Host ""
Write-Host "=== Demo complete ===" -ForegroundColor Cyan
