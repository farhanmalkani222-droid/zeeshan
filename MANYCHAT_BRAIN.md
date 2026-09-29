# Own bot + ManyChat (no Meta developer app)

ManyChat connects to Instagram with its own approved Meta app (you only click "Connect Instagram"). For every customer message, ManyChat sends the text to OUR server (`/manychat`) and sends back whatever our bot replies. Typos, two questions in one message, price totals, order capture and owner handoff all come from our code.

Note: ManyChat's "External Request" feature and its exact response format depend on their plan and docs (search "ManyChat External Request" and "dynamic content v2"). Verify on their site before paying.

## 1. Host our server (needs a public HTTPS address)
Deploy this repo (Dockerfile / `render.yaml`). Set only: `MANYCHAT_SECRET=<any long random string>`. No Meta values needed. Check: `https://YOUR-HOST/health` shows `ok`.

## 2. In ManyChat
1. Connect Instagram (Meta's own login screen). Turn on two-factor first.
2. Automation > New > trigger: **Default reply** (runs for every message that no other automation handles).
3. Add action **External Request**:
   - Method: POST, URL: `https://YOUR-HOST/manychat`
   - Header: `X-Bot-Secret: <your MANYCHAT_SECRET>`
   - Body (JSON): `{"user_id": "{{user_id}}", "text": "{{last_input_text}}"}` (use ManyChat's field picker for the two values)
   - Response: use it as the reply (dynamic content, version v2, Instagram).
4. Publish.

## 3. Test
DM @hawa_taps_ from another account: "Assalamu alaikum", "kimmat", "10 taps chahiye". See collected buyers with `python3 orders.py` on the server.

Limits: no 3-hour follow-up in this mode (ManyChat's own Smart Delay can do it), and the bot cannot see Ahmed bhai's manual replies, so pause ManyChat automation for a chat when he takes over.
