CREATE TABLE IF NOT EXISTS papers (
  id TEXT PRIMARY KEY,
  title TEXT,
  abstract TEXT,
  doi TEXT,
  published_date DATE,
  full_text_url TEXT,
  institutions JSONB,
  source TEXT DEFAULT 'CORE',
  ingested_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS runs (
  run_id BIGSERIAL PRIMARY KEY,
  started_at TIMESTAMPTZ DEFAULT NOW(),
  finished_at TIMESTAMPTZ,
  status TEXT CHECK (status IN ('running','success','error')),
  added_count INT,
  updated_count INT,
  skipped_count INT,
  failed_count INT,
  note TEXT
);

-- Indexes

-- IDE might show error for USING GIN, however it is necessary to run this for NEON DB
CREATE INDEX IF NOT EXISTS idx_papers_pubdate ON papers(published_date);
CREATE INDEX IF NOT EXISTS idx_papers_doi ON papers(doi);
CREATE INDEX IF NOT EXISTS idx_papers_institutions ON papers USING GIN (institutions);
