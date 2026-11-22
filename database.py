"""
database.py
-----------
All SQLite work lives in this file.

Database file : smart_parking.db   (created automatically in the project folder)

Tables
  parking_spaces : the CURRENT state of the 40 parking spaces
  parking_history: one row per space for EVERY recorded snapshot (time series)
  app_settings   : small key/value table (paused, activity level, interval ...)

Because everything is saved in the .db file, the data is still there after you
close and restart the application.

You can create the database by running:   python database.py
"""

import sqlite3
from contextlib import closing
from datetime import datetime

import pandas as pd

import config

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS parking_spaces (
    space_id     TEXT PRIMARY KEY,
    zone         TEXT NOT NULL,
    status       TEXT NOT NULL CHECK (status IN ('Available', 'Occupied')),
    vehicle_type TEXT NOT NULL DEFAULT 'None',
    last_updated TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS parking_history (
    record_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp    TEXT NOT NULL,
    space_id     TEXT NOT NULL,
    zone         TEXT NOT NULL,
    status       TEXT NOT NULL CHECK (status IN ('Available', 'Occupied')),
    vehicle_type TEXT NOT NULL DEFAULT 'None',
    source       TEXT NOT NULL DEFAULT 'live_simulation',
    UNIQUE (timestamp, space_id)
);

CREATE INDEX IF NOT EXISTS idx_history_timestamp ON parking_history (timestamp);

CREATE TABLE IF NOT EXISTS app_settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""
# The UNIQUE (timestamp, space_id) rule is what prevents duplicate history
# records when Streamlit re-runs the script.

DEFAULT_SETTINGS = {
    "paused": "0",
    "activity": config.DEFAULT_ACTIVITY,
    "interval_seconds": str(config.DEFAULT_INTERVAL),
    "last_update": "",
}

HISTORY_COLUMNS = ["timestamp", "space_id", "zone", "status", "vehicle_type", "source"]


# ----------------------------------------------------------------------------
# Basic helpers
# ----------------------------------------------------------------------------
def get_connection():
    """Open a new connection to smart_parking.db (waits up to 30 s if locked)."""
    return sqlite3.connect(str(config.DB_PATH), timeout=30)


def now_string():
    """Current local time as text, e.g. 2026-11-22 14:30:05."""
    return datetime.now().strftime(TIME_FORMAT)


def build_space_list():
    """Return [(space_id, zone), ...] -> A01..A10, B01..B10, C01..C10, D01..D10."""
    spaces = []
    for zone in config.ZONES:
        for number in range(1, config.SPACES_PER_ZONE + 1):
            spaces.append((f"{zone}{number:02d}", zone))
    return spaces


# ----------------------------------------------------------------------------
# Create / initialise
# ----------------------------------------------------------------------------
def init_database():
    """Create the tables and the 40 parking spaces if they do not exist yet."""
    with closing(get_connection()) as conn:
        with conn:
            conn.executescript(SCHEMA_SQL)

            count = conn.execute("SELECT COUNT(*) FROM parking_spaces").fetchone()[0]
            if count == 0:
                stamp = now_string()
                rows = [
                    (space_id, zone, config.STATUS_AVAILABLE, config.NO_VEHICLE, stamp)
                    for space_id, zone in build_space_list()
                ]
                conn.executemany(
                    "INSERT INTO parking_spaces "
                    "(space_id, zone, status, vehicle_type, last_updated) "
                    "VALUES (?, ?, ?, ?, ?)",
                    rows,
                )

            for key, value in DEFAULT_SETTINGS.items():
                conn.execute(
                    "INSERT OR IGNORE INTO app_settings (key, value) VALUES (?, ?)",
                    (key, value),
                )


# ----------------------------------------------------------------------------
# Settings
# ----------------------------------------------------------------------------
def get_setting(key, default=None):
    """Read one setting. Returns `default` if it is missing or empty."""
    with closing(get_connection()) as conn:
        row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    if row is None or row[0] == "":
        return default
    return row[0]


def set_setting(key, value):
    """Save one setting (insert or replace)."""
    with closing(get_connection()) as conn:
        with conn:
            conn.execute(
                "INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)",
                (key, str(value)),
            )


# ----------------------------------------------------------------------------
# Reading data
# ----------------------------------------------------------------------------
def get_current_status():
    """Current state of all 40 spaces as a DataFrame."""
    with closing(get_connection()) as conn:
        df = pd.read_sql_query(
            "SELECT space_id, zone, status, vehicle_type, last_updated "
            "FROM parking_spaces ORDER BY space_id",
            conn,
        )
    return df


def get_history(start=None, end=None, zones=None):
    """
    Read parking history.
      start / end : datetime objects (optional time range)
      zones       : list of zone letters, e.g. ["A", "B"] (optional)
    """
    query = "SELECT timestamp, space_id, zone, status, vehicle_type, source FROM parking_history WHERE 1=1"
    params = []

    if start is not None:
        query += " AND timestamp >= ?"
        params.append(start.strftime(TIME_FORMAT))
    if end is not None:
        query += " AND timestamp <= ?"
        params.append(end.strftime(TIME_FORMAT))
    if zones:
        placeholders = ",".join("?" for _ in zones)
        query += f" AND zone IN ({placeholders})"
        params.extend(list(zones))

    query += " ORDER BY timestamp, space_id"

    with closing(get_connection()) as conn:
        df = pd.read_sql_query(query, conn, params=params)

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def get_latest_snapshots(count=2):
    """Return the rows of the newest `count` snapshots (used to show recent changes)."""
    query = (
        "SELECT timestamp, space_id, zone, status, vehicle_type, source "
        "FROM parking_history WHERE timestamp IN ("
        "  SELECT DISTINCT timestamp FROM parking_history ORDER BY timestamp DESC LIMIT ?"
        ") ORDER BY timestamp, space_id"
    )
    with closing(get_connection()) as conn:
        df = pd.read_sql_query(query, conn, params=[int(count)])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def get_history_counts():
    """Return (number_of_snapshots, number_of_rows) stored in parking_history."""
    with closing(get_connection()) as conn:
        snapshots, rows = conn.execute(
            "SELECT COUNT(DISTINCT timestamp), COUNT(*) FROM parking_history"
        ).fetchone()
    return int(snapshots or 0), int(rows or 0)


# ----------------------------------------------------------------------------
# Writing data
# ----------------------------------------------------------------------------
def save_snapshot(status_df, timestamp=None, source="live_simulation"):
    """
    Save one snapshot: update parking_spaces AND append 40 rows to parking_history.

    Returns the number of history rows inserted. Returns 0 (and changes nothing)
    if a snapshot with the same timestamp already exists - this is the guard that
    stops duplicate records when the page re-runs.
    """
    timestamp = timestamp or now_string()

    history_rows = []
    space_updates = []
    for row in status_df.itertuples(index=False):
        history_rows.append((timestamp, row.space_id, row.zone, row.status, row.vehicle_type, source))
        space_updates.append((row.status, row.vehicle_type, timestamp, row.space_id))

    with closing(get_connection()) as conn:
        with conn:
            already_saved = conn.execute(
                "SELECT 1 FROM parking_history WHERE timestamp = ? LIMIT 1", (timestamp,)
            ).fetchone()
            if already_saved:
                return 0

            conn.executemany(
                "INSERT OR IGNORE INTO parking_history "
                "(timestamp, space_id, zone, status, vehicle_type, source) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                history_rows,
            )
            conn.executemany(
                "UPDATE parking_spaces SET status = ?, vehicle_type = ?, last_updated = ? "
                "WHERE space_id = ?",
                space_updates,
            )
            conn.execute(
                "INSERT OR REPLACE INTO app_settings (key, value) VALUES ('last_update', ?)",
                (timestamp,),
            )
    return len(history_rows)


def insert_history_rows(history_df, source="simulated_backfill"):
    """
    Bulk-insert many history rows (used to create the simulated backfill).
    Rows that already exist (same timestamp + space_id) are skipped.
    Returns the number of rows really inserted.
    """
    if history_df.empty:
        return 0

    rows = []
    for row in history_df.itertuples(index=False):
        stamp = row.timestamp
        if not isinstance(stamp, str):
            stamp = pd.Timestamp(stamp).strftime(TIME_FORMAT)
        rows.append((stamp, row.space_id, row.zone, row.status, row.vehicle_type, source))

    with closing(get_connection()) as conn:
        with conn:
            before = conn.total_changes
            conn.executemany(
                "INSERT OR IGNORE INTO parking_history "
                "(timestamp, space_id, zone, status, vehicle_type, source) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                rows,
            )
            inserted = conn.total_changes - before
    return inserted


def prune_live_history(max_snapshots=None):
    """Keep only the newest `max_snapshots` live snapshots (backfill rows are kept)."""
    max_snapshots = max_snapshots or config.MAX_LIVE_SNAPSHOTS
    with closing(get_connection()) as conn:
        with conn:
            conn.execute(
                "DELETE FROM parking_history "
                "WHERE source = 'live_simulation' AND timestamp IN ("
                "  SELECT timestamp FROM ("
                "    SELECT DISTINCT timestamp FROM parking_history "
                "    WHERE source = 'live_simulation' "
                "    ORDER BY timestamp DESC LIMIT -1 OFFSET ?"
                "  )"
                ")",
                (int(max_snapshots),),
            )


def reset_all():
    """Delete all history and set every space back to Available."""
    stamp = now_string()
    with closing(get_connection()) as conn:
        with conn:
            conn.execute("DELETE FROM parking_history")
            conn.execute(
                "UPDATE parking_spaces SET status = ?, vehicle_type = ?, last_updated = ?",
                (config.STATUS_AVAILABLE, config.NO_VEHICLE, stamp),
            )
            conn.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES ('last_update', '')")
            conn.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES ('paused', '0')")


# ----------------------------------------------------------------------------
# Run this file directly to create the database:  python database.py
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    init_database()
    snapshots, rows = get_history_counts()
    spaces = len(get_current_status())
    print("Database ready :", config.DB_PATH)
    print("Parking spaces :", spaces)
    print("History rows   :", rows, f"({snapshots} snapshots)")
    print("Next step      : streamlit run app.py")
