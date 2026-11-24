from __future__ import annotations

import json
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest

from src.research import holdout_gate
from scripts.run_tdk_independent_development import _staged_artifact_directory


COMMIT = "a" * 40
MATRIX_SHA256 = "b" * 64


def _evidence(tmp_path, name: str) -> tuple[str, str]:
    path = tmp_path / name
    path.write_text(f"verified evidence: {name}\n", encoding="utf-8")
    return str(path), sha256(path.read_bytes()).hexdigest()


def _authorization(tmp_path) -> dict:
    supervisor_path, supervisor_hash = _evidence(tmp_path, "supervisor.txt")
    first_path, first_hash = _evidence(tmp_path, "review-one.txt")
    second_path, second_hash = _evidence(tmp_path, "review-two.txt")
    return {
        "protocol_status": "frozen",
        "frozen_git_commit": COMMIT,
        "matrix_sha256": MATRIX_SHA256,
        "supervisor_approval": {
            "date": "2026-11-23",
            "evidence_path": supervisor_path,
            "checksum_sha256": supervisor_hash,
        },
        "reviewers": [
            {
                "reviewer_id": "reviewer-a",
                "qualification": "HR policy specialist",
                "blinded_review": {
                    "status": "completed",
                    "evidence_path": first_path,
                    "checksum_sha256": first_hash,
                },
            },
            {
                "reviewer_id": "reviewer-b",
                "qualification": "Information systems specialist",
                "blinded_review": {
                    "status": "completed",
                    "evidence_path": second_path,
                    "checksum_sha256": second_hash,
                },
            },
        ],
        "one_time_authorization": True,
    }


def _write_authorization(tmp_path, record=None):
    path = tmp_path / "authorization.json"
    path.write_text(json.dumps(record or _authorization(tmp_path)), encoding="utf-8")
    return path


def _clean_repository(monkeypatch):
    monkeypatch.setattr(
        holdout_gate,
        "inspect_repository",
        lambda _repository: holdout_gate.RepositoryState(commit=COMMIT, clean=True),
    )
    monkeypatch.setattr(holdout_gate, "_is_within", lambda _path, _root: False)


def test_valid_record_is_consumed_once_and_finalized_without_identity_change(
    tmp_path, monkeypatch
):
    _clean_repository(monkeypatch)
    authorization = _write_authorization(tmp_path)
    ledger = tmp_path / "ledger.json"

    attempt = holdout_gate.begin_holdout_attempt(
        authorization,
        ledger,
        repository=tmp_path,
        expected_matrix_sha256=MATRIX_SHA256,
    )
    started = json.loads(ledger.read_text(encoding="utf-8"))
    holdout_gate.finalize_holdout_attempt(attempt, success=True, detail="verified")
    finished = json.loads(ledger.read_text(encoding="utf-8"))

    assert finished["state"] == "succeeded"
    assert finished["outcome"] == {"success": True, "detail": "verified"}
    for field in (
        "attempt_id",
        "authorization_sha256",
        "frozen_git_commit",
        "matrix_sha256",
        "started_at_utc",
    ):
        assert finished[field] == started[field]

    with pytest.raises(holdout_gate.HoldoutAlreadyConsumedError):
        holdout_gate.begin_holdout_attempt(
            authorization,
            ledger,
            repository=tmp_path,
            expected_matrix_sha256=MATRIX_SHA256,
        )
    with pytest.raises(holdout_gate.LedgerStateError):
        holdout_gate.finalize_holdout_attempt(attempt, success=False)


def test_failed_attempt_is_final_and_cannot_be_reused(tmp_path, monkeypatch):
    _clean_repository(monkeypatch)
    ledger = tmp_path / "ledger.json"
    attempt = holdout_gate.begin_holdout_attempt(
        _write_authorization(tmp_path),
        ledger,
        repository=tmp_path,
        expected_matrix_sha256=MATRIX_SHA256,
    )

    holdout_gate.finalize_holdout_attempt(attempt, success=False, detail="runner failed")

    saved = json.loads(ledger.read_text(encoding="utf-8"))
    assert saved["state"] == "failed"
    assert saved["outcome"]["success"] is False
    assert ledger.exists()


