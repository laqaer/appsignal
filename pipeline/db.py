"""SQLite store for AppSignal pipeline. stdlib only."""
import sqlite3, os
DB = os.path.join(os.path.dirname(__file__), "..", "data", "appintel.db")
SCHEMA = """
CREATE TABLE IF NOT EXISTS apps(
  trackId INTEGER PRIMARY KEY, name TEXT, seller TEXT, genre TEXT,
  price REAL DEFAULT 0, artwork TEXT);
CREATE TABLE IF NOT EXISTS snapshots(
  trackId INTEGER, ts INTEGER, rank INTEGER, chart TEXT,
  rating REAL, rating_count INTEGER, price REAL,
  PRIMARY KEY(trackId, ts, chart));
"""
def conn():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    c = sqlite3.connect(DB)
    c.executescript(SCHEMA)
    for col in ("screenshots TEXT", "description TEXT"):
        try: c.execute(f"ALTER TABLE apps ADD COLUMN {col}")
        except sqlite3.OperationalError: pass  # column exists
    return c
