#!/usr/bin/env python3
"""Frontier — magazine-style AI news daily from follow-builders feeds.
Real images (YouTube maxres thumbnails + X avatars), builder field tags,
Editor's Choice notes. No deps, stdlib only.  Run: python3 build.py
"""
import json, re, html, pathlib

FB = pathlib.Path.home() / ".claude/skills/follow-builders"
OUT = pathlib.Path(__file__).resolve().parent
PORTFOLIO = "https://amberhuang.world/"
TWITTER = "https://x.com/amber168196"   # TODO: swap to @hiamberhuang after rename

# Builder field tags — so readers know who's who (handle -> "field · who")
BUILDER_FIELDS = {
    "karpathy": "AI research & education · ex-OpenAI/Tesla",
    "swyx": "AI engineering · Latent Space",
    "joshwoodward": "Google Labs / Gemini",
    "bcherny": "Claude Code · Anthropic",
    "thsottiaux": "Anthropic",
    "petergyang": "product & AI content",
    "thenanyu": "builder",
    "realmadhuguru": "builder",
    "AmandaAskell": "AI alignment · Anthropic",
    "_catwu": "Claude Code · Anthropic",
    "trq212": "agents · Anthropic",
    "GoogleLabs": "Google Labs · official",
    "amasad": "Replit · CEO",
    "rauchg": "Vercel · CEO",
    "alexalbert__": "developer relations · Anthropic",
    "levie": "Box · CEO",
    "ryolu_": "design · Cursor",
    "garrytan": "Y Combinator · president",
    "mattturck": "VC · FirstMark (MAD landscape)",
    "zarazhangrui": "builder & writer · ex-a16z",
    "nikunj": "operator & investor",
    "steipete": "indie dev · ex-PSPDFKit",
    "danshipper": "Every · CEO (AI workflows)",
    "adityaag": "investor · ex-Dropbox",
    "sama": "OpenAI · CEO",
    "claudeai": "Anthropic · official",
}

# Editor's notes for hero picks (keyed by substring of title). Human-curated = the POV.
EDITOR_NOTES = {
    "Jensen Huang": {
        "note": "Jensen with Sequoia on AI factories and compute as the new industrial base. If you want to grasp why this cycle is 'the largest infrastructure buildout in history' — and where the money flows — start here.",
        "tags": ["Sequoia", "AI infrastructure", "Investing", "Jensen Huang"],
    },
}

CAT = r'''
<div id="pet" title="drag me 🐾"><img src="cat.png" alt="" draggable="false"></div>
<style>
#pet{position:fixed;right:14px;bottom:10px;z-index:60;width:94px;cursor:grab;user-select:none;-webkit-user-select:none;filter:drop-shadow(0 6px 9px rgba(0,0,0,.22))}
#pet img{width:100%;display:block;pointer-events:none;transform-origin:bottom center;animation:breathe 3.8s ease-in-out infinite}
@keyframes breathe{0%,100%{transform:translateY(0) rotate(0)}50%{transform:translateY(-3px) rotate(-1.5deg)}}
#pet.grab{cursor:grabbing}
#pet.grab img{animation:none;transform:rotate(-5deg) scale(1.05)}
#pet.wig img{animation:wig .45s}
@keyframes wig{0%,100%{transform:rotate(0)}25%{transform:rotate(9deg)}75%{transform:rotate(-9deg)}}
</style>
<script>
(function(){var pet=document.getElementById('pet');
var s=localStorage.getItem('frontier-pet-pos');if(s){try{var q=JSON.parse(s);pet.style.left=q.x+'px';pet.style.top=q.y+'px';pet.style.right='auto';pet.style.bottom='auto';}catch(e){}}
var drag=false,moved=false,ox=0,oy=0;
pet.addEventListener('mousedown',function(e){drag=true;moved=false;pet.classList.add('grab');var r=pet.getBoundingClientRect();ox=e.clientX-r.left;oy=e.clientY-r.top;e.preventDefault();});
document.addEventListener('mousemove',function(e){if(!drag)return;moved=true;pet.style.left=(e.clientX-ox)+'px';pet.style.top=(e.clientY-oy)+'px';pet.style.right='auto';pet.style.bottom='auto';});
document.addEventListener('mouseup',function(){if(!drag)return;drag=false;pet.classList.remove('grab');var r=pet.getBoundingClientRect();localStorage.setItem('frontier-pet-pos',JSON.stringify({x:Math.round(r.left),y:Math.round(r.top)}));if(!moved){pet.classList.add('wig');setTimeout(function(){pet.classList.remove('wig')},460);}});
})();
</script>
'''

