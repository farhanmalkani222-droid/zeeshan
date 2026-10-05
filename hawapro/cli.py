"""python3 -m hawapro <command>.  DB path: env HAWAPRO_DB (default ./hawapro.db)."""
import argparse, csv, json, sys
from . import bills, engine, intake, masters, recon, register, tally
from .db import connect


def table(rows):
    if not rows:
        print("(none)")
        return
    cols = list(rows[0])
    w = {k: max(len(k), *(len(str(r[k] if r[k] is not None else "")) for r in rows)) for k in cols}
    print("  ".join(k.ljust(w[k]) for k in cols))
    for r in rows:
        print("  ".join(str(r[k] if r[k] is not None else "").ljust(w[k]) for k in cols))


def demo(c):
    """Sample data using the mills named in the build plan."""
    for m in ["Nexois", "Shri Varudi", "Craftech", "Ashton", "Sunshine", "Gajanan", "Sankalp", "Skywin"]:
        masters.add_master(c, "mill", m, aliases=[m.lower() + " paper mills"])
    cid = masters.add_master(c, "party", "Rajesh Traders", aliases=["rajesh trdrs", "RT"])
    masters.add_master(c, "party", "Om Packaging")
    mill = lambda n: masters.resolve(c, "mill", n)["id"]
    party = lambda n: masters.resolve(c, "party", n)["id"]
    register.add_bill(c, "HGH/P/0901", "purchase", "2026-09-05", mill("Craftech"), 12400, 22.0)
    register.add_bill(c, "HGH/S/1042", "sale", "2026-09-12", party("Rajesh Traders"), 12400, 24.5, linked_ref="HGH/P/0901")
    register.add_bill(c, "HGH/P/0915", "purchase", "2026-09-08", mill("Nexois"), 8000, 21.0)
    register.add_bill(c, "HGH/S/1050", "sale", "2026-09-14", party("Om Packaging"), 8000, 23.0, linked_ref="HGH/P/0915")
    # arrival order != date order; one deliberate bad amount
    engine.stage_note(c, "Rajesh Trdrs", "HGH/S/1042", "DN-5567", "2026-09-18", "short-qty", short_qty_kg=180, accepted_rate=23.0, source_channel="whatsapp", source_file="DN-5567.pdf")
    engine.stage_note(c, "Om Packaging", "HGH/S/1050", "OP-12", "2026-09-16", "rate-diff", accepted_rate=22.0, source_channel="mail", source_file="OP-12.pdf")
    engine.stage_note(c, "Rajesh Traders", "HGH/S/1042", "DN-5570", "2026-09-17", "short-qty", short_qty_kg=100, accepted_rate=23.0, amount=9999, source_channel="mail")


def main(argv=None):
    p = argparse.ArgumentParser(prog="hawapro", description=__doc__)
    s = p.add_subparsers(dest="cmd", required=True)
    a = s.add_parser("master-add"); a.add_argument("kind", choices=["party", "mill"]); a.add_argument("name")
    a.add_argument("--gst"); a.add_argument("--location"); a.add_argument("--terms"); a.add_argument("--alias", action="append", default=[])
    a = s.add_parser("bill-add"); a.add_argument("ref"); a.add_argument("side", choices=["sale", "purchase"]); a.add_argument("date")
    a.add_argument("master"); a.add_argument("qty", type=float); a.add_argument("rate", type=float)
    a.add_argument("--gst-rate", type=float, default=18.0); a.add_argument("--linked", help="sale bill: the purchase bill ref it traces to")
    a = s.add_parser("stage"); a.add_argument("party"); a.add_argument("bill"); a.add_argument("note_no"); a.add_argument("date")
    a.add_argument("reason", choices=["short-qty", "rate-diff"]); a.add_argument("--short-qty", type=float); a.add_argument("--qty", type=float)
    a.add_argument("--accepted-rate", type=float); a.add_argument("--amount", type=float); a.add_argument("--gst", type=float)
    a.add_argument("--mill"); a.add_argument("--mill-amount", type=float); a.add_argument("--channel", default="manual"); a.add_argument("--file")
    a = s.add_parser("import-csv", help="stage notes from CSV: party,bill,note_no,date,reason,short_qty,qty,accepted_rate,amount,gst,mill,channel,file")
    a.add_argument("path")
    s.add_parser("queue", help="date-sorted staging queue")
    for n in ("verify", "reject"):
        a = s.add_parser(n); a.add_argument("id", type=int)
        if n == "reject": a.add_argument("--why", default="")
    a = s.add_parser("verify-all", help="verify every unflagged pending note"); a.add_argument("--min-confidence", type=float, default=0.0, help="skip notes the extractor was less sure of")
    a = s.add_parser("edit"); a.add_argument("id", type=int); a.add_argument("fields", nargs="+", help="field=value")
    a = s.add_parser("close-period"); a.add_argument("through")
    a = s.add_parser("post"); a.add_argument("--dry-run", action="store_true"); a.add_argument("--xml", help="write Tally import XML (all posted vouchers) to this path")
    a.add_argument("--company")
    a = s.add_parser("mill-cn"); a.add_argument("mill_dn_id", type=int); a.add_argument("cn_no"); a.add_argument("date"); a.add_argument("amount", type=float)
    a = s.add_parser("report"); a.add_argument("name", choices=sorted(recon.REPORTS)); a.add_argument("--csv", action="store_true")
    a = s.add_parser("intake", help="extract debit-note PDFs/.txt (file or folder) into the staging queue"); a.add_argument("path"); a.add_argument("--channel", default="manual", choices=["mail", "whatsapp", "manual"])
    a = s.add_parser("bills-import", help="load the bill register from CSV"); a.add_argument("path"); a.add_argument("--create-masters", action="store_true")
    a = s.add_parser("set-ledger", help="Tally ledger name: sales_adj|purchase_adj|output_gst|input_gst"); a.add_argument("key", choices=sorted(tally.LEDGERS)); a.add_argument("name")
    a = s.add_parser("serve", help="web review/posting screen"); a.add_argument("--host", default="127.0.0.1"); a.add_argument("--port", type=int, default=8765)
    s.add_parser("demo")
    args = p.parse_args(argv)
    c = connect()
    try:
        out = run(c, args)
        c.commit()
        return out or 0
    except (ValueError, KeyError, engine.DuplicateNote) as e:
        c.rollback()
        print("error:", e.args[0] if isinstance(e, KeyError) else e, file=sys.stderr)
        return 1


