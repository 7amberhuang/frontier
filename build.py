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

# Builders on X: keep only original substantive takes (drop reposts/reactions), 6 max
REACTION_STARTS = ("great post", "this is the most", "this is the best", "counterpoint",
                   "love this", "so true", "exactly", "this.", "100%", "agreed",
                   "well said", "congrats", "amazing", "incredible", "+1")
def is_original(tweet):
    t = re.sub(r"https?://\S+", "", tweet).strip()
    if len(t) < 70:            # mostly a link / one-liner
        return False
    low = t.lower()
    return not any(low.startswith(s) for s in REACTION_STARTS)
x_items = [b for b in x_items if is_original(b["tweet"])][:6]

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
<div class="sec">Deep dives · today's 3 on AI</div>
{('<div class="pods">' + ''.join(pod_card(p) for p in rest_pods) + '</div>') if rest_pods else '<div class="empty">Quiet feed today — only the Editor\'s choice above. More as builders publish.</div>'}
<div class="sec">Builders on X</div>
<div class="xs">{''.join(x_card(b) for b in x_items)}</div>
<footer>Pick your own builders. Read AI like a magazine.<br>
<a href="https://github.com/7amberhuang/frontier" target="_blank">fork it on GitHub</a> · <a href="{TWITTER}" target="_blank">@amber</a></footer>
</div></body></html>"""

(OUT / "index.html").write_text(page, encoding="utf-8")
print(f"✓ built {OUT/'index.html'}  | {len(pod_items)} podcasts, {len(x_items)} builders ({sum(1 for b in x_items if b['field'])} tagged)")
