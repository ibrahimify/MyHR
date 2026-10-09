"""Statistical baseline placeholders for the research pipeline.

Baselines will be implemented after the synthetic dataset contract is fixed.
They should remain simple and reproducible so Isolation Forest results are not
compared against a weak or moving target.
"""

BASELINE_METHODS = (
    "z_score",
    "iqr",
)
