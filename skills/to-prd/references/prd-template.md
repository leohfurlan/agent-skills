# PRD structure and feature handoff

Adapt depth to the product and retain the repository's existing section names where useful. Fill only evidence-backed content; mark pending decisions explicitly.

## Document identity

Title, canonical location, revision/date, status (draft or confirmed), decision owners, source conversation/documents and existing tracker link if any. A revision identifies the requirements consumed by specs; it is not proof of approval.

## Problem Statement

User pain, current workflow, affected audience and evidence. Explain the cost of the problem without inventing measurements.

## Solution and business outcomes

Describe the intended experience, business objectives, success measures and validation approach. Distinguish agreed targets from proposed metrics and unknown baselines.

## Audience and permissions

Roles, workflow behavior, responsibilities, access limits and approvals. Use actual product roles, not a fixed administrator/member hierarchy.

## Scope and feature catalog

Summarize MVP, subsequent increments and exclusions. Catalog:

| ID | Feature / outcome | Actors | Priority / release | Status | Hard prerequisites | Provides / consumes |
| --- | --- | --- | --- | --- | --- | --- |

Use `none` for an intentionally independent feature, and `unresolved` for unknown dependencies. Keep external services separate from internal feature IDs. Status concerns requirements/delivery as labeled; documentation is not proof of implementation.

### Feature detail: Fxx — title

- Outcome and scope.
- Smaller numbered user stories: “As a/an [actor], I want [capability], so that [benefit]”, or the equivalent in the user's language.
- Observable acceptance criteria for success, applicable alternate paths, permissions and errors.
- Provider/consumer expectations in business terms: which feature owns or supplies which concept; which downstream feature uses it.
- Hard prerequisites, optional integrations and external dependencies, each with a reason.
- Exclusions, unresolved decisions, and links to existing technical artifacts.

Stories and acceptance criteria must remain traceable when an existing feature changes. Preserve established IDs; record retired or superseded IDs instead of reusing them.

## Dependency graph and delivery waves

Include a dependency table and a Mermaid graph when it clarifies the relationships. Edges point from prerequisite/provider to dependent/consumer. Clearly distinguish optional relationships.

Validate all referenced feature IDs and the absence of hard cycles before deriving waves. In the absence of resource constraints:

- First wave: features with no unmet hard prerequisites.
- Following waves: features whose hard prerequisites belong to earlier waves.
- Already implemented prerequisites: explicitly record evidence/status instead of scheduling them again.
- Unresolved, missing or cyclic prerequisites: flag blocked scheduling.

For each wave state the feature IDs, entry conditions and shared-contract or migration constraints on parallelism. A contract agreed in advance can permit consumer work against test doubles; that is not integrated readiness.

## Implementation Decisions

Only confirmed constraints or decisions already made: reuse, domain/module responsibilities, architecture and existing contracts. Separate proposals. Detailed implementation belongs in feature specs.

## Testing Decisions

Confirmed observable acceptance approach and public testing seams, relevant existing tests or lack of prior art, and how success will be evaluated. Avoid private implementation coupling.

## Out of Scope

Explicitly excluded capabilities and deferred releases. Deferred does not mean approved for immediate implementation.

## Further Notes

Assumptions, risks, open questions with decision owners when known, pending measurements, and legal/operational validation where relevant.

## Handoff to to-specs

The handoff identifies the canonical PRD revision, selected feature ID(s), acceptance criteria, prerequisite IDs and provider/consumer expectations. Specifying a feature does not authorize changing its providers or implementing its consumers. Existing specs and `contract.md` files remain authoritative for their technical interfaces unless a coordinated revision is approved.
