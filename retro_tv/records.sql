-- Additive catalog migration. Published playout tables are never rewritten.
CREATE TABLE IF NOT EXISTS content (
 id TEXT PRIMARY KEY, kind TEXT NOT NULL CHECK(kind IN
 ('program','series','episode','movie','commercial','bumper','promo','station_id','psa')),
 title TEXT NOT NULL, parent_id TEXT REFERENCES content(id), episode_title TEXT,
 season_number INTEGER CHECK(season_number>=0), episode_number INTEGER CHECK(episode_number>=0),
 original_air_date TEXT, date_evidence TEXT,
 episode_metadata TEXT, description TEXT, tags TEXT NOT NULL DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS asset_content (
 asset_id TEXT PRIMARY KEY REFERENCES asset(id), content_id TEXT NOT NULL REFERENCES content(id)
);
CREATE INDEX IF NOT EXISTS asset_content_identity ON asset_content(content_id);
CREATE TABLE IF NOT EXISTS program_content (
 program_id TEXT PRIMARY KEY REFERENCES program(id), content_id TEXT NOT NULL REFERENCES content(id)
);
CREATE TABLE IF NOT EXISTS network (
 id TEXT PRIMARY KEY, name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS channel_profile (
 service_id TEXT PRIMARY KEY REFERENCES service(id),
 mode TEXT NOT NULL CHECK(mode IN ('custom','themed','historical')),
 theme_tags TEXT NOT NULL DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS station_history (
 id TEXT PRIMARY KEY, service_id TEXT NOT NULL REFERENCES service(id),
 market_id TEXT NOT NULL REFERENCES market(id), call_sign TEXT NOT NULL,
 broadcast_channel TEXT NOT NULL, valid_from TEXT NOT NULL, valid_until TEXT NOT NULL,
 evidence_state TEXT NOT NULL CHECK(evidence_state IN ('verified','estimated','user_defined')),
 provenance TEXT NOT NULL, CHECK(valid_until>valid_from)
);
CREATE TABLE IF NOT EXISTS affiliation_history (
 id TEXT PRIMARY KEY, service_id TEXT NOT NULL REFERENCES service(id),
 network_id TEXT NOT NULL REFERENCES network(id), valid_from TEXT NOT NULL, valid_until TEXT NOT NULL,
 evidence_state TEXT NOT NULL CHECK(evidence_state IN ('verified','estimated','user_defined')),
 provenance TEXT NOT NULL, CHECK(valid_until>valid_from)
);
CREATE TABLE IF NOT EXISTS eligibility_window (
 id TEXT PRIMARY KEY, content_id TEXT NOT NULL REFERENCES content(id),
 valid_from TEXT NOT NULL, valid_until TEXT NOT NULL,
 service_id TEXT REFERENCES service(id), network_id TEXT REFERENCES network(id),
 market_id TEXT REFERENCES market(id), months TEXT NOT NULL DEFAULT '[]',
 evidence_state TEXT NOT NULL CHECK(evidence_state IN ('verified','estimated','user_defined')),
 provenance TEXT NOT NULL, CHECK(valid_until>valid_from)
);
CREATE INDEX IF NOT EXISTS eligibility_identity ON eligibility_window(content_id);
CREATE TABLE IF NOT EXISTS content_preference (
 content_id TEXT PRIMARY KEY REFERENCES content(id),
 never_schedule INTEGER NOT NULL DEFAULT 0 CHECK(never_schedule IN (0,1)),
 favorite INTEGER NOT NULL DEFAULT 0 CHECK(favorite IN (0,1)), note TEXT
);
CREATE TABLE IF NOT EXISTS recording_preference (
 asset_id TEXT PRIMARY KEY REFERENCES asset(id),
 excluded INTEGER NOT NULL DEFAULT 0 CHECK(excluded IN (0,1)), note TEXT
);
CREATE TABLE IF NOT EXISTS recording_quality (
 asset_id TEXT PRIMARY KEY REFERENCES asset(id),
 score INTEGER CHECK(score BETWEEN 0 AND 100), assessment TEXT,
 assessed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS quality_alert (
 id TEXT PRIMARY KEY, source_id TEXT REFERENCES source(id), asset_id TEXT REFERENCES asset(id),
 code TEXT NOT NULL, severity TEXT NOT NULL CHECK(severity IN ('info','warning','error')),
 details TEXT NOT NULL, created_at TEXT NOT NULL, resolved_at TEXT,
 CHECK((source_id IS NULL)!=(asset_id IS NULL))
);
CREATE TABLE IF NOT EXISTS viewing_event (
 id TEXT PRIMARY KEY, segment_id INTEGER NOT NULL REFERENCES segment(id),
 viewer_id TEXT NOT NULL, watched_ms INTEGER NOT NULL CHECK(watched_ms>0),
 recorded_at TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS station_history_no_overlap BEFORE INSERT ON station_history
 WHEN EXISTS(SELECT 1 FROM station_history WHERE service_id=NEW.service_id
 AND market_id=NEW.market_id AND valid_from<NEW.valid_until AND valid_until>NEW.valid_from)
 BEGIN SELECT RAISE(ABORT,'ambiguous station history'); END;
CREATE TRIGGER IF NOT EXISTS affiliation_no_overlap BEFORE INSERT ON affiliation_history
 WHEN EXISTS(SELECT 1 FROM affiliation_history WHERE service_id=NEW.service_id
 AND valid_from<NEW.valid_until AND valid_until>NEW.valid_from)
 BEGIN SELECT RAISE(ABORT,'ambiguous affiliation history'); END;
