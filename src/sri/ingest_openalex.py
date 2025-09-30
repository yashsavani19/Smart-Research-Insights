# src/sri/openalex.py
import time
import datetime as dt
from typing import Iterator, Dict, List
from urllib.parse import urlencode

from .utils import openalex_get, openalex_params, normalize_work

BASE = "https://api.openalex.org/works"


def iterate_works(
    query: str,
    since: dt.date,
    until: dt.date,
    country_filter: str,
    pause: float = 0.25,
    per_page: int = 200,
) -> Iterator[Dict]:
    """
    Stream normalized OpenAlex 'works' for the given window.
    Yields rows shaped for our schema (see normalize_work).
    """
    params = openalex_params(query, since, until, country_filter, per_page=per_page, cursor="*")
    while True:
        url = f"{BASE}?{urlencode(params)}"
        data = openalex_get(url)
        results = data.get("results", [])
        for w in results:
            yield normalize_work(w)

        next_cursor = (data.get("meta") or {}).get("next_cursor")
        if not next_cursor:
            break
        params["cursor"] = next_cursor
        time.sleep(pause)


def insert_batch(conn, rows: List[Dict]) -> None:
    """
    Upsert a batch of rows into 'papers' using three keys (in order):
      1) doi (if present)
      2) openalex_id (if no doi)
      3) url (last fallback)
    Matches Option A schema:
      papers(doi, openalex_id, url, source, title, abstract, published_date)
    """
    from psycopg2.extras import execute_batch

    with conn, conn.cursor() as cur:
        # 1) Upsert by DOI
        rows_doi = [r for r in rows if r.get("doi")]
        if rows_doi:
            sql_doi = """
            INSERT INTO papers (doi, openalex_id, url, source, title, abstract, published_date)
            VALUES (%(doi)s, %(openalex_id)s, %(url)s, %(source)s, %(title)s, %(abstract)s, %(published_date)s)
            ON CONFLICT (doi) DO UPDATE
              SET title          = EXCLUDED.title,
                  abstract       = COALESCE(NULLIF(EXCLUDED.abstract,''), papers.abstract),
                  openalex_id    = COALESCE(papers.openalex_id, EXCLUDED.openalex_id),
                  url            = COALESCE(papers.url, EXCLUDED.url),
                  published_date = COALESCE(EXCLUDED.published_date, papers.published_date),
                  updated_at     = now();
            """
            execute_batch(cur, sql_doi, rows_doi, page_size=500)

        # 2) Upsert by OpenAlex ID (only when DOI is missing)
        rows_oa = [r for r in rows if (not r.get("doi")) and r.get("openalex_id")]
        if rows_oa:
            sql_oa = """
            INSERT INTO papers (doi, openalex_id, url, source, title, abstract, published_date)
            VALUES (%(doi)s, %(openalex_id)s, %(url)s, %(source)s, %(title)s, %(abstract)s, %(published_date)s)
            ON CONFLICT (openalex_id) DO UPDATE
              SET title          = EXCLUDED.title,
                  abstract       = COALESCE(NULLIF(EXCLUDED.abstract,''), papers.abstract),
                  url            = COALESCE(papers.url, EXCLUDED.url),
                  published_date = COALESCE(EXCLUDED.published_date, papers.published_date),
                  updated_at     = now();
            """
            execute_batch(cur, sql_oa, rows_oa, page_size=500)

        # 3) Upsert by URL (last fallback when neither DOI nor OpenAlex ID)
        rows_url = [r for r in rows if (not r.get("doi")) and (not r.get("openalex_id")) and r.get("url")]
        if rows_url:
            sql_url = """
            INSERT INTO papers (doi, openalex_id, url, source, title, abstract, published_date)
            VALUES (%(doi)s, %(openalex_id)s, %(url)s, %(source)s, %(title)s, %(abstract)s, %(published_date)s)
            ON CONFLICT (url) DO UPDATE
              SET title          = EXCLUDED.title,
                  abstract       = COALESCE(NULLIF(EXCLUDED.abstract,''), papers.abstract),
                  published_date = COALESCE(EXCLUDED.published_date, papers.published_date),
                  updated_at     = now();
            """
            execute_batch(cur, sql_url, rows_url, page_size=500)
