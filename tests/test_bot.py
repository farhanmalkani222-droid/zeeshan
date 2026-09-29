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
        self.assertIn("₹300", ' '.join(self.b.reply("u1", "bhai ye kitne ka hai?")))
    def test_origin(self):
        r = ' '.join(self.b.reply("u1", "maal kahan se aata hai?"))
        self.assertIn("Taloja MIDC", r); self.assertNotIn("TODO", r)
    def test_delivery_all_india(self):
        r = ' '.join(self.b.reply("u1", "Delhi delivery hoti hai?"))
        self.assertIn("All India", r)
    def test_rapport_only_if_configured(self):
        self.assertNotIn("pehle bhi", ' '.join(self.b.reply("u1", "Mira Road delivery hoti hai?")))
        c2 = dict(cfg, past_shipment_cities=["mira road"])
        b2 = Brain(c2, entries, Store(tempfile.mktemp()))
        self.assertIn("Mira Road mein humara maal pehle bhi", ' '.join(b2.reply("u1", "Mira Road delivery hoti hai?")))
    def test_size(self):
        self.assertIn("half inch", ' '.join(self.b.reply("u1", "naal ka size kya hai?")).lower())
    def test_material(self):
        r = ' '.join(self.b.reply("u1", "material kya hai?"))
        self.assertIn("ABS", r); self.assertIn("aluminium", r.lower())
    def test_strength(self):
        self.assertIn("70", ' '.join(self.b.reply("u1", "kitna mazboot hai?")))
    def test_onboard_four_messages(self):
        msgs = self.b.reply("u1", "details")
        self.assertEqual(len(msgs), 4)
        self.assertIn("₹300", msgs[0])
        self.assertIn("Nagpada", msgs[1]); self.assertIn("Taloja", msgs[1])
        self.assertIn("warranty", msgs[2].lower())
        self.assertIn("ABS", msgs[3]); self.assertIn("aluminium", msgs[3].lower())
    def test_salam_opener(self):
        m = self.b.reply("u1", "Assalamu alaikum")
        self.assertTrue(m[0].startswith("Walaikum"))
    def test_walaikum_opener(self):
        m = self.b.reply("u1", "walaikum assalam")
        self.assertTrue(m[0].startswith("Assalam"))
    def test_onboard_only_on_first(self):
        self.b.reply("u1", "hi")
        self.assertEqual(len(self.b.reply("u1", "price?")), 1)
    def test_greeting_only_greets(self):
        m = self.b.reply("u1", "hi")
        self.assertEqual(len(m), 1); self.assertNotIn("₹", m[0])
    def test_price_answers_only_price(self):
        m = self.b.reply("u1", "price?")
        self.assertEqual(len(m), 1); self.assertIn("₹300", m[0]); self.assertNotIn("warranty", m[0].lower())
    def test_honest_about_bot(self):
        self.assertIn("automated", ' '.join(self.b.reply("u1", "are you a bot?")))
    def test_fallback_no_llm(self):
        self.assertIn("confirm", ' '.join(self.b.reply("u1", "xyzzy plugh")))
    def test_handoff_silences(self):
        ' '.join(self.b.reply("u1", "hi")); self.b.store.set_handoff("u1")
        self.assertEqual([], self.b.reply("u1", "price?"))
    def test_followup_due(self):
        ' '.join(self.b.reply("u1", "price")); s = self.b.store
        s.db.execute("UPDATE conv SET last_ts=last_ts-4*3600"); s.db.commit()
        self.assertEqual(s.due_followups(3, 1), ["u1"])
        s.mark_followup("u1"); self.assertEqual(s.due_followups(3, 1), [])
unittest.main()
