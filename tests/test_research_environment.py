from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from scripts.verify_research_environment import (
    _canonical_bytes,
    environment_report,
    main,
    read_lock,
    unlocked_dependencies,
)
from scripts.run_tdk_independent_development import (
    _artifact_schema_metadata as independent_schema,
)
from scripts.run_tdk_protocol_experiment import (
    _artifact_schema_metadata as protocol_schema,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_current_artifact_runners_declare_schema_eight() -> None:
    assert independent_schema() == {"artifact_schema_version": 8}
    assert protocol_schema() == {"artifact_schema_version": 8}


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
    packages = read_lock(lock_path)

    report = environment_report()

    assert report["expected_python_version"] == declaration["python_version"]
    assert report["lock_file"] == declaration["lock_file"]
    assert report["lock_sha256"] == sha256(_canonical_bytes(lock_path)).hexdigest()
    assert unlocked_dependencies(packages) == []


def test_canonical_hash_ignores_checkout_line_endings(tmp_path: Path) -> None:
    lf = tmp_path / "lf.txt"
    crlf = tmp_path / "crlf.txt"
    lf.write_bytes(b"numpy==2.5.4\n")
    crlf.write_bytes(b"numpy==2.5.4\r\n")

    assert sha256(_canonical_bytes(lf)).digest() == sha256(_canonical_bytes(crlf)).digest()


def test_unlocked_dependency_is_reported() -> None:
    with patch(
        "scripts.verify_research_environment.distribution",
        return_value=SimpleNamespace(requires=["unlocked-package>=1"]),
    ):
        assert unlocked_dependencies({"root-package": "1.0"}) == [
            "root-package -> unlocked-package"
        ]


def test_environment_report_detects_python_and_package_drift() -> None:
    declaration = json.loads(
        (REPO_ROOT / "research-environment.json").read_text(encoding="utf-8")
    )
    packages = read_lock(REPO_ROOT / declaration["lock_file"])

    with patch(
        "scripts.verify_research_environment.sys.version_info",
        (3, 12, 0),
    ), patch(
        "scripts.verify_research_environment.version",
        side_effect=lambda package: (
            "0.0" if package.casefold() == "numpy" else packages[package.casefold()]
        ),
    ):
        report = environment_report()

    assert any(item.startswith("python:") for item in report["mismatches"])
    assert any(item.startswith("numpy:") for item in report["mismatches"])


def test_cli_fails_when_environment_drift_is_reported() -> None:
    with patch(
        "scripts.verify_research_environment.environment_report",
        return_value={"mismatches": ["numpy drift"]},
    ), patch("scripts.verify_research_environment.sys.argv", ["verify"]):
        with pytest.raises(SystemExit) as error:
            main()

    assert error.value.code == 1
