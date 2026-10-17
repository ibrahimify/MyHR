# MyHR TDK Supervisor Decision Sheet

**NOTHING IS APPROVED UNTIL A HUMAN RESPONDS. AI agents cannot approve protocol decisions. The holdout remains locked.**

Date: __________  Human reviewer: ____________________

## 1. Primary Hypothesis

**Options:** A. Keep the current residual comparison. B. Redesign residual features and scenarios. C. Make the end-to-end rules-plus-ML queue primary.

**Evidence/objection:** All three policy-specific residual features are constant zero, so current AP differences cannot be attributed to policy context.

**Recommendation:** B. Preserve the current run only as development evidence.

[ ] Yes, B  [ ] No  [ ] Modify: _________________________________

## 2. Primary Endpoint

**Options:** A. Scenario-level AP. B. Fixed-capacity precision/recall or utility. C. Co-primary endpoints.

**Evidence/objection:** AP suits imbalanced ranking but depends on prevalence. Six scenarios have no residual positives and were incorrectly assigned AP zero.

**Recommendation:** A only when scenario families are predeclared to contain residual positives by construction. Never select or exclude scenarios after inspection. Otherwise choose B or redefine the estimand.

[ ] Yes  [ ] No  [ ] Modify: ____________________________________

## 3. Review Capacity

**Options:** A. Mandatory rules plus ML to a nominal 10% floor. B. Cap all alerts at 10%. C. Report all deterministic findings, then an equal fixed ML budget among rule-negative histories.

**Evidence/objection:** Dropping explicit findings is unsafe, while a rising capacity floor prevents a clean equal-budget ML comparison.

**Recommendation:** C.

[ ] Yes  [ ] No  [ ] Modify: ____________________________________

## 4. Historical Policy Model

**Options:** A. Apply current policy to all history. B. Store version and effective period. C. Also store jurisdiction, effective time, recorded time, recognized service, and correction provenance.

**Evidence/objection:** Current-policy replay flagged `39/72` rare histories; source regeneration found `39/39` realized transition histories flagged. This proves a constructed specification failure, not real-world prevalence.

**Recommendation:** C.

[ ] Yes  [ ] No  [ ] Modify: ____________________________________

## 5. Expert Realism Review

**Options:** A. None. B. Two independent blinded reviewers with agreement and adjudication. C. One supervisor review.

**Evidence/objection:** Synthetic correctness does not establish realism. Reviewer qualifications, sample size, and acceptance criteria remain undecided.

**Recommendation:** B, using the draft packet only after human approval.

[ ] Yes  [ ] No  [ ] Modify: ____________________________________

## 6. Holdout Design

**Options:** A. Reuse the development generator. B. Freeze a conceptually independent matrix with repeated seeds and per-record causal truth. C. Use authorized external data only.

**Evidence/objection:** Current scenarios have constant policy residuals, six zero-positive cases, and incomplete truth in the existing artifact.

**Recommendation:** B with predeclared residual-positive families. Use lawful external data only as secondary validation.

[ ] Yes  [ ] No  [ ] Modify: ____________________________________

**Protocol freeze:** [ ] No  [ ] Yes, after recorded modifications

Signature: ______________________________  Date: __________________
