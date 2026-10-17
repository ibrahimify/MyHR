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
python scripts/refresh_tdk_literature.py --smoke --sources openalex,arxiv --output-dir research_outputs/literature_smoke
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
- Literature metadata artifact `20261017T215024Z_f79f81f2c2b1`: 240 source records, 231 merged records, manifest and credential scan passed.
- Full-text artifact `20261017T215119Z_4b354b03c1af`: 16 papers, manifest and credential scan passed.
- OpenAlex citation-network run: passed for all six DOI-bearing core papers, including outgoing reference IDs and bounded incoming citing works.
- Semantic Scholar DOI resolution previously succeeded, but the anonymous shared pool returned HTTP `429` during the 2026-10-17 refresh. The client and key handling pass automated tests; reliable live discovery remains an optional setup item requiring a free key.

This is an integration limitation, not missing research evidence: OpenAlex, arXiv, DOI metadata, and the paper PDFs independently verify the tracked core references.

## Refresh Rules

1. Never replace an old artifact directory.
2. Review newly discovered papers before adding them to the curated manifest.
3. Do not infer findings from titles or citation counts.
4. Read the methods, evaluation, limitations, and conclusion of included full papers.
5. Verify DOI and arXiv identifiers before adding a bibliography entry.
6. Document protocol proposals separately; literature refreshes must not silently change the frozen experiment.
7. Never query, generate, or inspect the locked experimental holdout from this workflow.
