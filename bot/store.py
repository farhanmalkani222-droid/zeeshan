"""Tiny SQLite store: recent turns + follow-up state per customer."""
import sqlite3, time

class Store:
    def __init__(self, path="bot.db"):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS msgs(uid TEXT, role TEXT, text TEXT, ts REAL);
        CREATE TABLE IF NOT EXISTS conv(uid TEXT PRIMARY KEY, last_ts REAL, last_role TEXT,
                                        followups INTEGER DEFAULT 0, handoff INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS seen(mid TEXT PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS leads(uid TEXT, status TEXT, qty INTEGER, pincode TEXT, phone TEXT, details TEXT, ts REAL);
        CREATE TABLE IF NOT EXISTS unanswered(id INTEGER PRIMARY KEY AUTOINCREMENT, uid TEXT, question TEXT, reason TEXT, ts REAL, resolved INTEGER DEFAULT 0);""")
        for col, ddl in (("rapport", "rapport INTEGER DEFAULT 0"), ("last_user_ts", "last_user_ts REAL")):
            try:  # migrate older DBs in place
                self.db.execute(f"ALTER TABLE conv ADD COLUMN {ddl}"); self.db.commit()
            except sqlite3.OperationalError:
                pass  # column already exists

    def seen(self, mid):
        try:
            self.db.execute("INSERT INTO seen VALUES(?)", (mid,)); self.db.commit(); return False
        except sqlite3.IntegrityError:
            return True

    def add(self, uid, role, text):
        now = time.time()
        self.db.execute("INSERT INTO msgs VALUES(?,?,?,?)", (uid, role, text, now))
        if role == "user":  # reset follow-up count and stamp the customer's last inbound time (24h-window anchor)
            self.db.execute("""INSERT INTO conv(uid,last_ts,last_role,last_user_ts,followups) VALUES(?,?,?,?,0)
                ON CONFLICT(uid) DO UPDATE SET last_ts=?, last_role=?, last_user_ts=?, followups=0""",
                (uid, now, role, now, now, role, now))
        else:
            self.db.execute("""INSERT INTO conv(uid,last_ts,last_role) VALUES(?,?,?)
                ON CONFLICT(uid) DO UPDATE SET last_ts=?, last_role=?""", (uid, now, role, now, role))
        self.db.commit()

    def mark_bot_mid(self, mid):
        if mid:
            self.db.execute("INSERT OR IGNORE INTO seen VALUES(?)", ("bot:" + mid,)); self.db.commit()

    def is_bot_mid(self, mid):
        return self.db.execute("SELECT 1 FROM seen WHERE mid=?", ("bot:" + mid,)).fetchone() is not None

    def bot_sent_since(self, uid, seconds):
        return self.db.execute("SELECT COUNT(*) FROM msgs WHERE uid=? AND role='bot' AND ts>?",
                               (uid, time.time() - seconds)).fetchone()[0]

    def add_lead(self, uid, status, qty, pincode, phone, details):
        self.db.execute("INSERT INTO leads VALUES(?,?,?,?,?,?,?)", (uid, status, qty, pincode, phone, details, time.time()))
        self.db.commit()

    def leads(self, status=None):
        q = "SELECT uid,status,qty,pincode,phone,details,ts FROM leads" + (" WHERE status=?" if status else "") + " ORDER BY ts"
        return self.db.execute(q, (status,) if status else ()).fetchall()

    def add_unanswered(self, uid, question, reason):
        self.db.execute("INSERT INTO unanswered(uid,question,reason,ts) VALUES(?,?,?,?)", (uid, question, reason, time.time()))
        self.db.commit()

    def unanswered(self, include_resolved=False):
        q = "SELECT id, uid, question, reason, ts, resolved FROM unanswered" + ("" if include_resolved else " WHERE resolved=0") + " ORDER BY ts"
        return self.db.execute(q).fetchall()

    def resolve_unanswered(self, qid):
        self.db.execute("UPDATE unanswered SET resolved=1 WHERE id=?", (qid,)); self.db.commit()

    def user_message_count(self, uid):
        r = self.db.execute("SELECT COUNT(*) FROM msgs WHERE uid=? AND role='user'", (uid,)).fetchone()
        return r[0] if r else 0

    def history(self, uid, n):
        rows = self.db.execute("SELECT role,text FROM msgs WHERE uid=? ORDER BY ts DESC LIMIT ?", (uid, n)).fetchall()
        return rows[::-1]

    def rapport_sent(self, uid):
        r = self.db.execute("SELECT rapport FROM conv WHERE uid=?", (uid,)).fetchone()
        return bool(r and r[0])

    def mark_rapport(self, uid):
        self.db.execute("UPDATE conv SET rapport=1 WHERE uid=?", (uid,)); self.db.commit()

    def set_handoff(self, uid, v=1):
        self.db.execute("UPDATE conv SET handoff=? WHERE uid=?", (v, uid)); self.db.commit()

    def is_handoff(self, uid):
        r = self.db.execute("SELECT handoff FROM conv WHERE uid=?", (uid,)).fetchone()
        return bool(r and r[0])

    def due_followups(self, after_h, max_n):
        """Bot spoke last, customer silent >after_h, and still inside Meta's 24h window measured from the
        customer's OWN last message (not the bot's) — sending outside that window is a real policy/flag risk."""
        now = time.time()
        return [r[0] for r in self.db.execute(
            """SELECT uid FROM conv WHERE last_role='bot' AND handoff=0 AND followups<?
               AND last_ts<? AND last_user_ts IS NOT NULL AND last_user_ts>?""",
            (max_n, now - after_h * 3600, now - 24 * 3600))]

    def mark_followup(self, uid):
        self.db.execute("UPDATE conv SET followups=followups+1,last_ts=? WHERE uid=?", (time.time(), uid))
        self.db.commit()
