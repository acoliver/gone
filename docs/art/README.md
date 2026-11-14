# Art direction and production guides

The ship is an old colonial military vessel with paneled bulkheads, ribs, pipes, conduits and worn hardware. Personal rooms add fabric and belongings to that structure. The ship has been adrift about 1000 years. The [quarters guide](quarters/README.md#two-finish-states) defines the dry-storage treatment for its two room states.

Stasis pods contrast with the worn compartment. Their smooth white plastic shells remain clean under the maintenance robot's care. Raised canopies use dark glossy glass, with a separate padded couch and pillow inside. Material contrast should remain visible without suggesting that the pods were recently installed.

## Concept images

| Image | Subject |
| --- | --- |
| [room-walls.png](room-walls.png) | Riveted compartment panels, ribs, pipes, damage and emergency lighting |
| [pod-design-sheet.png](pod-design-sheet.png) | Rounded capsule form, canopy and padded interior |
| [stasis-bay-context.png](stasis-bay-context.png) | Repeated capsule pods in the worn compartment, including open lids |

These locally generated Z-Image-Turbo images guide form and composition. Their older off-white shell treatment is superseded by the production pod's neutral glossy white plastic. They are concept images rather than measurements of the installed scene.

## Recreate the concept images

The retained source recipes use Z-Image-Turbo 4-bit through mflux. Set `MFLUX` to the installed `mflux-generate-z-image-turbo` executable and `HF_HOME` to an existing model cache. No image model is bundled in this repository. For example, with the cached model available:

```sh
mkdir -p art-output
"$MFLUX" --model filipstrand/Z-Image-Turbo-mflux-4bit --quantize 4 --steps 8 --seed 11 --width 1536 --height 864 --output art-output/room-walls.png --prompt "$PROMPT"
```

Set `PROMPT` to the matching retained prompt below and substitute the seed, dimensions and output name for the other images. mflux creates a suffixed filename if the target already exists. These inputs preserve the source recipe; exact regeneration depends on the model and tool versions.

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

## Production pod

The game uses `assets/props/pod/pod-v4.glb`. Its editable tagged source, `build.py` exporter and geometry/optics checks are in [tools/blender/pod_v4](../../tools/blender/pod_v4/README.md). That guide provides the build command and records open glass limitations. The source includes the base, hinged lid, window pane, couch and pillow. Runtime uses `app/pod_mesh.gd` and `app/pod_glass.gdshader`.

For import conventions and verification, see [the asset pipeline](../dev/asset-pipeline.md). Run the game tests from the repository root:

```sh
godot --headless --path . -s tests/run_tests.gd
```

## Other production guides

- [Quarters](quarters/README.md): furniture, clothes, belongings, two-state finishes and captures.
- [Corridors](corridors/README.md): metric maps and connector concepts.
- [Whole-ship atlas](ship/README.md): planning data and interactive overview.
- [Stasis wiring](stasis-wiring-production-installation.md): installed source-to-pod network and build instructions.
- [Ceiling seat and pickup](seat-production-integration.md): shared formed rail and fallen pry tool.
- [Lighting fixtures](../dev/light-fixture-mounting.md): mounted emitters, circuit behavior and captures.

## Known limitations

Concept sheets do not specify hidden construction or guarantee generated views agree. Production sources and runtime checks take precedence for dimensions and placement. Some installed assets retain visual or reconstruction limitations, listed in their guides.
