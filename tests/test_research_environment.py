from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest

from scripts.verify_research_environment import environment_report, read_lock


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_research_lock_contains_only_exact_versions(tmp_path: Path) -> None:
    lock = tmp_path / "requirements-lock.txt"
    lock.write_text("numpy>=2\n", encoding="utf-8")

    with pytest.raises(ValueError, match="not exact"):
        read_lock(lock)


def test_declared_lock_is_nonempty_and_exact() -> None:
    declaration = json.loads(
        (REPO_ROOT / "research-environment.json").read_text(encoding="utf-8")
    )
    lock_path = REPO_ROOT / declaration["lock_file"]

    packages = read_lock(lock_path)

    assert packages
    assert all(packages.values())


def test_environment_report_binds_lock_checksum() -> None:
    declaration = json.loads(
        (REPO_ROOT / "research-environment.json").read_text(encoding="utf-8")
    )
    lock_path = REPO_ROOT / declaration["lock_file"]

    report = environment_report()

    assert report["expected_python_version"] == declaration["python_version"]
    assert report["lock_file"] == declaration["lock_file"]
    assert report["lock_sha256"] == sha256(lock_path.read_bytes()).hexdigest()
