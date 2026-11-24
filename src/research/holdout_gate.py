"""Fail-closed authorization gate for a single holdout attempt.

This module does not generate, load, or score holdout data. It only validates
an external authorization record and records whether its one permitted attempt
has been consumed.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Mapping


_COMMIT_RE = re.compile(r"^[0-9a-fA-F]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_CAPABILITY_NONCE = object()


class HoldoutGateError(RuntimeError):
    """Base class for authorization and ledger failures."""


class InvalidAuthorizationError(HoldoutGateError):
    """Raised when an authorization record is incomplete or inconsistent."""


class HoldoutAlreadyConsumedError(HoldoutGateError):
    """Raised when the one permitted attempt already has a ledger."""


class LedgerStateError(HoldoutGateError):
    """Raised when a ledger cannot be finalized safely."""


@dataclass(frozen=True)
class RepositoryState:
    commit: str
    clean: bool


@dataclass(frozen=True)
class HoldoutAttempt:
    attempt_id: str
    authorization_sha256: str
    frozen_git_commit: str
    matrix_sha256: str
    ledger_path: Path
    _capability_nonce: object = field(repr=False, compare=False)

    def assert_valid_holdout_capability(self) -> None:
        if self._capability_nonce is not _CAPABILITY_NONCE:
            raise InvalidAuthorizationError(
                "validated holdout authorization capability is required"
            )


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidAuthorizationError(f"{field} must be a nonempty string")
    return value.strip()


def _required_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise InvalidAuthorizationError(f"{field} must be an object")
    return value


def _canonical_json_digest(record: Mapping[str, Any]) -> str:
    payload = json.dumps(
        record, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _verify_external_evidence(
    locator: Any,
    expected_sha256: Any,
    *,
    field: str,
    repository_root: Path,
) -> None:
    path = Path(_required_text(locator, f"{field}.evidence_path")).expanduser().resolve()
    if _is_within(path, repository_root):
        raise InvalidAuthorizationError(f"{field}.evidence_path must be outside the repository")
    if not path.is_file():
        raise InvalidAuthorizationError(f"{field}.evidence_path does not exist")
    checksum = _required_text(expected_sha256, f"{field}.checksum_sha256")
    if not _SHA256_RE.fullmatch(checksum):
        raise InvalidAuthorizationError(f"{field}.checksum_sha256 must be a SHA-256 digest")
    if hashlib.sha256(path.read_bytes()).hexdigest() != checksum.lower():
        raise InvalidAuthorizationError(f"{field} evidence checksum does not match")


def parse_authorization_json(path: str | Path) -> dict[str, Any]:
    """Read an authorization record without retaining it in tracked code."""
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise InvalidAuthorizationError(f"cannot read authorization JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise InvalidAuthorizationError("authorization JSON must contain an object")
    return value


def inspect_repository(repository: str | Path) -> RepositoryState:
    """Return the exact HEAD revision and whether the Git worktree is clean."""
    root = Path(repository)
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise InvalidAuthorizationError("repository state could not be verified") from exc
    return RepositoryState(commit=commit, clean=not status.strip())


def validate_authorization(
    record: Mapping[str, Any],
    *,
    repository_state: RepositoryState,
    repository_root: str | Path,
    expected_matrix_sha256: str,
) -> str:
    """Validate all freeze prerequisites and return the record's stable digest."""
    if record.get("protocol_status") != "frozen":
        raise InvalidAuthorizationError("protocol_status must be 'frozen'")
    if record.get("one_time_authorization") is not True:
        raise InvalidAuthorizationError("one_time_authorization must be true")

    frozen_commit = _required_text(record.get("frozen_git_commit"), "frozen_git_commit")
    if not _COMMIT_RE.fullmatch(frozen_commit):
        raise InvalidAuthorizationError("frozen_git_commit must be a full 40-character Git commit")
    if not _COMMIT_RE.fullmatch(repository_state.commit):
        raise InvalidAuthorizationError("current repository revision is not a full Git commit")
    if frozen_commit.lower() != repository_state.commit.lower():
        raise InvalidAuthorizationError("current repository revision does not match frozen_git_commit")
    if not repository_state.clean:
        raise InvalidAuthorizationError("worktree must be clean")

    matrix_sha256 = _required_text(record.get("matrix_sha256"), "matrix_sha256")
    if not _SHA256_RE.fullmatch(matrix_sha256):
        raise InvalidAuthorizationError("matrix_sha256 must be a SHA-256 digest")
    if not _SHA256_RE.fullmatch(expected_matrix_sha256):
        raise InvalidAuthorizationError("expected matrix checksum must be a SHA-256 digest")
    if matrix_sha256.lower() != expected_matrix_sha256.lower():
        raise InvalidAuthorizationError("matrix checksum does not match the frozen matrix")

    approval = _required_mapping(record.get("supervisor_approval"), "supervisor_approval")
    approval_date = _required_text(approval.get("date"), "supervisor_approval.date")
    try:
        date.fromisoformat(approval_date)
    except ValueError as exc:
        raise InvalidAuthorizationError(
            "supervisor_approval.date must use YYYY-MM-DD"
        ) from exc
    root = Path(repository_root).resolve()
    _verify_external_evidence(
        approval.get("evidence_path"),
        approval.get("checksum_sha256"),
        field="supervisor_approval",
        repository_root=root,
    )

    reviewers = record.get("reviewers")
    if not isinstance(reviewers, list) or len(reviewers) != 2:
        raise InvalidAuthorizationError("exactly two reviewer entries are required")
    reviewer_ids: set[str] = set()
    for index, raw_reviewer in enumerate(reviewers):
        reviewer = _required_mapping(raw_reviewer, f"reviewers[{index}]")
        reviewer_id = _required_text(
            reviewer.get("reviewer_id"), f"reviewers[{index}].reviewer_id"
        )
        _required_text(
            reviewer.get("qualification"), f"reviewers[{index}].qualification"
        )
        normalized_id = reviewer_id.casefold()
        if normalized_id in reviewer_ids:
            raise InvalidAuthorizationError("reviewer IDs must be distinct")
        reviewer_ids.add(normalized_id)

        review = _required_mapping(
            reviewer.get("expert_review"), f"reviewers[{index}].expert_review"
        )
        if review.get("status") != "completed":
            raise InvalidAuthorizationError(
                f"reviewers[{index}].expert_review.status must be 'completed'"
            )
        _verify_external_evidence(
            review.get("evidence_path"),
            review.get("checksum_sha256"),
            field=f"reviewers[{index}].expert_review",
            repository_root=root,
        )

    return _canonical_json_digest(record)