def test_artifact_publication_finalizes_success_only_after_publish(tmp_path, monkeypatch):
    _clean_repository(monkeypatch)
    ledger = tmp_path / "publish-ledger.json"
    attempt = holdout_gate.begin_holdout_attempt(
        _write_authorization(tmp_path),
        ledger,
        repository=tmp_path,
        expected_matrix_sha256=MATRIX_SHA256,
    )
    final_dir = tmp_path / "published"

    with _staged_artifact_directory(final_dir, attempt) as staging:
        assert json.loads(ledger.read_text(encoding="utf-8"))["state"] == "started"
        (staging / "manifest.json").write_text("{}", encoding="utf-8")

    assert final_dir.is_dir()
    assert json.loads(ledger.read_text(encoding="utf-8"))["state"] == "succeeded"


def test_artifact_publication_failure_finalizes_failed(tmp_path, monkeypatch):
    _clean_repository(monkeypatch)
    ledger = tmp_path / "failure-ledger.json"
    attempt = holdout_gate.begin_holdout_attempt(
        _write_authorization(tmp_path),
        ledger,
        repository=tmp_path,
        expected_matrix_sha256=MATRIX_SHA256,
    )

    with pytest.raises(RuntimeError, match="synthetic failure"):
        with _staged_artifact_directory(tmp_path / "never-published", attempt):
            raise RuntimeError("synthetic failure")

    assert not (tmp_path / "never-published").exists()
    assert json.loads(ledger.read_text(encoding="utf-8"))["state"] == "failed"


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda record: record.update(protocol_status="draft"), "protocol_status"),
        (lambda record: record.update(one_time_authorization=False), "one_time_authorization"),
        (lambda record: record.pop("supervisor_approval"), "supervisor_approval"),
        (
            lambda record: record["supervisor_approval"].update(date="23/11/2026"),
            "YYYY-MM-DD",
        ),
        (
            lambda record: record["supervisor_approval"].update(evidence_path=""),
            "supervisor_approval.evidence_path",
        ),
        (lambda record: record.update(reviewers=record["reviewers"][:1]), "exactly two"),
        (
            lambda record: record["reviewers"][1].update(reviewer_id="REVIEWER-A"),
            "distinct",
        ),
        (
            lambda record: record["reviewers"][0].update(qualification=""),
            "qualification",
        ),
        (
            lambda record: record["reviewers"][0]["blinded_review"].update(
                status="pending"
            ),
            "completed",
        ),
        (
            lambda record: record["reviewers"][0]["blinded_review"].update(
                evidence_path=""
            ),
            "evidence_path",
        ),
        (
            lambda record: record["reviewers"][0]["blinded_review"].update(
                checksum_sha256="bad"
            ),
            "SHA-256",
        ),
    ],
)
def test_missing_or_invalid_authorization_fields_are_rejected(
    tmp_path, monkeypatch, mutate, message
):
    _clean_repository(monkeypatch)
    record = _authorization(tmp_path)
    mutate(record)

    with pytest.raises(holdout_gate.InvalidAuthorizationError, match=message):
        holdout_gate.begin_holdout_attempt(
            _write_authorization(tmp_path, record),
            tmp_path / "ledger.json",
            repository=tmp_path,
            expected_matrix_sha256=MATRIX_SHA256,
        )


