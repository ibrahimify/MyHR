"""Duplicate-only evidence contracts, including rehashed semantic tampering."""

from dataclasses import replace
from datetime import date
from hashlib import sha256
import json
from math import nextafter
from pathlib import Path
import subprocess
import sys
import tracemalloc

import pytest

from scripts import run_tdk_duplicate_development as producer
from scripts.audit_tdk_duplicate_artifact import DuplicateAuditError, audit_artifact
from scripts.run_tdk_duplicate_development import (
    build_evidence,
    calibrate_threshold,
    write_artifact,
)
from src.services.anomaly_detection import synthetic_data as syn


def record(key, split, *, parent=None, latent=None, name="Alex Stone",
           dob=date(1990, 1, 1), nid="00123", email="a@example.test",
           hard=None, anchor=None):
    return syn.WorkforceHistoryRecord(
        identity=syn.EmployeeIdentity(key, name, dob, nid, email),
        split=split, employment_track=syn.EmploymentTrack.OTHER,
        current_level=None, department="Synthetic", role="Test",
        hire_date=date(2020, 1, 1), events=(),
        duplicate_of_employee_id=parent, latent_person_id=latent,
        hard_nonduplicate_kind=hard, hard_nonduplicate_anchor_id=anchor,
    )


def dataset(records):
    return syn.SyntheticDataset(tuple(records), syn.SyntheticDatasetMetadata(
        schema_version="test-fixture", run_id="hand-calculated", seed=7,
        employee_count=len(records),
        split_counts={s.value: sum(r.split is s for r in records) for s in syn.DatasetSplit},
        label_counts={},
    ))


@pytest.fixture
def histories():
    v, t = syn.DatasetSplit.VALIDATION, syn.DatasetSplit.TEST
    return dataset([
        record("V1", v, latent="LV"),
        record("V2", v, parent="V1", latent="LV"),
        record("T1", t, latent="LT"),
        record("T2", t, parent="T1", latent="LT"),
        record("T3", t, parent="T1", latent="LT"),
        record("T4", t, name="Alex South", nid="999", email=None,
               hard=syn.HardNonduplicateKind.SHARED_BIRTHDAY, anchor="T1"),
    ])


def publish(tmp_path, histories):
    return write_artifact(histories, tmp_path / "evidence", configuration={"fixture": True},
                          data_origin="hand_calculated_test_fixture")


