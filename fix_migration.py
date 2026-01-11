#!/usr/bin/env python3
"""
Fix migration issue by creating the oracle_symbolperformance table directly
and recording the migration in django_migrations table.
"""
import sqlite3
import sys
from datetime import datetime


def create_table(conn):
    """Create the oracle_symbolperformance table"""
    cursor = conn.cursor()

    # Check if table already exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='oracle_symbolperformance';")
    if cursor.fetchone():
        print("✓ Table 'oracle_symbolperformance' already exists")
        return True

    print("Creating oracle_symbolperformance table...")

    # Create table
    cursor.execute("""
        CREATE TABLE "oracle_symbolperformance" (
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
    """)

    # Create indexes
    cursor.execute('CREATE INDEX "oracle_symbolperformance_timestamp_idx" ON "oracle_symbolperformance" ("timestamp");')
    cursor.execute('CREATE INDEX "oracle_symbolperformance_symbol_timestamp_idx" ON "oracle_symbolperformance" ("symbol_id", "timestamp" DESC);')
    cursor.execute('CREATE INDEX "oracle_symbolperformance_symbol_market_timestamp_idx" ON "oracle_symbolperformance" ("symbol_id", "market_type_id", "timestamp" DESC);')
    cursor.execute('CREATE INDEX "oracle_symbolperformance_market_type_id_idx" ON "oracle_symbolperformance" ("market_type_id");')
    cursor.execute('CREATE INDEX "oracle_symbolperformance_symbol_id_idx" ON "oracle_symbolperformance" ("symbol_id");')

    conn.commit()
    print("✓ Table created successfully")
    return True


def record_migration(conn):
    """Record the migration in django_migrations table"""
    cursor = conn.cursor()

    # Check if migration is already recorded
    cursor.execute("SELECT id FROM django_migrations WHERE app='oracle' AND name='0002_symbolperformance';")
    if cursor.fetchone():
        print("✓ Migration '0002_symbolperformance' already recorded")
        return True

    print("Recording migration in django_migrations...")

    # Insert migration record
    cursor.execute("""
        INSERT INTO django_migrations (app, name, applied)
        VALUES ('oracle', '0002_symbolperformance', ?);
    """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'),))

    conn.commit()
    print("✓ Migration recorded successfully")
    return True


def main():
    try:
        print("=" * 60)
        print("Trading Oracle - Fix SymbolPerformance Migration")
        print("=" * 60)
        print()

        # Connect to database
        conn = sqlite3.connect('db.sqlite3')

        # Create table
        if not create_table(conn):
            print("✗ Failed to create table")
            return 1

        # Record migration
        if not record_migration(conn):
            print("✗ Failed to record migration")
            return 1

        # Verify
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='oracle_symbolperformance';")
        if cursor.fetchone():
            print()
            print("=" * 60)
            print("✓ Success! oracle_symbolperformance table is ready")
            print("=" * 60)
            print()
            print("You can now run:")
            print("  python manage.py calculate_roi")
            print()
        else:
            print("✗ Verification failed - table not found")
            return 1

        conn.close()
        return 0

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
