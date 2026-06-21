#!/usr/bin/env python3
"""Pre-read the day's long videos so Amber reads a 预习 before deciding to watch.
For each Deep-dive YouTube video: grab auto-captions (fast, no whisper) →
claude distills a knowledge-ified preview → write one daily note into Brain.
Prints a short Feishu-ready preview to stdout. Run after build.py.
"""
import json, subprocess, pathlib, tempfile, re, datetime, urllib.parse, time, shutil

HERE = pathlib.Path(__file__).resolve().parent
BRAIN = pathlib.Path.home() / "Documents/Brain"
OUTDIR = BRAIN / "wiki/行业通用/每日预习"
CLAUDE = str(pathlib.Path.home() / ".local/bin/claude")
MAX = 4
TODAY = datetime.date.today().isoformat()

def captions(vid):
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(["yt-dlp", "--skip-download", "--write-auto-subs",
                        "--sub-lang", "en.*", "--sub-format", "vtt",
                        "-o", f"{d}/%(id)s.%(ext)s",
                        f"https://www.youtube.com/watch?v={vid}"],
                       capture_output=True, timeout=150)
        vtts = sorted(pathlib.Path(d).glob("*.vtt"), key=lambda p: ("orig" in p.name))
        if not vtts:
            return ""
        return clean_vtt(vtts[0].read_text(encoding="utf-8", errors="ignore"))

def clean_vtt(t):
    out = []
    for ln in t.splitlines():
        if "-->" in ln or ln.strip().isdigit() or ln.startswith(("WEBVTT", "Kind:", "Language:")) or not ln.strip():
            continue
        ln = re.sub(r"<[^>]+>", "", ln).strip()
        if ln and (not out or out[-1] != ln):
            out.append(ln)
    return " ".join(out)

def summarize(name, title, transcript):
    prompt = f"""这是一个 AI 长视频的字幕转写。给 Amber 做"预习总结"——让她不用看完一小时就知道重点，再决定要不要深看。

来源：{name} · {title}

输出（中文，知识化、体系化，像拆解 case 那样，别寒暄）：
🎯 **一句话**：bottom line
📌 **核心观点/框架**（3-5 条，凝练有信息量，能用图标/短语就别长句）
👤 **谁该看 / 重点在哪**
⏱️ **要不要花一小时**：值看 / 选看 / 跳过 + 一句理由

字幕（可能有口语错字，按上下文理解）：
{transcript[:14000]}"""
    ERRS = ("api error", "connection closed", "try again", "overloaded",
            "rate limit", "529", "503", "internal server error")
    for attempt in range(4):              # 重试：claude -p 偶发空/超时/API错误，别让视频被静默丢掉
        try:
            r = subprocess.run([CLAUDE, "-p", prompt], capture_output=True, text=True,
                               timeout=300, stdin=subprocess.DEVNULL)
            out = r.stdout.strip()
            low = out.lower()
            # 有效总结：含模板标记或足够长，且不是 API 错误串（错误串会被当成正文写进去，这正是之前的 bug）
            if out and ("🎯" in out or "一句话" in out or len(out) > 200) \
                    and not any(e in low for e in ERRS):
                return out
            print(f"     (claude 无效输出，重试 {attempt+1}/4：{(out or r.stderr.strip())[:110]})")
        except subprocess.TimeoutExpired:
            print(f"     (claude 超时，重试 {attempt+1}/4)")
        time.sleep(4 * (attempt + 1))     # 退避：连接被掐/过载时多等一会
    return ""

_all = json.load(open(HERE / "custom_feed.json")).get("youtube", [])
_seen, vids = set(), []
for v in _all:                       # 每频道取一条，去重
    if v["name"] in _seen:
        continue
    _seen.add(v["name"])
    vids.append(v)
