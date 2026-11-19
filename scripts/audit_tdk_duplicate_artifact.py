"""Reconstruct duplicate development evidence without importing its producer."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
from difflib import SequenceMatcher
from hashlib import sha256
from itertools import combinations, groupby
import json
from math import isclose, isfinite
from pathlib import Path
import subprocess

METHODS = ("exact", "normalized_exact", "similarity")
ROLES = {"train": "unused_by_duplicate_matchers",
         "validation": "similarity_threshold_selection_only",
         "test": "development_evaluation_not_final_holdout"}
SOURCES = (
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
FILES = {"metadata.json", "identities.json", "truth.json", "pairs.json",
         "threshold_search.json", "metrics.json"} | {"sources/" + name for name in SOURCES}


class DuplicateAuditError(ValueError):
    """Stored evidence is incomplete, inconsistent, or outside this development contract."""


def _require(condition, message):
    if not condition:
        raise DuplicateAuditError(message)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _read(path):
    def reject(value):
        raise DuplicateAuditError(f"nonfinite JSON: {value}")
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object,
                      parse_constant=reject)


def _equal(actual, expected, location):
    if isinstance(expected, dict):
        _require(isinstance(actual, dict) and actual.keys() == expected.keys(), f"{location}: keys differ")
        for key in expected:
            _equal(actual[key], expected[key], f"{location}.{key}")
    elif isinstance(expected, list):
        _require(isinstance(actual, list) and len(actual) == len(expected), f"{location}: rows differ")
        for index, (left, right) in enumerate(zip(actual, expected)):
            _equal(left, right, f"{location}[{index}]")
    elif isinstance(expected, float):
        exact = ".scores." in location or location.endswith(".threshold")
        _require(type(actual) in (int, float) and isfinite(actual)
                 and (actual == expected if exact else isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12)),
                 f"{location}: number differs")
    else:
        _require(type(actual) is type(expected) and actual == expected, f"{location}: value differs")


def _text(value):
    return " ".join((value or "").casefold().strip().split())


def _identifier(value):
    value = _text(value)
    if "-" in value:
        prefix, suffix = value.split("-", 1)
        return prefix + "-" + (suffix.lstrip("0") or "0")
    return value.lstrip("0") or value


def _similarity(a, b):
    a, b = _text(a), _text(b)
    return SequenceMatcher(None, a, b).ratio() if a and b else 0.0


def _pair_values(left, right):
    ln, rn = _text(left["full_name"]), _text(right["full_name"])
    li, ri = _identifier(left["national_id"]), _identifier(right["national_id"])
    dob = left["date_of_birth"] is not None and left["date_of_birth"] == right["date_of_birth"]
    blocked = bool(dob or li and li == ri or ln and rn and (ln == rn or ln.split()[0] == rn.split()[0]))
    exact = any(left[field] and left[field] == right[field] for field in ("national_id", "email"))
    normalized = bool(li and li == ri or _text(left["email"]) and _text(left["email"]) == _text(right["email"]))
    if not li or not ri:
        id_score = 0.0
    elif li == ri:
        id_score = 1.0
    else:
        ld = "".join(c for c in li if c in "0123456789")
        rd = "".join(c for c in ri if c in "0123456789")
        id_score = 0.95 if ld and rd and ld == rd else _similarity(li, ri)
    score = (0.35 * _similarity(ln, rn) + 0.30 * float(dob)
             + 0.25 * id_score + 0.10 * _similarity(left["email"], right["email"]))
    return blocked, {"exact": float(bool(exact)), "normalized_exact": float(normalized),
                     "similarity": score if blocked else None}


def _truth(identities, rows):
    by_id = {}
    fields = {"employee_id", "partition", "full_name", "date_of_birth", "national_id", "email"}
    for row in identities:
        _require(set(row) == fields, "identity fields differ or include evaluation truth")
        key = row["employee_id"]
        _require(isinstance(key, str) and key and key not in by_id, "duplicate/empty employee ID")
        _require(row["partition"] in ROLES, "unknown identity partition")
        for field in ("full_name", "national_id", "email"):
            _require(row[field] is None or isinstance(row[field], str), "invalid identity field")
        if row["date_of_birth"] is not None:
            date.fromisoformat(row["date_of_birth"])
        by_id[key] = row
    truth = {}
    fields = {"employee_id", "cluster_root", "duplicate_of_employee_id", "latent_person_id",
              "hard_nonduplicate_kind", "hard_nonduplicate_anchor_id"}
    for row in rows:
        _require(set(row) == fields and row["employee_id"] not in truth, "duplicate/invalid truth row")
        truth[row["employee_id"]] = row
    _require(truth.keys() == by_id.keys(), "identity/truth membership differs")
    roots = {}
    for key in by_id:
        current, visited = key, set()
        while truth[current]["duplicate_of_employee_id"] is not None:
            _require(current not in visited, "duplicate truth cycle")
            visited.add(current)
            current = truth[current]["duplicate_of_employee_id"]
            _require(current in by_id, "dangling truth link")
            _require(by_id[current]["partition"] == by_id[key]["partition"], "cluster partition leakage")
        roots[key] = current
        _require(truth[key]["cluster_root"] == current, "stored cluster root differs")
    latent_roots = {}
    for key, row in truth.items():
        latent = row["latent_person_id"]
        _require(latent == truth[roots[key]]["latent_person_id"], "latent/linked truth differs")
        if latent is not None:
            _require(isinstance(latent, str) and latent, "invalid latent identity")
            _require(latent_roots.setdefault(latent, roots[key]) == roots[key], "latent entity leaks across clusters")
        kind, anchor = row["hard_nonduplicate_kind"], row["hard_nonduplicate_anchor_id"]
        _require((kind is None) == (anchor is None), "incomplete hard nonduplicate evidence")
        if kind is not None:
            _require(kind in {"similar_name", "shared_birthday", "relative", "near_identical_id"}, "unknown hard-negative kind")
            _require(anchor in by_id and anchor != key, "dangling hard-negative anchor")
            _require(by_id[anchor]["partition"] == by_id[key]["partition"], "hard-negative partition leakage")
            _require(roots[anchor] != roots[key] and latent is None, "hard negative is a true duplicate")
    return by_id, roots


def _metrics(selected, truth, universe):
    cells = Counter()
    for pair in universe:
        cells[(pair in truth, pair in selected)] += 1
    tp, fp, tn, fn = cells[True, True], cells[False, True], cells[False, False], cells[True, False]
    return {"true_positives": tp, "false_positives": fp, "true_negatives": tn, "false_negatives": fn,
            "precision": tp / (tp + fp) if tp + fp else None,
            "recall": tp / (tp + fn) if tp + fn else None,
            "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None,
            "false_positive_rate": fp / (fp + tn) if fp + tn else None}


def _ap(scores, truth):
    positives = sum(p in truth for p in scores)
    if not positives:
        return None
    seen = found = 0
    area = 0.0
    for _, group in groupby(sorted(scores, key=scores.get, reverse=True), key=scores.get):
        group = list(group)
        new = sum(pair in truth for pair in group)
        seen += len(group)
        found += new
        area += (new / positives) * (found / seen)
    return area


def _resources(row):
    fields = {"blocking_time_s", "scoring_time_s", "evaluation_time_s", "peak_python_bytes", "memory_status", "scope"}
    _require(set(row["resources"]) == fields, "resource fields differ")
    r = row["resources"]
    for name in ("scoring_time_s", "evaluation_time_s"):
        _require(type(r[name]) in (float, int) and isfinite(r[name]) and r[name] >= 0, "invalid timing")
    if row["method"] == "similarity":
        value = r["blocking_time_s"]
        _require(type(value) in (float, int) and isfinite(value) and value >= 0, "invalid blocking timing")
    else:
        _require(r["blocking_time_s"] is None, "exact methods have no blocking phase")
    _require(r["evaluation_time_s"] >= r["scoring_time_s"] + (r["blocking_time_s"] or 0), "timing scope inconsistent")
    _require(r["scope"] == "identity_projection_through_metrics_excludes_generation_calibration_export", "resource scope differs")
    if r["memory_status"] == "unavailable_caller_tracing":
        _require(r["peak_python_bytes"] is None, "unavailable memory represented as a measurement")
    else:
        _require(r["memory_status"] == "measured_python_allocations" and type(r["peak_python_bytes"]) is int
                 and r["peak_python_bytes"] >= 0, "invalid Python memory measurement")


def audit_artifact(run_dir, *, repo_root=None):
    """Check integrity and independently reconstruct the complete duplicate result."""
    try:
        return _audit(Path(run_dir), Path(repo_root) if repo_root else Path(__file__).resolve().parents[1])
    except DuplicateAuditError:
        raise
    except (KeyError, TypeError, ValueError, OSError, subprocess.SubprocessError) as error:
        raise DuplicateAuditError(f"malformed evidence: {error}") from error


def _audit(path, repo_root):
    _require(path.is_dir() and not path.is_symlink(), "artifact must be a real directory")
    _require(not any(p.is_symlink() for p in path.rglob("*")), "artifact contains symbolic links")
    manifest = _read(path / "manifest.json")
    _require(manifest.keys() == {"algorithm", "files"} and manifest["algorithm"] == "sha256", "invalid manifest")
    _require(set(manifest["files"]) == FILES, "manifest file set differs")
    actual = {p.relative_to(path).as_posix() for p in path.rglob("*") if p.is_file()}
    _require(actual == FILES | {"manifest.json"}, "unexpected or missing artifact file")
    for name, digest in manifest["files"].items():
        _require(sha256((path / name).read_bytes()).hexdigest() == digest, f"checksum mismatch: {name}")
    metadata = _read(path / "metadata.json")
    _require(metadata["schema"] == "duplicate-development-evidence-v1", "unknown schema")
    _require(metadata["holdout_accessed"] is False and metadata["run_purpose"] == "duplicate_development"
             and metadata["protocol_status"] == "draft_holdout_locked", "development boundary violated")
    _equal(metadata["partition_roles"], ROLES, "partition roles")
    _require(metadata["data_origin"] in {"existing_synthetic_generator", "hand_calculated_test_fixture"}, "unknown data origin")
    _require(set(metadata["source_files"]) == set(SOURCES), "source inventory differs")
    matches = []
    revision = metadata["source_revision"]
    _require(isinstance(revision, str) and len(revision) == 40 and all(c in "0123456789abcdef" for c in revision), "invalid source revision")
    subprocess.run(("git", "cat-file", "-e", revision + "^{commit}"), cwd=repo_root, capture_output=True, check=True)
    for name, source in metadata["source_files"].items():
        snapshot = (path / "sources" / name).read_bytes()
        _require(sha256(snapshot).hexdigest() == source["sha256"], f"source checksum differs: {name}")
        stored = subprocess.run(("git", "show", f"{revision}:{name}"), cwd=repo_root, capture_output=True)
        match = stored.returncode == 0 and stored.stdout.replace(b"\r\n", b"\n") == snapshot.replace(b"\r\n", b"\n")
        _equal(source["matches_revision"], match, f"source revision: {name}")
        matches.append(match)
    _equal(metadata["source_snapshot_matches_revision"], all(matches), "source revision status")
    _equal(metadata["protocol_reference"], {"path": "docs/TDK_EXPERIMENT_PROTOCOL.md",
           "sha256": metadata["source_files"]["docs/TDK_EXPERIMENT_PROTOCOL.md"]["sha256"]}, "protocol reference")
    _require(isinstance(metadata["command"], list) and metadata["command"]
             and all(isinstance(x, str) for x in metadata["command"]), "missing command provenance")
    _require(isinstance(metadata["dependencies"], dict) and metadata["dependencies"]
             and metadata["python_version"] and metadata["platform"] and metadata["coverage_limits"], "missing environment/coverage provenance")
    identities = _read(path / "identities.json")
    by_id, roots = _truth(identities, _read(path / "truth.json"))
    _equal(metadata["dataset_metadata"]["employee_count"], len(by_id), "record count")
    _equal(metadata["dataset_metadata"]["split_counts"],
           {s: sum(r["partition"] == s for r in identities) for s in ROLES}, "split counts")
    seed = metadata["dataset_metadata"]["seed"]
    _equal(metadata["seeds"], {"dataset_seed": seed, "split_seed": seed,
                               "split_seed_independent": False, "model_seed": None}, "seed provenance")
    if metadata["data_origin"] == "existing_synthetic_generator":
        config = metadata["configuration"]
        _require(set(config) == {"seed", "employee_count", "anomaly_rate", "rare_legitimate_rate",
                                 "train_ratio", "validation_ratio", "test_ratio"}, "incomplete generator configuration")
        _equal(config["seed"], seed, "configuration seed")
        _equal(config["employee_count"], len(by_id), "configuration record count")
    expected_pairs, views = [], {}
    for partition in ("validation", "test"):
        ids = sorted(k for k in by_id if by_id[k]["partition"] == partition)
        universe = set(combinations(ids, 2))
        truth = {p for p in universe if roots[p[0]] == roots[p[1]]}
        scores, blocked = {m: {} for m in METHODS}, set()
        for pair in sorted(universe):
            is_blocked, values = _pair_values(by_id[pair[0]], by_id[pair[1]])
            if is_blocked:
                blocked.add(pair)
            for method in METHODS:
                if values[method] is not None:
                    scores[method][pair] = values[method]
            expected_pairs.append({"partition": partition, "left_employee_id": pair[0],
                                   "right_employee_id": pair[1], "similarity_blocked": is_blocked,
                                   "scores": values})
        views[partition] = (ids, universe, truth, scores, blocked)
    ids, universe, truth, scores, blocked = views["validation"]
    search = []
    for threshold in sorted(set(scores["similarity"].values()), reverse=True):
        selected = {p for p, score in scores["similarity"].items() if score >= threshold}
        search.append({"threshold": threshold, **_metrics(selected, truth, blocked)})
    status = ("empty_validation" if not ids else "no_blocked_pairs" if not blocked
              else "no_blocked_positive_pairs" if not truth & blocked else "selected")
    threshold = None
    if status == "selected":
        best = max(search, key=lambda r: (r["f1"] or 0, r["precision"] or 0, r["recall"] or 0, r["threshold"]))
        threshold = best["threshold"]
    _equal(_read(path / "threshold_search.json"), {
        "partition": "validation", "status": status, "threshold": threshold,
        "objective": "candidate_f1_then_precision_then_recall_then_higher_threshold",
        "record_count": len(ids), "true_pair_count": len(truth),
        "blocked_true_pair_count": len(truth & blocked), "search": search,
    }, "threshold search")
    for row in expected_pairs:
        row["predictions"] = {
            m: (None if m == "similarity" and threshold is None else
                row["scores"][m] is not None and row["scores"][m] >= (threshold if m == "similarity" else 1.0))
            for m in METHODS
        }
    _equal(_read(path / "pairs.json"), expected_pairs, "pairs")
    stored_metrics = _read(path / "metrics.json")
    _require(len(stored_metrics) == 6, "expected six partition/method metric rows")
    for row, (partition, method) in zip(stored_metrics, ((p, m) for p in views for m in METHODS)):
        ids, universe, truth, scores, blocked = views[partition]
        candidate_universe = blocked if method == "similarity" else universe
        available = method != "similarity" or threshold is not None
        selected = {p for p, value in scores[method].items() if value >= (threshold if method == "similarity" else 1.0)} if available else set()
        end = _metrics(selected, truth, universe) if available else None
        expected = {
            "partition": partition, "method": method,
            "threshold": threshold if method == "similarity" else None,
            "selection_status": "available" if available else "unavailable_validation_threshold",
            "record_count": len(ids), "total_pair_count": len(universe),
            "candidate_pair_count": len(candidate_universe), "true_pair_count": len(truth),
            "blocked_true_pair_count": len(candidate_universe & truth),
            "blocking_recall": len(candidate_universe & truth) / len(truth) if truth else None,
            "reduction_ratio": 1 - len(candidate_universe) / len(universe) if universe else None,
            "candidate_count": len(selected) if available else None,
            "candidates_per_1000_records": 1000 * len(selected) / len(ids) if ids and available else None,
            "false_matches_per_1000_records": 1000 * end["false_positives"] / len(ids) if ids and available else None,
            "candidate_average_precision": _ap(scores[method], truth),
            "end_to_end": end,
            "candidate": _metrics(selected, truth, candidate_universe) if available else None,
        }
        _resources(row)
        _equal({k: v for k, v in row.items() if k != "resources"}, expected, f"metrics {partition}/{method}")
    return {"verified": True, "run_purpose": "duplicate_development", "holdout_accessed": False,
            "records": len(by_id), "pair_rows": len(expected_pairs), "metric_rows": 6,
            "threshold_status": status, "source_snapshot_matches_revision": all(matches),
            "limitations": ["No dataset regeneration or truth-realism certification.",
                            "Resource values are structurally checked, not independently measured.",
                            "Self-contained hashes are integrity checks, not authenticated signatures."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    args = parser.parse_args()
    print(json.dumps(audit_artifact(args.artifact), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
