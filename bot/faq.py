"""Stage 1: FAQ matching. Costs 0 LLM tokens."""
import difflib, json, re

def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)["entries"]

def _norm(t):
    return " " + re.sub(r"[^\w\s₹]", " ", t.lower()) + " "

def _fuzzy_hit(keyword, tokens):
    k = keyword.lower()
    return len(k) >= 5 and " " not in k and any(
        abs(len(w) - len(k)) <= 2 and difflib.SequenceMatcher(None, w, k).ratio() >= 0.84 for w in tokens)

def score(text, entry):
    t = _norm(text)
    tokens = t.split()
    return sum(1 for k in entry["keywords"] if _norm(k) in t or _fuzzy_hit(k, tokens))

def ranked(text, entries):
    s = sorted(((score(text, e), i, e) for i, e in enumerate(entries)), key=lambda x: (-x[0], x[1]))
    return [(sc, e) for sc, _, e in s if sc > 0]

def city_line(text, cfg):
    """Rapport line, only for cities the owner listed as genuinely shipped to."""
    t = text.lower()
    for c in cfg.get("past_shipment_cities", []):
        if c.lower() in t:
            return f"{c.title()} mein humara maal pehle bhi ja chuka hai. "
    return ""

def answer(text, entries, cfg, threshold=1):
    """Best answer; if the customer asked two things (top two entries tie), answer both."""
    r = ranked(text, entries)
    if not r or r[0][0] < threshold:
        return None, r
    origin = cfg.get("origin") or f"Iske baare mein {cfg['owner_name']} confirm karke batayenge."
    top = [e for sc, e in r if sc == r[0][0] and e["id"] not in ("greeting", "order")][:2] or [r[0][1]]
    fmt = lambda e: e["answer"].format(shop_name=cfg["shop_name"], origin=origin, price=cfg["price"],
                                       shop_location=cfg["shop_location"])
    return " ".join(fmt(e) for e in top), r
