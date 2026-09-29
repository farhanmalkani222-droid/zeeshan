"""Builds helper.html: an offline reply helper. Paste a customer's message, get the best reply to copy into Instagram.
Rerun after editing config.json or faq.json:  python3 build_helper.py"""
import json, os
from bot import faq, onboard

HERE = os.path.dirname(os.path.abspath(__file__))
cfg = json.load(open(f"{HERE}/config.json", encoding="utf-8"))
entries = faq.load(f"{HERE}/faq.json")
origin = cfg.get("origin") or f"Iske baare mein {cfg['owner_name']} confirm karke batayenge."

data = {
    "entries": [{
        "id": e["id"], "keywords": e["keywords"],
        "answer": e["answer"].format(shop_name=cfg["shop_name"], origin=origin, price=cfg["price"],
                                      shop_location=cfg["shop_location"], city_line="")}
        for e in entries],
    "intro_salam": onboard.messages(cfg, "Assalamu alaikum"),
    "intro_walaikum": onboard.messages(cfg, "walaikum assalam"),
    "greet_salam": onboard.greeting(cfg, "Assalamu alaikum")[0],
    "greet_walaikum": onboard.greeting(cfg, "walaikum assalam")[0],
    "fallback": f"Thoda detail bata dein, {cfg['owner_name']} isko confirm karke jaldi reply karenge.",
    "shop": cfg["shop_name"],
}

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hawa Taps reply helper</title><style>
:root{--bg:#f4f4f6;--card:#fff;--txt:#1c1c1e;--mut:#6b6b70;--acc:#3b6cf6;--line:#dcdce2}
@media(prefers-color-scheme:dark){:root{--bg:#111;--card:#1c1c1e;--txt:#eee;--mut:#9a9aa0;--line:#333}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--txt);font:16px/1.45 system-ui,sans-serif}
main{max-width:720px;margin:0 auto;padding:16px}h1{font-size:20px;margin:4px 0 2px}.sub{color:var(--mut);margin-bottom:14px;font-size:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;margin-bottom:14px}
textarea{width:100%;min-height:90px;border:1px solid var(--line);border-radius:10px;padding:10px;font:inherit;background:var(--bg);color:var(--txt);resize:vertical}
button{font:inherit;border:0;border-radius:10px;padding:10px 14px;background:var(--acc);color:#fff;cursor:pointer}
button.alt{background:transparent;color:var(--acc);border:1px solid var(--acc)}
.row{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
.reply{border:1px solid var(--line);border-radius:10px;padding:10px;margin-top:8px;white-space:pre-wrap;background:var(--bg)}
.tag{font-size:12px;color:var(--mut);margin-top:10px}
</style></head><body><main>
<h1>Hawa Taps reply helper</h1>
<div class="sub">Paste the customer's message, tap Find reply, then Copy and paste it into the Instagram chat. Works offline. Nothing is sent or stored.</div>
<div class="card"><textarea id="in" placeholder="Customer ka message yahan paste karein..."></textarea>
<div class="row"><button onclick="find()">Find reply</button><button class="alt" onclick="clr()">Clear</button></div></div>
<div id="out"></div>
<div class="card"><b>Quick replies</b><div class="row" id="quick"></div></div>
<script>
const D=__DATA__;
const norm=t=>" "+t.toLowerCase().replace(/[^\\p{L}\\p{N}_\\s₹]/gu," ")+" ";
const score=(t,e)=>e.keywords.filter(k=>norm(t).includes(norm(k))).length;
const isWal=t=>/\\b(wa[\\W_]?alai?kum|walaikum|walekum|walikum)/i.test(t);
const isSalam=t=>/\\bassalam|salaam|salam[\\W_]?ale?ku?m|salam\\b/i.test(t);
const GREET=/^\\s*(hi+|hello+|hey+|namaste|salaam|salam|assalam[\\w\\s\\-o]*|walaikum[\\w\\s]*assalam|walaikum|walekum)\\s*[?.! ]*\\s*$/i;
const INTRO=/^\\s*(details?|info|information|inquiry|enquiry|moq|minimum order|tap ke baare mein|nal ke baare mein)\\s*[?.! ]*\\s*$/i;
function replies(text){
  const wal=isWal(text), sal=isSalam(text);
  if(GREET.test(text)) return [{tag:"Greeting",msgs:[sal&&!wal?D.greet_salam:D.greet_walaikum]}];
  if(INTRO.test(text)) return [{tag:"Full intro (send in this order)",msgs:(sal&&!wal)?D.intro_salam:D.intro_walaikum}];
  const r=D.entries.map(e=>({e,s:score(text,e)})).filter(x=>x.s>0).sort((a,b)=>b.s-a.s).slice(0,3);
  if(!r.length) return [{tag:"No match: safe reply",msgs:[D.fallback]}];
  return r.map((x,i)=>({tag:(i?"Other possible: ":"Best match: ")+x.e.id,msgs:[x.e.answer]}));
}
function esc(s){return s.replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]))}
function card(g){return '<div class="card"><div class="tag">'+esc(g.tag)+'</div>'+g.msgs.map(m=>'<div class="reply">'+esc(m)+'</div><div class="row"><button data-m="'+encodeURIComponent(m)+'" onclick="cp(this)">Copy</button></div>').join("")+'</div>'}
function find(){const t=document.getElementById("in").value.trim();if(!t)return;document.getElementById("out").innerHTML=replies(t).map(card).join("")}
function clr(){document.getElementById("in").value="";document.getElementById("out").innerHTML=""}
async function cp(b){const m=decodeURIComponent(b.dataset.m);try{await navigator.clipboard.writeText(m)}catch(e){const t=document.createElement("textarea");t.value=m;document.body.appendChild(t);t.select();document.execCommand("copy");t.remove()}const o=b.textContent;b.textContent="Copied";setTimeout(()=>b.textContent=o,1200)}
document.getElementById("quick").innerHTML=D.entries.map(e=>'<button class="alt" onclick="show(\\''+e.id+'\\')">'+e.id+'</button>').join("");
function show(id){const e=D.entries.find(x=>x.id===id);document.getElementById("out").innerHTML=card({tag:e.id,msgs:[e.answer]})}
document.getElementById("in").addEventListener("keydown",e=>{if(e.key==="Enter"&&(e.ctrlKey||e.metaKey))find()});
</script></main></body></html>"""

open(f"{HERE}/helper.html", "w", encoding="utf-8").write(PAGE.replace("__DATA__", json.dumps(data, ensure_ascii=False)))
print("wrote helper.html with", len(data["entries"]), "answers")
