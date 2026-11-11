CREATE TABLE IF NOT EXISTS historical_airing (
 id TEXT PRIMARY KEY, service_id TEXT NOT NULL REFERENCES service(id),
 content_id TEXT REFERENCES content(id), title TEXT NOT NULL,
 start_ms INTEGER NOT NULL, end_ms INTEGER NOT NULL CHECK(end_ms>start_ms),
 evidence_state TEXT NOT NULL CHECK(evidence_state IN ('exact','schedule_exact','seasonal','inferred')),
 provenance TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS historical_airing_time ON historical_airing(service_id,start_ms,end_ms);
CREATE TRIGGER IF NOT EXISTS historical_airing_no_overlap BEFORE INSERT ON historical_airing
 WHEN EXISTS(SELECT 1 FROM historical_airing WHERE service_id=NEW.service_id
 AND start_ms<NEW.end_ms AND end_ms>NEW.start_ms)
 BEGIN SELECT RAISE(ABORT,'overlapping historical airings'); END;
CREATE TABLE IF NOT EXISTS airing_requirement (
 id TEXT PRIMARY KEY, airing_id TEXT NOT NULL REFERENCES historical_airing(id),
 content_id TEXT REFERENCES content(id), kind TEXT NOT NULL CHECK(kind IN
 ('commercial','bumper','promo','station_id','psa')),
 duration_ms INTEGER NOT NULL CHECK(duration_ms>0), note TEXT NOT NULL,
 provenance TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS airing_override (
 airing_id TEXT PRIMARY KEY REFERENCES historical_airing(id),
 program_id TEXT NOT NULL REFERENCES program(id), note TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS broadcast_context (
 broadcast_id TEXT PRIMARY KEY REFERENCES broadcast(id),
 airing_id TEXT REFERENCES historical_airing(id), evidence_state TEXT NOT NULL,
 provenance TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS context_no_update BEFORE UPDATE ON broadcast_context
 BEGIN SELECT RAISE(ABORT,'published context is immutable'); END;
CREATE TRIGGER IF NOT EXISTS context_no_delete BEFORE DELETE ON broadcast_context
 BEGIN SELECT RAISE(ABORT,'published context is immutable'); END;
CREATE TABLE IF NOT EXISTS source_location (
 sha256 TEXT PRIMARY KEY, path TEXT NOT NULL, verified_at TEXT NOT NULL
);
