import os, sys, tempfile, threading, unittest, urllib.parse, urllib.request, urllib.error, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from hawapro import bills, engine, intake, recon, tally, web
from hawapro.cli import demo
from hawapro.db import connect

NOTE = """DEBIT NOTE
Debit Note No: DN-7001          Date: 18-09-2026
M/s Rajesh Traders
Against Bill No: HGH/S/1042
Material received short. Short quantity: 180 Kg   Accepted rate: Rs 23.00
Taxable Amount: 4,140.00
GST @18%: 745.20
"""


def mkpdf(path, lines):
    """Minimal single-page PDF with Helvetica text (no external libs)."""
    esc = lambda t: t.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = "BT /F1 11 Tf 40 780 Td 14 TL " + " ".join(f"({esc(l)}) Tj T*" for l in lines) + " ET"
    objs = ["<</Type/Catalog/Pages 2 0 R>>", "<</Type/Pages/Kids[3 0 R]/Count 1>>",
            "<</Type/Page/Parent 2 0 R/MediaBox[0 0 595 842]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>",
            f"<</Length {len(stream)}>>\nstream\n{stream}\nendstream", "<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>"]
    out, offs = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offs.append(len(out)); out += f"{i} 0 obj\n{o}\nendobj\n".encode()
    x = len(out)
    out += f"xref\n0 {len(objs)+1}\n0000000000 65535 f \n".encode() + b"".join(f"{o:010d} 00000 n \n".encode() for o in offs)
    out += f"trailer\n<</Size {len(objs)+1}/Root 1 0 R>>\nstartxref\n{x}\n%%EOF".encode()
    open(path, "wb").write(out)


class Intake(unittest.TestCase):
    def setUp(self):
        os.environ.pop("ANTHROPIC_API_KEY", None)
        self.c = connect(":memory:"); demo(self.c)
        self.d = tempfile.mkdtemp()

    def test_text_and_pdf_extraction_stage_clean_note(self):
        p = os.path.join(self.d, "a.txt"); open(p, "w").write(NOTE)
        r = intake.process_file(self.c, p, "whatsapp")
        self.assertEqual(r[0], "staged"); self.assertEqual(r[2], [])           # validates clean
        row = engine.get(self.c, r[1])
        self.assertEqual((row["party_text"], row["bill_ref"], row["note_date"], row["short_qty_kg"], row["amount"], row["gst"]),
                         ("Rajesh Traders", "HGH/S/1042", "2026-09-18", 180.0, 4140.0, 745.2))
        self.assertEqual(row["source_channel"], "whatsapp")
        self.assertEqual(intake.process_file(self.c, p)[0], "seen")              # idempotent by file hash
        q = os.path.join(self.d, "b.pdf"); mkpdf(q, NOTE.replace("DN-7001", "DN-7002").splitlines())
        r2 = intake.process_file(self.c, q)
        self.assertEqual(r2[0], "staged", r2)
        self.assertEqual(engine.get(self.c, r2[1])["note_no"], "DN-7002")

    def test_alias_party_rate_diff_and_failure(self):
        p = os.path.join(self.d, "c.txt")
        open(p, "w").write("Debit Note No: OP-77\nDate: 16 Sep 2026\nOm Packaging\nInvoice: HGH/S/1050\nRate difference - accepted rate 22.00\n")
        r = intake.process_file(self.c, p)
        self.assertEqual(r[0], "staged"); self.assertEqual(r[2], [])
        self.assertEqual(engine.validate(self.c, engine.get(self.c, r[1]))[1]["amount"], 8000.0)
        bad = os.path.join(self.d, "d.txt"); open(bad, "w").write("hello world")
        r = intake.process_file(self.c, bad); self.assertEqual(r[0], "failed"); self.assertIn("missing", r[1])

    def test_dates(self):
        self.assertEqual(intake.parse_date("5/9/26"), "2026-09-05"); self.assertEqual(intake.parse_date("31-02-2026"), None)


