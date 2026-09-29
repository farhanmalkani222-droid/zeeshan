"""Stage 1: FAQ matching. Costs 0 LLM tokens."""
import json, re

def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)["entries"]

def _norm(t):
    return " " + re.sub(r"[^\w\s₹]", " ", t.lower()) + " "

def score(text, entry):
    t = _norm(text)
    return sum(1 for k in entry["keywords"] if _norm(k) in t)

def ranked(text, entries):
    s = sorted(((score(text, e), i, e) for i, e in enumerate(entries)), key=lambda x: (-x[0], x[1]))
    return [(sc, e) for sc, _, e in s if sc > 0]

def city_line(text, cfg):
    t = text.lower()
    for c in cfg["served_cities"]:
        if c in t:
            # only states what is in config; owner controls this list
            return f"{c.title()} mein hum deliver karte hain. "
    return ""

def answer(text, entries, cfg, threshold=1):
    r = ranked(text, entries)
    if not r or r[0][0] < threshold:
        return None, r
    a = r[0][1]["answer"].format(shop_name=cfg["shop_name"], origin=cfg["origin"],
                                 city_line=city_line(text, cfg))
    return a, r
