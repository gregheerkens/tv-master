-- Fetched research is staging, not canonical schedule evidence.
CREATE TABLE IF NOT EXISTS research_batch (
 id TEXT PRIMARY KEY, service_id TEXT NOT NULL REFERENCES service(id),
 start_date TEXT NOT NULL, until_date TEXT NOT NULL, timezone TEXT NOT NULL,
 adapter TEXT NOT NULL, url_template TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS research_page (
 id TEXT PRIMARY KEY, batch_id TEXT NOT NULL REFERENCES research_batch(id), day TEXT NOT NULL,
 url TEXT NOT NULL, fetched_at TEXT, sha256 TEXT, body TEXT,
 status TEXT NOT NULL CHECK(status IN ('pending','failed','staged','accepted')),
 error TEXT, candidates TEXT NOT NULL DEFAULT '[]', warnings TEXT NOT NULL DEFAULT '[]',
 accepted_at TEXT, UNIQUE(batch_id,day)
);
CREATE TABLE IF NOT EXISTS research_acceptance (
 page_id TEXT NOT NULL REFERENCES research_page(id), candidate_index INTEGER NOT NULL, airing_id TEXT NOT NULL REFERENCES historical_airing(id),
 PRIMARY KEY(page_id,airing_id)
);
CREATE TABLE IF NOT EXISTS content_alias (
 content_id TEXT NOT NULL REFERENCES content(id), title TEXT NOT NULL,
 episode_title TEXT NOT NULL DEFAULT '', PRIMARY KEY(content_id,title,episode_title)
);
CREATE TABLE IF NOT EXISTS research_boundary (
 page_id TEXT PRIMARY KEY REFERENCES research_page(id), tail TEXT NOT NULL,
 next_url TEXT, status TEXT NOT NULL, error TEXT, snapshot TEXT
);
