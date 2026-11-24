# Holdout v1 Execution Failure

Date: 2026-11-24

## Outcome

The one authorized `myhr-tdk-holdout-v1` attempt was consumed and failed before
artifact publication. The runner completed 42 of 1,080 planned scenarios and
stopped while constructing scenario 43. No result artifact, aggregate metric,
or model comparison was published or inspected.

The external canonical ledger records the attempt as `failed`. It is preserved
outside the repository and v1 cannot be rerun through the supported workflow.

## Cause

Within each split, the truth planner selected error candidates first and then
removed them from the rare-case pool. Some employees were eligible for both
roles. In the failing validation split, this order consumed candidates required
to meet the predeclared grandfathered-policy count even though a feasible
disjoint allocation existed.

## Repair boundary

Protocol v2 selects exact disjoint error and rare-case sets jointly. It reserves
rare-only candidates first, then uses overlapping candidates only as needed,
and selects errors from the remainder. It rejects a split only when the two
candidate sets have no feasible disjoint allocation. When a random base
population is infeasible, v2 deterministically resamples the pre-intervention
population and records the accepted generation-attempt index in the scenario
configuration. It never changes a label, feature, threshold, or outcome after
model scoring.

The repaired constructor generated all 1,080 predeclared validation scenarios:
1,077 accepted the first base sample and three accepted the second. This was a
construction-only stress check on the existing validation seed family, not a
v2 holdout preview.

V2 changes no hypothesis, endpoint, feature, model, threshold, review budget,
condition factor, or statistical analysis. It uses a new disjoint seed family,
protocol ID, authorization, and one-time ledger. V2 remains locked until the
repair passes tests and CI and a new exact revision is frozen and authorized.
