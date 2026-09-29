"""Preflight for the real setup: python3 check.py [https://your-host]. Verifies env, token and webhook reachability."""
import json, os, sys, urllib.error, urllib.parse, urllib.request
ok = True
def line(good, msg):
    global ok; ok &= good; print(("PASS  " if good else "FAIL  ") + msg)
for k in ("VERIFY_TOKEN", "APP_SECRET", "IG_TOKEN", "IG_ID"):
    line(bool(os.environ.get(k)), f"env {k} set")
if all(os.environ.get(k) for k in ("IG_TOKEN", "IG_ID")):
    try:
        req = urllib.request.Request("https://graph.instagram.com/v21.0/me?fields=user_id,username",
                                     headers={"Authorization": f"Bearer {os.environ['IG_TOKEN']}"})
        me = json.loads(urllib.request.urlopen(req, timeout=15).read())
        line(True, f"token valid for @{me.get('username')}")
        line(me.get("username") == "hawa_taps_", "token belongs to @hawa_taps_")
        line(str(me.get("user_id")) == os.environ["IG_ID"], "IG_ID matches the token's account")
    except urllib.error.HTTPError as e:
        line(False, f"token rejected by Instagram ({e.code}): {e.read().decode(errors='replace')[:200]}")
    except Exception as e:
        line(False, f"could not reach Instagram: {e}")
if len(sys.argv) > 1 and os.environ.get("VERIFY_TOKEN"):
    host = sys.argv[1].rstrip("/")
    try:
        q = urllib.parse.urlencode({"hub.mode": "subscribe", "hub.verify_token": os.environ["VERIFY_TOKEN"], "hub.challenge": "777"})
        line(urllib.request.urlopen(f"{host}/?{q}", timeout=15).read() == b"777", "webhook verification handshake works")
        line(urllib.request.urlopen(f"{host}/privacy", timeout=15).status == 200, "/privacy page is public")
    except Exception as e:
        line(False, f"host {host} check failed: {e}")
print("\nALL GOOD" if ok else "\nFix the FAIL lines above, then run again.")
sys.exit(0 if ok else 1)
