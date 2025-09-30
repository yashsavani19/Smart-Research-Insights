from utils import normalize_work


def insert_batch(conn, rows):
    from psycopg2.extras import execute_batch

    with conn, conn.cursor() as cur:
        # 1) DOI upsert
        rows_doi = [r for r in rows if r.get("doi")]
        if rows_doi:
            sql_doi = """
            INSERT INTO papers (doi, openalex_id, url, source, title, abstract, published_date)
            VALUES (%(doi)s, %(openalex_id)s, %(url)s, %(source)s, %(title)s, %(abstract)s, %(published_date)s)
            ON CONFLICT (doi) DO UPDATE
              SET title = EXCLUDED.title,
                  abstract = COALESCE(NULLIF(EXCLUDED.abstract,''), papers.abstract),
                  openalex_id = COALESCE(papers.openalex_id, EXCLUDED.openalex_id),
                  url = COALESCE(papers.url, EXCLUDED.url),
                  published_date = COALESCE(EXCLUDED.published_date, papers.published_date),
                  updated_at = now();
            """
            execute_batch(cur, sql_doi, rows_doi, page_size=500)

        # 2) OpenAlex ID upsert
        rows_oa = [r for r in rows if (not r.get("doi")) and r.get("openalex_id")]
        if rows_oa:
            sql_oa = """
            INSERT INTO papers (doi, openalex_id, url, source, title, abstract, published_date)
            VALUES (%(doi)s, %(openalex_id)s, %(url)s, %(source)s, %(title)s, %(abstract)s, %(published_date)s)
            ON CONFLICT (openalex_id) DO UPDATE
              SET title = EXCLUDED.title,
                  abstract = COALESCE(NULLIF(EXCLUDED.abstract,''), papers.abstract),
                  url = COALESCE(papers.url, EXCLUDED.url),
                  published_date = COALESCE(EXCLUDED.published_date, papers.published_date),
                  updated_at = now();
            """
            execute_batch(cur, sql_oa, rows_oa, page_size=500)

        # 3) URL upsert
        rows_url = [r for r in rows if (not r.get("doi")) and (not r.get("openalex_id")) and r.get("url")]
        if rows_url:
            sql_url = """
            INSERT INTO papers (doi, openalex_id, url, source, title, abstract, published_date)
            VALUES (%(doi)s, %(openalex_id)s, %(url)s, %(source)s, %(title)s, %(abstract)s, %(published_date)s)
            ON CONFLICT (url) DO UPDATE
              SET title = EXCLUDED.title,
                  abstract = COALESCE(NULLIF(EXCLUDED.abstract,''), papers.abstract),
                  published_date = COALESCE(EXCLUDED.published_date, papers.published_date),
                  updated_at = now();
            """
            execute_batch(cur, sql_url, rows_url, page_size=500)
