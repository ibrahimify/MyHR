# TDK Supervisor Package Verification

Date: 30 October 2026

Status: development evidence only; draft protocol; final holdout locked.

## Source And Tracker State

- Branch: `research/policy-aware-anomaly`
- Scientific implementation checkpoint: `1942718e69ccf34d3e628767b5316e0467f63a52`
- Pull request: #1 remains open, draft, and unmerged.
- Issue #10 remains the scientific protocol blocker.
- No holdout command was executed.

## Current Artifact

- ID: `independent_development_b866ae2aa1b4b479`
- Provenance: clean commit `1942718`; Python 3.13.5; NumPy 2.5.4; pandas 2.3.3; scikit-learn 1.9.1; SciPy 1.18.1.
- Audit: verified with complete manifest, source hashes, stored denominators, paired comparisons, and `holdout_accessed: false`.
- Data: 12 scenarios; 864 test histories; 108 anomalies; 72 rare-legitimate histories.
- Deterministic result: 63 TP, 0 FP, 45 FN; 0/72 rare-legitimate alerts.
- Primary exploratory comparison: recall delta +0.0278, 95% CI [-0.0278, +0.1019], sign-flip p=0.6875.
- Interpretation: no advantage demonstrated; no equivalence claim.

## Required Verification Commands

```powershell
python -m unittest discover tests
python scripts/verify_tdk_citations.py --require-local-artifact
python -m scripts.audit_tdk_protocol_artifact research_outputs/independent_development/independent_development_b866ae2aa1b4b479
python scripts/generate_tdk_supervisor_package.py
```

The final execution results, CI URL, page count, rendered-page inspection, and package file hashes are recorded after generation. A package should not be treated as final if any check fails.

## Claims Explicitly Excluded

- Invalidated `39/72` and `8/72` readings are not current evidence.
- The historical constant-feature comparison is not a null, tie, or equivalence result.
- The secondary AP result is not confirmatory.
- Synthetic rates are not estimates of organizational prevalence.
- No final holdout or real-world validation result exists.

## Remaining Human Gates

Scenario proposals 1 and 3-6, grandfathering semantics, temporal views, expert reviewers and sampling, protocol-scale design, multiplicity, protocol freeze, holdout access, scientific conclusions, and PR merge remain human decisions.
