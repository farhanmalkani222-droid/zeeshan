"""Review & posting screen (plan Phases 4-5): python3 -m hawapro serve [--port 8765].
Binds 127.0.0.1 by default. Set HAWAPRO_PASSWORD to require HTTP Basic auth (use it if you bind a non-local host)."""
import base64, hmac, html, json, os, secrets, tempfile, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from . import engine, intake, recon, tally
from .db import connect

TOKEN = secrets.token_hex(16)                # CSRF token, per server process
e = html.escape
CSS = ("body{font:14px system-ui;margin:0;background:#f6f7f9;color:#1b1f24}header{background:#14365d;color:#fff;padding:10px 20px}"
       "header a{color:#cfe0f5;margin-right:16px;text-decoration:none}main{padding:20px;max-width:1200px;margin:auto}"
       "table{border-collapse:collapse;width:100%;background:#fff}td,th{border:1px solid #dde1e6;padding:6px 8px;text-align:left}"
       "th{background:#eef1f5}.flag{color:#b42318;font-weight:600}.ok{color:#067647}button{padding:4px 10px;cursor:pointer}"
       "form.inline{display:inline}.card{background:#fff;padding:12px 16px;border:1px solid #dde1e6;margin:12px 0}")


def page(body, msg=""):
    nav = "".join(f'<a href="{u}">{t}</a>' for u, t in [("/", "Queue"), ("/intake", "Intake"), ("/post", "Post"), ("/reports/day-register", "Reports"), ("/mill-cn", "Mill CN")])
    m = f'<div class="card">{e(msg)}</div>' if msg else ""
    return f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width'><title>HAWA PRO</title><style>{CSS}</style><header><b>HAWA PRO</b> &nbsp; {nav}</header><main>{m}{body}</main>"


def tbl(rows, extra=None):
    if not rows: return "<p>(none)</p>"
    cols = list(rows[0])
    h = "".join(f"<th>{e(k)}</th>" for k in cols) + ("<th></th>" if extra else "")
    b = "".join("<tr>" + "".join(f"<td>{e(str(r[k] if r[k] is not None else ''))}</td>" for k in cols) + (f"<td>{extra(r)}</td>" if extra else "") + "</tr>" for r in rows)
    return f"<table><tr>{h}</tr>{b}</table>"


