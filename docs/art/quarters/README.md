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

The fitted carcass measures 0.600 × 2.400 × 0.600 m. The fixed surround is 0.040 m wide at each side, with a 0.055 m upper rail. The door is 0.514 × 2.220 m and starts 0.110 m above the floor. The source uses Blender's native Z-up frame, with height along +Z and the front toward -Y, then exports with `export_yup=True` for the game's +Y-up frame and +Z-facing front.

The earlier top and bottom panels stopped at the rear half-depth because their depth was copied from a rear return. The side and back panels also began 95 mm above the kick plate, leaving a gap. Pass four extends both horizontal panels across the full depth and lowers the carcass sides, back and bottom to the kick plate top at y=0.105 m. The 0.520 × 0.105 × 0.520 m DarkSteel kick plate stays set back 0.040 m.

The door has three angled louvre blades over dark-backed recesses. The blades now stand about 20 mm proud of the door face and angle down by 30 degrees. Folded perimeter returns make a 3 to 4 mm shadow gap around the door. The carcass outer vertical corners have 0.003 m chamfers.

Three hinge knuckles sit at y=0.35, 1.25 and 2.15 m. Each is 0.020 m in diameter and 0.080 m long, with the pivot on their axis. They stand proud of the front plane. The exported mesh has three connected components after positional vertex welding. The surround has 12 mm low-poly domed rivets at 0.135 m spacing along all four edges. Matching rivets run down the carcass front corners.

The handle pocket is 0.060 × 0.170 m. Its 0.110 m lever stands 14 mm proud of the door face. The export has `PaintedSteel`, `BareSteel` and `DarkSteel` materials, UVs on every mesh, and deliberate names for the aging toolkit.

The earlier verifier measured the Blender source and missed the open panel faces and the gaps in the carcass. Pass four checks the exported GLB with trimesh. Its 50 mm inward-ray grid covers all six body faces while omitting the kick-plate setback band, and reports zero misses. Hero-angle rays measure first-hit visibility for the hinges, handle and louvres, each with a 60 percent minimum. The report also checks body bounds, the door front normal and pivot, swing clearance from 0 to 100 degrees, named nodes, three welded hinge components, kick-plate setback, topology, a triangle count below 6,000, and byte-identical re-export.

To rebuild the editable source and export, run `/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python tools/blender/quarters/storage_locker_module/build.py -- --save-source --output assets/props/quarters/storage_locker_module.glb`. To export again from the saved source, omit `--save-source`. Run `verify.py` with the same Blender options and `-- --input assets/props/quarters/storage_locker_module.glb --report tools/blender/quarters/storage_locker_module/verify.json`. Run `trimesh_verify.py assets/props/quarters/storage_locker_module.glb` with the local Hunyuan3D virtual environment's Python to check the exported game axes.

The third-pass neutral renders are in the gitignored `tmp/fit/locker/pass3/` directory. `compare-hero.png` and `compare-front.png` show the locker upright. `turntable.png` contains the 30°, 120°, 210° and 300° views under main and fill lighting. `compare-detail.png` shows the door hardware.

## Sofa

The cushions and throw now use baked Blender cloth simulations. The shape guide remains `tmp/hy/sofa-hero.glb`, the 391,256-triangle Hunyuan mesh generated from the approved hero. The editable source is `tools/blender/quarters/sofa/sofa-working.blend`. It uses Blender's native Z-up frame, with the front facing -Y. `build.py` opens that saved source and exports with `export_yup=True`, giving the game +Y up and the front toward +Z. There are no live simulation or thickness modifiers in the saved source.

### Cushion method and measurements

`cloth.py` starts with a closed rounded box, divided 14 × 14 × 4 for 616 quads, with a 22 mm corner radius. The selected seat trial, `seat-k`, uses pressure 1, pressure scale 1, quality 20, tension and compression stiffness 500, shear stiffness 350, bending 5 and mass 0.015. Structural damping is 15, bending damping 2 and air damping 5. The underside is pinned during the 12-frame settle against a flat deck. Object collision distance is 1 mm, self-collision distance 2 mm and collision quality 6.

