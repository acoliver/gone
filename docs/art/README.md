# gone: concept art

Direction (Andrew, 2026-09-17): the ship reads as an old, broken-down
colonial warship in the Battlestar Galactica / Stargate Universe
tradition. Walls are paneled, ribbed, piped structure, not flat cubes.
The stasis pods read as rounded, smooth, and newer than the ship around
them: the pods are recent hardware installed in a worn hull. The pods
are OPEN: the crew came out of stasis and left, so most canopies stand
raised with empty couches and hanging occupancy blankets; a few pods
remain sealed. These images are the visual target for the wall and pod
work.

## Pieces

| File | Subject | Serves |
| --- | --- | --- |
| `room-walls.png` | Worn compartment interior: riveted seamed bulkheads, pipe runs, cable conduits, hazard plates, battle damage, red emergency mood. | #35 wall/floor/ceiling textures, anti-cube wall geometry |
| `pod-design-sheet.png` | Stasis pod design sheet: rounded horizontal capsule, off-white composite shell, dark glass canopy over a single padded couch with pillow and straps, red spine light. Three views. | #37 pod meshes: rounded and newer than the ship |
| `stasis-bay-context.png` | The bay in context: one consistent capsule-pod design (matching the sheet) on cradles in the grimy riveted compartment; five pods open clamshell-style with raised canopy lids, empty couches, hanging blankets; one sealed. | Composite mood target for #35/#37/#40, the crew-left story beat |

## Verification

Each piece passed an independent Eyes review (vision subagent, strict
pass/fail with quoted observations). The wall piece passed first pass.
The pod sheet and bay piece were each regenerated once (the sheet had
an automotive cockpit inside the pod; the bay had all pods sealed), then
passed. The bay piece was revised a second time after review feedback
that the pods must visibly match the sheet design and read as open with
raised lids (crew already left stasis); that revision passed with the
pod family, open-canopy story beat, worn-ship contrast, and coherence
all confirmed. Generation prompts are recorded below.

## Provenance

Generated locally on this machine (M4 Max, MLX) with
Z-Image-Turbo 4-bit via mflux; no external service.

Reproduce with:

```
HF_HOME=/Volumes/XS1000/hf-cache \
  /Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-z-image-turbo \
  --model filipstrand/Z-Image-Turbo-mflux-4bit --quantize 4 --steps 8 \
  --seed <seed> --width <w> --height <h> --output <out.png> --prompt "<prompt>"
```

| Piece | Seed | Size |
| --- | --- | --- |
| room-walls | 11 | 1536x864 |
| pod-design-sheet | 44 | 1216x896 |
| stasis-bay-context | 66 | 1536x864 |

Prompts (verbatim, final revisions):

- room-walls: "Concept art, interior of an old broken-down colonial
  military starship compartment, Battlestar Galactica and Stargate
  Universe aesthetic. Worn riveted steel bulkheads broken into
  overlapping panels, ribs and frames rather than flat walls: exposed
  pipe runs, cable conduits, junction boxes, handrails, hazard stripes,
  scuffed deck plating. Deep red emergency light in darkness,
  industrial, lived-in, filmic cinematic wide establishing shot. No
  people, no text, no logos."
- pod-design-sheet: "Industrial design concept sheet for a military
  hibernation stasis pod, medical cryosleep equipment, not a vehicle.
  Smooth rounded horizontal capsule shell in clean off-white and light
  grey composite, newer and more advanced than the worn old ship it
  belongs to. Large curved transparent glass canopy on top, shown open
  in one view revealing a single padded reclining couch with a pillow
  and restraint straps inside. Slim red status light strip along the
  spine. Two views on one sheet: three-quarter view with canopy open
  showing the couch, and a closed side profile. Dark studio background,
  red rim lighting, precise product concept art rendering. No steering
  wheel, no cockpit, no car seats, no vehicle, no text, no people."
- stasis-bay-context: "Wide cinematic concept art of a derelict
  starship stasis bay: seven identical horizontal rounded capsule
  stasis pods in two rows on low deck cradles, one consistent product
  design: smooth off-white composite shells with dark glass canopy lids
  on top hinges. Five pods have their dark glass canopy lids hinged
  fully open, raised up above each shell like open clamshells, empty
  padded couches and hanging occupancy blankets visible inside; two
  pods are sealed shut. The pale pods look newer than the worn riveted
  steel compartment around them. Torn ceiling cable tray with hanging
  wires, deep red emergency lighting, thin drifting smoke, Battlestar
  Galactica meets Stargate Universe, dark filmic mood. No people, no
  text, no vehicles."

Operational note: mflux does not clobber an existing output file; it
writes `<name>_1.png`. Delete or move the target before regenerating.
The cached 4-bit snapshot also needed its `tokenizer_config.json`
patched with the upstream chat template before prompts would encode
(one-time local fix, 2026-09-17).
