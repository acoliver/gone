#!/bin/bash
set -eu
ROOT=/Volumes/XS1000/acoliver/projects/gone/branch-2/tmp/wt-130
SOURCE="$ROOT/tools/blender/quarters/dress_uniform/medal_v3"
OUT="$ROOT/tmp/issue130-v3/fit2"
PYTHON=/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python
BLENDER=/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender
ps -axo pid,ppid,etime,command > "$OUT/pre-render-processes.log"
"$BLENDER" --background --factory-startup --python-exit-code 1 --python "$SOURCE/render.py" -- --output "$OUT" > "$OUT/render.log" 2>&1
"$BLENDER" --background --factory-startup --python-exit-code 1 --python "$SOURCE/run_fit2.py" -- --script diagnose12.py --after > "$OUT/sector-and-rotation.log" 2>&1
"$PYTHON" "$SOURCE/run_fit2.py" --script controls12.py --after > "$OUT/rotation-sheets.log" 2>&1
"$PYTHON" "$SOURCE/run_fit2.py" --script sheets.py > "$OUT/sheets.log" 2>&1
"$BLENDER" --background --factory-startup --python-exit-code 1 --python "$SOURCE/inspect_fit2.py" -- --after > "$OUT/inspect-after.log" 2>&1
"$PYTHON" "$SOURCE/maps2.py" > "$OUT/finding-diagnostics.log" 2>&1
"$PYTHON" "$SOURCE/joins2.py" > "$OUT/joins.log" 2>&1
"$PYTHON" "$SOURCE/extra2.py" > "$OUT/extra-checks.log" 2>&1
"$PYTHON" "$SOURCE/comparisons2.py" > "$OUT/comparisons.log" 2>&1
"$PYTHON" "$SOURCE/run_fit2.py" --script final.py > "$OUT/final.log" 2>&1
"$PYTHON" "$SOURCE/report2.py" > "$OUT/report.log" 2>&1
printf 'FIT2_FINISHED\n'
