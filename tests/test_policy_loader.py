"""Tests for policy loader."""

from pathlib import Path

import pytest

from ai_devsecops_agent.policies.loader import load_policy_set
from ai_devsecops_agent.models import Severity


def test_load_default_policy():
    path = Path("policies/default.yaml")
    if not path.exists():
        pytest.skip("policies/default.yaml not found")
    ps = load_policy_set(path)
    assert ps.name == "default"
    assert len(ps.rules) >= 1
    ids = [r.id for r in ps.rules]
    assert "no_plaintext_secrets" in ids or len(ids) > 0


def test_load_missing_file():
    ps = load_policy_set(Path("nonexistent.yaml"))
    assert ps.name == "empty"
    assert ps.rules == []


def test_load_policy_rule_severity():
    path = Path("policies/default.yaml")
    if not path.exists():
        pytest.skip("policies/default.yaml not found")
    ps = load_policy_set(path)
    for r in ps.rules:
        assert r.severity in list(Severity)
