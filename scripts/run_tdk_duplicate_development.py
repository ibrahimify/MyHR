"""Write development-only duplicate evidence using the existing matchers."""

from __future__ import annotations

import argparse
from dataclasses import asdict, replace
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import distributions
from itertools import combinations
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
import tracemalloc

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.services.anomaly_detection.duplicate_detection import (
    DUPLICATE_METHODS,
    _blocked_similarity_pairs,
    confusion_counts_for_pairs,
    find_exact_duplicate_candidates,
    find_normalized_exact_duplicate_candidates,
    find_similarity_duplicate_candidates,
)
from src.services.anomaly_detection.synthetic_data import (
    AnomalyType, DatasetSplit, ExperimentConfig, SyntheticDataset, generate_synthetic_dataset,
)

SCHEMA = "duplicate-development-evidence-v1"
ROLES = {
    "train": "unused_by_duplicate_matchers",
    "validation": "similarity_threshold_selection_only",
    "test": "development_evaluation_not_final_holdout",
}
SOURCE_PATHS = (
    "src/__init__.py",
    "src/services/__init__.py",
    "src/services/anomaly_detection/__init__.py",
    "src/services/anomaly_detection/synthetic_data.py",
    "src/services/anomaly_detection/duplicate_detection.py",
    "src/services/anomaly_detection/metrics.py",
    "scripts/run_tdk_duplicate_development.py",
    "scripts/audit_tdk_duplicate_artifact.py",
    "docs/TDK_EXPERIMENT_PROTOCOL.md",
)


def _json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def _truth(records):
    by_id = {r.identity.employee_id: r for r in records}
    if len(by_id) != len(records) or any(not key for key in by_id):
        raise ValueError("employee IDs must be unique and nonempty")
    roots = {}
    for key, record in by_id.items():
        if record.split not in DatasetSplit:
            raise ValueError("unknown partition")
        current, visited = key, set()
        while by_id[current].duplicate_of_employee_id is not None:
            if current in visited:
                raise ValueError("duplicate link cycle")
            visited.add(current)
            parent = by_id[current].duplicate_of_employee_id
            if parent not in by_id:
                raise ValueError("dangling duplicate link")
            if by_id[parent].split is not record.split:
                raise ValueError("duplicate cluster crosses partitions")
            current = parent
        roots[key] = current
    latent_roots = {}
    for key, record in by_id.items():
        root = by_id[roots[key]]
        if record.latent_person_id != root.latent_person_id:
            raise ValueError("latent identity disagrees with cluster links")
        if record.latent_person_id:
            prior = latent_roots.setdefault(record.latent_person_id, roots[key])
            if prior != roots[key]:
                raise ValueError("latent identity spans separate clusters")
        kind, anchor = record.hard_nonduplicate_kind, record.hard_nonduplicate_anchor_id
        if (kind is None) != (anchor is None):
            raise ValueError("hard nonduplicate needs both kind and anchor")
        if anchor is not None:
            if anchor not in by_id or anchor == key or by_id[anchor].split is not record.split:
                raise ValueError("invalid hard nonduplicate anchor")
            if roots[anchor] == roots[key] or record.latent_person_id is not None:
                raise ValueError("hard nonduplicate overlaps duplicate truth")
    return roots


def _counts(predicted, truth, universe):
    counts = confusion_counts_for_pairs(predicted, truth, universe)
    tp, fp, tn, fn = (counts.true_positives, counts.false_positives,
                      counts.true_negatives, counts.false_negatives)
    return {
        "true_positives": tp, "false_positives": fp,
        "true_negatives": tn, "false_negatives": fn,
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
        "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None,
        "false_positive_rate": fp / (fp + tn) if fp + tn else None,
    }


def _key(candidate):
    return tuple(sorted((candidate.left_employee_id, candidate.right_employee_id)))


def _inputs(records):
    # Only identity fields reach the matchers; evaluation truth stays outside.
    return tuple(replace(r, events=(), anomaly_labels=(AnomalyType.CLEAN,),
                         duplicate_of_employee_id=None, latent_person_id=None,
                         hard_nonduplicate_kind=None, hard_nonduplicate_anchor_id=None)
                 for r in records)


