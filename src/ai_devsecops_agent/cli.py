"""CLI for running policy reviews."""

from pathlib import Path

import click

from ai_devsecops_agent.integrations.github import post_pr_comment
from ai_devsecops_agent.integrations.gitlab import post_mr_comment
from ai_devsecops_agent.models import Platform, ReviewContext, ReviewRequest
from ai_devsecops_agent.reporting import render_console, render_json, render_markdown, render_sarif
from ai_devsecops_agent.review_comments import (
    render_finding_comment,
    render_grouped_comments,
    render_summary_comment,
)
from ai_devsecops_agent.remediation.engine import generate_remediation
from ai_devsecops_agent.workflows.review_workflow import run_review


@click.group()
def main() -> None:
    """AI DevSecOps Policy Enforcement Agent – CI/CD, GitOps, and compliance-aware review."""
    pass


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

    if result.verdict.value == "fail":
        raise SystemExit(1)


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
@click.option("--out", "output_path", type=click.Path(path_type=Path), help="Write remediation suggestions to file")
def remediate(
    pipeline_path: Path | None,
    gitops_paths: tuple[Path, ...],
    manifest_paths: tuple[Path, ...],
    policy_path: Path,
    include_patch: bool,
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
