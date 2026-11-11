CREATE TABLE IF NOT EXISTS health_standard (
 id TEXT PRIMARY KEY, name TEXT NOT NULL,
 mode TEXT NOT NULL CHECK(mode IN ('historical','theme','channel')),
 settings TEXT NOT NULL
);
INSERT OR IGNORE INTO health_standard VALUES
 ('channel','Broadcast operation','channel','{"min_playable_percent":95,"min_history_percent":0,"min_exact_percent":0,"min_unique_hours":0,"max_inventory_passes":1000,"ad_minutes_per_day":0,"min_healthy_channels":1,"allow_substitutions":true}'),
 ('historical','Historical recreation','historical','{"min_playable_percent":95,"min_history_percent":100,"min_exact_percent":100,"min_unique_hours":0,"max_inventory_passes":1000,"ad_minutes_per_day":0,"min_healthy_channels":1,"allow_substitutions":false}'),
 ('theme','Theme blocks','theme','{"min_playable_percent":95,"min_history_percent":0,"min_exact_percent":0,"min_unique_hours":2,"max_inventory_passes":12,"ad_minutes_per_day":10,"min_healthy_channels":1,"allow_substitutions":true}');
