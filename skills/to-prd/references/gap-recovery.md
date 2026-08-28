# Focused gap recovery and authorized publication

Read when missing information blocks progress or the user requests issue-tracker publication.

## Recover a blocking gap

1. Check the conversation, repository instructions and available read-only tools before asking. Separate required decisions from optional notes.
2. Announce focused grilling. For choices, requirements or setup, use the underlying `grilling` skill if available. Add `domain-modeling` only when resolving terminology or an architectural decision. The explicit-only `grill-me` and `grill-with-docs` wrappers are not automatic dependencies. Use the environment's actual skill-reading mechanism, not a presumed tool named Skill. If unavailable, disclose it and continue with focused questions.
3. Present evidence and a recommendation, wait for the user's choices, and confirm the resulting understanding. Preserve settled decisions; do not silently accept recommendations.
4. Complete necessary repository configuration from confirmed answers. Reuse the existing layout; otherwise propose `docs/agents/issue-tracker.md` for destination/access and `docs/agents/triage-labels.md` for role-to-label mapping. Show proposed changes before writing and preserve unrelated settings. If a pointer is needed, use the existing instruction file; if none exists, ask which to create. Keep credentials out. Configuration alone does not warrant an ADR.
5. Verify configuration with read-only tools. If access, authentication or a missing label blocks progress, identify the exact user action or authorization required. Do not create external resources without authorization.
6. Resume the interrupted PRD/spec work in the same conversation, retaining answers and drafts. Completing setup is not completing the requested document. The setup helper is optional, not a mandatory manual detour.

## Publish

- Resolve tracker, exact repository/project, intended new or existing issue, and label mapped to `ready-for-agent`. Read the project's instructions and configuration; common locations are `docs/agents/issue-tracker.md` and `docs/agents/triage-labels.md`.
- Missing publication configuration does not block local drafting. A request to draft locally does not authorize external changes.
- Use only the destination and scope the user authorized. Confirm unresolved requirements and testing seams before publishing as ready.
- For uncertain publication results, inspect the destination before retrying to avoid duplicates.
- Verify the actual issue body and label, return the link, and distinguish body success from labeling failure or unavailable verification.
