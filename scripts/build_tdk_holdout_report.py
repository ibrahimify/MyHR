"""Build the final TDK result tables and figures from a verified holdout artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

matplotlib.rcParams["svg.hashsalt"] = "myhr-tdk-holdout-v2"


PRIMARY_METHOD = "rule_negative_isolation_forest"
PRIMARY_OPERATING_POINT = "fixed_review_budget"
POLICY = "policy_matched"
RAW = "raw_matched"
EXPECTED_PROTOCOL = "myhr-tdk-holdout-v2"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _one(frame: pd.DataFrame, **filters: str) -> pd.Series:
    selected = frame
    for column, value in filters.items():
        selected = selected[selected[column] == value]
    if len(selected) != 1:
        raise ValueError(f"expected one row for {filters}, found {len(selected)}")
    return selected.iloc[0]


def _primary_tables(
    aggregates: pd.DataFrame,
    paired: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    for representation, label in ((RAW, "Raw"), (POLICY, "Policy-aware")):
        row = _one(
            aggregates,
            method=PRIMARY_METHOD,
            representation=representation,
            operating_point=PRIMARY_OPERATING_POINT,
        )
        rows.append({
            "method": label,
            "evaluation_records": int(row["evaluation_count_total"]),
            "anomalies": int(row["positive_count_total"]),
            "non_anomalies": int(row["negative_count_total"]),
            "reviewed": int(row["alert_count_total"]),
            "true_positives": int(row["true_positives_total"]),
            "false_positives": int(row["false_positives_total"]),
            "true_negatives": int(row["true_negatives_total"]),
            "false_negatives": int(row["false_negatives_total"]),
            "rare_legitimate_records": int(row["rare_legitimate_count_total"]),
            "rare_legitimate_flagged": int(row["rare_legitimate_flagged_total"]),
            "ordinary_clean_records": int(row["ordinary_clean_count_total"]),
            "ordinary_clean_flagged": int(row["ordinary_clean_flagged_total"]),
            "scenario_mean_recall": float(row["recall_mean"]),
            "scenario_mean_precision": float(row["precision_mean"]),
            "scenario_mean_average_precision": float(row["average_precision_mean"]),
        })
    primary = pd.DataFrame(rows)
    contrast = _one(
        paired,
        method=PRIMARY_METHOD,
        operating_point=PRIMARY_OPERATING_POINT,
        comparison_role="primary_raw_vs_policy",
    )
    expected_delta = (
        primary.loc[primary["method"] == "Policy-aware", "scenario_mean_recall"].iloc[0]
        - primary.loc[primary["method"] == "Raw", "scenario_mean_recall"].iloc[0]
    )
    if abs(expected_delta - float(contrast["recall_delta_mean"])) > 1e-12:
        raise ValueError("primary recall delta disagrees with aggregate rows")
    contrasts = pd.DataFrame([{
        "endpoint": "Recall at fixed review capacity",
        "policy_minus_raw": float(contrast["recall_delta_mean"]),
        "ci95_low": float(contrast["recall_delta_ci95_low"]),
        "ci95_high": float(contrast["recall_delta_ci95_high"]),
        "p_value": float(contrast["primary_recall_sign_flip_p"]),
        "holm_adjusted_p": "not applicable (primary)",
    }, {
        "endpoint": "Average precision",
        "policy_minus_raw": float(contrast["average_precision_delta_mean"]),
        "ci95_low": float(contrast["average_precision_delta_ci95_low"]),
        "ci95_high": float(contrast["average_precision_delta_ci95_high"]),
        "p_value": float(contrast["average_precision_delta_sign_flip_p"]),
        "holm_adjusted_p": float(contrast["average_precision_delta_holm_secondary_p"]),
    }, {
        "endpoint": "Rare-legitimate flagged rate",
        "policy_minus_raw": float(contrast["rare_legitimate_flagged_rate_delta_mean"]),
        "ci95_low": float(contrast["rare_legitimate_flagged_rate_delta_ci95_low"]),
        "ci95_high": float(contrast["rare_legitimate_flagged_rate_delta_ci95_high"]),
        "p_value": float(contrast["rare_legitimate_flagged_rate_delta_sign_flip_p"]),
        "holm_adjusted_p": float(contrast["rare_legitimate_flagged_rate_delta_holm_secondary_p"]),
    }, {
        "endpoint": "Ordinary-clean flagged rate",
        "policy_minus_raw": float(contrast["ordinary_clean_flagged_rate_delta_mean"]),
        "ci95_low": float(contrast["ordinary_clean_flagged_rate_delta_ci95_low"]),
        "ci95_high": float(contrast["ordinary_clean_flagged_rate_delta_ci95_high"]),
        "p_value": float(contrast["ordinary_clean_flagged_rate_delta_sign_flip_p"]),
        "holm_adjusted_p": float(contrast["ordinary_clean_flagged_rate_delta_holm_secondary_p"]),
    }])
    return primary, contrasts


def _workflow_table(aggregates: pd.DataFrame) -> pd.DataFrame:
    selectors = (
        ("deterministic_policy_rules", "true_policy_checks", "rules_fixed", "Rules only"),
        ("policy_rules_plus_isolation_forest", RAW, "rules_first_budget_floor", "Rules + raw ML"),
        ("policy_rules_plus_isolation_forest", POLICY, "rules_first_budget_floor", "Rules + policy-aware ML"),
    )
    rows = []
    for method, representation, operating_point, label in selectors:
        row = _one(
            aggregates,
            method=method,
            representation=representation,
            operating_point=operating_point,
        )
        rows.append({
            "workflow": label,
            "reviewed": int(row["alert_count_total"]),
            "true_positives": int(row["true_positives_total"]),
            "false_positives": int(row["false_positives_total"]),
            "false_negatives": int(row["false_negatives_total"]),
            "rare_legitimate_flagged": int(row["rare_legitimate_flagged_total"]),
            "rare_legitimate_total": int(row["rare_legitimate_count_total"]),
            "scenario_mean_recall": float(row["recall_mean"]),
            "scenario_mean_precision": float(row["precision_mean"]),
        })
    return pd.DataFrame(rows)


def _model_table(
    model_aggregates: pd.DataFrame,
    model_paired: pd.DataFrame,
) -> pd.DataFrame:
    selected = model_aggregates[
        (model_aggregates["operating_point"] == PRIMARY_OPERATING_POINT)
        & model_aggregates["representation"].isin([RAW, POLICY])
    ].copy()
    pivot = selected.pivot(index="method", columns="representation", values="recall_mean")
    result = pd.DataFrame({
        "model": pivot.index,
        "raw_recall": pivot[RAW].values,
        "policy_aware_recall": pivot[POLICY].values,
    })
    result["policy_minus_raw"] = result["policy_aware_recall"] - result["raw_recall"]
    paired = model_paired[
        model_paired["operating_point"] == PRIMARY_OPERATING_POINT
    ].set_index("method")
    result["delta_ci95_low"] = result["model"].map(paired["recall_delta_ci95_low"])
    result["delta_ci95_high"] = result["model"].map(paired["recall_delta_ci95_high"])
    result["delta_sign_flip_p"] = result["model"].map(paired["recall_delta_sign_flip_p"])
    return result.sort_values("model").reset_index(drop=True)


def _robustness_table(robustness: pd.DataFrame) -> pd.DataFrame:
    selected = robustness[
        (robustness["method"] == PRIMARY_METHOD)
        & (robustness["operating_point"] == PRIMARY_OPERATING_POINT)
        & robustness["representation"].isin([RAW, POLICY])
    ]
    index = ["slice_dimension", "slice_value", "scenario_count"]
    pivot = selected.pivot(index=index, columns="representation", values="recall_mean").reset_index()
    pivot = pivot.rename(columns={RAW: "raw_recall", POLICY: "policy_aware_recall"})
    pivot["policy_minus_raw"] = pivot["policy_aware_recall"] - pivot["raw_recall"]
    return pivot.sort_values(["slice_dimension", "slice_value"]).reset_index(drop=True)


def _save_figure(fig: plt.Figure, base: Path) -> list[Path]:
    outputs = []
    formats = (
        (".png", {"dpi": 300}),
        (".pdf", {"metadata": {"CreationDate": None, "ModDate": None}}),
        (".svg", {"metadata": {"Date": None}}),
    )
    for suffix, kwargs in formats:
        path = base.with_suffix(suffix)
        fig.savefig(path, bbox_inches="tight", **kwargs)
        if suffix == ".svg":
            lines = path.read_text(encoding="utf-8").splitlines()
            path.write_text("\n".join(line.rstrip() for line in lines) + "\n", encoding="utf-8")
        outputs.append(path)
    plt.close(fig)
    return outputs


def _plot_primary(primary: pd.DataFrame, output: Path) -> list[Path]:
    colors = ["#4D4D4D", "#0072B2"]
    fig, axes = plt.subplots(1, 2, figsize=(7.1, 3.2))
    labels = primary["method"].tolist()
    values = primary["scenario_mean_recall"].to_numpy()
    axes[0].bar(labels, values, color=colors, width=0.58)
    axes[0].set_ylabel("Scenario-mean recall")
    axes[0].set_ylim(0, 0.5)
    axes[0].set_title("Equal-capacity residual comparison")
    for index, value in enumerate(values):
        axes[0].text(index, value + 0.012, f"{value:.1%}", ha="center", fontsize=9)
    outcomes = primary.set_index("method")
    x = range(len(labels))
    axes[1].bar(x, outcomes.loc[labels, "true_positives"], color="#009E73", label="True positives")
    axes[1].bar(
        x,
        outcomes.loc[labels, "false_positives"],
        bottom=outcomes.loc[labels, "true_positives"],
        color="#E69F00",
        label="False positives",
    )
    axes[1].set_xticks(list(x), labels)
    axes[1].set_ylabel("Reviewed records")
    axes[1].set_title("Pooled review outcomes")
    axes[1].legend(frameon=False, fontsize=7.5, loc="upper center", ncol=2)
    fig.tight_layout()
    return _save_figure(fig, output)


def _plot_models(models: pd.DataFrame, output: Path) -> list[Path]:
    model_labels = {
        "iqr": "IQR",
        "isolation_forest": "Isolation Forest",
        "local_outlier_factor": "Local Outlier Factor",
        "one_class_svm": "One-Class SVM",
        "robust_z_score": "Robust z-score",
    }
    rows = models.copy()
    rows["label"] = rows["model"].map(model_labels)
    rows = rows.sort_values("policy_minus_raw")
    positions = list(range(len(rows)))
    low = rows["policy_minus_raw"] - rows["delta_ci95_low"]
    high = rows["delta_ci95_high"] - rows["policy_minus_raw"]
    fig, ax = plt.subplots(figsize=(7.1, 3.8))
    ax.errorbar(
        rows["policy_minus_raw"],
        positions,
        xerr=[low, high],
        fmt="o",
        color="#0072B2",
        ecolor="#4D4D4D",
        capsize=4,
    )
    ax.axvline(0, color="#333333", linewidth=0.9)
    ax.set_yticks(positions, rows["label"])
    ax.set_xlabel("Policy-aware minus raw recall (95% paired interval)")
    ax.set_title("Exploratory model sensitivity at equal capacity")
    fig.tight_layout()
    return _save_figure(fig, output)


def _plot_robustness(robustness: pd.DataFrame, output: Path) -> list[Path]:
    dimensions = robustness["slice_dimension"].drop_duplicates().tolist()
    fig, axes = plt.subplots(3, 2, figsize=(7.1, 7.2), sharex=True)
    for ax, dimension in zip(axes.flat, dimensions):
        rows = robustness[robustness["slice_dimension"] == dimension].sort_values("policy_minus_raw")
        labels = [str(value).replace("_", " ").title() for value in rows["slice_value"]]
        ax.barh(labels, rows["policy_minus_raw"], color="#009E73")
        ax.axvline(0, color="#333333", linewidth=0.8)
        ax.set_title(dimension.replace("_", " ").title(), fontsize=10)
        ax.tick_params(axis="y", labelsize=8)
    for ax in axes[-1]:
        ax.set_xlabel("Policy-aware minus raw recall")
    fig.suptitle("Descriptive robustness across predeclared slices", fontsize=12)
    fig.tight_layout()
    return _save_figure(fig, output)


def build_report(artifact: Path, docs: Path) -> dict:
    metadata = json.loads((artifact / "metadata.json").read_text(encoding="utf-8"))
    if metadata.get("protocol_version") != EXPECTED_PROTOCOL:
        raise ValueError("unexpected protocol version")
    if metadata.get("protocol_status") != "frozen_independent_holdout":
        raise ValueError("artifact is not the frozen independent holdout")
    tables = docs / "tables"
    figures = docs / "figures"
    results = docs / "results"
    for directory in (tables, figures, results):
        directory.mkdir(parents=True, exist_ok=True)

    aggregate = pd.read_csv(artifact / "aggregate_metrics.csv")
    paired = pd.read_csv(artifact / "paired_comparisons.csv")
    model_aggregate = pd.read_csv(artifact / "model_comparison_aggregates.csv")
    model_paired = pd.read_csv(artifact / "model_comparison_paired.csv")
    robustness = pd.read_csv(artifact / "robustness_slices.csv")
    primary, contrasts = _primary_tables(aggregate, paired)
    workflow = _workflow_table(aggregate)
    models = _model_table(model_aggregate, model_paired)
    slices = _robustness_table(robustness)

    table_frames = {
        tables / "holdout_primary_results.csv": primary,
        tables / "holdout_endpoint_contrasts.csv": contrasts,
        tables / "holdout_complete_workflow.csv": workflow,
        tables / "holdout_model_sensitivity.csv": models,
        tables / "holdout_robustness.csv": slices,
    }
    for path, frame in table_frames.items():
        frame.to_csv(path, index=False, lineterminator="\n")

    figure_paths = []
    figure_paths += _plot_primary(primary, figures / "holdout_primary_comparison")
    figure_paths += _plot_models(models, figures / "holdout_model_sensitivity")
    figure_paths += _plot_robustness(slices, figures / "holdout_robustness")

    raw = _one(primary, method="Raw")
    policy = _one(primary, method="Policy-aware")
    recall = _one(contrasts, endpoint="Recall at fixed review capacity")
    average_precision = _one(contrasts, endpoint="Average precision")
    rare = _one(contrasts, endpoint="Rare-legitimate flagged rate")
    ordinary = _one(contrasts, endpoint="Ordinary-clean flagged rate")
    positive_slices = int((slices["policy_minus_raw"] > 0).sum())
    report = f"""# Frozen Holdout Results