Before fitting, the settled shell measures 667.2 × 705.6 × 166.6 mm. Its crown is 19.66 mm and its four side bulges are 6.13 to 9.95 mm. It is closed and manifold, with zero nonadjacent self-intersections and 1,232 triangles. The baked mesh supplies all six cushions. The seat copies are scaled to 660 × 700 × 150 mm; their measured crowns are 17.68 mm and side bulges 5.41 to 8.94 mm. Their highest points remain at game y=0.540 m.

The back copies face forward and measure 660 × 420 × 200 mm in game X, Y and Z. Their lower returns compress to 40 mm behind the seats, reaching full depth above the seat backs. This avoids the original pads occupying the same space as the rear seats. The seat centres remain at x=-0.67, 0 and 0.67 m. Both rows have 10.00 mm neighbour gaps. Exported triangle checks find no cushion-cushion or cushion-frame crossings. Seat-to-deck gaps are 0.25 to 0.49 mm.

Each cushion has a joined 8 mm piping tube around its upper perimeter, including the front and rear edges. Surface rays fit 44 six-sided rings on each seat and 76 on each back. The seat pipe's maximum surface gap is 0.442 mm and maximum embed is 0.159 mm. The back pipe's maximum gap is 0.950 mm and maximum embed 0.969 mm. Both stay within the 1 mm surface band. Seat cushions have 1,760 triangles each including piping; backs have 1,996 each.

The original arm interiors overlapped the seat edges. `assemble.py` preserves the exterior arm and hardware positions while narrowing the cheeks to 75 mm and caps to 80 mm. It lowers the front rail 18 mm, fills the support deck to 700 mm depth with its top at y=0.390 m, and moves the rear rails and uprights clear of the back pads. Final decimation ratios are 0.52 for the frame, 0.35 for the feet, 0.32 for rivets and 0.88 for back cushion bodies. These parts retain closed surfaces and outward winding.

### Throw method and measurements

`throw.py` represents a once-folded 1.3 × 1.5 m sheet as two 0.65 × 1.5 m plies. The selected `throw-g` trial uses a 24 × 12 quad grid per ply, wool stiffness 100/100/50, bending 0.1, mass 0.15, quality 30 and half-speed integration. Structural damping is 12, bending damping 3 and air damping 5. Self-collision stays on at 4 mm, object collision distance is 4 mm and collision quality 12. The arm-cap contact strip is pinned; the rest settles under gravity against the arm and seat colliders with friction 20. It runs for 180 frames. Maximum movement over the last five frames is 0.495 mm.

Each ply receives 6 mm thickness after simulation. A measured 2 mm upward bake clearance removes the remaining triangle-edge crossings at the rounded cap. A 0.30 mm trial lift still left 20 crossings, so it was not accepted. The final cap gap is 1.988 mm, the outside hang 444.24 mm and outward extension 38.29 mm. There are zero self-intersections, ply-ply crossings or throw-furniture crossings. The throw is a closed manifold mesh with two components and 2,592 triangles. It hangs over the positive-X arm, which is image-right in the fixed hero camera.

### Trials and verification

Full settings, failed measurements and changes are recorded in `tools/blender/quarters/sofa/cloth-trials.json`. Cushion trials `seat-a` through `seat-j` tested pressure from 0.001 to 10, pressure scales 0.001 to 1, lower fabric stiffness and bottom anchors. They produced excess footprints, shallow or excessive crowns, folded side walls or incomplete runs. Increasing solver quality and upholstery stiffness produced the passing `seat-k`; increasing its pressure to 3 in `seat-l` raised the height to 179.99 mm and crown to 33.47 mm, so it was rejected.

The throw trials exposed two initialization defects: vertical offsets made the hanging plies overlap, and the first placement crossed the back cushion. Offsetting along the cloth normal and moving the sheet forward removed those initial crossings. The connected fold still moved too much. Trial `throw-d` extended 65.45 mm beyond the frame and `throw-e` extended 105.27 mm. Impulse clamps in `throw-f` did not fix it. Separating the two folded plies in `throw-g` produced the settled result. A sequential-ply alternative, `throw-h`, left the upper ply moving 244.84 mm over its last five frames and was rejected.