def begin_holdout_attempt(
    authorization_path: str | Path,
    ledger_path: str | Path,
    *,
    repository: str | Path,
    expected_matrix_sha256: str,
) -> HoldoutAttempt:
    """Validate authorization and atomically consume its sole attempt."""
    record = parse_authorization_json(authorization_path)
    repository_root = Path(repository).resolve()
    authorization = Path(authorization_path).expanduser().resolve()
    if _is_within(authorization, repository_root):
        raise InvalidAuthorizationError("authorization JSON must be stored outside the repository")
    repository_state = inspect_repository(repository_root)
    authorization_sha256 = validate_authorization(
        record,
        repository_state=repository_state,
        repository_root=repository_root,
        expected_matrix_sha256=expected_matrix_sha256,
    )
    frozen_commit = str(record["frozen_git_commit"]).lower()
    matrix_sha256 = str(record["matrix_sha256"]).lower()
    attempt_id = uuid.uuid4().hex
    started_at = datetime.now(timezone.utc).isoformat()
    ledger = {
        "schema_version": 1,
        "attempt_id": attempt_id,
        "authorization_sha256": authorization_sha256,
        "frozen_git_commit": frozen_commit,
        "matrix_sha256": matrix_sha256,
        "state": "started",
        "started_at_utc": started_at,
        "finished_at_utc": None,
        "outcome": None,
    }

    destination = Path(ledger_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise HoldoutAlreadyConsumedError(
            f"holdout attempt already consumed: {destination}"
        ) from exc
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(ledger, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        # The file remains as evidence that consumption began, even if writing failed.
        raise

    return HoldoutAttempt(
        attempt_id=attempt_id,
        authorization_sha256=authorization_sha256,
        frozen_git_commit=frozen_commit,
        matrix_sha256=matrix_sha256,
        ledger_path=destination,
        _capability_nonce=_CAPABILITY_NONCE,
    )


def require_holdout_attempt(value: HoldoutAttempt | None) -> HoldoutAttempt:
    """Reject callers that did not obtain a capability from the validated gate."""
    if not isinstance(value, HoldoutAttempt) or value._capability_nonce is not _CAPABILITY_NONCE:
        raise InvalidAuthorizationError("validated holdout authorization capability is required")
    return value


def finalize_holdout_attempt(
    attempt: HoldoutAttempt,
    *,
    success: bool,
    detail: str | None = None,
) -> None:
    """Finalize the first attempt once; success and failure both consume it."""
    path = attempt.ledger_path
    try:
        ledger = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise LedgerStateError("consumption ledger cannot be read") from exc
    if not isinstance(ledger, dict):
        raise LedgerStateError("consumption ledger is invalid")
    identity = (
        ledger.get("attempt_id"),
        ledger.get("authorization_sha256"),
        ledger.get("frozen_git_commit"),
        ledger.get("matrix_sha256"),
    )
    expected_identity = (
        attempt.attempt_id,
        attempt.authorization_sha256,
        attempt.frozen_git_commit,
        attempt.matrix_sha256,
    )
    if identity != expected_identity:
        raise LedgerStateError("consumption ledger identity does not match this attempt")
    if ledger.get("state") != "started":
        raise LedgerStateError("consumption ledger has already been finalized")

    ledger["state"] = "succeeded" if success else "failed"
    ledger["outcome"] = {
        "success": bool(success),
        "detail": detail.strip() if isinstance(detail, str) and detail.strip() else None,
    }
    ledger["finished_at_utc"] = datetime.now(timezone.utc).isoformat()

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            json.dump(ledger, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
