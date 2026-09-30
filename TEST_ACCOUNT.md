# Trying the bot with a test account (no risk to @hawa_taps_)

Real DMs only reach a bot that holds a token from Meta. In Meta's app test mode the token works for accounts you list as testers, with no App Review, so this is the safe way to try the bot before customers use it.

1. Make a spare Instagram account (any name). Do NOT use it to log in to any script.
2. In the Meta app (test mode): App roles > Roles > add that spare account as an Instagram Tester, then accept the invite in the spare account (Settings > Apps and websites > Tester invites).
3. Deploy the bot (Render / `render.yaml`) with the four Meta values and `ALLOWED_USER_IDS` left empty for the first message.
4. From the spare account, DM @hawa_taps_. The server log prints `test mode: ignoring message from <ID>` only when the allowlist is set; with it empty the bot just replies.
5. To restrict replies to testers only, set `ALLOWED_USER_IDS=<id1>,<id2>` (the numeric IDs from the log line) and restart. Everyone else is ignored until you clear the variable.
6. Run `python3 check.py https://YOUR-HOST`, then try: "Assalamu alaikum", "kimmat", "size", "10 taps chahiye", "abc xyz".
7. Happy? Clear `ALLOWED_USER_IDS`, request App Review, and go live.

Tip: `python3 chat.py` tests the same replies in the terminal without Instagram.
