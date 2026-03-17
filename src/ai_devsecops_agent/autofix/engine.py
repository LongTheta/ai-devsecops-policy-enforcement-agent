"""Auto-fix engine: map findings to fixers, generate patches, apply when safe."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ai_devsecops_agent.autofix.models import AutoFixRequest, AutoFixResult, FixCandidate
from ai_devsecops_agent.autofix.patcher import create_backup, load_yaml
from ai_devsecops_agent.autofix.registry import get_fixers_for_finding
from ai_devsecops_agent.models import Finding, ReviewResult


def run_autofix(
    request: AutoFixRequest,
    findings: list[Finding] | None = None,
    file_contents: dict[str, tuple[str, dict | None]] | None = None,
) -> AutoFixResult:
    """
    Run auto-fix: suggest, patch, or apply.
    - findings: from in-memory review (optional)
    - file_contents: optional dict of path -> (raw_content, parsed_data)
    - If input_path set, load findings from review-result.json
    """
    # Load findings
    if findings is None and request.input_path:
        findings, file_contents = _load_from_review_result(request.input_path)
    if findings is None:
        findings = []

    if file_contents is None:
        file_contents = {}

    # Build normalized path -> content map for lookup
    _norm_contents: dict[str, tuple[str, dict | None]] = {}
    for k, v in file_contents.items():
        _norm_contents[_normalize_path(k)] = v

    # Generate candidates
    candidates: list[FixCandidate] = []
    for finding in findings:
        for path in finding.impacted_files:
            norm = _normalize_path(path)
            if norm not in _norm_contents:
                content, data = _load_file(path)
                _norm_contents[norm] = (content, data)
            content, data = _norm_contents[norm]
            if not content:
                continue
            for fixer in get_fixers_for_finding(finding):
                cand = fixer(finding, path, content, data)
                if cand:
                    if request.only_safe and not cand.can_auto_apply:
                        continue
                    if request.rules and cand.fix_type not in request.rules:
                        continue
                    candidates.append(cand)
                    break  # First successful fixer per finding/file

    # Deduplicate by (finding_id, file_path, fix_type)
    seen: set[tuple[str, str, str]] = set()
    unique: list[FixCandidate] = []
    for c in candidates:
        key = (c.finding_id, c.file_path, c.fix_type)
        if key not in seen:
            seen.add(key)
            unique.append(c)

    candidates = unique

    # Apply based on mode
    applied: list[FixCandidate] = []
    skipped: list[FixCandidate] = []
    backup_paths: list[str] = []
    errors: list[str] = []
    output_dir = Path(request.output_dir) if request.output_dir else None

    for cand in candidates:
        if request.mode == "suggest":
            skipped.append(cand)
            continue

        if request.mode == "apply":
            if not cand.can_auto_apply:
                skipped.append(cand)
                continue
            if request.dry_run:
                applied.append(cand)
                continue
            if not cand.patched_content:
                errors.append(f"No patched content for {cand.fix_type} on {cand.file_path}")
                continue
            path = Path(cand.file_path)
            if not path.exists():
                errors.append(f"File not found: {cand.file_path}")
                continue
            if request.backup:
                bp = create_backup(path)
                if bp:
                    backup_paths.append(bp)
            try:
                path.write_text(cand.patched_content, encoding="utf-8")
                applied.append(cand)
            except Exception as e:
                errors.append(f"Failed to apply {cand.fix_type} to {cand.file_path}: {e}")

        elif request.mode == "patch":
            if not cand.patched_content:
                skipped.append(cand)
                continue
            if not output_dir:
                errors.append("--output-dir required for patch mode")
                continue
            out_path = output_dir / Path(cand.file_path).name
            out_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                out_path.write_text(cand.patched_content, encoding="utf-8")
                applied.append(cand)
            except Exception as e:
                errors.append(f"Failed to write patch to {out_path}: {e}")

    # Summary
    if request.mode == "suggest":
        summary = f"Suggested {len(candidates)} fix(es) for {len(findings)} finding(s). No files modified."
    elif request.mode == "patch":
        summary = f"Wrote {len(applied)} patched file(s) to {output_dir}. Original files unchanged."
    else:
        summary = f"Applied {len(applied)} fix(es) to original files. Backups: {len(backup_paths)}."

    return AutoFixResult(
        mode=request.mode,
        finding_count=len(findings),
        candidate_count=len(candidates),
        applied_count=len(applied),
        patched_count=len(applied) if request.mode == "patch" else 0,
        candidates=candidates,
        applied=applied,
        skipped=skipped,
        backup_created=backup_paths,
        errors=errors,
        summary=summary,
    )


def _load_from_review_result(path: str) -> tuple[list[Finding], dict[str, tuple[str, Any | None]]]:
    """Load findings and file contents from review-result.json."""
    p = Path(path)
    if not p.exists():
        return [], {}

    data = json.loads(p.read_text(encoding="utf-8"))
    findings_data = data.get("findings", [])
    findings = [Finding.model_validate(f) for f in findings_data]

    file_contents: dict[str, tuple[str, Any | None]] = {}
    for f in findings:
        for path in f.impacted_files:
            if path not in file_contents:
                content, parsed = _load_file(path)
                file_contents[path] = (content, parsed)

    return findings, file_contents


def _normalize_path(path: str) -> str:
    """Normalize path for consistent lookup across platforms."""
    return str(Path(path).resolve())


def _load_file(path: str) -> tuple[str, dict | None]:
    """Load file content and parsed YAML."""
    p = Path(path)
    if not p.exists():
        return "", None
    content = p.read_text(encoding="utf-8")
    data, _ = load_yaml(p)
    return content, data


