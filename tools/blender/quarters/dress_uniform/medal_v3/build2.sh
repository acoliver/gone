#!/bin/bash
set -eu
ROOT=/Volumes/XS1000/acoliver/projects/gone/branch-2/tmp/wt-130
SOURCE="$ROOT/tools/blender/quarters/dress_uniform/medal_v3"
OUT="$ROOT/tmp/issue130-v3/fit2"
PYTHON=/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python
BLENDER=/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender
ps -axo pid,ppid,etime,command > "$OUT/pre-build-processes.log"
if [ "${1:-}" != --export ] && [ "${1:-}" != --uv ]; then
 "$PYTHON" "$SOURCE/fair2.py" > "$OUT/fair.log" 2>&1
 "$BLENDER" --background --factory-startup --python-exit-code 1 --python "$SOURCE/edit_fit2.py" > "$OUT/edit.log" 2>&1
fi
if [ "${1:-}" = --uv ]; then
 "$BLENDER" --background --factory-startup --python-exit-code 1 --python "$SOURCE/reuv2.py" > "$OUT/reuv.log" 2>&1
else
 "$BLENDER" --background --factory-startup --python-exit-code 1 --python "$SOURCE/run_fit2.py" -- --script build.py > "$OUT/build.log" 2>&1
fi
"$PYTHON" "$SOURCE/run_fit2.py" --script measure.py > "$OUT/local-measurements.log" 2>&1
"$PYTHON" "$SOURCE/run_fit2.py" --script verify2.py --output "$OUT" > "$OUT/verify.log" 2>&1
"$PYTHON" "$SOURCE/run_fit2.py" --script silhouette12.py --after > "$OUT/silhouette.log" 2>&1
"$PYTHON" "$SOURCE/run_fit2.py" --script surface_gate.py > "$OUT/surface-gate.log" 2>&1
printf 'BUILD2_FINISHED\n'