def calibrate_threshold(dataset, *, split=DatasetSplit.VALIDATION):
    if split is not DatasetSplit.VALIDATION:
        raise ValueError("threshold selection is restricted to validation")
    roots = _truth(dataset.records)
    records = tuple(r for r in dataset.records if r.split is split)
    scored = find_similarity_duplicate_candidates(_inputs(records), threshold=0.0)
    truth = {pair for pair in combinations(sorted(r.identity.employee_id for r in records), 2)
             if roots[pair[0]] == roots[pair[1]]}
    universe = {_key(c) for c in scored}
    rows = []
    for threshold in sorted({c.score for c in scored}, reverse=True):
        predicted = {_key(c) for c in scored if c.score >= threshold}
        rows.append({"threshold": threshold, **_counts(predicted, truth, universe)})
    status = ("empty_validation" if not records else "no_blocked_pairs" if not scored
              else "no_blocked_positive_pairs" if not truth & universe else "selected")
    threshold = None
    if status == "selected":
        best = max(
            rows,
            key=lambda row: (
                row["f1"] or 0,
                row["precision"] or 0,
                row["recall"] or 0,
                row["threshold"],
            ),
        )
        threshold = best["threshold"]
    return {
        "partition": "validation", "status": status, "threshold": threshold,
        "objective": "candidate_f1_then_precision_then_recall_then_higher_threshold",
        "record_count": len(records), "true_pair_count": len(truth),
        "blocked_true_pair_count": len(truth & universe), "search": rows,
    }


def _average_precision(scores, truth):
    if not scores or not any(pair in truth for pair in scores):
        return None
    from sklearn.metrics import average_precision_score
    return float(average_precision_score([pair in truth for pair in scores], list(scores.values())))


def _measure_method(records, roots, method, threshold):
    tracing = tracemalloc.is_tracing()
    if not tracing:
        tracemalloc.start()
    start = time.perf_counter()
    try:
        inputs = _inputs(records)
        ids = sorted(r.identity.employee_id for r in records)
        universe = set(combinations(ids, 2))
        truth = {p for p in universe if roots[p[0]] == roots[p[1]]}
        block_start = time.perf_counter()
        if method == "similarity":
            blocked_raw = tuple(_blocked_similarity_pairs(inputs))
            blocked = {tuple(sorted((a.identity.employee_id, b.identity.employee_id)))
                       for a, b in blocked_raw}
            blocking_time = time.perf_counter() - block_start
        else:
            blocked_raw, blocked, blocking_time = (), universe, None
        score_start = time.perf_counter()
        if method == "exact":
            matched = find_exact_duplicate_candidates(inputs)
        elif method == "normalized_exact":
            matched = find_normalized_exact_duplicate_candidates(inputs)
        else:
            matched = find_similarity_duplicate_candidates(inputs, threshold=0.0, blocked_pairs=blocked_raw)
        scores = {_key(c): c.score for c in matched}
        if method != "similarity":
            scores = {p: scores.get(p, 0.0) for p in universe}
        scoring_time = time.perf_counter() - score_start
        available = method != "similarity" or threshold is not None
        selected = {p for p, score in scores.items() if score >= (threshold if method == "similarity" else 1.0)} if available else set()
        end = _counts(selected, truth, universe) if available else None
        candidate = _counts(selected, truth, blocked) if available else None
        metrics = {
            "method": method, "threshold": threshold if method == "similarity" else None,
            "selection_status": "available" if available else "unavailable_validation_threshold",
            "record_count": len(records), "total_pair_count": len(universe),
            "candidate_pair_count": len(blocked), "true_pair_count": len(truth),
            "blocked_true_pair_count": len(blocked & truth),
            "blocking_recall": len(blocked & truth) / len(truth) if truth else None,
            "reduction_ratio": 1 - len(blocked) / len(universe) if universe else None,
            "candidate_count": len(selected) if available else None,
            "candidates_per_1000_records": 1000 * len(selected) / len(records) if records and available else None,
            "false_matches_per_1000_records": 1000 * end["false_positives"] / len(records) if records and available else None,
            "candidate_average_precision": _average_precision(scores, truth),
            "end_to_end": end, "candidate": candidate,
        }
        metrics["resources"] = {
            "blocking_time_s": blocking_time, "scoring_time_s": scoring_time,
            "evaluation_time_s": time.perf_counter() - start,
            "peak_python_bytes": None if tracing else tracemalloc.get_traced_memory()[1],
            "memory_status": "unavailable_caller_tracing" if tracing else "measured_python_allocations",
            "scope": "identity_projection_through_metrics_excludes_generation_calibration_export",
        }
        return scores, selected if available else None, blocked, metrics
    finally:
        if not tracing:
            tracemalloc.stop()


