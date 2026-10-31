"""Create a read-only inventory of local MyHR research evidence.

The inventory deliberately treats holdout-named paths as opaque and reports private
notes only as aggregate counts. It never deletes or modifies research artifacts.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT_ROOT = REPO_ROOT / "research_outputs"
DEFAULT_PRIVATE_NOTES_ROOT = REPO_ROOT / "docs" / "research"

CANONICAL_ARTIFACTS = {
    "protocol-development": (
        "protocol_v2_verified/development_5f0f99d3ffe8dc9e"
    ),
    "protocol-validation": (
        "protocol_v2_verified/validation_c5878ca7b927ccd2"
    ),
    "independent-development": (
        "independent_development/independent_development_e342bd4acf39b06b"
    ),
    "literature-metadata": "literature/20261017T215024Z_f79f81f2c2b1",
    "literature-fulltext": "literature_fulltext/20261017T215119Z_4b354b03c1af",
}


def _is_holdout_name(name: str) -> bool:
    return "holdout" in name.casefold()


def _safe_walk(root: Path):
    """Walk without following links or entering holdout-named directories."""
    if not root.exists():
        return
    for current, dir_names, file_names in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        retained_dirs: list[str] = []
        skipped_holdout_dirs = 0
        skipped_links = 0
        for name in dir_names:
            path = current_path / name
            if _is_holdout_name(name):
                skipped_holdout_dirs += 1
            elif path.is_symlink():
                skipped_links += 1
            else:
                retained_dirs.append(name)
        dir_names[:] = retained_dirs

        safe_files: list[str] = []
        skipped_holdout_files = 0
        for name in file_names:
            path = current_path / name
            if _is_holdout_name(name):
                skipped_holdout_files += 1
            elif path.is_symlink():
                skipped_links += 1
            else:
                safe_files.append(name)
        yield (
            current_path,
            retained_dirs,
            safe_files,
            skipped_holdout_dirs + skipped_holdout_files,
            skipped_links,
        )


def _tree_stats(root: Path) -> dict[str, int]:
    stats = {
        "file_count": 0,
        "size_bytes": 0,
        "skipped_holdout_entries": 0,
        "skipped_symlinks": 0,
    }
    if any(_is_holdout_name(part) for part in root.parts):
        stats["skipped_holdout_entries"] = 1
        return stats
    if not root.exists():
        return stats
    for current, _dirs, files, holdout_count, link_count in _safe_walk(root):
        stats["skipped_holdout_entries"] += holdout_count
        stats["skipped_symlinks"] += link_count
        for name in files:
            try:
                stat = (current / name).stat()
            except OSError:
                continue
            stats["file_count"] += 1
            stats["size_bytes"] += stat.st_size
    return stats


def _artifact_candidates(root: Path) -> list[Path]:
    if not root.is_dir():
        return []

    candidates: set[Path] = set()
    for current, dirs, files, _holdout_count, _link_count in _safe_walk(root):
        relative_parts = current.relative_to(root).parts
        if "manifest.json" in files:
            candidates.add(current)
        elif len(relative_parts) == 1 and files and not dirs:
            candidates.add(current)
        elif len(relative_parts) == 2:
            candidates.add(current)
        elif relative_parts and not files:
            try:
                if not any(current.iterdir()):
                    candidates.add(current)
            except OSError:
                pass
    return sorted(candidates, key=lambda path: path.relative_to(root).as_posix())


def _manifest_path(relative_name: str, artifact_dir: Path) -> Path | None:
    pure = PurePosixPath(relative_name)
    if pure.is_absolute() or ".." in pure.parts or "\\" in relative_name:
        return None
    if any(_is_holdout_name(part) for part in pure.parts):
        return None
    candidate = (artifact_dir / Path(*pure.parts)).resolve()
    try:
        candidate.relative_to(artifact_dir.resolve())
    except ValueError:
        return None
    return candidate


def _verify_manifest(artifact_dir: Path) -> dict[str, Any]:
    manifest_path = artifact_dir / "manifest.json"
    if not manifest_path.is_file():
        sidecar_result = _verify_sha256_sidecars(artifact_dir)
        if sidecar_result is not None:
            return sidecar_result
        return {
            "status": "missing",
            "source": None,
            "algorithm": None,
            "listed_file_count": 0,
            "verified_file_count": 0,
            "issues": ["manifest.json is absent"],
        }

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {
            "status": "invalid",
            "source": "manifest",
            "algorithm": None,
            "listed_file_count": 0,
            "verified_file_count": 0,
            "issues": ["manifest.json is unreadable or invalid JSON"],
        }

    algorithm = manifest.get("algorithm")
    files = manifest.get("files")
    if algorithm != "sha256" or not isinstance(files, dict):
        return {
            "status": "invalid",
            "source": "manifest",
            "algorithm": algorithm,
            "listed_file_count": len(files) if isinstance(files, dict) else 0,
            "verified_file_count": 0,
            "issues": ["manifest must use sha256 and contain a files object"],
        }

    issues: list[str] = []
    verified = 0
    safe_listed_paths: set[str] = set()
    for relative_name, expected_digest in sorted(files.items()):
        if not isinstance(relative_name, str) or not isinstance(expected_digest, str):
            issues.append("manifest contains a non-string path or digest")
            continue
        path = _manifest_path(relative_name, artifact_dir)
        if path is None:
            issues.append("manifest contains an unsafe or holdout-like path")
            continue
        safe_listed_paths.add(PurePosixPath(relative_name).as_posix())
        if not path.is_file() or path.is_symlink():
            issues.append(f"missing or unsupported manifest file: {relative_name}")
            continue
        try:
            digest = _sha256_file(path)
        except OSError:
            issues.append(f"unable to hash manifest file: {relative_name}")
            continue
        if digest != expected_digest:
            issues.append(f"checksum mismatch: {relative_name}")
            continue
        verified += 1

    actual_paths: set[str] = set()
    for current, _dirs, file_names, _holdout_count, _link_count in _safe_walk(artifact_dir):
        for name in file_names:
            path = current / name
            relative = path.relative_to(artifact_dir).as_posix()
            if relative != "manifest.json":
                actual_paths.add(relative)
    extras = sorted(actual_paths - safe_listed_paths)
    if extras:
        issues.append(f"{len(extras)} unlisted file(s) present")

    return {
        "status": "valid" if not issues else "failed",
        "source": "manifest",
        "algorithm": algorithm,
        "listed_file_count": len(files),
        "verified_file_count": verified,
        "issues": issues,
    }


def _verify_sha256_sidecars(artifact_dir: Path) -> dict[str, Any] | None:
    sidecars = sorted(artifact_dir.glob("*.sha256"))
    if not sidecars:
        return None

    issues: list[str] = []
    listed_paths: set[str] = set()
    verified = 0
    for sidecar in sidecars:
        try:
            parts = sidecar.read_text(encoding="ascii").strip().split()
        except (OSError, UnicodeError):
            issues.append(f"unreadable checksum sidecar: {sidecar.name}")
            continue
        if len(parts) != 2 or len(parts[0]) != 64:
            issues.append(f"invalid checksum sidecar: {sidecar.name}")
            continue
        expected_digest, relative_name = parts
        path = _manifest_path(relative_name.lstrip("*"), artifact_dir)
        if path is None or path.parent != artifact_dir.resolve():
            issues.append(f"unsafe checksum target in: {sidecar.name}")
            continue
        normalized_name = path.name
        if normalized_name in listed_paths:
            issues.append(f"duplicate checksum target in: {sidecar.name}")
            continue
        listed_paths.add(normalized_name)
        if not path.is_file() or path.is_symlink():
            issues.append(f"missing checksum target: {normalized_name}")
            continue
        try:
            digest = _sha256_file(path)
        except OSError:
            issues.append(f"unable to hash checksum target: {normalized_name}")
            continue
        if digest.casefold() != expected_digest.casefold():
            issues.append(f"checksum mismatch: {normalized_name}")
            continue
        verified += 1

    data_files = {
        path.name
        for path in artifact_dir.iterdir()
        if path.is_file() and not path.is_symlink() and path.suffix != ".sha256"
    }
    if data_files != listed_paths:
        issues.append("checksum sidecars do not cover every release file exactly once")

    return {
        "status": "valid" if not issues else "failed",
        "source": "sha256_sidecars",
        "algorithm": "sha256",
        "listed_file_count": len(listed_paths),
        "verified_file_count": verified,
        "issues": issues,
    }


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_inventory(
    artifact_root: Path = DEFAULT_ARTIFACT_ROOT,
    private_notes_root: Path = DEFAULT_PRIVATE_NOTES_ROOT,
) -> dict[str, Any]:
    artifact_root = artifact_root.resolve()
    private_notes_root = private_notes_root.resolve()
    if any(_is_holdout_name(part) for part in artifact_root.parts):
        raise ValueError("artifact root must not be a holdout-like path")

    root_stats = _tree_stats(artifact_root)
    artifacts: list[dict[str, Any]] = []
    canonical_by_path = {path: label for label, path in CANONICAL_ARTIFACTS.items()}

    for artifact_dir in _artifact_candidates(artifact_root):
        relative = artifact_dir.relative_to(artifact_root).as_posix()
        stats = _tree_stats(artifact_dir)
        manifest = _verify_manifest(artifact_dir)
        if stats["file_count"] == 0:
            state = "orphan_empty"
        elif stats["skipped_holdout_entries"] or stats["skipped_symlinks"]:
            state = "review_required_opaque_entries"
        elif manifest["status"] == "missing":
            state = "incomplete_missing_manifest"
        elif manifest["status"] == "valid":
            state = "complete"
        else:
            state = "integrity_problem"
        artifacts.append(
            {
                "path": relative,
                "canonical_label": canonical_by_path.get(relative),
                "state": state,
                "file_count": stats["file_count"],
                "size_bytes": stats["size_bytes"],
                "manifest": manifest,
            }
        )

    found = {entry["path"] for entry in artifacts}
    canonical = [
        {
            "label": label,
            "path": path,
            "present": path in found,
            "state": next(
                (entry["state"] for entry in artifacts if entry["path"] == path),
                "missing",
            ),
        }
        for label, path in CANONICAL_ARTIFACTS.items()
    ]
    private_stats = _tree_stats(private_notes_root)

    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "artifact_root": artifact_root.name,
        "safety": {
            "read_only": True,
            "holdout_content_inspected": False,
            "private_note_contents_inspected": False,
            "private_note_names_exposed": False,
        },
        "summary": {
            **root_stats,
            "artifact_count": len(artifacts),
            "complete_artifact_count": sum(
                entry["state"] == "complete" for entry in artifacts
            ),
            "problem_artifact_count": sum(
                entry["state"] != "complete" for entry in artifacts
            ),
        },
        "canonical_artifacts": canonical,
        "artifacts": artifacts,
        "private_notes": {
            "present": private_notes_root.is_dir(),
            "file_count": private_stats["file_count"],
            "size_bytes": private_stats["size_bytes"],
            "skipped_holdout_entries": private_stats["skipped_holdout_entries"],
            "skipped_symlinks": private_stats["skipped_symlinks"],
        },
    }


def _is_ignored_output(path: Path, repo_root: Path = REPO_ROOT) -> bool:
    try:
        relative = path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return False
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", "--no-index", "--", relative.as_posix()],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    return result.returncode == 0


def write_inventory(
    inventory: dict[str, Any],
    output: Path,
    ignore_checker: Callable[[Path], bool] = _is_ignored_output,
) -> None:
    output = output.resolve()
    if not ignore_checker(output):
        raise ValueError("output path must be inside the repository and ignored by Git")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as handle:
        json.dump(inventory, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inventory local MyHR research evidence without modifying artifacts."
    )
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    parser.add_argument(
        "--private-notes-root", type=Path, default=DEFAULT_PRIVATE_NOTES_ROOT
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write once to an explicitly supplied Git-ignored path; otherwise use stdout.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        inventory = build_inventory(args.artifact_root, args.private_notes_root)
        if args.output:
            write_inventory(inventory, args.output)
        else:
            json.dump(inventory, sys.stdout, indent=2, sort_keys=True)
            sys.stdout.write("\n")
    except (OSError, ValueError) as exc:
        print(f"inventory failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
