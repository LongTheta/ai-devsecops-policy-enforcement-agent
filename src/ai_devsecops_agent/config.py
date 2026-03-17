"""Configuration and environment for the policy enforcement agent."""

import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

load_dotenv()

Platform = Literal["gitlab", "github", "local"]
OutputFormat = Literal["markdown", "json", "console"]


def get_policy_path() -> Path:
    """Resolve policy path from env or default."""
    raw = os.environ.get("POLICY_PATH", "policies/default.yaml")
    return Path(raw)


def get_output_format() -> OutputFormat:
    """Output format from env or default."""
    raw = os.environ.get("OUTPUT_FORMAT", "markdown").lower()
    if raw in ("markdown", "json", "console"):
        return raw
    return "markdown"


def get_output_path() -> Path:
    """Output path from env or default."""
    raw = os.environ.get("OUTPUT_PATH", "report.md")
    return Path(raw)


def get_compliance_mode() -> str:
    """Compliance mode from env or default."""
    return os.environ.get("COMPLIANCE_MODE", "default")


def get_gitlab_url() -> str | None:
    return os.environ.get("GITLAB_URL")


def get_gitlab_token() -> str | None:
    return os.environ.get("GITLAB_TOKEN")


def get_github_token() -> str | None:
    return os.environ.get("GITHUB_TOKEN")
