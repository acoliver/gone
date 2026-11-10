#!/bin/bash
set -u
ROOT=art-source/terminal/generated
OUT=art-source/terminal/generated/console2/outputs
BIN=/Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-flux2-edit
run_one() {
  local kind="$1" seed="$2" width="$3" height="$4" prompt="$5" outfile="$6"
  local args=()
  if [ "$kind" = console ]; then
    args=("$ROOT/console2/inputs/ref-console-crop.png")
  else
    args=("$ROOT/kbmodel/render-top.png" "$ROOT/kbmodel/render-front.png")
  fi
  local attempt=1 status=0
  while [ "$attempt" -le 2 ]; do
    rm -f "$outfile"
    HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 "$BIN" --model flux2-klein-4b --quantize 4 --steps 8 --guidance 1.0 --width "$width" --height "$height" --seed "$seed" --image-paths "${args[@]}" --prompt-file "$prompt" --metadata --output "$outfile" >"$OUT/../logs/${kind}-s${seed}-try${attempt}.log" 2>&1
    status=$?
    if [ "$status" -eq 0 ]; then
      printf '%s\n' "SUCCESS $kind $seed $outfile" >> "$OUT/../logs/status.log"
      return 0
    fi
    printf '%s\n' "FAIL $kind $seed status=$status attempt=$attempt" >> "$OUT/../logs/status.log"
    if [ "$status" -eq 134 ] && [ "$attempt" -eq 1 ]; then
      sleep 60
      attempt=2
    else
      return "$status"
    fi
  done
}
for seed in 510 511 512 513; do run_one console "$seed" 768 1024 "$ROOT/console2/prompts/console-front.txt" "$OUT/console-s${seed}.png" || exit $?; done
for seed in 520 521 522 523; do run_one keyboard "$seed" 1024 768 "$ROOT/console2/prompts/keyboard-front.txt" "$OUT/keyboard-s${seed}.png" || exit $?; done
