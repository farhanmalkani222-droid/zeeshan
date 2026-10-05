from .db import connect


class NameError_(ValueError):
    pass


def add_master(c, kind, name, gst_no=None, location=None, terms=None, bill_ref_style=None, aliases=()):
    c.execute("INSERT INTO masters(kind,name,gst_no,location,terms,bill_ref_style) VALUES(?,?,?,?,?,?)",
              (kind, name, gst_no, location, terms, bill_ref_style))
    mid = c.execute("SELECT id FROM masters WHERE kind=? AND name=?", (kind, name)).fetchone()["id"]
    for a in aliases:
        add_alias(c, mid, a)
    return mid


def add_alias(c, master_id, alias):
    c.execute("INSERT OR IGNORE INTO aliases(alias,master_id) VALUES(?,?)", (alias.strip().lower(), master_id))


def resolve(c, kind, text):
    """Name text -> exactly one master of `kind` via name or alias; None if zero or ambiguous."""
    t = (text or "").strip().lower()
    if not t:
        return None
    rows = c.execute("""SELECT DISTINCT m.* FROM masters m LEFT JOIN aliases a ON a.master_id=m.id
                        WHERE m.kind=? AND (lower(m.name)=? OR a.alias=?)""", (kind, t, t)).fetchall()
    return rows[0] if len(rows) == 1 else None