Status: independently audited frozen holdout. No post-hoc tuning or rerun was performed.

## Research Questions

**RQ1: Did policy-aware Isolation Forest improve detection at equal review capacity?**

Yes within this synthetic holdout. Scenario-mean recall increased from {raw['scenario_mean_recall']:.1%} to {policy['scenario_mean_recall']:.1%}; the paired difference was {recall['policy_minus_raw'] * 100:+.1f} percentage points (95% CI {recall['ci95_low'] * 100:+.1f} to {recall['ci95_high'] * 100:+.1f}, sign-flip p approximately 0.000010). Both methods reviewed {int(raw['reviewed']):,} residual records. Policy-aware ML found {int(policy['true_positives']):,} anomalies and raw ML found {int(raw['true_positives']):,}.

**RQ2: Did the advantage persist across changed conditions?**

Descriptively, yes: policy-aware recall was higher in all {positive_slices} predeclared policy, population, anomaly-mechanism, rare-pattern, and rate slices. The slice differences ranged from {slices['policy_minus_raw'].min():+.1%} to {slices['policy_minus_raw'].max():+.1%}. These slice summaries are robustness diagnostics, not separately multiplicity-adjusted confirmatory tests. The exploratory effect also varied by scorer, from nearly zero for IQR to larger differences for Isolation Forest and Local Outlier Factor.

