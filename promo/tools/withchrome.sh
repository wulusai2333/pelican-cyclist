#!/usr/bin/env bash
# 启动一次性 Chrome（前台持有），把剩余参数交给 node 脚本
# 用法: tools/withchrome.sh <node-script.mjs> [args...]
set -uo pipefail
cd "$(dirname "$0")"
PORT=9333
CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
[ -x "$CHROME" ] || CHROME="/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"

if command -v pwsh >/dev/null 2>&1; then
  pwsh -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | Where-Object { \$_.CommandLine -like '*remote-debugging-port=$PORT*' } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force -ErrorAction SilentlyContinue }" >/dev/null 2>&1
fi
sleep 1

"$CHROME" --headless=new --enable-unsafe-swiftshader --use-angle=swiftshader \
  --disable-dev-shm-usage --hide-scrollbars --no-first-run --disable-features=Translate \
  --remote-debugging-port=$PORT --remote-allow-origins='*' --window-size=1280,720 \
  "file:///F:/Game/ComfyUI/pelican-cyclist/index.html" >/dev/null 2>&1 &
CHROME_PID=$!
trap 'kill $CHROME_PID 2>/dev/null' EXIT

for i in $(seq 1 30); do
  curl -s --max-time 2 "http://127.0.0.1:$PORT/json/version" >/dev/null 2>&1 && break
  sleep 1
done
sleep 2
node "$@"
rc=$?
exit $rc
