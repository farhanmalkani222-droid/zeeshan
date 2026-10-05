"""Staging, validation, review and the date-ordered paired-posting engine."""
import json, datetime as dt
from . import masters, register
from .db import get_setting, set_setting, next_seq

AMT_TOL = 1.0   # rupees; claim recompute and GST recompute tolerance
FLAG_TEXT = {
    "BAD_DATE": "note date is not a valid YYYY-MM-DD date",
    "NAME_UNRESOLVED": "party/mill name does not resolve to exactly one master",
    "BILL_NOT_FOUND": "Against-Ref sale bill not in register",
    "BILL_CLOSED": "Against-Ref bill has no open balance",
    "OVER_ADJUST": "note exceeds the open balance of its bill",
    "CLAIM_INCOMPLETE": "claim fields missing for this reason type",
    "AMOUNT_MISMATCH": "stated amount differs from recomputed claim",
    "GST_MISMATCH": "stated GST differs from recomputed GST",
    "PERIOD_CLOSED": "note date falls in a closed period",
    "NO_MILL_LINK": "sale bill is not linked to an open purchase bill, so the paired mill debit cannot be raised",
    "MILL_MISMATCH": "mill named on note differs from the mill the bill traces to",
    "MILL_OVER_ADJUST": "paired mill debit exceeds the purchase bill's open balance",
}


class DuplicateNote(ValueError):
    pass


def _date(s):
    try:
        return dt.date.fromisoformat(s)
    except (TypeError, ValueError):
        return None


def compute_claim(row, bill):
    """Taxable claim from the bill: short_qty*rate, or (billed-accepted rate)*qty. None if inputs missing."""
    if row["reason"] == "short-qty":
        if row["short_qty_kg"] is None:
            return None
        rate = row["accepted_rate"] if row["accepted_rate"] is not None else bill["rate"]
        return round(row["short_qty_kg"] * rate, 2)
    if row["accepted_rate"] is None:
        return None
    qty = row["qty_kg"] if row["qty_kg"] is not None else bill["quantity_kg"]
    return round((bill["rate"] - row["accepted_rate"]) * qty, 2)


def validate(c, row, open_sale=None, open_purchase=None):
    """Run every pre-posting check. Returns (flags, ctx). `open_*` override balances (used for in-batch running totals)."""
    flags, ctx = [], {}
    d = _date(row["note_date"])
    if not d:
        flags.append("BAD_DATE")
    party = masters.resolve(c, "party", row["party_text"])
    if not party:
        flags.append("NAME_UNRESOLVED")
    sale = register.get_bill(c, row["bill_ref"], "sale")
    if not sale:
        flags.append("BILL_NOT_FOUND")
    elif party and sale["master_id"] != party["id"]:
        flags.append("BILL_NOT_FOUND")          # bill exists but belongs to someone else
    if d:
        closed = get_setting(c, "closed_through")
        if closed and d <= dt.date.fromisoformat(closed):
            flags.append("PERIOD_CLOSED")
    if not sale or "BILL_NOT_FOUND" in flags:
        return flags, ctx
    bal = sale["open_balance"] if open_sale is None else open_sale
    if bal <= 0.005:
        flags.append("BILL_CLOSED")
    claim = compute_claim(row, sale)
    amount = row["amount"]
    if claim is None:
        flags.append("CLAIM_INCOMPLETE")
    elif amount is None:
        amount = claim
    elif abs(amount - claim) > AMT_TOL:
        flags.append("AMOUNT_MISMATCH")
    if amount is not None:
        if amount > bal + 0.005 and "BILL_CLOSED" not in flags:
            flags.append("OVER_ADJUST")
        gst = round(amount * sale["gst_rate"] / 100, 2)
        if row["gst"] is not None and abs(row["gst"] - gst) > AMT_TOL:
            flags.append("GST_MISMATCH")
        ctx.update(amount=amount, gst=gst if row["gst"] is None else row["gst"])
    # pairing: sale bill must trace to a purchase bill (and so a mill)
    purchase = register.get_bill(c, sale["linked_ref"], "purchase") if sale["linked_ref"] else None
    if not purchase:
        flags.append("NO_MILL_LINK")
    else:
        mill = c.execute("SELECT * FROM masters WHERE id=?", (purchase["master_id"],)).fetchone()
        if row["mill_text"]:
            named = masters.resolve(c, "mill", row["mill_text"])
            if not named:
                flags.append("NAME_UNRESOLVED")
            elif named["id"] != mill["id"]:
                flags.append("MILL_MISMATCH")
        m_amt = row["mill_amount"] if row["mill_amount"] is not None else amount
        pbal = purchase["open_balance"] if open_purchase is None else open_purchase
        if m_amt is not None and m_amt > pbal + 0.005:
            flags.append("MILL_OVER_ADJUST")
        ctx.update(mill=mill, purchase=purchase, mill_amount=m_amt)
    ctx.update(party=party, sale=sale)
    return list(dict.fromkeys(flags)), ctx


