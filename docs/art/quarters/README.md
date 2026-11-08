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

## Locker materials

The locker has one mesh and two baked finishes, `as_built` and `aged`. The aged finish represents 1000 years in sealed, sterile, oxygenated air. It has flaked paint, orange-brown oxide, downward rust trails, pitted fittings and grey-brown dust. Neither finish contains biological growth or water stains.

I chose two albedo/normal/ORM atlas sets instead of an age uniform. This leaves the existing hatch, door and ship-shell shader unchanged. `app/quarters_props.gd` caches one material per registered prop and state, shares the hatch's CC0 steel, paint and oxide detail scans, and swaps materials without changing meshes, names, transforms or pivots. `app/shaders/quarters_steel.gdshader` uses the hatch's `steel_sampling.gdshaderinc` and physical 0.20 m detail pitch. Scan luminance adds grain without importing green pigment from the source scans.

The clean paint uses sRGB (0.473, 0.575, 0.556), derived from the fitted source's grey-green paint. Its hardware is bare steel; its kick plate is dark steel. Clean atlases have zero oxide and dust. Aged colour, roughness and tangent normals come from the same geometry masks, with edge-biased flakes, broad-face failure and dust on exposed upward faces. The atlas imports enable mipmaps and disable alpha-border repair because alpha stores oxide or dust rather than transparency. Otherwise the importer replaces intact-paint colour and ORM data near rust boundaries. The material registry preloads every runtime atlas so exported builds retain these dependencies.

`tools/blender/quarters_aging/bake_masks.py` accepts a blend and mesh or root object names. It reuses the hatch's joined bake context, conservative bevel footprints, Cycles AO and image writer. Each planar face gets an isometric island. Non-planar corner faces are triangulated before unfolding so projection cannot discard surface area. All objects are packed together with a three-pixel margin. The locker atlas is 2048 by 2048 at 304.55 px/m, with measured triangle densities from 304.30 to 304.72 px/m. UVs stay at that scale even when a narrow bevel needs a conservative bake sample. The overlap check reports zero overlapping raster interiors.

The fixed locker seed is 9501. `masks.json` beside the atlas describes every channel. `geometry_masks.png` packs AO, cavity, edge proximity and coverage into RGBA. `weather_masks.png` packs upward exposure, downward streak fields, contact and material class. Contact measures distance to other parts, excluding the sampled part. Individual connected rivets and hinge knuckles remain separate streak sources even when they share one object. Horizontal returns seed additional downward fields, including opening lips. Authoring geometry arrays stay in scratch rather than the runtime asset directory.

Regenerate from the repository root with the installed Blender:

```sh
/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python tools/blender/quarters_aging/bake_masks.py -- --blend tools/blender/quarters/storage_locker_module/locker-working.blend --objects Carcass Door --output assets/props/quarters/storage_locker_module --seed 9501 --fields tmp/mat/locker/geometry.npz --save-source --export assets/props/quarters/storage_locker_module.glb
/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python tools/quarters_aging/bake_finishes.py assets/props/quarters/storage_locker_module --fields tmp/mat/locker/geometry.npz
godot --headless --path . --editor --import
godot --path . -s tools/quarters_pilot_preview.gd
/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python tools/quarters_aging/locker_gates.py --captures tmp/mat/locker --masks assets/props/quarters/storage_locker_module/masks.json
```

Run long commands with `nohup` and logs under `tmp/mat/locker/`. `tools/quarters_pilot_preview.gd` accepts `--asset`, `--prop`, `--factory`, `--height` and `--out` after `--` for other pilot props. Use `--aged-asset` for a separate collapsed or torn mesh, `--factory none` to retain imported materials, `--centre-y` for a hanging origin and `--frame-size` for wider furniture. Rigid geometry assertions apply when both states use one asset. A material factory implements `apply(root, prop, state)`; albedo/ID diagnostics are captured only when its shader exposes the diagnostic uniform. The preview renders remembered, present and neutral lanes from hero, front and upper-door cameras, plus a top view for dust. Present lighting uses `Lighting.REGULAR_WHITE`, colour (1.0, 0.97, 0.90), and the regular fixture energy. Neutral pairs hold lighting constant. Capture-only unlit albedo and material/up-face ID passes use the same shader and cameras so colour measurements do not confuse lighting with aging.

The measured capture gates pass:

| Gate | Measured | Requirement |
| --- | --- | --- |
| Aged PaintedSteel rust, pooled hero and front pixels | 38.00% | 25% to 60% |
| Fasteners with downward rust trails | 70 of 71, 98.59% | At least 80% |
| Dust on visible up-facing surfaces | 97.47% | At least 70% |
| As-built rust | 0.00% | Under 1% |
| Total newly green area | 0.00% | Under 0.5% of prop pixels |
| Shared mesh, pivots, names and footprint | Identical | Identical |

The streak measurement probes ten rows below each fastener in the front capture and requires rust in at least 70% of the visible receiving rows. Four low fasteners have no visible PaintedSteel receiving surface and are excluded, with their count recorded in `gates.json`. The no-green gate compares each aged pixel against its clean counterpart at hue 70 to 170 degrees and saturation above 0.25. Existing grey-green paint is excluded. Python controls reject an introduced green patch, detect orange-brown rust and exclude background pixels.

The full `godot --headless --path . -s tests/run_tests.gd` run completed under `nohup` with 792 passed, 0 failed and exit code 0. Godot printed allocator teardown warnings at exit. All five Python capture-classifier controls pass. The unchanged locker geometry verifier passes with 5,416 triangles, no nonmanifold edges, no degenerate faces and no invalid normals. A second seeded bake produces byte-identical mask PNGs and GLB output.

The image sheets are `tmp/mat/locker/before-after.png`, `details.png`, `neutral-pair.png` and `front-pair.png`, with as-built left and aged right. Captures and `gates.json` stay in scratch. The designated image-review endpoint at `127.0.0.1:8308` refused connections, so the images have measured gates but no visual sign-off.

## Sofa

The fitted source is `tools/blender/quarters/sofa/sofa-working.blend`, and the game asset is `assets/props/quarters/sofa.glb`. The cushions and throw are baked Blender cloth meshes with no live modifiers. Authoring uses Blender Z up and front -Y. Export uses `export_yup=True`, giving the game +Y up and front +Z.

### Aged state

`tools/blender/quarters/sofa/sofa-aged.blend` holds the baked aged geometry, exported as `assets/props/quarters/sofa_aged.glb`. The selected construction is `pass2-o`; `cloth-trials.json` retains the earlier simulations and the second-pass attempts. The frame, feet and rivets keep their geometry bytes. The age remains 1000 years in dry, sterile, oxygenated air.

`quarters_aging/sofa_pass2.py` constructs slack covers with lowered centres, raised seam edges and asymmetric wrinkles. The visible seat centre is measured independently of the filling volume. Each cushion has two actual openings with ragged boundary fibres, thin closed cloth sections and a separate closed inner crust in the same named node. The earlier polygon patches are absent. The back sacks retain their bottoms and height, with most filling in the lower half and the thin upper cover leaning forward. These are directly constructed gravity-shaped surfaces, without a new cloth simulation.

The continuous oatmeal throw runs across the arm cap, around its outside edge and down toward the floor. It has two irregular holes, frayed boundaries and a detached floor remnant. The deck carries 192 closed foam crumbs; 36 smaller solids form the floor spill. Thread tips that cross the cloth are removed before rebuilding the thin section. No cloth or cushion faces are excluded from the final collision check.

All following measurements come from the exported GLB in `verify-aged.json`. Seat values are ordered L / C / R.

| Gate | Measured | Requirement |
| --- | --- | --- |
| Cover centre height above deck, relative to unaged | 39.293% / 39.193% / 39.296% | 35% to 45% |
| Edge-to-centre sag | 19.107 / 19.261 / 19.160 mm | At least 15 mm |
| Top height standard deviation after plane removal | 8.445 / 8.500 / 8.526 mm | At least 6 mm |
| Back-cushion first-hit hero coverage, L / C / R | 76.499% / 76.793% / 65.135% | At least 55% |
| Back top height retained | 99.544% on each | At least about 65% |
| Cover openings | Two per cushion, 123.815 to 136.802 mm | One to four per cushion, 20 to 150 mm |
| Opening perimeter divided by square root of area | 5.563 to 6.960 | At least 5.5 |
| Seat volume ratios, crust plus cover | 0.254962 / 0.254961 / 0.254987 | 0.25 to 0.35 |
| Back volume ratios, crust plus cover, L / C / R | 0.255009 / 0.254972 / 0.255001 | 0.25 to 0.35 |
| Qualifying foam crumbs | 170 of 192 deck pieces | At least 150, 2 to 15 mm, within 250 mm of a split |
| Qualifying crumbs resting on a surface | 100%; largest measured deck gap 0.343 mm | At least 60% within 2 mm |
| Throw area below arm cap | 85.509% | At least 40% |
| Detached throw piece | On floor | Floor or seat |
| Throw hole irregularity | 6.882 / 5.837 | At least 5.5 |
| Changed-part self-intersections / part-to-part intersections | 0 / 0 | 0 / 0 |
| Cushion and throw topology | Closed, zero nonmanifold edges | Closed or properly bounded |
| Closed crust | All six | All six |
| Triangles | 28,788 / 19,550 unaged, ratio 1.472532 | At most 29,325, ratio 1.5 |
| Fixed geometry bytes, original pivots and origins | Unchanged | Unchanged |
| Re-export from saved source | Byte-identical | Byte-identical |

