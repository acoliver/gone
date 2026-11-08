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

The aged locker now follows the hatch's complete-face image method in `tools/prepare_hatch_paint.py`. Each visible face gets a separate FLUX.2-klein edit of a saved concept crop at that face's aspect ratio. The generated image supplies its complete paint/rust layout, ragged borders, trails and variation. Earlier procedural masks kept imposing recognisable islands and straight edge bands on generated swatch colours. That compositing path is no longer used by the aged material. The ship has been adrift about 1000 years.

The three as-built atlases remain byte-identical to `2fecbce`. Both states share the same replacement hinge mesh; state changes still preserve meshes, pivots, part names and footprint. The unchanged clean material keeps its original UV1 and shader path. The separately exported hinge mesh transfers UV1 from the fitted source, without rebuilding the other locker geometry.

### Faces, sources and selection

`art-source/quarters/locker/faces/` retains source crops, resized inputs, prompts, raw candidates, seeds, calibration metadata and selected final images. Every face has at least four generated seeds. Generation uses the installed FLUX.2-klein-4B, four steps, 4-bit weights, sequential jobs under `nohup`, and no installs. Sources are the locker/wardrobe panels in `concept-now.png` and door/heavy-corrosion regions in `hatch-concept-rusted.png`. Exact XYXY crops are in `face-layout.json`; each generation metadata file records its own input and full prompt. Thin vent and handle placement guides enter the door input only, not the atlas.

The atlas is 2048 by 4096. UV rectangles below use image origin at the upper left and exclusive right/bottom. Physical dimensions are width by height; top uses width by depth. Image pixels map directly to each face, without retiling its paint/rust pattern.

| Face | Metres | UV rectangle | px/m, X / Y | Selected seed |
| --- | --- | --- | --- | --- |
| door | 0.514000, 2.220000 | 0.003906, 0.001953, 0.253906, 0.548828 | 996.108949, 1009.009009 | 96001 |
| left | 0.560000, 2.295000 | 0.339844, 0.001953, 0.433594, 0.189453 | 342.857143, 334.640523 | 95511 |
| right | 0.560000, 2.295000 | 0.441406, 0.001953, 0.535156, 0.189453 | 342.857143, 334.640523 | 95523 |
| top | 0.556000, 0.580000 | 0.542969, 0.001953, 0.792969, 0.134766 | 920.863309, 937.931034 | 96130 |
| stile-left | 0.040000, 2.180000 | 0.261719, 0.001953, 0.292969, 0.853516 | 1600.000000, 1600.000000 | 95742 |
| stile-right | 0.040000, 2.180000 | 0.300781, 0.001953, 0.332031, 0.853516 | 1600.000000, 1600.000000 | 95652 |
| header | 0.520000, 0.055000 | 0.339844, 0.193359, 0.808594, 0.220703 | 1846.153846, 2036.363636 | 95562 |
| kick | 0.520000, 0.105000 | 0.339844, 0.224609, 0.652344, 0.255859 | 1230.769231, 1219.047619 | 95572 |
| hardware | 0.200000, 0.200000 | 0.339844, 0.259766, 0.839844, 0.509766 | 5120.000000, 5120.000000 | 95582 |

The hardware cell is a generated heavy-corrosion swatch at a 0.20 m square physical pitch. Knuckles unwrap by circumference and axial distance. Other hardware repeats only this fine corrosion swatch at equal physical pitch on both axes. It is not stretched across a thin lever or a whole rivet assembly. The rear and underside reuse the side image; these hidden surfaces are not additional generated front faces.

Selection measures source colour, planar lighting gradient, physical secondary autocorrelation and edge/broad rust ratio. Spatially uniform colour transforms remove the lighting plane and match source pigment statistics without a spatial wear mask. `candidate-scores.json` and `finish-scores.json` retain failed candidates as failures. `selection.json` records the selected calibration and final scores. Image-comparer selected top seed 96130 for fine soft dust and rejected candidates with cloudy patches, branching streaks or heavy dark margins.

