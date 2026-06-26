#!/usr/bin/env python3
"""今日金句：从当天爬到的 builder 推文里，让 claude **挑**最有料/能激发灵感的一条
（只挑选 + 截取原话，绝不改写/编造），并校验金句是真推文的子串（防篡改），@ 上本人。
→ .quote.json {quote, author}。失败则启发式兜底。 Run after fetch_x_builders.py.
"""
import json, subprocess, pathlib, re, time

HERE = pathlib.Path(__file__).resolve().parent
CLAUDE = str(pathlib.Path.home() / ".local/bin/claude")
OUT = HERE / ".quote.json"


def clean(t):
    return re.sub(r"\s+", " ", re.sub(r"https?://\S+", "", t or "")).strip()


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


xs = json.load(open(HERE / "builders_feed.json")).get("x", []) if (HERE / "builders_feed.json").exists() else []
cands = []
for b in xs:
    tw = b.get("tweets") or []
    if not tw:
        continue
    t = clean(tw[0].get("text", ""))
    if 40 < len(t) < 380 and not t.lower().startswith("rt @"):
        cands.append((b.get("name", ""), t))

quote = {}
if cands:
    listing = "\n".join(f"{i}. [{n}] {t}" for i, (n, t) in enumerate(cands))
    prompt = ("These are real tweets posted today by well-known AI builders. Pick the ONE that works best "
              "as an inspiring 'quote of the day' for an AI daily — sharp, insightful, a little provocative. "
              "Use their EXACT words; you may trim to the punchiest span (<=120 chars) but DO NOT rephrase, "
              "translate, or add words. Reply with ONLY compact JSON: {\"i\": <index>, \"quote\": \"<exact span>\"}.\n\n"
              + listing)
    for _ in range(3):
        try:
            r = subprocess.run([CLAUDE, "--model", "claude-sonnet-4-6", "-p", prompt],
                               capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            time.sleep(3); continue
        m = re.search(r"\{.*\}", r.stdout, re.S)
        if not m:
            time.sleep(3); continue
        try:
            d = json.loads(m.group(0))
            i, q = int(d["i"]), clean(d["quote"])
            # 防篡改：金句必须是被选推文的子串（归一化后）
            if 0 <= i < len(cands) and norm(q) and norm(q) in norm(cands[i][1]):
                quote = {"quote": q, "author": cands[i][0]}
                break
        except Exception:
            pass
        time.sleep(3)
    if not quote:                              # 兜底：挑一条结构像金句的（含破折号/冒号、长度适中）
        scored = sorted(cands, key=lambda c: (("—" in c[1] or ":" in c[1]), 200 - abs(len(c[1]) - 120)), reverse=True)
        n, t = scored[0]
        quote = {"quote": t[:120].rstrip() + ("…" if len(t) > 120 else ""), "author": n}

OUT.write_text(json.dumps(quote, ensure_ascii=False), encoding="utf-8")
print(f"今日金句: “{quote.get('quote','')}” —— {quote.get('author','(无)')}" if quote else "无可用金句")
