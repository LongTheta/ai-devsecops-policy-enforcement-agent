## Unpinned container image or action
Pin container images by digest
Unpinned images (e.g. :latest) can change without notice, breaking builds or introducing vulnerabilities.
Steps: ["Resolve the image to a specific digest: docker pull image:tag && docker inspect --format='{{.RepoDigests}}'.", 'Replace image:tag with image@sha256:... in the pipeline.']
---
## Action pinned by tag instead of full SHA
Pin GitHub Actions by full commit SHA
Tag-based pins (@v1, @v2) can be moved; SHA pins are immutable.
Steps: ["Look up the action's latest commit SHA (e.g. from GitHub).", 'Replace uses: owner/repo@v1 with uses: owner/repo@<full-40-char-sha>.']
---