| Face | Seed | Whole-image ΔE00 | Paint mean / std ΔE | Rust mean / std ΔE | Gradient | Secondary peak | Edge/broad rust |
| --- | --- | --- | --- | --- | --- | --- | --- |
| door | 96001 | 3.3066 | 4.6476 / 1.1093 | 0.2383 / 0.3293 | 0.001791 | 0.3247 | 2.7828 |
| left | 95511 | 4.7546 | 2.9443 / 3.3151 | 2.1724 / 1.4102 | 0.015130 | 0.4251 | 11.9274 |
| right | 95523 | 4.1122 | 4.0846 / 3.7576 | 0.4603 / 1.5036 | 0.027217 | 0.3265 | 30.7623 |
| top | 96130 | 2.7834 | 1.1178 / 3.3575 | 1.0361 / 0.6214 | 0.006491 | 0.2998 | 4.8430 |
| stile-left | 95742 | 7.8011 | 4.1494 / 6.7610 | 3.4158 / 0.4530 | 0.018272 | 0.2564 | 2.0936 |
| stile-right | 95652 | 4.7265 | 7.7524 / 7.9608 | 5.6609 / 2.3618 | 0.004379 | 0.2141 | 1.9925 |
| header | 95562 | 6.7059 | 7.9242 / 6.3702 | 4.7464 / 2.8335 | 0.008121 | 0.2274 | 1.9248 |
| kick | 95572 | 4.7967 | 4.4863 / 3.0667 | 2.3500 / 1.4555 | 0.016849 | 0.2165 | 2.0487 |
| hardware | 95582 | 1.1580 | 1.7400 / 0.9463 | 0.7178 / 0.3316 | 0.000001 | 0.0731 | 0.9704 |

### Relief, hardware and dust

The hatch's unchanged `paint_fields()` chroma rule derives raised paint from the selected image. It supplies the 1.5 mm paint relief, normal and roughness. It never composites paint and rust colours. The shader differentiates that same image-derived height in physical space. A 12 mm scan contributes at most 2.5% high-frequency paint grain; it cannot place wear or shift the generated boundaries. The previous procedural island, curvature-loss and full-strength analytic-streak composition is no longer used. Only the permitted low-opacity, image-coloured fixture stains remain as additions. Historical generator modules remain only for their existing regression fixtures and old reproduction tools; the clean bake still uses its original microscopic grain.

The original knuckles had 16 flat-shaded sides, producing 22.5-degree steps. `hinge_finish.py` exports 48-sided cylinders with smooth side normals and 0.7 mm end-rim bevels with seven segments. Exported triangle adjacency includes the end rims, with no cap exclusion; coincident split normals are also measured outside Blender. An unused automatically generated bevel UV layer was removed after it caused tiny nondeterministic export differences; only the transferred UV1 is exported. The first generated hardware mapping also stretched a square swatch across the thin handle. Equal 0.20 m physical pitch removes that anisotropy. Hardware pitting comes from its own generated image's linear luminance, with no independent pattern field.

Optional fixture stains use at most 30% linear-light opacity and pigment sampled from rust in the same receiving image. They leave existing image corrosion untouched. Positions come from actual hinge/rivet outlets, with tapered ends. They do not replace image-owned wear. The generated top already includes its fine soft dust; no cloudy density mask is composited over it. Seed 96230 edits that selected final top to illustrate dust removal. Because an image edit can change substrate detail, this is not treated as a matched numerical effect-disabled control.

### Gates and changes

**126 of 126 current gates pass.** Complete values and thresholds are in `art-source/quarters/locker/faces/gates.json` and reproduced below. Fractions use 0 to 1; distances use metres unless specified. Hardware is exempt from the painted-edge rust ratio because its swatch is deliberately corroded throughout. Every painted face requires the requested ratio of at least 1.8.

The following design-specific gates are retired, rather than marked as passes. As-built and colour-statistic checks remain.

| Retired gate | Reason |
| --- | --- |
| `dust_grain_std_ratio` | Compared a procedural dust-density field with its smoothed control. Dust is now in the complete generated top image. |
| `broad_face_island_max_m` | Measured placed blister instances; there are no placed islands in the image-owned layout. |
| `unattached_runoff_max` | Measured the removed analytic runoff control texture; new supplementary stains are baked at bounded opacity. |
| `streak_width_median_m` | Measured half-opacity contours of the removed full-opacity analytic generator. |
| `streak_source_length_range_m` | Preset source lengths no longer decide the corrosion layout. |
| `streak_reduced_opacity_max` | Replaced the old less-than-one generator opacity by the explicit <=0.30 limit. |
| `panel_edge_rust_cv_min` | Measured variability of the old procedural edge band, replaced by independently measured image edge/broad rust ratios. |
| `fasteners_with_streaks, visible_fastener_streaks_{albedo,neutral,present}` | The old >=50% population of strong 40 mm generated trails required a stamped fixture distribution and >=0.03 contrast. Image-owned trails and optional <=30% stains replace that generator contract; connected-run measurements remain diagnostics, not passes. |
| `dust_linear_difference_{albedo,neutral,present}` | The old control disabled a separate dust mask while retaining identical substrate. Dust is now part of the top image. A generated dust-removal edit is illustrative and is not a numerically matched effect-disabled control; differences remain diagnostics, not visibility passes. |

