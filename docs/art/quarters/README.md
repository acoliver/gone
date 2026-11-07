# Quarters art

## Plan view

Regenerate `plan.png` and its check report from the repository root with `/Volumes/XS1000/tools/mlximg-venv/bin/python tools/art/quarters_plan.py --layout docs/art/quarters/layout.json --out docs/art/quarters/plan.png --report docs/art/quarters/plan-checks.json`. The checks cover room bounds, intersecting floor footprints, player reachability and route clearance, entrance-wall storage, and the clear doorway opening. The command exits with a nonzero status when a check fails.

## Contact sheets

Run the commands from the repository root with `/Volumes/XS1000/tools/mlximg-venv/bin/python tools/art/contact_sheet.py`. The `hero --prompts docs/art/quarters/prompts/pilot.json --prop storage_locker_module --out tmp/contact` command generates a hero for each seed in the prompt file. Add `--seeds 101` to select a specific seed. Add `--dry-run` to print the commands without generating images.

The `views --prompts docs/art/quarters/prompts/pilot.json --prop storage_locker_module --hero tmp/contact/storage_locker_module/hero-s101.png --out tmp/contact` command generates the four view edits from a hero image. Add `--seed 1` to set the edit seed. Add `--dry-run` to print the edit commands without generating images.

The `sheet --prop storage_locker_module --out tmp/contact` command composes the hero and four views into `sheet.png` and writes `sheet.json` with input hashes. It selects the first hero image by seed order.

Generated images, prompt files and provenance stay in the gitignored `tmp/` directory until a sheet is approved. After approval, copy the chosen hero, views, sheet and provenance JSON to `docs/art/quarters/sheets/<prop>/`.

### What the pilot showed about generated views (2026-11-07)

The FLUX.2-klein edit model does not turn an object. Asked for a left, right or back view, it either redraws the front face again or changes the object.
- **Sofa:** all four views became a two-seat sofa with a throw on each arm.
- **Locker:** the left, right and back views each showed the door face again. Only the straight front view agreed with the hero.

So the hero image is the main input to Hunyuan. A generated view goes in alongside it only if the reviewer confirms it shows the same object at the requested angle. For the pilot props the inputs are:

| Prop | Hunyuan input |
| --- | --- |
| Locker | hero plus the front view |
| Sofa | hero alone |
| Tunic | hero alone, unless a view passes review |

Side and back geometry is filled in by Hunyuan and then corrected during fitting.

Two more pilot findings:
- **Uniform:** the image model kept hanging the trousers on a separate clip hanger, so the pilot uses the tunic alone and the trousers become their own prop.
- **Locker hero:** this is an edit of seed 107 that closed the open legs and recessed the handle. Its base flange sticks out slightly, and that gets corrected when the mesh is fitted.


## Storage locker module

The fitted source is `tools/blender/quarters/storage_locker_module/locker-working.blend`. The exporter and checks are `build.py` and `verify.py` in the same directory. The game asset is `assets/props/quarters/storage_locker_module.glb`.

The fitted carcass remains 0.600 × 2.400 × 0.600 m. The fixed surround is 0.040 m wide at each side, with a 0.055 m upper rail. The door is 0.480 × 2.220 m and starts 0.110 m above the floor. Its pivot is X=-0.240, Y=0.110, Z=0.258 m. I lowered the door and pivot with the base so the door meets the reduced kick plate while the total locker height stays 2.400 m.

The kick plate is 0.520 × 0.105 × 0.520 m in DarkSteel. It is set back 0.040 m from the carcass front and both sides, leaving a shadow line below the body. The bottom surround rail is now a shallow strip below the door, which keeps the door sweep clear.

The door has one upper group of three recessed horizontal vents. Each opening is 0.240 m wide and 0.014 m high, with an angled louvre inside. The lower vent group shown in the supplied hero is intentionally omitted, as required by the part layout. No pressed stiffening ribs were added because the hero shows a flat door panel. The door has a 0.002 m bevel and an 0.008 m shallow return around its perimeter. The carcass outer vertical corners have 0.003 m chamfers.

Three split hinge assemblies sit near the bottom, middle and top of the left edge. Each has two 0.032 m cylindrical knuckles, each 0.018 m in diameter, separated by a 0.006 m split. The surround has 12 mm low-poly domed rivets at 0.135 m spacing along all four edges. Matching rivets run down the carcass front corners.

