#!/usr/bin/env python3
"""Frontier daily as a RICH multi-column Feishu card — like a magazine spread:
each Deep-dive video is a column (cover thumbnail + title + source + AI one-line preview
+ 看视频 button), then bottom buttons (看完整日报 / 看预习笔记).
Run after digest_videos.py + build.py.
"""
import json, re, subprocess, datetime, urllib.request, pathlib

HERE = pathlib.Path(__file__).resolve().parent
OID = "ou_e71b8550edc0acc975ef9682aa3a0bc6"
LARK = str(pathlib.Path.home() / ".local/share/fnm/node-versions/v24.15.0/installation/bin/lark-cli")
NOTE = (pathlib.Path.home() / "Documents/Brain/wiki/行业通用/每日预习"
        / f"{datetime.date.today().isoformat()}.md")
SITE = "https://hiamberhuang.github.io/frontier/"
today = datetime.date.today().isoformat()


def blocks():
    """逐节解析预习笔记 → [(title, src, one)]，避免跨节误匹配。"""
    if not NOTE.exists():
        return []
    t = NOTE.read_text(encoding="utf-8")
    out = []
    for sec in re.split(r"(?=^## )", t, flags=re.M):
        if not sec.startswith("## "):
            continue
        title = sec.splitlines()[0][3:].split("|")[0].strip()
        ms = re.search(r"^\*(.+?)\*\s*·", sec, re.M)
        src = ms.group(1).strip() if ms else ""
        m = (re.search(r"🎯\s*\*\*一句话\*\*[：:]\s*(\S.*)", sec)
             or re.search(r"🎯\s*\*\*一句话\*\*[：:]?\s*\n+\s*(\S.*)", sec))
        out.append((title, src, m.group(1).strip() if m else ""))
    return out


def trim(s, n=46):
    """压到差不多长度，尽量在标点/空格处断 + …，让 3 列高度（和「看视频」位置）整齐。"""
    s = (s or "").strip()
    if len(s) <= n:
        return s
    cut = s[:n]
    for p in ("。", "——", "，", "、", " "):      # 末尾加空格 → 英文标题在词边界断
        i = cut.rfind(p)
        if i >= n * 0.55:
            return cut[:i].rstrip("，、—— ") + "…"
    return cut.rstrip("，、—— ") + "…"


def upload_thumb(vid):
    """下载 YouTube 缩略图 → 上传飞书拿 image_key（失败返回 ''，卡片自动退化为纯文字列）。"""
    p = HERE / f"_t_{vid}.jpg"
    try:
        for q in ("maxresdefault", "hqdefault"):
            try:
                urllib.request.urlretrieve(f"https://img.youtube.com/vi/{vid}/{q}.jpg", p)
                if p.stat().st_size > 3000:
                    break
            except Exception:
                continue
        r = subprocess.run([LARK, "im", "images", "create", "--file", f"image={p.name}",
                            "--data", '{"image_type":"message"}', "--as", "bot"],
                           cwd=HERE, capture_output=True, text=True, timeout=40)
        return (json.loads(r.stdout).get("data") or {}).get("image_key", "")
    except Exception:
        return ""
    finally:
        p.unlink(missing_ok=True)


bs = blocks()
preview_by_title = {t: one for t, s, one in bs}

# Deep-dive 视频（custom_feed 每频道一条，前 3 列）
vids, seen = [], set()
cf = HERE / "custom_feed.json"
if cf.exists():
    for v in json.load(open(cf)).get("youtube", []):
        if v.get("name") in seen:
            continue
        seen.add(v["name"]); vids.append(v)
    vids = vids[:3]

cols = []
for v in vids:
    ttl = v.get("title", "").split("|")[0].strip()
    one = preview_by_title.get(ttl) or next(
        (preview_by_title[t] for t in preview_by_title if ttl[:16] in t or t[:16] in ttl), "")
    ik = upload_thumb(v["vid"])
    elems = []
    if ik:
        elems.append({"tag": "img", "img_key": ik, "alt": {"tag": "plain_text", "content": ""},
                      "mode": "fit_horizontal"})
    yurl = f"https://www.youtube.com/watch?v={v['vid']}"
    # 标题 cap ~40、预习 cap ~30 → 每列大致 2 行标题 + 2 行预习，"看视频"基本同一行
    body = f"[**{trim(ttl, 40)}**]({yurl})\n_{v.get('name','')}_"
    if one:
        body += f"\n\n{trim(one, 30)}"
    body += f"\n\n[▶ 看视频]({yurl})"
    elems.append({"tag": "div", "text": {"tag": "lark_md", "content": body}})
    cols.append({"tag": "column", "width": "weighted", "weight": 1,
                 "vertical_align": "top", "elements": elems})

_pdu = HERE / ".preview_doc_url"
preview_url = _pdu.read_text(encoding="utf-8").strip() if _pdu.exists() else SITE
func = (f"**{today}** · AI 替你读完 **{len(bs)}** 条长视频，先看预习再决定要不要花一小时深看 👇"
        if bs else f"**{today}** · 今日 AI 日报已更新 👇")
q = {}
_qf = HERE / ".quote.json"
if _qf.exists():
    try:
        q = json.load(open(_qf))
    except Exception:
        q = {}
# 顶部「今日金句」= 真·当日 builder 推文（pick_quote.py 校验过原话），每天不一样
intro = (f"💬 *“{q['quote']}”* —— **{q['author']}**\n\n{func}") if q.get("quote") else func

card = {
    "config": {"wide_screen_mode": True},
    "header": {"template": "red",
               "title": {"tag": "plain_text", "content": "📰 Frontier · 今日 AI 日报"}},
    "elements": [
        {"tag": "div", "text": {"tag": "lark_md", "content": intro}},
    ] + ([{"tag": "column_set", "flex_mode": "stretch", "columns": cols}] if cols else []) + [
        {"tag": "hr"},
        {"tag": "action", "actions": [
            {"tag": "button", "text": {"tag": "plain_text", "content": "📖 看完整日报"},
             "type": "primary", "url": SITE},
            {"tag": "button", "text": {"tag": "plain_text", "content": "🧠 看预习笔记"},
             "type": "primary", "url": preview_url},
        ]},
    ],
}

content = json.dumps(card, ensure_ascii=False)
subs = HERE / ".subscribers"
recips = ([l.strip() for l in subs.read_text(encoding="utf-8").splitlines()
           if l.strip() and not l.startswith("#")] if subs.exists() else [OID])
for rid in recips:
    flag = "--chat-id" if rid.startswith("oc_") else "--user-id"
    r = subprocess.run([LARK, "im", "+messages-send", flag, rid,
                        "--msg-type", "interactive", "--content", content, "--as", "bot"],
                       capture_output=True, text=True)
    ok = '"message_id"' in r.stdout
    print(f"  {'✓' if ok else '✗'} {rid}: {(r.stdout or r.stderr).strip()[:120]}")