The old swatch colour and correlation gates become per-face checks at the same thresholds. The procedural-path edge/broad ratio of 2.5 becomes the requested 1.8. Rendered boundary-orientation, straight-boundary and secondary-correlation checks remain independent of source-image statistics. Legacy connected-trail measurements and generated dust-control differences remain in `gates.json` as diagnostics, without being counted as successful gates.

| Gate | Value | Threshold | Result |
| --- | --- | --- | --- |
| `face_door_delta_e` | 3.306598 | <=8 D65 Lab | PASS |
| `face_door_planar_light_gradient` | 0.001791 | <0.06 linear luminance across full image | PASS |
| `face_door_secondary_autocorrelation` | 0.324652 | <=0.5 at secondary peaks beyond 50 mm | PASS |
| `face_door_edge_broad_ratio` | 2.782825 | >=1.8, outer 10% against broad interior | PASS |
| `face_door_paint_mean_delta_e` | 4.647622 | <=8 D65 Lab | PASS |
| `face_door_paint_std_delta_e` | 1.109332 | <=8 D65 Lab | PASS |
| `face_door_rust_mean_delta_e` | 0.238326 | <=8 D65 Lab | PASS |
| `face_door_rust_std_delta_e` | 0.329309 | <=8 D65 Lab | PASS |
| `face_door_pixels_per_metre` | 996.108949 | >=600 | PASS |
| `face_left_delta_e` | 4.754643 | <=8 D65 Lab | PASS |
| `face_left_planar_light_gradient` | 0.015130 | <0.06 linear luminance across full image | PASS |
| `face_left_secondary_autocorrelation` | 0.425134 | <=0.5 at secondary peaks beyond 50 mm | PASS |
| `face_left_edge_broad_ratio` | 11.927444 | >=1.8, outer 10% against broad interior | PASS |
| `face_left_paint_mean_delta_e` | 2.944305 | <=8 D65 Lab | PASS |
| `face_left_paint_std_delta_e` | 3.315121 | <=8 D65 Lab | PASS |
| `face_left_rust_mean_delta_e` | 2.172395 | <=8 D65 Lab | PASS |
| `face_left_rust_std_delta_e` | 1.410204 | <=8 D65 Lab | PASS |
| `face_left_pixels_per_metre` | 334.640523 | >=300 | PASS |
| `face_right_delta_e` | 4.112159 | <=8 D65 Lab | PASS |
| `face_right_planar_light_gradient` | 0.027217 | <0.06 linear luminance across full image | PASS |
| `face_right_secondary_autocorrelation` | 0.326461 | <=0.5 at secondary peaks beyond 50 mm | PASS |
| `face_right_edge_broad_ratio` | 30.762305 | >=1.8, outer 10% against broad interior | PASS |
| `face_right_paint_mean_delta_e` | 4.084645 | <=8 D65 Lab | PASS |
| `face_right_paint_std_delta_e` | 3.757606 | <=8 D65 Lab | PASS |
| `face_right_rust_mean_delta_e` | 0.460318 | <=8 D65 Lab | PASS |
| `face_right_rust_std_delta_e` | 1.503564 | <=8 D65 Lab | PASS |
| `face_right_pixels_per_metre` | 334.640523 | >=300 | PASS |
| `face_top_delta_e` | 2.783428 | <=8 D65 Lab | PASS |
| `face_top_planar_light_gradient` | 0.006491 | <0.06 linear luminance across full image | PASS |
| `face_top_secondary_autocorrelation` | 0.299796 | <=0.5 at secondary peaks beyond 50 mm | PASS |
| `face_top_edge_broad_ratio` | 4.842975 | >=1.8, outer 10% against broad interior | PASS |
| `face_top_paint_mean_delta_e` | 1.117767 | <=8 D65 Lab | PASS |
| `face_top_paint_std_delta_e` | 3.357512 | <=8 D65 Lab | PASS |
| `face_top_rust_mean_delta_e` | 1.036111 | <=8 D65 Lab | PASS |
| `face_top_rust_std_delta_e` | 0.621441 | <=8 D65 Lab | PASS |
| `face_top_pixels_per_metre` | 920.863309 | >=300 | PASS |
| `face_stile-left_delta_e` | 7.801056 | <=8 D65 Lab | PASS |
| `face_stile-left_planar_light_gradient` | 0.018272 | <0.06 linear luminance across full image | PASS |
| `face_stile-left_secondary_autocorrelation` | 0.256412 | <=0.5 at secondary peaks beyond 50 mm | PASS |
| `face_stile-left_edge_broad_ratio` | 2.093593 | >=1.8, outer 10% against broad interior | PASS |
| `face_stile-left_paint_mean_delta_e` | 4.149431 | <=8 D65 Lab | PASS |
| `face_stile-left_paint_std_delta_e` | 6.760951 | <=8 D65 Lab | PASS |
| `face_stile-left_rust_mean_delta_e` | 3.415797 | <=8 D65 Lab | PASS |
| `face_stile-left_rust_std_delta_e` | 0.452955 | <=8 D65 Lab | PASS |
| `face_stile-left_pixels_per_metre` | 1600.000000 | >=300 | PASS |
| `face_stile-right_delta_e` | 4.726517 | <=8 D65 Lab | PASS |
| `face_stile-right_planar_light_gradient` | 0.004379 | <0.06 linear luminance across full image | PASS |
| `face_stile-right_secondary_autocorrelation` | 0.214115 | <=0.5 at secondary peaks beyond 50 mm | PASS |
| `face_stile-right_edge_broad_ratio` | 1.992473 | >=1.8, outer 10% against broad interior | PASS |
| `face_stile-right_paint_mean_delta_e` | 7.752382 | <=8 D65 Lab | PASS |
| `face_stile-right_paint_std_delta_e` | 7.960829 | <=8 D65 Lab | PASS |
| `face_stile-right_rust_mean_delta_e` | 5.660857 | <=8 D65 Lab | PASS |
| `face_stile-right_rust_std_delta_e` | 2.361817 | <=8 D65 Lab | PASS |
| `face_stile-right_pixels_per_metre` | 1600.000000 | >=300 | PASS |
| `face_header_delta_e` | 6.705902 | <=8 D65 Lab | PASS |
| `face_header_planar_light_gradient` | 0.008121 | <0.06 linear luminance across full image | PASS |
| `face_header_secondary_autocorrelation` | 0.227420 | <=0.5 at secondary peaks beyond 50 mm | PASS |
| `face_header_edge_broad_ratio` | 1.924838 | >=1.8, outer 10% against broad interior | PASS |
| `face_header_paint_mean_delta_e` | 7.924178 | <=8 D65 Lab | PASS |
| `face_header_paint_std_delta_e` | 6.370245 | <=8 D65 Lab | PASS |
| `face_header_rust_mean_delta_e` | 4.746393 | <=8 D65 Lab | PASS |
| `face_header_rust_std_delta_e` | 2.833491 | <=8 D65 Lab | PASS |
| `face_header_pixels_per_metre` | 1846.153846 | >=300 | PASS |
| `face_kick_delta_e` | 4.796706 | <=8 D65 Lab | PASS |
| `face_kick_planar_light_gradient` | 0.016849 | <0.06 linear luminance across full image | PASS |
| `face_kick_secondary_autocorrelation` | 0.216525 | <=0.5 at secondary peaks beyond 50 mm | PASS |
| `face_kick_edge_broad_ratio` | 2.048747 | >=1.8, outer 10% against broad interior | PASS |
| `face_kick_paint_mean_delta_e` | 4.486262 | <=8 D65 Lab | PASS |
| `face_kick_paint_std_delta_e` | 3.066661 | <=8 D65 Lab | PASS |
| `face_kick_rust_mean_delta_e` | 2.349953 | <=8 D65 Lab | PASS |
| `face_kick_rust_std_delta_e` | 1.455520 | <=8 D65 Lab | PASS |
| `face_kick_pixels_per_metre` | 1219.047619 | >=300 | PASS |
| `face_hardware_delta_e` | 1.157993 | <=8 D65 Lab | PASS |
| `face_hardware_planar_light_gradient` | 0.000001 | <0.06 linear luminance across full image | PASS |
| `face_hardware_secondary_autocorrelation` | 0.073121 | <=0.5 at secondary peaks beyond 50 mm | PASS |
| `face_hardware_paint_mean_delta_e` | 1.739994 | <=8 D65 Lab | PASS |
| `face_hardware_paint_std_delta_e` | 0.946332 | <=8 D65 Lab | PASS |
| `face_hardware_rust_mean_delta_e` | 0.717796 | <=8 D65 Lab | PASS |
| `face_hardware_rust_std_delta_e` | 0.331606 | <=8 D65 Lab | PASS |
| `face_hardware_pixels_per_metre` | 5120.000000 | >=300 | PASS |
| `knuckle_adjacent_face_angle_max_deg` | 12.996104 | <=15 degrees, all exported knuckle adjacency including rounded end rims | PASS |
| `knuckle_split_normal_jump_max_deg` | 6.423121 | <=15 degrees, all exported knuckle adjacency including rounded end rims | PASS |
| `byte_identical_bakes` | True | True | PASS |
| `as_built_atlases_unchanged` | True | True | PASS |
| `as_built_exported_uv_density` | 304.127508, 304.844790 | 304.6 +/-15% px/m | PASS |
| `as_built_exported_uv_no_stretch` | 1.001787 | <=1.015 | PASS |
| `paint_roughness_range` | 0.349020, 0.549020 | .34 <= minimum; maximum <= .56; span >= .12 | PASS |
| `as_built_rust` | 0.000000 | <0.01 | PASS |
| `aged_painted_rust` | 0.252922 | [.25,.60] | PASS |
| `no_new_green` | 0.000004 | <0.005 | PASS |
| `up_face_dust` | 0.797302 | >=0.70 | PASS |
| `identical_geometry` | True | True | PASS |
| `broad_face_rust_albedo` | 0.149709 | [.08,.25] | PASS |
| `edge_broad_ratio_albedo` | 3.294882 | >=1.8, replaces procedural-path >=2.5 | PASS |
| `dust_warm_low_saturation_albedo` | 0.817760 | >=0.70 | PASS |
| `broad_face_rust_neutral` | 0.142193 | [.08,.25] | PASS |
| `edge_broad_ratio_neutral` | 3.373030 | >=1.8, replaces procedural-path >=2.5 | PASS |
| `dust_warm_low_saturation_neutral` | 0.821022 | >=0.70 | PASS |
| `broad_face_rust_present` | 0.191413 | [.08,.25] | PASS |
| `edge_broad_ratio_present` | 2.878184 | >=1.8, replaces procedural-path >=2.5 | PASS |
| `dust_warm_low_saturation_present` | 0.752953 | >=0.70 | PASS |
| `aged_bare_steel_rust` | 0.923957 | >=0.30 | PASS |
| `as_built_bare_steel_linear_luminance` | 0.476270 | >=0.35 | PASS |
| `as_built_bare_steel_roughness_max` | 0.391573 | <=0.45 | PASS |
| `as_built_design_delta_e_2000` | 1.529041 | <=6 | PASS |
| `closeup_atlas_axis_peak_ratio` | 1.619847 | <=2.0 | PASS |
| `door_secondary_autocorrelation` | 0.310291 | <=0.5 beyond 50 mm, actual rendered door | PASS |
| `longest_straight_rust_boundary_m` | 0.038965 | <=0.040 at <=1 mm chord deviation | PASS |
| `hardware_Rivets_rust` | 0.878400 | >=0.30 | PASS |
| `hardware_Rivets_chroma_rust` | 0.656800 | >=0.30 | PASS |
| `hardware_Rivets_pit_normal_rms` | 0.016612 | >=0.01 | PASS |
| `hardware_Hinges_rust` | 0.871071 | >=0.30 | PASS |
| `hardware_Hinges_chroma_rust` | 0.613214 | >=0.30 | PASS |
| `hardware_Hinges_pit_normal_rms` | 0.017255 | >=0.01 | PASS |
| `hardware_DoorVents_rust` | 0.953859 | >=0.30 | PASS |
| `hardware_DoorVents_chroma_rust` | 0.789616 | >=0.30 | PASS |
| `hardware_DoorVents_pit_normal_rms` | 0.015925 | >=0.01 | PASS |
| `hardware_Handle_rust` | 0.936047 | >=0.30 | PASS |
| `hardware_Handle_chroma_rust` | 0.720930 | >=0.30 | PASS |
| `hardware_Handle_pit_normal_rms` | 0.016207 | >=0.01 | PASS |
| `hardware_KickPlate_rust` | 0.438099 | >=0.30 | PASS |
| `hardware_KickPlate_chroma_rust` | 0.561029 | >=0.30 | PASS |
| `hardware_KickPlate_pit_normal_rms` | 0.293316 | >=0.01 | PASS |
| `hinge_screen_px_per_mm` | 6.400000 | >=5 at 0.3 m, ID-pass horizontal silhouette pixels / physical width in mm | PASS |
| `handle_screen_px_per_mm` | 6.400000 | >=5 at 0.3 m, ID-pass horizontal silhouette pixels / physical width in mm | PASS |
| `supplemental_runoff_max_opacity` | 0.300000 | <=0.30 | PASS |