class Bills(unittest.TestCase):
    def test_csv_import(self):
        c = connect(":memory:")
        p = tempfile.mktemp(suffix=".csv")
        open(p, "w").write("ref_no,side,date,party_or_mill,quantity_kg,rate,linked_ref,gst_no\n"
                           "P1,purchase,2026-09-01,Skywin,1000,20,,24ABC\nS1,sale,2026-09-02,New Party,1000,22,P1,\n")
        self.assertEqual(bills.import_csv(c, p, True)[:2], (2, 0))
        self.assertEqual(bills.import_csv(c, p, False), (0, 2, []))                  # idempotent
        open(p, "a").write("S2,sale,2026-09-02,Nobody,1,1,,\n")
        a, s, e = bills.import_csv(c, p, False)
        self.assertEqual((a, s, len(e)), (0, 2, 1))                                  # unknown master reported, not created
        self.assertEqual(c.execute("SELECT linked_ref FROM bills WHERE ref_no='S1'").fetchone()[0], "P1")

    def test_ledger_config_reaches_xml(self):
        c = connect(":memory:"); demo(c)
        from hawapro.db import set_setting; set_setting(c, "ledger_sales_adj", "My Sales Adj")
        for r in engine.queue(c):
            if not json.loads(r["flags"]): engine.verify(c, r["id"])
        engine.post_batch(c)
        self.assertIn("My Sales Adj", tally.vouchers(c))


class Web(unittest.TestCase):
    def test_flow_and_csrf(self):
        path = tempfile.mktemp(); os.environ["HAWAPRO_DB"] = path; os.environ.pop("HAWAPRO_PASSWORD", None)
        c = connect(path); demo(c); c.commit(); c.close()
        srv = web.ThreadingHTTPServer(("127.0.0.1", 0), web.H); port = srv.server_address[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{port}"
        class NoRedir(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *a, **k): return None
        op = urllib.request.build_opener(NoRedir)
        def post(p, data, hdr=None):
            try: return op.open(urllib.request.Request(base + p, urllib.parse.urlencode(data).encode(), hdr or {})).status
            except urllib.error.HTTPError as e: return e.code
        self.assertIn("Staging queue", urllib.request.urlopen(base + "/").read().decode())
        self.assertEqual(post("/verify-all", {"_t": "wrong"}), 403)                  # CSRF enforced
        self.assertEqual(post("/verify-all", {"_t": web.TOKEN}), 303)
        self.assertEqual(post("/post", {"_t": web.TOKEN}), 303)
        for pth in ("/post", "/reports/linkage", "/reports/month-gap", "/mill-cn", "/intake"):
            self.assertEqual(urllib.request.urlopen(base + pth).status, 200)
        self.assertIn("CN/1", urllib.request.urlopen(base + "/reports/linkage").read().decode())
        with self.assertRaises(urllib.error.HTTPError): urllib.request.urlopen(base + "/export.xml")           # no state change via GET
        exp = lambda t: urllib.request.urlopen(urllib.request.Request(base + "/export.xml", urllib.parse.urlencode({"_t": t}).encode()))
        with self.assertRaises(urllib.error.HTTPError): exp("bad")
        self.assertEqual(exp(web.TOKEN).read().decode().count("<VOUCHER "), 4)
        self.assertEqual(exp(web.TOKEN).read().decode().count("<VOUCHER "), 0)   # exported once
        up = urllib.request.Request(base + "/upload?name=n.txt&ch=mail", NOTE.replace("DN-7001", "DN-9").encode(), {"X-CSRF": web.TOKEN})
        os.environ.pop("ANTHROPIC_API_KEY", None)
        self.assertIn("staged", urllib.request.urlopen(up).read().decode())
        srv.shutdown(); srv.server_close()

    def test_password(self):
        os.environ["HAWAPRO_PASSWORD"] = "pw"; os.environ["HAWAPRO_DB"] = tempfile.mktemp()
        srv = web.ThreadingHTTPServer(("127.0.0.1", 0), web.H); port = srv.server_address[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        with self.assertRaises(urllib.error.HTTPError) as cm: urllib.request.urlopen(f"http://127.0.0.1:{port}/")
        self.assertEqual(cm.exception.code, 401)
        import base64
        r = urllib.request.Request(f"http://127.0.0.1:{port}/", headers={"Authorization": "Basic " + base64.b64encode(b"u:pw").decode()})
        self.assertEqual(urllib.request.urlopen(r).status, 200)
        os.environ.pop("HAWAPRO_PASSWORD"); srv.shutdown(); srv.server_close()


if __name__ == "__main__":
    unittest.main()
