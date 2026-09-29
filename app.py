"""Instagram DM webhook server using Meta's OFFICIAL Instagram Messaging API (no scraping/unofficial login).
Env: VERIFY_TOKEN, APP_SECRET, IG_TOKEN (page/IG access token), IG_ID (IG business account id),
     optional ANTHROPIC_API_KEY, PORT."""
import hashlib, hmac, json, os, threading, time, urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from bot import faq
from bot.core import Brain
from bot.store import Store

HERE = os.path.dirname(os.path.abspath(__file__))
cfg = json.load(open(os.path.join(HERE, "config.json"), encoding="utf-8"))
brain = Brain(cfg, faq.load(os.path.join(HERE, "faq.json")), Store(os.path.join(HERE, "bot.db")))

def send(uid, text):
    url = f"https://graph.instagram.com/v21.0/{os.environ['IG_ID']}/messages"
    body = json.dumps({"recipient": {"id": uid}, "message": {"text": text}}).encode()
    req = urllib.request.Request(url, body, {"Authorization": f"Bearer {os.environ['IG_TOKEN']}",
                                             "Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=15).read()

def handle(payload):
    for entry in payload.get("entry", []):
        for ev in entry.get("messaging", []):
            m = ev.get("message")
            if not m or m.get("is_echo"):
                # owner typing manually from the app => pause bot for that customer
                if m and m.get("is_echo"):
                    brain.store.set_handoff(ev["recipient"]["id"])
                continue
            if brain.store.seen(m.get("mid", "")) or not m.get("text"):
                continue
            uid = ev["sender"]["id"]
            out = brain.reply(uid, m["text"])
            if out:
                send(uid, out)

def followup_loop():
    while True:
        time.sleep(600)
        for uid in brain.store.due_followups(cfg["followup_after_hours"], cfg["followup_max"]):
            try:
                send(uid, brain.followup_text()); brain.store.mark_followup(uid)
            except Exception as e:
                print("followup error:", e)

class H(BaseHTTPRequestHandler):
    def do_GET(self):  # Meta webhook verification
        q = parse_qs(urlparse(self.path).query)
        ok = q.get("hub.verify_token", [""])[0] == os.environ.get("VERIFY_TOKEN") and q.get("hub.mode") == ["subscribe"]
        self.send_response(200 if ok else 403); self.end_headers()
        if ok: self.wfile.write(q["hub.challenge"][0].encode())

    def do_POST(self):
        raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        sig = self.headers.get("X-Hub-Signature-256", "")
        exp = "sha256=" + hmac.new(os.environ["APP_SECRET"].encode(), raw, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, exp):
            self.send_response(403); self.end_headers(); return
        self.send_response(200); self.end_headers()
        threading.Thread(target=handle, args=(json.loads(raw),), daemon=True).start()

if __name__ == "__main__":
    threading.Thread(target=followup_loop, daemon=True).start()
    HTTPServer(("", int(os.environ.get("PORT", 8080))), H).serve_forever()
