-- Editable drafts are separate from append-only broadcasts.
CREATE TABLE IF NOT EXISTS party_playlist (
 id TEXT PRIMARY KEY, document TEXT NOT NULL, revision INTEGER NOT NULL,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
