"""ManyChat mode: External Request -> bot brain, no Meta app."""
import json, os, sys, tempfile, threading, urllib.request, urllib.error
os.environ.update(MANYCHAT_SECRET="s3", DB_PATH=tempfile.mktemp())
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import app
from http.server import ThreadingHTTPServer
threading.Thread(target=ThreadingHTTPServer(("", 8095), app.H).serve_forever, daemon=True).start()
def call(body, secret="s3"):
    r = urllib.request.Request("http://localhost:8095/manychat", json.dumps(body).encode(), {"X-Bot-Secret": secret})
    return json.loads(urllib.request.urlopen(r).read())
a = call({"user_id": "1", "text": "Assalamu alaikum"})["content"]["messages"]
assert len(a) == 1 and a[0]["text"].startswith("Walaikum"), a
b = call({"user_id": "1", "text": "kimmat kya hai, size bhi batao"})["content"]["messages"][0]["text"]
assert "₹300" in b and "half inch" in b, b
c = call({"user_id": "1", "text": "details"})  # not first contact -> FAQ answer
try: call({"user_id": "1", "text": "x"}, secret="bad"); assert 0
except urllib.error.HTTPError as e: assert e.code == 403
print("MANYCHAT OK:", b[:50])
