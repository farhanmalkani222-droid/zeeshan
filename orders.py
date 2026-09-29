"""Show buyers the bot collected.  python3 orders.py [--csv]"""
import csv, os, sys, time
from bot.store import Store
rows = Store(os.environ.get("DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot.db"))).leads()
head = ["time", "instagram_user_id", "status", "qty", "pincode", "phone", "chat"]
out = [[time.strftime("%Y-%m-%d %H:%M", time.localtime(ts)), uid, st, q or "", pin or "", ph or "", d]
       for uid, st, q, pin, ph, d, ts in rows]
if "--csv" in sys.argv:
    csv.writer(sys.stdout).writerows([head] + out)
else:
    for r in out:
        print(f"{r[0]}  user {r[1]}  [{r[2]}]  qty={r[3] or '?'}  pincode={r[4] or '?'}  phone={r[5] or '?'}\n    {r[6][:160]}")
    print(f"\n{len(out)} lead(s)" if out else "No leads yet.")