def yt_id(url):
    for pat in (r"[?&]v=([\w-]{6,})", r"youtu\.be/([\w-]{6,})", r"/live/([\w-]{6,})", r"/embed/([\w-]{6,})"):
        m = re.search(pat, url or "")
        if m:
            return m.group(1)
    return None

def clean(t, n=300):
    if not t:
        return ""
    t = re.sub(r"Speaker\s*\d+\s*\|\s*[\d:]+\s*-\s*[\d:]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return (t[:n].rsplit(" ", 1)[0] + "…") if len(t) > n else t

def esc(s):
    return html.escape(s or "")

def editor_note(title):
    for k, v in EDITOR_NOTES.items():
        if k in (title or ""):
            return v
    return {}

pods = json.load(open(FB / "feed-podcasts.json")).get("podcasts", [])
xs = json.load(open(FB / "feed-x.json")).get("x", [])
gen = json.load(open(FB / "feed-podcasts.json")).get("generatedAt", "")[:10]

pod_items = []
for p in pods:
    vid = yt_id(p.get("url", ""))
    if not vid:
        continue
    pod_items.append({
        "name": p.get("name", ""), "title": p.get("title", ""), "url": p.get("url", ""),
        "vid": vid, "teaser": clean(p.get("transcript", ""), 320),
    })

# Merge Amber's custom YouTube sources (from fetch_sources.py → custom_feed.json)
_cf = OUT / "custom_feed.json"
if _cf.exists():
    for c in json.load(open(_cf)).get("youtube", []):
        if c.get("vid"):
            pod_items.append({"name": c["name"], "title": c.get("title", ""),
                              "url": c.get("url", ""), "vid": c["vid"], "teaser": ""})

x_items = []
for b in xs:
    tw = (b.get("tweets") or [])
    if not tw:
        continue
    h = b.get("handle", "")
    x_items.append({
        "name": b.get("name", ""), "handle": h, "field": BUILDER_FIELDS.get(h, ""),
        "avatar": f"https://unavatar.io/x/{h}",
        "tweet": clean(tw[0].get("text", ""), 220),
        "url": f"https://x.com/{h}/status/{tw[0].get('id','')}",
    })

hero = pod_items[0] if pod_items else None

# Deep dives: rank the rest by AI-industry relevance, keep top 3
AI_KW = ["ai", " model", "agent", "foundation", "llm", "venture", "gpt", "openai",
         "anthropic", "compute", "gpu", "intelligence", "robot", "frontier", "scal"]
def ai_score(title):
    t = (title or "").lower()
    return sum(t.count(k) for k in AI_KW)
rest_pods = sorted(pod_items[1:], key=lambda p: -ai_score(p["title"]))[:3]

# Builders on X: keep ORIGINAL TECH/AI takes — drop reposts, reactions, and chit-chat.
REACTION_STARTS = ("great post", "this is the most", "this is the best", "counterpoint",
                   "love this", "so true", "exactly", "this.", "100%", "agreed",
                   "well said", "congrats", "amazing", "incredible", "+1")
TECH_KW = ["ai ", "model", "agent", "llm", "gpt", "claude", "token", "prompt", "coding",
           "code", "repo", "product", "build", "ship", "startup", "founder", "open source",
           "compute", "gpu", "inference", "fine-tun", "rag", "eval", "benchmark", " api",
           "subagent", "context", "reasoning", "robot", "chip", "scal", "venture",
           "enterprise", "saas", "research", "training", "dataset", "intelligence"]
CHATTER = ["flight", "weather", "god bless", "good morning", "gm ", "happy birthday",
           "coffee", "weekend", "tired", "jetlag", "airport", "starlink", "wright brothers",
           "vacation", "dinner", "congrats on"]
def tweet_score(tweet):
    t = re.sub(r"https?://\S+", "", tweet).strip()
    low = t.lower()
    if len(t) < 70:                                   # mostly a link / one-liner
        return -10
    if any(low.startswith(s) for s in REACTION_STARTS):  # reaction/repost
        return -10
    if any(c in low for c in CHATTER):                # personal chit-chat
        return -10
    return sum(1 for k in TECH_KW if k in low)        # tech/AI substance
x_items = sorted([b for b in x_items if tweet_score(b["tweet"]) >= 1],
                 key=lambda b: -tweet_score(b["tweet"]))[:6]

def thumb(vid):  # maxres, fall back to hq on error
    return (f'<img src="https://img.youtube.com/vi/{vid}/maxresdefault.jpg" '
            f'onerror="this.src=\'https://img.youtube.com/vi/{vid}/hqdefault.jpg\'" alt="">')

def pod_card(p):
    return f"""<a class="pod" href="{esc(p['url'])}" target="_blank">
      <div class="thumb sm">{thumb(p['vid'])}</div>
      <div><span class="src">{esc(p['name'])}</span><h3>{esc(p['title'])}</h3></div></a>"""

def x_card(b):
    field = f'<div class="field">{esc(b["field"])}</div>' if b["field"] else ""
    return f"""<div class="xc">
      <img loading="lazy" class="av" src="{esc(b['avatar'])}" alt="" onerror="this.style.visibility='hidden'">
      <div><div class="xn">{esc(b['name'])} <span>@{esc(b['handle'])}</span></div>{field}
      <p>{esc(b['tweet'])}</p><a href="{esc(b['url'])}" target="_blank">read on X →</a></div></div>"""

hero_html = ""
if hero:
    ed = editor_note(hero["title"])
    note_html = ""
    if ed.get("note"):
        tags = "".join(f'<span class="edtag">{esc(t)}</span>' for t in ed.get("tags", []))
        note_html = (f'<div class="ednote"><div class="ednote-h"><i class="star">★</i>'
                     f'Editor\'s choice — why this today</div>{esc(ed["note"])}'
                     f'<div class="edtags">{tags}</div></div>')
    hero_html = f"""<a class="hero" href="{esc(hero['url'])}" target="_blank">
      <div class="thumb">{thumb(hero['vid'])}</div>
      <span class="kicker"><i class="star">★</i> Editor's choice · {esc(hero['name'])}</span>
      <h1>{esc(hero['title'])}</h1></a>{note_html}"""

page = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Frontier · AI daily</title>
<style>
:root{{--ink:#111;--muted:#666;--line:#e4e2dc;--accent:#b8341a;--bg:#faf9f6}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 -apple-system,"Segoe UI",Roboto,sans-serif;-webkit-font-smoothing:antialiased}}
.wrap{{max-width:880px;margin:0 auto;padding:0 20px 80px}}
a{{color:inherit}}
header{{text-align:center;border-bottom:2px solid var(--ink);padding:30px 0 16px;margin-bottom:36px}}
.mast{{font-family:Georgia,serif;font-size:66px;font-weight:700;letter-spacing:-1px;line-height:1}}
.tag{{font-size:13px;color:var(--muted);margin-top:8px;font-style:italic}}
.byl{{font-size:12px;color:var(--muted);margin-top:8px}}
.byl a{{color:var(--accent);text-decoration:none}}
.thumb img{{width:100%;aspect-ratio:16/9;object-fit:cover;border-radius:8px;background:var(--line);display:block}}
.thumb.sm{{width:210px;flex-shrink:0}}
.hero{{display:block;text-decoration:none;margin-bottom:8px}}
.kicker{{display:block;font-size:12px;text-transform:uppercase;letter-spacing:.12em;color:var(--accent);margin:16px 0 6px;font-weight:600}}
.hero h1{{font-family:Georgia,serif;font-size:40px;line-height:1.12;margin:0;font-weight:700}}
.ednote{{background:#fff;border:1px solid var(--accent);border-left:4px solid var(--accent);padding:14px 18px;margin:16px 0 44px;font-size:15px;line-height:1.6;color:#222;border-radius:8px}}
.ednote-h{{font-size:12px;text-transform:uppercase;letter-spacing:.1em;color:var(--accent);font-weight:600;margin-bottom:8px}}
.star{{color:var(--accent);font-style:normal}}
.edtags{{margin-top:12px;display:flex;flex-wrap:wrap;gap:6px}}
.edtag{{font-size:12px;color:var(--accent);background:#f6e7e3;border:0.5px solid #e3b9ae;padding:2px 10px;border-radius:20px}}
.sec{{font-size:12px;text-transform:uppercase;letter-spacing:.14em;color:var(--muted);border-bottom:1px solid var(--ink);padding-bottom:6px;margin:0 0 24px;font-weight:600}}
.pods{{display:grid;gap:26px;margin-bottom:48px}}
.pod{{display:flex;gap:18px;text-decoration:none;align-items:start}}
.pod .src{{font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:var(--accent);font-weight:600}}
.pod h3{{font-family:Georgia,serif;font-size:21px;line-height:1.25;margin:5px 0 0;font-weight:700}}
.empty{{font-size:14px;color:var(--muted);font-style:italic;margin-bottom:48px}}
.xs{{display:grid;grid-template-columns:1fr 1fr;gap:26px}}
.xc{{display:flex;gap:12px}}
.av{{width:48px;height:48px;border-radius:50%;flex-shrink:0;object-fit:cover;background:var(--line)}}
.xn{{font-weight:600;font-size:15px}}.xn span{{color:var(--muted);font-weight:400}}
.field{{font-size:11px;color:var(--accent);margin:1px 0 5px}}
.xc p{{font-size:14px;line-height:1.55;color:#333;margin:0 0 4px}}
.xc a{{font-size:12px;color:var(--accent);text-decoration:none}}
footer{{text-align:center;border-top:2px solid var(--ink);margin-top:52px;padding-top:20px;font-size:13px;color:var(--muted)}}
footer a{{color:var(--accent);text-decoration:none}}
@media(max-width:640px){{.mast{{font-size:46px}}.hero h1{{font-size:29px}}.pod{{flex-direction:column}}.thumb.sm{{width:100%}}.xs{{grid-template-columns:1fr}}}}
</style></head>
<body><div class="wrap">
<header><div class="mast">Frontier</div>
<div class="tag">AI news, curated from builders — not influencers</div>
<div class="byl">{esc(gen)} · created by <a href="{PORTFOLIO}" target="_blank">Amber Huang</a> · <a href="{TWITTER}" target="_blank">follow on X</a></div></header>
{hero_html}
<div class="sec">Deep dives</div>
{('<div class="pods">' + ''.join(pod_card(p) for p in rest_pods) + '</div>') if rest_pods else '<div class="empty">Quiet feed today — only the Editor\'s choice above. More as builders publish.</div>'}
<div class="sec">Builders on X</div>
<div class="xs">{''.join(x_card(b) for b in x_items)}</div>
<footer>Pick your own builders. Read AI like a magazine.<br>
<a href="https://github.com/7amberhuang/frontier" target="_blank">fork it on GitHub</a> · <a href="{TWITTER}" target="_blank">@amber</a> · <a href="manual.html">how to file this in Obsidian</a></footer>
</div>{CAT}</body></html>"""

(OUT / "index.html").write_text(page, encoding="utf-8")
print(f"✓ built {OUT/'index.html'}  | {len(pod_items)} podcasts, {len(x_items)} builders ({sum(1 for b in x_items if b['field'])} tagged)")

# ---- Daily Prophet edition (Hogwarts newspaper skin, same data) ----
_ed = editor_note(hero["title"]) if hero else {}

def prophet_pod(p):
    return (f'<a class="pcol" href="{esc(p["url"])}" target="_blank">'
            f'<div class="pframe">{thumb(p["vid"])}<span class="pcap">moving photograph</span></div>'
            f'<div class="psrc">{esc(p["name"])}</div><h3>{esc(p["title"])}</h3></a>')

def prophet_x(b):
    fld = (" · " + esc(b["field"])) if b["field"] else ""
    return (f'<div class="powl"><div class="pwho">{esc(b["name"])} '
            f'<span>@{esc(b["handle"])}{fld}</span></div><p>{esc(b["tweet"])}</p></div>')

phero = ""
if hero:
    phero = (f'<a class="plead" href="{esc(hero["url"])}" target="_blank">'
             f'<div class="pframe big">{thumb(hero["vid"])}<span class="pcap">moving photograph · {esc(hero["name"])}</span></div>'
             f'<div class="pkick">★ Editor\'s choice</div><h1>{esc(hero["title"])}</h1></a>'
             f'<p class="pnote">{esc(_ed.get("note",""))}</p>')

prophet = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The Frontier Prophet</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IM+Fell+English:ital@0;1&family=UnifrakturMaguntia&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box}}
body{{margin:0;background:#dccfa8;color:#2c2114;font-family:'IM Fell English',Georgia,serif;font-size:17px;line-height:1.55}}
.pw{{max-width:860px;margin:0 auto;padding:0 26px 90px;background:#efe3c4;box-shadow:0 0 60px rgba(80,60,30,.3);border-left:1px solid #cbb88a;border-right:1px solid #cbb88a}}
.prule{{border:0;border-top:3px double #2c2114;margin:0}}
.pmast{{font-family:'UnifrakturMaguntia',serif;font-size:72px;text-align:center;line-height:1;margin:16px 0 4px}}
.pmeta{{display:flex;justify-content:space-between;font-size:12px;font-style:italic;text-transform:uppercase;letter-spacing:.08em;padding:6px 0}}
.ptag{{text-align:center;font-style:italic;font-size:15px;margin:6px 0 12px}}
.plead{{display:block;text-decoration:none;color:inherit;margin:24px 0 8px}}
.pframe{{position:relative;border:6px double #2c2114;padding:5px;background:#d9c79a}}
.pframe img{{width:100%;aspect-ratio:16/9;object-fit:cover;display:block;filter:sepia(.6) contrast(1.05) brightness(.95);animation:flick 7s ease-in-out infinite}}
@keyframes flick{{0%,100%{{filter:sepia(.6) contrast(1.05) brightness(.95)}}50%{{filter:sepia(.46) contrast(1.13) brightness(1.04)}}}}
.pcap{{position:absolute;bottom:9px;left:11px;font-size:11px;font-style:italic;background:#efe3c4;padding:1px 8px;border:1px solid #2c2114}}
.pkick{{text-align:center;font-variant:small-caps;letter-spacing:.1em;color:#7a1d12;margin:12px 0 0;font-size:14px}}
.plead h1{{font-family:'UnifrakturMaguntia',serif;font-size:42px;text-align:center;line-height:1.08;margin:4px 0}}
.pnote{{font-size:17px;column-count:2;column-gap:28px;text-align:justify;margin:0 0 34px}}
.pnote::first-letter{{font-family:'UnifrakturMaguntia',serif;font-size:56px;float:left;line-height:.78;padding:6px 8px 0 0;color:#7a1d12}}
.psec{{font-family:'UnifrakturMaguntia',serif;font-size:27px;text-align:center;margin:28px 0 16px;border-top:1px solid #2c2114;border-bottom:1px solid #2c2114;padding:6px 0}}
.pcols{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:22px;margin-bottom:28px}}
.pcol{{text-decoration:none;color:inherit}}
.pcol .psrc{{font-variant:small-caps;letter-spacing:.06em;color:#7a1d12;font-size:13px;margin-top:7px}}
.pcol h3{{font-size:18px;line-height:1.2;margin:2px 0 0;font-weight:400}}
.powls{{column-count:2;column-gap:30px}}
.powl{{break-inside:avoid;margin:0 0 16px;border-top:1px solid #b8a474;padding-top:8px}}
.pwho{{font-size:15px}}.pwho span{{font-style:italic;color:#6a5a3a;font-size:13px}}
.powl p{{font-size:15px;margin:3px 0 0;text-align:justify}}
.pfoot{{text-align:center;border-top:3px double #2c2114;margin-top:40px;padding-top:16px;font-size:13px;font-style:italic}}
.pfoot a{{color:#7a1d12}}
@media(max-width:640px){{.pmast{{font-size:44px}}.plead h1{{font-size:30px}}.pcols{{grid-template-columns:1fr}}.pnote,.powls{{column-count:1}}}}
</style></head>
<body><div class="pw">
<div class="pmeta"><span>{esc(gen)}</span><span>Wizarding AI · Daily</span><span>Price: 5 Knuts</span></div>
<hr class="prule">
<div class="pmast">The Frontier Prophet</div>
<div class="ptag">~ the wizarding world's AI news · by builders, not influencers ~</div>
<hr class="prule">
{phero}
<div class="psec">✦ Moving Pictures ✦</div>
<div class="pcols">{''.join(prophet_pod(p) for p in rest_pods)}</div>
<div class="psec">✦ Owl Post from the Builders ✦</div>
<div class="powls">{''.join(prophet_x(b) for b in x_items)}</div>
<div class="pfoot">Mischief managed. · <a href="index.html">← back to the Muggle edition</a> · <a href="{PORTFOLIO}" target="_blank">Amber Huang</a></div>
</div>{CAT}</body></html>"""

# Daily Prophet edition removed per user request (2026-06-17) — generation skipped.
_ = prophet  # keep var to avoid lint; not written
