# Independent Development Scenario Specification

## Boundary

These scenarios are adversarial development tests. They are not a final holdout and must never be described as independent external validation.

The simulator in `src/research/independent_scenarios.py` imports only Python standard-library modules. It does not import MyHR policy arithmetic, features, models, deterministic checks, or the original synthetic generator.

## Two-World Design

1. A latent administrative world creates employment histories, policy epochs, approvals, effective dates, and recording dates.
2. Observation failures alter what reaches the HR record through migration, missing imports, workflow bypass, or batch retry.
3. A separate truth ledger records ordinary legitimate, rare legitimate, explicit policy violation, recording error, process error, or ambiguity.
4. A neutral adapter exposes observable records and the current policy to MyHR. Truth labels are attached only for evaluation.

## Current Development Matrix

Populations: stable administration, rapid expansion, and merger or migration.

Causal errors: wrong-employee linkage, missing increment import, promotion approval bypass, and duplicate event from batch retry.

Rare legitimate patterns: grandfathering, recognized prior service, and delayed bulk recording with unchanged effective dates.

The matrix contains all 12 population-by-error combinations. Every split contains ordinary, erroneous, and rare-legitimate histories. Event IDs are neutral hashes and labels remain separate until adaptation.

## Development Findings

The first run is artifact `independent_development_e342bd4acf39b06b`.

- The stored residual AP values are `0.3621` for policy-aware features and `0.3616` for raw features, but this comparison is not evidence of a tie or a policy-aware effect.
- After deterministic filtering, all three policy-specific residual features are constant zero. The experiment therefore contains no varying policy signal with which to test the central hypothesis.
- Apparent mechanism-level differences must not be interpreted because six of the twelve scenarios contain no residual positives and the implemented AP convention assigns those scenarios zero.
- Approval bypass and batch retry are removed by deterministic checks, as intended.
- Deterministic rules raised false alerts for 39 of 72 broadly labelled rare-legitimate histories. Source regeneration found 39 realised policy-transition histories and all 39 were flagged, but the original stored artifact does not preserve mechanism attribution per record. The artifact-supported claim is therefore `39/72`, while `39/39` remains a qualified regeneration finding.

These findings are retained as development evidence. No detector feature will be tuned against this artifact. See `TDK_INDEPENDENT_REVIEW_2026-10-17.md` for the adversarial re-analysis.

## Approved Expert-Review Method

Before protocol freeze, prepare a human-approved sample of blinded history summaries without model scores or intended labels. Use two independent reviewers with complementary HR-policy and information-systems expertise. They classify each history as legitimate, erroneous, ambiguous, or insufficient information and rate realism. Preserve their initial reasons, report agreement using a statistic selected before distribution, adjudicate from documented policy evidence, and retain genuinely ambiguous cases. Do not change cases to improve model metrics. Exact reviewers, sample size, statistic, sampling seed, and packet checksum remain pending.

Only fictional histories and aggregate organizational assumptions may be used unless lawful access and safeguards for real data are approved.

## Proposed Contract Extensions

- policy version and jurisdiction;
- effective date and recorded date;
- approval and source-system references;
- correction and reversal relationships;
- employment spells, transfers, and track changes;
- recognized prior service and service interruptions;
- explicit ambiguous/adjudication status.

The supervisor should approve these assumptions before they enter a frozen detector or holdout specification.
