from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _plain_text(value: str) -> str:
    parser = _TextExtractor()
    parser.feed(value or "")
    parser.close()
    return normalize_whitespace(" ".join(parser.parts))


def _iso_date(item: dict, *keys: str) -> str:
    for key in keys:
        value = item.get(key) or {}
        if value.get("date-time"):
            return value["date-time"].replace("Z", "+00:00")
        parts = (value.get("date-parts") or [[]])[0]
        if parts:
            year, month, day = (*parts, 1, 1)[:3]
            return date(int(year), int(month), int(day)).isoformat()
    return ""


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse and normalize a Crossref response into the pipeline schema."""
    records: list[PaperRecord] = []
    for item in payload.get("message", {}).get("items", []):
        doi = unquote(str(item.get("DOI", ""))).strip().lower()
        for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
            if doi.startswith(prefix):
                doi = doi[len(prefix) :]
        title = normalize_whitespace(" ".join(item.get("title") or []))
        summary = _plain_text(str(item.get("abstract", "")))
        if not doi or not title:
            continue
        authors = [
            normalize_whitespace(author.get("name") or f"{author.get('given', '')} {author.get('family', '')}")
            for author in item.get("author", [])
        ]
        authors = [author for author in authors if author]
        categories = [normalize_whitespace(str(value)) for value in item.get("subject", [])]
        categories = [value for value in categories if value]
        published = _iso_date(item, "published", "published-online", "published-print", "created")
        updated = _iso_date(item, "indexed", "updated", "created") or published
        abs_url = str(item.get("URL") or f"https://doi.org/{doi}")
        pdf_url = next(
            (str(link.get("URL")) for link in item.get("link", []) if link.get("content-type") == "application/pdf" and link.get("URL")),
            abs_url,
        )
        records.append(
            PaperRecord(doi, title, summary, authors, categories, categories[0] if categories else "", published, updated, abs_url, pdf_url, f"Crossref record {doi}")
        )
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch Crossref records, falling back to the bundled offline snapshot."""
    session = requests.Session()
    session.mount(
        "https://",
        HTTPAdapter(
            max_retries=Retry(
                total=2,
                backoff_factor=0.5,
                status_forcelist=(429, 503),
                respect_retry_after_header=False,
            )
        ),
    )
    try:
        response = session.get(
            "https://api.crossref.org/works",
            params={
                "query.bibliographic": settings.source_query,
                "filter": settings.source_filter,
                "rows": settings.max_results,
            },
            headers={"User-Agent": "day10-data-observability-lab/0.1"},
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        records = parse_crossref_payload(payload)
        if len({record.paper_id for record in records}) < settings.max_results:
            raise ValueError("Crossref returned fewer usable unique records than requested.")
        write_json(settings.paths.raw_api_response, payload)
    except (requests.RequestException, ValueError):
        records = parse_crossref_payload(read_json(settings.paths.raw_api_response))
    finally:
        session.close()

    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load normalized records from a JSON snapshot."""
    return [PaperRecord(**item) for item in read_json(path)]