`verify.py` measures the exported GLB through `trimesh_verify.py` and uses Blender BVHs on those exported triangles for intersection checks. `verify.json` records all shape, support, piping, manifold, winding, normal, node, geometry and triangle gates. The source exports exactly the ten required nodes with ten distinct mesh resources. Seat-top normals have maximum +Y components of 0.999919. Total cost is 17,324 triangles against the 18,000 limit. The measured game bounds are x [-1.10003, 1.13829], y [0.00030, 0.84966], z [-0.47500, 0.47796] m. The extended X bound includes the throw. Re-export from the saved source is byte-identical.

Run `build.py` with Blender's `--background --factory-startup --python-exit-code 1 --python` options, followed by `-- --output assets/props/quarters/sofa.glb`. Repeat with `--output tmp/fit/sofa/cloth/reexport.glb`. Run `verify.py` with the same Blender options and `-- --input assets/props/quarters/sofa.glb --report tools/blender/quarters/sofa/verify.json --reexport tmp/fit/sofa/cloth/reexport.glb`. Long jobs run under `nohup` with logs in the same scratch directory. `assemble.py` accepts an explicit pre-cloth `--frame-source` and the selected cushion trial; routine exports need only the saved source.

The neutral light-grey captures are in gitignored `tmp/fit/sofa/cloth/`, using grey-green steel, charcoal upholstery and oatmeal wool. `cushion-step1.png` is the settled-shell close-up. `compare-hero.png` places the design on the left and the fixed-angle render on the right. `compare-detail.png` compares the image-right arm and throw. `turntable.png` contains 30°, 120°, 210° and 300° views, with fill lighting on every side. The image-comparer review could not run because its local endpoint at `127.0.0.1:8308` returned connection errors. The geometry gates pass; visual agreement with the design remains unreviewed.


## Tunic

The input guide is `tmp/hy/tunic-hero.glb`. It is a filled torso about 0.70 m deep, with a rounded back, pinched waist and fused armpits. I used its front silhouette and the placement of the collar, boards, button row, pockets and sleeves. I did not shrinkwrap the fitted mesh to the guide because its depth and fused underarms do not describe a hanging garment. The front design reference is `docs/art/quarters/sheets/dress_uniform/hero.png`.

The fitted tunic is 0.574 m wide, 0.9502 m tall and 0.1786 m deep in the exported GLB. Its origin is at the hook's top centre. The vertical bounds are -0.9502 to -0.00002 m, so the garment hangs below the origin. The GLB has +Y up and its front details face +Z. The fitting uses a 4 mm nested cloth shell for the body, a straight hanging back, a small front drape and a neck opening. Separate tubular sleeves begin below the body edge. Their measured armpit gaps are 14.7 mm on each side. The collar and shoulder boards sit as separate cloth parts. Five brass buttons form one row. The medal and ribbon bar sit on the wearer's left breast, which is image-right.

The named parts are `TunicBody`, `Sleeve_L`, `Sleeve_R`, `Collar`, `ShoulderBoard_L`, `ShoulderBoard_R`, `Buttons`, `CollarInsignia_L`, `CollarInsignia_R`, `RibbonBar`, `Medal` and `Hanger`. They use `NaturalFabric`, `Brass`, `RibbonFabric` and `BareSteel`. The Blender source and build and verify scripts are in `tools/blender/quarters/dress_uniform/`. The exported asset is `assets/props/quarters/dress_uniform.glb`.

The trimesh report confirms all named part meshes are closed and manifold after welding duplicated UV-seam vertices. Blender's exported-mesh BVH check finds no intersecting part pairs. The brass front-detail normals have maximum +Z components from 0.978 to 0.985. The asset has 4,108 triangles against the 12,000 limit. Re-exporting the saved Blender source produces a byte-identical GLB. `verify.py` writes `verify.json`.

The neutral comparison images are in `tmp/fit/tunic/`. `compare-hero.png` puts the design beside the fitted model from the front. `turntable.png` shows 30°, 120°, 210° and 300° views. `compare-detail.png` places a crop of the design's collar and breast insignia beside the rendered detail.