def run(c, a):
    if a.cmd == "master-add":
        masters.add_master(c, a.kind, a.name, a.gst, a.location, a.terms, aliases=a.alias)
    elif a.cmd == "bill-add":
        m = masters.resolve(c, "party" if a.side == "sale" else "mill", a.master)
        if not m: raise ValueError(f"{a.master!r} does not resolve to one {'party' if a.side == 'sale' else 'mill'}")
        register.add_bill(c, a.ref, a.side, a.date, m["id"], a.qty, a.rate, gst_rate=a.gst_rate, linked_ref=a.linked)
    elif a.cmd == "stage":
        sid, flags = engine.stage_note(c, a.party, a.bill, a.note_no, a.date, a.reason, a.short_qty, a.qty, a.accepted_rate,
                                       a.amount, a.gst, a.mill, a.mill_amount, a.channel, a.file)
        print(f"staged #{sid}", "HELD: " + ", ".join(flags) if flags else "ok")
    elif a.cmd == "import-csv":
        f = lambda v: float(v) if v not in (None, "") else None
        for r in csv.DictReader(open(a.path, newline="")):
            sid, flags = engine.stage_note(c, r["party"], r["bill"], r["note_no"], r["date"], r["reason"], f(r.get("short_qty")), f(r.get("qty")),
                                           f(r.get("accepted_rate")), f(r.get("amount")), f(r.get("gst")), r.get("mill") or None, None,
                                           r.get("channel") or "manual", r.get("file") or None)
            print(f"#{sid} {r['note_no']}:", "HELD " + ",".join(flags) if flags else "ok")
    elif a.cmd == "queue":
        table([{"id": r["id"], "date": r["note_date"], "party": r["party_text"], "bill": r["bill_ref"], "note": r["note_no"],
                "reason": r["reason"], "review": r["review_status"], "flags": ",".join(json.loads(r["flags"]))} for r in engine.queue(c)])
    elif a.cmd == "verify":
        engine.verify(c, a.id); print(f"#{a.id} verified")
    elif a.cmd == "verify-all":
        for r in engine.queue(c, ("pending",)):
            if r["confidence"] < a.min_confidence: print(f"#{r['id']} skipped (confidence {r['confidence']})"); continue
            try: engine.verify(c, r["id"]); print(f"#{r['id']} verified")
            except ValueError as e: print(e)
    elif a.cmd == "reject":
        engine.reject(c, a.id, a.why)
    elif a.cmd == "edit":
        kv = dict(x.split("=", 1) for x in a.fields)
        num = {"short_qty_kg", "qty_kg", "accepted_rate", "amount", "gst", "mill_amount"}
        flags = engine.edit(c, a.id, **{k: (float(v) if k in num and v != "" else (None if k in num else v)) for k, v in kv.items()})
        print("flags:", ", ".join(flags) or "none")
    elif a.cmd == "close-period":
        engine.close_period(c, a.through)
    elif a.cmd == "post":
        res = engine.post_batch(c, a.dry_run)
        table(res["posted"]); [print(f"HELD #{i}: {', '.join(f)}") for i, f in res["held"]]
        print(("DRY RUN - nothing saved. " if a.dry_run else "") + f"{len(res['posted'])} paired note(s) posted, {len(res['held'])} held")
        if a.xml and not a.dry_run:
            open(a.xml, "w", encoding="utf-8").write(tally.vouchers(c, a.company)); tally.mark_exported(c); print("wrote", a.xml, "(new vouchers only; each is exported once)")
    elif a.cmd == "mill-cn":
        engine.record_mill_cn(c, a.mill_dn_id, a.cn_no, a.date, a.amount)
    elif a.cmd == "report":
        rows = recon.REPORTS[a.name](c)
        if a.csv and rows:
            w = csv.DictWriter(sys.stdout, rows[0].keys()); w.writeheader(); w.writerows(rows)
        else:
            table(rows)
    elif a.cmd == "intake":
        import os
        rows = intake.process_dir(c, a.path, a.channel) if os.path.isdir(a.path) else [(os.path.basename(a.path), *intake.process_file(c, a.path, a.channel))]
        for r in rows: print(*r)
    elif a.cmd == "bills-import":
        added, skipped, errs = bills.import_csv(c, a.path, a.create_masters)
        print(f"{added} added, {skipped} already present"); [print("  " + e) for e in errs]
    elif a.cmd == "set-ledger":
        from .db import set_setting; set_setting(c, "ledger_" + a.key, a.name)
    elif a.cmd == "serve":
        c.commit(); from .web import serve; serve(a.host, a.port)
    elif a.cmd == "demo":
        demo(c); print("demo data loaded; try: queue, verify-all, post --dry-run")


if __name__ == "__main__":
    sys.exit(main())
