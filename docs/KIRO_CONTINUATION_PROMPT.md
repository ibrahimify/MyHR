# Kiro Continuation Prompt

Open this repository and continue the MyHR TDK research on branch `research/policy-aware-anomaly`.

First read `AGENTS.md`, then follow its resume procedure. Read `docs/TDK_AUTONOMOUS_RESEARCH_ROADMAP.md`, `docs/TDK_EXPERIMENT_PROTOCOL.md`, and `docs/TDK_DATA_TEST_CORRECTNESS_AUDIT_2026-10-29.md`. Confirm branch, clean worktree, draft PR #1, issues, and CI before editing.

Hard rules: keep the final holdout locked; never generate, inspect, score, or unlock it; do not change frozen research decisions silently; preserve negative results; use no paid services or private employee data; keep PR #1 draft and unmerged. Treat the latest pushed commit as the verified checkpoint. It corrects synthetic mechanisms, bitemporal visibility, invariant-only primary filtering, equal-budget evaluation, duplicate partitioning/missing-value behavior, and artifact auditing. Its full suite passed 181 tests.

Next, run a clean-revision development/validation artifact and audit it. Investigate failures instead of bypassing them. Then address the documented remaining gaps only: latent-person-first duplicate generation, explicit hard nonduplicates, explicit late-correction scenarios, runtime/memory reporting, and independent verification of the new artifact. Keep counts and denominators explicit. Update tests, the correctness audit, handover, and roadmap with evidence. Commit and push verified increments; do not merge, close the scientific blocker, or claim superiority.

Several Codex subagents existed only as independent read-only reviewers to challenge leakage, circularity, denominators, and documentation/code mismatches. Their existence is not approval. Re-check any reported finding against code and artifacts before acting.
