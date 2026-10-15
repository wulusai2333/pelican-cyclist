#!/usr/bin/env bash
# 在无头 Chrome 里加载页面并报告是否出现错误层（用于回归验证赛道回绕缺陷）
# 用法: tools/crashtest.sh "adv=42.6&freeze=1"
CHROME="${CHROME:-/c/Program Files/Google/Chrome/Application/chrome.exe}"
[ -x "$CHROME" ] || CHROME="/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
Q="${1:-}"
to_win() { if command -v cygpath >/dev/null 2>&1; then cygpath -m "$1"; else echo "$1"; fi; }
DOM="$("$CHROME" --headless=new --enable-unsafe-swiftshader --use-angle=swiftshader \
  --disable-dev-shm-usage --window-size=1280,720 --virtual-time-budget=25000 --dump-dom \
  "file:///$(to_win "$ROOT/index.html")?$Q" 2>/dev/null)"

ERR="$(printf '%s' "$DOM" | grep -oE '<code id="err-msg">[^<]*' | sed 's/.*>//')"
LOADHID="$(printf '%s' "$DOM" | grep -oE '<div id="load" class="[^"]*"' | grep -c hide || true)"
KMH="$(printf '%s' "$DOM" | grep -oE '<b id="s-kmh">[^<]*' | sed 's/.*>//')"

if [ -n "$ERR" ]; then
  echo "❌ 崩溃  |  $Q"
  echo "     $ERR"
  exit 1
fi
if [ "$LOADHID" = "0" ]; then
  echo "⚠️  未进入渲染（加载层未撤） | $Q"
  exit 2
fi
echo "✅ 正常  |  $Q   (HUD 时速=$KMH)"
