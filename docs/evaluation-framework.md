# Evaluation Framework for AI-Driven Systems

This document describes a practical evaluation framework for an AI-driven system running in production. The goal is **measurable reliability**: define what “good” means in advance, detect regressions before they reach users, and tune cost without guesswork.

Treat evaluation as **continuous engineering**, not a one-time benchmark. Offline tests catch structural mistakes; online metrics catch real-world drift; safety gates limit harm; economics keep the system sustainable; regression suites protect every change to models, prompts, or orchestration.

---

## 1. Principles

- **Define success in advance.** Every metric should map to a product or operational outcome (correctness, latency, safety, spend).
- **Separate “model quality” from “system quality.”** A strong model behind a flaky integration still fails users.
- **Version everything.** Record model ID, prompt hash, tool/schema version, and feature flags with every run you evaluate.
- **Automate gates.** CI blocks releases when offline thresholds fail; production alerts fire when online SLIs breach.

---

## 2. Offline Evaluation

Offline evaluation runs **without live traffic**, using curated inputs and known-good (or known-bad) references. Use it for fast feedback in CI and for comparing candidates before promotion.

### 2.1 Test datasets

| Dataset type | Purpose |
|--------------|---------|
| **Golden set** | Representative real or synthetic inputs with **expected outputs** (final answer, structured JSON, tool calls, or policy verdicts). |
| **Edge cases** | Empty inputs, oversized payloads, ambiguous instructions, multilingual or noisy text, malformed API responses. |
| **Adversarial / stress** | Prompt injection snippets, jailbreak attempts, and inputs designed to elicit policy violations (paired with safety expectations in §4). |
| **Regression suite** | Inputs that previously failed in production or support tickets—**frozen** so they never regress silently. |

**Practices**

- **Stratify** by intent (e.g., “summarize,” “classify,” “invoke tool X”) so aggregate scores are not dominated by one use case.
- **Refresh periodically** from production samples (with consent and PII handling), but **never delete** regression cases without explicit review.
- Store datasets in version control or an artifact store with **immutable versions** referenced by evaluation jobs.

### 2.2 Expected outputs

Choose evaluation criteria that match how the product is consumed:

- **Exact or normalized match** for structured outputs (JSON keys, enums, verdict codes).
- **Semantic similarity** or **LLM-as-judge** (with a fixed rubric and human spot-checks) for free text—document limitations and bias.
- **Tool-call correctness**: right tool, valid arguments, no extra calls, ordering when it matters.
- **Multi-step workflows**: assert intermediate states only when they are part of your contract (avoid over-specifying implementation details).

**Pass/fail thresholds** should be numeric (e.g., ≥ 95% exact match on structured fields; ≥ 90% judge agreement on a held-out set validated against humans).

### 2.3 When to run

- On every change that can affect behavior: **model version**, **system prompt**, **tool definitions**, retrieval index, or routing logic.
- Nightly or weekly **full** sweeps on larger datasets if PR-sized sets are subsets.

---

## 3. Online Evaluation

Online evaluation measures behavior **with real or shadow traffic** in production-like conditions. It answers whether the system meets **latency**, **availability**, and **outcome** expectations under load.

### 3.1 Core metrics

| Metric | What to measure | Why it matters |
|--------|-----------------|----------------|
| **Latency** | p50 / p95 / p99 end-to-end; optionally time-to-first-token for streaming | User experience and headroom for retries/timeouts |
| **Success rate** | Fraction of requests completing without system error (HTTP 2xx, no unhandled exception) | Stability of the integration |
| **Task success / business outcome** | User completed flow, policy passed, ticket resolved—per the product’s definition | Aligns technical metrics with product value |
| **Error rate** | 4xx/5xx, timeouts, rate limits, model refusals when not intended | Distinguishes client, server, and upstream failures |

**Practices**

- Emit **structured logs** with `request_id`, model/prompt versions, and outcome labels for sampling and drill-down.
- Use **SLOs** (e.g., “p95 latency < 3s for 30 rolling days”) and **error budgets** to pace releases and incident response.

### 3.2 Shadow and canary traffic

- **Shadow**: duplicate requests to a new model/prompt without affecting users; compare outputs offline or with automated diff checks.
- **Canary**: route a small percentage of traffic to the new stack; watch latency and error regressions before full rollout.

### 3.3 Human-in-the-loop (lightweight)

For high-stakes domains, sample a fixed rate of production outputs for human review. Track **disagreement rate** with automated labels and feed mistakes back into the golden and regression sets.

---

## 4. Safety Evaluation

Safety evaluation verifies the system **respects policies** and **does not take invalid actions**, especially when tools touch external systems.

### 4.1 Policy violations

Define **explicit policies** (content, PII, data residency, allowed tools, rate limits). Measure:

- **Violation rate**: outputs or actions that breach policy, per 1k requests or per time window.
- **Severity tiers**: e.g., release-blocking (data exfiltration attempt) versus advisory (borderline phrasing).

**Practices**

- Maintain a **policy test pack** (inputs that should always refuse, redact, or escalate).
- Log **policy decisions** with enough context for audit without storing unnecessary sensitive data.

### 4.2 Invalid actions

When the AI invokes tools or APIs:

- **Schema validation**: every call conforms to the tool contract.
- **Authorization**: caller identity and scopes are checked **outside** the model; the model never “is” the authority.
- **Allowlists**: destinations, commands, or file paths restricted by configuration.

