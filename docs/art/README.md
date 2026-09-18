# gone: concept art

Direction (Andrew, 2026-09-17): the ship reads as an old, broken-down
colonial warship in the Battlestar Galactica / Stargate Universe
tradition. Walls are paneled, ribbed, piped structure, not flat cubes.
The stasis pods read as rounded, smooth, and newer than the ship around
them: the pods are recent hardware installed in a worn hull. These
images are the visual target for the wall and pod work.

## Pieces

| File | Subject | Serves |
| --- | --- | --- |
| `room-walls.png` | Worn compartment interior: riveted seamed bulkheads, pipe runs, cable conduits, hazard plates, battle damage, red emergency mood. | #35 wall/floor/ceiling textures, anti-cube wall geometry |
| `pod-design-sheet.png` | Stasis pod design sheet: rounded horizontal capsule, off-white composite shell, dark glass canopy over a single padded couch with pillow and straps, red spine light. Three views. | #37 pod meshes: rounded and newer than the ship |
| `stasis-bay-context.png` | The bay in context: pale capsule pods on cradles in the grimy riveted compartment, nearest pod open with canopy raised and couch visible. | Composite mood target for #35/#37/#40 review |

## Verification

Each piece passed an independent Eyes review (vision subagent, strict
pass/fail with quoted observations): the wall piece passed structure and
mood; the pod sheet and bay pieces were regenerated once to remove an
automotive-cockpit read and add an open canopy, then passed. Artifacts of
the review (quotes, verdicts) live in the session log; generation
prompts are recorded below.

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
| stasis-bay-context | 55 | 1536x864 |

Prompts (verbatim):

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
  starship stasis bay: seven horizontal rounded capsule pods like
  smooth white medical cryosleep berths resting on low deck cradles in
  two rows, pale composite shells that look newer than the worn riveted
  steel compartment around them. The nearest pod is open: its curved
  glass canopy hinged fully up like an open clamshell, an empty padded
  couch visible inside. Torn ceiling cable tray with hanging wires,
  deep red emergency lighting, thin drifting smoke, Battlestar Galactica
  meets Stargate Universe, dark filmic mood. No people, no text, no
  vehicles."

Operational note: mflux does not clobber an existing output file; it
writes `<name>_1.png`. Delete or move the target before regenerating.
The cached 4-bit snapshot also needed its `tokenizer_config.json`
patched with the upstream chat template before prompts would encode
(one-time local fix, 2026-09-17).
