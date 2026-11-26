# TDK Literature Workflow

Research title:

**MyHR: Policy-Aware Machine Learning for Anomaly Detection in Workforce Progression**

Status: reusable development workflow. It does not access the experimental holdout or alter the experiment protocol.

## Architecture Decision

The workflow uses small direct Python clients rather than third-party MCP servers. The three services expose straightforward public HTTP APIs, and direct clients provide a smaller dependency and permission surface, visible request construction, explicit rate limiting, and reproducible raw responses. MCP remains useful for interactive tools, but it adds no scientific value to this read-only metadata task.

Only free access modes are implemented. The code contains no billing integration and records `paid_services_enabled: false` in generated artifacts.

## Official Services

| Service | Use | Authentication | Politeness behavior |
| --- | --- | --- | --- |
| [Semantic Scholar Academic Graph API](https://api.semanticscholar.org/api-docs/) | Discovery, citation counts, DOI/arXiv cross-identifiers, open-access links | Optional free API key in `SEMANTIC_SCHOLAR_API_KEY` | One request per second when using the client; bounded retries on `429` and server errors |
| [OpenAlex API](https://help.openalex.org/) | Discovery, scholarly metadata, open-access locations, DOI verification | Keyless basic access; optional free key in `OPENALEX_API_KEY` | Bearer header for keys, short pacing, bounded retries |
| [arXiv API](https://info.arxiv.org/help/api/index.html) | Recent preprints, exact arXiv metadata, legal author-submitted PDFs | No key | At least three seconds between requests, following the [arXiv API manual](https://info.arxiv.org/help/api/user-manual.html) |
| [Crossref REST API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/) | DOI registration metadata and independent identifier verification | No key; optional contact email in `MYHR_RESEARCH_CONTACT` | Versioned REST endpoint, bounded retries, caching through write-once artifacts, and polite-pool identification when a contact is configured |

OpenAlex documents a free key with a daily free budget on its [authentication page](https://help.openalex.org/how-to-use-the-api/api-authentication). No payment method is required for the workflow. arXiv metadata is reusable, but each paper retains its own copyright and license; downloaded files are local research artifacts and are never committed.

## Security

- API keys are read only from process environment variables.
- Keys are sent in request headers, never query strings.
- `.env`, local research outputs, PDFs, and extracted text are ignored by Git.
- `.env.example` contains names only, never values.
- Artifacts record whether a key was present, never the key itself.
- `scripts/verify_literature_artifact.py` recomputes SHA-256 hashes and scans tracked artifact content for likely credentials.
- HTTP failures, certificate failures, non-PDF responses, oversized files, and metadata mismatches fail closed.

Optional PowerShell setup for the current terminal:

```powershell
$env:SEMANTIC_SCHOLAR_API_KEY = "your-free-key"
$env:OPENALEX_API_KEY = "your-free-key"
$env:MYHR_RESEARCH_CONTACT = "your-university-email"
```

To persist a key for the Windows user without writing it to the repository:

```powershell
[Environment]::SetEnvironmentVariable("SEMANTIC_SCHOLAR_API_KEY", "your-free-key", "User")
```

Request a free Semantic Scholar key through its [API key form](https://www.semanticscholar.org/product/api#api-key-form). A key is strongly recommended because anonymous requests use a shared throttled pool.

## Reproducible Commands

Install the normal dependencies, including `pypdf`:

```powershell
python -m pip install -r requirements.txt
```

Run a small live metadata check:

```powershell
python scripts/refresh_tdk_literature.py --smoke --sources openalex,arxiv,crossref --output-dir research_outputs/literature_smoke
```

After configuring the Semantic Scholar key, verify it independently:

```powershell
python scripts/refresh_tdk_literature.py --smoke --sources semantic_scholar --output-dir research_outputs/literature_smoke
```

Refresh the full metadata discovery corpus:

```powershell
python scripts/refresh_tdk_literature.py --max-results 12
```

Build a bounded citation neighborhood around DOI-bearing core papers:

```powershell
python scripts/build_tdk_citation_network.py --citing-limit 25
```

Fetch the curated legal full-text corpus and extract searchable text:

```powershell
python scripts/fetch_tdk_fulltext.py
```

Verify either generated artifact:

```powershell
python scripts/verify_literature_artifact.py research_outputs/literature/<run-id>
python scripts/verify_literature_artifact.py research_outputs/literature_fulltext/<run-id>
```

Every run directory is timestamped and write-once. It stores configuration hashes, source revision and dirty state, request metadata, source records, normalized records, publication-year trend counts, file hashes, and an explicit `holdout_accessed: false` where applicable. The Semantic Scholar client also exposes tested citation and recommendation retrieval methods; these become reliably usable after the free key is configured.

## Query Scope

`config/tdk_literature_queries.json` searches mainly from 2022 through 2026 and separately searches the 2008-2012 Isolation Forest foundation. Topics cover:

- policy-aware and contextual anomaly detection;
- Isolation Forest evaluation;
- explainable anomaly detection and human review;
- synthetic-data validation and benchmark design;
- workforce and HR anomalies;
- entity resolution and duplicate records;
- robust evaluation and statistical significance.

`config/tdk_fulltext_selection.json` is a human-reviewed subset. A paper enters the full-text corpus only when its title and identifier can be verified and its PDF is legally accessible from arXiv, the publisher, or an author-controlled page.

## Verification Status On 2026-10-17

- OpenAlex live search: passed across 13 targeted queries, producing 130 source records.
- OpenAlex DOI resolution: passed for every DOI-bearing paper in the curated corpus.
- arXiv live search: passed across the same query set, producing 110 source records.
- arXiv exact-ID resolution: passed for every arXiv-only paper in the curated corpus.
- Curated full-text run: 16 papers, 428 pages, PDF validation, text extraction, DOI/arXiv resolution, and checksums passed.
- The preserved metadata run contains 240 source records and 231 merged records; manifest and credential checks passed.
- The preserved full-text run contains 16 papers; manifest and file checks passed.
- OpenAlex citation-network run: passed for all six DOI-bearing core papers, including outgoing reference IDs and bounded incoming citing works.
- Semantic Scholar DOI resolution previously succeeded, but the anonymous shared pool returned HTTP `429` during the 2026-10-17 refresh. The client and key handling pass automated tests; reliable live discovery remains an optional setup item requiring a free key.

This is an integration limitation, not missing research evidence: OpenAlex, arXiv, DOI metadata, and the paper PDFs independently verify the tracked core references.

## Integration Recheck On 2026-10-29

- OpenAlex, arXiv, and Crossref each passed the same real Isolation Forest smoke query through the repository client.
- Crossref independently resolved the four corrected publication DOIs and the Krippendorff DOI to matching titles.
- Semantic Scholar remains configured and covered by client tests, but its anonymous shared pool returned HTTP `429` after bounded retries. No paid access was enabled. A free `SEMANTIC_SCHOLAR_API_KEY` is required for a reliable live recheck from this network.
- The 18-entry bibliography and 15-claim evidence ledger pass the citation-governance verifier. Two claim records remain intentionally unverified because inspected full text is not preserved.

Official service documentation was rechecked before the integration update: OpenAlex documents free keyless casual access and an optional free key, Crossref documents free public and polite-pool access, arXiv documents its query interface and three-second pacing guidance, and Semantic Scholar documents header-based optional API keys.

## Evidence Recheck On 2026-11-22

- The curated corpus now contains 17 legally accessible full texts. The added Krippendorff paper was resolved through the University of Pennsylvania repository and matched to its DOI and document title.
- The first repository bitstream candidate was rejected because its extracted title did not match the selected paper. Full-text retrieval now enforces document-title token coverage, preventing metadata from being paired with the wrong PDF.
- The 18-entry bibliography and 15-claim evidence ledger pass strict local-artifact verification with no unverified records or claims.
- The reliability claim is deliberately limited to what the inspected paper supports: independent coders, common instructions, and agreement assessment. Disagreement retention and adjudication remain MyHR study-design choices.
- OpenAlex, arXiv, and Crossref remain operational. Semantic Scholar's anonymous endpoint returned HTTP `429` after bounded retries; the integration is implemented and tested, but a reliable live check still requires the optional free API key.

## Recency Recheck On 2026-11-26

- A bounded OpenAlex, Crossref, and arXiv refresh returned 298 source records and 282 deduplicated records. Discovery stopped after selecting nine directly relevant additions; this was not an exhaustive review.
- The centralized bibliography now contains 27 verified entries: 19 published from 2022 through 2026 and eight retained foundational sources. The claim-evidence ledger contains 22 scoped claims.
- The additions strengthen evidence for temporal distribution shift, synthetic-data limitations, responsible HR use, anomaly-detector diversity, benchmark reliability, and entity-resolution evaluation. Adjacent time-series evidence and the one arXiv preprint are labelled as such rather than presented as direct workforce-progression validation.
- Official publisher or repository pages and legally accessible full text were inspected for the selected additions. OpenAlex and Crossref were also used to cross-check identifiers and metadata; no paid service or credential was used.
- Portable citation verification passes with no unverified bibliography entry or claim. Strict local-artifact verification is currently unavailable because the previously recorded full-text artifact directory is not present in this checkout; the provenance registry retains that historical location instead of claiming a new local archive.
- An independent recheck verified the nine additions and required narrower manuscript wording where evidence came from adjacent domains.

## Refresh Rules

1. Never replace an old artifact directory.
2. Review newly discovered papers before adding them to the curated manifest.
3. Do not infer findings from titles or citation counts.
4. Read the methods, evaluation, limitations, and conclusion of included full papers.
5. Verify DOI and arXiv identifiers before adding a bibliography entry.
6. Document protocol proposals separately; literature refreshes must not silently change the frozen experiment.
7. Never regenerate, rerun, or inspect unpublished contents of the completed protected evaluation from this workflow.
8. Every literature-supported claim must be recorded in `TDK_CLAIM_EVIDENCE_LEDGER.json`; every paper must have one deduplicated bibliography entry and a provenance record.
9. Run `python scripts/verify_tdk_citations.py --require-local-artifact` before research review. CI runs portable registry checks; publication review also verifies local checksums, page locators, citation accuracy, and claim scope.
