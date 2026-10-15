# TDK Research Verification

Research title:

**MyHR: Policy-Aware Machine Learning for Anomaly Detection in Workforce Progression**

This page is for supervisors, reviewers, and future maintainers who want to verify that the research pipeline is wired correctly. It is not the final paper result page.

## Research Status

Seeds `2026-2030` are development-only because their outputs influenced feature design. Existing artifacts from those seeds must not be used as untouched holdout evidence. See `TDK_RESEARCH_AUDIT_2026-10-15.md` for the audit findings and `TDK_EXPERIMENT_PROTOCOL.md` for the holdout rules.

## Environments

Desktop app runtime:

```bash
pip install -r requirements.txt
python main.py
```

Research environment:

```bash
pip install -r requirements.txt -r requirements-research.txt
```

The research dependency file includes scikit-learn for Isolation Forest, pandas for result tables, and matplotlib for later paper figures.

## Smoke Verification

Run a small reproducible research smoke experiment:

```bash
python scripts/run_tdk_research_smoke.py --seed 2026 --employee-count 300
```

Optional: save the JSON report:

```bash
python scripts/run_tdk_research_smoke.py --seed 2026 --employee-count 300 --output research_outputs/smoke_2026.json
```

The output includes:

- run ID;
- seed;
- employee count;
- train/validation/test split counts;
- anomaly label counts;
- IQR and z-score baseline metrics;
- raw and policy-aware feature-set metrics;
- Isolation Forest metrics when scikit-learn is installed;
- false positives on rare legitimate policy cases.
- duplicate-detection metrics and sample candidate evidence.

## Interpretation Rule

Smoke output proves that the pipeline runs. It does not prove the final research claim.

Final paper claims must come only from documented experiment runs with fixed configuration, saved outputs, and reviewed methodology.

## Artifact Generation

Generate reviewable result artifacts:

```bash
python scripts/run_tdk_research_experiment.py --seed 2026 --employee-count 1000
```

This creates a run-specific folder under `research_outputs/<run_id>/` containing:

- `metadata.json`: configuration, seed, run ID, split counts, and label counts;
- `method_metrics.csv`: anomaly-detection metrics for statistical baselines and Isolation Forest;
- `duplicate_metrics.csv`: duplicate-detection metrics;
- `duplicate_candidates.csv`: duplicate candidate pairs with field-level evidence;
- `README.md`: short explanation of the run.

The `research_outputs/` folder is ignored by Git by default. Commit or archive selected outputs only after they are reviewed and intentionally chosen for the paper.

## Multi-Seed Stability Check

Run several seeds and aggregate the results:

```bash
python scripts/run_tdk_research_multiseed.py --seeds 2026,2027,2028,2029,2030 --employee-count 1000
```

This creates a folder under `research_outputs/multi_seed/` containing:

- `per_seed_method_metrics.csv`;
- `aggregate_method_metrics.csv`;
- `per_seed_duplicate_metrics.csv`;
- `aggregate_duplicate_metrics.csv`;
- `method_comparisons.csv`.

Use `method_comparisons.csv` for development diagnostics only. A final claim requires the frozen protocol, independent scenarios, validation-selected thresholds, uncertainty estimates, and an untouched holdout.

Small employee counts are useful for checking that the pipeline runs. Final paper evidence should use larger datasets and reviewed seeds because small test splits make precision and recall unstable.

Current implementation note: the default policy-aware Isolation Forest feature set uses policy residuals instead of the raw minimum-promotion-interval feature. This representation is not yet validated as non-circular and remains subject to the matched ablation protocol.

## Protocol V2 Verification

Run the dedicated protocol tests:

```bash
python -m unittest tests.test_tdk_protocol_v2
```

Generate the complete development matrix:

```bash
python scripts/run_tdk_protocol_experiment.py --run-purpose development --scenario-count 30 --employee-count 600
```

Generate the independently seeded validation matrix:

```bash
python scripts/run_tdk_protocol_experiment.py --run-purpose validation --scenario-count 30 --employee-count 600
```

The runner refuses `--run-purpose holdout`. Each write-once artifact contains:

- `metadata.json`: protocol status, exact command, Git state, source hashes, Python and package versions;
- `scenario_configs.csv`: policy, population, mechanism, rates, and all three seeds;
- `scenario_metrics.csv`: per-scenario metrics with explicit denominators and per-class recall;
- `record_predictions.csv`: every test-record score, prediction, and ground-truth label;
- `aggregate_metrics.csv`: descriptive summaries and bootstrap intervals;
- `paired_comparisons.csv`: policy-minus-raw paired differences, intervals, and sign-flip tests;
- `robustness_slices.csv`: results grouped by policy, population, mechanism, prevalence, and rare-case family;
- `utility_sensitivity.csv`: review, missed-error, and rare-escalation cost scenarios;
- `manifest.json`: SHA-256 checksums for every other artifact file.

Development and validation outputs remain diagnostics until the supervisor reviews the scenario assumptions and protocol. Do not copy their most favorable rows into the paper as final evidence.

The verified 30-scenario development and validation diagnostics are summarized in `TDK_PROTOCOL_V2_DEVELOPMENT_VALIDATION_REPORT.md`, including exact denominators, uncertainty intervals, controls, conditional utility findings, and remaining weaknesses.

Two deterministic rows are intentional. `deterministic_rules` contains policy-agnostic administrative checks. `deterministic_policy_rules` additionally applies the assigned promotion policy. The `policy_rules_plus_isolation_forest` rows measure whether ML adds ranking value after those explicit policy violations are already handled.
