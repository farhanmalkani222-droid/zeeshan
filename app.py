"""Instagram DM webhook server using Meta's OFFICIAL Instagram Messaging API (no scraping/unofficial login).
Env: VERIFY_TOKEN, APP_SECRET, IG_TOKEN, IG_ID (required); ANTHROPIC_API_KEY, PORT, DB_PATH (optional)."""
import hashlib, hmac, json, logging, os, sys, threading, time, urllib.error, urllib.request
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from bot import faq
from bot.core import Brain
from bot.store import Store

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("hawa")

HERE = os.path.dirname(os.path.abspath(__file__))
cfg = json.load(open(os.path.join(HERE, "config.json"), encoding="utf-8"))
brain = Brain(cfg, faq.load(os.path.join(HERE, "faq.json")),
              Store(os.environ.get("DB_PATH", os.path.join(HERE, "bot.db"))))

MEDIA_REPLY = "Aapka message mil gaya. {owner} khud dekh kar jaldi reply karenge. Tab tak koi sawaal ho toh text mein likh dein."
MAX_BOT_MSGS_PER_HOUR = 40
_locks = defaultdict(threading.Lock)

def send(uid, text):
    """Official Send API with retry/backoff. Returns Meta's message id."""
    url = f"https://graph.instagram.com/v21.0/{os.environ['IG_ID']}/messages"
    body = json.dumps({"recipient": {"id": uid}, "message": {"text": text}}).encode()
    for attempt in range(4):
        req = urllib.request.Request(url, body, {"Authorization": f"Bearer {os.environ['IG_TOKEN']}",
                                                 "Content-Type": "application/json"})
        try:
            resp = json.loads(urllib.request.urlopen(req, timeout=15).read() or b"{}")
            brain.store.mark_bot_mid(resp.get("message_id", ""))
            return resp.get("message_id")
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:300]
            if e.code in (400, 401, 403):  # permanent: bad token / outside 24h window / blocked user
                log.error("send failed permanently (%s): %s", e.code, detail); return None
            log.warning("send retry %d (%s): %s", attempt + 1, e.code, detail)
        except Exception as e:
            log.warning("send retry %d: %s", attempt + 1, e)
        time.sleep(2 ** attempt)
    log.error("send gave up for %s", uid)

def handle_event(ev):
    m = ev.get("message")
    if not m:
        return
    if m.get("is_echo"):
        time.sleep(3)  # let send() record the bot's own message id first
        if not brain.store.is_bot_mid(m.get("mid", "")):
            brain.store.set_handoff(ev["recipient"]["id"])  # owner typed manually -> bot goes quiet
            log.info("owner replied manually to %s; bot paused for them", ev["recipient"]["id"])
        return
    if brain.store.seen(m.get("mid", "")):
        return
    uid = ev["sender"]["id"]
    with _locks[uid]:  # keep replies in order if customer sends several messages quickly
        text = m.get("text")
        if text:
            msgs = brain.reply(uid, text)
        elif m.get("attachments") and not brain.store.is_handoff(uid):
            msgs = [MEDIA_REPLY.format(owner=cfg["owner_name"])]
            brain.store.add(uid, "user", "[media]"); brain.store.add(uid, "bot", msgs[0])
        else:
            return
        if msgs and brain.store.bot_sent_since(uid, 3600) > MAX_BOT_MSGS_PER_HOUR:
            log.warning("rate cap hit for %s; staying silent", uid); return
        for i, msg in enumerate(msgs):
            if i: time.sleep(1.2)
            send(uid, msg)

def handle(payload):
    for entry in payload.get("entry", []):
        for ev in entry.get("messaging", []):
            try:
                handle_event(ev)
            except Exception:
                log.exception("event failed")

def followup_loop():
    while True:
        time.sleep(600)
        try:
            for uid in brain.store.due_followups(cfg["followup_after_hours"], cfg["followup_max"]):
                if send(uid, brain.followup_text()):
                    brain.store.mark_followup(uid)
        except Exception:
            log.exception("followup loop error")

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/health":
            self.send_response(200); self.end_headers(); self.wfile.write(b"ok"); return
        q = parse_qs(u.query)  # Meta webhook verification
        ok = q.get("hub.verify_token", [""])[0] == os.environ.get("VERIFY_TOKEN") and q.get("hub.mode") == ["subscribe"]
        self.send_response(200 if ok else 403); self.end_headers()
        if ok: self.wfile.write(q["hub.challenge"][0].encode())

    def do_POST(self):
        raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        sig = self.headers.get("X-Hub-Signature-256", "")
        exp = "sha256=" + hmac.new(os.environ["APP_SECRET"].encode(), raw, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, exp):
            self.send_response(403); self.end_headers(); return
        try:
            payload = json.loads(raw)
        except ValueError:
            self.send_response(400); self.end_headers(); return
        self.send_response(200); self.end_headers()
        threading.Thread(target=handle, args=(payload,), daemon=True).start()

if __name__ == "__main__":
    missing = [k for k in ("VERIFY_TOKEN", "APP_SECRET", "IG_TOKEN", "IG_ID") if not os.environ.get(k)]
    if missing:
        sys.exit(f"Missing env vars: {', '.join(missing)} (see README.md)")
    threading.Thread(target=followup_loop, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    log.info("Hawa Taps bot listening on :%d", port)
    ThreadingHTTPServer(("", port), H).serve_forever()