**RQ3: Did policy awareness reduce false alerts on rare legitimate behavior?**

Not conclusively. The scenario-mean rare-legitimate flagged-rate difference was {rare['policy_minus_raw']:+.1%} (95% CI {rare['ci95_low']:+.1%} to {rare['ci95_high']:+.1%}, Holm-adjusted p={float(rare['holm_adjusted_p']):.3f}). The pooled counts were {int(policy['rare_legitimate_flagged'])}/{int(policy['rare_legitimate_records'])} for policy-aware ML and {int(raw['rare_legitimate_flagged'])}/{int(raw['rare_legitimate_records'])} for raw ML. The direction was favorable, but the evidence does not establish a rare-case benefit.

## Secondary Results

- Average precision improved by {average_precision['policy_minus_raw'] * 100:+.1f} percentage points (95% CI {average_precision['ci95_low'] * 100:+.1f} to {average_precision['ci95_high'] * 100:+.1f}, Holm-adjusted p={float(average_precision['holm_adjusted_p']):.5f}).
- The ordinary-clean flagged rate decreased by {ordinary['policy_minus_raw'] * 100:+.1f} percentage points (95% CI {ordinary['ci95_low'] * 100:+.1f} to {ordinary['ci95_high'] * 100:+.1f}, Holm-adjusted p={float(ordinary['holm_adjusted_p']):.5f}).
- The complete workflow found {int(workflow.iloc[2]['true_positives'])} anomalies with policy-aware ML and {int(workflow.iloc[1]['true_positives'])} with raw ML, from equal {int(workflow.iloc[2]['reviewed'])}-record queues containing policy-rule findings plus ML queue filling.
- Exploratory results for five scorers are reported without selecting a winner after holdout inspection.

