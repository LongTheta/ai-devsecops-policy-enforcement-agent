"""CLI for running policy reviews."""

import os
from pathlib import Path

import click

from ai_devsecops_agent.integrations.github import post_pr_comment
from ai_devsecops_agent.integrations.gitlab import post_mr_comment
from ai_devsecops_agent.models import (
    Platform,
    ReviewContext,
    ReviewEventContext,
    ReviewRequest,
)
from ai_devsecops_agent.reporting import render_console, render_json, render_markdown, render_sarif
from ai_devsecops_agent.review_comments import (
    render_finding_comment,
    render_grouped_comments,
    render_summary_comment,
)
from ai_devsecops_agent.remediation.engine import generate_remediation, generate_remediation_bundle
from ai_devsecops_agent.workflows.artifacts import (
    workflow_integration_result,
    write_artifacts,
)
from ai_devsecops_agent.workflows.review_workflow import run_review
from ai_devsecops_agent.autofix import run_autofix
from ai_devsecops_agent.autofix.models import AutoFixRequest
from ai_devsecops_agent.integrations.github import fetch_pipeline_from_pr
from ai_devsecops_agent.integrations.gitlab import fetch_pipeline_from_mr


@click.group()
def main() -> None:
    """Policy enforcement engine with AI-assisted remediation – CI/CD, GitOps, and compliance-aware review."""
    pass


def _detect_event_context(platform: str, repo: str | None, branch: str | None, compliance: str) -> ReviewEventContext | None:
    """Build ReviewEventContext from env (GitHub Actions, GitLab CI) when available."""
    plat = platform
    rep = repo or os.environ.get("GITHUB_REPOSITORY") or os.environ.get("CI_PROJECT_PATH")
    br = branch or os.environ.get("GITHUB_REF_NAME") or os.environ.get("CI_COMMIT_REF_NAME")
    sha = os.environ.get("GITHUB_SHA") or os.environ.get("CI_COMMIT_SHA")
    pr_mr = None
    if os.environ.get("GITHUB_EVENT_NAME") == "pull_request":
        # GITHUB_REF = refs/pull/123/merge
        try:
            parts = (os.environ.get("GITHUB_REF") or "").split("/")
            if len(parts) >= 3 and parts[1] == "pull":
                pr_mr = int(parts[2])
        except (ValueError, IndexError):
            pass
    if pr_mr is None and os.environ.get("CI_MERGE_REQUEST_IID"):
        try:
            pr_mr = int(os.environ["CI_MERGE_REQUEST_IID"])
        except ValueError:
            pass
    actor = os.environ.get("GITHUB_ACTOR") or os.environ.get("GITLAB_USER_LOGIN")
    return ReviewEventContext(
        platform=plat,
        repo=rep,
        branch=br,
        commit_sha=sha,
        pr_or_mr_number=pr_mr,
        actor=actor,
        policy_mode=compliance,
    )