### Rebuild, tests and images

Run these commands from the worktree with the installed Hunyuan Python and Godot. Run generation jobs one at a time under `nohup`; all scratch stays in `tmp/mat/locker/pass5/`.

```sh
PYTHON=/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python
$PYTHON tools/quarters_aging/generate_locker_faces.py
$PYTHON tools/quarters_aging/select_locker_faces.py
$PYTHON tools/quarters_aging/finish_locker_faces.py
/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python tools/blender/quarters/storage_locker_module/hinge_finish.py
godot --headless --editor --path . --import
godot --windowed --path . -s tools/quarters_aging/locker_preview.gd -- --out res://tmp/mat/locker/pass5
$PYTHON tools/quarters_aging/locker_face_gates.py
$PYTHON -m unittest discover -s tools/quarters_aging -p 'test_*.py'
godot --headless --path . -s tests/run_tests.gd
```

The saved raw candidates allow selection and packing without running an image model. `bake_finishes.py` retains the unchanged clean bake and packs the selected aged face images. The source normal atlas and runtime atlas reproduce byte for byte. Hinge export is also byte-identical on repeat.

Python passes **51 tests, 0 failures**. Godot passes **798 tests, 0 failures**, including ten locker tests. Godot still prints resource/allocator teardown warnings after the passing suite. Regression controls include direct RGB packing, chroma-derived alpha, atlas separation/density, constant-image rejection, threshold failures, exported hinge normals, unchanged existing corrosion under optional stains, physical hardware pitch and isolated material caches. The procedural-colour regression failed before implementation; the hardware-pitch regression failed on the stretched mapping before its correction. No OCR code review was run, per Andrew's instruction.

