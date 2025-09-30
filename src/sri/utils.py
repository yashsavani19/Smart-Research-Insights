import datetime as dt
from urllib.parse import urlencode
import requests

def reconstruct_openalex_abstract(inv_idx: dict) -> str:
    """Rebuild plain-text abstract from OpenAlex's inverted index, if needed."""
    pairs = [(pos, token) for token, positions in inv_idx.items() for pos in positions]
    pairs.sort(key=lambda x: x[0])
    return " ".join(tok for _, tok in pairs)

def normalize_work(w: dict) -> dict:
    """Flatten an OpenAlex work into our schema row."""
    abstract = w.get("abstract") or ""
    if not abstract and w.get("abstract_inverted_index"):
        abstract = reconstruct_openalex_abstract(w["abstract_inverted_index"])

    url = (w.get("primary_location") or {}).get("landing_page_url") or w.get("id")
    pub_date = (w.get("publication_date") or "")[:10] or None

    return {
        "doi": w.get("doi"),
        "openalex_id": w.get("id"),  # e.g. 'https://openalex.org/W123...'
        "url": url,
        "source": "openalex",
        "title": w.get("title") or "",
        "abstract": abstract or "",
        "published_date": pub_date,
    }


def daterange_2019_to_today():
    return dt.date.fromisoformat("2019-01-01"), dt.date.today()

def openalex_params(query: str, since: dt.date, until: dt.date, country_filter: str, per_page=200, cursor="*"):
    filters = [
        f"from_publication_date:{since}",
        f"to_publication_date:{until}",
        "has_abstract:true",
    ]
    if country_filter:
        filters.append(f"institutions.country_code:{country_filter}")
    return {
        "search": query,
        "filter": ",".join(filters),
        "per_page": per_page,
        "cursor": cursor
    }

def openalex_get(url: str, timeout=45):
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return r.json()