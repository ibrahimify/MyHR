# MyHR Research Working Rules

These instructions apply to repository work on the TDK research branch.

## Scientific boundaries

- Treat `docs/TDK_EXPERIMENT_PROTOCOL.md` as draft and the final holdout as locked.
- Never generate, inspect, score, or unlock a holdout without explicit supervisor approval and a frozen protocol.
- Do not silently change hypotheses, endpoints, scenario definitions, or evaluation decisions. Record proposed changes separately for supervisor approval.
- Preserve negative and inconclusive findings. Do not select favorable seeds or optimize against inspected test outputs.
- Keep progression anomaly detection and duplicate-record detection as separate evaluation tasks.
- Anomaly scores support human review and must never trigger automatic personnel decisions.
- Do not use private employee data, paid services, or credentials without explicit authorization.
- When scientific literature informs work, use the repository `researcher` skill at `.codex/skills/researcher/SKILL.md` and update the centralized bibliography, citation provenance, and claim-evidence ledger in the same change.
- The Research & Citation Specialist is the sixth research role. It verifies identifiers and legally accessible evidence, preserves provenance, and deduplicates citations; it cannot approve protocol decisions.

## Resume procedure

1. Read `docs/TDK_AUTONOMOUS_RESEARCH_ROADMAP.md`.
2. Read `docs/TDK_EXPERIMENT_PROTOCOL.md` and the latest research report named by the roadmap.
3. Confirm the current branch, worktree status, open PR, relevant issues, and CI status.
4. Continue the highest-priority unblocked roadmap task.
5. Update the roadmap with evidence, limitations, validation, and outcome before committing.

## Verification

- Use scenario seeds as the independent units for statistical comparisons.
- Report counts with denominators and distinguish scenario-mean metrics from pooled metrics.
- Compare ML representations at equal review budgets and report incremental value beyond deterministic rules.
- Record source revision, configuration, dependencies, seeds, and checksums for experiment artifacts.
- Keep the draft research PR open. Do not merge it without user authorization.
- Before recommending a literature-informed change for human review, the Independent Auditor must verify citation identity, claim scope, evidence locators, conflicts, and reproducibility with `scripts/verify_tdk_citations.py --require-local-artifact`.