@main.command("review")
@click.option("--platform", "-p", type=click.Choice(["gitlab", "github", "local"]), default="local")
@click.option("--pipeline", "pipeline_path", type=click.Path(path_type=Path), help="Path to CI/CD pipeline file (.gitlab-ci.yml)")
@click.option("--gitops", "gitops_paths", multiple=True, type=click.Path(path_type=Path), help="Path(s) to Argo CD Application manifests")
@click.option("--manifests", "manifest_paths", multiple=True, type=click.Path(path_type=Path), help="Path(s) to supporting K8s manifests (Deployments, etc.)")
@click.option("--policy", "policy_path", type=click.Path(path_type=Path), default="policies/default.yaml")
@click.option("--output", "-o", "output_format", type=click.Choice(["markdown", "json", "console", "sarif"]), default="markdown")
@click.option("--out", "output_path", type=click.Path(path_type=Path), help="Write report to this file (default: stdout for console)")
@click.option("--repo", "repository_name", help="Repository name (for context)")
@click.option("--branch", help="Branch name (for context)")
@click.option("--compliance", "compliance_mode", default="default", help="Compliance mode (e.g. fedramp-moderate)")
@click.option("--artifact-dir", type=click.Path(path_type=Path), help="Write CI/CD artifacts (review-result.json, policy-summary.json, etc.)")
@click.option("--include-comments", is_flag=True, default=True, help="Include comments.json in artifact-dir (default: True)")
@click.option("--include-remediations", is_flag=True, default=True, help="Include remediations.json in artifact-dir (default: True)")
def review(
    platform: str,
    pipeline_path: Path | None,
    gitops_paths: tuple[Path, ...],
    manifest_paths: tuple[Path, ...],
    policy_path: Path,
    output_format: str,
    output_path: Path | None,
    repository_name: str | None,
    branch: str | None,
    compliance_mode: str,
    artifact_dir: Path | None,
    include_comments: bool,
    include_remediations: bool,
) -> None:
    """Run a full policy review on pipeline and/or GitOps manifests."""
    context = ReviewContext(
        platform=Platform(platform),
        repository_name=repository_name,
        branch=branch,
        compliance_mode=compliance_mode,
    )

    request = ReviewRequest(
        context=context,
        pipeline_path=str(pipeline_path) if pipeline_path else None,
        gitops_paths=[str(p) for p in gitops_paths],
        manifest_paths=[str(p) for p in manifest_paths],
        policy_path=str(policy_path),
    )

    result = run_review(request)

    if output_format == "markdown":
        report = render_markdown(result)
    elif output_format == "json":
        report = render_json(result)
    elif output_format == "sarif":
        report = render_sarif(result)
    else:
        report = render_console(result)

    if output_path:
        output_path.write_text(report, encoding="utf-8")
        click.echo(f"Report written to {output_path}")
    else:
        click.echo(report)

    if artifact_dir:
        report_md = render_markdown(result)
        artifacts = write_artifacts(
            result,
            Path(artifact_dir),
            include_comments=include_comments,
            include_remediations=include_remediations,
            platform=platform,
            report_markdown=report_md,
        )
        event_ctx = _detect_event_context(platform, repository_name, branch, compliance_mode)
        wf_result = workflow_integration_result(result, artifacts, event_ctx)
        status_path = Path(artifact_dir) / "workflow-status.json"
        import json
        status_path.write_text(json.dumps(wf_result.model_dump(mode="json"), indent=2), encoding="utf-8")
        click.echo(f"Artifacts written to {artifact_dir}/")
        for a in artifacts:
            click.echo(f"  - {a.name}")
        click.echo(f"  - workflow-status.json")

    if result.verdict.value == "fail":
        raise SystemExit(1)


