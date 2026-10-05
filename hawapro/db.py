import json, os, sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS masters (
  id INTEGER PRIMARY KEY, kind TEXT NOT NULL CHECK (kind IN ('party','mill')), name TEXT NOT NULL,
  gst_no TEXT, location TEXT, terms TEXT, bill_ref_style TEXT, UNIQUE (kind, name));
CREATE TABLE IF NOT EXISTS aliases (alias TEXT NOT NULL, master_id INTEGER NOT NULL REFERENCES masters(id), PRIMARY KEY (alias, master_id));
CREATE TABLE IF NOT EXISTS bills (
  id INTEGER PRIMARY KEY, ref_no TEXT NOT NULL, side TEXT NOT NULL CHECK (side IN ('sale','purchase')),
  bill_date TEXT NOT NULL, master_id INTEGER NOT NULL REFERENCES masters(id),
  quantity_kg REAL NOT NULL, rate REAL NOT NULL, value REAL NOT NULL, gst_rate REAL NOT NULL DEFAULT 18,
  open_balance REAL NOT NULL, linked_ref TEXT, UNIQUE (ref_no, side));
CREATE TABLE IF NOT EXISTS staging (
  id INTEGER PRIMARY KEY, note_no TEXT NOT NULL, note_date TEXT NOT NULL, party_text TEXT NOT NULL, mill_text TEXT,
  bill_ref TEXT NOT NULL, reason TEXT NOT NULL CHECK (reason IN ('short-qty','rate-diff')),
  short_qty_kg REAL, qty_kg REAL, accepted_rate REAL, amount REAL, gst REAL, mill_amount REAL,
  source_channel TEXT NOT NULL DEFAULT 'manual', source_file TEXT, confidence REAL NOT NULL DEFAULT 1,
  review_status TEXT NOT NULL DEFAULT 'pending' CHECK (review_status IN ('pending','verified','rejected','posted')),
  flags TEXT NOT NULL DEFAULT '[]', reject_reason TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS notes (
  id INTEGER PRIMARY KEY, note_type TEXT NOT NULL CHECK (note_type IN ('party-DN','CN-to-party','DN-to-mill','mill-CN')),
  note_no TEXT NOT NULL, note_date TEXT NOT NULL, bill_id INTEGER NOT NULL REFERENCES bills(id),
  master_id INTEGER NOT NULL REFERENCES masters(id), reason TEXT, short_qty_kg REAL, accepted_rate REAL,
  amount REAL NOT NULL, gst REAL NOT NULL, paired_note_id INTEGER, staging_id INTEGER,
  source_channel TEXT, source_file TEXT, tally_voucher_no TEXT, narration TEXT,
  status TEXT NOT NULL DEFAULT 'posted', exported INTEGER NOT NULL DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS notes_date ON notes(note_date, id);
"""


def connect(path=None):
    path = path or os.environ.get("HAWAPRO_DB", "hawapro.db")
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    c.executescript(SCHEMA)
    return c


def get_setting(c, k, default=None):
    r = c.execute("SELECT v FROM settings WHERE k=?", (k,)).fetchone()
    return r["v"] if r else default


def set_setting(c, k, v):
    c.execute("INSERT INTO settings(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, str(v)))


def next_seq(c, key):
    n = int(get_setting(c, key, 0)) + 1
    set_setting(c, key, n)
    return n
