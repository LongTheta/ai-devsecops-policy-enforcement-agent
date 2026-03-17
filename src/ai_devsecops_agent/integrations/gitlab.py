"""GitLab API integration for fetching repo content and MR context."""

import os
from typing import Any

import requests


def _get_base_url() -> str:
    """Get GitLab base URL from environment."""
    return os.environ.get("GITLAB_URL", "https://gitlab.com").rstrip("/")


def _get_token() -> str | None:
    """Get GitLab token from environment."""
    return os.environ.get("GITLAB_TOKEN")


def _project_id_to_path(project_id: str) -> str:
    """Convert project ID (numeric or path) to URL-encoded path."""
    return requests.utils.quote(project_id, safe="")


def fetch_file_content(
    project_id: str,
    path: str,
    ref: str = "HEAD",
) -> str | None:
    """
    Fetch raw file content from a GitLab project.
    project_id can be numeric or path (e.g. "group/repo").
    Requires GITLAB_TOKEN for private repos; works without token for public repos.
    """
    base_url = _get_base_url()
    encoded = _project_id_to_path(project_id)
    file_path_encoded = requests.utils.quote(path, safe=".")
    url = f"{base_url}/api/v4/projects/{encoded}/repository/files/{file_path_encoded}/raw"
    headers: dict[str, str] = {}
    if token := _get_token():
        headers["PRIVATE-TOKEN"] = token

    try:
        resp = requests.get(url, headers=headers, params={"ref": ref}, timeout=30)
        resp.raise_for_status()
        return resp.text
    except Exception:
        return None


def get_merge_request_context(project_id: str, mr_iid: int) -> dict | None:
    """
    Fetch MR context: diff, changed files, source/target branches.
    Returns None if token missing or API call fails.
    """
    token = _get_token()
    if not token:
        return None

    base_url = _get_base_url()
    encoded = _project_id_to_path(project_id)
    url = f"{base_url}/api/v4/projects/{encoded}/merge_requests/{mr_iid}"
    headers = {"PRIVATE-TOKEN": token}

    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def post_mr_comment(project_id: str, mr_iid: int, body: str) -> bool:
    """
    Post a comment (note) on a merge request.
    Returns True on success, False on failure.
    """
    token = _get_token()
    if not token:
        return False

    base_url = _get_base_url()
    encoded = _project_id_to_path(project_id)
    url = f"{base_url}/api/v4/projects/{encoded}/merge_requests/{mr_iid}/notes"
    headers = {"PRIVATE-TOKEN": token, "Content-Type": "application/json"}

    try:
        resp = requests.post(url, headers=headers, json={"body": body}, timeout=30)
        resp.raise_for_status()
        return True
    except Exception:
        return False


def fetch_pipeline_from_mr(
    project_id: str,
    mr_iid: int,
    path: str = ".gitlab-ci.yml",
) -> str | None:
    """
    Fetch pipeline file content from the MR's source branch.
    Returns None if MR context or file fetch fails.
    """
    ctx = get_merge_request_context(project_id, mr_iid)
    if not ctx:
        return None
    source_branch = ctx.get("source_branch")
    if not source_branch:
        return None
    return fetch_file_content(project_id, path, ref=source_branch)