@main.command("review-all")
@click.option("--platform", "-p", type=click.Choice(["gitlab", "github", "local"]), default="local")
@click.option("--owner", help="GitHub repo owner (for remote fetch)")
@click.option("--repo", "github_repo", help="GitHub repo name (for remote fetch)")
@click.option("--pr", "pr_number", type=int, help="GitHub PR number (for remote fetch)")
@click.option("--project", "gitlab_project", help="GitLab project ID or path (for remote fetch)")
@click.option("--mr", "mr_iid", type=int, help="GitLab MR IID (for remote fetch)")
@click.option("--pipeline-path", default=None, help="Path to fetch (default: .github/workflows/ci.yml or .gitlab-ci.yml)")
@click.option("--pipeline", "pipeline_path_local", type=click.Path(path_type=Path), help="Local pipeline file (alternative to remote fetch)")
@click.option("--gitops", "gitops_paths", multiple=True, type=click.Path(path_type=Path), help="Path(s) to GitOps manifests")
@click.option("--manifests", "manifest_paths", multiple=True, type=click.Path(path_type=Path), help="Path(s) to K8s manifests")
@click.option("--policy", "policy_path", type=click.Path(path_type=Path), default="policies/default.yaml")
@click.option("--output", "-o", "output_format", type=click.Choice(["markdown", "json", "console", "sarif"]), default="markdown")
@click.option("--out", "output_path", type=click.Path(path_type=Path), help="Write report to file")
@click.option("--artifact-dir", type=click.Path(path_type=Path), help="Write CI/CD artifacts")
def review_all(
    platform: str,
    owner: str | None,
    github_repo: str | None,
    pr_number: int | None,
    gitlab_project: str | None,
    mr_iid: int | None,
    pipeline_path: str | None,
    pipeline_path_local: Path | None,
    gitops_paths: tuple[Path, ...],
    manifest_paths: tuple[Path, ...],
    policy_path: Path,
    output_format: str,
    output_path: Path | None,
    artifact_dir: Path | None,
) -> None:
    """Run full review with optional remote fetch of pipeline from PR/MR."""
    import tempfile

    pipeline_to_use: str | None = None
    temp_file: Path | None = None

    if owner and github_repo and pr_number is not None:
        path = pipeline_path or ".github/workflows/ci.yml"
        content = fetch_pipeline_from_pr(owner, github_repo, pr_number, path)
        if content:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
                f.write(content)
                temp_file = Path(f.name)
            pipeline_to_use = str(temp_file)
            click.echo(f"Fetched pipeline from PR #{pr_number} ({path})", err=True)
        else:
            click.echo("Failed to fetch pipeline from PR. Check GITHUB_TOKEN and repo access.", err=True)
            raise SystemExit(1)
    elif gitlab_project and mr_iid is not None:
        path = pipeline_path or ".gitlab-ci.yml"
        content = fetch_pipeline_from_mr(gitlab_project, mr_iid, path)
        if content:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
                f.write(content)
                temp_file = Path(f.name)
            pipeline_to_use = str(temp_file)
            click.echo(f"Fetched pipeline from MR !{mr_iid} ({path})", err=True)
        else:
            click.echo("Failed to fetch pipeline from MR. Check GITLAB_TOKEN and project access.", err=True)
            raise SystemExit(1)
    elif pipeline_path_local:
        pipeline_to_use = str(pipeline_path_local)

    if not pipeline_to_use and not gitops_paths and not manifest_paths:
        click.echo("Provide --owner/--repo/--pr (GitHub), --project/--mr (GitLab), or --pipeline/--gitops/--manifests.", err=True)
        raise SystemExit(1)

    try:
        context = ReviewContext(platform=Platform(platform))
        request = ReviewRequest(
            context=context,
            pipeline_path=pipeline_to_use,
            gitops_paths=[str(p) for p in gitops_paths],
            manifest_paths=[str(p) for p in manifest_paths],
            policy_path=str(policy_path),
        )
        result = run_review(request)

        if output_format == "markdown":
            report = render_markdown(result)
        elif output_format == "json":
            report = render_json(result)
        elif output_format == "sarif":
            report = render_sarif(result)
        else:
            report = render_console(result)

        if output_path:
            output_path.write_text(report, encoding="utf-8")
            click.echo(f"Report written to {output_path}")
        else:
            click.echo(report)

        if artifact_dir:
            report_md = render_markdown(result)
            artifacts = write_artifacts(
                result,
                Path(artifact_dir),
                platform=platform,
                report_markdown=report_md,
            )
            event_ctx = _detect_event_context(platform, None, None, "default")
            wf_result = workflow_integration_result(result, artifacts, event_ctx)
            import json
            (Path(artifact_dir) / "workflow-status.json").write_text(
                json.dumps(wf_result.model_dump(mode="json"), indent=2), encoding="utf-8"
            )
            click.echo(f"Artifacts written to {artifact_dir}/")

        if result.verdict.value == "fail":
            raise SystemExit(1)
    finally:
        if temp_file and temp_file.exists():
            temp_file.unlink(missing_ok=True)


