"""YAML-aware patching utilities."""

from __future__ import annotations

import difflib
from pathlib import Path
from typing import Any

import yaml

from ai_devsecops_agent.autofix.models import FilePatch, PatchOperation


def load_yaml(path: str | Path) -> tuple[dict[str, Any] | None, str | None]:
    """Load YAML file. Returns (data, raw_content) or (None, None) on error."""
    p = Path(path)
    if not p.exists():
        return None, None
    try:
        raw = p.read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
        return data if isinstance(data, dict) else {}, raw
    except Exception:
        return None, None


def save_yaml(path: str | Path, data: dict[str, Any], raw_content: str | None = None) -> bool:
    """Save data as YAML. If raw_content provided, preserve formatting where possible."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        if raw_content and _is_simple_update(data):
            # For simple cases, write with default formatting
            p.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False), encoding="utf-8")
        else:
            p.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False), encoding="utf-8")
        return True
    except Exception:
        return False


def _is_simple_update(data: Any) -> bool:
    """Heuristic: data is simple enough for direct dump."""
    if not isinstance(data, dict):
        return True
    if len(data) > 20:
        return False
    for v in data.values():
        if isinstance(v, (dict, list)) and (isinstance(v, dict) and len(v) > 5 or isinstance(v, list) and len(v) > 5):
            return False
    return True


def apply_patch_to_dict(data: dict[str, Any], patch: FilePatch) -> dict[str, Any]:
    """
    Apply a FilePatch to a dict (in-memory). Returns modified copy.
    Path format: spec.template.spec.containers[0].resources
    """
    import copy
    result = copy.deepcopy(data)
    parts = _parse_path(patch.path)
    if not parts:
        return result

    # Navigate to parent of target
    current: Any = result
    for i, part in enumerate(parts[:-1]):
        key = part["key"]
        idx = part.get("index")
        if key and isinstance(current, dict):
            if key not in current:
                return result
            current = current[key]
        if idx is not None:
            if not isinstance(current, list) or idx >= len(current):
                return result
            current = current[idx]

    last = parts[-1]
    key = last["key"]
    idx = last.get("index")

    if idx is not None:
        if isinstance(current, list) and idx < len(current):
            if patch.operation == PatchOperation.REPLACE:
                current[idx] = patch.new_value
            elif patch.operation == PatchOperation.INSERT:
                current.insert(idx, patch.new_value)
    else:
        if isinstance(current, dict):
            if patch.operation in (PatchOperation.REPLACE, PatchOperation.INSERT):
                current[key] = patch.new_value
            elif patch.operation == PatchOperation.DELETE:
                current.pop(key, None)

    return result


def _parse_path(path: str) -> list[dict[str, Any]]:
    """Parse path like spec.template.spec.containers[0].resources into segments."""
    import re
    segments: list[dict[str, Any]] = []
    for part in path.split("."):
        if not part:
            continue
        match = re.match(r"^(\w+)\[(\d+)\]$", part)
        if match:
            segments.append({"key": match.group(1), "index": int(match.group(2))})
        else:
            segments.append({"key": part, "index": None})
    return segments


def generate_diff(original: str, patched: str, from_file: str = "a", to_file: str = "b") -> str:
    """Generate unified diff between two strings."""
    a_lines = original.splitlines(keepends=True)
    b_lines = patched.splitlines(keepends=True)
    diff = difflib.unified_diff(a_lines, b_lines, fromfile=from_file, tofile=to_file, lineterm="")
    return "".join(diff)


def create_backup(path: str | Path) -> str | None:
    """Create .bak backup of file. Returns backup path or None."""
    p = Path(path)
    if not p.exists():
        return None
    backup = p.with_suffix(p.suffix + ".bak")
    try:
        backup.write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
        return str(backup)
    except Exception:
        return None
