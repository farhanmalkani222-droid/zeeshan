"""Bill register import from CSV (e.g. a Tally outstanding / day-book export massaged to these columns):
ref_no,side,date,party_or_mill,quantity_kg,rate[,value,gst_rate,open_balance,linked_ref,gst_no,location]"""
import csv
from . import masters, register


def import_csv(c, path, create_masters=False):
    added, skipped, errors = 0, 0, []
    f = lambda v: float(str(v).replace(",", "")) if v not in (None, "") else None
    for n, r in enumerate(csv.DictReader(open(path, newline="", encoding="utf-8-sig")), 2):
        try:
            side = r["side"].strip().lower()
            kind = "party" if side == "sale" else "mill"
            m = masters.resolve(c, kind, r["party_or_mill"])
            if not m and create_masters:
                masters.add_master(c, kind, r["party_or_mill"].strip(), r.get("gst_no") or None, r.get("location") or None)
                m = masters.resolve(c, kind, r["party_or_mill"])
            if not m:
                raise ValueError(f"{r['party_or_mill']!r} is not a known {kind}")
            if register.get_bill(c, r["ref_no"].strip(), side):
                skipped += 1
                continue
            register.add_bill(c, r["ref_no"].strip(), side, r["date"].strip(), m["id"], f(r["quantity_kg"]), f(r["rate"]), f(r.get("value")),
                              f(r.get("gst_rate")) if r.get("gst_rate") else 18.0, (r.get("linked_ref") or "").strip() or None)
            if r.get("open_balance") not in (None, ""):
                c.execute("UPDATE bills SET open_balance=? WHERE ref_no=? AND side=?", (f(r["open_balance"]), r["ref_no"].strip(), side))
            added += 1
        except (KeyError, ValueError, TypeError) as e:
            errors.append(f"row {n}: {e}")
    return added, skipped, errors
