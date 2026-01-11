-- Create oracle_symbolperformance table
-- Run this if migrations don't work: python3 -c "import sqlite3; conn=sqlite3.connect('db.sqlite3'); conn.executescript(open('create_symbolperformance_table.sql').read()); conn.commit()"

CREATE TABLE IF NOT EXISTS "oracle_symbolperformance" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "current_price" decimal NOT NULL,
    "roi_1h" decimal NULL,
    "roi_1d" decimal NULL,
    "roi_1w" decimal NULL,
    "roi_1m" decimal NULL,
    "roi_1y" decimal NULL,
    "volume_24h" decimal NULL,
    "volume_change_24h" decimal NULL,
    "volatility_24h" decimal NULL,
    "high_24h" decimal NULL,
    "low_24h" decimal NULL,
    "market_cap" decimal NULL,
    "market_cap_rank" integer NULL,
    "trades_24h" integer NULL,
    "timestamp" datetime NOT NULL,
    "market_type_id" bigint NOT NULL REFERENCES "oracle_markettype" ("id") DEFERRABLE INITIALLY DEFERRED,
    "symbol_id" bigint NOT NULL REFERENCES "oracle_symbol" ("id") DEFERRABLE INITIALLY DEFERRED
);

CREATE INDEX IF NOT EXISTS "oracle_symbolperformance_timestamp_idx" ON "oracle_symbolperformance" ("timestamp");
CREATE INDEX IF NOT EXISTS "oracle_symbolperformance_symbol_timestamp_idx" ON "oracle_symbolperformance" ("symbol_id", "timestamp" DESC);
CREATE INDEX IF NOT EXISTS "oracle_symbolperformance_symbol_market_timestamp_idx" ON "oracle_symbolperformance" ("symbol_id", "market_type_id", "timestamp" DESC);
CREATE INDEX IF NOT EXISTS "oracle_symbolperformance_market_type_id_idx" ON "oracle_symbolperformance" ("market_type_id");
CREATE INDEX IF NOT EXISTS "oracle_symbolperformance_symbol_id_idx" ON "oracle_symbolperformance" ("symbol_id");
