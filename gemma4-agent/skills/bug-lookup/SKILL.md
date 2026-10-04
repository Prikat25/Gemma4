---
name: bug-lookup
description: Performs issue analysis, flow-based bug localization, and historical local Bug DB lookup (`issue_analysis`, `bug_localization`, `bug_lookup`, `similar_fix_lookup`).
---

# Bug Lookup & Localization Skill

## Capabilities
- `issue_analysis`: Extracts symptoms, domain entities, and expected vs actual behavior from the issue text.
- `bug_localization`: Scores repository functions by lexical overlap, flow graph reachability, and failing test coverage.
- `bug_lookup` & `similar_fix_lookup`: Retrieves top-K historical bug records from `resources/seed_bugs.json`.

## Invariant
**Similarity is evidence, not truth.** Returned records include a mandatory `warning: "SIMILARITY_IS_EVIDENCE_NOT_TRUTH"` metadata flag.
