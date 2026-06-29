#!/usr/bin/env python3
"""AI 投资新闻周报：抓 TechCrunch venture/AI RSS → 过滤出"融资事件" → claude 整理成
中文结构化周报（公司 · 轮次 · 金额 · 领投 · 估值 · 信号）→ 写进 Brain 投资区。
让"投资 literacy"从静态知识变成每周自动累积。 每周一 10:30 由 launchd 触发。
用正则解析 RSS（系统 python 的 xml 解析器在本机坏掉，绕开 pyexpat）。
"""
import urllib.request, re, datetime, subprocess, pathlib, html

BRAIN = pathlib.Path.home() / "Documents/Brain"
OUTDIR = BRAIN / "wiki/行业通用/投资周报"
CLAUDE = str(pathlib.Path.home() / ".local/bin/claude")
TODAY = datetime.date.today()
WEEK = f"{TODAY.isocalendar().year}-W{TODAY.isocalendar().week:02d}"

FEEDS = [
    "https://techcrunch.com/category/venture/feed/",
    "https://techcrunch.com/category/artificial-intelligence/feed/",
]
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

FUND = ("raises", "raised", "funding", "series a", "series b", "series c", "seed round",
        "led by", "valuation", "valued at", "million", "billion", "round", "invests", "backs")
AI = ("ai", "artificial intelligence", " llm", "model", "agent", "openai", "anthropic",
      "genai", "machine learning", "chatbot", "inference", "gpu", "neural")


def fetch(url):
    try:
        return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25).read().decode("utf-8", "ignore")
    except Exception:
        return ""


def items(xml):
    out = []
    for it in re.findall(r"<item>(.*?)</item>", xml, re.S):
        t = re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", it, re.S)
        l = re.search(r"<link>(.*?)</link>", it, re.S)
        d = re.search(r"<description>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</description>", it, re.S)
        if t:
            title = html.unescape(re.sub(r"<[^>]+>", "", t.group(1))).strip()
            desc = html.unescape(re.sub(r"<[^>]+>", "", d.group(1))).strip() if d else ""
            out.append((title, (l.group(1).strip() if l else ""), desc))
    return out


seen, cand = set(), []
for f in FEEDS:
    for title, link, desc in items(fetch(f)):
        low = (title + " " + desc).lower()
        if link in seen:
            continue
        if any(k in low for k in FUND) and any(k in low for k in AI):
            seen.add(link)
            cand.append((title, link, desc[:200]))
cand = cand[:25]

OUTDIR.mkdir(parents=True, exist_ok=True)
note = OUTDIR / f"{WEEK}.md"
front = (f"---\ntitle: AI 投资周报 {WEEK}\ncategory: synthesis\ntags: [investing, ai, funding]\n"
         f"date: {TODAY.isoformat()}\n---\n\n# 💰 AI 投资周报 · {WEEK}\n\n"
         "> 本周 AI 圈重要融资事件（自动抓取 TechCrunch venture/AI）。判断强信号见 [[AI投资入门-机构与强势信号]]。\n\n")

if not cand:
    note.write_text(front + "_本周没抓到明显的 AI 融资事件（或源暂时不可用）。_\n", encoding="utf-8")
    print("本周无融资事件")
else:
    headlines = "\n".join(f"- {t} — {d}" for t, l, d in cand)
    prompt = ("下面是本周 AI 圈的融资相关新闻标题（英文）。挑出真正的'融资事件'，整理成中文表格，"
              "每行：公司 | 轮次 | 金额 | 领投/投资方 | 估值（没有就写—）。只保留确实是融资的，"
              "去掉不相关的。最多 12 行。表格后加一行『🔥 本周最强信号：<一句话，谁的融资最值得注意+为什么>』。\n\n"
              + headlines)
    body = ""
    for _ in range(3):
        try:
            r = subprocess.run([CLAUDE, "--model", "claude-sonnet-4-6", "-p", prompt],
                               capture_output=True, text=True, timeout=240, stdin=subprocess.DEVNULL)
            o = r.stdout.strip()
            if o and "api error" not in o.lower() and "connection closed" not in o.lower():
                body = o
                break
        except subprocess.TimeoutExpired:
            pass
    if not body:                       # claude 挂了就退回原始列表
        body = "（自动整理失败，原始抓取）\n\n" + "\n".join(f"- [{t}]({l})" for t, l, d in cand)
    refs = "\n\n---\n原始来源：\n" + "\n".join(f"- [{t}]({l})" for t, l, d in cand[:12])
    note.write_text(front + body + refs + "\n\n→ 回 [[AI投资入门-机构与强势信号]]", encoding="utf-8")
    print(f"✓ AI 投资周报 {WEEK}（{len(cand)} 条候选）→ {note}")

subprocess.run(["git", "-C", str(BRAIN), "add", "-A"], capture_output=True)
subprocess.run(["git", "-C", str(BRAIN), "commit", "-q", "-m", f"AI 投资周报 {WEEK}"], capture_output=True)
