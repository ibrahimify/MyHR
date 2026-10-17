# MyHR TDK Supervisor Decision Sheet

**NOTHING BELOW IS APPROVED UNTIL A HUMAN RESPONDS. AI agents and automated reviewers cannot approve protocol decisions. The holdout remains locked.**

Date reviewed: __________  Human reviewer: ____________________

## 1. Primary Hypothesis

**Options:** A. Keep the current rule-negative policy-aware comparison. B. Retain the research question but redesign the residual features and scenarios before freeze. C. Make the end-to-end rules-plus-ML cascade the primary claim.

**Evidence:** Independent development found policy AP `0.3621` and raw AP `0.3616`, but the hostile review proved all three policy-specific residual features are constant zero. Literature supports scenario-specific, protected evaluation, not this representation.

**Reviewer objection:** Current results cannot be attributed to policy context. **Recommendation:** B; preserve the current run only as development evidence.

Decision: [ ] Yes, B  [ ] No  [ ] Modify: ______________________________

## 2. Primary Endpoint

**Options:** A. Scenario-level average precision (AP). B. Precision/recall or utility at fixed review capacity. C. Co-primary AP and capacity metrics.

**Evidence:** PR measures suit imbalance and AP evaluates rankings without selecting a test threshold, but AP depends on prevalence. Six current scenarios have no residual positives, making AP undefined; storing zero distorted the mean and interval.

**Reviewer objection:** The current 12-scenario interval is not valid for the proposed eligibility rule. **Recommendation:** A only for predeclared eligible scenarios containing residual positives; report fixed-capacity outcomes as secondary operational evidence with full denominators.

Decision: [ ] Yes  [ ] No  [ ] Modify: _________________________________

## 3. Review-Capacity Rule

**Options:** A. Mandatory deterministic findings plus ML up to a nominal 10% total floor. B. Cap all alerts at 10%, even if rules are dropped. C. Report two queues: all deterministic findings, then an equal fixed ML budget among rule-negative histories.

**Evidence:** Dropping explicit findings is operationally unsafe; a rising floor complicates equal-budget ML comparison. **Reviewer objection:** The current independent artifact does not isolate valid incremental policy information. **Recommendation:** C for scientific comparison and product transparency.

Decision: [ ] Yes  [ ] No  [ ] Modify: _________________________________

## 4. Historical Policy Model

**Options:** A. Apply the current policy to all history. B. Store policy version and effective period only. C. Store policy version, jurisdiction, valid/effective time, recorded/transaction time, recognized service, and correction provenance.

**Evidence:** Current-policy replay flagged `39/72` rare histories and, by source regeneration, `39/39` realized transition histories. Bitemporal literature distinguishes when a fact is true from when it is recorded. **Reviewer objection:** The count is a constructed specification failure, not a real-world prevalence estimate. **Recommendation:** C.

Decision: [ ] Yes  [ ] No  [ ] Modify: _________________________________

## 5. Expert Realism Review

**Options:** A. No expert review. B. Two independent blinded reviewers plus recorded agreement and adjudication. C. One supervisor review only.

**Evidence:** Synthetic fidelity does not establish administrative realism. Human-in-the-loop and reliability research support independent instructions, preserved disagreement, and explicit agreement analysis. **Reviewer objection:** Reviewer qualifications, sample size, and acceptance rule are not yet defined. **Recommendation:** B using the draft 48-case packet, after human approval of assumptions.

Decision: [ ] Yes  [ ] No  [ ] Modify: _________________________________

## 6. Holdout Generation

**Options:** A. Reuse the current development generator. B. Freeze an independently implemented scenario matrix with repeated seeds, positive residual cases, per-record causal truth, and no detector-derived shortcuts. C. Use authorized external data as the only holdout.

**Evidence:** Current source-code independence is useful, but scenarios lack varying policy residual signal, six have zero positives, and mechanism truth is incomplete in artifacts. Recent benchmarking work recommends scenario diversity, repeated random factors, and protected evaluation data. **Recommendation:** B; use lawful external data only as a separately labelled secondary validation if available.

Decision: [ ] Yes  [ ] No  [ ] Modify: _________________________________

**Protocol freeze approved:** [ ] No  [ ] Yes, after recorded modifications

Signature: ______________________________  Date: __________________
