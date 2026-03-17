"""GitHub API integration for fetching repo content and PR context."""

import os
from typing import Any

import requests

GITHUB_API = "https://api.github.com"


def format_comment_payload(body: str) -> dict[str, Any]:
    """
    Format a review comment for GitHub Issues/PR API.
    POST /repos/{owner}/{repo}/issues/{issue_number}/comments
    Body: {"body": "markdown content"}
    """
    return {"body": body}


def format_review_payload(summary: str, event_context: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Format payload for GitHub PR review comment.
    Ready for POST when GITHUB_TOKEN, owner, repo, pr_number are available.
    """
    payload: dict[str, Any] = {"body": summary}
    if event_context:
        payload["_meta"] = {"event_context": event_context}
    return payload


def _get_token() -> str | None:
    """Get GitHub token from environment."""
    return os.environ.get("GITHUB_TOKEN")


def fetch_file_content(
    owner: str,
    repo: str,
    path: str,
    ref: str = "HEAD",
) -> str | None:
    """
    Fetch raw file content from a GitHub repository.
    Requires GITHUB_TOKEN for private repos; works without token for public repos.
    """
    url = f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}"
    headers: dict[str, str] = {"Accept": "application/vnd.github.raw"}
    if token := _get_token():
        headers["Authorization"] = f"Bearer {token}"

    try:
        resp = requests.get(url, headers=headers, params={"ref": ref}, timeout=30)
        resp.raise_for_status()
        return resp.text
    except Exception:
        return None


def get_pull_request_context(owner: str, repo: str, pr_number: int) -> dict | None:
    """
    Fetch PR context: diff, changed files, base/head refs.
    Returns None if token missing or API call fails.
    """
    token = _get_token()
    if not token:
        return None

    url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"}

    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def post_pr_comment(owner: str, repo: str, pr_number: int, body: str) -> bool:
    """
    Post a comment on a pull request.
    Returns True on success, False on failure.
    """
    token = _get_token()
    if not token:
        return False

    url = f"{GITHUB_API}/repos/{owner}/{repo}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(url, headers=headers, json={"body": body}, timeout=30)
        resp.raise_for_status()
        return True
    except Exception:
        return False


def fetch_pipeline_from_pr(
    owner: str,
    repo: str,
    pr_number: int,
    path: str = ".github/workflows/ci.yml",
) -> str | None:
    """
    Fetch pipeline file content from the PR's head branch.
    Returns None if PR context or file fetch fails.
    """
    ctx = get_pull_request_context(owner, repo, pr_number)
    if not ctx:
        return None
    head_ref = ctx.get("head", {}).get("ref")
    if not head_ref:
        return None
    return fetch_file_content(owner, repo, path, ref=head_ref)
