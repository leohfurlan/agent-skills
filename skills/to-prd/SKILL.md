---
name: to-prd
description: Interview about product needs and turn decisions into PRD.md with stable feature IDs, acceptance criteria, dependencies, and development waves. Use to create or revise a product requirements document; publish only when requested.
---

# Product requirements writer

Turn the user's business vision into an actionable product document. Interview to resolve missing product decisions, using existing conversation and repository evidence first. Preserve confirmed choices; separate approved requirements, proposals, assumptions, and open questions. Write in the user's language.

This skill produces product requirements, not implementation code. The handoff to `to-specs` is one identified feature and its dependencies.

## 1. Establish context

Read project instructions, the canonical PRD if present, domain glossary and relevant ADRs. Follow the repository's documented layout rather than assuming particular files exist. Inspect enough existing product behavior to distinguish reuse from proposed work; leave detailed technical discovery to `to-specs`.

Resolve the output from the user's request or repository convention; otherwise use `docs/PRD.md`. Maintain one canonical PRD and preserve unrelated content. A request for an in-chat draft does not authorize file writes or publication.

## 2. Interview and iterate

Use known answers to build a short decision inventory. Ask focused questions at the current unresolved decision frontier, recommend an option with its tradeoff, and wait for the user's answer before deciding dependent questions. Cover:

- User pains, existing workflows, workarounds, and desired outcomes.
- Business goals, success measures, budget and operational constraints.
- Audience roles and behavior: administrators, members, external collaborators, their permissions and approval responsibilities where relevant.
- MVP boundaries, exclusions, priority, alternate paths and failure cases.
- Adoption, delivery and validation assumptions that materially affect scope.

Ask only what remains unresolved; do not replay an interview when the conversation already supplies the answers. After each consequential answer, update the understanding and continue. Optional unknowns may remain in Further Notes; unresolved scope or approval decisions block a final PRD, not a clearly marked draft.

Before finalizing, confirm the resulting scope, acceptance approach and public testing seams unless already explicitly confirmed. Prefer existing seams and the smallest practical set exercising observable outcomes. Keep detailed test design for specs.

When a gap requires deeper grilling, terminology work or missing publication setup, read [gap recovery](references/gap-recovery.md). Resume this workflow after resolving it.

## 3. Catalog features and dependencies

Read [the PRD structure](references/prd-template.md) when drafting or revising the document.

Assign each feature a unique sequential ID starting at `F01`. Allocate new IDs after the highest previously allocated ID; keep IDs stable across revisions and never recycle retired IDs. For a legacy PRD without IDs, map existing requirements to features and preserve their meaning; do not silently replace an established identifier scheme. Record supersession when splitting or merging features.

For each feature, capture actors, outcome, smaller user stories, observable acceptance criteria, scope, priority, dependencies and what it provides or consumes. Use numbered stories associated with their feature; do not inflate the story count with duplicates or unsupported scope.

Distinguish hard prerequisites from optional integrations and external dependencies. Give every dependency a reason and direction, provider → consumer. Validate that all internal IDs exist and hard prerequisites have no self-dependencies or cycles; surface conflicts for resolution rather than inventing a sequence.

Derive development waves from hard dependencies. Features in a wave are only candidates for parallel work: shared contracts, shared migrations or unresolved ownership can still require sequencing. Explain those constraints. Do not infer permission to launch agents or implementation work from a wave diagram.

## 4. Write and hand off

Write `PRD.md` using the reference structure. Keep confirmed architectural constraints and testing decisions, but leave new HTTP schemas, table definitions and implementation plans to `to-specs`. Use domain responsibilities rather than speculative file paths or code. A decision-rich prototype snippet may be retained with provenance.

Each feature must be selectable by ID for technical specification, with its prerequisite features and business-level provider/consumer expectations visible. Link existing specs/contracts if present; do not claim future artifacts exist. Technical details in a contract may refine the PRD but cannot silently change its scope.

Before reporting completion, check story coverage, acceptance criteria, ID uniqueness and stability, dependency references, acyclicity, wave ordering, unresolved decisions, and consistency with prior approved requirements. Report whether the result is a draft or confirmed requirements. Return the actual local path or draft.

## 5. Publish only when authorized

For a publication request, read [publication and gap recovery](references/gap-recovery.md). Verify the exact destination and ready-for-agent label mapping, then create or update the intended issue. Preserve local/remote consistency within the authorized scope and verify the body and label after writing.

A local drafting request, skill invocation or missing tracker configuration is not permission to publish. Do not publish an unconfirmed draft as ready for implementation. Report partial publication outcomes accurately.
