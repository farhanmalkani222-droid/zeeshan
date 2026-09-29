# Hawa Taps Instagram DM bot

Replies to DMs on @hawa_taps_ through Meta's **official** Instagram Messaging API (no scraping, no unofficial login).

## How it replies
1. First greeting/inquiry -> 4 short messages (price + delivery, locations, warranty, material + Amazon comparison).
2. Everything else -> `faq.json` keyword match (0 tokens).
3. No match -> one Claude Haiku call (<=150 output tokens), else "Ahmed bhai confirm karke batayenge".
4. Customer silent 3h -> one follow-up. Ahmed bhai types manually -> bot goes quiet for that customer.
5. Photos/voice notes -> polite "Ahmed bhai dekhenge". Safety cap: 40 bot messages/customer/hour.

## Extra powers
- Typo-tolerant matching (kimmat, warrenty, mazbut all work) and two questions in one message get both answers.
- Customer says a quantity ("10 taps chahiye") -> bot quotes the total (10 x price) and asks for name, address, pincode.
- Customer sends pincode or phone -> order saved. See buyers with `python3 orders.py` (or `--csv`).
- Try the bot in the terminal: `python3 chat.py`.

## No Meta app? ManyChat mode
See `MANYCHAT_BRAIN.md`: ManyChat handles the Instagram connection, our bot answers via `POST /manychat` (env `MANYCHAT_SECRET` only).

## Setup (one time, ~30 min)
1. Instagram account must be **Business/Creator** (Settings > Account type).
2. developers.facebook.com > Create App (Business) > add **Instagram** product > *API setup with Instagram login*.
3. Add the @hawa_taps_ account, generate a token with `instagram_business_basic` and `instagram_business_manage_messages`. Copy the token (`IG_TOKEN`) and account id (`IG_ID`). App secret is under App settings > Basic (`APP_SECRET`).
4. Deploy (any host with HTTPS: Railway, Render, Fly, VPS):
   `docker build -t hawa . && docker run -p 8080:8080 -v hawa-data:/data --env-file .env hawa`
   Keep a persistent volume at `/data` so history survives restarts. Copy `.env.example` to `.env` and fill it.
5. In Meta dashboard > Webhooks: callback URL `https://YOUR-HOST/`, verify token = `VERIFY_TOKEN`, subscribe to **messages**.
6. Instagram app: Settings > Messages > allow access to connected tools. Send a DM from another account to test.
7. Privacy policy URL for App Review: `https://YOUR-HOST/privacy` (served from `privacy.html`; edit if details change).
8. Go live: Meta App Review for `instagram_business_manage_messages` is required before non-tester customers get replies (Advanced Access).

## Verify it is really working
- Before deploying: `python3 tests/e2e_mock.py` (full flow against a fake Meta server).
- After deploying: set the env vars locally and run `python3 check.py https://YOUR-HOST` (checks token, account, webhook handshake, /privacy).
- One-click host: `render.yaml` is a Render blueprint (Docker + persistent disk).

## Editing
- Prices/addresses/warranty: `config.json`. Answers: `faq.json`. Restart after edits.
- `past_shipment_cities`: only cities Ahmed bhai confirms; enables the "pehle bhi maal gaya" line.

## Cost
FAQ hits and onboarding cost 0 tokens. A fallback is roughly 250-450 input + <=150 output tokens. Set `llm_enabled:false` for pure FAQ.

## Tests
`python3 tests/test_bot.py` and `python3 tests/smoke.py`. Health check: `GET /health`.
