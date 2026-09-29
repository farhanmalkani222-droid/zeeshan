"""Message brain: onboarding -> FAQ -> (LLM) -> handoff. Transport-agnostic."""
import re
from . import faq, llm, onboard

BOT_Q = re.compile(r"\b(bot|robot|ai|real\s*(person|insaan|human)|human|insaan|automatic|machine)\b", re.I)
HONEST = "Main {shop} ka automated assistant hoon. Zaroorat ho toh {owner} khud bhi aapse baat kar lenge."
FALLBACK = "Thoda detail bata dein, {owner} isko confirm karke jaldi reply karenge."
FOLLOWUP = "Hello! Aapne {product} ke baare mein poocha tha. Koi aur sawaal ho ya order karna ho toh bata dein."

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
        if onboard.should_onboard(text, prior_count):
            msgs = onboard.messages(self.cfg, text)
        elif BOT_Q.search(text) and len(text.split()) <= 8:
            msgs = [self._fmt(HONEST)]
        else:
            out, ranked = faq.answer(text, self.entries, self.cfg, self.cfg["match_threshold"])
            if out is None:
                hist = self.store.history(uid, self.cfg["history_turns"])
                out = llm.ask(self.cfg, [e for _, e in ranked], hist, text) or self._fmt(FALLBACK)
            msgs = [out]
        for m in msgs:
            self.store.add(uid, "bot", m)
        return msgs

    def followup_text(self):
        return self._fmt(FOLLOWUP)
