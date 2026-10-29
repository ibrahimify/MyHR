"""Verify bibliography, citation provenance, and claim-to-source evidence."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re


ENTRY_START = re.compile(r"^\s*@\w+\s*\{\s*([^,\s]+)\s*,", re.MULTILINE)
DOI_FIELD = re.compile(r"\bdoi\s*=\s*\{([^}]+)\}", re.IGNORECASE)


def verify_citation_governance(
    bibliography_path: Path,
    provenance_path: Path,
    ledger_path: Path,
    *,
    require_local_artifact: bool = False,
) -> dict[str, object]:
    bibliography = bibliography_path.read_text(encoding="utf-8")
    entries = _bibliography_entries(bibliography)
    keys = list(entries)
    if not keys:
        raise ValueError("bibliography contains no entries")
    _require_unique(keys, "bibliography key")

    provenance = _read_object(provenance_path)
    records = provenance.get("records")
    if not isinstance(records, list):
        raise ValueError("citation provenance records must be a list")
    provenance_keys = [_required_text(item, "citation_key") for item in records]
    _require_unique(provenance_keys, "provenance citation_key")
    if set(provenance_keys) != set(keys):
        missing = sorted(set(keys) - set(provenance_keys))
        extra = sorted(set(provenance_keys) - set(keys))
        raise ValueError(f"provenance/bibliography mismatch; missing={missing}, extra={extra}")

    doi_owners: dict[str, str] = {}
    arxiv_owners: dict[str, str] = {}
    provenance_by_key = {}
    for item in records:
        provenance_by_key[item["citation_key"]] = item
        status = _required_text(item, "verification_status")
        if status not in {"full_text_reviewed", "full_text_available", "metadata_verified", "unverified"}:
            raise ValueError(f"invalid verification_status for {item['citation_key']}: {status}")
        sources = item.get("sources")
        if not isinstance(sources, list) or not sources:
            raise ValueError(f"provenance source missing for {item['citation_key']}")
        for source in sources:
            _required_text(source, "service")
            _required_text(source, "identifier")
            _required_text(source, "retrieved_at")
        doi = _normalize_doi(item.get("doi"))
        arxiv_id = str(item.get("arxiv_id") or "").strip().lower()
        if doi:
            _register_identifier(doi_owners, doi, item["citation_key"], "DOI")
        if arxiv_id:
            _register_identifier(
                arxiv_owners, arxiv_id, item["citation_key"], "arXiv identifier"
            )
        doi_arxiv_id = _arxiv_id_from_doi(doi)
        if doi_arxiv_id:
            _register_identifier(
                arxiv_owners, doi_arxiv_id, item["citation_key"], "arXiv identifier"
            )
        bib_doi_match = DOI_FIELD.search(entries[item["citation_key"]])
        bib_doi = _normalize_doi(bib_doi_match.group(1)) if bib_doi_match else None
        provenance_doi = _normalize_doi(item.get("doi")) or None
        if bib_doi != provenance_doi:
            raise ValueError(
                f"DOI mismatch for {item['citation_key']}: bibliography={bib_doi}, "
                f"provenance={provenance_doi}"
            )
    artifact_value = str(provenance.get("full_text_artifact") or "").strip()
    artifact_root = Path(artifact_value) if artifact_value else None
    artifact_result = None
    if artifact_root is not None and artifact_root.is_dir():
        artifact_result = _verify_fulltext_artifact(provenance, records, artifact_root)
    elif require_local_artifact:
        raise ValueError(f"required local full-text artifact is unavailable: {artifact_root}")

    ledger = _read_object(ledger_path)
    audit_state = ledger.get("audit_state")
    if not isinstance(audit_state, dict):
        raise ValueError("claim ledger audit_state must be an object")
    audit_status = _required_text(audit_state, "status")
    if audit_status not in {"pending_independent_audit", "independent_audit_passed"}:
        raise ValueError(f"invalid independent audit status: {audit_status}")
    if audit_status == "independent_audit_passed":
        report = Path(_required_text(audit_state, "report"))
        if not report.is_file():
            raise ValueError(f"independent audit report is missing: {report}")
    claims = ledger.get("claims")
    if not isinstance(claims, list):
        raise ValueError("claim ledger claims must be a list")
    if audit_status == "independent_audit_passed":
        expected_fingerprint = _required_text(audit_state, "fingerprint_sha256")
        actual_fingerprint = citation_audit_fingerprint(bibliography, provenance, claims)
        if expected_fingerprint != actual_fingerprint:
            raise ValueError("citation evidence changed after the independent audit")
    claim_ids = [_required_text(item, "claim_id") for item in claims]
    _require_unique(claim_ids, "claim_id")
    for claim in claims:
        _required_text(claim, "claim")
        _required_text(claim, "document")
        _verify_document_anchor(_required_text(claim, "document"))
        status = _required_text(claim, "status")
        if status not in {"verified", "inference", "unverified", "contradicted"}:
            raise ValueError(f"claim {claim['claim_id']} has invalid status {status}")
        evidence = claim.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            raise ValueError(f"claim {claim['claim_id']} has no evidence")
        for item in evidence:
            citation_key = _required_text(item, "citation_key")
            if citation_key not in keys:
                raise ValueError(f"claim {claim['claim_id']} cites unknown key {citation_key}")
            evidence_type = _required_text(item, "evidence_type")
            if evidence_type not in {"full_text", "metadata", "repository_artifact", "expert_judgment"}:
                raise ValueError(f"claim {claim['claim_id']} has invalid evidence type {evidence_type}")
            _required_text(item, "locator")
            _required_text(item, "supports")
            support_type = _required_text(item, "support_type")
            if support_type not in {"direct", "inference", "contradiction", "identity_only"}:
                raise ValueError(
                    f"claim {claim['claim_id']} has invalid support type {support_type}"
                )
            provenance_status = provenance_by_key[citation_key]["verification_status"]
            if evidence_type == "full_text" and provenance_status != "full_text_reviewed":
                raise ValueError(
                    f"claim {claim['claim_id']} uses unreviewed full text {citation_key}"
                )
            if evidence_type == "full_text":
                artifact_id = _required_text(item, "artifact_id")
                if not re.fullmatch(r"PDF pages? \d+(?:-\d+)?", item["locator"]):
                    raise ValueError(
                        f"claim {claim['claim_id']} needs an exact PDF page locator"
                    )
                if artifact_result is not None:
                    expected_artifacts = {
                        source["identifier"]
                        for source in provenance_by_key[citation_key]["sources"]
                        if source["service"] == "local_fulltext"
                    }
                    if artifact_id not in expected_artifacts:
                        raise ValueError(
                            f"claim {claim['claim_id']} artifact does not match {citation_key}"
                        )
                    paper = artifact_result["papers_by_id"].get(artifact_id)
                    if not paper:
                        raise ValueError(
                            f"claim {claim['claim_id']} references unknown artifact {artifact_id}"
                        )
                    _verify_page_locator(item["locator"], paper, artifact_root)
        if status in {"verified", "inference"} and all(
            item["evidence_type"] == "metadata" for item in evidence
        ):
            raise ValueError(f"claim {claim['claim_id']} relies only on metadata")

    cited_keys = {
        item["citation_key"]
        for claim in claims
        for item in claim.get("evidence", [])
    }
    return {
        "bibliography_entries": len(keys),
        "provenance_records": len(records),
        "claims": len(claims),
        "cited_bibliography_entries": len(cited_keys),
        "unverified_entries": sorted(
            item["citation_key"] for item in records if item["verification_status"] == "unverified"
        ),
        "unverified_claims": sorted(
            item["claim_id"] for item in claims if item["status"] == "unverified"
        ),
        "local_artifact_verified": artifact_result is not None,
        "legacy_text_hash_mismatches": (
            artifact_result["legacy_text_hash_mismatches"] if artifact_result else None
        ),
        "valid": True,
    }


def _read_object(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def citation_audit_fingerprint(
    bibliography: str,
    provenance: dict[str, object],
    claims: list[dict[str, object]],
) -> str:
    payload = {
        "bibliography": bibliography.replace("\r\n", "\n"),
        "provenance": provenance,
        "claims": claims,
    }
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return sha256(encoded).hexdigest()


def _bibliography_entries(text: str) -> dict[str, str]:
    matches = list(ENTRY_START.finditer(text))
    entries = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        entries[match.group(1)] = text[match.start():end]
    return entries


def _required_text(value: object, key: str) -> str:
    if not isinstance(value, dict) or not isinstance(value.get(key), str) or not value[key].strip():
        raise ValueError(f"required non-empty text field missing: {key}")
    return value[key].strip()


def _verify_fulltext_artifact(
    provenance: dict[str, object],
    records: list[dict[str, object]],
    artifact_root: Path,
) -> dict[str, object]:
    manifest = _read_object(artifact_root / "manifest.json")
    files = manifest.get("files")
    if manifest.get("algorithm") != "sha256" or not isinstance(files, dict):
        raise ValueError("invalid full-text artifact manifest")
    for relative, expected in files.items():
        path = artifact_root / relative
        if not path.is_file() or sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"full-text artifact checksum failed: {relative}")
    papers_value = json.loads((artifact_root / "papers.json").read_text(encoding="utf-8"))
    if "papers.json" not in files:
        raise ValueError("full-text manifest omits papers.json")
    if not isinstance(papers_value, list):
        raise ValueError("full-text papers.json must contain a list")
    papers_by_id = {paper["id"]: paper for paper in papers_value}
    mismatches = 0
    for record in records:
        if record["verification_status"] != "full_text_reviewed":
            continue
        local_sources = [
            source for source in record["sources"] if source["service"] == "local_fulltext"
        ]
        if len(local_sources) != 1:
            raise ValueError(f"reviewed paper needs one local artifact: {record['citation_key']}")
        artifact_id = local_sources[0]["identifier"]
        paper = papers_by_id.get(artifact_id)
        if not paper:
            raise ValueError(f"local full-text paper is missing: {artifact_id}")
        record_arxiv = str(record.get("arxiv_id") or "").lower()
        paper_arxiv = str(paper.get("arxiv_id") or "").lower()
        if record_arxiv and paper_arxiv and record_arxiv != paper_arxiv:
            raise ValueError(f"full-text arXiv identity mismatch: {artifact_id}")
        record_doi = str(record.get("doi") or "").lower()
        paper_doi = str(paper.get("doi") or "").lower()
        if record_doi and paper_doi and record_doi != paper_doi:
            raise ValueError(f"full-text DOI identity mismatch: {artifact_id}")
        for kind in ("pdf", "text"):
            relative = paper[f"{kind}_file"]
            if relative not in files:
                raise ValueError(f"manifest omits {relative}")
            recorded_hash = paper.get(f"{kind}_sha256")
            if recorded_hash != files[relative]:
                if kind == "text":
                    mismatches += 1
                else:
                    raise ValueError(f"per-paper PDF hash mismatch: {artifact_id}")
    if mismatches:
        limitations = provenance.get("known_artifact_limitations") or []
        codes = {item.get("code") for item in limitations if isinstance(item, dict)}
        if "legacy_text_hash_pre_newline_normalization" not in codes:
            raise ValueError("legacy per-paper text hash mismatch is not documented")
    return {"papers_by_id": papers_by_id, "legacy_text_hash_mismatches": mismatches}


def _verify_page_locator(locator: str, paper: dict[str, object], artifact_root: Path) -> None:
    match = re.fullmatch(r"PDF pages? (\d+)(?:-(\d+))?", locator)
    if not match:
        raise ValueError(f"invalid page locator: {locator}")
    start = int(match.group(1))
    end = int(match.group(2) or start)
    page_count = int(paper["page_count"])
    if start < 1 or end < start or end > page_count:
        raise ValueError(f"page locator outside artifact: {locator}")
    text = (artifact_root / paper["text_file"]).read_text(encoding="utf-8")
    for page in range(start, end + 1):
        if f"--- PAGE {page} ---" not in text:
            raise ValueError(f"page {page} missing from extracted artifact {paper['id']}")


def _verify_document_anchor(value: str) -> None:
    path_text, separator, anchor = value.partition("#")
    path = Path(path_text)
    if not path.is_file():
        raise ValueError(f"claim document does not exist: {path}")
    if not separator:
        return
    headings = re.findall(r"^#{1,6}\s+(.+?)\s*$", path.read_text(encoding="utf-8"), re.MULTILINE)
    slugs = {
        re.sub(r"[^a-z0-9 -]", "", heading.lower()).strip().replace(" ", "-")
        for heading in headings
    }
    if anchor not in slugs:
        raise ValueError(f"claim document anchor does not exist: {value}")


def _require_unique(values: list[str], label: str) -> None:
    duplicates = sorted({value for value in values if values.count(value) > 1})
    if duplicates:
        raise ValueError(f"duplicate {label}: {duplicates}")


def _register_identifier(
    owners: dict[str, str], identifier: str, citation_key: str, label: str
) -> None:
    existing = owners.get(identifier)
    if existing and existing != citation_key:
        raise ValueError(
            f"duplicate {label}: {identifier} is used by {existing} and {citation_key}"
        )
    owners[identifier] = citation_key


def _arxiv_id_from_doi(doi: str) -> str | None:
    match = re.fullmatch(r"10\.48550/arxiv\.(.+)", doi, re.IGNORECASE)
    return match.group(1).lower() if match else None


def _normalize_doi(value: object) -> str:
    doi = str(value or "").strip().lower()
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi)
    doi = re.sub(r"^doi:\s*", "", doi)
    return doi.rstrip(" .")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bibliography", type=Path, default=Path("docs/TDK_REFERENCES.bib"))
    parser.add_argument("--provenance", type=Path, default=Path("docs/TDK_CITATION_PROVENANCE.json"))
    parser.add_argument("--ledger", type=Path, default=Path("docs/TDK_CLAIM_EVIDENCE_LEDGER.json"))
    parser.add_argument("--require-local-artifact", action="store_true")
    args = parser.parse_args()
    print(json.dumps(verify_citation_governance(
        args.bibliography, args.provenance, args.ledger,
        require_local_artifact=args.require_local_artifact,
    ), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
