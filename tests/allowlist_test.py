import os, sys, tempfile
os.environ.update(VERIFY_TOKEN="v", APP_SECRET="s", IG_TOKEN="t", IG_ID="1", DB_PATH=tempfile.mktemp(), ALLOWED_USER_IDS="111, 222")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import app
sent = []; app.send = lambda uid, t: sent.append(uid)
ev = lambda uid, mid: {"sender": {"id": uid}, "recipient": {"id": "1"}, "message": {"mid": mid, "text": "price?"}}
app.handle_event(ev("999", "a")); assert sent == []          # stranger ignored in test mode
app.handle_event(ev("111", "b")); assert sent == ["111"]     # tester answered
print("ALLOWLIST OK")
