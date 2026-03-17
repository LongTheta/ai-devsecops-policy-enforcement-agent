# Policy Model

## Structure

Policies are YAML files with:

- **name** – Policy set name
- **description** – Optional description
- **rules** – List of rule objects

Each rule:

| Field | Type | Description |
|-------|------|--------------|
| id | string | Unique rule ID (e.g. no_plaintext_secrets) |
| name | string | Human-readable name |
| description | string | Optional |
| severity | string | critical, high, medium, low, info |
| category | string | secrets, supply_chain, governance, policy, etc. |
| enabled | bool | If false, rule is not evaluated |
| config | object | Optional key-value config for the rule |

## Built-in rule IDs

The pipeline analyzer currently reacts to:

- **no_plaintext_secrets** – Fails if plaintext secret patterns are detected
- **require_sbom** – Warns if no SBOM/provenance step is found

Other rules (require_pinned_pipeline_dependencies, require_manual_promotion_gate, etc.) are loaded and reported in policy_results; full evaluation can be extended in the analyzer.

## Example

See `policies/default.yaml`, `policies/fedramp-moderate.yaml`, and `policies/supply-chain-baseline.yaml`.

## Verdict

Verdict is computed from **findings**, not directly from policy pass/fail:

- **fail** – Any finding with severity critical or high
- **pass_with_warnings** – Any medium or low (no critical/high)
- **pass** – No findings or only info

Policy rules that are not satisfied produce findings; those findings drive the verdict.

---

## Related docs

- [COMPONENTS.md](COMPONENTS.md) – Detailed component reference, including policies/loader
