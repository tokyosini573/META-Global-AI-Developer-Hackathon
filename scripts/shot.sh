#!/usr/bin/env bash
# 1920×1080 스크린샷 (디자인 점검용, CLAUDE.md 규칙 6)
#   scripts/shot.sh "http://localhost:5173/?day=90&still" out.png
set -euo pipefail
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
"$CHROME" --headless=new --disable-gpu --hide-scrollbars --window-size=1920,1080 \
  --virtual-time-budget=5000 --screenshot="$2" "$1" 2>/dev/null
echo "$2"
