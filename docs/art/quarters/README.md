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

The input was `tmp/hy/sofa-hero.glb`, a single watertight mesh with 391,256 triangles. The fit uses a 2.2 × 0.95 × 0.85 m envelope. The editable source is authored in Blender's native Z-up frame, with height along +Z and the seat side facing -Y. The exporter sets `export_yup=True`, giving the game +Y up and the front toward +Z. Pass one incorrectly treated Blender Y as the height axis. Its in-Blender bounds check passed while the exported sofa lay on its side and was offset 54 mm in X.

Pass one showed broad white arm panels because the side cheeks were thin, flat sheets. The corner plates sat 2 mm off those panels, and their rivets sat about 1 mm off the surface. The pass-two arm panels have rounded caps and integrated sides. Corner plates and fasteners meet the surface, and the fasteners are included in the named frame mesh. The old throw held height constant while varying the depth axis, so the cloth stayed within the arm instead of hanging from it. The replacement is a folded 7 mm shell resting over the image-right cap and hanging 0.45 m down the outside.

Each of the three seat cushions measures 0.66 × 0.70 × 0.15 m, with 10 mm gaps and rounded edges. Each back cushion measures 0.66 × 0.20 × 0.42 m. Both groups have a shallow crown and 8 mm welt. The frame is grey-green, the upholstery charcoal and the throw oatmeal. Four short feet and the corner hardware are visible as distinct forms in the model.

The source and exporter are `tools/blender/quarters/sofa/sofa-working.blend` and `build.py`. `verify.py` loads the exported GLB through trimesh and writes its report. It checks the exported extrema against x [-1.1, 1.1], y [0, 0.85], z [-0.475, 0.475] m with a 5 mm tolerance, checks upward-facing seat-top normals, exact node names and duplicate geometry. The measured bounds are x [-1.1000, 1.1020], y [0, 0.8500], z [-0.4750, 0.4750] m. The seat top faces point +Y. The GLB has exactly ten named nodes and 12,664 triangles, below the 15,000 limit. Re-exporting from the saved Blender source produces a byte-identical GLB.

The pass-two render files are in gitignored `tmp/fit/sofa/pass2/`. `compare-hero.png` places the design beside the rendered model. `compare-detail.png` shows the arm and hardware close-up. `turntable.png` contains the 30°, 120°, 210° and 300° views.


## Tunic

The input guide is `tmp/hy/tunic-hero.glb`. It is a filled torso about 0.70 m deep, with a rounded back, pinched waist and fused armpits. I used its front silhouette and the placement of the collar, boards, button row, pockets and sleeves. I did not shrinkwrap the fitted mesh to the guide because its depth and fused underarms do not describe a hanging garment. The front design reference is `docs/art/quarters/sheets/dress_uniform/hero.png`.

The fitted tunic is 0.574 m wide, 0.9502 m tall and 0.1786 m deep in the exported GLB. Its origin is at the hook's top centre. The vertical bounds are -0.9502 to -0.00002 m, so the garment hangs below the origin. The GLB has +Y up and its front details face +Z. The fitting uses a 4 mm nested cloth shell for the body, a straight hanging back, a small front drape and a neck opening. Separate tubular sleeves begin below the body edge. Their measured armpit gaps are 14.7 mm on each side. The collar and shoulder boards sit as separate cloth parts. Five brass buttons form one row. The medal and ribbon bar sit on the wearer's left breast, which is image-right.

The named parts are `TunicBody`, `Sleeve_L`, `Sleeve_R`, `Collar`, `ShoulderBoard_L`, `ShoulderBoard_R`, `Buttons`, `CollarInsignia_L`, `CollarInsignia_R`, `RibbonBar`, `Medal` and `Hanger`. They use `NaturalFabric`, `Brass`, `RibbonFabric` and `BareSteel`. The Blender source and build and verify scripts are in `tools/blender/quarters/dress_uniform/`. The exported asset is `assets/props/quarters/dress_uniform.glb`.

The trimesh report confirms all named part meshes are closed and manifold after welding duplicated UV-seam vertices. Blender's exported-mesh BVH check finds no intersecting part pairs. The brass front-detail normals have maximum +Z components from 0.978 to 0.985. The asset has 4,108 triangles against the 12,000 limit. Re-exporting the saved Blender source produces a byte-identical GLB. `verify.py` writes `verify.json`.

The neutral comparison images are in `tmp/fit/tunic/`. `compare-hero.png` puts the design beside the fitted model from the front. `turntable.png` shows 30°, 120°, 210° and 300° views. `compare-detail.png` places a crop of the design's collar and breast insignia beside the rendered detail.