def rewrite(path, name, mutate, *, rehash=True):
    target = path / name
    obj = json.loads(target.read_text(encoding="utf-8"))
    mutate(obj)
    target.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    if rehash:
        manifest_path = path / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["files"][name] = sha256(target.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")


def test_hand_calculated_cluster_siblings_and_hard_negative(tmp_path, histories):
    payload = build_evidence(histories)
    rows = [r for r in payload["metrics.json"] if r["partition"] == "test"]
    for row in rows:
        assert row["record_count"] == 4
        assert row["total_pair_count"] == 6
        assert row["true_pair_count"] == 3
        assert row["end_to_end"]["true_positives"] == 3
        assert row["end_to_end"]["false_positives"] == 0
        assert row["end_to_end"]["false_negatives"] == 0
    path = publish(tmp_path, histories)
    report = audit_artifact(path)
    assert report["verified"] is False
    assert report["verification_status"] == "arithmetic_verified_test_fixture"
    assert not any("latent" in r or "duplicate_of" in r for r in payload["identities.json"])


def test_validation_only_and_test_changes_cannot_change_selection(histories):
    expected = calibrate_threshold(histories)
    modified = dataset([
        replace(r, identity=replace(r.identity, full_name="Different", national_id=None, email=None))
        if r.split is syn.DatasetSplit.TEST else r for r in histories.records
    ])
    assert calibrate_threshold(modified) == expected
    with pytest.raises(ValueError, match="validation"):
        calibrate_threshold(histories, split=syn.DatasetSplit.TEST)


def test_threshold_scoring_receives_no_truth_fields(histories, monkeypatch):
    original = producer.find_similarity_duplicate_candidates

    def guarded(records, *args, **kwargs):
        assert all(record.duplicate_of_employee_id is None for record in records)
        assert all(record.latent_person_id is None for record in records)
        assert all(record.hard_nonduplicate_kind is None for record in records)
        assert all(record.hard_nonduplicate_anchor_id is None for record in records)
        assert all(record.anomaly_labels == (syn.AnomalyType.CLEAN,) for record in records)
        return original(records, *args, **kwargs)

    monkeypatch.setattr(producer, "find_similarity_duplicate_candidates", guarded)
    assert calibrate_threshold(histories)["status"] == "selected"


def test_mixed_score_validation_selects_existing_f1_optimum(tmp_path):
    v = syn.DatasetSplit.VALIDATION
    data = dataset([
        record("A", v, latent="L"),
        record("B", v, parent="A", latent="L", email=None),
        record("C", v, name="Alex South", nid="999", email=None),
    ])
    selection = calibrate_threshold(data)
    # One true pair: .35 name + .30 birth date + .25 ID + 0 missing email.
    assert selection["threshold"] == pytest.approx(0.90)
    assert len(selection["search"]) >= 2
    chosen = next(r for r in selection["search"] if r["threshold"] == selection["threshold"])
    assert chosen["true_positives"] == 1 and chosen["false_positives"] == 0
    assert chosen["f1"] == 1.0
    assert audit_artifact(publish(tmp_path, data))["verification_status"] == "arithmetic_verified_test_fixture"


@pytest.mark.parametrize("mode", ["empty", "no_pairs", "no_positives", "blocking_miss"])
def test_uninformative_validation_does_not_invent_threshold(tmp_path, mode):
    v = syn.DatasetSplit.VALIDATION
    records = [] if mode == "empty" else [record("A", v)]
    if mode in {"no_positives", "blocking_miss"}:
        records.append(record("B", v, parent="A" if mode == "blocking_miss" else None,
                              name="Zoe West" if mode == "blocking_miss" else "Alex Stone",
                              dob=date(1980, 2, 2), nid="XYZ", email=None))
    data = dataset(records)
    selection = calibrate_threshold(data)
    assert selection["threshold"] is None
    assert selection["status"] != "selected"
    path = publish(tmp_path, data)
    assert audit_artifact(path)["verification_status"] == "arithmetic_verified_test_fixture"
    similarity = [r for r in build_evidence(data)["metrics.json"] if r["method"] == "similarity"]
    assert all(r["end_to_end"] is None for r in similarity)


def test_blocking_miss_affects_end_to_end_not_candidate_counts(tmp_path, histories):
    t = syn.DatasetSplit.TEST
    records = list(histories.records[:2]) + [
        record("A", t, latent="L"),
        record("B", t, parent="A", latent="L", name="Zoe West",
               dob=date(1980, 2, 2), nid="XYZ", email="z@example.test"),
    ]
    data = dataset(records)
    row = next(r for r in build_evidence(data)["metrics.json"]
               if r["partition"] == "test" and r["method"] == "similarity")
    assert row["blocking_recall"] == 0
    assert row["end_to_end"]["false_negatives"] == 1
    assert row["candidate"]["false_negatives"] == 0
    assert row["candidate_average_precision"] is None
    assert audit_artifact(publish(tmp_path, data))["verification_status"] == "arithmetic_verified_test_fixture"


def test_ties_missing_values_and_zero_positive_evaluation(tmp_path, histories):
    t = syn.DatasetSplit.TEST
    data = dataset(list(histories.records[:2]) + [
        record("A", t, nid=None, email=None),
        record("B", t, nid=None, email=None),
        record("C", t, nid=None, email=None),
    ])
    payload = build_evidence(data)
    pairs = [p for p in payload["pairs.json"] if p["partition"] == "test"]
    assert all(p["scores"]["similarity"] == pytest.approx(0.65) for p in pairs)
    row = next(r for r in payload["metrics.json"] if r["partition"] == "test" and r["method"] == "similarity")
    assert row["end_to_end"]["recall"] is None
    assert row["candidate_average_precision"] is None
    assert audit_artifact(publish(tmp_path, data))["verification_status"] == "arithmetic_verified_test_fixture"


def test_average_precision_groups_tied_positive_and_negative_pairs(tmp_path, histories):
    t = syn.DatasetSplit.TEST
    data = dataset(list(histories.records[:2]) + [
        record("A", t, latent="L"), record("B", t, parent="A", latent="L"), record("C", t),
    ])
    rows = [r for r in build_evidence(data)["metrics.json"] if r["partition"] == "test"]
    for row in rows:
        assert row["candidate_average_precision"] == pytest.approx(1 / 3)
        assert row["end_to_end"]["true_positives"] == 1
        assert row["end_to_end"]["false_positives"] == 2
    assert audit_artifact(publish(tmp_path, data))["verification_status"] == "arithmetic_verified_test_fixture"


@pytest.mark.parametrize("defect", ["cross_partition", "dangling", "cycle", "duplicate_id", "latent_conflict", "hard_truth"])
def test_invalid_identity_truth_is_rejected(histories, defect):
    records = list(histories.records)
    if defect == "cross_partition":
        records[1] = replace(records[1], split=syn.DatasetSplit.TEST)
    elif defect == "dangling":
        records[1] = replace(records[1], duplicate_of_employee_id="MISSING")
    elif defect == "cycle":
        records[0] = replace(records[0], duplicate_of_employee_id="V2")
    elif defect == "duplicate_id":
        records.append(records[0])
    elif defect == "latent_conflict":
        records[1] = replace(records[1], latent_person_id="OTHER")
    else:
        records[3] = replace(records[3], hard_nonduplicate_kind=syn.HardNonduplicateKind.SIMILAR_NAME,
                             hard_nonduplicate_anchor_id="T1")
    with pytest.raises(ValueError):
        build_evidence(dataset(records))


def test_memory_unavailable_when_tracing_is_owned_by_caller(histories):
    tracemalloc.start()
    try:
        payload = build_evidence(histories)
        assert tracemalloc.is_tracing()
        assert all(r["resources"]["peak_python_bytes"] is None for r in payload["metrics.json"])
        assert all(r["resources"]["memory_status"] == "unavailable_caller_tracing"
                   for r in payload["metrics.json"])
    finally:
        tracemalloc.stop()


def test_write_once(tmp_path, histories):
    path = publish(tmp_path, histories)
    before = (path / "manifest.json").read_bytes()
    with pytest.raises(FileExistsError):
        publish(tmp_path, histories)
    assert (path / "manifest.json").read_bytes() == before


def test_auditor_is_read_only(tmp_path, histories):
    path = publish(tmp_path, histories)
    before = {p.relative_to(path): p.read_bytes() for p in path.rglob("*") if p.is_file()}
    assert audit_artifact(path)["verification_status"] == "arithmetic_verified_test_fixture"
    assert {p.relative_to(path): p.read_bytes() for p in path.rglob("*") if p.is_file()} == before


def test_failed_artifact_has_no_completion_manifest_and_cannot_be_overwritten(tmp_path, histories):
    bad = dataset([replace(histories.records[0], duplicate_of_employee_id="missing")])
    target = tmp_path / "incomplete"
    with pytest.raises(ValueError, match="dangling"):
        write_artifact(bad, target, configuration={"fixture": True}, data_origin="hand_calculated_test_fixture")
    assert target.is_dir() and not (target / "manifest.json").exists()
    with pytest.raises(DuplicateAuditError):
        audit_artifact(target)
    with pytest.raises(FileExistsError):
        write_artifact(histories, target, configuration={"fixture": True}, data_origin="hand_calculated_test_fixture")


def test_source_drift_cannot_publish_completion_manifest(tmp_path, histories, monkeypatch):
    snapshots = producer._source_snapshots()
    changed = dict(snapshots)
    changed["scripts/run_tdk_duplicate_development.py"] += b"\n"
    readings = iter((snapshots, changed))
    monkeypatch.setattr(producer, "_source_snapshots", lambda: next(readings))
    target = tmp_path / "source-drift"
    with pytest.raises(RuntimeError, match="source changed"):
        write_artifact(histories, target, configuration={"fixture": True}, data_origin="hand_calculated_test_fixture")
    assert not (target / "manifest.json").exists()


def test_standalone_commands_with_existing_generator(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    command = [sys.executable, "scripts/run_tdk_duplicate_development.py", "--seed", "2026",
               "--employee-count", "80", "--output-dir", str(tmp_path)]
    completed = subprocess.run(command, cwd=repo, capture_output=True, text=True, check=True)
    artifact = Path(completed.stdout.strip())
    assert artifact.parent == tmp_path
    metadata = json.loads((artifact / "metadata.json").read_text(encoding="utf-8"))
    report = subprocess.run([sys.executable, "scripts/audit_tdk_duplicate_artifact.py", str(artifact)],
                            cwd=repo, capture_output=True, text=True)
    if metadata["source_snapshot_matches_revision"]:
        assert report.returncode == 0
        assert json.loads(report.stdout)["verified"] is True
    else:
        assert report.returncode != 0
        assert "do not match the recorded source revision" in report.stderr
    assert metadata["data_origin"] == "existing_synthetic_generator"
    assert metadata["generation_verification"] == "regenerated_and_matched"
    assert metadata["configuration"]["employee_count"] == 80
    assert metadata["command"] == command
    before = (artifact / "manifest.json").read_bytes()
    assert subprocess.run(command, cwd=repo, capture_output=True).returncode != 0
    assert (artifact / "manifest.json").read_bytes() == before


def test_generated_origin_rejects_dataset_not_created_by_recorded_configuration(tmp_path, histories):
    config = syn.ExperimentConfig(seed=2026, employee_count=80)
    with pytest.raises(ValueError, match="does not match"):
        write_artifact(
            histories,
            tmp_path / "false-origin",
            configuration={
                "seed": config.seed,
                "employee_count": config.employee_count,
                "anomaly_rate": config.anomaly_rate,
                "rare_legitimate_rate": config.rare_legitimate_rate,
                "train_ratio": config.train_ratio,
                "validation_ratio": config.validation_ratio,
                "test_ratio": config.test_ratio,
            },
            data_origin="existing_synthetic_generator",
        )
    assert not (tmp_path / "false-origin" / "manifest.json").exists()


@pytest.mark.parametrize("name,mutate", [
    ("pairs.json", lambda x: x.pop()),
    ("pairs.json", lambda x: x.append(x[0])),
    ("pairs.json", lambda x: x[0]["scores"].update(similarity=0.123)),
    ("pairs.json", lambda x: x[0]["scores"].update(similarity=nextafter(x[0]["scores"]["similarity"], 0))),
    ("pairs.json", lambda x: x[0]["predictions"].update(similarity=False)),
    ("threshold_search.json", lambda x: x.update(threshold=0.1)),
    ("metrics.json", lambda x: x[0].update(true_pair_count=999)),
    ("truth.json", lambda x: x[1].update(duplicate_of_employee_id="missing")),
    ("truth.json", lambda x: x[1].update(latent_person_id="other")),
    ("truth.json", lambda x: x[-1].update(hard_nonduplicate_anchor_id="missing")),
    ("identities.json", lambda x: next(r for r in x if r["employee_id"] == "V2").update(partition="test")),
    ("identities.json", lambda x: x[0].update(partition="holdout")),
    ("metadata.json", lambda x: x.update(holdout_accessed=True)),
    ("metadata.json", lambda x: x["partition_roles"].update(test="final_holdout")),
])
def test_auditor_rejects_rehashed_semantic_tamper(tmp_path, histories, name, mutate):
    path = publish(tmp_path, histories)
    rewrite(path, name, mutate)
    with pytest.raises(DuplicateAuditError):
        audit_artifact(path)


def test_checksum_extra_file_and_snapshot_tamper(tmp_path, histories):
    path = publish(tmp_path, histories)
    rewrite(path, "pairs.json", lambda x: x.pop(), rehash=False)
    with pytest.raises(DuplicateAuditError, match="checksum"):
        audit_artifact(path)


def test_unexpected_file_is_rejected(tmp_path, histories):
    path = publish(tmp_path, histories)
    (path / "unexpected.txt").write_text("extra", encoding="utf-8")
    with pytest.raises(DuplicateAuditError, match="file"):
        audit_artifact(path)


def test_source_snapshot_is_independently_checked(tmp_path, histories):
    path = publish(tmp_path, histories)
    target = path / "sources/src/services/anomaly_detection/duplicate_detection.py"
    target.write_text("changed", encoding="utf-8")
    manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    manifest["files"][target.relative_to(path).as_posix()] = sha256(target.read_bytes()).hexdigest()
    (path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(DuplicateAuditError, match="source"):
        audit_artifact(path)