The triangle test uses BVH candidates followed by triangle-triangle separating-axis tests, including coplanar overlap. It omits only shared-vertex adjacency from self checks. Unchanged frame joints are reported separately: 522 frame self-crossings and 272 frame/rivet crossings. Feet and rivets have zero self-crossings. The fixed geometry bytes are checked against the unaged export.

Re-export with Blender using `sofa/build.py -- --aged --output <file.glb>`. `quarters_aging/pass2.py -- --prop sofa --trial <name>` constructs a fresh trial from the unchanged fitted source. The final lit captures are `tmp/age/pass2/sofa-before-after.png`, `sofa-turntable.png` and `sofa-closeup.png`; the closeup camera is 0.6 m from the split-seat target. Unaged is left in the comparison. The image-comparer endpoint at `127.0.0.1:8308` refused connections, so appearance has no visual sign-off despite passing geometry gates.

### Why the shape gates changed

The previous 12 to 30 mm crown and 5 to 20 mm side-bulge windows admitted cushions that still looked flat against `docs/art/quarters/sheets/sofa/hero.png`. The seat gates now require a 35 to 50 mm crown, 15 to 30 mm side bulges, 160 to 190 mm height and fitted top-edge radii of at least 35 mm. Four diagonal corner sections must rise toward the top without pinching. Back front-face crowns must be 40 to 60 mm, with their existing width and height retained. The piping, neighbour-gap, support, contact, topology, winding, axis and intersection gates remain in place. The total triangle ceiling is 20,000; each cushion remains below 2,500 triangles.

These measurements come from the exported GLB, before and after the follow-up to `1547cad`:

| Measurement | Before | After |
| --- | --- | --- |
| Seat crown | 17.68 mm | 35.98 mm |
| Seat side bulges | 5.41 to 8.94 mm | 17.13 to 22.86 mm |
| Seat height | 150.00 mm | 180.45 mm |
| Back front crown | 23.90 mm | 41.63 mm |
| Back top-edge fitted radius | 24.96 mm | 49.41 mm |
| Foot-top distance to nearest frame surface | 79.23 to 123.10 mm | 0.15 mm on all four feet |
| Hanging-panel plane deviation | 8.74 mm | 22.05 mm |
| Hanging-panel fold peaks | 1 | 3 |
| Right seat top covered by throw | 79.82 percent | 8.56 percent |
| Throw components | 2 | 1 |
| Triangles | 17,324 | 19,550 |

The old global vertical bounds showed a 45 mm foot-to-frame separation. The nearest-surface gaps were larger because the feet also sat inward of the side rails. Four 190 by 110 mm mounting plates now bridge the feet to those rails. Their lower surfaces sit 0.15 mm above each foot, and their tops reach y=0.131 m. The new gate measures each foot's top vertices and top centre against the nearest frame surface above them, with a 0 to 1 mm limit.

### Cushion recipe

`cloth.py` builds a closed 660 by 700 by 180 mm shell on a 20 by 20 by 8 grid, with a 45 mm rounded-box radius. Its upper shoulders are inset 18 mm from the side-wall belly before simulation. This separates the inflated belly from the rounded upper seam instead of turning the whole upper shell into a narrow dome. The selected `seat-u` trial uses pressure 0.2, pressure scale 1, quality 20, tension and compression stiffness 500, shear 350, bending 10 and mass 0.015. Structural damping is 15, bending damping 2 and air damping 5. The underside is pinned during a 40-frame settle against the deck. Object collision distance is 1 mm, self-separation 2 mm and collision quality 6.

