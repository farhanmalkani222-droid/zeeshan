"""Reconciliation reports. Mill timing gap is a pending item, not an error; true mismatches are flagged separately."""
import datetime as dt
from .engine import AMT_TOL

OVERDUE_DAYS = 60


def day_register(c):
    return [dict(r) for r in c.execute("""
        SELECT n.note_date, n.tally_voucher_no voucher, n.note_type, m.name party_or_mill, b.ref_no against_ref, n.reason,
               n.amount, n.gst, n.amount+n.gst total, n.source_channel channel
        FROM notes n JOIN masters m ON m.id=n.master_id JOIN bills b ON b.id=n.bill_id
        ORDER BY n.note_date, n.id""")]


def bill_outstanding(c):
    return [dict(r) for r in c.execute("""
        SELECT b.ref_no, b.side, b.bill_date, m.name party_or_mill, b.value, b.value-b.open_balance adjusted,
               b.open_balance, CASE WHEN b.open_balance>0.005 THEN 'open' ELSE 'closed' END status
        FROM bills b JOIN masters m ON m.id=b.master_id ORDER BY b.side, b.bill_date, b.ref_no""")]


def linkage(c):
    return [dict(r) for r in c.execute("""
        SELECT cn.note_date, cn.note_no party_note, p.name party, sb.ref_no sale_bill, cn.tally_voucher_no party_cn,
               cn.amount party_amount, dn.tally_voucher_no mill_dn, m.name mill, pb.ref_no purchase_bill, dn.amount mill_amount
        FROM notes cn JOIN notes dn ON dn.id=cn.paired_note_id
        JOIN masters p ON p.id=cn.master_id JOIN masters m ON m.id=dn.master_id
        JOIN bills sb ON sb.id=cn.bill_id JOIN bills pb ON pb.id=dn.bill_id
        WHERE cn.note_type='CN-to-party' ORDER BY cn.note_date, cn.id""")]


def pending_mill_cn(c, today=None):
    """Every mill debit with its credit-note status: pending (timing), received, mismatch (amount), overdue (> 60 days)."""
    today = today or dt.date.today()
    rows = []
    for r in c.execute("""SELECT dn.id, dn.tally_voucher_no dn_voucher, dn.note_date, m.name mill, b.ref_no purchase_bill, dn.amount,
                                 mc.note_no mill_cn_no, mc.note_date mill_cn_date, mc.amount mill_cn_amount
                          FROM notes dn JOIN masters m ON m.id=dn.master_id JOIN bills b ON b.id=dn.bill_id
                          LEFT JOIN notes mc ON mc.paired_note_id=dn.id AND mc.note_type='mill-CN'
                          WHERE dn.note_type='DN-to-mill' ORDER BY dn.note_date, dn.id"""):
        d = dict(r)
        d["age_days"] = (today - dt.date.fromisoformat(d["note_date"])).days
        if d["mill_cn_no"] is None:
            d["status"] = "overdue" if d["age_days"] > OVERDUE_DAYS else "pending"
        else:
            d["status"] = "received" if abs(d["mill_cn_amount"] - d["amount"]) <= AMT_TOL else "mismatch"
        rows.append(d)
    return rows


def month_gap(c):
    """Debits raised vs mill credit notes received, per month - a debit in Oct answered in Nov reads as timing."""
    months = {}
    for r in pending_mill_cn(c):
        raised = months.setdefault(r["note_date"][:7], {"month": r["note_date"][:7], "debits_raised": 0.0, "cn_received": 0.0})
        raised["debits_raised"] += r["amount"]
        if r["mill_cn_no"]:
            got = months.setdefault(r["mill_cn_date"][:7], {"month": r["mill_cn_date"][:7], "debits_raised": 0.0, "cn_received": 0.0})
            got["cn_received"] += r["mill_cn_amount"]
    out, cum = [], 0.0
    for m in sorted(months):
        v = months[m]
        cum += v["debits_raised"] - v["cn_received"]
        out.append({**{k: (round(x, 2) if isinstance(x, float) else x) for k, x in v.items()}, "net_month": round(v["debits_raised"] - v["cn_received"], 2),
                    "cumulative_pending": round(cum, 2)})
    return out


def exceptions(c):
    from . import engine
    import json
    return [{"id": r["id"], "note_date": r["note_date"], "party": r["party_text"], "bill_ref": r["bill_ref"], "note_no": r["note_no"],
             "review": r["review_status"], "flags": ", ".join(json.loads(r["flags"])) or "awaiting review"}
            for r in engine.queue(c) if json.loads(r["flags"]) or r["review_status"] == "pending"]


REPORTS = {"day-register": day_register, "bill-outstanding": bill_outstanding, "pending-mill-cn": pending_mill_cn,
           "linkage": linkage, "month-gap": month_gap, "exceptions": exceptions}
