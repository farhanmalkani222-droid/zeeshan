"""Message brain: onboarding -> FAQ -> (LLM) -> handoff. Transport-agnostic."""
import re
from . import faq, llm, onboard

BOT_Q = re.compile(r"\b(bot|robot|ai|real\s*(person|insaan|human)|human|insaan|automatic|machine)\b", re.I)
HONEST = "Main {shop} ka automated assistant hoon. Zaroorat ho toh {owner} khud bhi aapse baat kar lenge."
FALLBACK = "Thoda detail bata dein, {owner} isko confirm karke jaldi reply karenge."
FOLLOWUP = "Hello! Aapne {product} ke baare mein poocha tha. Koi aur sawaal ho ya order karna ho toh bata dein."

QTY = re.compile(r"(?<!\d)(\d{1,5})\s*(nal|naal|nals|tap|taps|piece|pieces|pcs|pc)\b", re.I)
PIN = re.compile(r"(?<!\d)\d{6}(?!\d)")
PHONE = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{9}(?!\d)")
QUOTE = "{n} nal ka total ₹{total} hoga (₹{price} per nal). Courier se All India delivery. Order ke liye apna naam, pura address aur pincode bhej dein."
ORDER_OK = "Aapka order note kar liya. {owner} confirm karke jaldi aapse contact karenge. Shukriya!"

class Brain:
    def __init__(self, cfg, entries, store):
        self.cfg, self.entries, self.store = cfg, entries, store

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
        elif BOT_Q.search(text) and len(text.split()) <= 8:
            msgs = [self._fmt(HONEST)]
        elif PIN.search(text) or PHONE.search(text):
            self._save_lead(uid, text, "order")
            msgs = [self._fmt(ORDER_OK)]
        elif QTY.search(text):
            n = int(QTY.search(text).group(1))
            self._save_lead(uid, text, "interested")
            msgs = [QUOTE.format(n=n, total=n * int(self.cfg["price"]), price=self.cfg["price"])]
        else:
            out, ranked = faq.answer(text, self.entries, self.cfg, self.cfg["match_threshold"])
            if out is None:
                hist = self.store.history(uid, self.cfg["history_turns"])
                out = llm.ask(self.cfg, [e for _, e in ranked], hist, text) or self._fmt(FALLBACK)
            msgs = [out]
        for m in msgs:
            self.store.add(uid, "bot", m)
        return msgs

    def _save_lead(self, uid, text, status):
        mine = [t for r, t in self.store.history(uid, 12) if r == "user"]
        blob = " | ".join(mine)
        q, pin, ph = QTY.search(blob), PIN.search(blob), PHONE.search(blob)
        self.store.add_lead(uid, status, int(q.group(1)) if q else None,
                            pin.group(0) if pin else None, ph.group(0) if ph else None, blob[:1000])

    def followup_text(self):
        return self._fmt(FOLLOWUP)
