# TDK Supervisor Methodology Decisions

Date recorded: 29 October 2026

Decision source: these decisions were recorded as the project author's (Muhammad
Ibrahim Shoeb) own implementation-authorization decisions. The second external
audit (2026-10-30) correctly noted that the earlier phrasing "supervisor answers
relayed by..." implied an independent supervisor endorsement that is not
separately documented. Unless and until a distinct supervisor communication is
recorded, these are the author's authorizations to IMPLEMENT the methodology.
They remain subject to the scientific boundaries below: they do not freeze the
protocol or unlock the holdout, which require a separately documented approval.

Status: **APPROVED FOR IMPLEMENTATION (AUTHOR-AUTHORIZED). PROTOCOL NOT YET FROZEN. HOLDOUT LOCKED.**

These decisions authorize the methodology changes below. They do not certify that the implementation is complete, freeze a source revision, or authorize holdout generation or evaluation.

## 1. Primary Experiment

Retain the raw-versus-policy-aware residual ML comparison as primary. Restrict the deterministic filter for that comparison to invariant contradictions so it cannot consume the policy signal intended for ML. Evaluate the complete rules-plus-ML workflow secondarily.

The existing development harness correctly exposed the architectural conflict before it could support a misleading claim. Existing inspected artifacts remain development evidence and are not reclassified as confirmatory evidence.

## 2. Primary Metric

Use recall at a fixed review capacity as the primary endpoint. Report precision, total false alerts, and rare-legitimate false-alert rates alongside it.

Average Precision remains secondary. Zero-positive scenarios must be reported explicitly, and their treatment must be specified before evaluation.

## 3. Equal Review Capacity

Apply the same invariant checks to raw and policy-aware pipelines and preserve their findings. On the same remaining records, allocate an identical additional ML review budget to both representations.

Report the invariant-rules-only baseline and the complete review queue separately so any difference can be attributed to ML rather than unequal review capacity.

## 4. Historical Policy Contract

Adopt a bitemporal contract that records when policies and administrative facts were effective and when the system learned them. Also record policy versions, recognized service, and correction provenance.

The `39/72` historical false-alert result motivates this requirement. Exact transition-mechanism attribution remains qualified because the stored artifact does not preserve the realized mechanism per record.

## 5. Synthetic-Case Review

Use two independent reviewers with complementary HR-policy and information-systems expertise. Blind both reviewers to generated labels and model scores.

Preserve initial judgments, report agreement, and adjudicate disagreements against documented policy evidence. Retain genuinely ambiguous cases rather than forcing agreement.

## 6. Final Holdout Design

Freeze an independently specified matrix covering policy transitions, lawful exceptions, administrative errors, populations, and repeated seeds. Keep causal truth outside model inputs.

After implementation, verification, and a complete protocol freeze, execute the holdout once at the frozen revision and preserve every result. These decisions do not by themselves unlock that run.

## Remaining Approval Gate

Before holdout execution, the repository must contain and verify:

1. the implemented invariant-contradiction boundary;
2. equal-capacity raw and policy-aware residual pipelines;
3. the bitemporal policy and fact contract;
4. the independently specified scenario matrix and causal truth contract;
5. the predeclared zero-positive-scenario treatment;
6. reviewer identities, qualifications, sampling, agreement, and adjudication procedures;
7. exact dependencies, source revision, tests, analysis code, and write-once artifact configuration;
8. an explicit dated protocol-freeze approval.

Until all eight conditions are satisfied, `docs/TDK_EXPERIMENT_PROTOCOL.md` remains draft and the final holdout remains locked.