vids = vids[:MAX]
OUTDIR.mkdir(parents=True, exist_ok=True)
blocks, feishu = [], []
for v in vids:
    tr = captions(v["vid"])
    if len(tr) < 400:
        print(f"  ✗ {v['name']}: 无字幕/太短，跳过")
        continue
    s = summarize(v["name"], v["title"], tr)
    if not s:
        print(f"  ✗ {v['name']}: 总结失败")
        continue
    url = f"https://www.youtube.com/watch?v={v['vid']}"
    blocks.append(f"## {v['title']}\n*{v['name']}* · [▶ 看视频]({url})\n\n{s}\n")
    bl = next((l for l in s.splitlines() if "一句话" in l or "🎯" in l), s[:80])
    feishu.append(f"· {v['name']}：{re.sub(r'[*🎯]', '', bl).replace('一句话','').strip(': ：')[:60]}")
    print(f"  ✓ {v['name']} 预习完成")

note = OUTDIR / f"{TODAY}.md"
front = f"---\ntitle: 每日预习 {TODAY}\ncategory: synthesis\ntags: [general-ai, ai-workflow]\ndate: {TODAY}\n---\n\n# 📖 每日预习 · {TODAY}\n\n> AI 已帮你读完今天的长视频。先看这个再决定要不要花一小时沉浸看。\n\n"
note.write_text(front + "\n---\n\n".join(blocks) + "\n\n→ 回 [[输入体系]]", encoding="utf-8")
subprocess.run(["git", "-C", str(BRAIN), "add", "-A"], capture_output=True)
subprocess.run(["git", "-C", str(BRAIN), "commit", "-q", "-m", f"每日预习 {TODAY}"], capture_output=True)

# 同步生成「飞书预习文档」——订阅者不用装 Obsidian 也能看；滚动覆盖同一篇，URL 不变，落自己飞书云空间。
# Fork 的人各自生成自己的文档（信源/播客可本地化），所以这步跑在每个人本地。
LARKCLI = shutil.which("lark-cli") or str(pathlib.Path.home() / ".local/share/fnm/node-versions/v24.15.0/installation/bin/lark-cli")
preview_url = ""
if blocks:
    fmd = (f"# 📖 Frontier 每日预习 · {TODAY}\n\n"
           "> AI 已替你读完今天的长视频。先看这页，再决定要不要花一小时深看。\n\n"
           + "\n\n---\n\n".join(blocks))
    (HERE / "preview_feishu.md").write_text(fmd, encoding="utf-8")
    tokf, urlf = HERE / ".preview_doc_token", HERE / ".preview_doc_url"
    try:
        if tokf.exists():                       # 已有滚动文档 → 覆盖（URL 不变）
            subprocess.run([LARKCLI, "docs", "+update", "--api-version", "v2", "--as", "user",
                            "--doc", tokf.read_text().strip(), "--command", "overwrite",
                            "--doc-format", "markdown", "--content", "@preview_feishu.md"],
                           cwd=HERE, capture_output=True, text=True, timeout=120)
            preview_url = urlf.read_text().strip() if urlf.exists() else ""
        else:                                   # 第一次 → 新建并记住 token + url
            r = subprocess.run([LARKCLI, "docs", "+create", "--api-version", "v2", "--as", "user",
                                "--doc-format", "markdown", "--parent-position", "my_library",
                                "--content", "@preview_feishu.md"],
                               cwd=HERE, capture_output=True, text=True, timeout=120)
            doc = json.loads(r.stdout or "{}").get("data", {}).get("document", {})
            preview_url = doc.get("url", "")
            if doc.get("document_id"):
                tokf.write_text(doc["document_id"]); urlf.write_text(preview_url)
        print(f"  ✓ 飞书预习文档：{preview_url or '(写入失败)'}")
    except Exception as ex:
        print(f"  ✗ 飞书文档生成失败：{str(ex)[:120]}")

# Feishu-ready preview + 链接（优先飞书文档，退回 obsidian）
rel = f"wiki/行业通用/每日预习/{TODAY}"
ob = "obsidian://open?vault=Brain&file=" + urllib.parse.quote(rel)
print("---FEISHU---")
print(f"📖 今日预习（AI 已读完 {len(blocks)} 条长视频）：\n" + "\n".join(feishu) + f"\n\n看预习笔记 → {preview_url or ob}")
