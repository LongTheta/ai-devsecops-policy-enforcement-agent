"""Tests for review-all command with remote fetch."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from ai_devsecops_agent.cli import main


def test_review_all_with_local_pipeline(tmp_path):
    """review-all with --pipeline uses local file."""
    pipeline = tmp_path / "ci.yml"
    pipeline.write_text("""
name: CI
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo build
""")
    out_path = tmp_path / "out.md"
    old_argv = sys.argv
    try:
        sys.argv = ["cli", "review-all", "--pipeline", str(pipeline), "--out", str(out_path)]
        main()
    except SystemExit:
        pass
    finally:
        sys.argv = old_argv
    assert out_path.exists()
    assert "CI" in out_path.read_text() or "build" in out_path.read_text()


def test_review_all_requires_input():
    """review-all without pipeline/gitops/manifests or remote args fails."""
    with pytest.raises(SystemExit):
        main(["review-all"])


@patch("ai_devsecops_agent.cli.fetch_pipeline_from_pr")
def test_review_all_fetches_from_pr(mock_fetch, tmp_path):
    """review-all with --owner/--repo/--pr fetches pipeline and runs review."""
    mock_fetch.return_value = """
name: CI
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo build
"""
    out_path = tmp_path / "out.md"
    old_argv = sys.argv
    try:
        sys.argv = [
            "cli", "review-all",
            "--owner", "org", "--repo", "repo", "--pr", "1",
            "--out", str(out_path),
        ]
        main()
    except SystemExit:
        pass
    finally:
        sys.argv = old_argv
    mock_fetch.assert_called_once_with("org", "repo", 1, ".github/workflows/ci.yml")
    assert out_path.exists()
    assert "build" in out_path.read_text() or "CI" in out_path.read_text()
