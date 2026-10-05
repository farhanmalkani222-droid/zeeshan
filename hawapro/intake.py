"""Intake layer (plan Phase 3): debit-note PDF/text -> extracted fields -> staging queue.
Extraction is register-guided: known party names/aliases and open sale-bill refs are searched for in the text, so odd
layouts still resolve. If ANTHROPIC_API_KEY is set the Claude pass runs first and regex fills any gaps."""
import hashlib, json, os, re, shutil, subprocess, urllib.request, datetime as dt
from . import engine, masters

NUM = r"([0-9][0-9,]*\.?[0-9]*)"
MONTHS = {m: i for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split(), 1)}
REQUIRED = ("party", "bill_ref", "note_no", "note_date", "reason")


def read_text(path):
    if path.lower().endswith(".pdf"):
        if not shutil.which("pdftotext"):
            raise RuntimeError("pdftotext not installed (poppler-utils); needed to read PDFs")
        return subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True, check=True).stdout
    return open(path, encoding="utf-8", errors="replace").read()


def _num(s):
    return float(s.replace(",", "")) if s else None


def parse_date(s):
    s = s.strip()
    m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})$", s)
    if m: y, mo, d = map(int, m.groups())
    else:
        m = re.match(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})$", s)          # Indian dd-mm-yyyy
        if m:
            d, mo, y = map(int, m.groups()); y += 2000 if y < 100 else 0
        else:
            m = re.match(r"(\d{1,2})[ -]([A-Za-z]{3})[a-z]*[ -,]*(\d{4})$", s)
            if not m: return None
            d, mo, y = int(m.group(1)), MONTHS.get(m.group(2).lower()), int(m.group(3))
    try: return dt.date(y, mo, d).isoformat()
    except (ValueError, TypeError): return None


def extract_regex(c, text):
    """Returns (fields, found_count). Unknown fields are simply absent."""
    f, low = {}, text.lower()
    best = None                                               # longest known party name/alias present wins
    for r in c.execute("SELECT m.id, m.name, a.alias FROM masters m LEFT JOIN aliases a ON a.master_id=m.id WHERE m.kind='party'"):
        for cand in {r["name"].lower(), (r["alias"] or "")}:
            if cand and re.search(r"(?<![a-z0-9])" + re.escape(cand) + r"(?![a-z0-9])", low) and (best is None or len(cand) > len(best[1])):
                best = (r["name"], cand)
    if best: f["party"] = best[0]
    refs = [r["ref_no"] for r in c.execute("SELECT ref_no FROM bills WHERE side='sale'") if r["ref_no"].lower() in low]
    m = re.search(r"(?:bill|invoice|inv)\s*(?:no\.?|number|ref)?\s*[:#-]?\s*([A-Z0-9][A-Z0-9/\-]{3,})", text, re.I)
    f["bill_ref"] = max(refs, key=len) if refs else (m.group(1) if m else None)
    m = re.search(r"(?:debit\s*note|d\.?n\.?)\s*(?:no\.?|number|#)\s*[:#-]?\s*([A-Z0-9][A-Z0-9/\-]*)", text, re.I)
    if m: f["note_no"] = m.group(1)
    m = re.search(r"date\s*[:\-]?\s*(\d{4}-\d{1,2}-\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}|\d{1,2}[ -][A-Za-z]{3,9}[ -,]*\d{4})", text, re.I)
    if m and parse_date(m.group(1)): f["note_date"] = parse_date(m.group(1))
    short = re.search(r"short(?:age)?[^0-9\n]{0,25}?" + NUM + r"\s*(?:kg|kgs)?", text, re.I)
    rated = re.search(r"rate\s*(?:diff(?:erence)?|difference)", text, re.I)
    if short and not rated: f["reason"], f["short_qty_kg"] = "short-qty", _num(short.group(1))
    elif rated: f["reason"] = "rate-diff"
    elif short: f["reason"], f["short_qty_kg"] = "short-qty", _num(short.group(1))
    m = re.search(r"(?:accepted|agreed|settled|correct)\s*rate[^0-9\n]{0,15}" + NUM, text, re.I) or re.search(r"\brate[^0-9\n]{0,10}" + NUM, text, re.I)
    if m: f["accepted_rate"] = _num(m.group(1))
    m = re.search(r"(?:debit\s*)?(?:amount|taxable value|taxable)\s*[:\-]?\s*(?:rs\.?|inr|₹)?\s*" + NUM, text, re.I)
    if m: f["amount"] = _num(m.group(1))
    nopct = re.sub(r"@?\s*\d+(?:\.\d+)?\s*%", " ", text)                  # drop '@18%' so the rupee figure is what matches
    m = re.search(r"(?:gst|igst|cgst\s*\+\s*sgst)[^0-9\n]{0,15}" + NUM, nopct, re.I)
    if m and "amount" in f: f["gst"] = _num(m.group(1))
    mill = None
    for r in c.execute("SELECT m.name, a.alias FROM masters m LEFT JOIN aliases a ON a.master_id=m.id WHERE m.kind='mill'"):
        if any(x and x.lower() in low for x in (r["name"], r["alias"])): mill = r["name"]
    if mill: f["mill"] = mill
    return {k: v for k, v in f.items() if v is not None}


