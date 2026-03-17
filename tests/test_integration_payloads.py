"""Tests for GitHub/GitLab payload formatting."""

from ai_devsecops_agent.integrations.github import format_comment_payload, format_review_payload
from ai_devsecops_agent.integrations.gitlab import format_comment_payload as gitlab_format_comment
from ai_devsecops_agent.integrations.gitlab import format_review_payload as gitlab_format_review


def test_gitlab_format_comment_payload_structure():
    """GitLab MR note payload has correct structure for Notes API."""
    body = "## DevSecOps Policy Review\n\n**Verdict:** FAIL"
    payload = gitlab_format_comment(body)
    assert "body" in payload
    assert payload["body"] == body
    assert len(payload) == 1  # Only body for API


def test_gitlab_format_review_payload_with_markdown():
    """GitLab format_review_payload accepts markdown and optional context."""
    summary = "## Review\n\n- **Critical:** 1\n- **High:** 2"
    payload = gitlab_format_review(summary)
    assert payload["body"] == summary


def test_github_format_comment_payload_structure():
    """GitHub PR comment payload has correct structure for Issues API."""
    body = "## DevSecOps Policy Review\n\n**Verdict:** FAIL"
    payload = format_comment_payload(body)
    assert "body" in payload
    assert payload["body"] == body
    assert len(payload) == 1  # Only body for API


def test_github_format_comment_payload():
    body = "## Review\n\n**Verdict:** FAIL"
    payload = format_comment_payload(body)
    assert payload == {"body": body}


def test_github_format_review_payload():
    summary = "Policy review failed"
    payload = format_review_payload(summary)
    assert payload["body"] == summary


def test_github_format_review_payload_with_context():
    summary = "Review"
    ctx = {"platform": "github", "repo": "owner/repo"}
    payload = format_review_payload(summary, ctx)
    assert payload["body"] == summary
    assert payload["_meta"]["event_context"] == ctx


def test_gitlab_format_comment_payload():
    body = "## Review\n\n**Verdict:** FAIL"
    payload = gitlab_format_comment(body)
    assert payload == {"body": body}


def test_gitlab_format_review_payload():
    summary = "Policy review failed"
    payload = gitlab_format_review(summary)
    assert payload["body"] == summary
