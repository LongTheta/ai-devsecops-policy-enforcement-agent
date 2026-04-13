# System Thinking and Operational Design Notes

This document captures how this system is designed, evaluated, and operated in practice, including the tradeoffs.

Internal guidance on **building and operating** AI-adjacent systems in production: design constraints, measurable outcomes, and common failure modes. This repository emphasizes **deterministic** analysis (policy checks, structured artifacts); if generative or orchestrated LLM components are added, the same operational practices apply, typically with tighter controls.

---

## System Model

- **Deterministic core (policy enforcement)** — Versioned rules and evaluators; same inputs yield the same verdicts and structured artifacts.
- **Agent orchestration (decision layer)** — Plans steps, selects tools, and proposes actions through validated contracts; it does not replace or bypass policy.
- **Persistent memory (state + trace)** — Task graph, handoffs, and execution history (for example Beads) so long-running workflows stay coherent and auditable.

This separation ensures:

- **Reliability** — Failures are localized; the enforcement path stays testable and repeatable.
- **Auditability** — Authority and evidence live in policy outputs and traces, not in model prose.
- **Controlled flexibility** — Orchestration can explore and iterate; only approved, validated actions affect production systems.

---

## 1. Agent Design Considerations

### How agents decide what actions to take

Actions should come from an explicit **contract**: allowed inputs, a fixed decision procedure, and outputs that downstream systems can parse. In this project, “decisions” are **not** open-ended: analyzers emit findings, severity rolls up to a verdict, and the CLI encodes pass/fail for CI. If you add model-based routing or summarization later, keep that layer **behind** the same kind of contract (schemas, verdict enums, versioned prompts).

Operations and security teams must define **who holds authority**: if a model proposes an action, the runtime must still enforce **identity, scope, and policy** outside the model.

### Tool usage and constraints

Treat every integration (API clients, analyzers, auto-fix fixers) as a **tool** with a narrow surface:

- **Allowlisted operations** — Call only tested code paths; reject unknown parameters at the boundary.
- **Explicit failure** — Timeouts and HTTP errors should surface as structured errors, not silent empty success.
- **Separation** — Read-only analysis (`review`) should stay separable from mutating paths (`auto-fix apply`). This repo keeps that split at the CLI and safety levels on fixers.

### Preventing invalid or unsafe actions

Layer controls so no single mistake bypasses everything:

1. **Validate before execute** — Schema-check structured outputs; validate YAML before treating it as authoritative.
2. **Policy outside the model** — Rules live in versioned YAML; disabled rules do not run. Severity for policy-backed findings comes from policy metadata, not from model text.
3. **Mutations** — Auto-fix uses registered fixers with safety classification; `--only-safe` restricts what may run unattended. Suggest-only paths stay human-reviewed.

---

## 2. Evaluation Strategy

### How system correctness is measured

Correctness here is **verifiable**: given inputs, do you get the expected findings, verdict, and artifacts? Measure at three levels:

- **Rule-level** — Does each detector fire on known-good and known-bad fixtures?
- **Integration-level** — Does the full `run_review` path produce stable JSON/Markdown for representative repos?
- **Outcome-level** — Does CI block when it should (exit non-zero on fail verdict) and pass when appropriate?

### Offline evaluation vs runtime validation

| | **Offline evaluation** | **Runtime validation** |
|---|------------------------|-------------------------|
| **What** | Curated datasets, golden files, regression cases | Live or canary runs, real pipelines, API latency and quotas |
| **When** | Every change to analyzers, policy, or packaging | Continuously in staging/production |
| **Purpose** | Catch regressions before merge; compare candidates | Confirm SLOs, cost, and failure rates under real load |

Offline tests prove the **logic**; runtime proves the **system** (tokens, network, rate limits, concurrent jobs).

### What metrics matter

Prioritize a small set tied to user impact:

- **Success rate** — Jobs completed without infrastructure error (distinct from “policy pass”).
- **Error rate** — Failed fetches, parse failures, unhandled exceptions, upstream 4xx/5xx.
- **Latency** — p95/p99 for full review; budget headroom for CI job timeouts.
- **Cost** — API calls, compute minutes, and—if models are involved—tokens per successful review.

Policy **pass rate** is a product metric, not purely a reliability metric: a spike may mean the policy tightened or repos improved—correlate with policy and commit history.

More detail: [evaluation-framework.md](evaluation-framework.md).

---

## 3. Failure Modes

### Typical failure patterns

- **Brittle integrations** — Tokens expire, APIs change, or rate limits throttle batch jobs; failures look like “empty pipeline” or flaky CI.
- **Ambiguous inputs** — Malformed YAML, huge files, or non-standard workflow layouts; partial analysis without a loud warning.
- **Drift** — Model or prompt updates change behavior without a corresponding test bump.
- **Coupling** — One failure (e.g., comment post) marked as total job failure when the core verdict was already computed.

### Invalid outputs, hallucinations, unsafe actions

Generative components can emit plausible but wrong tool arguments or skip steps. Deterministic pipelines avoid **argument hallucination** by construction; if you add LLM steps, assume **invalid JSON and wrong tool names** until proven otherwise—validate every call.

