import hashlib

import matplotlib.pyplot as plt
import pandas as pd
import pytest

from scripts.build_tdk_holdout_report import _one, _primary_tables, _save_figure


def test_one_rejects_ambiguous_selection():
    frame = pd.DataFrame([{"kind": "x"}, {"kind": "x"}])
    with pytest.raises(ValueError, match="expected one row"):
        _one(frame, kind="x")


def test_primary_table_checks_paired_delta():
    common = {
        "method": "rule_negative_isolation_forest",
        "operating_point": "fixed_review_budget",
        "evaluation_count_total": 20,
        "positive_count_total": 4,
        "negative_count_total": 16,
        "alert_count_total": 2,
        "false_positives_total": 1,
        "true_negatives_total": 15,
        "false_negatives_total": 3,
        "rare_legitimate_count_total": 2,
        "rare_legitimate_flagged_total": 0,
        "ordinary_clean_count_total": 14,
        "ordinary_clean_flagged_total": 1,
        "precision_mean": 0.5,
        "average_precision_mean": 0.5,
    }
    aggregates = pd.DataFrame([
        {**common, "representation": "raw_matched", "true_positives_total": 1, "recall_mean": 0.25},
        {**common, "representation": "policy_matched", "true_positives_total": 2, "recall_mean": 0.50},
    ])
    paired = pd.DataFrame([{
        "method": "rule_negative_isolation_forest",
        "operating_point": "fixed_review_budget",
        "comparison_role": "primary_raw_vs_policy",
        "recall_delta_mean": 0.10,
    }])
    with pytest.raises(ValueError, match="recall delta"):
        _primary_tables(aggregates, paired)


def test_figure_outputs_are_reproducible(tmp_path):
    def render():
        figure, axis = plt.subplots()
        axis.plot([0, 1], [0, 1])
        return {
            path.suffix: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in _save_figure(figure, tmp_path / "result")
        }

    assert render() == render()
