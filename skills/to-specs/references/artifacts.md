# Feature artifact requirements

Use the project's layout if one exists; otherwise keep the three artifacts together in `docs/features/Fxx-short-name/`. Adapt depth to the feature; use “not applicable” with a reason for irrelevant sections instead of inventing HTTP endpoints, databases or infrastructure.

## Common identity and traceability

Each artifact identifies the feature ID/title, canonical PRD and revision, status (draft/confirmed), and links to its siblings. Identify relevant provider/consumer feature IDs and existing contract paths. Use repository-relative links that resolve from the document. Record source revisions or hashes only when actually known; document absence.

Track approval explicitly where known; writing an artifact cannot approve it. A change in upstream requirements or contract invalidates affected assumptions until reviewed.

## spec.md — technical specification

### Scope and evidence

Selected feature's outcomes and acceptance criteria, exclusions, inspected repository state, existing modules to reuse and changes needed. Cite actual files/configuration as evidence; label proposed paths. Preserve confirmed stack and ADR constraints, and explain any agreed deviations.

### Behavioral requirements and falsifiability

Describe what the system must do through preconditions, inputs or triggers, observable outcomes and business constraints. Define entities, identifiers and ownership, relationships, invariants, lifecycle/state transitions, authorization and tenant boundaries where present. State what must always remain true and under which conditions. Link authoritative input/output and validation definitions in `contract.md`.

Keep these requirements independent of implementation choices: classes, algorithms, storage mechanisms and code belong under technical decisions. Preserve mandated technical constraints from the PRD or ADRs there with their source; an observable public interface remains part of the behavior/contract.

Every behavioral requirement and guarantee must have an observable pass/fail condition. Replace vague claims such as "fast", "robust" or "performant" with explicit outcomes. For quantitative requirements, specify the metric, unit, threshold and measurement conditions (relevant workload/concurrency, data volume, environment and observation window). Derive targets from confirmed requirements or propose them for approval; never invent an accepted threshold. Use deterministic outcomes for qualitative rules rather than forcing arbitrary numbers. A missing required target or expected outcome is a blocking decision, not a satisfied requirement.

### Named edge cases

Systematically review the feature's inputs, invariants, state transitions and interaction boundaries for edge cases. Consider missing/null/empty values; zero, negative and invalid values; minimum/maximum and just-outside limits; and, where applicable, simultaneous requests, duplicate delivery, out-of-order operations, timeouts and partial failures. Select cases from actual domain constraints and interfaces; record why a reviewed category is not applicable instead of expanding scope.

Give each applicable case a stable name or local ID and record:

| Case | Preconditions / input or concurrent actions | Expected observable outcome and invariant | Verification / linked requirement or contract |
| --- | --- | --- | --- |

State expected acceptance or rejection and relevant side effects or recovery, not merely "handle gracefully". Reference the canonical contract for exact error/field definitions. An unresolved expected outcome remains an explicit decision gap.

### Technical decisions and architecture

For consequential decisions, give alternatives, chosen tradeoff and status. Explain module responsibilities and boundaries, keeping deterministic business rules separate from infrastructure and optional agents where the product requires it. Link each consequential choice to the behavior or sourced constraint it supports.

Describe persistence changes, transaction/concurrency mechanisms and migration/backfill/rollback needs where applicable. Use existing representations and naming. Keep observable concurrency, failure and recovery guarantees in the behavioral requirements or authoritative contract; distinguish guarantees from eventual consistency and pending design.

Include a high-level Mermaid sequence diagram for the principal flow, showing actual provider/consumer calls and relevant failure/approval paths. For a feature without an interaction sequence, use the appropriate small diagram and explain why. A diagram does not replace a contract.

### Regression and acceptance strategy

