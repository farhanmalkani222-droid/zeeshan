"""Message brain: onboarding -> FAQ -> (LLM) -> handoff. Transport-agnostic."""
import re
from . import faq, llm, onboard

# Only real "are you a bot / real person?" questions — NOT product words like "automatic tap" or "machine".
BOT_Q = re.compile(
    r"\bare\s+you\s+(a\s+)?(real\s+)?(bot|robot|ai|human|person|machine)"
    r"|\b(tum|tu|aap)\s+(kya\s+)?(ek\s+)?(ai|bot|robot|insaan|human|machine)\b"
    r"|\b(bot|robot|ai|insaan|human|machine)\s+ho(?:\s|\?|$)"
    r"|\breal\s+(person|insaan|human)\b", re.I)
HONEST = "Main {shop} ka automated assistant hoon. Zaroorat ho toh {owner} khud bhi aapse baat kar lenge."
FALLBACK = "Thoda detail bata dein, {owner} isko confirm karke jaldi reply karenge."
FOLLOWUP = "Hello! Aapne {product} ke baare mein poocha tha. Koi aur sawaal ho ya order karna ho toh bata dein."
FOLLOWUP_QUOTE = "Aapne {n} nal ka poocha tha (total ₹{total}). Order confirm karun? Naam, pura address aur pincode bhej dein toh {owner} bhijwa denge."

QTY = re.compile(r"(?<!\d)(\d{1,5})\s*(nal|naal|nals|tap|taps|piece|pieces|pcs|pc)\b", re.I)
PIN = re.compile(r"(?<!\d)\d{6}(?!\d)")
PHONE = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{9}(?!\d)")
QUOTE = "{n} nal ka total ₹{total} hoga (₹{price} per nal). Courier se All India delivery. Order ke liye apna naam, pura address, pincode aur WhatsApp number bhej dein."
ORDER_OK = "Aapka order note kar liya. {owner} confirm karke jaldi aapse contact karenge. Shukriya!"
ORDER_OK_QTY = "Aapka order note kar liya — {n} nal, total ₹{total}. {owner} confirm karke jaldi aapse contact karenge. Shukriya!"
NEED_ADDRESS = "Order note karne ke liye apna pura address aur 6-digit pincode bhi bhej dein, phir {owner} confirm kar denge."

class Brain:
    def __init__(self, cfg, entries, store, on_lead=None):
        self.cfg, self.entries, self.store = cfg, entries, store
        self.on_lead = on_lead  # optional callback(kind, uid, qty, pincode, phone, blob) for real-time owner alerts

    def _fmt(self, s):
        c = self.cfg
        return s.format(shop=c["shop_name"], owner=c["owner_name"], product=c["product"])

    def reply(self, uid, text):
        """Returns list[str] of messages to send, or [] if bot should stay silent."""
        prior_count = self.store.user_message_count(uid)
        history = self.store.history(uid, self.cfg["history_turns"])
        self.store.add(uid, "user", text)
        if self.store.is_handoff(uid):
            return []
        first = onboard.mode(text, prior_count)
        if first == "greet":
            msgs = onboard.greeting(self.cfg, text)
        elif first == "intro":
            msgs = onboard.messages(self.cfg, text)
        elif BOT_Q.search(text):
            msgs = [self._fmt(HONEST)]
        elif PIN.search(text) or PHONE.search(text):
            blob, n, pin, ph = self._collect(uid)
            if pin:  # pincode present -> shippable, confirm the order
                self.store.add_lead(uid, "order", n, pin, ph, blob[:1000])
                self._fire_lead("order", uid, n, pin, ph, blob)
                msgs = [ORDER_OK_QTY.format(owner=self.cfg["owner_name"], n=n, total=n * int(self.cfg["price"]))
                        if n else self._fmt(ORDER_OK)]
            else:  # phone but no address yet -> don't falsely confirm, ask for what's missing
                self.store.add_lead(uid, "interested", n, None, ph, blob[:1000])
                msgs = [self._fmt(NEED_ADDRESS)]
        elif QTY.search(text):
            n = int(QTY.search(text).group(1))
            blob, qn, pin, ph = self._collect(uid)
            self.store.add_lead(uid, "interested", n, pin, ph, blob[:1000])
            msgs = [QUOTE.format(n=n, total=n * int(self.cfg["price"]), price=self.cfg["price"])]
        else:
            out, ranked = faq.answer(text, self.entries, self.cfg, self.cfg["match_threshold"])
            if out is None:
                hist = self.store.history(uid, self.cfg["history_turns"])
                out = llm.ask(self.cfg, [e for _, e in ranked], hist, text) or self._fmt(FALLBACK)
            msgs = [out]
        # Flagship human touch: if the customer names a city Ahmed bhai has really shipped to,
        # open with "yahan pehle bhi maal gaya hai" — once per chat, so it never repeats robotically.
        if first not in ("greet", "intro") and msgs and not self.store.rapport_sent(uid):
            line = faq.city_line(text, self.cfg)
            if line:
                msgs[0] = line + msgs[0]
                self.store.mark_rapport(uid)
        for m in msgs:
            self.store.add(uid, "bot", m)
        return msgs

    def _collect(self, uid):
        """Pull qty/pincode/phone out of everything the customer has said so far (fields can arrive over several messages)."""
        mine = [t for r, t in self.store.history(uid, 20) if r == "user"]
        blob = " | ".join(mine)
        q, pin, ph = QTY.search(blob), PIN.search(blob), PHONE.search(blob)
        return blob, (int(q.group(1)) if q else None), (pin.group(0) if pin else None), (ph.group(0) if ph else None)

    def _fire_lead(self, kind, uid, n, pin, ph, blob):
        if self.on_lead:
            try:
                self.on_lead(kind, uid, n, pin, ph, blob)
            except Exception:
                pass  # a failed alert must never block the customer's reply

    def followup_text(self, uid=None):
        """Quote-aware nudge: if we quoted a quantity, remind them of it; else a generic ping."""
        if uid:
            mine = [l for l in self.store.leads("interested") if l[0] == uid and l[2]]
            if mine:
                n = mine[-1][2]
                return FOLLOWUP_QUOTE.format(n=n, total=n * int(self.cfg["price"]), owner=self.cfg["owner_name"])
        return self._fmt(FOLLOWUP)