def _save_flags(c, sid, flags):
    c.execute("UPDATE staging SET flags=? WHERE id=?", (json.dumps(flags), sid))


def stage_note(c, party, bill_ref, note_no, note_date, reason, short_qty_kg=None, qty_kg=None, accepted_rate=None,
               amount=None, gst=None, mill=None, mill_amount=None, source_channel="manual", source_file=None,
               confidence=1.0):
    """Capture a party debit note into the staging queue. Rejects duplicates; runs validation immediately."""
    mine = masters.resolve(c, "party", party)
    pid = mine["id"] if mine else None
    for r in c.execute("SELECT * FROM staging WHERE lower(note_no)=lower(?) AND bill_ref=? AND review_status!='rejected'", (note_no, bill_ref)):
        other = masters.resolve(c, "party", r["party_text"])
        if r["party_text"].lower() == party.lower() or (pid is not None and other is not None and other["id"] == pid):
            raise DuplicateNote(f"note {note_no} for {party} against {bill_ref} already staged (#{r['id']})")
    cur = c.execute("""INSERT INTO staging(note_no,note_date,party_text,mill_text,bill_ref,reason,short_qty_kg,qty_kg,accepted_rate,
                       amount,gst,mill_amount,source_channel,source_file,confidence) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (note_no, note_date, party, mill, bill_ref, reason, short_qty_kg, qty_kg, accepted_rate, amount, gst,
                     mill_amount, source_channel, source_file, confidence))
    sid = cur.lastrowid
    flags, _ = validate(c, get(c, sid))
    _save_flags(c, sid, flags)
    return sid, flags


def get(c, sid):
    r = c.execute("SELECT * FROM staging WHERE id=?", (sid,)).fetchone()
    if not r:
        raise KeyError(f"no staged note #{sid}")
    return r


EDITABLE = {"note_no", "note_date", "party_text", "mill_text", "bill_ref", "reason", "short_qty_kg", "qty_kg",
            "accepted_rate", "amount", "gst", "mill_amount"}


def edit(c, sid, **fields):
    bad = set(fields) - EDITABLE
    if bad:
        raise ValueError(f"cannot edit {sorted(bad)}")
    if get(c, sid)["review_status"] == "posted":
        raise ValueError("note already posted")
    for k, v in fields.items():
        c.execute(f"UPDATE staging SET {k}=?, review_status='pending' WHERE id=?", (v, sid))
    flags, _ = validate(c, get(c, sid))
    _save_flags(c, sid, flags)
    return flags


def verify(c, sid):
    """Accountant sign-off. Refuses while any validation flag is open - fix via edit() or reject."""
    row = get(c, sid)
    flags, _ = validate(c, row)
    _save_flags(c, sid, flags)
    if flags:
        raise ValueError(f"#{sid} held: " + "; ".join(f"{f} ({FLAG_TEXT[f]})" for f in flags))
    c.execute("UPDATE staging SET review_status='verified' WHERE id=? AND review_status!='posted'", (sid,))


def reject(c, sid, why=""):
    if get(c, sid)["review_status"] == "posted":
        raise ValueError("note already posted")
    c.execute("UPDATE staging SET review_status='rejected', reject_reason=? WHERE id=?", (why, sid))


def close_period(c, through_date):
    if not _date(through_date):
        raise ValueError("date must be YYYY-MM-DD")
    set_setting(c, "closed_through", through_date)


def queue(c, statuses=("pending", "verified")):
    """Staging queue sorted by the note's own date (never arrival order), across all parties and mills."""
    q = ",".join("?" * len(statuses))
    return c.execute(f"SELECT * FROM staging WHERE review_status IN ({q}) ORDER BY note_date, id", statuses).fetchall()


def exceptions(c):
    return [r for r in queue(c) if json.loads(r["flags"])]


def post_batch(c, dry_run=False):
    """Post every verified note in note-date order as a paired action (CN to party + DN to mill, same date).
    Each note is re-validated against running balances; a failing note is held, never half-posted.
    Returns {"posted": [...], "held": [(id, flags)]}."""
    out = {"posted": [], "held": []}
    running = {}                      # bill id -> running open balance within this batch
    c.execute("SAVEPOINT batch")
    try:
        for row in queue(c, ("verified",)):
            sale = register.get_bill(c, row["bill_ref"], "sale")
            pur = register.get_bill(c, sale["linked_ref"], "purchase") if sale and sale["linked_ref"] else None
            flags, ctx = validate(c, row, running.get(sale["id"]) if sale else None,
                                  running.get(pur["id"]) if pur else None)
            if flags:
                _save_flags(c, row["id"], flags)
                c.execute("UPDATE staging SET review_status='pending' WHERE id=?", (row["id"],))
                out["held"].append((row["id"], flags))
                continue
            amt, gst, m_amt = ctx["amount"], ctx["gst"], ctx["mill_amount"]
            m_gst = round(m_amt * pur["gst_rate"] / 100, 2)
            src = f"{row['source_channel']}; party DN {row['note_no']}"
            cn_no, dn_no = f"CN/{next_seq(c, 'seq_cn')}", f"DN/{next_seq(c, 'seq_dn')}"
            cn = c.execute("""INSERT INTO notes(note_type,note_no,note_date,bill_id,master_id,reason,short_qty_kg,accepted_rate,amount,gst,
                              staging_id,source_channel,source_file,tally_voucher_no,narration) VALUES('CN-to-party',?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                           (row["note_no"], row["note_date"], sale["id"], ctx["party"]["id"], row["reason"], row["short_qty_kg"],
                            row["accepted_rate"], amt, gst, row["id"], row["source_channel"], row["source_file"], cn_no, src)).lastrowid
            dn = c.execute("""INSERT INTO notes(note_type,note_no,note_date,bill_id,master_id,reason,short_qty_kg,accepted_rate,amount,gst,
                              paired_note_id,staging_id,source_channel,source_file,tally_voucher_no,narration) VALUES('DN-to-mill',?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                           (row["note_no"], row["note_date"], pur["id"], ctx["mill"]["id"], row["reason"], row["short_qty_kg"],
                            row["accepted_rate"], m_amt, m_gst, cn, row["id"], row["source_channel"], row["source_file"], dn_no,
                            f"{src}; against {row['bill_ref']}")).lastrowid
            c.execute("UPDATE notes SET paired_note_id=? WHERE id=?", (dn, cn))
            running[sale["id"]] = round(running.get(sale["id"], sale["open_balance"]) - amt, 2)
            running[pur["id"]] = round(running.get(pur["id"], pur["open_balance"]) - m_amt, 2)
            c.execute("UPDATE staging SET review_status='posted', flags='[]' WHERE id=?", (row["id"],))
            out["posted"].append({"staging_id": row["id"], "date": row["note_date"], "cn": cn_no, "dn": dn_no, "amount": amt})
        if not dry_run:
            for bid, bal in running.items():
                c.execute("UPDATE bills SET open_balance=? WHERE id=?", (bal, bid))
        if dry_run:
            c.execute("ROLLBACK TO batch")
        c.execute("RELEASE batch")
    except Exception:
        c.execute("ROLLBACK TO batch")
        c.execute("RELEASE batch")
        raise
    return out


def record_mill_cn(c, mill_dn_id, cn_no, cn_date, amount):
    """Record the credit note a mill sends back against our debit note (any later month). Does not move bill balance."""
    dn = c.execute("SELECT * FROM notes WHERE id=? AND note_type='DN-to-mill'", (mill_dn_id,)).fetchone()
    if not dn:
        raise KeyError(f"no mill debit note #{mill_dn_id}")
    if not _date(cn_date):
        raise ValueError("date must be YYYY-MM-DD")
    if c.execute("SELECT 1 FROM notes WHERE note_type='mill-CN' AND paired_note_id=?", (mill_dn_id,)).fetchone():
        raise DuplicateNote(f"mill debit #{mill_dn_id} already has a credit note recorded")
    c.execute("""INSERT INTO notes(note_type,note_no,note_date,bill_id,master_id,amount,gst,paired_note_id,narration)
                 VALUES('mill-CN',?,?,?,?,?,0,?,?)""", (cn_no, cn_date, dn["bill_id"], dn["master_id"], round(amount, 2),
                                                          mill_dn_id, f"mill credit note against {dn['tally_voucher_no']}"))
