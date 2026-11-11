"""Local SQLite schema. No patient data leaves this database automatically."""
import sqlite3
from pathlib import Path

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS patients (
  id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS visits (
  id TEXT PRIMARY KEY,
  patient_id TEXT NOT NULL REFERENCES patients(id),
  clinic_id TEXT NOT NULL,
  appointment_start TEXT NOT NULL,
  appointment_end TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS photos (
  id TEXT PRIMARY KEY,
  visit_id TEXT REFERENCES visits(id),
  original_filename TEXT NOT NULL,
  capture_time TEXT,
  sha256 TEXT NOT NULL,
  stored_path TEXT NOT NULL,
  camera_model TEXT
);
CREATE TABLE IF NOT EXISTS sync_events (
  id TEXT PRIMARY KEY,
  device_id TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  created_at TEXT NOT NULL,
  payload_json TEXT NOT NULL
);
"""

def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.executescript(SCHEMA)
    return db
