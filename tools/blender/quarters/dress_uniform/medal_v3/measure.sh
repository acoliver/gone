#!/bin/bash
set -eu
ROOT=/Volumes/XS1000/acoliver/projects/gone/branch-2/tmp/wt-130
SOURCE="$ROOT/tools/blender/quarters/dress_uniform/medal_v3"
OUT="$ROOT/tmp/issue130-v3/fit1"
PYTHON=/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python
grep -q BUILD_COMPLETE "$OUT/build.log"
"$PYTHON" "$SOURCE/match_camera.py" > "$OUT/camera-match.log" 2>&1
"$PYTHON" "$SOURCE/measure.py" > "$OUT/local-measurements.log" 2>&1
"$PYTHON" "$SOURCE/verify2.py" --output "$OUT" > "$OUT/verify.log" 2>&1
"$PYTHON" "$SOURCE/silhouette12.py" --after > "$OUT/silhouette.log" 2>&1
printf 'MEASURE_FINISHED\n'