def build_evidence(dataset):
    roots = _truth(dataset.records)
    selection = calibrate_threshold(dataset)
    identities, truth_rows, pairs, metrics = [], [], [], []
    for r in sorted(dataset.records, key=lambda r: r.identity.employee_id):
        identity = asdict(r.identity)
        identity["date_of_birth"] = r.identity.date_of_birth.isoformat() if r.identity.date_of_birth else None
        identities.append({"partition": r.split.value, **identity})
        truth_rows.append({
            "employee_id": r.identity.employee_id, "cluster_root": roots[r.identity.employee_id],
            "duplicate_of_employee_id": r.duplicate_of_employee_id,
            "latent_person_id": r.latent_person_id,
            "hard_nonduplicate_kind": r.hard_nonduplicate_kind.value if r.hard_nonduplicate_kind else None,
            "hard_nonduplicate_anchor_id": r.hard_nonduplicate_anchor_id,
        })
    for split in (DatasetSplit.VALIDATION, DatasetSplit.TEST):
        records = tuple(r for r in dataset.records if r.split is split)
        outputs = {}
        for method in DUPLICATE_METHODS:
            scores, selected, blocked, row = _measure_method(records, roots, method, selection["threshold"])
            outputs[method] = (scores, selected, blocked)
            metrics.append({"partition": split.value, **row})
        for pair in combinations(sorted(r.identity.employee_id for r in records), 2):
            pairs.append({
                "partition": split.value, "left_employee_id": pair[0], "right_employee_id": pair[1],
                "similarity_blocked": pair in outputs["similarity"][2],
                "scores": {m: outputs[m][0].get(pair) for m in DUPLICATE_METHODS},
                "predictions": {m: pair in outputs[m][1] if outputs[m][1] is not None else None
                                for m in DUPLICATE_METHODS},
            })
    return {"identities.json": identities, "truth.json": truth_rows,
            "pairs.json": pairs, "threshold_search.json": selection, "metrics.json": metrics}


def _git(*args):
    return subprocess.run(("git", *args), cwd=REPO_ROOT, capture_output=True, check=True).stdout


def _source_snapshots():
    return {name: (REPO_ROOT / name).read_bytes() for name in SOURCE_PATHS}