@main.command("comments")
@click.option("--platform", "-p", type=click.Choice(["gitlab", "github", "local"]), default="local")
@click.option("--pipeline", "pipeline_path", type=click.Path(path_type=Path), help="Path to CI/CD pipeline file")
@click.option("--gitops", "gitops_paths", multiple=True, type=click.Path(path_type=Path), help="Path(s) to Argo CD manifests")
@click.option("--manifests", "manifest_paths", multiple=True, type=click.Path(path_type=Path), help="Path(s) to K8s manifests")
@click.option("--policy", "policy_path", type=click.Path(path_type=Path), default="policies/default.yaml")
@click.option(
    "comment_type",
    "--type",
    "-t",
    type=click.Choice(["summary", "grouped", "individual"]),
    default="summary",
    help="Comment output type",
)
@click.option(
    "comment_format",
    "--format",
    "-f",
    type=click.Choice(["github", "gitlab", "generic"]),
    default="generic",
    help="Output format for PR/MR platform",
)
@click.option("--group-by", type=click.Choice(["severity", "category"]), default="severity", help="For grouped: group by severity or category")
@click.option("--out", "output_path", type=click.Path(path_type=Path), help="Write comments to file")
@click.option("--post", "post_comment", is_flag=True, help="Post comment to PR/MR (requires --owner/--repo/--pr for GitHub or --project/--mr for GitLab)")
@click.option("--owner", help="GitHub repo owner (for --post)")
@click.option("--repo", "github_repo", help="GitHub repo name (for --post)")
@click.option("--pr", "pr_number", type=int, help="GitHub PR number (for --post)")
@click.option("--project", "gitlab_project", help="GitLab project ID or path (for --post)")
@click.option("--mr", "mr_iid", type=int, help="GitLab MR IID (for --post)")
def comments(
    platform: str,
    pipeline_path: Path | None,
    gitops_paths: tuple[Path, ...],
    manifest_paths: tuple[Path, ...],
    policy_path: Path,
    comment_type: str,
    comment_format: str,
    group_by: str,
    output_path: Path | None,
    post_comment: bool,
    owner: str | None,
    github_repo: str | None,
    pr_number: int | None,
    gitlab_project: str | None,
    mr_iid: int | None,
) -> None:
    """Generate PR/MR review comments from findings."""
    context = ReviewContext(platform=Platform(platform))
    request = ReviewRequest(
        context=context,
        pipeline_path=str(pipeline_path) if pipeline_path else None,
        gitops_paths=[str(p) for p in gitops_paths],
        manifest_paths=[str(p) for p in manifest_paths],
        policy_path=str(policy_path),
    )
    result = run_review(request)

    if comment_type == "summary":
        output = render_summary_comment(result, format=comment_format)
    elif comment_type == "grouped":
        output = render_grouped_comments(result, group_by=group_by, format=comment_format)
    else:
        lines = []
        for f in result.findings:
            lines.append(render_finding_comment(f, format=comment_format))
            lines.append("---")
        output = "\n\n".join(lines)

    if output_path:
        output_path.write_text(output, encoding="utf-8")
        click.echo(f"Comments written to {output_path}")
    else:
        click.echo(output)

    if post_comment:
        if platform == "github" and owner and github_repo and pr_number is not None:
            if post_pr_comment(owner, github_repo, pr_number, output):
                click.echo("Comment posted to PR.")
            else:
                click.echo("Failed to post comment. Check GITHUB_TOKEN.", err=True)
                raise SystemExit(1)
        elif platform == "gitlab" and gitlab_project and mr_iid is not None:
            if post_mr_comment(gitlab_project, mr_iid, output):
                click.echo("Comment posted to MR.")
            else:
                click.echo("Failed to post comment. Check GITLAB_TOKEN.", err=True)
                raise SystemExit(1)
        else:
            click.echo(
                "For --post: use --platform github with --owner, --repo, --pr; "
                "or --platform gitlab with --project, --mr.",
                err=True,
            )
            raise SystemExit(1)


