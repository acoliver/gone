# Ceiling and fire-safety props

The detector, sprinkler and duct use Andrew's seed-410 selections from the ceiling-model trial. The light cassette uses seed 411 from a new FLUX.2-klein edit of a crop of the accepted beam concept. The long structural beam was not replaced.

Each object directory retains its generated mesh, conditioning views, masks, prompts and concept images. `provenance.json` records their hashes and generation settings. `generator/` freezes the local Hunyuan implementation used for these meshes. Generation used the same non-turbo Hunyuan3D-2mv model and settings as the hatch pipeline: float16, 30 steps, guidance 5, octree 384, 50,000 chunks and no component pruning.

The three cassette seeds are non-watertight. Seed 411 had the closest front length-to-width ratio and the fewest triangles. Its raw ratio is 1.535, while the requested metric envelope is narrower. This is a provisional numerical selection, not a visual acceptance claim. The concept and all candidate clay views are in `tmp/ceiling-props/module-sheet.jpg`.

`tools/blender/build_ceiling_props.py` fits the selected detector, sprinkler and cassette meshes to unit bounds for the metric placements in `sim/ceiling_services.gd`. The fitting is anisotropic. Wall-mounted backs are flattened, and the cassette's generated glass backing is cut away between four retained louvre bands. The runtime glass remains a separate surface behind those openings, retaining the existing circuit, energy and fade policy. The builder reduces each mesh to its instance budget and writes `assets/props/ceiling/manifest.json` with the measured counts.

The generated duct remains frozen as a record of the selected source, but is not used at runtime. Its smooth irregular relief produced a swollen silhouette. The builder instead authors flat sheet faces around a 0.40 by 0.30 m rectangular body, raised end flanges, rivets and a strap with ceiling-reaching legs. Its total envelope is 0.44 m wide and 0.35 m high including hardware. The assembled mesh uses 576 triangles, one surface and the same weathered-steel wall material as the surrounding structure.

Detectors are selected near each wall's midpoint instead of scanning from a corner. Bay candidates must clear five sight lines from the room centre at standing eye height. Detector fronts face inward at 2.2 m; the power-room centre sight check starts above the generator crown because the generator occupies the floor centre. Lift sprinklers mount on the back wall rather than within the entrance lintel. Purpose-framed service views use the production circuits without additional inspection lights.

Rebuild from the repository root with Blender 4.5:

```sh
/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python-exit-code 1 --python tools/blender/build_ceiling_props.py
```

All runtime finishes come from `Surfaces`: existing weathered steel, weathered red paint, corroded brass and light glass. The detector flame has no emission or light source. These props add no colliders.