The settled shell is fitted to the seats and backs by `refit.py` and `assemble.py`. Seat body reduction targets 1,440 triangles, and back body reduction targets 1,210. The seats retain 660 by 700 mm footprints and centres at x=-0.67, 0 and 0.67 m. Back pads retain 660 mm width and 420 mm height. Their lower returns stay 40 mm deep behind the seats, reaching full depth between normalized heights 0.38 and 0.58. Surface-fitted 8 mm piping uses offsets of 4.70 mm on seats and 4.58 mm on backs. Its measured gaps and embeds remain below 1 mm.

The final seat edge radii are 51.02 to 58.40 mm. All four corner sections pass. Seat neighbour gaps are 10.11 mm, back gaps 10.07 mm and seat-to-deck gaps 0.25 to 0.49 mm. Exported triangle checks find no cushion-cushion or cushion-frame crossings.

Each corner plate has four 12 mm diameter, 3 mm high closed domed rivets. Their `BareSteel` material uses colour (0.48, 0.52, 0.54), metallic 0.85 and roughness 0.32 to contrast with the grey-green frame paint.

### Throw recipe

The selected `throw-l` is one continuous 4 mm thick wool sheet, 630 mm wide, with a 35 mm rolled turn over the arm. There is no second loose ply. Four initial gathered waves have 22 mm amplitude, fading to zero at the cap. The sheet starts 65 mm farther forward to clear the back cushion. The cap and rolled contact strip are pinned while the inside and outside hangs settle under gravity against the fitted furniture.

The 240-frame simulation uses quality 30, half-speed integration, mass 0.15, tension and compression stiffness 150, shear 80 and bending 0.7. Structural damping is 12, bending damping 3 and air damping 5. Self-separation is 5 mm, object collision distance 3 mm, collision quality 12 and collider friction 30. The initial profile is lowered 1 mm for cap clearance. Thickness is applied after simulation. Maximum movement over the last five frames is 0.0231 mm.

The exported hanging section at y=0.56 m deviates 22.05 mm from its fitted vertical plane and has three peaks with at least 6 mm prominence. Top-down ray sampling measures 8.56 percent right-seat coverage against the 30 percent ceiling. Three arm-roll sections fit radii of 34.88 to 34.92 mm. The circle fit uses geometric residuals so the two skins of the thick sheet do not bias its radius. Cap clearance is 1.95 mm, outside hang 434.00 mm and outward extension 47.82 mm. There are zero self-crossings, furniture crossings or measured furniture penetrations.

### Trials, export and captures

`cloth-trials.json` retains every earlier trial and records follow-up trials `seat-m` through `seat-u` and `throw-i` through `throw-l`, including failed fits and before/after gates. Increasing pressure alone overinflated the cushions. The denser rounded shell and inset shoulder produced the selected shape. The throw trials identified an inside rear hem initialized against the back cushion. Moving the sheet forward and holding its rolled contact strip removed that source of movement and twisting.

`build.py` clears unused mesh datablocks before assigning each mesh resource its node name. The GLB has ten named nodes with ten distinct, matching mesh resources. `verify.py`, `trimesh_verify.py` and `followup_gates.py` check the exported asset, including Blender BVH triangle crossings. `verify.json` passes every gate and confirms byte-identical re-export from the saved source.

Run `build.py` with Blender's `--background --factory-startup --python-exit-code 1 --python` options, then `-- --output assets/props/quarters/sofa.glb`. Repeat with `--output tmp/fit/sofa/cloth2/reexport.glb`. Run `verify.py` with the same Blender options and `-- --input assets/props/quarters/sofa.glb --report tools/blender/quarters/sofa/verify.json --reexport tmp/fit/sofa/cloth2/reexport.glb`. Long jobs use `nohup` and logs in that scratch directory.

The lit captures are `tmp/fit/sofa/cloth2/compare-hero.png`, `compare-detail.png`, `turntable.png` and `cushion-close.png`. The hero and detail sheets place the design beside the fitted asset. The turntable contains 30, 120, 210 and 300 degree views. Every view uses the same world fill and four area lights. The designated image-comparer endpoint at `127.0.0.1:8308` was unavailable, so these captures have no new visual rating.


## Tunic

The tunic now comes from Blender cloth simulation. The hand-modelled pilot rated 2/10: its waist was pinched, its sleeves were detached cylinders, and its collar and shoulders had visible voids. A sewn pattern lets gravity and fabric strain produce the hanging shape. The design remains `docs/art/quarters/sheets/dress_uniform/hero.png`; the filled Hunyuan torso is only a silhouette reference.

### Aged state