The requested images are `tmp/mat/locker/pass5/before-after.png`, `neutral-pair.png`, `front-pair.png`, `details.png`, `streaks-closeup.png`, `top-pair.png`, `swatches.png`, `closeup-hinge.png`, `faces.png` and `pattern-compare.png`. `faces.png` pairs each chosen image with its source crop. `pattern-compare.png` pairs the aged door with the concept-now locker crop at 400 px/m by height, registering the concept locker to the fitted 2.4 m carcass and preserving the crop's aspect ratio. The concept has no independent metric annotation, so that registration is an assumption. The hinge/handle capture is 4096-square, with an actual 0.3 m camera-to-front-plane distance and silhouette-measured screen density. Individual views, IDs and `preview.json` remain beside them.

The delivered sheet received **8/10 as-built and 6/10 aged** from image-comparer. It found dense connected door flaking, a cloudy-looking top coating at sheet scale and regular-looking hardware bands. These remain visual limitations; passing the numerical checks does not establish visual sign-off. Matched controls show hinge bands remain with height disabled and in a flat-grey geometry view; a handle band remains with height disabled while the flat-grey handle is smooth. The exported normal measurements establish the numerical faceting limit, without treating every visible band as a normal discontinuity.

Generated-face inspection found no apparent hardware, perspective objects or repeated stamped shapes in the assessable crops. The narrow stile images were too small for reliable fine-feature judgments; dark areas in the kick and hardware images could not be confidently distinguished from texture. Reports are `tmp/mat/locker/pass5/image-faces-final.log`, `image-delivery.log` and `image-hardware-controls.log`.

