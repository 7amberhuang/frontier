#!/usr/bin/env bash
# AI 投资周报：每周一 10:30 由 launchd 触发。抓融资新闻 → claude 整理 → 写进 Brain 投资区。
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$HOME/.local/bin:$HOME/.local/share/fnm/node-versions/v24.15.0/installation/bin"
cd "$HOME/Developer/frontier" || exit 1
LOG="$HOME/Developer/frontier/.funding.log"
echo "[$(date '+%F %T')] funding weekly start" >> "$LOG"
python3 fetch_funding.py >> "$LOG" 2>&1
echo "[$(date '+%F %T')] funding weekly done" >> "$LOG"
