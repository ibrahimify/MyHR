# MyHR Research Working Rules

These instructions apply to repository work on the TDK research branch.

## Scientific boundaries

- Treat `docs/TDK_EXPERIMENT_PROTOCOL.md` as frozen for the completed v2 evaluation.
- The v2 holdout attempt has been consumed. Never rerun it, tune against it, or alter its preserved result. A future holdout requires a separately versioned protocol, seed family, authorization, and ledger.
- Do not silently change hypotheses, endpoints, scenario definitions, or evaluation decisions. Record proposed changes separately for supervisor approval.
- Preserve negative and inconclusive findings. Do not select favorable seeds or optimize against inspected test outputs.
- Keep progression anomaly detection and duplicate-record detection as separate evaluation tasks.
- Anomaly scores support human review and must never trigger automatic personnel decisions.
- Do not use private employee data, paid services, or credentials without explicit authorization.
- When scientific literature informs work, use the repository `researcher` skill at `.codex/skills/researcher/SKILL.md` and update the centralized bibliography, citation provenance, and claim-evidence ledger in the same change.
- The Research & Citation Specialist is the sixth research role. It verifies identifiers and legally accessible evidence, preserves provenance, and deduplicates citations; it cannot approve protocol decisions.

## Repository permissions (updated 2026-10-31)

The author has authorized routine engineering and repository maintenance,
including branch management, commits, and normal pushes. This authorization is
strictly operational. It does NOT authorize automatic personnel decisions from
anomaly scores, invented expert evidence, post-hoc tuning, or a second v2
holdout run. New protocols and protected evaluations require a new explicit
authorization record.

The three permanent branches are `master` (Project Lab submission), `thesis`
(verified working application), and `research` (research plus working app).
Never force-push, destructively reset, or `git clean` to manufacture
cleanliness; preserve work with tags and bundles first.

## Resume procedure

1. Read `docs/TDK_RESEARCH_ROADMAP.md`.
2. Read `docs/TDK_EXPERIMENT_PROTOCOL.md` and the latest research report named by the roadmap.
3. Confirm the current branch, worktree status, open PR, relevant issues, and CI status.
4. Continue the highest-priority unblocked roadmap task.
5. Update the roadmap with evidence, limitations, validation, and outcome before committing.

## Verification

- Use scenario seeds as the independent units for statistical comparisons.
- Report counts with denominators and distinguish scenario-mean metrics from pooled metrics.
- Compare ML representations at equal review budgets and report incremental value beyond deterministic rules.
- Record source revision, configuration, dependencies, seeds, and checksums for experiment artifacts.
- Merge only reviewed changes with passing required checks; do not force-push.
- Before recommending a literature-informed change for human review, the Independent Auditor must verify citation identity, claim scope, evidence locators, conflicts, and reproducibility with `scripts/verify_tdk_citations.py --require-local-artifact`.

