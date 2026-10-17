"""Build a free, reproducible OpenAlex citation neighborhood for the TDK corpus."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.research.literature import OpenAlexClient


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the MyHR TDK citation network.")
    parser.add_argument(
        "--selection", type=Path, default=Path("config/tdk_fulltext_selection.json")
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("research_outputs/literature_citations")
    )
    parser.add_argument("--citing-limit", type=int, default=25)
    args = parser.parse_args()
    if not 1 <= args.citing_limit <= 100:
        raise ValueError("--citing-limit must be between 1 and 100")

    selection_bytes = args.selection.read_bytes()
    papers = json.loads(selection_bytes.decode("utf-8"))["papers"]
    doi_papers = [paper for paper in papers if paper.get("doi")]
    client = OpenAlexClient()
    neighborhoods = []
    for paper in doi_papers:
        neighborhood = client.citation_neighborhood(
            str(paper["doi"]), citing_limit=args.citing_limit
        )
        neighborhoods.append({"selection_id": paper["id"], **neighborhood})
        print(
            f"{paper['id']}: {len(neighborhood['references'])} references, "
            f"{len(neighborhood['citing_works'])} citing works"
        )

    generated_at = datetime.now(timezone.utc)
    revision = _git_revision()
    identity = {
        "selection_sha256": sha256(selection_bytes).hexdigest(),
        "citing_limit": args.citing_limit,
        "git_commit": revision["commit"],
        "generated_at": generated_at.isoformat(),
    }
    digest = sha256(json.dumps(identity, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    run_dir = args.output_dir / f"{generated_at.strftime('%Y%m%dT%H%M%SZ')}_{digest}"
    run_dir.mkdir(parents=True, exist_ok=False)
    _write_json(run_dir / "metadata.json", {
        "workflow": "MyHR TDK OpenAlex citation network",
        "schema_version": "1.0",
        "generated_at_utc": generated_at.isoformat(),
        "free_services_only": True,
        "paid_services_enabled": False,
        "holdout_accessed": False,
        "seed_count": len(neighborhoods),
        "citing_limit_per_seed": args.citing_limit,
        "selection_sha256": sha256(selection_bytes).hexdigest(),
        "git": revision,
    })
    _write_json(run_dir / "citation_network.json", neighborhoods)
    _write_manifest(run_dir)
    print(json.dumps({"output_dir": str(run_dir), "seed_count": len(neighborhoods)}, indent=2))


def _git_revision() -> dict[str, object]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()
    dirty = bool(subprocess.run(
        ["git", "status", "--porcelain"], cwd=REPO_ROOT, check=True, capture_output=True, text=True
    ).stdout.strip())
    return {"commit": commit, "dirty": dirty}


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_manifest(run_dir: Path) -> None:
    files = sorted(path for path in run_dir.iterdir() if path.is_file() and path.name != "manifest.json")
    _write_json(run_dir / "manifest.json", {
        "algorithm": "sha256",
        "files": {path.name: sha256(path.read_bytes()).hexdigest() for path in files},
    })


if __name__ == "__main__":
    main()
