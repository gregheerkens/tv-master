CREATE TABLE IF NOT EXISTS source_ingest (
 source_id TEXT PRIMARY KEY REFERENCES source(id),
 kind TEXT NOT NULL CHECK(kind IN ('ripped','recorded','generated','legacy_unknown')),
 context TEXT NOT NULL
);
