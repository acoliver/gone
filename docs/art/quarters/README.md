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

I used `tmp/hy/locker-hero.glb`. Its watertight mesh has 319,852 faces and bounds of 0.7451 × 1.9919 × 0.7519 m on X, Y and Z. Scaling its height to 2.4 m takes a factor of 1.20485 and gives 0.8977 × 2.4 × 0.9060 m. At 2%, 12%, 50% and 90% of the height, measured section widths were 0.6362, 0.6341, 0.6327 and 0.6249 m. The corresponding depths were 0.6457, 0.6464, 0.6748 and 0.6683 m. The cross-sections are noisy and include the door details. I chose this guide over `locker-front.glb`, whose bounds are 0.8986 × 1.9919 × 0.5331 m and whose mid-height sections measure 0.7428 m wide by 0.4950 m deep. The hero guide is closer to the square 0.6 m footprint and preserves the better box proportions. I replaced its softened edges and lumpy plinth with planar low-poly surfaces.

The fitted carcass is 0.600 × 2.400 × 0.600 m. The plinth is 0.200 m high. The fixed surround is 0.040 m wide at each side, with a 0.055 m upper rail. The 0.480 × 2.120 m door sits 0.030 m behind the surround face, with its pivot at X=-0.240, Y=0.210, Z=0.258 m. The dark kick plate is 0.490 m wide and 0.150 m high. Its face is 0.040 m behind the front plane. Three horizontal louvre cuts sit at Y=2.100, 2.150 and 2.200 m. The handle pocket is 0.060 × 0.170 m and centred at Y=1.065 m. The hinge knuckles are at Y=0.355 and 2.085 m. Thirty low-poly rivets sit around the surround.

The supplied hero depicts upper and lower vent groups with four louvres each. The requested part layout calls for one upper group of three, so I used that configuration and omitted the lower group. I removed the guide's projecting base flange and kept the plinth within the 0.600 m footprint. The handle is a separate lever in a boolean-cut recess. The export has `PaintedSteel`, `BareSteel` and `DarkSteel` materials, UVs on every mesh, and the named parent relationships for the door, vents, handle, hinges and rivets.

The export verification reports bounds of 0.600000 × 2.400000 × 0.600000 m, within the 0.002 m tolerance. The door pivot error is below 0.000001 m on every axis. The 0° to 100° outward swing was checked at 1° steps with 0 intersections outside the 0.015 m hinge-edge clearance. The export has 4,156 triangles, 0 non-manifold edges, 0 degenerate faces and 0 flipped-normal checks. All seven required named nodes are present with the expected parents, every mesh has UVs, and all three materials are present. Re-exporting from the saved Blender source produced a byte-identical GLB with `cmp`.

To rebuild the editable source and export, run `/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python tools/blender/quarters/storage_locker_module/build.py -- --save-source --output assets/props/quarters/storage_locker_module.glb`. To export again from the saved source, omit `--save-source`. Run `verify.py` with the same Blender options and `-- --input assets/props/quarters/storage_locker_module.glb --report tools/blender/quarters/storage_locker_module/verify.json`.

The neutral studio renders are in the gitignored `tmp/fit/locker/` directory: `compare-hero.png`, `compare-front.png` and `turntable.png`. The hero sheet places the supplied image on the left and the fit render on the right. The turntable sheet contains 30°, 120°, 210° and 300° views.