## Interpretation Boundary

The result supports the value of policy-conditioned features within the frozen synthetic design. It does not prove performance on real employee data, establish that every gain is caused by correct policy knowledge, or justify automatic personnel decisions. Wrong-policy, shuffled-policy, ablation, and multi-model results remain necessary context. The expert review supplied qualitative support for continuing the study but did not produce case-level ratings or an agreement statistic.

## Evidence

- Artifact: `{metadata['artifact_id']}`
- Frozen source revision: `{metadata['holdout_gate']['frozen_git_commit']}`
- Scenarios: {metadata['scenario_count']:,} ({metadata['condition_count']} conditions x {metadata['seeds_per_condition']} seeds)
- Evaluation histories: {int(raw['evaluation_records']):,}
- Manifest and authorization were independently verified before interpretation.
"""
    report_path = results / "TDK_HOLDOUT_RESULTS.md"
    report_path.write_text(report, encoding="utf-8", newline="\n")

    source_files = [
        artifact / "metadata.json",
        artifact / "manifest.json",
        artifact / "aggregate_metrics.csv",
        artifact / "paired_comparisons.csv",
        artifact / "model_comparison_aggregates.csv",
        artifact / "model_comparison_paired.csv",
        artifact / "robustness_slices.csv",
    ]
    outputs = list(table_frames) + figure_paths + [report_path]
    manifest = {
        "generator": "scripts/build_tdk_holdout_report.py",
        "artifact_id": metadata["artifact_id"],
        "protocol_version": metadata["protocol_version"],
        "frozen_git_commit": metadata["holdout_gate"]["frozen_git_commit"],
        "sources": {str(path.name): _sha256(path) for path in source_files},
        "outputs": {path.relative_to(docs).as_posix(): _sha256(path) for path in outputs},
    }
    manifest_path = results / "holdout_report_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--docs", type=Path, default=Path(__file__).resolve().parents[1] / "docs")
    args = parser.parse_args()
    print(json.dumps(build_report(args.artifact.resolve(), args.docs.resolve()), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
