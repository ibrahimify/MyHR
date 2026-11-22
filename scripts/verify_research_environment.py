"""Verify the declared scientific runtime and locked dependencies."""

from __future__ import annotations

import argparse
import json
import sys
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, distribution, version
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


REPO_ROOT = Path(__file__).resolve().parents[1]
DECLARATION_PATH = REPO_ROOT / "research-environment.json"


def _canonical_bytes(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n")


def read_lock(path: Path) -> dict[str, str]:
    packages: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        if "==" not in value:
            raise ValueError(f"research lock entry is not exact: {value}")
        package, package_version = value.split("==", 1)
        packages[canonicalize_name(package)] = package_version
    if not packages:
        raise ValueError("research lock contains no packages")
    return packages


def unlocked_dependencies(packages: dict[str, str]) -> list[str]:
    missing: set[str] = set()
    for package in packages:
        try:
            requirements = distribution(package).requires or []
        except PackageNotFoundError:
            continue
        for raw_requirement in requirements:
            requirement = Requirement(raw_requirement)
            if requirement.marker is not None and not requirement.marker.evaluate():
                continue
            dependency = canonicalize_name(requirement.name)
            if dependency not in packages:
                missing.add(f"{package} -> {dependency}")
    return sorted(missing)


def environment_report(repo_root: Path = REPO_ROOT) -> dict[str, object]:
    declaration = json.loads(
        (repo_root / DECLARATION_PATH.name).read_text(encoding="utf-8")
    )
    lock_path = repo_root / str(declaration["lock_file"])
    expected = read_lock(lock_path)
    installed: dict[str, str] = {}
    mismatches: list[str] = []
    for package, expected_version in expected.items():
        try:
            installed_version = version(package)
        except PackageNotFoundError:
            installed_version = "not-installed"
        installed[package] = installed_version
        if installed_version != expected_version:
            mismatches.append(
                f"{package}: expected {expected_version}, found {installed_version}"
            )
    mismatches.extend(
        f"unlocked dependency: {dependency}"
        for dependency in unlocked_dependencies(expected)
    )

    actual_python = ".".join(str(part) for part in sys.version_info[:3])
    expected_python = str(declaration["python_version"])
    if actual_python != expected_python:
        mismatches.insert(
            0, f"python: expected {expected_python}, found {actual_python}"
        )

    return {
        "python_version": actual_python,
        "expected_python_version": expected_python,
        "declaration_file": DECLARATION_PATH.name,
        "declaration_sha256": sha256(
            _canonical_bytes(repo_root / DECLARATION_PATH.name)
        ).hexdigest(),
        "lock_file": str(declaration["lock_file"]),
        "lock_sha256": sha256(_canonical_bytes(lock_path)).hexdigest(),
        "packages": installed,
        "mismatches": mismatches,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Print drift without returning a failure status.",
    )
    args = parser.parse_args()
    report = environment_report()
    print(json.dumps(report, indent=2, sort_keys=True))
    if report["mismatches"] and not args.report_only:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