@main.command("remediate")
@click.option("--pipeline", "pipeline_path", type=click.Path(path_type=Path), help="Path to pipeline file")
@click.option("--gitops", "gitops_paths", multiple=True, type=click.Path(path_type=Path), help="Path(s) to GitOps manifests")
@click.option("--manifests", "manifest_paths", multiple=True, type=click.Path(path_type=Path), help="Path(s) to K8s manifests")
@click.option("--policy", "policy_path", type=click.Path(path_type=Path), default="policies/default.yaml")
@click.option("--include-patch", is_flag=True, help="Include patch-style diff suggestions")
@click.option("--format", "output_format", type=click.Choice(["markdown", "bundle"]), default="markdown", help="Output format: markdown (default) or bundle (JSON)")
@click.option("--out", "output_path", type=click.Path(path_type=Path), help="Write remediation suggestions to file")
def remediate(
    pipeline_path: Path | None,
    gitops_paths: tuple[Path, ...],
    manifest_paths: tuple[Path, ...],
    policy_path: Path,
    include_patch: bool,
    output_format: str,
    output_path: Path | None,
) -> None:
    """Output actionable remediation suggestions for all findings."""
    request = ReviewRequest(
        context=ReviewContext(),
        pipeline_path=str(pipeline_path) if pipeline_path else None,
        gitops_paths=[str(p) for p in gitops_paths],
        manifest_paths=[str(p) for p in manifest_paths],
        policy_path=str(policy_path),
    )
    result = run_review(request)

    if output_format == "bundle":
        bundle = generate_remediation_bundle(result)
        import json
        output = json.dumps(bundle.model_dump(mode="json"), indent=2)
        if output_path:
            output_path.write_text(output, encoding="utf-8")
            click.echo(f"Remediation bundle written to {output_path}")
        else:
            click.echo(output)
        return

    lines = ["# Remediation Suggestions", ""]
    for f in result.findings:
        rem = generate_remediation(f)
        lines.append(f"## {f.title} (`{f.id}`)")
        lines.append("")
        lines.append(f"**Severity:** {f.severity.value} | **Category:** {f.category}")
        if rem:
            lines.append(f"**Confidence:** {rem.confidence}")
            if rem.is_organization_specific:
                lines.append("*(Organization-specific fix)*")
        lines.append("")
        lines.append(f"**Issue:** {f.description}")
        lines.append("")
        if rem:
            lines.append("**Summary:**")
            lines.append(rem.summary)
            lines.append("")
            lines.append("**Why this matters:**")
            lines.append(rem.rationale)
            lines.append("")
            if rem.steps:
                lines.append("**Steps:**")
                for i, step in enumerate(rem.steps, 1):
                    lines.append(f"{i}. {step}")
                lines.append("")
            if rem.snippet:
                lines.append("**Example (for reference only):**")
                lines.append("```yaml")
                lines.append(rem.snippet.strip())
                lines.append("```")
                lines.append("")
            if include_patch and rem.patch:
                lines.append("**Patch-style suggestion:**")
                lines.append("```diff")
                lines.append(rem.patch.strip())
                lines.append("```")
                lines.append("")
            if rem.limitations:
                lines.append("**Limitations:**")
                for lim in rem.limitations:
                    lines.append(f"- {lim}")
                lines.append("")
            if rem.notes:
                lines.append(f"**Notes:** {rem.notes}")
                lines.append("")
        elif f.remediation_summary:
            lines.append(f"**Fix:** {f.remediation_summary}")
            lines.append("")
        if f.impacted_files:
            lines.append(f"**Impacted files:** {', '.join(f.impacted_files)}")
            lines.append("")
        lines.append("---")
        lines.append("")

    output = "\n".join(lines)
    if output_path:
        output_path.write_text(output, encoding="utf-8")
        click.echo(f"Remediation suggestions written to {output_path}")
    else:
        click.echo(output)


