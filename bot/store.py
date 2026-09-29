"""Tiny SQLite store: recent turns + follow-up state per customer."""
import sqlite3, time

class Store:
    def __init__(self, path="bot.db"):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS msgs(uid TEXT, role TEXT, text TEXT, ts REAL);
        CREATE TABLE IF NOT EXISTS conv(uid TEXT PRIMARY KEY, last_ts REAL, last_role TEXT,
                                        followups INTEGER DEFAULT 0, handoff INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS seen(mid TEXT PRIMARY KEY);""")

    def seen(self, mid):
        try:
            self.db.execute("INSERT INTO seen VALUES(?)", (mid,)); self.db.commit(); return False
        except sqlite3.IntegrityError:
            return True

    def add(self, uid, role, text):
        now = time.time()
        self.db.execute("INSERT INTO msgs VALUES(?,?,?,?)", (uid, role, text, now))
        fu = "followups=0," if role == "user" else ""
        self.db.execute(f"""INSERT INTO conv(uid,last_ts,last_role) VALUES(?,?,?)
            ON CONFLICT(uid) DO UPDATE SET {fu} last_ts=?, last_role=?""", (uid, now, role, now, role))
        self.db.commit()

    def mark_bot_mid(self, mid):
        if mid:
            self.db.execute("INSERT OR IGNORE INTO seen VALUES(?)", ("bot:" + mid,)); self.db.commit()

    def is_bot_mid(self, mid):
        return self.db.execute("SELECT 1 FROM seen WHERE mid=?", ("bot:" + mid,)).fetchone() is not None

    def bot_sent_since(self, uid, seconds):
        return self.db.execute("SELECT COUNT(*) FROM msgs WHERE uid=? AND role='bot' AND ts>?",
                               (uid, time.time() - seconds)).fetchone()[0]

    def user_message_count(self, uid):
        r = self.db.execute("SELECT COUNT(*) FROM msgs WHERE uid=? AND role='user'", (uid,)).fetchone()
        return r[0] if r else 0

    def history(self, uid, n):
        rows = self.db.execute("SELECT role,text FROM msgs WHERE uid=? ORDER BY ts DESC LIMIT ?", (uid, n)).fetchall()
        return rows[::-1]

    def set_handoff(self, uid, v=1):
        self.db.execute("UPDATE conv SET handoff=? WHERE uid=?", (v, uid)); self.db.commit()

    def is_handoff(self, uid):
        r = self.db.execute("SELECT handoff FROM conv WHERE uid=?", (uid,)).fetchone()
        return bool(r and r[0])

    def due_followups(self, after_h, max_n):
        """Bot spoke last, customer silent >after_h, still inside Meta's 24h window."""
        now = time.time()
        return [r[0] for r in self.db.execute(
            """SELECT uid FROM conv WHERE last_role='bot' AND handoff=0 AND followups<?
               AND last_ts<? AND last_ts>?""", (max_n, now - after_h * 3600, now - 23 * 3600))]

    def mark_followup(self, uid):
        self.db.execute("UPDATE conv SET followups=followups+1,last_ts=? WHERE uid=?", (time.time(), uid))
        self.db.commit()
