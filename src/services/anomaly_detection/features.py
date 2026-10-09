"""Feature extraction boundary for anomaly-detection experiments.

The concrete feature sets will be added in small, testable steps:

- raw administrative history features;
- policy-aware features;
- duplicate-detection comparison features.
"""

RAW_FEATURE_SET = "raw"
POLICY_AWARE_FEATURE_SET = "policy_aware"


def supported_feature_sets() -> tuple[str, str]:
    return RAW_FEATURE_SET, POLICY_AWARE_FEATURE_SET
