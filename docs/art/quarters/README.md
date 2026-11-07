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