`tools/blender/quarters/dress_uniform/tunic-aged.blend` contains the baked aged cloth, exported as `assets/props/quarters/dress_uniform_aged.glb`. `cloth-trials.json` records the second-pass attempts and selected `pass2-n` bake alongside the earlier simulations. The age remains 1000 years in dry, sterile, oxygenated air, without biological or water damage.

`quarters_aging/tunic_pass2.py` releases a contiguous arc of one armhole, then lowers and twists that sleeve while retaining the back seam bridge. The original sewn pattern supplies the body; its shoulders drop and its waist contracts asymmetrically into folds. Four stress tears plus the open armhole have refined, displaced boundaries and short attached thread tips. Hem losses have varying lengths. This pass uses constrained geometric deformation, without a new cloth simulation.

The body is a double-sided, zero-thickness cloth midsurface with explicit neck, hem, cuff and tear boundary loops. The thick-shell trials crossed themselves around narrow folds. Before moving an edge vertex, the final construction checks that its incident triangles keep their orientation and at least 20% of their previous projected area. Thread tips crossing the body are removed. The garment has zero remaining non-adjacent triangle crossings. Verification still tests every remaining cloth face.

Brass details follow the cloth by rigid translation, while shoulder boards are fitted to the lowered shoulder surface. The placket, ribbon and medal remain separate named parts. The original collar facing crossed the collar band, so the aged source retains the band and insignia and removes the overlapping facing. The hanger geometry remains byte-identical. A closed FibreDust heap sits directly below the hem.

All following measurements come from the exported GLB in `verify-aged.json`:

| Gate | Measured | Requirement |
| --- | --- | --- |
| Tear boundaries | Five openings, irregularity 5.975 to 10.675 | At least 5.5 |
| Longest straight boundary run within 1 mm | 25.049 mm | At most 30 mm |
| Hem notch lengths, mean / standard deviation | 7.663 / 11.684 mm | Standard deviation at least 40% of mean |
| Hem standard deviation divided by mean | 1.52473 | At least 0.40 |
| Open armhole reference seam length | 62.213% | 50% to 70% |
| Mean shoulder drop | 15.680 mm | At least 15 mm |
| Front silhouette IoU | 0.740480 | 0.55 to 0.80 |
| Fibre heap height | 10.800 mm | At least 6 mm |
| Fibre heap diameter | 144.000 mm | 80 to 200 mm |
| Heap offset from point beneath hem centre | Less than 0.001 mm | At most 50 mm |
| Changed-part self-intersections / part-to-part intersections | 0 / 0 | 0 / 0 |
| Body topology | Nine unbranched boundary loops, zero nonmanifold edges | Only intended openings |
| Other changed-part topology | Closed, zero nonmanifold edges | Closed or properly bounded |
| Triangles | 9,901 / 13,768 unaged, ratio 0.719131 | At most 20,652, ratio 1.5 |
| Hanger geometry bytes, original pivots and origins | Unchanged | Unchanged |
| Re-export from saved source | Byte-identical | Byte-identical |

The collision test imports the exported GLB and uses BVH candidates plus triangle-triangle separating-axis tests, including coplanar overlap. The unchanged hanger has 28 self-crossing triangle pairs, reported separately. No garment or attachment pair is excluded.

Re-export with Blender using `dress_uniform/build.py -- --aged --output <file.glb>`. `quarters_aging/pass2.py -- --prop dress_uniform --trial <name>` constructs a fresh trial from the unchanged fitted source. Lit neutral sheets are `tmp/age/pass2/tunic-before-after.png` and `tunic-turntable.png`, with unaged left and aged right. The configured image-comparer endpoint at `127.0.0.1:8308` refused connections, so appearance has no visual sign-off despite passing geometry gates.

### Pattern and simulation

The front and back are flat panels, each cut on a 28 by 30 quad grid with UVs assigned before assembly. The pattern is 0.55 m across the shoulders, 0.48 m across each chest panel and about 0.75 m from shoulder to hem. Loose edges pair the side and shoulder seams for Blender sewing springs. The neck and armholes remain open during the torso simulation.

A 0.50 m steel hanger and a smooth 0.448 by 0.100 by 0.250 m upper-chest form support the cloth. The form stops at mid-chest and is excluded from export. Pins cover the 20 mm shoulder binding strip, with no pins or support at the waist or hem. The selected torso trial is `body-p`: 600 frames, quality 30, time scale 0.25, mass setting 0.22, tension/compression/shear stiffness 500/500/350, bending 0.3, structural damping 5, bending damping 0.5 and air damping 10. Placket interfacing raises local bending stiffness to 5. Sewing force is capped at 10. Collision and self-collision distances are both 4 mm. Stitch-adjacent faces are excluded from self-collision so paired edges can close. The largest spring gap before joining the stitches is 1.00 mm.