Unsafe actions usually mean **unscoped credentials**, **destructive APIs**, or **auto-apply without review**. Mitigate with least privilege, dry-run modes, and human gates for high-impact changes.

### Partial failures and retries

- **Idempotent reads** — Safe to retry fetches of pipeline YAML if failures are transient.
- **Don’t double-apply** — Auto-fix apply should not assume retries are harmless; use backups and clear “already applied” detection where possible.
- **Degrade gracefully** — If comment posting fails, still persist artifacts and exit with the correct verdict unless policy says otherwise.

---

## 4. Agent Execution and Evaluation Considerations

When extending this system with agent-driven behavior, evaluating the final output alone is not sufficient. The system must also evaluate the sequence of decisions taken to reach that output.

**Key considerations**

- **Decision traceability**
  - Every step (decision → tool call → result) should be recorded and correlated to a single run.
  - This enables debugging when outcomes are incorrect but not obviously failing.

- **Tool selection correctness**
  - The agent must choose the appropriate tool for a given task.
  - Incorrect tool usage is often a higher-risk failure than incorrect output.

- **Argument validation**
  - All tool inputs must be schema-validated before execution.
  - Invalid arguments should fail fast and surface clearly.

- **Execution path efficiency**
  - Excessive steps, loops, or redundant tool calls increase cost and latency.
  - Track steps per task and compare against expected baselines.

- **Outcome vs trajectory**
  - A correct final result achieved through unsafe or inefficient steps is still a failure condition.
  - Evaluation should include both final output quality and execution path quality.

**In practice, this requires**

- capturing full execution traces;
- defining success criteria at the workflow level; and
- incorporating multi-step scenarios into regression testing.

---

## 5. Reliability Patterns

### Idempotency

Running `review` twice on the same inputs and policy should yield the **same verdict and comparable findings** (stable ordering in artifacts helps diffing). CI should be able to re-run jobs without changing production state—this repo’s read path is naturally idempotent.

### Safe retries

Retry only **read** operations with exponential backoff and jitter. Avoid blind retries on **writes** (comments, apply) without idempotency keys or deduplication.

### Deterministic validation

Prefer rules that produce the same result for the same file bytes. Verdict logic should be **code-defined** and test-covered so “pass/fail” is not interpreted from free text.

### Guardrails before execution

Order of operations: **analyze → decide → optionally suggest → human or policy gate → mutate**. Never let an LLM execute shell or cloud APIs without schema validation and authorization checks on the service side.

---

## 6. Observability

### What signals are needed to debug the system

Minimum useful context per run:

- **Identity** — Repository, branch, MR/PR, policy file name and version, commit SHA if available.
- **Outcome** — Verdict, finding counts by severity, exit code.
- **Scope** — Which paths were analyzed; whether fetch was remote or local.
- **Upstream** — HTTP status and latency for Git provider calls; token auth failures (without logging secrets).

### Logs, traces, metrics

- **Logs** — Structured, one line per major step (load policy, each analyzer, verdict). Include a **correlation id** across CI steps if the review is part of a larger pipeline.
- **Traces** — Useful when multiple services participate (CI runner → agent → Git API). A single span for “review” with child spans per analyzer is enough to start.
- **Metrics** — Counters for runs, failures, duration histograms; optional gauges for queue depth if you batch reviews.

### Why observability matters for agent systems

When behavior is non-deterministic or multi-step, you cannot debug from “it failed” alone. You need to reconstruct **which path** ran, **which policy** applied, and **which dependency** flaked. Even for deterministic agents, production issues are usually **integration and environment** issues; logs tie artifacts back to a specific run.

---

## 7. Tradeoffs

### Flexibility vs control

More flexible prompts or broader tool sets increase coverage but widen the failure surface. Tight schemas, fixed analyzers, and explicit policy YAML favor **predictable** behavior, which aligns with compliance-oriented CI use cases in this repository.

### Speed vs validation

Skipping checks or shrinking inputs saves seconds but hides findings. Cap input size and fail closed with a clear error rather than silently analyzing a truncated file.

### Cost vs accuracy

Larger models or more API calls improve edge cases but raise cost and latency. Measure **cost per successful gated merge** (or per clean review), not cost per token in isolation.

---

## 8. Lessons Learned

The following patterns recur when operating systems of this class. Use them to calibrate controls as capabilities and scope evolve.

- **Heuristics vs policy** — When built-in detectors and policy-driven rules overlap, teams need clear documentation on which severity wins and how to avoid duplicate noise. Prefer one authoritative path per concern where possible.
- **“Pass” in CI ≠ secure** — A passing verdict only means **no critical/high findings under this policy**. Operators still need asset context, threat model, and manual review for high-risk changes.
- **Remote fetch is a dependency** — Tokens, permissions, and API availability become part of your SLO. Failures should be visible in logs and metrics, not silent fallbacks.
- **Auto-fix needs ownership** — Apply mode is powerful; teams that skip code review on automated patches eventually ship a bad change. Keep suggest-only where resolution requires environment-specific knowledge (e.g., pinning to a real digest).
- **Production hardening** — Stricter versioning of policy packs (pin by hash or tag), artifact retention for audits, and alerts when error rate or latency regress after a release.

---

*Internal guidance: revise this document when architecture, dependencies, or operating assumptions change.*