The handle pocket is 0.060 × 0.170 m and centred at Y=0.855 m. The handle is a separate lever in a boolean-cut recess. The export has `PaintedSteel`, `BareSteel` and `DarkSteel` materials, UVs on every mesh, and the named parent relationships for the door, vents, handle, hinges and rivets.

The Blender verification reports bounds of 0.600000 × 2.400000 × 0.600000 m within the 0.002 m tolerance. The door pivot error is below 0.000001 m on every axis. The 0° to 100° outward swing was checked at 1° steps with no intersections outside the 0.015 m hinge-edge clearance. The kick plate check confirms 0.520 × 0.105 × 0.520 m bounds and its floor-level bottom. The export has 5,176 triangles, 0 non-manifold edges, 0 degenerate faces and 0 invalid normals. All seven required named nodes have their expected parents, every mesh has UVs, and all three materials are present. Re-exporting from the saved Blender source produced a byte-identical GLB.

To rebuild the editable source and export, run `/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python tools/blender/quarters/storage_locker_module/build.py -- --save-source --output assets/props/quarters/storage_locker_module.glb`. To export again from the saved source, omit `--save-source`. Run `verify.py` with the same Blender options and `-- --input assets/props/quarters/storage_locker_module.glb --report tools/blender/quarters/storage_locker_module/verify.json`.

The second-pass neutral renders are in the gitignored `tmp/fit/locker/pass2/` directory. `compare-hero.png` places the supplied hero beside the fitted render. `compare-front.png` is the fitted front view. `turntable.png` contains the 30°, 120°, 210° and 300° views under main and fill lighting. `compare-detail.png` places a crop of the hero's upper door beside the close-up render.

## Sofa

The input was `tmp/hy/sofa-hero.glb`, a single watertight mesh with 391,256 triangles and bounds of 1.9621 × 0.8932 × 0.8440 arbitrary units. Its long axis is X, depth is Y and height is Z. The cross-section through the middle shows the seat around Z=-0.008, or about 0.41 m above the guide's floor after height normalization. The front-to-back section is about 0.45 guide units at the seat. The rear edge stays close to Y=-0.259 from seat height to the top, so the back is almost upright. Mapping the guide to 2.2 × 0.95 × 0.85 m uses axis scale factors 1.121 along length, 1.064 along depth and 1.007 along height.

The guide retained six cushion masses and shallow grooves. The fit keeps the six separate pieces, with low-poly rounded shells and modelled welt loops. Each cushion is 0.66 m wide, with 10 mm gaps between neighbours. Seat cushions are 0.70 m deep and 0.11 m thick, and their top is 0.469 m above the floor. Back cushions are 0.31 m high and 0.17 m deep, leaning back 8°. The guide's rough mid-seat depth was about 0.49 m after scaling, so the fitted 0.70 m depth follows the approved image's deeper upholstered seat. The guide's solid arm and back slabs became 26 mm arm panels, a top and lower back rail, and two uprights. The plain underside gained two seat support rails. Four 80 mm feet and separate corner plates with bare-steel rivets replace the guide's faint feet and fasteners. The oversized guide throw became a closed wool shell with 7 mm thickness, folded over the image-right arm and hanging 0.49 m. Its nearest clearance to the arm is about 2 mm, leaving no mesh intersection.

The source and exporter are `tools/blender/quarters/sofa/sofa-working.blend` and `build.py`; `verify.py` writes `verify.json`. The export bounds are 2.2000 × 0.8500 × 0.9525 m, each within the 5 mm tolerance. The seat top is 0.469 m, and its support gap is 1.5 mm. All ten required mesh nodes are present; each has UVs, closed manifold topology, consistent normals and no degenerate faces. The frame, cushions and throw have zero detected intersections. The export has 12,488 triangles against the 15,000 limit. Re-exporting from the saved Blender source is byte-identical.

The neutral studio comparison sheets are in gitignored `tmp/fit/sofa/`. `compare-hero.png` puts the design hero next to the fitted render from a matching front-left view. `turntable.png` contains 30°, 120°, 210° and 300° views. `compare-detail.png` places the image-right arm crop beside its rendered corner-plate close-up.
