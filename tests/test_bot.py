import json, os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from bot import faq
from bot.core import Brain
from bot.store import Store

ROOT = os.path.join(os.path.dirname(__file__), "..")
cfg = json.load(open(f"{ROOT}/config.json")); cfg["llm_enabled"] = False
entries = faq.load(f"{ROOT}/faq.json")

class T(unittest.TestCase):
    def setUp(self):
        self.b = Brain(cfg, entries, Store(tempfile.mktemp()))
    def test_price(self):
        self.assertIn("₹300", self.b.reply("u1", "bhai ye kitne ka hai?"))
    def test_origin_never_leaks_todo(self):
        r = self.b.reply("u1", "maal kahan se aata hai?")
        self.assertNotIn("TODO", r); self.assertIn("confirm", r)
    def test_location(self):
        self.assertIn("Nagpada", self.b.reply("u1", "delivery kaise hoti hai?"))
    def test_city_only_if_configured(self):
        self.assertIn("Mira Road", self.b.reply("u1", "Mira Road delivery kab tak?"))
        self.assertNotIn("Delhi mein hum", self.b.reply("u2", "Delhi delivery kab tak?"))
    def test_honest_about_bot(self):
        self.assertIn("automated", self.b.reply("u1", "are you a bot?"))
    def test_fallback_no_llm(self):
        self.assertIn("confirm", self.b.reply("u1", "xyzzy plugh"))
    def test_handoff_silences(self):
        self.b.reply("u1", "hi"); self.b.store.set_handoff("u1")
        self.assertIsNone(self.b.reply("u1", "price?"))
    def test_followup_due(self):
        self.b.reply("u1", "price"); s = self.b.store
        s.db.execute("UPDATE conv SET last_ts=last_ts-4*3600"); s.db.commit()
        self.assertEqual(s.due_followups(3, 1), ["u1"])
        s.mark_followup("u1"); self.assertEqual(s.due_followups(3, 1), [])
unittest.main()
