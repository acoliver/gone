#!/bin/bash
set -eu
ROOT=/Volumes/XS1000/acoliver/projects/gone/branch-2/tmp/wt-130
SOURCE="$ROOT/tools/blender/quarters/dress_uniform/medal_v3"
OUT="$ROOT/tmp/issue130-v3/fit2"
PYTHON=/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python
BLENDER=/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender
"$PYTHON" "$SOURCE/run_fit2.py" --script surface_gate.py > "$OUT/surface-gate.log" 2>&1
ps -axo pid,ppid,etime,command > "$OUT/pre-bake-processes.log"
"$BLENDER" --background --factory-startup --python-exit-code 1 --python "$SOURCE/bake3.py" -- --output "$OUT" --current-only --body-extrusion 0.0001 --body-ray-distance 0.00025 > "$OUT/bake.log" 2>&1
"$BLENDER" --background --factory-startup --python-exit-code 1 --python "$SOURCE/run_fit2.py" -- --script bake12.py > "$OUT/rear-bake.log" 2>&1
"$BLENDER" --background --factory-startup --python-exit-code 1 --python "$SOURCE/bake_audit2.py" > "$OUT/bake-check.log" 2>&1
printf 'BAKE2_FINISHED\n'
