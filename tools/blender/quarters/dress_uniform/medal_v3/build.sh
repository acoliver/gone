#!/bin/bash
set -eu
ROOT=/Volumes/XS1000/acoliver/projects/gone/branch-2/tmp/wt-130
SOURCE="$ROOT/tools/blender/quarters/dress_uniform/medal_v3"
OUT="$ROOT/tmp/issue130-v3/fit1"
PYTHON=/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python
BLENDER=/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender
mkdir -p "$OUT"
ps -axo pid,ppid,etime,command > "$OUT/pre-build-processes.log"
"$BLENDER" --background --factory-startup --python-exit-code 1 --python "$SOURCE/cage.py" > "$OUT/cage.log" 2>&1
"$PYTHON" "$SOURCE/fair.py" > "$OUT/fair.log" 2>&1
"$PYTHON" "$SOURCE/match_camera.py" > "$OUT/camera-match.log" 2>&1
"$BLENDER" --background --factory-startup --python-exit-code 1 --python "$SOURCE/build.py" > "$OUT/build.log" 2>&1
printf 'BUILD_FINISHED\n'
