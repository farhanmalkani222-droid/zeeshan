"""End-to-end against a fake Meta Graph server: real HTTP, signed webhooks, real send() path, retry, echo handling."""
import hashlib, hmac, json, os, sys, tempfile, threading, time, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
os.environ.update(VERIFY_TOKEN="vt", APP_SECRET="sec", IG_TOKEN="tok", IG_ID="IG1",
                  GRAPH_BASE="http://localhost:8097", DB_PATH=tempfile.mktemp())
os.environ.pop("ANTHROPIC_API_KEY", None)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

posts, state = [], {"n": 0, "fail_once": True}
class Graph(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if state["fail_once"]:
            state["fail_once"] = False; self.send_response(500); self.end_headers(); return
        assert self.path == "/IG1/messages" and self.headers["Authorization"] == "Bearer tok"
        state["n"] += 1; posts.append(body)
        self.send_response(200); self.end_headers()
        self.wfile.write(json.dumps({"recipient_id": body["recipient"]["id"], "message_id": f"mid.bot{state['n']}"}).encode())
threading.Thread(target=ThreadingHTTPServer(("", 8097), Graph).serve_forever, daemon=True).start()

import app
threading.Thread(target=ThreadingHTTPServer(("", 8096), app.H).serve_forever, daemon=True).start()

def hook(*events):
    body = json.dumps({"entry": [{"messaging": list(events)}]}).encode()
    sig = "sha256=" + hmac.new(b"sec", body, hashlib.sha256).hexdigest()
    urllib.request.urlopen(urllib.request.Request("http://localhost:8096/", body, {"X-Hub-Signature-256": sig}))
def cust(uid, mid, text=None, **kw):
    return {"sender": {"id": uid}, "recipient": {"id": "IG1"}, "message": dict({"mid": mid, **({"text": text} if text else {})}, **kw)}
def to(uid): return [p["message"]["text"] for p in posts if p["recipient"]["id"] == uid]

hook(cust("A", "m1", "Assalamu alaikum")); time.sleep(9)
a = to("A"); assert len(a) == 4 and a[0].startswith("Walaikum") and "₹300" in a[0], a   # incl. one 500 -> retry
n = len(posts); hook(cust("A", "m1", "Assalamu alaikum")); time.sleep(1); assert len(posts) == n  # duplicate ignored

hook({"sender": {"id": "IG1"}, "recipient": {"id": "A"}, "message": {"mid": "mid.bot1", "is_echo": True, "text": "x"}}); time.sleep(4)
hook(cust("A", "m2", "size kya hai?")); time.sleep(1.5)
assert to("A")[-1] == "Naal half inch size ka hai.", to("A")  # bot's own echo did NOT silence it

hook({"sender": {"id": "IG1"}, "recipient": {"id": "A"}, "message": {"mid": "mid.owner9", "is_echo": True, "text": "Ji bhai"}}); time.sleep(4)
n = len(posts); hook(cust("A", "m3", "10 taps chahiye")); time.sleep(1.5)
assert len(posts) == n  # owner replied manually -> bot silent

hook(cust("B", "m4", attachments=[{"type": "image", "payload": {"url": "x"}}])); time.sleep(1.5)
assert "Ahmed bhai" in to("B")[0], to("B")
print("E2E OK:", len(posts), "messages sent via mock Meta API")
