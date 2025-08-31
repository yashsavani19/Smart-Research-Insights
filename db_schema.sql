-- Database schema for BERTopic CORE Online MVP

-- Documents table to store research papers
CREATE TABLE IF NOT EXISTS documents (
    id BIGSERIAL PRIMARY KEY,
    core_id TEXT UNIQUE,
    doi TEXT,
    title TEXT,
    abstract TEXT,
    full_text TEXT,
    authors TEXT,
    venue TEXT,
    year INTEGER,
    lang TEXT,
    url TEXT,
    pdf_url TEXT,
    raw_json JSONB,
    content_hash TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Topics table to store topic information
CREATE TABLE IF NOT EXISTS topics (
    topic_id INTEGER PRIMARY KEY,
    label TEXT,
    top_terms TEXT,
    size INTEGER,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Topic terms table to store individual terms and their weights
CREATE TABLE IF NOT EXISTS topic_terms (
    topic_id INTEGER,
    term TEXT,
    weight DOUBLE PRECISION,
    PRIMARY KEY(topic_id, term)
);

-- Topic assignments table to store document-topic assignments
CREATE TABLE IF NOT EXISTS topic_assignments (
    doc_id BIGINT REFERENCES documents(id),
    topic_id INTEGER,
    probability DOUBLE PRECISION,
    assigned_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY(doc_id, topic_id)
);

-- Topic trends table to store monthly topic trends
CREATE TABLE IF NOT EXISTS topic_trends (
    topic_id INTEGER,
    year INTEGER,
    month INTEGER,
    doc_count INTEGER,
    PRIMARY KEY(topic_id, year, month)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_documents_year ON documents(year);
CREATE INDEX IF NOT EXISTS idx_documents_lang ON documents(lang);
CREATE INDEX IF NOT EXISTS idx_topic_assignments_topic_id ON topic_assignments(topic_id);
CREATE INDEX IF NOT EXISTS idx_topic_assignments_doc_id ON topic_assignments(doc_id);
CREATE INDEX IF NOT EXISTS idx_topic_trends_topic_id ON topic_trends(topic_id);
CREATE INDEX IF NOT EXISTS idx_topic_trends_year_month ON topic_trends(year, month);
