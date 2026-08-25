-- Committee of Fifteen v1 schema (Vercel Postgres / Neon)

CREATE TABLE IF NOT EXISTS cof_records (
  uuid            UUID PRIMARY KEY,
  title           TEXT NOT NULL,
  address_norm    TEXT,
  title_kind      TEXT,
  precinct        TEXT,
  precinct_num    SMALLINT,
  date_start      SMALLINT,
  date_end        SMALLINT,
  nypl_image_id   TEXT,
  nypl_item_url   TEXT,
  genres          TEXT[],
  host_chain      TEXT
);

CREATE TABLE IF NOT EXISTS cof_geocodes (
  address_norm    TEXT PRIMARY KEY,
  query           TEXT NOT NULL,
  lat             DOUBLE PRECISION,
  lng             DOUBLE PRECISION,
  geo_source      TEXT,
  confidence      REAL,
  status          TEXT NOT NULL DEFAULT 'pending',
  raw             JSONB,
  geocoded_at     TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cof_documents (
  uuid            UUID PRIMARY KEY REFERENCES cof_records(uuid) ON DELETE CASCADE,
  ocr_text        TEXT,
  char_count      INT,
  quality         TEXT
);

CREATE TABLE IF NOT EXISTS cof_terms (
  uuid            UUID REFERENCES cof_records(uuid) ON DELETE CASCADE,
  term            TEXT NOT NULL,
  category        TEXT NOT NULL,
  count           INT NOT NULL DEFAULT 1,
  PRIMARY KEY (uuid, term, category)
);

CREATE INDEX IF NOT EXISTS cof_records_precinct ON cof_records(precinct_num);
CREATE INDEX IF NOT EXISTS cof_records_address ON cof_records(address_norm);
CREATE INDEX IF NOT EXISTS cof_records_title_kind ON cof_records(title_kind);
CREATE INDEX IF NOT EXISTS cof_geocodes_status ON cof_geocodes(status);
CREATE INDEX IF NOT EXISTS cof_documents_fts ON cof_documents
  USING gin(to_tsvector('english', coalesce(ocr_text, '')));
