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
    def test_rapport_fires_on_any_question_not_just_delivery(self):
        c2 = dict(cfg, past_shipment_cities=["mira road"])
        b2 = Brain(c2, entries, Store(tempfile.mktemp()))
        self.assertIn("pehle bhi", ' '.join(b2.reply("u1", "Mira Road se hoon, price kya hai?")))
    def test_rapport_only_once_per_chat(self):
        c2 = dict(cfg, past_shipment_cities=["mira road"])
        b2 = Brain(c2, entries, Store(tempfile.mktemp()))
        self.assertIn("pehle bhi", ' '.join(b2.reply("u1", "Mira Road delivery?")))
        self.assertNotIn("pehle bhi", ' '.join(b2.reply("u1", "Mira Road warranty milti hai?")))  # not repeated
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
    def test_typo_tolerant(self):
        self.assertIn("₹300", ' '.join(self.b.reply("u1", "bhai kimmat kya hai")))
        self.assertIn("warranty", ' '.join(self.b.reply("u2", "warrenty milti hai?")).lower())
    def test_two_questions_one_reply(self):
        r = ' '.join(self.b.reply("u1", "price aur size batao"))
        self.assertIn("₹300", r); self.assertIn("half inch", r)
    def test_quantity_quote(self):
        r = ' '.join(self.b.reply("u1", "10 taps chahiye"))
        self.assertIn("₹3000", r)
        self.assertEqual(self.b.store.leads("interested")[0][2], 10)
    def test_order_lead_saved(self):
        self.b.reply("u1", "50 nal chahiye")
        r = ' '.join(self.b.reply("u1", "Ali Khan, Bhiwandi, 421302, 9876543210"))
        self.assertIn("order note", r)
        lead = self.b.store.leads("order")[0]
        self.assertEqual((lead[2], lead[3], lead[4]), (50, "421302", "9876543210"))
    def test_honest_about_bot(self):
        self.assertIn("automated", ' '.join(self.b.reply("u1", "are you a bot?")))
    def test_honest_about_bot_hinglish(self):
        self.assertIn("automated", ' '.join(self.b.reply("u1", "tum insaan ho ya robot?")))
    def test_product_words_do_not_trigger_bot_disclosure(self):
        # "automatic"/"machine" are product talk, not identity questions
        self.assertNotIn("automated", ' '.join(self.b.reply("u1", "ye automatic tap hai kya?")))
        self.assertNotIn("automated", ' '.join(self.b.reply("u2", "machine se banta hai kya?")))
    def test_phone_only_asks_for_address_not_confirm(self):
        self.b.reply("u1", "10 nal chahiye")
        r = ' '.join(self.b.reply("u1", "mera number 9876543210"))
        self.assertIn("pincode", r.lower()); self.assertNotIn("order note", r)
        self.assertEqual(self.b.store.leads("order"), [])  # not confirmed yet
    def test_order_confirmed_with_total_when_pincode_arrives(self):
        self.b.reply("u1", "10 nal chahiye"); self.b.reply("u1", "9876543210")
        r = ' '.join(self.b.reply("u1", "Ali Khan, Bhiwandi 421302"))
        self.assertIn("order note", r); self.assertIn("₹3000", r)
        lead = self.b.store.leads("order")[0]
        self.assertEqual((lead[2], lead[3], lead[4]), (10, "421302", "9876543210"))
    def test_quote_aware_followup(self):
        self.b.reply("u1", "20 nal chahiye")
        r = self.b.followup_text("u1")
        self.assertIn("20 nal", r); self.assertIn("₹6000", r)
    def test_generic_followup_without_quote(self):
        self.b.reply("u1", "hello")
        self.assertNotIn("nal ka poocha", self.b.followup_text("u1"))
    def test_owner_alerted_on_order(self):
        fired = []
        b = Brain(cfg, entries, Store(tempfile.mktemp()), on_lead=lambda *a: fired.append(a))
        b.reply("u1", "5 nal chahiye"); b.reply("u1", "Ali, Mumbai, 400001")
        self.assertTrue(fired and fired[-1][0] == "order" and fired[-1][3] == "400001")
    def test_unanswered_question_saved(self):
        self.b.reply("u1", "xyzzy plugh kya aap gold plated tap banate ho")
        q = self.b.store.unanswered()
        self.assertEqual(len(q), 1); self.assertIn("gold plated", q[0][2])
    def test_answered_question_not_saved(self):
        self.b.reply("u1", "price?"); self.assertEqual(self.b.store.unanswered(), [])
    def test_llm_unsure_is_saved(self):
        from bot import llm
        old = llm.ask; llm.ask = lambda *a, **k: "UNSURE"
        try:
            c2 = dict(cfg, chat_mode=True)
            b2 = Brain(c2, entries, Store(tempfile.mktemp()))
            r = ' '.join(b2.reply("u1", "kya ye tap NASA approved hai?"))
            self.assertIn("confirm", r); self.assertEqual(len(b2.store.unanswered()), 1)
        finally: llm.ask = old
    def test_chat_mode_llm_answer_used(self):
        from bot import llm
        old = llm.ask; llm.ask = lambda *a, **k: "Ji bilkul, bata dijiye."
        try:
            b2 = Brain(dict(cfg, chat_mode=True), entries, Store(tempfile.mktemp()))
            self.assertIn("Ji bilkul", ' '.join(b2.reply("u1", "mujhe masjid ke liye advice chahiye")))
            self.assertEqual(b2.store.unanswered(), [])
        finally: llm.ask = old
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
