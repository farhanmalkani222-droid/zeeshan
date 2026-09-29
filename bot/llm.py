"""Stage 2 (only when FAQ has no confident match): one small Claude Haiku call.
Token-saving choices: tiny system prompt, only top-3 FAQ entries, last N turns, max_tokens cap."""
import json, os, urllib.request

SYSTEM = ("You reply to Instagram DMs for {shop}, a {product} seller. Reply in the customer's language "
          "(Hinglish/Hindi/English), 1-2 short friendly sentences. Use ONLY the facts given below; if unsure, "
          "say {owner} will confirm shortly. Never invent prices, locations, past orders or origin. "
          "Never claim to be a human; if asked, say you're {shop}'s automated assistant.\nFacts:\n{facts}")

def ask(cfg, top_entries, history, user_text):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key or not cfg.get("llm_enabled"):
        return None
    facts = "\n".join(f"- {e['answer']}" for e in top_entries[:3]) or "- (no matching FAQ)"
    facts += f"\n- Origin: {cfg['origin']}\n- Served cities: {', '.join(cfg['served_cities'])}"
    sys_p = SYSTEM.format(shop=cfg["shop_name"], product=cfg["product"], owner=cfg["owner_name"], facts=facts)
    msgs = [{"role": "user" if r == "user" else "assistant", "content": t} for r, t in history]
    if not msgs or msgs[-1]["role"] != "user":
        msgs.append({"role": "user", "content": user_text})
    body = {"model": cfg["llm_model"], "max_tokens": cfg["llm_max_output_tokens"],
            "system": [{"type": "text", "text": sys_p}], "messages": msgs}
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", json.dumps(body).encode(),
        {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r)["content"][0]["text"].strip()
    except Exception as e:
        print("llm error:", e)
        return None
