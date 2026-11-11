-- WHAT is a reusable selection. Published order and clock anchors stay immutable.
CREATE TABLE IF NOT EXISTS selection_rule (
 service_id TEXT PRIMARY KEY REFERENCES service(id), rules TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS viewing_mode (
 id INTEGER PRIMARY KEY CHECK(id=1), mode TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS channel_recipe (
 id TEXT PRIMARY KEY, name TEXT NOT NULL, service_id TEXT NOT NULL REFERENCES service(id),
 rules TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS viewing_context (
 id TEXT PRIMARY KEY, context_key TEXT UNIQUE NOT NULL, mode TEXT NOT NULL,
 name TEXT NOT NULL, request TEXT NOT NULL, path TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS viewing_context_no_update BEFORE UPDATE ON viewing_context
 BEGIN SELECT RAISE(ABORT,'viewing contexts cannot be reset'); END;
CREATE TRIGGER IF NOT EXISTS viewing_context_no_delete BEFORE DELETE ON viewing_context
 BEGIN SELECT RAISE(ABORT,'viewing contexts cannot be reset'); END;