Track **invalid action rate** and **blocked-by-policy middleware rate** separately from model refusals.

### 4.3 Abuse and misuse

Monitor unusual patterns (volume spikes, probing sequences). Pair automated heuristics with periodic **red-team** runs using updated attack corpora.

### 4.4 Agent-level evaluation

For agent-driven systems, evaluating the final output alone is insufficient. The system must also be assessed on the **actions taken and the execution path** used to reach that result.

**Key considerations**

- **Tool selection accuracy** — Verify that the agent invokes the correct tool for the task. Track **correct tool usage rate** against expected tool invocations from fixtures or labeled traces.

- **Argument correctness** — Confirm tool inputs are complete and valid before execution. Monitor schema validation failures, repair attempts, and retries.

- **Execution path quality** — Detect unnecessary steps, loops, or redundant calls. Compare **steps per task** to an established baseline or budget.

- **Task completion success** — Define success at the **workflow** level (end state and side effects), not only at the final natural-language response.

- **Failure containment** — Confirm unsafe or invalid actions are blocked prior to execution. Measure **blocked versus allowed** actions separately from model refusals.

**Practices**

- Capture full execution traces (decision → tool → result).
- Score both **trajectory quality** and **final outcome** in evaluation harnesses.
- Extend regression datasets with **multi-step workflows**, not only single-turn prompts.

---

## 5. Cost and Performance Tradeoffs

Production AI systems trade **quality**, **speed**, and **money**. Make the tradeoff **explicit** and **measurable**.

| Lever | Typical effect | What to plot |
|-------|----------------|--------------|
| **Model tier** | Smaller/cheaper models: lower cost, sometimes lower quality | Cost per successful task vs. offline score |
| **Max tokens / context** | Higher caps: better on long inputs; higher latency and cost | Latency p95 vs. cost per request |
| **Caching** | Repeat queries: lower cost and latency; stale risk | Cache hit rate, savings, staleness incidents |
| **Routing** | Simple queries to small models, hard ones to large | Routing accuracy, overall cost, error rate |
| **Parallelism / batching** | Throughput vs. complexity and failure modes | Jobs per minute, tail latency |

**Practices**

- Standardize **unit economics**: cost per successful user task, not just cost per token.
- Set **budgets** per environment (dev/stage/prod) and **alerts** on daily spend anomalies.
- Re-evaluate after **every** pricing or model change—vendor updates move the Pareto frontier.

---

## 6. Regression Testing for Model or Prompt Changes

Model swaps and prompt edits are **code changes** with nondeterministic effects. Treat them with the same rigor as a refactor of core business logic.

### 6.1 Pre-merge checklist (minimum)

1. **Offline suite** on the golden + regression sets passes defined thresholds.
2. **Structured output** schemas unchanged or version-bumped with consumers updated.
3. **Safety pack** unchanged or explicitly updated with new expectations.
4. **Diff report**: aggregate deltas vs. baseline (accuracy, latency in shadow, token usage).

### 6.2 Promotion workflow

1. **Baseline** current production config (model, prompt hash, tools).
2. **Candidate** in staging with production-like data (sanitized).
3. **Shadow** optional but recommended for high-risk paths.
4. **Canary** with tight alerts on SLIs and safety metrics.
5. **Full rollout** with feature flag; keep instant rollback to baseline.

### 6.3 Pinning and reproducibility

- Store **prompts** in git; reference by **hash** in telemetry.
- Record **model name and version** (and inference parameters: temperature, top_p, max tokens).
- For nondeterminism, use **seeded** runs in CI where the API allows, or **statistical** comparisons over repeated trials for critical cases.

### 6.4 What to do when a regression appears

- **Stop** the rollout; revert flag or model binding.
- **Add** failing cases to the regression suite.
- **Root-cause**: prompt ambiguity, tool description, retrieval noise, or model capability gap—fix the layer that owns the contract.

---

## 7. Putting It Together: A Minimal Scorecard

Use a single dashboard or report that rolls up:

| Area | Example SLI / gate |
|------|---------------------|
| Offline | Golden pass rate ≥ X%; regression set 100% on blockers |
| Online | p95 latency < Y ms; success rate > Z% |
| Safety | Policy violation rate < V per 1M; invalid action rate = 0 for tier-1 tools |
| Cost | Cost per successful task within budget; token usage within band vs. last week |
| Change control | No promotion without offline + canary criteria met |

Review the scorecard in **release reviews** and after **incidents**. Update thresholds when product expectations or infrastructure change.

---

## 8. Summary

Reliable AI in production requires **layered evaluation**: offline datasets with clear expected outputs, online SLIs with SLOs and safe rollout patterns, safety metrics tied to policy and tooling, explicit cost–quality tradeoffs, and **regression discipline** whenever the model, prompts, or orchestration change. Automate these checks so they run on every relevant change, not only after incidents.

For agent-driven systems, reliability extends beyond final outputs to the correctness of **decisions**, **tool usage**, and **execution paths**.

---

## 9. Agent observability

Production debugging for agents requires correlating **what** ran with **why** it failed. Minimum expectations:

- Trace each step of agent execution (decision, tool call, result).
- Correlate failures to specific steps in the workflow.
- Monitor drift in tool usage patterns over time.