## Sofa

The fitted source is `tools/blender/quarters/sofa/sofa-working.blend`, and the game asset is `assets/props/quarters/sofa.glb`. The cushions and throw are baked Blender cloth meshes with no live modifiers. Authoring uses Blender Z up and front -Y. Export uses `export_yup=True`, giving the game +Y up and front +Z.

### Pass 7: partitioned aging controls

Pass 7 uses invisible seam and arm partitions, fitted back-contact helpers for seat solves, then each predecessor's final reduced surface. None of the helpers exports. The centre-settled/right-fitted control reports zero initial SAT crossings. The final six-cover solve starts from the fitted source; controls and checkpoints stay under `tmp/age/pass7/`.

The throw's floor-contact controls isolate the response before tuning it. Both a plane and a solid floor settle the same 200 mm swatch: final clearances are 2.320 and 2.336 mm, with maximum speeds 5.960 and 6.490 mm/s. Disabling throw self-collision removes its ejection, but permits crossings. Resolving narrow elements against Blender's actual 1 mm minimum self-distance does not fully cure the falling throw: its reduced mesh still crosses itself, and halving the time step leaves 153 self-crossings. These are failed controls, not accepted substitutes. The production contact pool now includes only the final mechanical surfaces, excluding duplicate dense covers and alpha cards.

