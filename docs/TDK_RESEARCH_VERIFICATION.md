# TDK Research Verification

Research title:

**MyHR: Policy-Aware Machine Learning for Anomaly Detection in Workforce Progression**

This page is for supervisors, reviewers, and future maintainers who want to verify that the research pipeline is wired correctly. It is not the final paper result page.

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
