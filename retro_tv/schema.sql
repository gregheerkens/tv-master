PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS state (
 id INTEGER PRIMARY KEY CHECK(id=1), real_anchor_ms INTEGER NOT NULL,
 historical_anchor_ms INTEGER NOT NULL, high_water_ms INTEGER NOT NULL,
 timezone TEXT NOT NULL, seed TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS market (id TEXT PRIMARY KEY, name TEXT NOT NULL, timezone TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS provider (id TEXT PRIMARY KEY, market_id TEXT NOT NULL REFERENCES market(id), name TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS service (id TEXT PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS lineup (id TEXT PRIMARY KEY, provider_id TEXT NOT NULL REFERENCES provider(id), valid_from TEXT NOT NULL, valid_until TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS lineup_entry (
 lineup_id TEXT NOT NULL REFERENCES lineup(id), channel TEXT NOT NULL,
 service_id TEXT NOT NULL REFERENCES service(id), PRIMARY KEY(lineup_id,channel)
);
CREATE TABLE IF NOT EXISTS source (
 id TEXT PRIMARY KEY, path TEXT NOT NULL, duration_ms INTEGER NOT NULL CHECK(duration_ms>0),
 sha256 TEXT NOT NULL, provenance TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS asset (
 id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES source(id), title TEXT NOT NULL,
 kind TEXT NOT NULL CHECK(kind IN ('program','commercial','bumper','promo','station_id','psa')),
 in_ms INTEGER NOT NULL CHECK(in_ms>=0), out_ms INTEGER NOT NULL CHECK(out_ms>in_ms),
 valid_from TEXT NOT NULL, valid_until TEXT NOT NULL,
 services TEXT NOT NULL, metadata TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS program (
 id TEXT PRIMARY KEY, title TEXT NOT NULL, parts TEXT NOT NULL, services TEXT NOT NULL,
 valid_from TEXT NOT NULL, valid_until TEXT NOT NULL, metadata TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS broadcast (
 id TEXT PRIMARY KEY, service_id TEXT NOT NULL REFERENCES service(id),
 start_ms INTEGER NOT NULL, end_ms INTEGER NOT NULL CHECK(end_ms>start_ms),
 title TEXT NOT NULL, program_id TEXT, evidence TEXT NOT NULL,
 UNIQUE(service_id,start_ms)
);
CREATE TABLE IF NOT EXISTS segment (
 id INTEGER PRIMARY KEY, broadcast_id TEXT NOT NULL REFERENCES broadcast(id),
 start_ms INTEGER NOT NULL, end_ms INTEGER NOT NULL CHECK(end_ms>start_ms),
 asset_id TEXT, title TEXT NOT NULL, kind TEXT NOT NULL, path TEXT,
 source_in_ms INTEGER NOT NULL, source_hash TEXT, reason TEXT,
 UNIQUE(broadcast_id,start_ms)
);
CREATE INDEX IF NOT EXISTS broadcast_time ON broadcast(service_id,start_ms,end_ms);
CREATE INDEX IF NOT EXISTS segment_time ON segment(broadcast_id,start_ms,end_ms);
CREATE TRIGGER IF NOT EXISTS broadcast_no_update BEFORE UPDATE ON broadcast BEGIN SELECT RAISE(ABORT,'published broadcasts are immutable'); END;
CREATE TRIGGER IF NOT EXISTS broadcast_no_delete BEFORE DELETE ON broadcast BEGIN SELECT RAISE(ABORT,'published broadcasts are immutable'); END;
CREATE TRIGGER IF NOT EXISTS segment_no_update BEFORE UPDATE ON segment BEGIN SELECT RAISE(ABORT,'published segments are immutable'); END;
CREATE TRIGGER IF NOT EXISTS segment_no_delete BEFORE DELETE ON segment BEGIN SELECT RAISE(ABORT,'published segments are immutable'); END;
CREATE TRIGGER IF NOT EXISTS anchor_no_update BEFORE UPDATE OF real_anchor_ms,historical_anchor_ms,timezone,seed ON state BEGIN SELECT RAISE(ABORT,'simulation anchor is immutable'); END;
CREATE TRIGGER IF NOT EXISTS anchor_no_delete BEFORE DELETE ON state BEGIN SELECT RAISE(ABORT,'simulation cannot be reset'); END;
CREATE TRIGGER IF NOT EXISTS clock_no_rewind BEFORE UPDATE OF high_water_ms ON state WHEN NEW.high_water_ms<OLD.high_water_ms BEGIN SELECT RAISE(ABORT,'clock cannot rewind'); END;
CREATE TRIGGER IF NOT EXISTS broadcast_no_overlap BEFORE INSERT ON broadcast WHEN EXISTS (
 SELECT 1 FROM broadcast WHERE service_id=NEW.service_id AND start_ms<NEW.end_ms AND end_ms>NEW.start_ms
) BEGIN SELECT RAISE(ABORT,'broadcast overlap'); END;
