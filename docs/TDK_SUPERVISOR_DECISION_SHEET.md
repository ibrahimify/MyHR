# MyHR TDK Supervisor Decision Sheet

**SUPERVISOR DECISIONS RECORDED 29 OCTOBER 2026. APPROVED FOR IMPLEMENTATION. PROTOCOL FREEZE PENDING. HOLDOUT LOCKED.**

Decision source: supervisor answers relayed by Muhammad Ibrahim Shoeb. Full record: `TDK_SUPERVISOR_DECISIONS_2026-10-29.md`.

## 1. Primary Hypothesis

**Options:** A. Keep the current residual comparison. B. Redesign residual features and scenarios. C. Make the end-to-end rules-plus-ML queue primary.

**Evidence/objection:** All three policy-specific residual features are constant zero, so current AP differences cannot be attributed to policy context.

**Decision:** Retain residual raw-versus-policy-aware ML as primary, restrict filtering to invariant contradictions, and evaluate the complete workflow secondarily. Preserve current runs as development evidence.

## 2. Primary Endpoint

**Options:** A. Scenario-level AP. B. Fixed-capacity precision/recall or utility. C. Co-primary endpoints.

**Evidence/objection:** AP suits imbalanced ranking but depends on prevalence. Six scenarios have no residual positives and were incorrectly assigned AP zero.

**Decision:** Recall at fixed review capacity is primary. Report precision, total false alerts, and rare-legitimate false-alert rates alongside it. AP is secondary with predeclared zero-positive handling.

## 3. Review Capacity

**Options:** A. Mandatory rules plus ML to a nominal 10% floor. B. Cap all alerts at 10%. C. Report all deterministic findings, then an equal fixed ML budget among rule-negative histories.

**Evidence/objection:** Dropping explicit findings is unsafe, while a rising capacity floor prevents a clean equal-budget ML comparison.

**Decision:** C. Preserve identical invariant findings, then allocate equal additional ML review capacity on the same residual records. Report rule-only and complete queues separately.

## 4. Historical Policy Model

**Options:** A. Apply current policy to all history. B. Store version and effective period. C. Also store jurisdiction, effective time, recorded time, recognized service, and correction provenance.

**Evidence/objection:** Current-policy replay flagged `39/72` rare histories; source regeneration found `39/39` realized transition histories flagged. This proves a constructed specification failure, not real-world prevalence.

**Decision:** C. Implement policy versions, recognized service, correction provenance, effective time, and recorded time.

## 5. Expert Realism Review

**Options:** A. None. B. Two independent blinded reviewers with agreement and adjudication. C. One supervisor review.

**Evidence/objection:** Synthetic correctness does not establish realism. Reviewer qualifications, sample size, and acceptance criteria remain undecided.

**Decision:** B. Use two independent blinded reviewers with complementary expertise, preserve initial judgments, report agreement, and adjudicate from documented evidence while retaining ambiguity.

## 6. Holdout Design

**Options:** A. Reuse the development generator. B. Freeze a conceptually independent matrix with repeated seeds and per-record causal truth. C. Use authorized external data only.

**Evidence/objection:** Current scenarios have constant policy residuals, six zero-positive cases, and incomplete truth in the existing artifact.

**Decision:** B. Freeze an independent repeated-seed matrix covering policy transitions, lawful exceptions, administrative errors, and populations, with causal truth outside model inputs.

**Protocol freeze:** Not granted. It requires completed implementation, verification, exact dependency and source freeze, and a separate dated approval.