@main.command("auto-fix")
@click.option("--platform", "-p", type=click.Choice(["gitlab", "github", "local"]), default="local")
@click.option("--input", "input_path", type=click.Path(path_type=Path), help="Path to review-result.json (alternative to --pipeline/--gitops)")
@click.option("--pipeline", "pipeline_path", type=click.Path(path_type=Path), help="Path to pipeline file")
@click.option("--gitops", "gitops_paths", multiple=True, type=click.Path(path_type=Path), help="Path(s) to GitOps manifests")
@click.option("--manifests", "manifest_paths", multiple=True, type=click.Path(path_type=Path), help="Path(s) to K8s manifests")
@click.option("--policy", "policy_path", type=click.Path(path_type=Path), default="policies/default.yaml")
@click.option("--mode", "-m", type=click.Choice(["suggest", "patch", "apply"]), default="suggest", help="suggest (no changes) | patch (write to output-dir) | apply (modify originals)")
@click.option("--only-safe", is_flag=True, help="Only include fixes with can_auto_apply=True")
@click.option("--output-dir", "-o", type=click.Path(path_type=Path), help="Output directory for patch mode")
@click.option("--backup/--no-backup", default=True, help="Create backups before apply (default: True)")
@click.option("--dry-run", is_flag=True, help="Show what would be done without writing")
@click.option("--rules", multiple=True, help="Restrict to specific fix types (e.g. add_sbom_step)")
@click.option("--out", "output_path", type=click.Path(path_type=Path), help="Write auto-fix report to file")
@click.option("--format", "output_format", type=click.Choice(["markdown", "json"]), default="markdown", help="Output format")
def auto_fix(
    platform: str,
    input_path: Path | None,
    pipeline_path: Path | None,
    gitops_paths: tuple[Path, ...],
    manifest_paths: tuple[Path, ...],
    policy_path: Path,
    mode: str,
    only_safe: bool,
    output_dir: Path | None,
    backup: bool,
    dry_run: bool,
    rules: tuple[str, ...],
    output_path: Path | None,
    output_format: str,
) -> None:
    """Generate or apply safe, policy-aware config patches for findings."""
    if input_path and (pipeline_path or gitops_paths or manifest_paths):
        click.echo("Use either --input or --pipeline/--gitops/--manifests, not both.", err=True)
        raise SystemExit(1)
    if not input_path and not pipeline_path and not gitops_paths and not manifest_paths:
        click.echo("Provide --input or --pipeline/--gitops/--manifests.", err=True)
        raise SystemExit(1)
    if mode == "patch" and not output_dir:
        click.echo("--output-dir required for patch mode.", err=True)
        raise SystemExit(1)

    request = AutoFixRequest(
        mode=mode,
        input_path=str(input_path) if input_path else None,
        pipeline_path=str(pipeline_path) if pipeline_path else None,
        gitops_paths=[str(p) for p in gitops_paths],
        manifest_paths=[str(p) for p in manifest_paths],
        output_dir=str(output_dir) if output_dir else None,
        only_safe=only_safe,
        backup=backup,
        dry_run=dry_run,
        rules=list(rules) if rules else None,
    )

    findings: list | None = None
    file_contents: dict | None = None

    if not input_path:
        # Run review to get findings
        rev_request = ReviewRequest(
            context=ReviewContext(platform=Platform(platform)),
            pipeline_path=str(pipeline_path) if pipeline_path else None,
            gitops_paths=[str(p) for p in gitops_paths],
            manifest_paths=[str(p) for p in manifest_paths],
            policy_path=str(policy_path),
        )
        result = run_review(rev_request)
        findings = result.findings
        path_set = set()
        for f in findings:
            path_set.update(f.impacted_files)
        # Include explicit paths from request
        if pipeline_path:
            path_set.add(str(pipeline_path))
        path_set.update(str(p) for p in gitops_paths)
        path_set.update(str(p) for p in manifest_paths)
        file_contents = {}
        from ai_devsecops_agent.autofix.patcher import load_yaml
        for p in path_set:
            path = Path(p)
            if path.exists():
                content = path.read_text(encoding="utf-8")
                data, _ = load_yaml(path)
                file_contents[p] = (content, data)

    autofix_result = run_autofix(request, findings=findings, file_contents=file_contents)

    report = _render_autofix_report(autofix_result, output_format)
    if output_path:
        output_path.write_text(report, encoding="utf-8")
        click.echo(f"Auto-fix report written to {output_path}")
    else:
        click.echo(report)

    if autofix_result.errors:
        for err in autofix_result.errors:
            click.echo(f"Error: {err}", err=True)
        raise SystemExit(1)


def _render_autofix_report(result, fmt: str) -> str:
    """Render auto-fix result as markdown or JSON."""
    import json

    if fmt == "json":
        return json.dumps(result.model_dump(mode="json"), indent=2)

    lines = [
        "# Auto-Fix Report",
        "",
        f"**Mode:** {result.mode}",
        f"**Findings:** {result.finding_count}",
        f"**Candidates:** {result.candidate_count}",
        f"**Applied:** {result.applied_count}",
        "",
        result.summary,
        "",
    ]
    if result.backup_created:
        lines.append("## Backups Created")
        for bp in result.backup_created:
            lines.append(f"- {bp}")
        lines.append("")

    lines.append("## Fix Candidates")
    for c in result.candidates:
        lines.append(f"### {c.title} (`{c.fix_type}`)")
        lines.append("")
        lines.append(f"- **Finding:** {c.finding_id} | **File:** {c.file_path}")
        lines.append(f"- **Safety:** {c.safety_level.value} | **Confidence:** {c.confidence.value}")
        lines.append(f"- **Can auto-apply:** {c.can_auto_apply}")
        lines.append("")
        lines.append(c.description)
        lines.append("")
        if c.diff:
            lines.append("**Diff:**")
            lines.append("```diff")
            lines.append(c.diff[:2000] + ("..." if len(c.diff) > 2000 else ""))
            lines.append("```")
            lines.append("")
        if c.limitations:
            lines.append("**Limitations:**")
            for lim in c.limitations:
                lines.append(f"- {lim}")
            lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)