Map every feature acceptance criterion, behavioral requirement, invariant and applicable named edge case to a public behavior, test seam and proposed evidence with an explicit pass/fail condition. Several items may share one scenario; preserve traceability without duplicating tests. Reuse existing tests and fixtures where possible. Include relevant errors, permissions, idempotency, compatibility and cross-feature integration. Prefer the highest practical observable seam and the smallest useful set; avoid tests tied to private implementation.

For a consumed provider contract, identify consumer expectations, provider conformance checks, fixture provenance and a real integration scenario. Test doubles must reflect the agreed contract and cannot demonstrate a provider is implemented.

### Quality gates

| Gate | Configuration evidence | Command and cwd | Prerequisites / scope | Policy | Execution evidence |
| --- | --- | --- | --- | --- | --- |

Policy: required by existing project rules, newly approved, or proposed. Execution evidence: not run, passed, failed, or blocked with reason and actual output summary when run. An unavailable architecture validator is a proposed gap, not a fabricated command. Separate pre-existing failures from regressions and record the decision needed rather than silently weakening a gate.

### Risks and readiness

Remaining questions, compatibility/migration risks, operational considerations and conditions needed before implementation or integration. Avoid unrelated hardening scope.

## contract.md — authoritative feature boundary

Keep this compact and precise enough to serve implementation and test agents. Define interfaces once here; the spec links to them.

### Identity and ownership

Feature ID, contract revision, draft/confirmed status, provider/consumer owners when known, relevant PRD/spec revisions, and compatibility expectations. A contract revision is separate from a software package version.

### Provider/consumer map

| Provider feature or external system | Consumer feature | Interface / capability | Data and ID owner | Direction / dependency | Contract reference and readiness |
| --- | --- | --- | --- | --- | --- |

Record both what this feature provides and what it consumes. Link prerequisite contracts without copying their definitions. Mark provider capability as implemented (with evidence), agreed but not implemented, or unresolved. For provider-owned IDs, state where the consumer obtains them and how existence/access are checked.

### Interface definitions

For HTTP boundaries specify method/path, authentication and authorization, request/response fields and types, required/optional/nullability rules, status/error shapes, validation, idempotency and pagination/versioning where relevant.

For internal or event boundaries use the actual equivalent: operation/event name, payload/result, invariants, identity ownership, authorization context and error semantics. Do not introduce HTTP solely to fill a template.

For applicable asynchronous or stateful operations, define retry, ordering, duplicate delivery and consistency expectations. Include representative valid and invalid examples when they remove ambiguity; use synthetic data, not credentials or production personal data.

### Compatibility and contract tests

State producer guarantees, consumer expectations, observable acceptance cases and failure cases. Reference canonical schemas if they exist. Explain which tests demonstrate provider conformance, consumer compatibility and cross-feature behavior; test results remain unknown until run.

Identify breaking changes, impacted consumers, migration/version negotiation and rollout coordination if relevant. Where another feature owns an interface, propose a change for agreement rather than silently editing its contract.

## plan.md — high-level execution plan

Organize a small set of meaningful phases, each with an outcome, dependencies and verification checkpoint. A useful shape is:

1. Resolve blocking decisions and align provider/consumer contracts.
2. Extend or reuse the domain/application behavior and data boundaries.
3. Integrate adapters and user-facing flows.
4. Verify contracts, regressions and the end-to-end acceptance scenario.
5. Prepare applicable migration/rollout and operational evidence.

Adapt this outline to the feature; do not mandate unnecessary layers. Use the repository's public seams and confirmed gates. Keep implementation choices open within the agreed contracts.

Show feature-level prerequisites and broad waves where useful. Parallel candidates must have agreed interfaces and no unresolved shared ownership or conflicting migrations. Consumer development against a test double can begin only with an agreed contract, and still needs a later provider integration checkpoint. Do not place dependent integration in a wave before its provider is ready.

Finish with a definition of done tied to acceptance criteria, contract compatibility and actual required gates. Distinguish specification readiness, implementation completion and integrated readiness. Do not claim any of these solely because the plan exists.
