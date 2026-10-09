"""Entry points for reproducible research experiments."""

from .synthetic_data import ExperimentConfig


def describe_experiment(config: ExperimentConfig) -> dict[str, int | float | str]:
    """Return metadata for an experiment run without executing models."""

    config.validate()
    return {
        "run_id": config.run_id(),
        "seed": config.seed,
        "employee_count": config.employee_count,
        "anomaly_rate": config.anomaly_rate,
        "rare_legitimate_rate": config.rare_legitimate_rate,
    }
