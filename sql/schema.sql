CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS papers (
  id              BIGSERIAL PRIMARY KEY,
  doi             TEXT UNIQUE,            
  openalex_id     TEXT UNIQUE,            
  url             TEXT UNIQUE,            
  source          TEXT NOT NULL DEFAULT 'openalex',
  title           TEXT NOT NULL,
  abstract        TEXT,
  published_date  DATE,

  created_at      TIMESTAMPTZ DEFAULT now(),
  updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_papers_pub_date ON papers (published_date);
CREATE INDEX IF NOT EXISTS idx_papers_title_trgm ON papers USING gin (title gin_trgm_ops);

-- Track incremental runs
CREATE TABLE IF NOT EXISTS ingestion_state (
  source       TEXT PRIMARY KEY,
  last_run_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  since_date   DATE,
  until_date   DATE,
  next_cursor  TEXT
);