The old floor patches came from placing most foam on the floor. Deposition now places six floor crumbs per leaking seat, up to twenty inside or under its openings and twelve along its front lip. The powder cards follow the deck instead of forming three floor discs. The template library's `fragment-05` contains a self-crossing triangle pair, so it is rejected before instancing; eight qualifying templates remain.

Seat tears now bound the actual snapped cut length, rather than only the authored walk, and conserve a long tapered fallen island as the third opening. An under-resolved tip detached a three-vertex sliver and shortened the centre island to 111.9 mm. Resolving that tip and allowing for mesh snapping makes all three seats pass the 120–250 mm opening regression. Alpha-aware contour acceptance remains separate. The G7 failure included the residue's planar underside and side caps. The balanced low mesh now samples the stable roof and an irregular underside separately, retaining relief on the lower rim.

A same-mesh shrink control found that a 3% minimum shrink also contracts vertices outside the lip group. At frame 20 it produced 30.726% sharp dihedrals; changing only that minimum to zero reduced the share to 2.044%. Production keeps zero minimum shrink and 5% maximum shrink in the authored lip group. This preserves local lip curl without contracting the whole panel.

The Blender regression suite passes 25 tests. The final six-cover, throw, render and export acceptance milestones remain pending at this checkpoint. No pass-7 candidate has replaced the shipped sofa or its textures.

### Dense aging pilot, not shipped

Pass 4 has reusable dense-mesh, zero-area split, residue SDF, bake-down, fringe, opacity and powder stages under `tools/blender/quarters_aging/`. The centre seat has an experimental baked source at `tmp/age/pass4/seat-proxy/sofa-seat-pilot.blend` and a GLB beside it. The rest of that comparison uses the recorded `sofa-k` geometry. No pass-4 trial is selected, and the shipped asset is unchanged.

The old crumb clustering and spacing-CV gates rewarded compact piles. They are retired in favour of G10's Clark-Evans R and DBSCAN limits and G11's decaying powder spill. Perimeter-only tear scoring and 30 mm straight runs admitted slots; G3 to G6 instead require short alpha-aware contour runs, varying width, lifted lips and contour dimension. The old 35% to 45% seat-height band is replaced by 10% to 25%, with vertical-wall and rounded-box checks. The >=65% retained back-height target is replaced by 40% to 65%, bottom-heavy residue and front folds. `quarters_aging/README.md` records each change and the full threshold list. G2 to G6 and several dense-source/story measurements remain unfinished and fail as unmeasured.

| Centre-seat pilot check | Value | Requirement / state |
| --- | --- | --- |
| Simulation and game cover triangles | 22,976 to 2,400 | 2,400 game triangles |
| Residue game triangles | 700 | 700 |
| Open-boundary error upper bound | 0.125 mm | <=1.5 mm; centre seat only |
| Full comparison triangles | 29,096 | <=29,325; passes |
| Centre height above deck, relative to unaged | 32.69% | 10% to 25%; fails |
| Remaining vertical-wall area | 28.95% | <=25%; fails |
| Cloth dihedral >30 degrees | 60.98% | <=8%; fails |
| All-part SAT intersections | 6,409 | 0; fails |
| Fixed geometry bytes and original pivots | Unchanged | Passes |
| Re-export from saved blend | Byte-identical | Passes |

