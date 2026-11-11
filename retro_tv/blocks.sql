CREATE TABLE IF NOT EXISTS stream_source (
 source_id TEXT PRIMARY KEY REFERENCES source(id),url TEXT NOT NULL,
 enabled INTEGER NOT NULL CHECK(enabled IN (0,1)),availability TEXT NOT NULL DEFAULT 'unknown'
 CHECK(availability IN ('unknown','online','offline')),checked_at TEXT
);
CREATE TABLE IF NOT EXISTS complete_block (
 id TEXT PRIMARY KEY,service_id TEXT NOT NULL REFERENCES service(id),source_id TEXT NOT NULL REFERENCES source(id),
 title TEXT NOT NULL,start_ms INTEGER NOT NULL,end_ms INTEGER NOT NULL CHECK(end_ms>start_ms),
 source_in_ms INTEGER NOT NULL CHECK(source_in_ms>=0),source_out_ms INTEGER NOT NULL CHECK(source_out_ms>source_in_ms),
 known_points TEXT NOT NULL,created_at TEXT NOT NULL,
 CHECK(end_ms-start_ms=source_out_ms-source_in_ms)
);
CREATE TRIGGER IF NOT EXISTS complete_block_no_overlap BEFORE INSERT ON complete_block
 WHEN EXISTS(SELECT 1 FROM complete_block WHERE service_id=NEW.service_id AND start_ms<NEW.end_ms AND end_ms>NEW.start_ms)
 BEGIN SELECT RAISE(ABORT,'complete blocks overlap'); END;
CREATE TRIGGER IF NOT EXISTS complete_block_anchor_fixed BEFORE UPDATE ON complete_block
 BEGIN SELECT RAISE(ABORT,'complete block anchors are fixed'); END;
CREATE TRIGGER IF NOT EXISTS complete_block_no_delete BEFORE DELETE ON complete_block
 BEGIN SELECT RAISE(ABORT,'complete block anchors are fixed'); END;
CREATE TABLE IF NOT EXISTS block_presentation (
 source_id TEXT PRIMARY KEY REFERENCES source(id),path TEXT NOT NULL,sha256 TEXT NOT NULL,
 duration_ms INTEGER NOT NULL,approved_at TEXT NOT NULL
);
