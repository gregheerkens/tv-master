-- Editable drafts are separate from append-only broadcasts.
CREATE TABLE IF NOT EXISTS party_playlist (
 id TEXT PRIMARY KEY, document TEXT NOT NULL, revision INTEGER NOT NULL,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS party_pin (
 playlist_id TEXT PRIMARY KEY REFERENCES party_playlist(id) ON DELETE CASCADE,
 pinned INTEGER NOT NULL DEFAULT 0 CHECK(pinned IN (0,1))
);
