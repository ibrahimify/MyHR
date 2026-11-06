# TDK Repository Morning Approval Gate

This file prepares repository maintenance but does not authorize a merge, issue closure, branch deletion, protocol decision, or holdout access.

## Pull Request

- PR #1 must remain draft until Ibrahim reviews the supervisor package and explicitly authorizes the merge.
- Before readiness, rerun the full local suite, citation verification, artifact audits, document build, and GitHub CI.
- The PR description must preserve the constant-feature failure, locked holdout, and pending Issue #10 decisions.

## Issue Disposition

| Issue | Prepared disposition | Condition |
| ---: | --- | --- |
| #2 | Close as implemented | Schema, taxonomy, docs, and tests remain linked in the closure comment |
| #3 | Close as implemented | Deterministic generator, partitions, metadata, and tests verified |
| #4 | Close as implemented | Explainable checks and clean/error/rare-case tests verified |
| #5 | Close as implemented with limitation | Constant residual-feature failure remains documented |
| #6 | Keep open or rescope | Central scientific comparison is not valid yet |
| #7 | Close implementation slice, open later validation task if needed | Current duplicate results remain preliminary |
| #8 | Keep open or rescope | Paper figures are generated, but final confirmatory figures do not exist |
| #9 | Close as completed audit | Thesis and TDK boundaries are documented |
| #10 | Keep open | Protocol redesign and approval are genuinely unresolved |
| #11 | Close implementation slice or keep optional service note | Free workflow works; anonymous Semantic Scholar is rate-limited |

No issue should be closed merely to produce a zero-open-issue appearance.

## Branches

- Keep `master`, `thesis`, `thesis-final-polish`, and `research/policy-aware-anomaly` until the approved merge path is complete.
- Delete `maintenance/research-repository-hygiene` only after confirming its merge commit is reachable from the research branch and remote.
- Inspect `claude/charming-jemison-f93721` for unique commits before any deletion.
- Never delete a branch with unique or unreviewed work.

## Human Checklist

- [ ] Read the professor package `README.md`.
- [ ] Inspect the complete PDF.
- [ ] Review the verification report and page count.
- [ ] Confirm PR #1 still describes the science honestly.
- [ ] Approve or reject the prepared issue dispositions.
- [ ] Approve or reject the PR merge.
- [ ] Approve or reject each branch deletion separately.

