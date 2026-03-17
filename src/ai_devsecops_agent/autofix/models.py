"""Models for policy-aware auto-fix."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SafetyLevel(str, Enum):
    """Safety classification for a fix."""

    SAFE = "safe"
    REVIEW_REQUIRED = "review_required"
    SUGGEST_ONLY = "suggest_only"


class Confidence(str, Enum):
    """Confidence in the fix correctness."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PatchOperation(str, Enum):
    """Type of patch operation."""

    REPLACE = "replace"
    INSERT = "insert"
    DELETE = "delete"


class FilePatch(BaseModel):
    """A single patch to apply to a file."""

    file_path: str = Field(description="Path to the file to patch")
    operation: PatchOperation = Field(description="Type of operation")
    path: str = Field(description="JSONPath or YAML path to target (e.g. spec.template.spec.containers[0].resources)")
    original_value: Any = Field(default=None, description="Original value being changed")
    new_value: Any = Field(description="New value to apply")
    description: str = Field(default="", description="Human-readable description of the change")


class FixCandidate(BaseModel):
    """A single fix candidate for a finding."""

    finding_id: str = Field(description="ID of the finding this fix addresses")
    file_path: str = Field(description="Path to the file to fix")
    fix_type: str = Field(description="Fixer type identifier")
    title: str = Field(description="Short title")
    description: str = Field(description="What this fix does")
    confidence: Confidence = Field(description="Confidence level")
    safety_level: SafetyLevel = Field(description="Safety classification")
    can_auto_apply: bool = Field(description="Whether apply mode is allowed")
    requires_review: bool = Field(default=True, description="Whether human review is recommended")
    diff: str | None = Field(default=None, description="Unified diff preview")
    original_excerpt: str | None = Field(default=None, description="Original snippet")
    patched_excerpt: str | None = Field(default=None, description="Patched snippet")
    patches: list[FilePatch] = Field(default_factory=list, description="Structured patches")
    limitations: list[str] = Field(default_factory=list, description="Known limitations")
    rollback_notes: str | None = Field(default=None, description="How to revert if needed")
    patched_content: str | None = Field(default=None, description="Full patched file content (for fixers that replace entire file)")


class AutoFixRequest(BaseModel):
    """Input for auto-fix run."""

    mode: str = Field(description="suggest | patch | apply")
    input_path: str | None = Field(default=None, description="Path to review-result.json (alternative to in-memory findings)")
    pipeline_path: str | None = Field(default=None, description="Path to pipeline file")
    gitops_paths: list[str] = Field(default_factory=list, description="Paths to GitOps manifests")
    manifest_paths: list[str] = Field(default_factory=list, description="Paths to K8s manifests")
    output_dir: str | None = Field(default=None, description="Output directory for patch mode")
    only_safe: bool = Field(default=False, description="Only include fixes with can_auto_apply=True")
    backup: bool = Field(default=True, description="Create backups before apply")
    dry_run: bool = Field(default=False, description="Show what would be done without writing")
    rules: list[str] | None = Field(default=None, description="Restrict to specific fix types")


class AutoFixResult(BaseModel):
    """Result of an auto-fix run."""

    mode: str = Field(description="suggest | patch | apply")
    finding_count: int = Field(default=0, description="Number of findings considered")
    candidate_count: int = Field(default=0, description="Number of fix candidates generated")
    applied_count: int = Field(default=0, description="Number of fixes applied (apply mode only)")
    patched_count: int = Field(default=0, description="Number of patched files written (patch mode only)")
    candidates: list[FixCandidate] = Field(default_factory=list, description="All fix candidates")
    applied: list[FixCandidate] = Field(default_factory=list, description="Candidates that were applied")
    skipped: list[FixCandidate] = Field(default_factory=list, description="Candidates skipped (e.g. not safe)")
    backup_created: list[str] = Field(default_factory=list, description="Paths to backup files created")
    errors: list[str] = Field(default_factory=list, description="Errors encountered")
    summary: str = Field(default="", description="Human-readable summary")
