#!/usr/bin/env bash
# 重新生成 README 的横幅和流程图（深色 + 浅色，2 倍像素）。需要 Chrome。
#   docs/src/render.sh
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$HERE/../images"
CH="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
shot() {  # page width height name
  for t in dark light; do
    q=""; [ "$t" = light ] && q="?theme=light"
    rm -f "$OUT/$4-$t.png"
    # Chrome sometimes exits non-zero after writing the screenshot: judge by the file, not the exit code
    "$CH" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=2 \
      --window-size="$2,$3" --screenshot="$OUT/$4-$t.png" "file://$HERE/$1$q" 2>/dev/null || true
    [ -s "$OUT/$4-$t.png" ] || { echo "没有生成 $4-$t.png" >&2; exit 1; }
  done
}
shot banner.html 1280 480 banner
shot pipeline.html 1600 650 pipeline
ls -la "$OUT"/banner-*.png "$OUT"/pipeline-*.png
