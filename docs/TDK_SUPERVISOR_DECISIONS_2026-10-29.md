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

## Author Decision Addendum - 30 October 2026

Decision source: Muhammad Ibrahim Shoeb. These are author decisions for
implementation and protocol preparation. They are not represented as an
independent supervisor signature, do not freeze the protocol, and do not unlock
the holdout.

### A. Scenario semantics - approved with constraints

Lawful correction histories and their eligibility requirements are accepted.
Every generated correction must retain the original record, identify the exact
record it supersedes, remain visible in the audit history, and produce a lawful
effective history. A scenario may be instantiated only when its employee and
population satisfy the mechanism's preconditions. Concrete examples must be
reviewed before protocol freeze.

The approved population-pattern compatibility boundary is:

| Population | Compatible rare-legitimate patterns | Exclusion |
| --- | --- | --- |
| Stable administration | grandfathered policy, recognized prior service, delayed bulk recording, late correction, policy transition | none of the five patterns is excluded when record-level eligibility holds |
| Rapid expansion | grandfathered policy, recognized prior service, delayed bulk recording, late correction | policy transition is excluded because the 2021-2025 hire window cannot reliably support a lawful promotion in the legacy epoch |
| Merger or migration | grandfathered policy, recognized prior service, delayed bulk recording, late correction, policy transition | none of the five patterns is excluded when record-level eligibility holds |

Across all three populations, `late_correction` requires a progression-track
employee with an existing promotion. `policy_transition` additionally requires
an existing promotion and `hire date + 30 months <= 31 December 2022`.
Grandfathering requires the entitlement evidence defined below. Recognized prior
service requires an evidence-bearing service credit linked to the relevant
decision. Delayed bulk recording may change recorded time but not effective
time. All anomaly mechanisms remain eligible only when their required source
events exist. These rules approve compatibility and eligibility, not the current
12-scenario frequency allocation or a final holdout matrix.

### B. Employee-linked entitlement evidence - approved

A grandfathering or comparable exception is valid only when an entitlement
evidence record links all of the following: the employee, applicable policy ID
and version, relevant administrative event, evidence reference, and the time by
which the evidence was known. A generated label or policy identity alone is not
proof of entitlement.

### C. Decision-time and later-review views - approved

The experiment must distinguish:

- `known_then`: facts effective by the decision date and recorded by that date,
  using policy knowledge available by that date;
- `later_review`: the same effective decision horizon, while admitting facts,
  corrections, and policy amendments recorded by the later review date.

Both views must be tested. Later knowledge must not be silently treated as if it
had been available to the original decision-maker.

### D. Expert realism review - approved with execution conditions

Use two independent blinded reviewers with complementary HR-policy and
information-systems expertise. Do not invent identities. The exact two people
must be nominated before execution. Sampling, agreement reporting, and
adjudication are predeclared in `TDK_EXPERT_REVIEW_PACKET.md`; initial judgments
must remain immutable, and unresolved cases remain ambiguous.

### E. Repeated seeds and zero-positive scenarios - approved with modification

Use 30 independent scenario seeds for every predeclared protocol-scale condition
unless a written power or feasibility justification is approved before running
that condition. Methods are paired within each scenario seed. Retain every
zero-positive scenario in design and denominator tables; recall is undefined for
those scenarios and they are excluded only from recall-specific paired
inference under the predeclared eligibility indicator. AP is likewise undefined
when no positive class exists.

### F. Endpoint and multiplicity - approved

Recall at identical fixed additional review capacity is primary. AP is
secondary. The confirmatory secondary comparison family is predeclared as the
policy-aware-versus-raw paired differences in: (1) AP, (2) rare-legitimate
false-alert rate, and (3) ordinary-legitimate false-alert rate. Apply Holm's
step-down adjustment across these three two-sided tests. Precision and total
false alerts accompany the primary endpoint descriptively because at fixed
queue size they are algebraically tied to true positives. Per-class analyses,
controls, ablations, and utility sensitivity remain exploratory.

### G. Freeze and holdout - authorization withheld

Protocol freeze and the one-time holdout run are not authorized. They may be
requested only after the approved semantics, reviewer protocol, protocol-scale
development and validation evidence, exact environment, source revision,
analysis, and independent verification are complete and signed by a human.
