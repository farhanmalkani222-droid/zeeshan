"""Runs the real bot brain on sample chats and writes demo.html (local simulation, not live Instagram)."""
import html, json, os, tempfile
from bot import faq
from bot.core import Brain
from bot.store import Store

HERE = os.path.dirname(os.path.abspath(__file__))
cfg = json.load(open(f"{HERE}/config.json", encoding="utf-8")); cfg["llm_enabled"] = False
entries = faq.load(f"{HERE}/faq.json")

SCENES = [
    ("New customer says salam", [("cust", "Assalamu alaikum")]),
    ("Customer wants general details", [("cust", "details")]),
    ("Customer asks price and size", [("cust", "bhai ye kitne ka hai?"), ("cust", "naal ka size kya hai?")]),
    ("Customer asks about quality and warranty", [("cust", "kitna mazboot hai?"), ("cust", "warranty milti hai?")]),
    ("Customer asks if it is a bot", [("cust", "are you a bot?")]),
    ("Unknown question falls back to owner", [("cust", "xyzzy plugh")]),
    ("Ahmed bhai replies himself, bot goes quiet", [("cust", "hi"), ("owner", "Ji bhai, kitne chahiye?"), ("cust", "10 taps")]),
]

def run():
    out = []
    for i, (title, turns) in enumerate(SCENES):
        b = Brain(cfg, entries, Store(tempfile.mktemp())); uid = f"c{i}"; chat = []
        for who, text in turns:
            if who == "owner":
                b.store.set_handoff(uid); chat.append(("owner", text)); continue
            chat.append(("cust", text))
            replies = b.reply(uid, text)
            chat += [("bot", r) for r in replies]
            if not replies: chat.append(("note", "Bot stays silent: owner is handling this customer"))
        out.append((title, chat))
    return out

def render(scenes):
    cards = ""
    for title, chat in scenes:
        msgs = "".join(f'<div class="m {w}">{html.escape(t)}</div>' for w, t in chat)
        cards += f'<section><h2>{html.escape(title)}</h2><div class="phone">{msgs}</div></section>'
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hawa Taps bot demo</title><style>
:root{{--bg:#f4f4f6;--card:#fff;--txt:#1c1c1e;--cust:#e9e9ee;--bot:#3b6cf6;--owner:#2e9e5b}}
@media(prefers-color-scheme:dark){{:root{{--bg:#111;--card:#1c1c1e;--txt:#eee;--cust:#2c2c30}}}}
body{{margin:0;background:var(--bg);color:var(--txt);font:15px/1.45 system-ui,sans-serif}}
main{{max-width:760px;margin:0 auto;padding:16px}}
h1{{font-size:22px}} .sub{{opacity:.7;margin-bottom:16px}}
section{{background:var(--card);border-radius:14px;padding:14px;margin-bottom:16px}}
h2{{font-size:15px;margin:0 0 10px}}
.phone{{display:flex;flex-direction:column;gap:6px}}
.m{{max-width:82%;padding:8px 12px;border-radius:16px;white-space:pre-wrap}}
.cust{{background:var(--cust);align-self:flex-start}}
.bot{{background:var(--bot);color:#fff;align-self:flex-end}}
.owner{{background:var(--owner);color:#fff;align-self:flex-end}}
.note{{align-self:center;font-size:12px;opacity:.65;font-style:italic}}
</style></head><body><main><h1>Hawa Taps bot: how it replies</h1>
<div class="sub">Grey = customer, blue = bot, green = Ahmed bhai. These replies come from the real bot code running locally. This is a simulation, not live Instagram.</div>
{cards}</main></body></html>"""

if __name__ == "__main__":
    s = run()
    open(f"{HERE}/demo.html", "w", encoding="utf-8").write(render(s))
    for t, c in s:
        print(f"\n== {t}")
        for w, x in c: print(f"  [{w}] {x[:110]}")