LLM_SYSTEM = ("Extract a party debit note (waste-paper trade, India) into JSON with keys: party, mill, bill_ref (our sale bill/invoice number), "
              "note_no, note_date (YYYY-MM-DD; Indian dates are dd-mm-yyyy), reason ('short-qty' or 'rate-diff'), short_qty_kg, qty_kg, "
              "accepted_rate, amount (taxable), gst (rupees). Omit unknown keys. Output JSON only.")


def extract_llm(text):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return {}
    body = {"model": os.environ.get("HAWAPRO_LLM_MODEL", "claude-haiku-4-5-20251001"), "max_tokens": 600, "system": LLM_SYSTEM,
            "messages": [{"role": "user", "content": text[:8000]}]}
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", json.dumps(body).encode(),
                                 {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = json.load(r)["content"][0]["text"]
        d = json.loads(raw[raw.index("{"):raw.rindex("}") + 1])
        if d.get("note_date"): d["note_date"] = parse_date(str(d["note_date"]))
        return {k: v for k, v in d.items() if v not in (None, "")}
    except Exception as e:
        print("llm extract error:", e)
        return {}


def extract(c, text):
    llm = extract_llm(text)
    rx = extract_regex(c, text)
    f = {**rx, **llm}
    if llm and rx.get("party") and masters.resolve(c, "party", llm.get("party", "")) is None:
        f["party"] = rx["party"]                              # LLM name unknown to masters; trust the register match
    got = sum(1 for k in REQUIRED + ("amount",) if f.get(k) is not None) + (1 if f.get("short_qty_kg") or f.get("accepted_rate") else 0)
    return f, round(got / 7, 2)


def process_file(c, path, channel="manual"):
    """Idempotent by file hash. Returns ('staged', id, flags) | ('failed', reason) | ('seen', id)."""
    c.execute("CREATE TABLE IF NOT EXISTS intake_log (sha TEXT PRIMARY KEY, file TEXT, status TEXT, detail TEXT, staging_id INTEGER, at TEXT DEFAULT CURRENT_TIMESTAMP)")
    sha = hashlib.sha256(open(path, "rb").read()).hexdigest()
    seen = c.execute("SELECT * FROM intake_log WHERE sha=?", (sha,)).fetchone()
    if seen and seen["status"] == "staged":
        return ("seen", seen["staging_id"])
    f, conf = extract(c, read_text(path))
    missing = [k for k in REQUIRED if not f.get(k)]
    if missing:
        c.execute("INSERT OR REPLACE INTO intake_log(sha,file,status,detail) VALUES(?,?,?,?)", (sha, os.path.basename(path), "failed", "missing: " + ",".join(missing)))
        return ("failed", "missing " + ",".join(missing))
    try:
        sid, flags = engine.stage_note(c, f["party"], f["bill_ref"], f["note_no"], f["note_date"], f["reason"], f.get("short_qty_kg"), f.get("qty_kg"),
                                       f.get("accepted_rate"), f.get("amount"), f.get("gst"), f.get("mill"), None, channel, os.path.basename(path), conf)
    except engine.DuplicateNote as e:
        c.execute("INSERT OR REPLACE INTO intake_log(sha,file,status,detail) VALUES(?,?,?,?)", (sha, os.path.basename(path), "duplicate", str(e)))
        return ("failed", str(e))
    c.execute("INSERT OR REPLACE INTO intake_log(sha,file,status,detail,staging_id) VALUES(?,?,?,?,?)", (sha, os.path.basename(path), "staged", f"confidence {conf}", sid))
    return ("staged", sid, flags)


def process_dir(c, folder, channel="manual"):
    out = []
    for n in sorted(os.listdir(folder)):
        if n.lower().endswith((".pdf", ".txt")):
            out.append((n, *process_file(c, os.path.join(folder, n), channel)))
    return out
