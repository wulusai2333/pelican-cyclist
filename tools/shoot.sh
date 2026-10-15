#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# 无头 Chrome 截图工具
#   用于自动化验证 3D 场景（不需要人来点开浏览器），也可用来生成 README 配图。
#
# 用法:
#   tools/shoot.sh screenshots/01-chase.png "adv=3.4"
#   tools/shoot.sh out.png "adv=1.5&freeze=1&nohud=1&cam=1.5708,0.09,2.5,1.05,36" 1280 800
#
# 页面支持的一次性 URL 参数（只影响调试/截图，不影响正常交互）:
#   adv=<秒>            以固定步长把仿真快进 N 秒（保证截图姿态可复现）
#   freeze=1            快进后暂停仿真，只保留相机
#   view=<模式>         chase | orbit | cine | front | low | head
#   cam=th,ph,dist,lookY,fov   自由机位（th 为相对车头方向的方位角）
#   tod=<小时>          时刻，5..21
#   speed=<m/s>         巡航速度
#   honk=1              摆出鸣叫姿态（喉囊充气、张口）
#   nohud=1             隐藏 UI
# ---------------------------------------------------------------------------
set -euo pipefail

CHROME="${CHROME:-/c/Program Files/Google/Chrome/Application/chrome.exe}"
[ -x "$CHROME" ] || CHROME="/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$1"
QUERY="${2:-}"
W="${3:-1280}"
H="${4:-800}"

# Windows 上给 Chrome 用正斜杠路径最稳
to_win() { if command -v cygpath >/dev/null 2>&1; then cygpath -m "$1"; else echo "$1"; fi; }

mkdir -p "$(dirname "$OUT")"
OUT="$(cd "$(dirname "$OUT")" && pwd)/$(basename "$OUT")"   # Chrome 的相对路径以自身 cwd 解析，必须绝对化
URL="file:///$(to_win "$ROOT/index.html")"
[ -n "$QUERY" ] && URL="$URL?$QUERY"

"$CHROME" --headless=new --enable-unsafe-swiftshader --use-angle=swiftshader \
  --disable-dev-shm-usage --hide-scrollbars --window-size="$W,$H" \
  --virtual-time-budget=20000 \
  --screenshot="$(to_win "$OUT")" "$URL" 2>&1 \
  | grep -viE "libpng|iCCP|fontconfig|gpu|devtools|vulkan|gl_|registration_request|mcs_client|gcm" || true

[ -f "$OUT" ] && echo "OK  $OUT" || { echo "FAILED  $OUT" >&2; exit 1; }