def test_wrong_revision_dirty_tree_and_matrix_mismatch_are_rejected(tmp_path, monkeypatch):
    _clean_repository(monkeypatch)
    authorization = _write_authorization(tmp_path)
    ledger = tmp_path / "ledger.json"

    monkeypatch.setattr(
        holdout_gate,
        "inspect_repository",
        lambda _repository: holdout_gate.RepositoryState(commit="e" * 40, clean=True),
    )
    with pytest.raises(holdout_gate.InvalidAuthorizationError, match="revision"):
        holdout_gate.begin_holdout_attempt(
            authorization,
            ledger,
            repository=tmp_path,
            expected_matrix_sha256=MATRIX_SHA256,
        )

    monkeypatch.setattr(
        holdout_gate,
        "inspect_repository",
        lambda _repository: holdout_gate.RepositoryState(commit=COMMIT, clean=False),
    )
    with pytest.raises(holdout_gate.InvalidAuthorizationError, match="clean"):
        holdout_gate.begin_holdout_attempt(
            authorization,
            ledger,
            repository=tmp_path,
            expected_matrix_sha256=MATRIX_SHA256,
        )

    _clean_repository(monkeypatch)
    with pytest.raises(holdout_gate.InvalidAuthorizationError, match="matrix checksum"):
        holdout_gate.begin_holdout_attempt(
            authorization,
            ledger,
            repository=tmp_path,
            expected_matrix_sha256="f" * 64,
        )
    assert not ledger.exists()


def test_authorization_and_evidence_must_be_external_and_checksum_valid(
    tmp_path, monkeypatch
):
    repository = tmp_path / "repo"
    repository.mkdir()
    record = _authorization(tmp_path)
    inside = repository / "authorization.json"
    inside.write_text(json.dumps(record), encoding="utf-8")

    with pytest.raises(holdout_gate.InvalidAuthorizationError, match="outside"):
        holdout_gate.begin_holdout_attempt(
            inside,
            tmp_path / "inside-ledger.json",
            repository=repository,
            expected_matrix_sha256=MATRIX_SHA256,
        )

    _clean_repository(monkeypatch)
    authorization = _write_authorization(tmp_path, record)
    Path(record["reviewers"][0]["blinded_review"]["evidence_path"]).write_text(
        "tampered\n",
        encoding="utf-8",
    )
    with pytest.raises(holdout_gate.InvalidAuthorizationError, match="checksum"):
        holdout_gate.begin_holdout_attempt(
            authorization,
            tmp_path / "tampered-ledger.json",
            repository=repository,
            expected_matrix_sha256=MATRIX_SHA256,
        )


def test_malformed_json_and_tampered_ledger_are_rejected(tmp_path, monkeypatch):
    _clean_repository(monkeypatch)
    malformed = tmp_path / "bad.json"
    malformed.write_text("not json", encoding="utf-8")
    with pytest.raises(holdout_gate.InvalidAuthorizationError, match="cannot read"):
        holdout_gate.begin_holdout_attempt(
            malformed,
            tmp_path / "ledger.json",
            repository=tmp_path,
            expected_matrix_sha256=MATRIX_SHA256,
        )

    authorization = _write_authorization(tmp_path)
    ledger = tmp_path / "other-ledger.json"
    attempt = holdout_gate.begin_holdout_attempt(
        authorization,
        ledger,
        repository=tmp_path,
        expected_matrix_sha256=MATRIX_SHA256,
    )
    tampered = json.loads(ledger.read_text(encoding="utf-8"))
    tampered["attempt_id"] = "different"
    ledger.write_text(json.dumps(tampered), encoding="utf-8")

    with pytest.raises(holdout_gate.LedgerStateError, match="identity"):
        holdout_gate.finalize_holdout_attempt(attempt, success=True)


def test_attempt_handle_identity_cannot_finalize_another_ledger(tmp_path, monkeypatch):
    _clean_repository(monkeypatch)
    authorization = _write_authorization(tmp_path)
    first = holdout_gate.begin_holdout_attempt(
        authorization,
        tmp_path / "first.json",
        repository=tmp_path,
        expected_matrix_sha256=MATRIX_SHA256,
    )
    forged = replace(first, attempt_id="not-the-first-attempt")

    with pytest.raises(holdout_gate.LedgerStateError, match="identity"):
        holdout_gate.finalize_holdout_attempt(forged, success=True)
