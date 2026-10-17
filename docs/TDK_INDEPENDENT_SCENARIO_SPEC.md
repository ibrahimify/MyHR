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

- Policy-aware and raw residual AP are effectively tied overall.
- Policy-aware features help wrong-employee sanction-link cases.
- Raw features perform better for missing-increment imports.
- Approval bypass and batch retry are removed by deterministic checks, as intended.
- Current-policy rules falsely flag lawful grandfathered or recognized-service cases.

These mixed findings are retained. No detector feature will be tuned against this artifact.

## Required Expert Review

Before protocol freeze, prepare 40 to 60 blinded history summaries without model scores or intended labels. Ask at least two reviewers to classify each as legitimate, erroneous, ambiguous, or insufficient information and rate realism. Record reasons and agreement using Cohen's kappa or Gwet's AC1. Do not change cases to improve model metrics.

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
