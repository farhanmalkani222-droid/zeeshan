"""Questions the bot could not answer, saved for Ahmed bhai to review.
python3 unanswered.py            # list open ones
python3 unanswered.py --csv      # export
python3 unanswered.py --done 3   # mark #3 resolved (add the answer to faq.json!)"""
import csv, os, sys, time
from bot.store import Store
st = Store(os.environ.get("DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot.db")))
if "--done" in sys.argv:
    st.resolve_unanswered(int(sys.argv[sys.argv.index("--done") + 1])); print("marked resolved"); sys.exit()
rows = st.unanswered()
if "--csv" in sys.argv:
    w = csv.writer(sys.stdout); w.writerow(["id", "time", "instagram_user_id", "question"])
    for i, uid, q, why, ts, _ in rows: w.writerow([i, time.strftime("%Y-%m-%d %H:%M", time.localtime(ts)), uid, q])
else:
    for i, uid, q, why, ts, _ in rows:
        print(f"#{i}  {time.strftime('%Y-%m-%d %H:%M', time.localtime(ts))}  user {uid}\n    {q}")
    print(f"\n{len(rows)} open question(s)" if rows else "No unanswered questions.")