def post_form(action, label, **hidden):
    hid = "".join(f'<input type=hidden name="{k}" value="{e(str(v))}">' for k, v in hidden.items())
    return f'<form class=inline method=post action="{action}"><input type=hidden name=_t value="{TOKEN}">{hid}<button>{label}</button></form>'


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _auth(self):
        pw = os.environ.get("HAWAPRO_PASSWORD")
        if not pw: return True
        got = self.headers.get("Authorization", "")
        ok = got.startswith("Basic ") and hmac.compare_digest(base64.b64decode(got[6:] + "==").decode("utf-8", "replace").split(":", 1)[-1], pw)
        if not ok:
            self.send_response(401); self.send_header("WWW-Authenticate", 'Basic realm="HAWA PRO"'); self.end_headers()
        return ok

    def _send(self, body, ctype="text/html; charset=utf-8", code=200, headers=()):
        b = body.encode() if isinstance(body, str) else body
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(b)))
        for k, v in headers: self.send_header(k, v)
        self.end_headers(); self.wfile.write(b)

    def _redirect(self, to, msg=""):
        self.send_response(303); self.send_header("Location", to + (("?m=" + urllib.parse.quote(msg)) if msg else "")); self.end_headers()

    def do_GET(self):
        if not self._auth(): return
        u = urllib.parse.urlparse(self.path); q = urllib.parse.parse_qs(u.query); msg = q.get("m", [""])[0]
        c = connect()
        try:
            if u.path == "/":
                rows = []
                for r in engine.queue(c):
                    fl, ctx = engine.validate(c, r)
                    amt = r["amount"] if r["amount"] is not None else ctx.get("amount")
                    rows.append({"id": r["id"], "date": r["note_date"], "party": (ctx.get("party") or {"name": r["party_text"]})["name"], "bill": r["bill_ref"],
                                 "note": r["note_no"], "reason": r["reason"], "amount": f"{amt:,.2f}" if amt is not None else "", "gst": f"{ctx['gst']:,.2f}" if "gst" in ctx else "",
                                 "mill": (ctx.get("mill") or {"name": ""})["name"], "conf": r["confidence"], "status": r["review_status"],
                                 "flags": "; ".join(engine.FLAG_TEXT[f] for f in fl)})
                act = lambda r: (post_form("/verify", "Verify", id=r["id"]) if not r["flags"] else f'<span class=flag>held</span>') + " " + post_form("/reject", "Reject", id=r["id"]) + f' <a href="/edit?id={r["id"]}">edit</a>'
                self._send(page("<h2>Staging queue (by note date)</h2>" + tbl(rows, act) + "<p>" + post_form("/verify-all", "Verify all clean notes") + "</p>", msg))
            elif u.path == "/edit":
                r = engine.get(c, int(q["id"][0]))
                fields = "".join(f'<p><label>{k} <input name="{k}" value="{e(str(r[k] if r[k] is not None else ""))}"></label></p>' for k in sorted(engine.EDITABLE))
                self._send(page(f'<h2>Edit #{r["id"]}</h2><p class=flag>{e(", ".join(engine.FLAG_TEXT[f] for f in json.loads(r["flags"])))}</p><form method=post action=/edit><input type=hidden name=_t value="{TOKEN}"><input type=hidden name=id value="{r["id"]}">{fields}<button>Save &amp; revalidate</button></form>'))
            elif u.path == "/intake":
                log = [dict(x) for x in c.execute("SELECT file,status,detail,staging_id,at FROM intake_log ORDER BY at DESC LIMIT 30")] if c.execute("SELECT 1 FROM sqlite_master WHERE name='intake_log'").fetchone() else []
                self._send(page('<h2>Intake</h2><div class=card>Upload debit-note PDF or .txt files (select several):<br><input type=file id=f multiple accept=".pdf,.txt"> '
                                f'<select id=ch><option>mail<option>whatsapp<option>manual</select> <button onclick="up()">Upload</button> <span id=o></span></div>{tbl(log)}'
                                f'<script>async function up(){{let n=0,o=document.getElementById("o");for(const f of document.getElementById("f").files){{let r=await fetch("/upload?name="+encodeURIComponent(f.name)+"&ch="+document.getElementById("ch").value,{{method:"POST",headers:{{"X-CSRF":"{TOKEN}"}},body:f}});o.textContent=(++n)+" done: "+await r.text()}}location.reload()}}</script>', msg))
            elif u.path == "/post":
                res = engine.post_batch(c, dry_run=True)
                self._send(page("<h2>Post preview (dry run)</h2>" + tbl(res["posted"]) + "".join(f'<p class=flag>HELD #{i}: {e(", ".join(f))}</p>' for i, f in res["held"])
                                + "<p>" + post_form("/post", f"Post {len(res['posted'])} paired note(s)") + "</p><p>" + post_form("/export.xml", "Download Tally XML (new vouchers only)") + "</p>", msg))
            elif u.path.startswith("/reports/"):
                name = u.path.split("/", 2)[2]
                if name not in recon.REPORTS: return self._send("not found", code=404)
                nav = " | ".join(f'<a href="/reports/{n}">{n}</a>' for n in sorted(recon.REPORTS))
                self._send(page(f"<p>{nav}</p><h2>{e(name)}</h2>" + tbl(recon.REPORTS[name](c))))
            elif u.path == "/mill-cn":
                dns = [r for r in recon.pending_mill_cn(c) if r["status"] in ("pending", "overdue", "mismatch")]
                form = ('<form method=post action=/mill-cn><input type=hidden name=_t value="%s">Mill debit id <input name=id size=4> CN no <input name=cn_no> date <input name=date placeholder=YYYY-MM-DD> amount <input name=amount size=8> <button>Record mill credit note</button></form>' % TOKEN)
                self._send(page("<h2>Mill credit notes</h2><div class=card>" + form + "</div>" + tbl(dns), msg))
            else:
                self._send("not found", code=404)
        finally:
            c.close()

    def do_POST(self):
        if not self._auth(): return
        u = urllib.parse.urlparse(self.path); n = int(self.headers.get("Content-Length", 0)); raw = self.rfile.read(n)
        c = connect()
        try:
            if u.path == "/upload":
                if not hmac.compare_digest(self.headers.get("X-CSRF", ""), TOKEN): return self._send("bad token", code=403)
                q = urllib.parse.parse_qs(u.query); name = os.path.basename(q.get("name", ["upload"])[0])
                if not name.lower().endswith((".pdf", ".txt")): return self._send("only .pdf/.txt", code=400)
                with tempfile.TemporaryDirectory() as d:
                    p = os.path.join(d, name); open(p, "wb").write(raw)
                    try: r = intake.process_file(c, p, q.get("ch", ["manual"])[0])
                    except Exception as ex: r = ("failed", str(ex))
                c.commit()
                return self._send(f"{name}: {r[0]}" + (f" #{r[1]}" if r[0] != "failed" else f" ({r[1]})"), "text/plain")
            f = {k: v[0] for k, v in urllib.parse.parse_qs(raw.decode()).items()}
            if not hmac.compare_digest(f.get("_t", ""), TOKEN): return self._send("bad token", code=403)
            try:
                if u.path == "/verify": engine.verify(c, int(f["id"])); msg = f"#{f['id']} verified"
                elif u.path == "/reject": engine.reject(c, int(f["id"]), "rejected in UI"); msg = f"#{f['id']} rejected"
                elif u.path == "/verify-all":
                    ok = 0
                    for r in engine.queue(c, ("pending",)):
                        try: engine.verify(c, r["id"]); ok += 1
                        except ValueError: pass
                    msg = f"{ok} verified"
                elif u.path == "/edit":
                    num = {"short_qty_kg", "qty_kg", "accepted_rate", "amount", "gst", "mill_amount"}
                    vals = {k: ((float(v) if v else None) if k in num else (v or None) if k in ("mill_text",) else v) for k, v in f.items() if k in engine.EDITABLE}
                    fl = engine.edit(c, int(f["id"]), **vals); msg = f"#{f['id']} saved; flags: {', '.join(fl) or 'none'}"
                elif u.path == "/post":
                    res = engine.post_batch(c); msg = f"{len(res['posted'])} paired note(s) posted, {len(res['held'])} held"
                elif u.path == "/export.xml":
                    x = tally.vouchers(c, os.environ.get("HAWAPRO_COMPANY")); tally.mark_exported(c); c.commit()
                    return self._send(x, "application/xml", headers=[("Content-Disposition", "attachment; filename=hawapro-vouchers.xml")])
                elif u.path == "/mill-cn":
                    engine.record_mill_cn(c, int(f["id"]), f["cn_no"], f["date"], float(f["amount"])); msg = "mill credit note recorded"
                else: return self._send("not found", code=404)
                c.commit()
            except (ValueError, KeyError, engine.DuplicateNote) as ex:
                c.rollback(); msg = "error: " + str(ex.args[0] if isinstance(ex, KeyError) else ex)
            self._redirect({"/post": "/post", "/mill-cn": "/mill-cn"}.get(u.path, "/"), msg)
        finally:
            c.close()


def serve(host="127.0.0.1", port=8765):
    print(f"HAWA PRO on http://{host}:{port}" + ("  (password required)" if os.environ.get("HAWAPRO_PASSWORD") else ""))
    ThreadingHTTPServer((host, port), H).serve_forever()
