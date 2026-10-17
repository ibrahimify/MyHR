"""Auditable clients for free scholarly metadata services.

The clients intentionally use the Python standard library. This keeps the
research workflow independent from the desktop application's dependency set
and makes every HTTP request visible in one small module.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import os
import re
from time import monotonic, sleep
from typing import Callable, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET


SEMANTIC_SCHOLAR_BASE = "https://api.semanticscholar.org/graph/v1"
SEMANTIC_SCHOLAR_RECOMMENDATIONS_BASE = "https://api.semanticscholar.org/recommendations/v1"
OPENALEX_BASE = "https://api.openalex.org"
ARXIV_BASE = "https://export.arxiv.org/api/query"


class LiteratureApiError(RuntimeError):
    """Raised when a scholarly API cannot return a valid response."""


@dataclass(frozen=True)
class PaperRecord:
    source: str
    source_id: str
    title: str
    year: int | None
    publication_date: str | None
    authors: tuple[str, ...]
    abstract: str | None
    doi: str | None
    arxiv_id: str | None
    venue: str | None
    citation_count: int | None
    landing_url: str | None
    pdf_url: str | None
    open_access_status: str | None
    license: str | None

    def as_json(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SearchBatch:
    source: str
    query: str
    request_url: str
    retrieved_at_utc: str
    records: tuple[PaperRecord, ...]
    raw_body: bytes
    raw_extension: str


@dataclass(frozen=True)
class HttpResponse:
    url: str
    status: int
    body: bytes
    headers: dict[str, str]


class HttpTransport:
    """Small GET transport with polite pacing and bounded retries."""

    def __init__(
        self,
        *,
        minimum_interval_seconds: float = 0.0,
        timeout_seconds: float = 30.0,
        max_attempts: int = 4,
        sleeper: Callable[[float], None] = sleep,
    ) -> None:
        self.minimum_interval_seconds = minimum_interval_seconds
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max_attempts
        self._sleeper = sleeper
        self._last_request_at: float | None = None

    def get(self, url: str, *, headers: dict[str, str] | None = None) -> HttpResponse:
        request_headers = {"User-Agent": _user_agent(), "Accept": "*/*"}
        request_headers.update(headers or {})
        last_error: Exception | None = None
        for attempt in range(self.max_attempts):
            self._wait_for_rate_limit()
            request = Request(url, headers=request_headers, method="GET")
            try:
                with urlopen(request, timeout=self.timeout_seconds) as response:
                    body = response.read()
                    return HttpResponse(
                        url=response.geturl(),
                        status=response.status,
                        body=body,
                        headers={key.lower(): value for key, value in response.headers.items()},
                    )
            except HTTPError as error:
                last_error = error
                if error.code not in {429, 500, 502, 503, 504} or attempt + 1 >= self.max_attempts:
                    detail = error.read().decode("utf-8", errors="replace")[:500]
                    raise LiteratureApiError(
                        f"GET {redact_url(url)} failed with HTTP {error.code}: {detail}"
                    ) from error
                self._sleeper(_retry_delay(error.headers.get("Retry-After"), attempt))
            except URLError as error:
                last_error = error
                if attempt + 1 >= self.max_attempts:
                    raise LiteratureApiError(f"GET {redact_url(url)} failed: {error.reason}") from error
                self._sleeper(2 ** attempt)
        raise LiteratureApiError(f"GET {redact_url(url)} failed: {last_error}")

    def _wait_for_rate_limit(self) -> None:
        now = monotonic()
        if self._last_request_at is not None:
            remaining = self.minimum_interval_seconds - (now - self._last_request_at)
            if remaining > 0:
                self._sleeper(remaining)
        self._last_request_at = monotonic()


class SemanticScholarClient:
    def __init__(self, transport: HttpTransport | None = None, api_key: str | None = None) -> None:
        self.transport = transport or HttpTransport(minimum_interval_seconds=1.05)
        self.api_key = api_key if api_key is not None else os.getenv("SEMANTIC_SCHOLAR_API_KEY")

    def search(self, query: str, *, year_from: int, year_to: int, limit: int) -> SearchBatch:
        fields = (
            "paperId,title,year,publicationDate,authors,abstract,externalIds,venue,"
            "citationCount,url,openAccessPdf,isOpenAccess"
        )
        params = {
            "query": query.replace("-", " "),
            "year": f"{year_from}-{year_to}",
            "limit": min(max(limit, 1), 100),
            "fields": fields,
        }
        request_url = f"{SEMANTIC_SCHOLAR_BASE}/paper/search?{urlencode(params)}"
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        response = self.transport.get(request_url, headers=headers)
        payload = _json_object(response.body, "Semantic Scholar")
        records = tuple(_semantic_scholar_record(item) for item in payload.get("data", []))
        return _batch("semantic_scholar", query, response, records, "json")

    def get_paper(self, identifier: str) -> SearchBatch:
        """Resolve a DOI, arXiv ID, Corpus ID, or Semantic Scholar paper ID."""

        fields = (
            "paperId,title,year,publicationDate,authors,abstract,externalIds,venue,"
            "citationCount,referenceCount,influentialCitationCount,url,openAccessPdf,isOpenAccess"
        )
        encoded_identifier = quote(identifier, safe="")
        request_url = (
            f"{SEMANTIC_SCHOLAR_BASE}/paper/{encoded_identifier}?"
            f"{urlencode({'fields': fields})}"
        )
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        response = self.transport.get(request_url, headers=headers)
        payload = _json_object(response.body, "Semantic Scholar")
        record = _semantic_scholar_record(payload)
        return _batch("semantic_scholar", identifier, response, (record,), "json")

    def get_citations(self, identifier: str, *, limit: int = 20) -> SearchBatch:
        fields = (
            "paperId,title,year,publicationDate,authors,abstract,externalIds,venue,"
            "citationCount,url,openAccessPdf,isOpenAccess"
        )
        encoded_identifier = quote(identifier, safe="")
        request_url = (
            f"{SEMANTIC_SCHOLAR_BASE}/paper/{encoded_identifier}/citations?"
            f"{urlencode({'limit': min(max(limit, 1), 100), 'fields': fields})}"
        )
        response = self.transport.get(request_url, headers=self._headers())
        payload = _json_object(response.body, "Semantic Scholar")
        papers = [item.get("citingPaper") for item in payload.get("data", [])]
        records = tuple(_semantic_scholar_record(item) for item in papers if isinstance(item, dict))
        return _batch("semantic_scholar", identifier, response, records, "json")

    def get_recommendations(self, identifier: str, *, limit: int = 20) -> SearchBatch:
        fields = (
            "paperId,title,year,publicationDate,authors,abstract,externalIds,venue,"
            "citationCount,url,openAccessPdf,isOpenAccess"
        )
        encoded_identifier = quote(identifier, safe="")
        request_url = (
            f"{SEMANTIC_SCHOLAR_RECOMMENDATIONS_BASE}/papers/forpaper/{encoded_identifier}?"
            f"{urlencode({'limit': min(max(limit, 1), 100), 'fields': fields})}"
        )
        response = self.transport.get(request_url, headers=self._headers())
        payload = _json_object(response.body, "Semantic Scholar")
        records = tuple(
            _semantic_scholar_record(item)
            for item in payload.get("recommendedPapers", [])
            if isinstance(item, dict)
        )
        return _batch("semantic_scholar", identifier, response, records, "json")

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return headers


class OpenAlexClient:
    def __init__(self, transport: HttpTransport | None = None, api_key: str | None = None) -> None:
        self.transport = transport or HttpTransport(minimum_interval_seconds=0.12)
        self.api_key = api_key if api_key is not None else os.getenv("OPENALEX_API_KEY")

    def search(self, query: str, *, year_from: int, year_to: int, limit: int) -> SearchBatch:
        params = {
            "search": query,
            "filter": f"from_publication_date:{year_from}-01-01,to_publication_date:{year_to}-12-31",
            "per_page": min(max(limit, 1), 100),
            "select": (
                "id,doi,title,publication_year,publication_date,authorships,abstract_inverted_index,"
                "primary_location,best_oa_location,open_access,cited_by_count"
            ),
        }
        request_url = f"{OPENALEX_BASE}/works?{urlencode(params)}"
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        response = self.transport.get(request_url, headers=headers)
        payload = _json_object(response.body, "OpenAlex")
        records = tuple(_openalex_record(item) for item in payload.get("results", []))
        return _batch("openalex", query, response, records, "json")

    def get_by_doi(self, doi: str) -> SearchBatch:
        normalized = normalize_doi(doi)
        if not normalized:
            raise ValueError("a DOI is required")
        identifier = quote(f"https://doi.org/{normalized}", safe="")
        params = {
            "select": (
                "id,doi,title,publication_year,publication_date,authorships,abstract_inverted_index,"
                "primary_location,best_oa_location,open_access,cited_by_count"
            )
        }
        request_url = f"{OPENALEX_BASE}/works/{identifier}?{urlencode(params)}"
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        response = self.transport.get(request_url, headers=headers)
        payload = _json_object(response.body, "OpenAlex")
        return _batch("openalex", normalized, response, (_openalex_record(payload),), "json")

    def citation_neighborhood(self, doi: str, *, citing_limit: int = 25) -> dict[str, object]:
        normalized = normalize_doi(doi)
        if not normalized:
            raise ValueError("a DOI is required")
        identifier = quote(f"https://doi.org/{normalized}", safe="")
        seed_url = (
            f"{OPENALEX_BASE}/works/{identifier}?"
            f"{urlencode({'select': 'id,doi,title,publication_year,referenced_works,cited_by_count'})}"
        )
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        seed_response = self.transport.get(seed_url, headers=headers)
        seed = _json_object(seed_response.body, "OpenAlex")
        seed_id = str(seed.get("id") or "").rsplit("/", 1)[-1]
        if not seed_id:
            raise LiteratureApiError(f"OpenAlex did not resolve DOI {normalized}")
        citing_url = f"{OPENALEX_BASE}/works?{urlencode({
            'filter': f'cites:{seed_id}',
            'per_page': min(max(citing_limit, 1), 100),
            'select': 'id,doi,title,publication_year,cited_by_count',
        })}"
        citing_response = self.transport.get(citing_url, headers=headers)
        citing_payload = _json_object(citing_response.body, "OpenAlex")
        return {
            "seed": _openalex_network_node(seed),
            "references": [str(value).rsplit("/", 1)[-1] for value in seed.get("referenced_works", [])],
            "citing_works": [
                _openalex_network_node(item)
                for item in citing_payload.get("results", [])
                if isinstance(item, dict)
            ],
            "requests": [redact_url(seed_response.url), redact_url(citing_response.url)],
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        }


class ArxivClient:
    def __init__(self, transport: HttpTransport | None = None) -> None:
        self.transport = transport or HttpTransport(minimum_interval_seconds=3.1)

    def search(self, query: str, *, year_from: int, year_to: int, limit: int) -> SearchBatch:
        if query.startswith("raw:"):
            topic_query = query.removeprefix("raw:").strip()
        else:
            cleaned = re.sub(r"\s+", " ", query.replace('"', " ")).strip()
            topic_query = f'all:"{cleaned}"'
        search_query = f"{topic_query} AND submittedDate:[{year_from}01010000 TO {year_to}12312359]"
        params = {
            "search_query": search_query,
            "start": 0,
            "max_results": min(max(limit, 1), 100),
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
        request_url = f"{ARXIV_BASE}?{urlencode(params)}"
        response = self.transport.get(request_url, headers={"Accept": "application/atom+xml"})
        records = _parse_arxiv(response.body)
        return _batch("arxiv", query, response, records, "xml")

    def get_by_id(self, arxiv_id: str) -> SearchBatch:
        normalized = re.sub(r"v\d+$", "", arxiv_id.strip())
        if not re.fullmatch(r"(?:[a-z-]+(?:\.[A-Z]{2})?/\d{7}|\d{4}\.\d{4,5})", normalized, re.IGNORECASE):
            raise ValueError("invalid arXiv identifier")
        request_url = f"{ARXIV_BASE}?{urlencode({'id_list': normalized, 'max_results': 1})}"
        response = self.transport.get(request_url, headers={"Accept": "application/atom+xml"})
        records = _parse_arxiv(response.body)
        if len(records) != 1:
            raise LiteratureApiError(f"arXiv ID {normalized} resolved to {len(records)} records")
        return _batch("arxiv", normalized, response, records, "xml")


def merge_records(records: Iterable[PaperRecord]) -> list[dict[str, object]]:
    """Cross-source merge without assuming that titles alone prove identity."""

    groups: dict[str, list[PaperRecord]] = {}
    for record in records:
        key = canonical_paper_key(record)
        groups.setdefault(key, []).append(record)
    merged = []
    for key, versions in sorted(groups.items()):
        ordered = sorted(versions, key=lambda item: (item.source, item.source_id))
        primary = max(
            ordered,
            key=lambda item: (
                bool(item.doi),
                bool(item.abstract),
                bool(item.pdf_url),
                item.citation_count or 0,
            ),
        )
        merged.append({
            **primary.as_json(),
            "canonical_key": key,
            "sources": sorted({item.source for item in ordered}),
            "source_ids": {item.source: item.source_id for item in ordered},
            "doi_candidates": sorted({item.doi for item in ordered if item.doi}),
            "arxiv_id_candidates": sorted({item.arxiv_id for item in ordered if item.arxiv_id}),
            "pdf_candidates": sorted({item.pdf_url for item in ordered if item.pdf_url}),
        })
    return merged


def canonical_paper_key(record: PaperRecord) -> str:
    if record.doi:
        return f"doi:{record.doi}"
    if record.arxiv_id:
        return f"arxiv:{record.arxiv_id.lower()}"
    normalized_title = re.sub(r"[^a-z0-9]+", " ", record.title.lower()).strip()
    return f"title:{normalized_title}"


def normalize_doi(value: object) -> str | None:
    if not value:
        return None
    doi = str(value).strip().lower()
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi)
    doi = re.sub(r"^doi:\s*", "", doi)
    return doi.rstrip(" .") or None


def redact_url(url: str) -> str:
    return re.sub(r"([?&]api_key=)[^&]+", r"\1REDACTED", url, flags=re.IGNORECASE)


def _semantic_scholar_record(item: dict[str, object]) -> PaperRecord:
    external_ids = item.get("externalIds") or {}
    open_pdf = item.get("openAccessPdf") or {}
    authors = item.get("authors") or []
    return PaperRecord(
        source="semantic_scholar",
        source_id=str(item.get("paperId") or ""),
        title=_clean_text(item.get("title")) or "Untitled",
        year=_int_or_none(item.get("year")),
        publication_date=_string_or_none(item.get("publicationDate")),
        authors=tuple(
            name for name in (_clean_text(author.get("name")) for author in authors) if name
        ),
        abstract=_clean_text(item.get("abstract")),
        doi=normalize_doi(external_ids.get("DOI")),
        arxiv_id=_string_or_none(external_ids.get("ArXiv")),
        venue=_clean_text(item.get("venue")),
        citation_count=_int_or_none(item.get("citationCount")),
        landing_url=_string_or_none(item.get("url")),
        pdf_url=_string_or_none(open_pdf.get("url")),
        open_access_status=_string_or_none(open_pdf.get("status")),
        license=_string_or_none(open_pdf.get("license")),
    )


def _openalex_record(item: dict[str, object]) -> PaperRecord:
    authorships = item.get("authorships") or []
    primary = item.get("primary_location") or {}
    best_oa = item.get("best_oa_location") or {}
    location = best_oa or primary
    source = primary.get("source") or {}
    open_access = item.get("open_access") or {}
    return PaperRecord(
        source="openalex",
        source_id=str(item.get("id") or "").rsplit("/", 1)[-1],
        title=_clean_text(item.get("title")) or "Untitled",
        year=_int_or_none(item.get("publication_year")),
        publication_date=_string_or_none(item.get("publication_date")),
        authors=tuple(
            name
            for name in (
                _clean_text((authorship.get("author") or {}).get("display_name"))
                for authorship in authorships
            )
            if name
        ),
        abstract=_reconstruct_abstract(item.get("abstract_inverted_index")),
        doi=normalize_doi(item.get("doi")),
        arxiv_id=_arxiv_id_from_url(_string_or_none(location.get("landing_page_url"))),
        venue=_clean_text(source.get("display_name")),
        citation_count=_int_or_none(item.get("cited_by_count")),
        landing_url=_string_or_none(location.get("landing_page_url")) or _string_or_none(item.get("id")),
        pdf_url=_string_or_none(location.get("pdf_url")),
        open_access_status=_string_or_none(open_access.get("oa_status")),
        license=_string_or_none(location.get("license")),
    )


def _openalex_network_node(item: dict[str, object]) -> dict[str, object]:
    return {
        "openalex_id": str(item.get("id") or "").rsplit("/", 1)[-1],
        "doi": normalize_doi(item.get("doi")),
        "title": _clean_text(item.get("title")),
        "year": _int_or_none(item.get("publication_year")),
        "citation_count": _int_or_none(item.get("cited_by_count")),
    }


def _parse_arxiv(body: bytes) -> tuple[PaperRecord, ...]:
    try:
        root = ET.fromstring(body)
    except ET.ParseError as error:
        raise LiteratureApiError(f"arXiv returned invalid Atom XML: {error}") from error
    atom = "{http://www.w3.org/2005/Atom}"
    arxiv = "{http://arxiv.org/schemas/atom}"
    records = []
    for entry in root.findall(f"{atom}entry"):
        entry_id = _element_text(entry.find(f"{atom}id")) or ""
        arxiv_id = entry_id.rstrip("/").rsplit("/", 1)[-1]
        arxiv_id = re.sub(r"v\d+$", "", arxiv_id)
        links = {link.attrib.get("title") or link.attrib.get("rel"): link.attrib.get("href") for link in entry.findall(f"{atom}link")}
        published = _element_text(entry.find(f"{atom}published"))
        doi = _element_text(entry.find(f"{arxiv}doi"))
        journal_ref = _element_text(entry.find(f"{arxiv}journal_ref"))
        authors = tuple(
            name
            for name in (
                _element_text(author.find(f"{atom}name"))
                for author in entry.findall(f"{atom}author")
            )
            if name
        )
        records.append(PaperRecord(
            source="arxiv",
            source_id=arxiv_id,
            title=_clean_text(_element_text(entry.find(f"{atom}title"))) or "Untitled",
            year=int(published[:4]) if published and published[:4].isdigit() else None,
            publication_date=published[:10] if published else None,
            authors=authors,
            abstract=_clean_text(_element_text(entry.find(f"{atom}summary"))),
            doi=normalize_doi(doi),
            arxiv_id=arxiv_id,
            venue=journal_ref,
            citation_count=None,
            landing_url=entry_id or links.get("alternate"),
            pdf_url=links.get("pdf") or f"https://arxiv.org/pdf/{arxiv_id}",
            open_access_status="arxiv",
            license=None,
        ))
    return tuple(records)


def _batch(
    source: str,
    query: str,
    response: HttpResponse,
    records: tuple[PaperRecord, ...],
    extension: str,
) -> SearchBatch:
    return SearchBatch(
        source=source,
        query=query,
        request_url=redact_url(response.url),
        retrieved_at_utc=datetime.now(timezone.utc).isoformat(),
        records=records,
        raw_body=response.body,
        raw_extension=extension,
    )


def _json_object(body: bytes, source: str) -> dict[str, object]:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise LiteratureApiError(f"{source} returned invalid JSON: {error}") from error
    if not isinstance(payload, dict):
        raise LiteratureApiError(f"{source} returned a non-object JSON payload")
    return payload


def _reconstruct_abstract(index: object) -> str | None:
    if not isinstance(index, dict) or not index:
        return None
    positions: dict[int, str] = {}
    for word, indexes in index.items():
        if not isinstance(indexes, list):
            continue
        for position in indexes:
            if isinstance(position, int):
                positions[position] = str(word)
    return " ".join(positions[position] for position in sorted(positions)) or None


def _arxiv_id_from_url(url: str | None) -> str | None:
    if not url or "arxiv.org/" not in url:
        return None
    match = re.search(r"arxiv\.org/(?:abs|pdf)/([^?#/]+)", url)
    return re.sub(r"v\d+$", "", match.group(1)) if match else None


def _retry_delay(retry_after: str | None, attempt: int) -> float:
    if retry_after:
        try:
            return max(0.0, float(retry_after))
        except ValueError:
            try:
                parsed = parsedate_to_datetime(retry_after)
                return max(0.0, (parsed - datetime.now(parsed.tzinfo)).total_seconds())
            except (TypeError, ValueError):
                pass
    return float(2 ** attempt)


def _user_agent() -> str:
    contact = os.getenv("MYHR_RESEARCH_CONTACT", "").strip()
    suffix = f"; contact={contact}" if contact else ""
    return f"MyHR-TDK-Literature/1.0 (noncommercial academic research{suffix})"


def _clean_text(value: object) -> str | None:
    if value is None:
        return None
    cleaned = re.sub(r"\s+", " ", str(value)).strip()
    return cleaned or None


def _string_or_none(value: object) -> str | None:
    return str(value).strip() if value is not None and str(value).strip() else None


def _int_or_none(value: object) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _element_text(element: ET.Element | None) -> str | None:
    return element.text.strip() if element is not None and element.text else None
