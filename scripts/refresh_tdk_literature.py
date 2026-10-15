"""Refresh the reproducible MyHR TDK scholarly metadata corpus."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.research.literature import (
    ArxivClient,
    OpenAlexClient,
    PaperRecord,
    SearchBatch,
    SemanticScholarClient,
    merge_records,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh MyHR TDK literature metadata.")
    parser.add_argument(
        "--query-config",
        type=Path,
        default=Path("config/tdk_literature_queries.json"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("research_outputs/literature"),
    )
    parser.add_argument("--max-results", type=int, default=8)
    parser.add_argument(
        "--sources",
        default="semantic_scholar,openalex,arxiv",
        help="Comma-separated subset of semantic_scholar, openalex,arxiv.",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run one query with at most three records per source.",
    )
    args = parser.parse_args()

    if not 1 <= args.max_results <= 100:
        raise ValueError("--max-results must be between 1 and 100")
    config_bytes = args.query_config.read_bytes()
    config = json.loads(config_bytes.decode("utf-8"))
    if args.smoke:
        smoke_query = next(
            (item for item in config["queries"] if item["id"] == "isolation_forest"),
            config["queries"][0],
        )
        queries = [smoke_query]
    else:
        queries = config["queries"]
    limit = min(args.max_results, 3) if args.smoke else args.max_results
    source_names = tuple(part.strip() for part in args.sources.split(",") if part.strip())
    clients = {
        "semantic_scholar": SemanticScholarClient(),
        "openalex": OpenAlexClient(),
        "arxiv": ArxivClient(),
    }
    unknown = set(source_names) - set(clients)
    if unknown:
        raise ValueError(f"unknown sources: {', '.join(sorted(unknown))}")

    started_at = datetime.now(timezone.utc)
    batches: list[tuple[str, SearchBatch]] = []
    records: list[PaperRecord] = []
    for query_config in queries:
        query_id = str(query_config["id"])
        query = str(query_config["query"])
        year_from = int(query_config.get("year_from", config["default_year_from"]))
        year_to = int(query_config.get("year_to", config["default_year_to"]))
        for source_name in source_names:
            source_query = str(query_config.get(f"{source_name}_query", query))
            batch = clients[source_name].search(
                source_query,
                year_from=year_from,
                year_to=year_to,
                limit=limit,
            )
            batches.append((query_id, batch))
            records.extend(batch.records)
            print(f"{query_id}: {source_name} returned {len(batch.records)} records")

    revision = _git_revision()
    identity = {
        "config_sha256": sha256(config_bytes).hexdigest(),
        "sources": source_names,
        "limit": limit,
        "smoke": args.smoke,
        "git_commit": revision["commit"],
        "started_at": started_at.isoformat(),
    }
    digest = sha256(json.dumps(identity, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    timestamp = started_at.strftime("%Y%m%dT%H%M%SZ")
    run_dir = args.output_dir / f"{timestamp}_{digest}"
    run_dir.mkdir(parents=True, exist_ok=False)
    raw_dir = run_dir / "raw"
    raw_dir.mkdir()

    query_rows = []
    for index, (query_id, batch) in enumerate(batches, start=1):
        raw_name = f"{index:03d}_{query_id}_{batch.source}.{batch.raw_extension}"
        (raw_dir / raw_name).write_bytes(batch.raw_body)
        query_rows.append({
            "query_id": query_id,
            "source": batch.source,
            "query": batch.query,
            "request_url": batch.request_url,
            "retrieved_at_utc": batch.retrieved_at_utc,
            "record_count": len(batch.records),
            "raw_file": f"raw/{raw_name}",
            "raw_sha256": sha256(batch.raw_body).hexdigest(),
        })

    merged = merge_records(records)
    _write_json(run_dir / "metadata.json", {
        "workflow": "MyHR TDK literature refresh",
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "free_services_only": True,
        "paid_services_enabled": False,
        "query_config": str(args.query_config),
        "query_config_sha256": sha256(config_bytes).hexdigest(),
        "sources": source_names,
        "query_count": len(queries),
        "source_query_count": len(batches),
        "source_record_count": len(records),
        "merged_record_count": len(merged),
        "git": revision,
        "credentials": {
            "semantic_scholar_key_present": bool(clients["semantic_scholar"].api_key),
            "openalex_key_present": bool(clients["openalex"].api_key),
            "values_recorded": False,
        },
    })
    _write_json(run_dir / "queries.json", query_rows)
    _write_json(run_dir / "source_records.json", [record.as_json() for record in records])
    _write_json(run_dir / "papers.json", merged)
    _write_papers_csv(run_dir / "papers.csv", merged)
    _write_trends_csv(run_dir / "trend_counts.csv", batches)
    _write_manifest(run_dir)
    print(json.dumps({
        "output_dir": str(run_dir),
        "source_records": len(records),
        "merged_records": len(merged),
        "holdout_accessed": False,
    }, indent=2))


def _git_revision() -> dict[str, object]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    dirty = bool(subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip())
    return {"commit": commit, "dirty": dirty}


def _write_papers_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames = (
        "canonical_key", "title", "year", "publication_date", "authors", "doi",
        "arxiv_id", "venue", "citation_count", "sources", "landing_url", "pdf_url",
        "open_access_status", "license",
    )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            output = dict(row)
            output["authors"] = "; ".join(str(value) for value in row.get("authors", []))
            output["sources"] = "; ".join(str(value) for value in row.get("sources", []))
            writer.writerow(output)


def _write_trends_csv(path: Path, batches: list[tuple[str, SearchBatch]]) -> None:
    counts: dict[tuple[str, str, int | None], int] = {}
    for query_id, batch in batches:
        for record in batch.records:
            key = (query_id, batch.source, record.year)
            counts[key] = counts.get(key, 0) + 1
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("query_id", "source", "publication_year", "record_count"))
        for (query_id, source, year), count in sorted(
            counts.items(), key=lambda item: (item[0][0], item[0][1], item[0][2] or 0)
        ):
            writer.writerow((query_id, source, year or "unknown", count))


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_manifest(run_dir: Path) -> None:
    files = sorted(path for path in run_dir.rglob("*") if path.is_file() and path.name != "manifest.json")
    _write_json(run_dir / "manifest.json", {
        "algorithm": "sha256",
        "files": {
            path.relative_to(run_dir).as_posix(): sha256(path.read_bytes()).hexdigest()
            for path in files
        },
    })


if __name__ == "__main__":
    main()
