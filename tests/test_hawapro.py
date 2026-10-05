import datetime as dt, os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from hawapro import engine, masters, recon, register, tally
from hawapro.cli import demo
from hawapro.db import connect


def fresh():
    c = connect(":memory:")
    demo(c)
    return c


class T(unittest.TestCase):
    def test_validation_flags_and_amounts(self):
        c = fresh()
        q = {r["note_no"]: r for r in engine.queue(c)}
        self.assertEqual(engine.validate(c, q["DN-5567"])[0], [])
        _, ctx = engine.validate(c, q["DN-5567"])
        self.assertEqual((ctx["amount"], ctx["gst"]), (4140.0, 745.2))      # plan example: 180 kg x 23.00
        _, ctx = engine.validate(c, q["OP-12"])
        self.assertEqual(ctx["amount"], 8000.0)                              # (23-22) x 8000
        self.assertEqual(engine.validate(c, q["DN-5570"])[0], ["AMOUNT_MISMATCH"])

    def test_duplicate_rejected_and_alias(self):
        c = fresh()
        with self.assertRaises(engine.DuplicateNote):
            engine.stage_note(c, "rajesh traders", "HGH/S/1042", "dn-5567", "2026-09-18", "short-qty", short_qty_kg=1, accepted_rate=23)
        self.assertIsNotNone(masters.resolve(c, "party", "RT"))
        _, f = engine.stage_note(c, "Unknown Co", "HGH/S/1042", "X1", "2026-09-19", "short-qty", short_qty_kg=1, accepted_rate=23)
        self.assertIn("NAME_UNRESOLVED", f)

    def test_verify_blocks_flagged_then_edit_fixes(self):
        c = fresh()
        bad = [r for r in engine.queue(c) if r["note_no"] == "DN-5570"][0]["id"]
        with self.assertRaises(ValueError): engine.verify(c, bad)
        self.assertEqual(engine.edit(c, bad, amount=None), [])
        engine.verify(c, bad)

    def test_post_in_date_order_paired_same_date(self):
        c = fresh()
        for r in engine.queue(c):
            if not __import__("json").loads(r["flags"]): engine.verify(c, r["id"])
        res = engine.post_batch(c)
        self.assertEqual([p["date"] for p in res["posted"]], ["2026-09-16", "2026-09-18"])   # date order, not arrival order
        self.assertEqual([p["cn"] for p in res["posted"]], ["CN/1", "CN/2"])
        for l in recon.linkage(c):
            self.assertTrue(l["party_cn"] and l["mill_dn"])
        n = {r["tally_voucher_no"]: r for r in c.execute("SELECT * FROM notes")}
        self.assertEqual(n["CN/1"]["note_date"], n["DN/1"]["note_date"])
        bal = {b["ref_no"]: b["open_balance"] for b in recon.bill_outstanding(c)}
        self.assertEqual(bal["HGH/S/1042"], 303800 - 4140)
        self.assertEqual(bal["HGH/P/0901"], 12400 * 22 - 4140)

    def test_dry_run_changes_nothing_and_running_balance_holds_overclaim(self):
        c = fresh()
        sid, f = engine.stage_note(c, "Rajesh Traders", "HGH/S/1042", "BIG", "2026-09-19", "short-qty", short_qty_kg=12000, accepted_rate=22.0)
        self.assertEqual(f, [])
        engine.verify(c, sid)
        before = recon.bill_outstanding(c)
        engine.post_batch(c, dry_run=True)
        self.assertEqual(recon.bill_outstanding(c), before)
        self.assertEqual(c.execute("SELECT count(*) FROM notes").fetchone()[0], 0)
        # two claims each fine alone (264,000 / 150,000 of 303,800) but not together: second is held at post time
        s2, f2 = engine.stage_note(c, "Rajesh Traders", "HGH/S/1042", "BIG2", "2026-09-20", "short-qty", short_qty_kg=6000, accepted_rate=22.0)
        self.assertEqual(f2, [])
        engine.verify(c, s2)
        res = engine.post_batch(c)
        self.assertEqual(len(res["posted"]), 1)
        self.assertEqual(res["held"][0][0], s2)
        self.assertIn("OVER_ADJUST", res["held"][0][1])
        self.assertEqual(engine.get(c, s2)["review_status"], "pending")      # back in the exceptions queue

    def test_closed_period_hold(self):
        c = fresh()
        engine.close_period(c, "2026-09-17")
        flags = {r["note_no"]: __import__("json").loads(r["flags"]) for r in engine.queue(c)}
        engine.edit(c, 1, note_date="2026-09-18")                # revalidates
        _, f = engine.stage_note(c, "Om Packaging", "HGH/S/1050", "OLD", "2026-09-10", "rate-diff", accepted_rate=22.0)
        self.assertIn("PERIOD_CLOSED", f)

    def test_no_mill_link_blocks_posting(self):
        c = fresh()
        register.add_bill(c, "HGH/S/2000", "sale", "2026-09-20", masters.resolve(c, "party", "Om Packaging")["id"], 1000, 25.0)
        sid, f = engine.stage_note(c, "Om Packaging", "HGH/S/2000", "N1", "2026-09-21", "short-qty", short_qty_kg=10, accepted_rate=25)
        self.assertEqual(f, ["NO_MILL_LINK"])
        with self.assertRaises(ValueError): engine.verify(c, sid)

    def test_mill_cn_gap_and_mismatch(self):
        c = fresh()
        for r in engine.queue(c):
            if not __import__("json").loads(r["flags"]): engine.verify(c, r["id"])
        engine.post_batch(c)
        dns = {r["dn_voucher"]: r for r in recon.pending_mill_cn(c, today=dt.date(2026, 10, 1))}
        self.assertEqual({r["status"] for r in dns.values()}, {"pending"})
        late = recon.pending_mill_cn(c, today=dt.date(2026, 12, 1))
        self.assertEqual({r["status"] for r in late}, {"overdue"})
        d1 = dns["DN/1"]["id"]; d2 = dns["DN/2"]["id"]
        engine.record_mill_cn(c, d1, "MCN-1", "2026-10-05", dns["DN/1"]["amount"])       # next month, right amount
        engine.record_mill_cn(c, d2, "MCN-2", "2026-10-06", 1.0)                         # wrong amount
        st = {r["dn_voucher"]: r["status"] for r in recon.pending_mill_cn(c, today=dt.date(2026, 10, 10))}
        self.assertEqual(st, {"DN/1": "received", "DN/2": "mismatch"})
        gap = {g["month"]: g for g in recon.month_gap(c)}
        self.assertEqual(gap["2026-09"]["debits_raised"], 12140.0)
        self.assertEqual(gap["2026-10"]["cn_received"], round(dns["DN/1"]["amount"] + 1, 2))
        with self.assertRaises(engine.DuplicateNote): engine.record_mill_cn(c, d1, "MCN-9", "2026-10-07", 5)

    def test_tally_xml_balances_and_is_wellformed(self):
        import xml.etree.ElementTree as ET
        c = fresh()
        for r in engine.queue(c):
            if not __import__("json").loads(r["flags"]): engine.verify(c, r["id"])
        engine.post_batch(c)
        root = ET.fromstring(tally.vouchers(c, "H.G. Hawa & Co."))
        vs = root.findall(".//VOUCHER")
        self.assertEqual(len(vs), 4)
        for v in vs:
            self.assertAlmostEqual(sum(float(e.find("AMOUNT").text) * (1 if e.find("ISDEEMEDPOSITIVE").text == "No" else 1)
                                       for e in v.findall("ALLLEDGERENTRIES.LIST")), 0, places=2)   # debits negative, credits positive
            self.assertTrue(any(b.find("BILLTYPE").text == "Agst Ref" for b in v.iter("BILLALLOCATIONS.LIST")))
        tally.mark_exported(c)
        self.assertEqual(len(ET.fromstring(tally.vouchers(c)).findall(".//VOUCHER")), 0)   # never re-exported


if __name__ == "__main__":
    unittest.main()
