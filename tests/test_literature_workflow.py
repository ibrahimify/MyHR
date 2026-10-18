import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.research.literature import (
    ArxivClient,
    HttpResponse,
    OpenAlexClient,
    PaperRecord,
    SemanticScholarClient,
    canonical_paper_key,
    merge_records,
    normalize_doi,
    redact_url,
)
from scripts.fetch_tdk_fulltext import (
    extract_pdf_text,
    title_token_similarity,
    validate_pdf_bytes,
)
from scripts.verify_literature_artifact import verify_artifact


class FakeTransport:
    def __init__(self, body: bytes):
        self.body = body
        self.urls = []
        self.headers = []

    def get(self, url, *, headers=None):
        self.urls.append(url)
        self.headers.append(headers or {})
        return HttpResponse(url, 200, self.body, {})


class LiteratureClientTests(unittest.TestCase):
    def test_semantic_scholar_parses_and_sends_key_only_in_header(self):
        transport = FakeTransport(json.dumps({"data": [{
            "paperId": "s2-1",
            "title": "Policy-aware detection",
            "year": 2025,
            "authors": [{"name": "A. Author"}],
            "externalIds": {"DOI": "https://doi.org/10.1000/ABC"},
            "openAccessPdf": {"url": "https://example.org/paper.pdf", "status": "GOLD"},
        }]}).encode())

        batch = SemanticScholarClient(transport, api_key="secret").search(
            "policy-aware detection", year_from=2022, year_to=2026, limit=5
        )

        self.assertEqual(batch.records[0].doi, "10.1000/abc")
        self.assertNotIn("secret", transport.urls[0])
        self.assertEqual(transport.headers[0]["x-api-key"], "secret")
        self.assertIn("policy+aware+detection", transport.urls[0])

    def test_semantic_scholar_resolves_doi_without_exposing_key(self):
        transport = FakeTransport(json.dumps({
            "paperId": "s2-1",
            "title": "Isolation-Based Anomaly Detection",
            "year": 2012,
            "authors": [],
            "externalIds": {"DOI": "10.1145/2133360.2133363"},
        }).encode())

        batch = SemanticScholarClient(transport, api_key="secret").get_paper(
            "DOI:10.1145/2133360.2133363"
        )

        self.assertEqual(batch.records[0].year, 2012)
        self.assertIn("DOI%3A10.1145%2F2133360.2133363", transport.urls[0])
        self.assertNotIn("secret", transport.urls[0])

    def test_semantic_scholar_citations_and_recommendations_are_parsed(self):
        paper = {"paperId": "s2-2", "title": "Related", "year": 2024, "authors": []}
        citation_transport = FakeTransport(json.dumps({
            "data": [{"citingPaper": paper}],
        }).encode())
        recommendation_transport = FakeTransport(json.dumps({
            "recommendedPapers": [paper],
        }).encode())

        citations = SemanticScholarClient(citation_transport, api_key="secret").get_citations(
            "DOI:10.1000/test", limit=5
        )
        recommendations = SemanticScholarClient(
            recommendation_transport, api_key="secret"
        ).get_recommendations("s2-seed", limit=5)

        self.assertEqual(citations.records[0].title, "Related")
        self.assertEqual(recommendations.records[0].source_id, "s2-2")
        self.assertIn("citations", citation_transport.urls[0])
        self.assertIn("recommendations", recommendation_transport.urls[0])

    def test_openalex_reconstructs_abstract_and_uses_bearer_key(self):
        transport = FakeTransport(json.dumps({"results": [{
            "id": "https://openalex.org/W1",
            "doi": "https://doi.org/10.1000/test",
            "title": "Robust evaluation",
            "publication_year": 2024,
            "authorships": [{"author": {"display_name": "B. Author"}}],
            "abstract_inverted_index": {"Hello": [0], "world": [1]},
            "primary_location": {"source": {"display_name": "Journal"}},
            "best_oa_location": {"landing_page_url": "https://arxiv.org/abs/2401.00001", "pdf_url": "https://arxiv.org/pdf/2401.00001"},
            "open_access": {"oa_status": "green"},
            "cited_by_count": 7,
        }]}).encode())

        batch = OpenAlexClient(transport, api_key="secret").search(
            "robust evaluation", year_from=2022, year_to=2026, limit=5
        )

        self.assertEqual(batch.records[0].abstract, "Hello world")
        self.assertEqual(batch.records[0].arxiv_id, "2401.00001")
        self.assertEqual(transport.headers[0]["Authorization"], "Bearer secret")
        self.assertNotIn("secret", transport.urls[0])

    def test_openalex_doi_lookup_encodes_identifier_and_keeps_key_in_header(self):
        transport = FakeTransport(json.dumps({
            "id": "https://openalex.org/W1",
            "doi": "https://doi.org/10.1000/Test",
            "title": "A verified title",
            "publication_year": 2024,
            "authorships": [],
            "primary_location": {},
            "open_access": {},
        }).encode())

        batch = OpenAlexClient(transport, api_key="secret").get_by_doi("10.1000/Test")

        self.assertEqual(batch.records[0].doi, "10.1000/test")
        self.assertIn("https%3A%2F%2Fdoi.org%2F10.1000%2Ftest", transport.urls[0])
        self.assertNotIn("secret", transport.urls[0])
        self.assertEqual(transport.headers[0]["Authorization"], "Bearer secret")

    def test_openalex_citation_neighborhood_has_both_edge_directions(self):
        class SequenceTransport:
            def __init__(self):
                self.urls = []
                self.headers = []
                self.bodies = [
                    json.dumps({
                        "id": "https://openalex.org/WSEED",
                        "doi": "https://doi.org/10.1000/seed",
                        "title": "Seed",
                        "publication_year": 2020,
                        "referenced_works": ["https://openalex.org/WREF"],
                        "cited_by_count": 1,
                    }).encode(),
                    json.dumps({"results": [{
                        "id": "https://openalex.org/WCITING",
                        "doi": "https://doi.org/10.1000/citing",
                        "title": "Citing",
                        "publication_year": 2024,
                        "cited_by_count": 0,
                    }]}).encode(),
                ]

            def get(self, url, *, headers=None):
                self.urls.append(url)
                self.headers.append(headers or {})
                return HttpResponse(url, 200, self.bodies.pop(0), {})

        transport = SequenceTransport()
        network = OpenAlexClient(transport, api_key="secret").citation_neighborhood(
            "10.1000/seed", citing_limit=5
        )

        self.assertEqual(network["seed"]["openalex_id"], "WSEED")
        self.assertEqual(network["references"], ["WREF"])
        self.assertEqual(network["citing_works"][0]["openalex_id"], "WCITING")
        self.assertIn("cites%3AWSEED", transport.urls[1])
        self.assertTrue(all("secret" not in url for url in transport.urls))

    def test_arxiv_parses_atom_metadata_and_pdf(self):
        body = b'''<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
          <entry><id>https://arxiv.org/abs/2401.00001v2</id><updated>2024-02-01T00:00:00Z</updated>
          <published>2024-01-01T00:00:00Z</published><title> Explainable anomaly detection </title>
          <summary> Full abstract. </summary><author><name>C. Author</name></author>
          <arxiv:doi>10.1000/ARXIV</arxiv:doi><link title="pdf" href="https://arxiv.org/pdf/2401.00001v2"/></entry>
        </feed>'''

        batch = ArxivClient(FakeTransport(body)).search(
            "explainable anomaly", year_from=2022, year_to=2026, limit=5
        )

        self.assertEqual(batch.records[0].arxiv_id, "2401.00001")
        self.assertEqual(batch.records[0].doi, "10.1000/arxiv")
        self.assertEqual(batch.records[0].authors, ("C. Author",))

    def test_arxiv_accepts_explicit_auditable_query_syntax(self):
        transport = FakeTransport(b'''<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"/>''')

        ArxivClient(transport).search(
            'raw:all:"Isolation Forest"', year_from=2022, year_to=2026, limit=5
        )

        self.assertIn("all%3A%22Isolation+Forest%22", transport.urls[0])
        self.assertIn("submittedDate", transport.urls[0])

    def test_arxiv_id_lookup_is_exact_and_validated(self):
        body = b'''<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom"><entry>
        <id>https://arxiv.org/abs/2401.00001v2</id><published>2024-01-01T00:00:00Z</published>
        <title>Verified paper</title><summary>Abstract.</summary><author><name>A. Author</name></author>
        </entry></feed>'''
        transport = FakeTransport(body)

        batch = ArxivClient(transport).get_by_id("2401.00001v2")

        self.assertEqual(batch.records[0].arxiv_id, "2401.00001")
        self.assertIn("id_list=2401.00001", transport.urls[0])
        with self.assertRaisesRegex(ValueError, "invalid arXiv"):
            ArxivClient(transport).get_by_id("not-an-id")

    def test_cross_source_merge_prefers_doi_over_title(self):
        first = _paper("semantic_scholar", "s1", doi="10.1/shared")
        second = _paper("openalex", "W1", doi="https://doi.org/10.1/SHARED")

        merged = merge_records([first, second])

        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["sources"], ["openalex", "semantic_scholar"])
        self.assertEqual(canonical_paper_key(first), "doi:10.1/shared")

    def test_credentials_are_redacted_and_env_file_is_ignored(self):
        self.assertEqual(normalize_doi(" DOI: 10.1000/XYZ. "), "10.1000/xyz")
        self.assertNotIn("secret", redact_url("https://example.org?api_key=secret&x=1"))
        gitignore = Path(".gitignore").read_text(encoding="utf-8")
        self.assertIn(".env", gitignore)

    def test_pdf_validation_rejects_non_pdf_and_oversize_payloads(self):
        with self.assertRaisesRegex(ValueError, "PDF header"):
            validate_pdf_bytes(b"<html>not a paper</html>", max_bytes=100)
        with self.assertRaisesRegex(ValueError, "safety limit"):
            validate_pdf_bytes(b"%PDF-" + b"x" * 100, max_bytes=20)

    def test_pdf_text_extraction_and_title_similarity(self):
        from pypdf import PdfWriter
        import io

        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        payload = io.BytesIO()
        writer.write(payload)
        validate_pdf_bytes(payload.getvalue(), max_bytes=10_000)
        self.assertGreater(title_token_similarity(
            "Isolation-Based Anomaly Detection",
            "Isolation Based Anomaly Detection",
        ), 0.99)
        with self.assertRaisesRegex(ValueError, "fewer than 500"):
            extract_pdf_text(payload.getvalue())

    def test_artifact_verifier_checks_hashes_and_rejects_credentials(self):
        from hashlib import sha256

        with TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            body = b'{"holdout_accessed": false, "paid_services_enabled": false}'
            (run_dir / "metadata.json").write_bytes(body)
            (run_dir / "manifest.json").write_text(json.dumps({
                "algorithm": "sha256",
                "files": {"metadata.json": sha256(body).hexdigest()},
            }), encoding="utf-8")
            self.assertTrue(verify_artifact(run_dir)["checksums_valid"])

            secret = b"OPENALEX_API_KEY=not-a-real-secret-value"
            (run_dir / "metadata.json").write_bytes(secret)
            (run_dir / "manifest.json").write_text(json.dumps({
                "algorithm": "sha256",
                "files": {"metadata.json": sha256(secret).hexdigest()},
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "credential"):
                verify_artifact(run_dir)


def _paper(source: str, source_id: str, doi: str | None) -> PaperRecord:
    return PaperRecord(
        source=source,
        source_id=source_id,
        title="Same title",
        year=2024,
        publication_date="2024-01-01",
        authors=("A. Author",),
        abstract="Abstract",
        doi=normalize_doi(doi),
        arxiv_id=None,
        venue=None,
        citation_count=1,
        landing_url=None,
        pdf_url=None,
        open_access_status=None,
        license=None,
    )


if __name__ == "__main__":
    unittest.main()
