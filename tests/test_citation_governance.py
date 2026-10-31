import json
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.verify_tdk_citations import citation_audit_fingerprint, verify_citation_governance


class CitationGovernanceTests(unittest.TestCase):
    def test_repository_citation_governance_is_valid(self):
        result = verify_citation_governance(
            Path("docs/TDK_REFERENCES.bib"),
            Path("docs/TDK_CITATION_PROVENANCE.json"),
            Path("docs/TDK_CLAIM_EVIDENCE_LEDGER.json"),
        )
        self.assertTrue(result["valid"])

    def test_unknown_claim_citation_is_rejected(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            bibliography, provenance, ledger = self._valid_files(root)
            value = json.loads(ledger.read_text(encoding="utf-8"))
            value["claims"][0]["evidence"][0]["citation_key"] = "missing"
            ledger.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unknown key"):
                verify_citation_governance(bibliography, provenance, ledger)

    def test_duplicate_identifier_is_rejected(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            bibliography, provenance, ledger = self._valid_files(root)
            bibliography.write_text(
                bibliography.read_text(encoding="utf-8")
                + "\n@article{second, title={Second}, doi={10.1/test}}\n",
                encoding="utf-8",
            )
            value = json.loads(provenance.read_text(encoding="utf-8"))
            duplicate = dict(value["records"][0])
            duplicate["citation_key"] = "second"
            value["records"].append(duplicate)
            provenance.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "DOI"):
                verify_citation_governance(bibliography, provenance, ledger)

    def test_strict_mode_requires_local_artifact(self):
        with TemporaryDirectory() as temporary:
            bibliography, provenance, ledger = self._valid_files(Path(temporary))
            with self.assertRaisesRegex(ValueError, "required local full-text artifact"):
                verify_citation_governance(
                    bibliography, provenance, ledger, require_local_artifact=True
                )

    def test_post_audit_evidence_change_is_rejected(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            bibliography, provenance, ledger = self._valid_files(root)
            report = root / "audit.md"
            report.write_text("audited", encoding="utf-8")
            bib_text = bibliography.read_text(encoding="utf-8")
            provenance_value = json.loads(provenance.read_text(encoding="utf-8"))
            ledger_value = json.loads(ledger.read_text(encoding="utf-8"))
            ledger_value["audit_state"] = {
                "status": "independent_audit_passed",
                "report": str(report),
                "fingerprint_sha256": citation_audit_fingerprint(
                    bib_text, provenance_value, ledger_value["claims"]
                ),
            }
            ledger.write_text(json.dumps(ledger_value), encoding="utf-8")
            verify_citation_governance(bibliography, provenance, ledger)

            provenance_value["records"][0]["sources"][0]["retrieved_at"] = "changed"
            provenance.write_text(json.dumps(provenance_value), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "changed after the independent audit"):
                verify_citation_governance(bibliography, provenance, ledger)

    def test_strict_mode_verifies_artifact_hashes_and_page_locator(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            bibliography, provenance, ledger, text_path = self._strict_files(root)
            result = verify_citation_governance(
                bibliography, provenance, ledger, require_local_artifact=True
            )
            self.assertTrue(result["local_artifact_verified"])

            text_path.write_text("tampered", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "checksum failed"):
                verify_citation_governance(
                    bibliography, provenance, ledger, require_local_artifact=True
                )

    def test_duplicate_arxiv_identifier_is_rejected(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            bibliography, provenance, ledger = self._valid_files(root)
            bibliography.write_text(
                bibliography.read_text(encoding="utf-8")
                + "\n@article{second, title={Second}, doi={10.1/second}}\n",
                encoding="utf-8",
            )
            value = json.loads(provenance.read_text(encoding="utf-8"))
            value["records"][0]["arxiv_id"] = "2401.00001"
            duplicate = dict(value["records"][0])
            duplicate.update({"citation_key": "second", "doi": "10.1/second"})
            value["records"].append(duplicate)
            provenance.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "arXiv identifier"):
                verify_citation_governance(bibliography, provenance, ledger)

    def test_arxiv_doi_alias_is_deduplicated_against_arxiv_id(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            bibliography, provenance, ledger = self._valid_files(root)
            bibliography.write_text(
                bibliography.read_text(encoding="utf-8")
                + "\n@article{second, title={Second}, doi={10.48550/arXiv.2401.00001}}\n",
                encoding="utf-8",
            )
            value = json.loads(provenance.read_text(encoding="utf-8"))
            value["records"][0]["arxiv_id"] = "2401.00001"
            duplicate = dict(value["records"][0])
            duplicate.update({
                "citation_key": "second",
                "doi": "10.48550/arXiv.2401.00001",
            })
            duplicate.pop("arxiv_id", None)
            value["records"].append(duplicate)
            provenance.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "arXiv identifier"):
                verify_citation_governance(bibliography, provenance, ledger)

    def test_arxiv_doi_url_alias_is_deduplicated_against_arxiv_id(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            bibliography, provenance, ledger = self._valid_files(root)
            bibliography.write_text(
                bibliography.read_text(encoding="utf-8")
                + "\n@article{second, title={Second}, doi={https://doi.org/10.48550/arXiv.2401.00001}}\n",
                encoding="utf-8",
            )
            value = json.loads(provenance.read_text(encoding="utf-8"))
            value["records"][0]["arxiv_id"] = "2401.00001"
            duplicate = dict(value["records"][0])
            duplicate.update({
                "citation_key": "second",
                "doi": "https://doi.org/10.48550/arXiv.2401.00001",
            })
            duplicate.pop("arxiv_id", None)
            value["records"].append(duplicate)
            provenance.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "arXiv identifier"):
                verify_citation_governance(bibliography, provenance, ledger)

    def test_strict_mode_binds_claim_to_cited_paper_artifact(self):
        with TemporaryDirectory() as temporary:
            bibliography, provenance, ledger, _ = self._strict_files(Path(temporary))
            value = json.loads(ledger.read_text(encoding="utf-8"))
            value["claims"][0]["evidence"][0]["artifact_id"] = "different-paper"
            ledger.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "artifact does not match"):
                verify_citation_governance(
                    bibliography, provenance, ledger, require_local_artifact=True
                )

    def test_strict_mode_requires_manifested_papers_index(self):
        with TemporaryDirectory() as temporary:
            bibliography, provenance, ledger, _ = self._strict_files(Path(temporary))
            artifact = Path(json.loads(provenance.read_text(encoding="utf-8"))["full_text_artifact"])
            manifest_path = artifact / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["files"].pop("papers.json")
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "omits papers.json"):
                verify_citation_governance(
                    bibliography, provenance, ledger, require_local_artifact=True
                )

    def test_strict_mode_checks_every_page_in_range(self):
        with TemporaryDirectory() as temporary:
            bibliography, provenance, ledger, text_path = self._strict_files(Path(temporary))
            artifact = text_path.parents[1]
            text_path.write_text(
                "\n\n--- PAGE 1 ---\n\nEvidence\n\n--- PAGE 3 ---\n\nMore\n",
                encoding="utf-8",
            )
            papers_path = artifact / "papers.json"
            papers = json.loads(papers_path.read_text(encoding="utf-8"))
            papers[0]["page_count"] = 3
            papers[0]["text_sha256"] = sha256(text_path.read_bytes()).hexdigest()
            papers_path.write_text(json.dumps(papers), encoding="utf-8")
            value = json.loads(ledger.read_text(encoding="utf-8"))
            value["claims"][0]["evidence"][0]["locator"] = "PDF pages 1-3"
            ledger.write_text(json.dumps(value), encoding="utf-8")
            self._refresh_manifest(artifact)
            with self.assertRaisesRegex(ValueError, "page 2 missing"):
                verify_citation_governance(
                    bibliography, provenance, ledger, require_local_artifact=True
                )

    @staticmethod
    def _valid_files(root: Path):
        bibliography = root / "refs.bib"
        provenance = root / "provenance.json"
        ledger = root / "ledger.json"
        document = root / "paper.md"
        document.write_text("# Section\n", encoding="utf-8")
        bibliography.write_text(
            "@article{paper, title={Paper}, doi={10.1/test}}\n", encoding="utf-8"
        )
        provenance.write_text(json.dumps({"records": [{
            "citation_key": "paper",
            "doi": "10.1/test",
            "verification_status": "full_text_reviewed",
            "sources": [{
                "service": "crossref",
                "identifier": "10.1/test",
                "retrieved_at": "2026-10-29",
            }],
        }]}), encoding="utf-8")
        ledger.write_text(json.dumps({
            "audit_state": {"status": "pending_independent_audit"},
            "claims": [{
            "claim_id": "claim-1",
            "claim": "A bounded claim.",
            "document": f"{document.as_posix()}#section",
            "status": "verified",
            "evidence": [{
                "citation_key": "paper",
                "evidence_type": "full_text",
                "artifact_id": "paper-artifact",
                "locator": "PDF page 1",
                "supports": "The bounded claim.",
                "support_type": "direct",
            }],
        }]}), encoding="utf-8")
        return bibliography, provenance, ledger

    @staticmethod
    def _strict_files(root: Path):
        bibliography, provenance, ledger = CitationGovernanceTests._valid_files(root)
        artifact = root / "artifact"
        (artifact / "pdf").mkdir(parents=True)
        (artifact / "text").mkdir()
        pdf_path = artifact / "pdf" / "paper-artifact.pdf"
        text_path = artifact / "text" / "paper-artifact.txt"
        pdf_path.write_bytes(b"%PDF-test")
        text_path.write_text("\n\n--- PAGE 1 ---\n\nEvidence\n", encoding="utf-8")
        papers = [{
            "id": "paper-artifact",
            "doi": "10.1/test",
            "page_count": 1,
            "pdf_file": "pdf/paper-artifact.pdf",
            "pdf_sha256": sha256(pdf_path.read_bytes()).hexdigest(),
            "text_file": "text/paper-artifact.txt",
            "text_sha256": sha256(text_path.read_bytes()).hexdigest(),
        }]
        (artifact / "papers.json").write_text(json.dumps(papers), encoding="utf-8")
        files = {
            path.relative_to(artifact).as_posix(): sha256(path.read_bytes()).hexdigest()
            for path in (pdf_path, text_path, artifact / "papers.json")
        }
        (artifact / "manifest.json").write_text(json.dumps({
            "algorithm": "sha256", "files": files,
        }), encoding="utf-8")
        value = json.loads(provenance.read_text(encoding="utf-8"))
        value["full_text_artifact"] = str(artifact)
        value["records"][0]["sources"].append({
            "service": "local_fulltext",
            "identifier": "paper-artifact",
            "retrieved_at": "2026-10-29",
        })
        provenance.write_text(json.dumps(value), encoding="utf-8")
        return bibliography, provenance, ledger, text_path

    @staticmethod
    def _refresh_manifest(artifact: Path):
        manifest_path = artifact / "manifest.json"
        files = {
            path.relative_to(artifact).as_posix(): sha256(path.read_bytes()).hexdigest()
            for path in artifact.rglob("*")
            if path.is_file() and path != manifest_path
        }
        manifest_path.write_text(json.dumps({
            "algorithm": "sha256", "files": files,
        }), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
