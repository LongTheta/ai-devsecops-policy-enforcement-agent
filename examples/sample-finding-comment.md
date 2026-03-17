# Example: Individual Finding Comment

This is the format produced by `render_finding_comment()` for use in PR/MR reviews.

---

### Missing SBOM Generation Step

**Severity:** High
**Category:** Supply Chain

**Why this matters:**
This pipeline does not generate an SBOM, reducing artifact traceability and weakening supply chain visibility.

**Suggested fix:**
Add a build step that generates and stores an SPDX or CycloneDX SBOM artifact.

**Example:**
```yaml
- name: Generate SBOM
  run: syft . -o cyclonedx-json > sbom.json
```

**Impacted files:** .github/workflows/ci.yml
