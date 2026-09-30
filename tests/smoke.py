"""End-to-end: real HTTP server, signed webhook POST, Instagram send mocked."""
import hashlib, hmac, json, os, sys, threading, time, urllib.request
os.environ.update(VERIFY_TOKEN="vt", APP_SECRET="sec", IG_TOKEN="t", IG_ID="1", PORT="8099", HUMAN_TYPING="0")
os.environ.pop("ANTHROPIC_API_KEY", None)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import app
sent = []; app.send = lambda uid, t: sent.append((uid, t))
from http.server import HTTPServer
srv = HTTPServer(("", 8099), app.H); threading.Thread(target=srv.serve_forever, daemon=True).start()
u = "http://localhost:8099/"
assert urllib.request.urlopen(u + "?hub.mode=subscribe&hub.verify_token=vt&hub.challenge=42").read() == b"42"
body = json.dumps({"entry": [{"messaging": [{"sender": {"id": "cust1"}, "message": {"mid": "m1", "text": "kitne ka hai?"}}]}]}).encode()
sig = "sha256=" + hmac.new(b"sec", body, hashlib.sha256).hexdigest()
urllib.request.urlopen(urllib.request.Request(u, body, {"X-Hub-Signature-256": sig}))
try:
    urllib.request.urlopen(urllib.request.Request(u, body, {"X-Hub-Signature-256": "bad"})); assert 0
except urllib.error.HTTPError as e: assert e.code == 403
time.sleep(0.5)
assert len(sent) == 1 and "₹300" in sent[0][1], sent
os.remove(os.path.join(os.path.dirname(app.__file__), "bot.db"))
print("SMOKE OK:", sent[0][1])
