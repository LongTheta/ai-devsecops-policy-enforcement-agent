# Retrieval-Augmented Generation (RAG) Integration Design

**Principle:** *Rules decide. RAG explains. Templates remediate.*

This document designs a RAG layer for [ai-devsecops-policy-enforcement-agent](https://github.com/LongTheta/ai-devsecops-policy-enforcement-agent) that **enriches** findings after deterministic evaluation. It does **not** change pass/fail logic, policy YAML semantics, analyzer rules, or auto-fix applicability.

---

## Step 1 — Repository analysis

### 1.1 Where policy evaluation occurs

| Location | Role |
|----------|------|
| `src/ai_devsecops_agent/workflows/review_workflow.py` | **`run_review(request)`** — orchestrates analyzers, compliance enrichment, verdict |
| `src/ai_devsecops_agent/policies/loader.py` | Loads `PolicySet` from YAML |
| `src/ai_devsecops_agent/analyzers/pipeline_analyzer.py` | Heuristics + **policy-driven** rules when `policy_path` set |
| `src/ai_devsecops_agent/analyzers/gitops_analyzer.py` | Argo/K8s findings |
| `src/ai_devsecops_agent/analyzers/cross_system_analyzer.py` | CI↔GitOps governance |
| `src/ai_devsecops_agent/analyzers/sbom_analyzer.py` | SBOM/provenance patterns |
| `src/ai_devsecops_agent/analyzers/compliance_mapper.py` | **`enrich_findings_with_controls`** — deterministic NIST-style **family** hints (`IA`, `CM`, …) |

**Verdict:** `_compute_verdict_and_summary` in `review_workflow.py` — **critical/high → fail**; medium/low → pass_with_warnings; else pass. **RAG must not run before this** in a way that alters `findings` used for verdict (see §5).

### 1.2 How findings are structured

- **`src/ai_devsecops_agent/models.py`**
  - **`Finding`**: `id`, `title`, `severity`, `category`, `description`, `evidence`, `impacted_files`, `control_families` (`ComplianceMapping[]`), `remediation_summary`, `remediation`, `policy_rule_id`, `source_analyzer`, `finding_group`
  - **`ReviewResult`**: `verdict`, `summary`, `findings`, `policy_results`, `compliance_considerations`, `recommended_remediations`, `next_steps`, `context`, `metadata`

Serialization: `workflows/artifacts.py` — **`_result_to_review_dict`** → `review-result.json` (findings as `model_dump`).

### 1.3 Where remediation logic is generated

| Location | Role |
|----------|------|
| `src/ai_devsecops_agent/remediation/engine.py` | **`generate_remediation_bundle`** — templates keyed by **finding id**; deterministic text/patches |
| `src/ai_devsecops_agent/autofix/engine.py` | **`run_autofix`** — registered fixers; safety levels; **no LLM** |

RAG may **summarize or cite** remediation text; it must **not** invent new patches or change which fixers run.

### 1.4 Where outputs are rendered

| Location | Output |
|----------|--------|
| `src/ai_devsecops_agent/cli.py` | `review`, `review-all`, `comments`, `remediate`, `auto-fix` |
| `src/ai_devsecops_agent/reporting/` | Markdown, JSON, SARIF, console |
| `src/ai_devsecops_agent/review_comments/` | PR/MR comment bodies |
| `src/ai_devsecops_agent/workflows/artifacts.py` | `review-result.json`, `policy-summary.json`, `comments.json`, `remediations.json` |

### 1.5 Knowledge sources already in-repo

| Source | Use in RAG |
|--------|----------------|
| `docs/*.md` | Architecture, policy model, workflows, evaluation, system thinking |
| `policies/*.yaml` | Rule ids, names, severities — **metadata filters** and chunk boundaries |
| `examples/` | Sample pipelines, GitOps, outputs — **approved pattern** examples (tag `approved_fix: true` only for vetted snippets) |
| `src/.../compliance_mapper.py` | Seed **deterministic** control families; RAG adds **optional** FedRAMP/NIST 800-53/Zero Trust **references** as enrichment, not replacements |

### 1.6 Data flow (today)

```
ReviewRequest
  → load_policy_set
  → analyze_pipeline / analyze_gitops / analyze_sbom / analyze_cross_system
  → enrich_findings_with_controls
  → policy_results list
  → _compute_verdict_and_summary  → ReviewResult
  → reporting / write_artifacts / comments
```

---

## Step 2 — RAG architecture

### 2.1 Insertion point (required)

**After** findings exist and **verdict is computed from the same finding list the analyzers produced**, **before** rendering/writing artifacts:

```
… → ReviewResult(verdict, findings, …)  # verdict frozen
  → optional_rag_enrich(result)         # adds sidecar fields ONLY
  → reporting / write_artifacts
```

**Critical implementation rule:** Build `ReviewResult` with **immutable verdict**. The enrichment step returns a **copy** of `ReviewResult` (or copies each `Finding`) with additional optional fields populated. **Never** re-run `_compute_verdict_and_summary` on RAG-augmented text.

Safer variant: `enrich_findings_post_verdict(findings, context) -> list[Finding]` that only attaches `rag` / `enrichment` payloads; verdict already computed from pre-enrichment findings.

### 2.2 Updated data flow (with RAG)

```
Input → Parse paths → Policy evaluation (analyzers) → Findings
  → enrich_findings_with_controls (deterministic)
  → verdict / summary (deterministic, from findings)
  → [RAG] per-finding retrieval + optional LLM summarize (explain only)
  → merge enrichment into Finding sidecar fields
  → ReviewResult → Markdown / JSON / SARIF / comments / artifacts
```

### 2.3 Retrieval strategy

- **Per finding**, not one global chat context.
- **Hybrid retrieval:**
  - **Metadata filter** (exact): `finding.id` prefix family (`pipeline-*`, `policy-*`, `gitops-*`, `cross-*`), `category`, `finding_group`, `platform` (from `ReviewContext.platform`), `severity`, optional `policy_rule_id`.
  - **Semantic search** over chunk embeddings (title + description + rule text from policy YAML).
- **Top-k:** 3–8 chunks; **score floor** (e.g. cosine similarity ≥ 0.72) to avoid irrelevant context.
- **No retrieval → no LLM call** (optional: template-only explanation from `finding.id` lookup table as fallback).

### 2.4 Storage recommendation

| Environment | Store |
|-------------|--------|
| Local / CI first | **Chroma** (persistent dir under `.rag/index/` gitignored) or **FAISS** + sidecar JSON metadata |
| Production | **PostgreSQL + pgvector** — same metadata columns for audit; index version in `ReviewResult.metadata` |

---

## Step 3 — Knowledge base design

### 3.1 Content to ingest

1. `docs/` — section-level chunks (POLICY-MODEL, WORKFLOW-INTEGRATION, ARCHITECTURE).
2. `policies/*.yaml` — one chunk per **rule** (`rules[]` entries) with full id/name/description/severity.
3. `examples/sample-output*.md` / JSON — narrative only; label `source_type: example`.
4. **Simulated / org packs** (future): `knowledge/fedramp/` — control narratives keyed by SP 800-53 control IDs (text, not verdict logic).
5. **Approved patterns** — small curated YAML snippets from `examples/` that are explicitly tagged as reference-only in metadata (`approved_fix: false` unless security-reviewed).

### 3.2 Chunking

- **By policy rule:** one chunk per YAML rule id.
- **By doc section:** Markdown split on `##` headers; max ~512–1024 tokens per chunk.
- **By finding template:** static paragraphs keyed by analyzer finding id (e.g. `pipeline-002` unpinned image).

### 3.3 Metadata on every chunk (required)

| Field | Example |
|-------|---------|
| `chunk_id` | `policy:require_sbom:v1` |
| `finding_type` | `unpinned_image`, `plaintext_secret`, `argo_prune_selfheal`, … |
| `finding_id_prefix` | `pipeline`, `policy`, `gitops`, `cross` |
| `platform` | `gitlab` \| `github` \| `argocd` \| `kubernetes` \| `any` |
| `framework` | `NIST` \| `FedRAMP` \| `ZeroTrust` \| `internal` \| `none` |
| `severity` | mirrors finding when rule-specific; else `any` |
| `approved_fix` | `true` only for vetted snippets |
| `source_type` | `policy` \| `doc` \| `example` \| `runbook` \| `control_ref` |
| `source_path` | repo-relative path |

### 3.4 Example chunk record (JSON)

```json
{
  "chunk_id": "doc:POLICY-MODEL:require_pinned_pipeline_dependencies",
  "text": "Rule require_pinned_pipeline_dependencies ensures images and GitHub Actions are pinned to digests or commit SHAs…",
  "metadata": {
    "finding_type": "unpinned_image",
    "finding_id_prefix": "pipeline",
    "platform": "github",
    "framework": "NIST",
    "severity": "high",
    "approved_fix": false,
    "source_type": "doc",
    "source_path": "docs/POLICY-MODEL.md"
  }
}
```

---

## Step 4 — Retrieval logic

### 4.1 Query construction

For each `Finding` `f`:

1. **Structured filter:** `metadata.finding_type` matches normalized type from `f.id` + `f.category` (see mapping table in code: `pipeline-002` → `unpinned_image`).
2. **Text query string** (for embedding):
   ```
   {f.title} {f.category} {f.finding_group or ""}
   {context.platform.value} {context.compliance_mode}
   supply chain gitops policy
   ```
3. **Optional boost:** append `policy_rule_id` text from loaded `PolicySet` if `f.policy_rule_id` is set.

### 4.2 Filters before vector search

Apply hard filters: `platform in (chunk.platform, any)`, `framework` match if user requests FedRAMP mode (`ReviewContext.compliance_mode == fedramp-moderate`), `severity` compatible.

### 4.3 Top-k and thresholds

- Retrieve **2×k** candidates by vector similarity, then **re-rank** by metadata match score.
- Drop chunks below **similarity threshold**.
- Cap **total tokens** sent to any summarizer LLM (e.g. 2k tokens) to control cost and hallucination risk.

### 4.4 LLM usage (optional)

If an LLM is used, **prompt contract:**

- Input: finding JSON (without enrichment) + retrieved chunk texts + instruction: *“Explain why this finding matters and how it relates to the cited references. Do not change severity or recommend bypassing policy.”*
- Output: **explanation** and **recommended_fix_summary** strings only; parse and attach; **discard** if schema validation fails.

**No LLM:** concatenate top chunk titles + first 2 sentences as `explanation` (fully deterministic).

---

## Step 5 — Code integration plan

### 5.1 Proposed module layout

```
src/ai_devsecops_agent/retrieval/
  __init__.py
  schemas.py       # RetrievedChunk, RagEnrichment, FindingRagPayload (Pydantic)
  normalize.py     # finding id → finding_type, platform hints
  ingest.py        # load docs/policies/examples → chunks + metadata
  index.py         # build / load Chroma or FAISS + metadata store
  query.py         # hybrid query per Finding
  enrich.py        # enrich_findings_with_rag(result | findings, config) -> ReviewResult
  llm_summarize.py # optional, strict output schema; off by default
```

### 5.2 Integration in `run_review` (pseudocode)

```python
def run_review(request: ReviewRequest) -> ReviewResult:
    # ... existing analyzer + enrich_findings_with_controls ...
    verdict, summary = _compute_verdict_and_summary(all_findings, context)
    result = ReviewResult(verdict=verdict, summary=summary, findings=all_findings, ...)

    if request.context.integrations.get("rag_enabled"):
        result = apply_rag_enrichment(result, RagConfig.from_env())
    return result
```

**Alternative (cleaner):** keep `run_review` pure; call `apply_rag_enrichment` only from **`cli.review`** after `run_review` and before `render_*` / `write_artifacts`. That avoids importing retrieval in the core workflow for tests that disable RAG.

### 5.3 Function signatures (Python)

```python
# retrieval/enrich.py
def apply_rag_enrichment(
    result: ReviewResult,
    config: RagConfig,
) -> ReviewResult:
    """Attach RAG fields to findings; verdict unchanged."""
    ...

def enrich_findings_with_rag(
    findings: list[Finding],
    context: ReviewContext,
    config: RagConfig,
) -> list[Finding]:
    """Per-finding retrieval + optional summarize; deterministic if llm_disabled."""
    ...
```

```python
# retrieval/query.py
def retrieve_for_finding(
    finding: Finding,
    context: ReviewContext,
    index: RetrievalIndex,
    k: int = 5,
) -> list[RetrievedChunk]:
    ...
```

### 5.4 Extending `Finding` (schema)

Add **optional** nested model (backward compatible):

```python
class RetrievedContextItem(BaseModel):
    chunk_id: str
    source_path: str
    source_type: str
    snippet: str
    score: float
    framework: str | None = None

class RagEnrichment(BaseModel):
    explanation: str | None = None
    compliance_mapping_rag: list[ComplianceMapping] = Field(default_factory=list)
    retrieved_context: list[RetrievedContextItem] = Field(default_factory=list)
    recommended_fix_summary: str | None = None
    rag_model_id: str | None = None
    index_version: str | None = None

# On Finding:
# rag: RagEnrichment | None = None
```

**Rule engine and auto-fix read `Finding` without requiring `rag`.** Serializers already use `model_dump`; new fields flow to `review-result.json` automatically.

---

## Step 6 — Output enhancement

### 6.1 Fields (all optional, advisory)

| Field | Purpose |
|-------|---------|
| `explanation` | Human-readable context (RAG + optional LLM) |
| `compliance_mapping_rag` | **Additional** mappings from retrieval; keep existing `control_families` from `compliance_mapper` |
| `retrieved_context[]` | Citations for audit |
| `recommended_fix_summary` | Short text; **remediation engine remains authoritative** for structured steps |

### 6.2 Example enriched finding (JSON)

```json
{
  "id": "pipeline-002",
  "title": "Unpinned container image or action",
  "severity": "high",
  "category": "supply_chain",
  "description": "Pipeline uses an image or action without a digest or explicit tag…",
  "evidence": "uses: actions/checkout@v4",
  "impacted_files": [".github/workflows/ci.yml"],
  "control_families": [
    {
      "control_family": "SA",
      "control_id": null,
      "rationale": "System and services acquisition – supply chain and SBOM",
      "note": "This mapping supports engineering review and is not a formal compliance determination."
    }
  ],
  "remediation_summary": "Pin images by digest; pin actions by full commit SHA.",
  "policy_rule_id": null,
  "source_analyzer": "pipeline_analyzer",
  "finding_group": "github_actions",
  "rag": {
    "explanation": "Unpinned GitHub Actions references rely on moving tags; supply-chain compromises of third-party actions are mitigated by pinning to an immutable commit SHA, consistent with NIST SSDF and organizational SDLC controls.",
    "compliance_mapping_rag": [
      {
        "control_family": "SI",
        "control_id": "SI-7",
        "rationale": "Software integrity; pinned references support integrity verification (informational).",
        "note": "RAG-suggested mapping for review only; not a formal assessment."
      }
    ],
    "retrieved_context": [
      {
        "chunk_id": "policy:require_pinned_pipeline_dependencies",
        "source_path": "policies/default.yaml",
        "source_type": "policy",
        "snippet": "require_pinned_pipeline_dependencies: …",
        "score": 0.84,
        "framework": "NIST"
      },
      {
        "chunk_id": "doc:WORKFLOW-INTEGRATION:pinning",
        "source_path": "docs/WORKFLOW-INTEGRATION.md",
        "source_type": "doc",
        "snippet": "…artifact generation and policy gates…",
        "score": 0.78,
        "framework": "internal"
      }
    ],
    "recommended_fix_summary": "Replace actions/checkout@v4 with actions/checkout@<full-40-char-sha>; verify in Actions release notes.",
    "rag_model_id": null,
    "index_version": "2026-04-01"
  }
}
```

---

## Step 7 — Optional enhancements (do not implement yet)

- **PR/MR comments:** second column “References” from `retrieved_context` (markdown links to in-repo doc anchors).
- **Policy-to-control traceability:** export CSV/SARIF extension with `control_families` + `compliance_mapping_rag` for auditors.
- **Org knowledge packs:** mount `knowledge/ept/` or JADE-style YAML as extra Chroma collection with `source_type: org_standard`.
- **Future agents:** orchestrator calls `run_review` unchanged; a separate “analyst agent” only **reads** `review-result.json` + RAG fields; never writes policy.

---

## Step 8 — Deliverables summary

### Architecture (text diagram)

```
┌─────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Analyzers   │───▶│ Findings +      │───▶│ Verdict (code) │
│ + policy    │    │ compliance_map  │    │ PASS/FAIL      │
└─────────────┘    └────────┬─────────┘    └────────┬────────┘
                           │                         │
                           ▼                         ▼
                    ┌──────────────┐          ┌──────────────┐
                    │ RAG retrieve │          │ NO FEEDBACK  │
                    │ per finding  │          │ INTO VERDICT│
                    └──────┬───────┘          └──────────────┘
                           ▼
                    ┌──────────────┐
                    │ Optional LLM  │  summarize only
                    │ (explain)     │
                    └──────┬───────┘
                           ▼
                    ┌──────────────┐
                    │ ReviewResult  │──▶ reports / artifacts
                    │ + rag fields  │
                    └──────────────┘
```

### Why this is safe and production-ready

1. **Deterministic enforcement preserved:** Verdict uses only analyzer outputs; RAG runs **after** verdict computation.
2. **No auto-fix contamination:** `autofix/engine.py` uses `Finding` fields used today; RAG fields are ignored unless you explicitly **never** wire them to fixers.
3. **Auditability:** `retrieved_context` cites chunk ids and paths; `index_version` supports reproducibility.
4. **Graceful degradation:** RAG off → current behavior unchanged.
5. **Cost control:** Per-finding retrieval with caps; LLM optional.

### Pseudocode — enrichment pipeline

```text
FOR each finding F in result.findings:
  Q = build_query(F, context)
  C = hybrid_search(index, Q, filters=metadata_filters(F), k=8)
  C = filter_by_score(C, min_score=0.72)
  IF config.use_llm:
    E = llm_explain(F, C)   # strict JSON schema
  ELSE:
    E = template_explain(F, C)
  F' = F with rag=E attached
RETURN result with findings replaced by F'
# verdict, summary unchanged from pre-loop snapshot
```

---

## Appendix — Key file reference

| Path | Role |
|------|------|
| `src/ai_devsecops_agent/workflows/review_workflow.py` | `run_review`, verdict |
| `src/ai_devsecops_agent/models.py` | `Finding`, `ReviewResult`, `ComplianceMapping` |
| `src/ai_devsecops_agent/workflows/artifacts.py` | `review-result.json` |
| `src/ai_devsecops_agent/remediation/engine.py` | Deterministic remediation bundle |
| `src/ai_devsecops_agent/analyzers/compliance_mapper.py` | Deterministic control families |
| `policies/*.yaml` | Rule definitions |
| `docs/` | Ingestible knowledge |

---

*This design is implementation-ready; add dependencies (chromadb, sentence-transformers, or pgvector client) only when implementing `index.py` / `query.py`.*
