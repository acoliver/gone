#!/bin/bash
set -euo pipefail

# Regenerates concept.png and guide.glb in this directory. Both model tools and
# their weights live outside the repository.
: "${HUNYUAN3D_ROOT:?set HUNYUAN3D_ROOT to the Hunyuan3D checkout containing .venv/bin/python and generate.py}"
MFLUX_GENERATOR="${MFLUX_GENERATOR:-mflux-generate-z-image-turbo}"
ART_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export HF_HUB_OFFLINE=1
PROMPT='Industrial product photograph of a single short slim formed sheet steel ceiling panel support rail, a 320 mm long shallow inverted C channel only 36 mm wide and 18 mm deep, made from thin 3 mm sheet steel. Long narrow flat top bearing face, two small downturned side returns with smoothly rounded manufacturing folds and tiny inward rolled bottom lips. Clearly visible hollow open underside and exposed thin-walled C cross section at the near end, not a solid rectangular bar, not timber, not a square beam, not a floor plate. Two small elongated punched mounting slots in the vertical side returns. Old dull neutral gray galvanized steel dominates, fine real metal grain, small localized dark orange rust abrasions only around slots and cut edges, no brown checker pattern, no paint. Single whole component centered and entirely in frame, isolated on light gray studio background, soft diffuse lighting, low three-quarter perspective looking into the near end and along the open underside, realistic engineering component, no text, no logos, no supports, no other objects.'
printf '%s\n' "$PROMPT" > "$ART_DIR/prompt.txt"
printf '{"seed":1103618,"steps":8,"quantize":4,"width":1024,"height":768,"model":"filipstrand/Z-Image-Turbo-mflux-4bit"}\n' > "$ART_DIR/concept-settings.json"
# mflux writes concept_1.png rather than replacing an existing concept.png.
rm -f "$ART_DIR/concept.png"
"$MFLUX_GENERATOR" --model filipstrand/Z-Image-Turbo-mflux-4bit --quantize 4 --steps 8 --seed 1103618 --width 1024 --height 768 --output "$ART_DIR/concept.png" --prompt "$PROMPT"
"$HUNYUAN3D_ROOT/.venv/bin/python" "$HUNYUAN3D_ROOT/generate.py" --front "$ART_DIR/concept.png" --remove-bg --subfolder hunyuan3d-dit-v2-mv --octree-resolution 320 --min-component-faces 50 --seed 0 --out "$ART_DIR/guide.glb"
