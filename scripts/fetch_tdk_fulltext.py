"""Fetch and extract the curated, legally accessible MyHR TDK paper corpus."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import io
import json
from pathlib import Path
import re
import subprocess
import sys

from pypdf import PdfReader

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.research.literature import ArxivClient, HttpTransport, OpenAlexClient


MAX_PDF_BYTES = 50 * 1024 * 1024


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch the curated MyHR TDK full-text corpus.")
    parser.add_argument(
        "--selection",
        type=Path,
        default=Path("config/tdk_fulltext_selection.json"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("research_outputs/literature_fulltext"),
    )
    parser.add_argument("--limit", type=int, help="Fetch only the first N papers for a smoke test.")
    args = parser.parse_args()

    selection_bytes = args.selection.read_bytes()
    selection = json.loads(selection_bytes.decode("utf-8"))
    papers = selection["papers"][: args.limit] if args.limit else selection["papers"]
    if not papers:
        raise ValueError("the full-text selection is empty")

    started_at = datetime.now(timezone.utc)
    revision = _git_revision()
    identity = {
        "selection_sha256": sha256(selection_bytes).hexdigest(),
        "paper_ids": [paper["id"] for paper in papers],
        "git_commit": revision["commit"],
        "started_at": started_at.isoformat(),
    }
    digest = sha256(json.dumps(identity, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    run_dir = args.output_dir / f"{started_at.strftime('%Y%m%dT%H%M%SZ')}_{digest}"
    run_dir.mkdir(parents=True, exist_ok=False)
    pdf_dir = run_dir / "pdf"
    text_dir = run_dir / "text"
    pdf_dir.mkdir()
    text_dir.mkdir()

    download_transport = HttpTransport(minimum_interval_seconds=3.1, timeout_seconds=90.0)
    metadata_client = OpenAlexClient()
    arxiv_client = ArxivClient()
    records = []
    for paper in papers:
        paper_id = _safe_id(str(paper["id"]))
        response = download_transport.get(
            str(paper["pdf_url"]),
            headers={"Accept": "application/pdf"},
        )
        validate_pdf_bytes(response.body, max_bytes=MAX_PDF_BYTES)
        pdf_path = pdf_dir / f"{paper_id}.pdf"
        pdf_path.write_bytes(response.body)
        extracted_text, page_count = extract_pdf_text(response.body)
        text_path = text_dir / f"{paper_id}.txt"
        text_path.write_text(extracted_text, encoding="utf-8")

        verification = None
        doi = paper.get("doi")
        if doi:
            batch = metadata_client.get_by_doi(str(doi))
            resolved = batch.records[0]
            similarity = title_token_similarity(str(paper["expected_title"]), resolved.title)
            if resolved.doi != str(doi).lower() or similarity < 0.70:
                raise ValueError(
                    f"metadata mismatch for {paper_id}: DOI={resolved.doi!r}, "
                    f"title={resolved.title!r}, similarity={similarity:.3f}"
                )
            verification = {
                "source": "openalex",
                "retrieved_at_utc": batch.retrieved_at_utc,
                "request_url": batch.request_url,
                "resolved_title": resolved.title,
                "resolved_doi": resolved.doi,
                "title_token_similarity": similarity,
                "authors": list(resolved.authors),
                "publication_year": resolved.year,
                "venue": resolved.venue,
            }
        elif paper.get("arxiv_id"):
            batch = arxiv_client.get_by_id(str(paper["arxiv_id"]))
            resolved = batch.records[0]
            similarity = title_token_similarity(str(paper["expected_title"]), resolved.title)
            if resolved.arxiv_id != str(paper["arxiv_id"]) or similarity < 0.70:
                raise ValueError(
                    f"metadata mismatch for {paper_id}: arXiv={resolved.arxiv_id!r}, "
                    f"title={resolved.title!r}, similarity={similarity:.3f}"
                )
            verification = {
                "source": "arxiv",
                "retrieved_at_utc": batch.retrieved_at_utc,
                "request_url": batch.request_url,
                "resolved_title": resolved.title,
                "resolved_arxiv_id": resolved.arxiv_id,
                "resolved_doi": resolved.doi,
                "title_token_similarity": similarity,
                "authors": list(resolved.authors),
                "publication_year": resolved.year,
                "venue": resolved.venue,
            }

        records.append({
            **paper,
            "download_final_url": response.url,
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "http_status": response.status,
            "content_type": response.headers.get("content-type"),
            "pdf_file": pdf_path.relative_to(run_dir).as_posix(),
            "pdf_sha256": sha256(response.body).hexdigest(),
            "pdf_bytes": len(response.body),
            "text_file": text_path.relative_to(run_dir).as_posix(),
            "text_sha256": sha256(extracted_text.encode("utf-8")).hexdigest(),
            "text_characters": len(extracted_text),
            "page_count": page_count,
            "metadata_verification": verification,
        })
        print(f"{paper_id}: {page_count} pages, {len(extracted_text):,} text characters")

    _write_json(run_dir / "metadata.json", {
        "workflow": "MyHR TDK curated full-text corpus",
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "free_services_only": True,
        "paid_services_enabled": False,
        "selection_file": str(args.selection),
        "selection_sha256": sha256(selection_bytes).hexdigest(),
        "paper_count": len(records),
        "git": revision,
        "holdout_accessed": False,
        "copyright_note": (
            "Files are retained as local research artifacts only. Access basis and source URL "
            "are recorded per paper; copyright remains with each rightsholder."
        ),
    })
    _write_json(run_dir / "papers.json", records)
    _write_manifest(run_dir)
    print(json.dumps({
        "output_dir": str(run_dir),
        "paper_count": len(records),
        "holdout_accessed": False,
    }, indent=2))


def validate_pdf_bytes(body: bytes, *, max_bytes: int) -> None:
    if not body.startswith(b"%PDF-"):
        raise ValueError("download did not contain a PDF header")
    if len(body) > max_bytes:
        raise ValueError(f"PDF exceeds the {max_bytes}-byte safety limit")


def extract_pdf_text(body: bytes) -> tuple[str, int]:
    reader = PdfReader(io.BytesIO(body), strict=False)
    pages = []
    for number, page in enumerate(reader.pages, start=1):
        pages.append(f"\n\n--- PAGE {number} ---\n\n{page.extract_text() or ''}")
    text = "".join(pages).strip() + "\n"
    if len(text) < 500:
        raise ValueError("PDF text extraction produced fewer than 500 characters")
    return text, len(reader.pages)


def title_token_similarity(expected: str, actual: str) -> float:
    expected_tokens = set(re.findall(r"[a-z0-9]+", expected.lower()))
    actual_tokens = set(re.findall(r"[a-z0-9]+", actual.lower()))
    if not expected_tokens or not actual_tokens:
        return 0.0
    return len(expected_tokens & actual_tokens) / len(expected_tokens | actual_tokens)


def _safe_id(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_.-]+", "_", value).strip("._")
    if not cleaned:
        raise ValueError("paper id is not filesystem-safe")
    return cleaned


def _git_revision() -> dict[str, object]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()
    dirty = bool(subprocess.run(
        ["git", "status", "--porcelain"], cwd=REPO_ROOT, check=True, capture_output=True, text=True
    ).stdout.strip())
    return {"commit": commit, "dirty": dirty}


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


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
