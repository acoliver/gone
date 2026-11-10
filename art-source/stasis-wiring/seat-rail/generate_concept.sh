#!/bin/bash
set -euo pipefail
cd /Volumes/XS1000/acoliver/projects/gone/branch-4
export HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1
PROMPT='Industrial product photograph of a single short slim formed sheet steel ceiling panel support rail, a 320 mm long shallow inverted C channel only 36 mm wide and 18 mm deep, made from thin 3 mm sheet steel. Long narrow flat top bearing face, two small downturned side returns with smoothly rounded manufacturing folds and tiny inward rolled bottom lips. Clearly visible hollow open underside and exposed thin-walled C cross section at the near end, not a solid rectangular bar, not timber, not a square beam, not a floor plate. Two small elongated punched mounting slots in the vertical side returns. Old dull neutral gray galvanized steel dominates, fine real metal grain, small localized dark orange rust abrasions only around slots and cut edges, no brown checker pattern, no paint. Single whole component centered and entirely in frame, isolated on light gray studio background, soft diffuse lighting, low three-quarter perspective looking into the near end and along the open underside, realistic engineering component, no text, no logos, no supports, no other objects.'
printf '%s\n' "$PROMPT" > art-source/stasis-wiring/seat-rail/prompt.txt
printf '{"seed":1103618,"steps":8,"quantize":4,"width":1024,"height":768,"model":"filipstrand/Z-Image-Turbo-mflux-4bit"}\n' > art-source/stasis-wiring/seat-rail/concept-settings.json
/Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-z-image-turbo --model filipstrand/Z-Image-Turbo-mflux-4bit --quantize 4 --steps 8 --seed 1103618 --width 1024 --height 768 --output art-source/stasis-wiring/seat-rail/concept.png --prompt "$PROMPT"
echo $? > tmp/verify-stasis-wiring/seat-rail/concept.exit
cd /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d
.venv/bin/python generate.py --front /Volumes/XS1000/acoliver/projects/gone/branch-4/art-source/stasis-wiring/seat-rail/concept.png --remove-bg --subfolder hunyuan3d-dit-v2-mv --octree-resolution 320 --min-component-faces 50 --seed 0 --out /Volumes/XS1000/acoliver/projects/gone/branch-4/art-source/stasis-wiring/seat-rail/guide.glb
echo $? > /Volumes/XS1000/acoliver/projects/gone/branch-4/tmp/verify-stasis-wiring/seat-rail/guide.exit
