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

`tools/blender/quarters/sofa/sofa-aged.blend` holds the applied aged geometry. The game export is `assets/props/quarters/sofa_aged.glb`. Settings are in `aging.json`, with trials `age-a` through `age-e` and the final `age-f-support-fit` placement pass in `cloth-trials.json`. The frame, feet and rivets retain their original geometry attribute and index bytes. Their rust belongs to the material pipeline.

The shared `tools/blender/quarters_aging/foam_collapse.py` compresses the six original cushion shells, splits them into 12 seeded Voronoi plates apiece and caps every cut. The seed starts at 9501 and advances by 101 per cushion. Cracks are 2.5 mm wide. The nominal volume factor is 0.31. Back pads reduce their depth to 0.70 with compensating height, then move 45 mm forward onto the frame deck. Each original cushion name and pivot is retained, with crust and cover in that node. FoamDebris is a separate mesh of oxidised brown fragments derived from the source geometry.

The covers settle with pressure zero, mass 0.025, stiffness 180, bending 0.2, quality 16 and time scale 0.35 for 100 frames. Rim stitches remain pinned, while the interior settles onto a continuous shrunken-core collider. That temporary collider bridges the narrow cracks and is not exported. Core reduction is 0.30 and cover reduction 0.80. A measured clearance fit after reduction keeps vertices outside the core envelope, with 2.5 mm nominal clearance and 0.4 mm cover thickness. The final support stage raycasts the actual curved frame beneath each crust and translates the baked cushion to a 0.6 mm gap. It preserves the object's pivot and leaves the frame untouched.

`cloth_decay.py` weakens the throw, releases most arm-cap pins and removes elongated fold splits with seed 10501. Part of the blanket falls onto the floor. The final settle uses quality 30, 400 frames, time scale 0.35, mass 0.15, stiffness 80 and bending 0.25. Self-distance is 5 mm, object distance 4.5 mm and collision quality 16. Narrow fibres extend from torn boundaries before thickness is applied. These are dry, brittle splits and foam oxidation after 1000 years in sterile, oxygenated air, without biological or water damage.

The exported measurements in `verify-aged.json` are:

| Cushion | Aged/unaged volume | Frame gap | Requirements |
| --- | --- | --- | --- |
| Seat L | 0.303061 | 0.591 mm | Volume 0.25 to 0.35, gap at most 3 mm |
| Seat C | 0.303714 | 0.599 mm | Volume 0.25 to 0.35, gap at most 3 mm |
| Seat R | 0.303274 | 0.597 mm | Volume 0.25 to 0.35, gap at most 3 mm |
| Back L | 0.295947 | 0.599 mm | Volume 0.25 to 0.35, gap at most 3 mm |
| Back C | 0.295742 | 0.599 mm | Volume 0.25 to 0.35, gap at most 3 mm |
| Back R | 0.295627 | 0.599 mm | Volume 0.25 to 0.35, gap at most 3 mm |

| Other aged gate | Result | Requirement |
| --- | --- | --- |
| Closed crust plates | All six cushion crusts closed | Closed |
| Missing reference throw surface | 22.277% | 10% to 30% |
| Triangles | 28,050, 1.43478 times unaged | At most 29,325, 1.5 times unaged |
| Frame, feet and rivet geometry bytes | Identical | Identical |
| Original names, pivots and origin | Unchanged | Unchanged |
| Re-export from the baked source | Byte-identical | Byte-identical |
| Sampled penetration involving changed geometry | 0 mm at tested closed surfaces | At most 1 mm |
| Absolute sampled depth, including retained frame joints | 37.272 mm | At most 1 mm, fails by 36.272 mm |
| Nonadjacent self-edge hits | Throw 453, seat L 6, seat R 7 | Zero for an intersection-free result |

The collision gate remains failed. The 37.272 mm frame-joint overlap is inherited from untouched geometry. The cloth edge hits prevent certification of the 1 mm self-penetration limit. The crust is closed, but the combined cover meshes still have open or nonmanifold components, so sampled volume penetration does not certify those covers. Trials record free covers that slipped off their cores, a throw with 44 percent loss, rim anchoring, thinner fibres, increased collision resolution and the support correction from a global frame height to the actual curved support surface.