The swatches were simulated at 6 mm and 3 mm for both upholstery and wool. Per-vertex mass scaling did not preserve drape in three of the four uncut fixtures, so the candidate settings are not accepted. The centre-seat run averaged 0.423 seconds per frame. The standalone crumb library exports nine qualifying cut-residue templates at 24 triangles each, but deposition onto final sofa surfaces remains undone.

The no-exclusion collision requirement conflicts with unchanged rigid geometry. The same SAT check on the unaged source finds 522 Frame self-crossings and 272 Frame/Rivets crossings. Those 794 contacts remain in every byte-identical rigid assembly. They are included in the failed total, with no exclusions and no rigid mesh edits.

The provisional centre-seat material includes 4096-square normal, AO and opacity maps and alpha-scissor fringe. Its residue has 2048-square normal and AO maps. The captures are `tmp/age/pass4/sofa-before-after.png`, `sofa-turntable.png` and `sofa-closeup.png`; the closeup remains 0.6 m from the split seat. These captures have no visual sign-off. Calibration, both other seats, all three backs, the throw, deposition, shared-atlas packing, remaining measurements and final publication are still pending. Raw trial and gate values are committed in `sofa/cloth-trials.json`.

### Historical aged state and measurements

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

### Dense-cloth candidate: rejected

The `tunic6-main` candidate passes 13 of 19 gates and has not replaced the shipped aged tunic. Its source stages and scratch GLB are under `tmp/age/tunic6/main/`. The full measurements, commands and remaining failures are in `tools/blender/quarters/dress_uniform/README.md`; `cloth-trials.json` records the trial separately under `dense_aging`.

The new trial completed 600 frames on 30,000 working cloth triangles with the chest form. Shoulder release is 60.56%; armhole release is 58.93%, leaving a 41.07% back arc. The structural starting sleeve and bending rest both retain 40% depth. The collar follows its sewn columns with 2 mm of support-normal layering clearance. The 200 mm wool calibration retains the `body-p` springs (500/500/350) and bending 0.3, with profile errors of 4.11 and 5.59 mm against a 10 mm limit.

Protected reduction preserves the support crest and sampled silhouette. It produces 10,799 body sheet triangles and 249, 249 and 59 triangles for the three fallen pieces. Boundary error is at most 0.639 mm against 1.5 mm allowed. Normal/AO bakes, stitch opacity, fringe, a 22.45 mm mass-balanced mound, a dust skirt and 65 fibre cards are present. The scratch export has 18,219 triangles against 20,652 allowed and re-exports byte-identically. Original part names, transforms and pivots are retained.

The remaining failures prevent delivery:

| Gate | Measured | Requirement |
| --- | --- | --- |
| G1 visible sharp adjacency | 27.4034% | At most 6% |
| G3 longest straight opening contour | 270.601 px | At most 12 px |
| G6 contour dimension | 1.110458 | 1.15 to 1.40 |
| G20 near-hanger sharp adjacency | 27.2378% | At most 10% |
| G21 hanger pixels outside split hull | 2 | Zero |
| G30 changed-part contacts | 1,878 | Zero |

The unchanged hanger matches its exact geometry and 28-contact baseline. Changed contacts include 1,805 body self contacts, 30 fallen-piece self contacts, 40 collar contacts and three strip/skirt contacts. The dense simulation still moves 15.05 mm over its final five frames. Of 4,326 dense self contacts, 4,171 touch a face excluded from Blender contact because its rest tessellation cannot resolve the minimum contact radius. That mesh needs repair before another settling attempt. Two fallen pieces also miss the local 70% fringe-coverage control, and some card roots exceed the prescribed normal offset.

A plane control showed that centered rim-only Solidify shifts the already baked sheet by 1.5 mm. The local rim uses offset -1 instead of the plan's zero offset, preserving the sheet and extending the nominal 3 mm edge inward. Support-limited thickness passes a plane-floor control but does not eliminate the folded candidate's contacts. Final SAT checks still apply to all changed and new parts without exemptions.

All 13 local test scripts pass. The lit navy-wool renders are `tmp/age/tunic6/tunic-before-after.png`, `tunic-turntable.png` and `tunic-closeup.png`; the shoulder/armhole close camera is 0.5 m away. Face-ID visibility uses close and four turntable views with output dithering disabled. The image-comparer endpoint is unavailable, and the installed local model service returns HTTP 500, so no independent visual approval exists.

### Previously delivered aged state

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