The two tapered sleeve tubes are placed within 2 mm of their armholes and joined into shared stitches before gravity settling. The torso is held in its baked pose. Trial `sleeve-h` uses 480 frames, quality 30, time scale 0.25 and bending 5, with the same stretch, damping and collision settings. The sleeves hang slightly forward and remain part of the continuous `TunicBody` mesh. Twelve local smoothing passes at factor 0.35 round the stitched armhole returns before applying 3.5 mm cloth thickness. This removes thickness crossings without replacing the simulated drape.

### Details and measured gates

The 43 mm standing collar has a recessed fabric facing around the hook, with at most 0.504 mm radial clearance around the steel wire. The shoulder boards follow the shoulder surface. The placket, six 14 mm brass domes, two 20 mm collar emblems, ribbon bar and 32 mm medal remain separate meshes. Rigid buttons and the medal are fitted to sampled cloth planes rather than warped onto individual triangles. The medal hangs from a short ribbon below the bar on the wearer's left breast, which is image-right.

`verify.py` measures the exported GLB with trimesh and writes `verify.json`. The final report passes every implemented gate:

| Measurement | Result | Limit |
| --- | --- | --- |
| Body width | 553.878 mm | 500 to 580 mm |
| Body depth | 184.205 mm | At most 220 mm |
| Hem height variation | 8.374 mm | At most 30 mm |
| Waist/chest width ratio | 0.9642 | At least 0.85 |
| Joined side, shoulder and armhole gaps | 0 mm | 2 mm body, 3 mm armhole |
| Underarm clearance below Y = -0.48 m, left/right | 48.119 / 49.043 mm | At least 10 mm |
| Cloth thickness | 3.49988 to 3.50012 mm | 3 to 4 mm |
| Cloth self-crossings and collider crossings | 0 | 0 |
| Largest detail attachment gap | 1.971 mm, medal | At most 2 mm |
| Shoulder-board attachment gaps | 0.900 mm | At most 1.5 mm |
| Largest inward detail penetration | 0.921 mm, medal | At most 1 mm |

The collar attachment gap is 1.714 mm, the button gap is 1.318 mm, and the emblem and ribbon-bar gaps are about 0.700 mm. The measured brass diameters are 14.009 mm for the buttons, 20.005 to 20.122 mm for the emblems and 32.004 mm for the medal. Motion over the last five simulation frames is 0.368 mm for the torso and 0.000924 mm for the sleeves, below the 1 mm settling limit. These motion measurements come from the simulation record, since a static GLB cannot measure settling.

### Export and trials

The baked source is `tools/blender/quarters/dress_uniform/tunic-working.blend`. Running `build.py` in Blender re-exports it byte-identically without rerunning physics. `simulate.py`, `sleeves.py` and `build.py --assemble` regenerate the selected stages; `settle_body.py` retains the joined-stitch experiment used in rejected trials. `construction.json` retains the collision geometry and attachment footprints needed for verification. `cloth-trials.json` records 16 torso trials, eight sleeve trials and ten detail/export trials, including failures. The selected combination is `body-p`, `sleeve-h` and `details-j`.

The exported asset is `assets/props/quarters/dress_uniform.glb`. It has 13,768 triangles against the 15,000 exclusive limit. The cloth is watertight with consistent winding. Authoring uses Blender Z-up and front -Y; export uses +Y up and front +Z. The origin is exactly at the hook top. Overall bounds, including sleeves, are 0.77110 m wide, 0.87889 m tall and 0.18420 m deep.

Node and mesh names are `TunicBody`, `Collar`, `ShoulderBoard_L`, `ShoulderBoard_R`, `Placket`, `Buttons`, `CollarInsignia_L`, `CollarInsignia_R`, `RibbonBar`, `Medal` and `Hanger`. Materials are `NaturalFabric`, `Brass`, `RibbonFabric` and `BareSteel`.

The neutral, light-grey comparison sheets are in `tmp/fit/tunic/sim/`: `compare-hero.png`, `turntable.png` and `compare-detail.png`. The hero uses a front-left orthographic view, and the turntable shows 30°, 120°, 210° and 300°. Four area lights illuminate the navy cloth, brass and steel from both sides. The PNG files were rendered and validated, but visual sign-off remains unavailable: the configured Qwen image endpoint refused connections, and the installed local alternative returned HTTP 500.
