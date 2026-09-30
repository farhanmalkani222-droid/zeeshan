"""Human feel: the bot marks the DM 'Seen' and sends a 'typing_on' bubble before the real reply,
using the official sender_action API. The reply itself is still delivered."""
import hashlib, hmac, json, os, sys, tempfile, threading, time, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
os.environ.update(VERIFY_TOKEN="vt", APP_SECRET="sec", IG_TOKEN="tok", IG_ID="IG1",
                  GRAPH_BASE="http://localhost:8099", DB_PATH=tempfile.mktemp(), HUMAN_TYPING="1")
os.environ.pop("ANTHROPIC_API_KEY", None)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

posts = []
class Graph(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        assert self.path == "/IG1/messages" and self.headers["Authorization"] == "Bearer tok"
        posts.append(body)
        self.send_response(200); self.end_headers()
        self.wfile.write(json.dumps({"message_id": f"mid.bot{len(posts)}"}).encode())
threading.Thread(target=ThreadingHTTPServer(("", 8099), Graph).serve_forever, daemon=True).start()

import app
app.typing_delay = lambda t: 0.0   # keep the test fast; real pauses are covered by config
threading.Thread(target=ThreadingHTTPServer(("", 8098), app.H).serve_forever, daemon=True).start()

def hook(ev):
    body = json.dumps({"entry": [{"messaging": [ev]}]}).encode()
    sig = "sha256=" + hmac.new(b"sec", body, hashlib.sha256).hexdigest()
    urllib.request.urlopen(urllib.request.Request("http://localhost:8098/", body, {"X-Hub-Signature-256": sig}))

hook({"sender": {"id": "A"}, "recipient": {"id": "IG1"}, "message": {"mid": "m1", "text": "size kya hai?"}})
time.sleep(2)
actions = [p["sender_action"] for p in posts if "sender_action" in p]
texts = [p["message"]["text"] for p in posts if "message" in p]
assert "mark_seen" in actions, actions
assert "typing_on" in actions, actions
assert any("half inch" in t for t in texts), texts
print("TYPING OK:", actions, texts)
