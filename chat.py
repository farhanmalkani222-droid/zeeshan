"""Talk to the Hawa Taps bot in the terminal, exactly as a customer would on Instagram.  python3 chat.py"""
import json, os, tempfile
from bot import faq
from bot.core import Brain
from bot.store import Store

HERE = os.path.dirname(os.path.abspath(__file__))
cfg = json.load(open(f"{HERE}/config.json", encoding="utf-8"))
if not os.environ.get("ANTHROPIC_API_KEY"):
    cfg["llm_enabled"] = False
brain = Brain(cfg, faq.load(f"{HERE}/faq.json"), Store(tempfile.mktemp()))
print(f"{cfg['shop_name']} bot (type a customer message, empty line to quit)")
while True:
    try:
        text = input("customer> ").strip()
    except EOFError:
        break
    if not text:
        break
    for m in brain.reply("local", text) or ["(bot stays silent)"]:
        print("  bot>", m)
