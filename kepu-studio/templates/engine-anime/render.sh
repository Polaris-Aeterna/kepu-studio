#!/usr/bin/env bash
# Render ManimGL scene(s) off-screen to mp4 (1920x1080, 30fps) with the project config.
#
#   engine/render.sh chapters/ch01_sat/ch01.py Ch01_01_Intro [Ch01_02_... ] [extra manimgl args]
#   engine/render.sh chapters/ch01_sat/ch01.py -a            # all scenes in the file
#   QUALITY=low engine/render.sh ...                          # 480p quick preview (-l)
#   QUALITY=med  ...  (720p)       SUBTITLES=0 ...            # subtitles off
#   FRAME=1 engine/render.sh file.py Scene                    # only save the last frame as PNG
#
# Output: <scene file dir>/videos/<Scene>.mp4  (+ .srt / .timeline.json for NarratedScene)
set -euo pipefail
ENGINE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ $# -ge 1 ] || { sed -n 2,10p "$0"; exit 1; }
FILE="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"; shift
DIR="$(dirname "$FILE")"
case "${QUALITY:-hd}" in
  low) Q="-l" ;; med) Q="-m" ;; uhd) Q="--uhd" ;; *) Q="--hd" ;;
esac
MODE=(-w)
[ "${FRAME:-0}" = "1" ] && MODE=(-w -s)   # NOTE: never use -s without -w (opens a window and hangs)
cd "$DIR"
exec "$ENGINE/.venv/bin/manimgl" "$FILE" "$@" "${MODE[@]}" $Q \
  --config_file "$ENGINE/custom_config.yml" --video_dir "$DIR/videos"