Re-export with the existing Blender command for `sofa/build.py`, adding `-- --aged --output <file.glb>`. Regenerate the aged source with `quarters_aging/build.py` and this prop's unaged blend and `aging.json`. The lit neutral sheets are `tmp/age/sofa-before-after.png` and `tmp/age/sofa-turntable.png`, with the unaged sofa on the left of the comparison. The configured image-review endpoint refused connections, so these images have no visual sign-off.

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

`tools/blender/quarters/dress_uniform/tunic-aged.blend` contains the baked aged cloth. `assets/props/quarters/dress_uniform_aged.glb` is its game export. The settings are in `aging.json`, and trials `age-a` through `age-e` are appended to `cloth-trials.json`. The age is 1000 years in dry, sealed, sterile, oxygenated air. The damage consists of brittle wool splits and fallen fibres, without biological growth or water damage.

The shared `tools/blender/quarters_aging/cloth_decay.py` removes elongated, seeded stress splits from the original pattern surface, releases the outer shoulder stitches and settles the weakened body and sleeves under gravity. The final seed is 9521, with cloth mask seed 10521. Tension, compression and shear are 150, 150 and 105, bending is 0.08, mass is 0.18, quality is 30 and time scale is 0.25 over 320 frames. Object distance is 2 mm and self-distance is 4 mm. The lower side panels contract by 12 percent before settling. The back of the wearer's right sleeve cap retains a fabric bridge while its front seam tears. The exported cloth remains one connected piece.

The collar, shoulder boards, placket, brass, insignia and ribbon keep their original geometry. Their attachment patches retain the original 3.5 mm wool thickness. Hanging wool thins to 1.575 mm and the narrow edge fibres to 0.14 mm. The fibre tips extend 2 to 5 mm into the torn boundaries. `debris.py` scatters fragments derived from three source triangles into the separate FibreDust node. Its nominal floor is 0.95 m below the hook top, set by `drop_height_m`. The heap's radii are 0.22 and 0.07 m, with 5 mm central height and a 0.2 mm floor gap.

The exported measurements in `verify-aged.json` are:

| Aged gate | Result | Requirement |
| --- | --- | --- |
| Missing reference cloth surface | 11.576% | 8% to 25% |
| Front silhouette IoU | 0.702315 | 0.60 to 0.85 |
| Largest detail attachment gap | 1.969 mm | At most 2 mm |
| Triangles | 16,640, 1.20860 times unaged | At most 20,652, 1.5 times unaged |
| Hanger geometry attribute and index bytes | Identical | Identical |
| Original names, pivots and origin | Unchanged | Unchanged |
| Re-export from the baked source | Byte-identical | Byte-identical |
| Sampled penetration involving changed cloth | 0.256 mm | At most 1 mm |
| Absolute sampled depth, including the unchanged hanger joint | 3.234 mm | At most 1 mm, fails by 2.234 mm |
| Nonadjacent self-edge hits in the cloth | 180 | Zero for an intersection-free result |

The collision gate remains failed. The 3.234 mm hanger joint and 1.500 mm collar-facing overlap are inherited from untouched geometry. The 180 cloth edge hits prevent certification of the 1 mm self-penetration limit; their continuous depth is not measured. The trial record includes uniform thinning that opened the detail gaps, retained-thickness patches that restored them, narrower fibre sections and a retained back seam that stopped the sleeve falling completely free.

Re-export with the existing Blender command for `dress_uniform/build.py`, adding `-- --aged --output <file.glb>`. Regenerate the aged source with `quarters_aging/build.py` and this prop's unaged blend and `aging.json`. The lit neutral sheets are `tmp/age/tunic-before-after.png` and `tmp/age/tunic-turntable.png`. The former places unaged left and aged right under the same camera. The configured image-review endpoint refused connections, so these images have no visual sign-off.

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
