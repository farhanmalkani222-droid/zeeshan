# Instagram DM Auto-Reply Bot (Ahmed Taps)

Replies to customer DMs from the shop's own Instagram account and sends one follow-up if the customer goes silent.
Uses Meta's **official Instagram Messaging API** (webhook + Send API). No scraping, no unofficial login.

## How it works
1. Customer DM -> webhook (`app.py`, signature verified).
2. `bot/faq.py` matches keywords against `faq.json` -> instant answer, **0 tokens**.
3. No match -> one small Claude Haiku call (`bot/llm.py`). No key / disabled -> polite "Ahmed bhai will confirm" reply.
4. If the customer asks "bot ho?", it answers honestly. It never invents prices, cities, past orders or origin.
5. If the owner replies manually from the app, the bot goes silent for that customer.
6. Follow-up: one fixed template message after `followup_after_hours`, only inside Meta's 24h window.

## Setup
1. Instagram Business/Creator account linked to a Facebook Page; create a Meta app, add Instagram messaging, get `IG_TOKEN` and `IG_ID`.
2. Webhook callback URL = `https://<your-host>/`, subscribe to `messages`.
3. Env vars: `VERIFY_TOKEN`, `APP_SECRET`, `IG_TOKEN`, `IG_ID`, optional `ANTHROPIC_API_KEY`, `PORT`.
4. Fill real data: `faq.json` (prices/answers), `config.json` (`origin` from Faisal sir, `served_cities`).
5. `python3 app.py` (tests: `python3 tests/test_bot.py`).

## Where tokens get used (and how much)
| Step | Tokens |
|---|---|
| FAQ match (most messages) | 0 |
| Follow-up message (template) | 0 |
| FAQ miss -> Haiku call | ~250-450 in + <=150 out |

Grows with: `history_turns`, longer FAQ text sent as facts (only top-3 sent), `llm_max_output_tokens`, using a bigger model, and how often FAQ misses.
Reduce: add more keywords to `faq.json`, lower `history_turns`, or set `"llm_enabled": false`.