def write_artifact(dataset, output_dir, *, configuration, data_origin="existing_synthetic_generator", command=None,
                   expected_source_hashes=None):
    """Reserve a new directory; publish the completion manifest last. Never overwrite."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    snapshots = _source_snapshots()
    if expected_source_hashes is not None:
        actual_hashes = {name: sha256(content).hexdigest() for name, content in snapshots.items()}
        if actual_hashes != expected_source_hashes:
            raise RuntimeError("source changed during dataset generation")
    if data_origin == "existing_synthetic_generator":
        expected_dataset = generate_synthetic_dataset(ExperimentConfig(**configuration))
        if dataset != expected_dataset:
            raise ValueError("dataset does not match the recorded generator configuration")
        generation_verification = "regenerated_and_matched"
    elif data_origin == "hand_calculated_test_fixture":
        generation_verification = "caller_asserted_fixture"
    else:
        raise ValueError(f"unsupported data origin: {data_origin}")
    revision = _git("rev-parse", "HEAD").decode().strip()
    payload = build_evidence(dataset)
    sources = {}
    for name, content in snapshots.items():
        target = output_dir / "sources" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        original = subprocess.run(("git", "show", f"{revision}:{name}"), cwd=REPO_ROOT, capture_output=True)
        # Compare normalized newlines without hiding other working-copy changes.
        matches = original.returncode == 0 and original.stdout.replace(b"\r\n", b"\n") == content.replace(b"\r\n", b"\n")
        sources[name] = {"sha256": sha256(content).hexdigest(), "matches_revision": matches}
    metadata = {
        "schema": SCHEMA, "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_purpose": "duplicate_development", "protocol_status": "draft_holdout_locked",
        "protocol_reference": {"path": "docs/TDK_EXPERIMENT_PROTOCOL.md",
                               "sha256": sources["docs/TDK_EXPERIMENT_PROTOCOL.md"]["sha256"]},
        "holdout_accessed": False, "partition_roles": ROLES,
        "data_origin": data_origin, "generation_verification": generation_verification,
        "configuration": configuration,
        "dataset_metadata": asdict(dataset.metadata),
        "seeds": {"dataset_seed": dataset.metadata.seed, "split_seed": dataset.metadata.seed,
                  "split_seed_independent": False, "model_seed": None},
        "seed_note": "Existing generator couples dataset and split seeds; matchers are deterministic.",
        "source_revision": revision,
        "source_snapshot_matches_revision": all(s["matches_revision"] for s in sources.values()),
        "working_tree_status": _git("status", "--porcelain", "--untracked-files=normal").decode(),
        "source_files": sources, "command": command or [sys.executable, *sys.argv],
        "python_version": sys.version, "platform": platform.platform(),
        "dependencies": dict(sorted((d.metadata["Name"], d.version) for d in distributions() if d.metadata["Name"])),
        "coverage_limits": [
            "Existing four duplicate variants and four hard-negative mechanisms only; not the complete protocol matrix.",
            "Hard negatives preferentially populate test, not validation; no generator changes were made.",
            "AP is within each method's candidate universe, not a shared end-to-end ranking.",
            "No independent validation campaign, expert review, protocol freeze, or holdout assessment.",
            "Python allocation peaks exclude native process RSS; timing measurements are observations, not reproducible constants.",
        ],
    }
    payload["metadata.json"] = metadata
    for name, value in payload.items():
        (output_dir / name).write_bytes(_json_bytes(value))
    if snapshots != _source_snapshots() or revision != _git("rev-parse", "HEAD").decode().strip():
        raise RuntimeError("source changed during evidence generation; artifact is incomplete")
    manifest = {"algorithm": "sha256", "files": {
        path.relative_to(output_dir).as_posix(): sha256(path.read_bytes()).hexdigest()
        for path in sorted(output_dir.rglob("*")) if path.is_file()
    }}
    (output_dir / "manifest.json").write_bytes(_json_bytes(manifest))
    return output_dir


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--employee-count", type=int, default=1000)
    parser.add_argument("--anomaly-rate", type=float, default=0.10)
    parser.add_argument("--rare-legitimate-rate", type=float, default=0.05)
    parser.add_argument("--output-dir", type=Path, default=Path("research_outputs/duplicate_development"))
    args = parser.parse_args()
    config = ExperimentConfig(seed=args.seed, employee_count=args.employee_count,
                              anomaly_rate=args.anomaly_rate, rare_legitimate_rate=args.rare_legitimate_rate)
    config.validate()
    source_hashes = {name: sha256((REPO_ROOT / name).read_bytes()).hexdigest() for name in SOURCE_PATHS}
    digest = sha256(_json_bytes({"config": asdict(config), "sources": source_hashes, "schema": SCHEMA})).hexdigest()[:16]
    target = args.output_dir / f"duplicate_development_{digest}"
    if target.exists():
        raise FileExistsError(f"Artifact already exists: {target}")
    dataset = generate_synthetic_dataset(config)
    print(write_artifact(dataset, target, configuration=asdict(config), expected_source_hashes=source_hashes))


if __name__ == "__main__":
    main()
