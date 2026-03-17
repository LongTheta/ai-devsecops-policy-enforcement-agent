"""Tests for GitLab/GitHub integrations."""

import os

from ai_devsecops_agent.integrations.github import post_pr_comment
from ai_devsecops_agent.integrations.gitlab import post_mr_comment


def test_post_pr_comment_no_token():
    """post_pr_comment returns False when GITHUB_TOKEN is not set."""
    # Ensure token is unset for this test
    token = os.environ.pop("GITHUB_TOKEN", None)
    try:
        result = post_pr_comment("owner", "repo", 1, "test")
        assert result is False
    finally:
        if token is not None:
            os.environ["GITHUB_TOKEN"] = token


def test_post_mr_comment_no_token():
    """post_mr_comment returns False when GITLAB_TOKEN is not set."""
    token = os.environ.pop("GITLAB_TOKEN", None)
    try:
        result = post_mr_comment("group/repo", 1, "test")
        assert result is False
    finally:
        if token is not None:
            os.environ["GITLAB_TOKEN"] = token
