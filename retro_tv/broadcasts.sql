CREATE TABLE IF NOT EXISTS broadcast_layout (
 id TEXT PRIMARY KEY,name TEXT NOT NULL,region TEXT NOT NULL,timezone TEXT NOT NULL,
 reception TEXT NOT NULL CHECK(reception IN ('antenna','cable')),provider_id TEXT NOT NULL REFERENCES provider(id),
 tier TEXT NOT NULL,created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS broadcast_layout_entry (
 layout_id TEXT NOT NULL REFERENCES broadcast_layout(id),service_id TEXT NOT NULL REFERENCES service(id),
 channel TEXT NOT NULL,valid_from TEXT NOT NULL,valid_until TEXT NOT NULL,
 PRIMARY KEY(layout_id,channel,valid_from),CHECK(valid_until>valid_from)
);
CREATE TABLE IF NOT EXISTS broadcast_settings (
 id INTEGER PRIMARY KEY CHECK(id=1),active_layout TEXT REFERENCES broadcast_layout(id)
);
