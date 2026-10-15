"""Verify hashes and safety properties of a MyHR literature artifact directory."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re


SECRET_PATTERNS = (
    re.compile(rb"SEMANTIC_SCHOLAR_API_KEY\s*[=:]\s*[^\s\"']+", re.IGNORECASE),
    re.compile(rb"OPENALEX_API_KEY\s*[=:]\s*[^\s\"']+", re.IGNORECASE),
    re.compile(rb"x-api-key[\"']?\s*[:=]\s*[\"']?(?!REDACTED)[A-Za-z0-9_-]{12,}", re.IGNORECASE),
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify a MyHR literature artifact.")
    parser.add_argument("artifact", type=Path)
    args = parser.parse_args()
    result = verify_artifact(args.artifact)
    print(json.dumps(result, indent=2))


def verify_artifact(run_dir: Path) -> dict[str, object]:
    manifest_path = run_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("algorithm") != "sha256":
        raise ValueError("artifact manifest must use sha256")
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("artifact manifest contains no files")

    verified = 0
    for relative_name, expected_hash in files.items():
        path = (run_dir / relative_name).resolve()
        if run_dir.resolve() not in path.parents:
            raise ValueError(f"manifest path escapes artifact directory: {relative_name}")
        body = path.read_bytes()
        actual_hash = sha256(body).hexdigest()
        if actual_hash != expected_hash:
            raise ValueError(f"checksum mismatch: {relative_name}")
        if any(pattern.search(body) for pattern in SECRET_PATTERNS):
            raise ValueError(f"possible credential found: {relative_name}")
        verified += 1

    metadata_path = run_dir / "metadata.json"
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("holdout_accessed") is True:
            raise ValueError("literature artifact unexpectedly reports holdout access")
        if metadata.get("paid_services_enabled") is True:
            raise ValueError("literature artifact unexpectedly enables paid services")

    return {
        "artifact": str(run_dir),
        "files_verified": verified,
        "checksums_valid": True,
        "credential_scan_passed": True,
        "holdout_accessed": False,
        "paid_services_enabled": False,
    }


if __name__ == "__main__":
    main()
