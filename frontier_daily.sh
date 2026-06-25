#!/usr/bin/env bash
# Frontier 日更：抓源 → build → push → 本地通知。launchd 每天 10:00 触发。
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$HOME/.local/bin:$HOME/.local/share/fnm/node-versions/v24.15.0/installation/bin"
cd "$HOME/Developer/frontier" || exit 1
LOG="$HOME/Developer/frontier/.daily.log"

echo "[$(date '+%F %T')] start" >> "$LOG"
python3 fetch_sources.py          >> "$LOG" 2>&1
python3 fetch_x_products.py       >> "$LOG" 2>&1   # TikHub 官号最新推（需 .tikhub_key）
python3 fetch_x_builders.py       >> "$LOG" 2>&1   # TikHub builders 最新推（Builders on X 保新鲜）
# 先预习：AI 读完长视频 → 写 Brain + 生成头条英文 Editor's note（build 要用）+ 飞书预习文档
python3 digest_videos.py          >> "$LOG" 2>&1
echo "[$(date '+%F %T')] preview done" >> "$LOG"
python3 build.py                  >> "$LOG" 2>&1

# 推送前 review 门禁：站点必须有实质内容才推，避免空站/坏站覆盖线上
REVIEW_OK=1
[ -s index.html ] && [ "$(wc -c < index.html)" -gt 4000 ] && grep -q '<h1>' index.html || REVIEW_OK=0
grep -q 'class="xc"' index.html || echo "[$(date '+%F %T')] ⚠ review: Builders on X 空（TikHub？）" >> "$LOG"

git add -A >> "$LOG" 2>&1
git commit -q -m "daily: $(date '+%Y-%m-%d') refresh" >> "$LOG" 2>&1
if [ "$REVIEW_OK" = 1 ]; then
  PUSH="⚠ push failed (本地已更新)"
  for i in 1 2 3; do                              # push 自动重试，扛偶发网络
    if git push -q >> "$LOG" 2>&1; then PUSH="✓ pushed"; break; fi
    sleep $((i * 8))
  done
else
  PUSH="⛔ review 未通过（站点内容异常）→ 跳过 push，保留线上旧版"
fi
echo "[$(date '+%F %T')] $PUSH" >> "$LOG"

osascript -e 'display notification "今日 AI 日报 + 预习已更新" with title "Frontier 📰" sound name "Glass"' 2>/dev/null

# 飞书推送：交互卡片（红色 header + 预习 + 看日报/看预习 按钮）
python3 feishu_card.py >> "$LOG" 2>&1 || true
