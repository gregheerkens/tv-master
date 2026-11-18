CREATE TABLE IF NOT EXISTS reference_packet (
 id TEXT PRIMARY KEY, sha256 TEXT NOT NULL, document TEXT NOT NULL, imported_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS packet_airing (
 airing_id TEXT PRIMARY KEY REFERENCES historical_airing(id) ON DELETE CASCADE,
 packet_id TEXT NOT NULL REFERENCES reference_packet(id)
);
CREATE INDEX IF NOT EXISTS packet_airing_range ON packet_airing(packet_id,airing_id);
