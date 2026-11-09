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

### Material pilot: pass 10 accepted with known geometry failures

Geometry iteration stops at pass 10 by Andrew's decision. The anchored comparison against aged-target version 1 rated pass 10 at 60% shape/damage match, versus 38–55% for pass 11. Version 2 at `sheets/sofa/aged-target.png` governs colours and materials only. Much of the remaining difference concerns dusty faded fabric, grime and brown debris contrast, so this pilot proceeds to materials without changing geometry thresholds.

A Hunyuan mesh generated from the aged target was tried as a shape guide under `tmp/hy/aged/`. It did not improve on pass 10 and is not used for the pilot.

The accepted source is `tmp/age/pass10/sofa-preview.blend` and its candidate GLB, recorded by `e691a80`. `sofa_pass10_remeasure.py` applies pass 11's combined R+G antialiased coverage and open-lip metrics to the pass-10 camera diagnostics, plus a matching arm-crease close camera. Physical pass-10 panel boundaries select tear contours; seam gape/fringe requirements remain in force. Full per-outline measurements are saved in `tools/blender/quarters/sofa/pass10-material-pilot-gates.json`.

Known pilot limitations remain: G1 right-back sharp adjacency is **9.426987%**, above **8%**; G3 straight runs reach **47.942674 px**, above **12 px**; G4 includes width CV **0.016485**, below **0.35**; G6 resolved contour dimensions span **1.030141–1.202918**, outside **1.15–1.40**. The centre/left backs and throw have no qualifying 64 px contour for G6 and fail rather than being omitted. G1, G3, G4 and G6 fail; the other 18 of 22 gates retain their measured passing results. Publication is allowed only by the explicit pilot geometry exception, not by a claim that these gates pass.

#### Material sources and build

The pilot uses generated diffuse images. `art-source/quarters/sofa/` saves the concept crops, prompts, FLUX.2-klein-4B outputs, selected-image map and colour statistics. The six initial edits use seeds 95600–95605, 4-bit weights, four steps and 768-square output. Seed 95606 edits the aged upholstery crop into a separate granular warm-grey dust scan, with its own prompt, crop and generation metadata. Refinements 95620–95622 flatten wool/foam and replace the weave; 95630–95631 derive flat aged wool and finer yarn from accepted clean fabric. All generation runs sequentially with cached weights and offline mode. Rejected images remain as provenance, not material inputs.

The earlier oatmeal-upholstery brief was incorrect: the approved hero has charcoal-grey upholstery on all six cushions, with oatmeal confined to the throw. The current cloth palette follows that hero and aged-target version 2 through the Godot display-to-albedo fit recorded below. The generated images still supply weave, pore and broad cloth variation. A fitted log-linear illumination plane is removed before linear-RGB colour calibration. The final per-role diffuse images and sRGB/Lab statistics are saved beside their generated inputs. The version-1 crops and rejected generations remain as provenance; their colours no longer determine the cloth pigments.

Mean sRGB values below are weighted by occupied, alpha-surviving atlas texels, before runtime lighting and fine grain. Full generated/crop mean and standard deviation in sRGB and D65 Lab, calibration gains, and each part's final colour are in `as_built-statistics.json` and `aged-statistics.json`.

| Role | As-built mean RGB | Aged mean RGB |
| --- | --- | --- |
| Upholstery | 0.3444, 0.3493, 0.3611 | 0.4078, 0.4102, 0.4102 |
| Throw | 0.5594, 0.4926, 0.4219 | 0.5901, 0.5559, 0.5210 |
| Foam/crust/powder | Not exposed | 0.4973, 0.4177, 0.2860 |
| Painted frame/feet | 0.4080, 0.4235, 0.4319 | 0.4225, 0.4360, 0.4413 |
| Bare rivets | 0.7212, 0.7503, 0.7682 | 0.3243, 0.2415, 0.1801 |

The unchanged locker no-green predicate is reused: hue 70–170 degrees with saturation above 0.25, allowing less than 0.5% newly green coverage. Clean atlas coverage is **0%** and aged coverage is **0.0001305%**, with a largest connected region of **0.0000145%**. These values pass without altering the threshold. The mask mean AO/cavity/up values are **0.4742/0.9672/0.2397** clean and **0.4812/0.9615/0.3744** aged; all three channels span 0–1.

Frame/feet paint follows the sofa's approved hero, independently of the locker's grey-green paint. Both states start with the same calibrated grey pigment; the aged state adds local grime and settled dust. The generated metal scan supplies normalized fine grain, with broad oxide staining removed. Bare rivets retain the locker's clean steel palette and selected aged hardware image, whose aged contrast is reduced to 10%. Clean paint has roughness 0.45 and metallic 0.02; bare steel has roughness 0.35 and metallic 0.45. Aged metal has roughness 0.96 and is non-metallic. Runtime metal grain still uses the shared hatch scans and sampling include. Colour-derived normal relief is omitted. Baked metal AO affects ambient rather than direct lighting, and the overlapping frame UVs are replaced as described below. No locker shader code changes.

`material_pilot.py` preserves every retained vertex, triangle and local pivot while repacking UVs. The clean atlas is 2048-square; the aged atlas is 4096-square, with 8 px gutters. Cycles bakes 120 mm whole-prop AO, 8 mm local cavity and up-facing exposure. Separate cloth-only bakes use 30 mm for folds and 8 mm for local cavity. Joined inner foam was suppressing broad cloth areas in the original bakes. Cloth material slots are temporarily isolated, then their copies are discarded without changing retained geometry. A regression fixture measures joined AO at 0.000568 and the isolated flat cloth at 1.0 for both radii. The grime mask combines cloth-only cavity and folds with a 10% broad-AO contribution. Fabric ORM uses the cloth-only bake too, so joined filling cannot darken the broad fabric field through runtime AO. Upward exposure deposits the generated warm-grey dust scan at 0.24 m pitch, with coverage varying with the scan's granular deposits. Its calibrated mean sRGB is 0.8413/0.8038/0.7257, standard deviation 0.1136/0.1194/0.1223, and mean D65 Lab 82.513/0.016/11.144.

Each cloth/foam part uses a complete generated colour image. Cloth diffuse maps are low-pass filtered at 6 px to avoid stretching the source yarn across a cushion. Fine yarn is extracted from the generated clean upholstery swatch, normalized against a 6 px low-frequency field and made periodic; it repeats at a 0.12 m pitch. Separate weave-generation attempts are retained but not selected because their broad bands remained visible. Foam retains its granular image and uses 25% AO strength to keep tan pores visible in shadow. The original baked normals, cover cutout alpha, fringe and powder masks survive the repack. Aged fringe receives 512 by 1024 px per chart instead of 256 by 512 px to resolve its alpha edge without editing geometry. Packed mask alpha identifies fabric, throw, foam, paint and bare steel. Both states have direct albedo/normal/ORM exports and a separate no-dust runtime control.

The editable material sources are `sofa-material-clean.blend` and `sofa-material-aged.blend` under `tools/blender/quarters/sofa/`. The current exporter is `material_pilot.py -- --stage export --state as_built|aged --output <path.glb>`, run with Blender's `--background --threads 6 --python-exit-code 1 --python` flags. Both saved-source re-exports are byte-identical. External trimesh checks confirm unchanged named geometry and pivots against the clean baseline and pass-10 candidate, with maximum position difference below 0.1 micrometres. No shared aging signatures are changed.

Rebuild in order: run `generate_materials.py`, `refine_materials.py` and `refine_flat_fabric.py` with the installed Hunyuan Python; run Blender `material_pilot.py -- --stage prepare --state <state>`; run Python `finish_materials.py --state <state>`; run Blender `material_pilot.py -- --stage assemble --state <state>`; then Python `texture_imports.py` and Godot import. Preparation reads the original clean source or the retained pass-10 checkpoint. Material generation is separate from baking and need not be repeated when only masks or the shader change.

#### Godot validation and captures

`QuartersProps.material(&"sofa", state)` caches one shared solid-surface material per state. Powder cards use a separate cached transparent material with the same atlas set, preserving filtered alpha coverage at distance. `apply` overrides the imported surfaces without moving nodes or invoking the rigid locker's UV preparation. The four sofa Godot tests check both states, shared resource identity, powder alpha mode, texture completeness/import settings, retained transforms and names, and unchanged locker shader/uniform/face mappings. The headless suite and sofa/locker regression results are recorded below. The original locker shader remains byte-for-byte untouched. The suite emits ObjectDB/resource/PagedAllocator shutdown warnings despite its passing tally; this is not a zero-warning run.

Godot 4.7.2 windowed Forward+ / Metal captures use `tools/quarters_pilot_preview.gd` through `tools/blender/quarters/sofa/material_preview.gd`. The detail target is (-0.18, 0.46, 0.29) m; the throw target is (1.05, 0.50, 0.18) m. The remembered state uses the preview's warm light; present uses `Lighting.REGULAR_WHITE`, RGB **1.0, 0.97, 0.90**. The neutral pair uses identical illumination for both states. Both detail cameras are verified at **0.600000 m**, perspective FOV **43.6028 degrees**. Each state retains its own source geometry; the clean and collapsed aged meshes intentionally differ.

In the initial material pilot, rendered no-green coverage was **0%** in all five actual-shader albedo views. Matched lit top controls showed dust changing **72.54%** of visible upward-face pixels by at least **8/255** under neutral light and **71.58%** under present light, above the authored **5%** numerical gate. Mean maximum-channel absolute sRGB changes are **0.11597** and **0.09630** respectively. This measures the effect against the same shader with dust disabled; visual acceptance is assessed separately. All **89 locker control PNGs are byte-identical** to the pre-change captures, covering both finish states and diagnostics. Final mesh comparison reports zero position difference and unchanged per-state names, pivots and triangle counts; both material-source GLB re-exports remain byte-identical.

Initial material-pilot images are in `tmp/mat/sofa/`: `before-after.png`, `neutral-pair.png`, `closeup.png` and `target-compare.png`. `beforeafter.png` and `neutral.png` are aliases. The directory also contains source sheets, per-angle lighting/diagnostic controls, `preview.json`, and `material-gates.json`. The target comparison uses the aged Godot hero angle beside the fixed aged target; lighting and the accepted geometry limitations prevent treating it as a pixel-matching test.

The initial image-comparer inspected all seven material/control sheets before the clean-metal correction. It confirmed warm oatmeal fabric, fine crosshatch in the 0.6 m close-up, different clean/aged wool, distinct brown filling and visible settled dust in the matched controls. It did not accept the target fit: grime still read broadly across cushion faces, filling looked more uniformly granular than porous, and ragged edges and broad-scale fabric readability remained limitations. The aged frame read warm tan, and bare rivet identity was not clearly verified. The chipped-looking clean-frame pattern was subsequently removed. Those observations are recorded in `tmp/mat/sofa/observed-review.json`. The finish work below replaces those material settings; the accepted geometry limits remain.

#### Finish calibration and visibility (2026-11-09)

The sofa frame now follows its own approved design image, not the locker's paint. `calibrate_finish.py` samples three steel regions in `hero.png` and warm-pixel subsets of three irregular foam tears and two floor-debris regions in `aged-target.png`. Neutral steel selection excludes saturated pixels; foam/crumb selection excludes neutral floor and cloth. Exact rectangles, surviving pixel counts, medians, attempted albedos and displayed results are in `art-source/quarters/sofa/finish-calibration.json`.

The flat swatches use the Godot preview's unchanged Forward+ / Metal lighting and linear tone mapper. Frame fitting uses the front-rail plane at (0, 0.24, 0.475) m, neutral light, roughness 0.45 and metallic 0.02. Foam uses an upward-facing plane at (-0.18, 0.43, 0.29) m; crumbs use (0, 0.012, 0.58) m, both under present light with roughness 0.98 and metallic 0. The fitter starts from the linearised target display colour, renders, measures the central 64-square swatch and multiplies the linear albedo by the linearised target/display ratio. Each role converges in two renders, within one sRGB byte per channel. An earlier six-render common-roughness trial remains in `tmp/mat/sofa2/calibration/`; the six final reflectance-matched swatches are in `calibration-physical/`.

| Pigment | Target display RGB | Final display RGB | Final linear-RGB albedo |
| --- | --- | --- | --- |
| Frame paint | 117, 121, 124 | 117, 122, 124 | 0.139423, 0.150891, 0.157349 |
| Exposed foam | 121, 92, 61 | 121, 93, 62 | 0.148489, 0.084448, 0.038797 |
| Floor crumbs/powder | 125, 91, 65 | 125, 92, 66 | 0.155481, 0.080693, 0.043119 |

Both frame states derive from this grey base. Foam and floor residue retain the generated pore/grain image but use their separate fitted pigments. A quadratic colour blend over five source texels tints surviving torn cloth toward the foam at the rim, with at most 45% blending and no change to alpha, tear contours or geometry. The no-dust control receives the same rim treatment, so the dust difference does not include an edge-colour change. These swatch fits establish regional pigment colours under the preview, not a whole-image match to concept lighting.

The lower-rail streaking came from the retained frame UVs. At the 1024-square diagnostic resolution, **99.398%** of occupied aged-frame texels were shared by multiple triangles, with up to **21 layers**. Median physical texel anisotropy was **4.506:1**, and its 90th percentile was **27.258:1**. Smart-projected, separate metal charts and uniform aspect-preserving atlas scaling reduce those values to **0.00348%** shared boundary pixels, **1.183:1** median and **1.604:1** at the 90th percentile. The as-built frame receives the same correction. Mask bakes are repeated on these charts; reducing texture contrast alone had left the overlapping bake unchanged. `rail-closeup.png` compares the same lit rail camera before and after.

Floor debris had two presentation/material causes. The earlier hero preview had no floor plane, and its retained 18 solid fragments are only about 1–8 mm across. More importantly, the fine powder cards used the same 0.5 alpha cutoff as torn cloth. Their sparse binary alpha averaged below that cutoff in the minified atlas, erasing the broader deposits. Powder now has a separate cached transparent Godot material and a glTF `BLEND` material, while cloth and solid fragments retain `MASK`. The floor plane belongs only to the sofa preview; neither game geometry nor the locker preview changes. Fragment templates, centroids, geometry and powder-card positions remain unchanged, preserving G9, G10 and G11.

The debris control uses the same lit hero camera with floor debris enabled and disabled. Its diagnostic retains occluding sofa geometry and uses the same anisotropic/mipmap alpha filtering as the runtime material. Pixels with at least 5% resolved coverage participate, because requiring fully opaque pixels would exclude the corrected transparent powder. The gate requires a median difference of at least 8 sRGB levels and that difference over most participating pixels. This coverage rule replaces the initial solid-fragment-only diagnostic; it does not change G9–G11. In the final 1024-square hero capture, **1,209 visible debris pixels** have a median maximum-channel ON/OFF difference of **13 sRGB levels**, mean **16.009 levels**, and **73.366%** differ by at least 8 levels. The previous cutoff left only 32 fully covered fragment pixels and no resolved powder deposits.

Both final GLBs re-export byte-identically from their saved material sources. External trimesh checks report **zero position difference**, unchanged named parts, local pivots and triangle counts against each state's retained geometry. All **89 locker control PNGs remain byte-identical**, and the locker shader, assets and material branch are unchanged. The five final actual-shader albedo views retain **0% newly green coverage**. The neutral/present top dust controls retain the unchanged 8-level/5%-coverage gate.

Final images are under `tmp/mat/sofa2/`: `before-after.png`, `neutral-pair.png`, `closeup.png`, `rail-closeup.png`, `target-compare.png`, `debris-on.png`, `debris-off.png` and their labelled pair `debris-on-off.png`. `design-compare.png` compares the clean frame with the approved hero; `material-before-after.png` holds the stage, camera and lights fixed across material changes. Raw captures, swatches, `finish-gates.json` and verification logs are in the same directory. Close upholstery and throw cameras remain 0.6 m away. The material pass preserves the accepted tear/shape limitations and does not establish the target's debris-pile volume.

Final verification passes **16 sofa Python tests**, **51 unchanged locker Python tests**, **14 focused Godot tests** (four sofa and ten locker), and the full headless suite with **802 passed, 0 failed**. The final suite ran under `nohup`; counts are in `physical-python-tests.log`, `locker-python-tests.log`, `physical-focused-tests.log` and `physical-unit-suite.log`. Resource, ObjectDB and allocator warnings still appear during Godot teardown. Quality checks and G9–G11 thresholds are unchanged. No OCR review was run.

Image-comparer identifies neutral grey rather than teal on the clean frame, reduced longitudinal rail streaking and visible brown floor deposits in the enabled control. Its full-sheet inspection calls the exposed filling pale, but an isolated crop distinguishes light beige woven cloth from tan/yellow-brown granular filling. The role-diagnostic-selected foam pixels in that detail view have median displayed RGB **107, 83, 57**. Both observations are retained in `final-vision.json` and `single-vision.json`; the isolated crop is `foam-isolated.png`. Broad-view material readability and the target's larger debris piles remain visual limitations, rather than numerical passes being treated as target acceptance.

To rebuild this finish without regenerating material scans, run `calibrate_finish.py`; run Blender `material_pilot.py -- --stage prepare --state as_built|aged --scratch tmp/mat/sofa2`; run Python `finish_materials.py --state as_built|aged --scratch tmp/mat/sofa2`; then Blender `material_pilot.py -- --stage assemble --state as_built|aged --scratch tmp/mat/sofa2`. Run `texture_imports.py`, import in Godot, and capture with `material_preview.gd` using the two sofa assets, height 0.86, centre Y 0.43 and output `res://tmp/mat/sofa2`. `compose_finish.py` builds the comparison sheets; `validate_finish.py` checks exports, UV density, visible dust/debris and locker bytes. Long jobs run under `nohup`. Texture import metadata retains existing resource UIDs.

#### Charcoal upholstery correction (2026-11-09)

The earlier brief called the upholstery oatmeal. That was an error: `hero.png` specifies charcoal-grey woven fabric on all six cushions and an oatmeal throw. The first aged target inherited the same error. The current palette uses the hero and `aged-target.png` version 2, whose metadata restricts it to colours and materials. Geometry remains frozen at pass 10; the target's heavy edge rust, larger foam clumps, upright backs and shorter throw are not copied.

`cloth-reference.json` records the reference rectangles, material roles, swatch positions, normals and lighting. The image-comparer identified cloth, foam and debris regions; numerical inspection narrowed the faded-cloth samples to low-variance interiors. Cloth selection requires saturation below 0.35 and display values between 20 and 235, excluding saturated exposed filling. Foam and crumbs retain the warm-pixel predicate. `calibrate_finish.py` renders flat swatches through the same Godot Forward+ / Metal preview, measures the central 64 by 64 pixels, and updates linear albedo using the target/display linear-light ratio. Every new fit converged in two renders, within one sRGB level per channel. Roughness is 0.98 and metallic is zero for these swatches. Frame settings and lighting are unchanged.

| Role | Sampled display RGB | Fitted display RGB | Fitted linear-RGB albedo |
| --- | --- | --- | --- |
| As-built upholstery | 108, 110, 113 | 109, 111, 114 | 0.097460, 0.100351, 0.107293 |
| As-built throw | 153, 135, 116 | 153, 135, 116 | 0.273334, 0.207312, 0.148732 |
| Aged upholstery | 119, 117, 111 | 120, 118, 112 | 0.140461, 0.144148, 0.147389 |
| Aged throw | 143, 132, 117 | 143, 131, 116 | 0.343684, 0.299294, 0.259085 |
| Upward cloth dust | 144, 139, 129 | 144, 140, 130 | 0.221265, 0.218561, 0.212330 |
| Exposed foam | 142, 117, 78 | 142, 118, 78 | 0.213998, 0.146596, 0.067100 |
| Floor crumbs/powder | 169, 143, 96 | 169, 143, 96 | 0.309335, 0.223772, 0.105137 |

The new foam and crumb samples differ from the previous fitted display colours by at most 24 and 51 sRGB levels respectively. Both exceed the requested six-level tolerance, so their pigments are adjusted; their pores, fragment shapes and alpha are retained. `version2_check` records the old displayed values and the decision. Subsequent calibration runs preserve that comparison when the target samples have not changed.

The cloth base images are recoloured in linear light after illumination removal and low-pass filtering. Their variation survives, and the separate fine weave texture is byte-identical to the previous finish. Folds still darken through the retained cloth-only masks. Upward cloth dust has a separate fitted grey pigment, while deposit density still comes from the original granular scan. Separating density from pigment prevents the darker dust colour from erasing deposits. The initial cloth recolour still produced an overly broad film: the old density rule imposed at least 30% coverage and allowed 85% dust blending on an upward face. Cloth now uses a smooth coverage transition between scan values 0.65 and 0.90, without that coverage floor, and a maximum blend of 65%. A 6 px periodic low-pass softens the density scan; pigment variation is reduced to 45% before restoring the fitted linear mean. This addresses the image-comparer's broad-film and pale-patch observations without changing any visibility threshold, cloth alpha, normal map or weave texture. Frame and foam keep their original density rule and dust palette. This keeps all 786,432 covered clean-frame texels and 1,572,864 covered aged-frame texels byte-identical, including the existing restrained aging.

Both saved material sources re-export byte-identically. External GLB measurements confirm zero position difference, unchanged triangles and local pivots, ten named clean parts and 21 named aged parts. The pass-10 G9–G11 measurements and their thresholds remain unchanged. These checks preserve the accepted geometry exception; they do not resolve its G1, G3, G4 or G6 failures.

The five actual-shader albedo views have **0% newly green coverage**. Matched lit top controls show dust changing **52.487%** of visible upward-face pixels by at least eight sRGB levels under neutral light and **41.343%** under present light, above the unchanged 5% gate. Debris retains **1,209 visible pixels**, a median ON/OFF difference of **10 levels**, a mean of **11.945 levels**, and **63.027%** of pixels at or above eight levels. This passes the unchanged median-eight-level and majority-coverage requirements. All **89 locker control PNGs are byte-identical**, and the locker assets, shader and shared material code remain unchanged.

Final verification passes **19 sofa Python tests**, **37 unchanged locker Python tests**, **14 focused Godot tests** (four sofa and ten locker), and the full headless suite with **802 passed, 0 failed** after the cloth-dust refinement. The full suite ran under `nohup`; logs are `python-tests.log`, `locker-python-tests.log`, `focused-tests.log` and `unit-suite.log` under `tmp/mat/sofa3/`. Godot retains the existing ObjectDB leak, resources-in-use and allocator teardown diagnostics. The no-green, debris and geometry thresholds are unchanged. No OCR review was run.

The final image-comparer inspection passes the charcoal/oatmeal separation, faded aged cloth, debris toggle and absence of green/teal or sampling artifacts. It calls the colour correction ready to show, with two remaining visual concerns: foam can read gold/yellow in the close-up, and the throw boundary looks sharply cut out. The fitted foam and crumb swatches already match the version-2 regional samples within one level, so their pigments are not desaturated again to chase that contextual appearance. Original alpha, tears and normals stay intact. These observations and the fixed shape limitations remain visible in `final-material-vision.json`; the review does not establish full target parity.

The current outputs and raw controls are under `tmp/mat/sofa3/`. `before-after.png` places the old oatmeal brief on the left and the corrected palette on the right, with clean above aged. `neutral-pair.png` compares clean and aged under identical lighting; `closeup.png` shows upholstery and throw at 0.6 m. `target-compare.png` uses aged-target version 2, and `design-compare.png` uses the approved hero. Rebuild with `calibrate_finish.py --out tmp/mat/sofa3/calibration`; use `material_pilot.py -- --stage prepare --state as_built|aged --scratch tmp/mat/sofa3` only when masks need rebuilding, then `finish_materials.py --state as_built|aged --scratch tmp/mat/sofa3` and Blender `material_pilot.py -- --stage assemble --state as_built|aged --scratch tmp/mat/sofa3`. This pass reuses the retained prepared scenes and mask arrays from `sofa2`, without rebaking or changing geometry. After `texture_imports.py` and Godot import, capture with the existing sofa `material_preview.gd` arguments and `--out res://tmp/mat/sofa3`. `compose_finish.py --out tmp/mat/sofa3` builds the sheets; `validate_finish.py --out tmp/mat/sofa3` checks the retained geometry, export bytes, UVs and lit controls.

### Pass 11: rejected visible-boundary candidate

This shape trial used version 1 of `sheets/sofa/aged-target.png`, depicting
1000 years of aging. The shipped sofa remained unchanged while this candidate was measured.
The target calls for broad gashes and exposed tan foam, individual seat sag
and much more debris. Small repeated holes do not meet that target.

The pass-10 G3 wrapper accepted only nearly pure red or green diagnostic
pixels. It discarded 5,499 to 18,166 cloth-coverage pixels per cushion,
including antialiased cloth/fringe mixtures. On the centre back this created
11 enclosed diagnostic holes where coverage decoding finds two. Neither
result makes the old tears acceptable: their remaining longest runs still
exceed 12 px. The new sofa-local measurements decode combined coverage and
trace visible alpha outlines near physical lips, including open gashes,
without adding a closing segment. G3's 12 px maximum, G4's 0.35 minimum and
G6's 1.15 to 1.40 range are unchanged. Four controls cover mixed coverage,
constant slots, exterior-connected tears and other-object silhouettes.

### Pass 10: rejected, 18 of 22 gates pass

Pass 10 continues the pass-9 solve (`bdd5171`). G5 lip lift, G7 residue
planarity and G30 contact now pass. Every collapse gate G12–G19 remains
passing. G1 still fails on the right back (9.427%, against ≤8%); G3, G4
and G6 still fail on tear runs, width variation and contour dimension.
The throw has no enclosed diagnostic opening qualifying for those gates.

Dense/reduced comparisons identify reduction-driven cover faceting, plus
sharp folds already present in the left back and throw. Bounded fairing
retains open boundaries and
stitches. A local repair restores the unpinched prepared throw fold around
the retained corner, rather than excluding its collision pairs.

The dark tear interiors combined a dark placeholder colour with a
surrounding-cover AO bake. Provisional foam is now tan-brown with an 8 mm
residue-only cavity bake. Seat residue has additional crust relief;
non-floor crumbs use a 4 mm median and contact-fitted fine powder is added
inside and below openings. Packed alpha is explicitly unpacked, edited,
saved and repacked so exported tears use the edited payload.

The candidate does not replace `sofa_aged.glb`, shipped textures, or the
fitted Blender source. More aggressive back-collapse trials failed the
unchanged area controls and were rejected. Broad seat slabs, pillow-like
backs and uneven apparent sag remain visual concerns. Numerical collapse
passes do not establish that those visual defects are fixed.

All gate values and root-cause controls are in the Sofa pass-10 section of
[the aging README](../../../tools/blender/quarters_aging/README.md).
Matching pass-9 camera captures are `tmp/age/pass10/sofa-before-after.png`,
`tmp/age/pass10/sofa-turntable.png` and `tmp/age/pass10/sofa-closeup.png`.
The closeup is at 0.6 m. The preview GLB and per-opening measurements stay
in that scratch directory. Software verification passes 34 Blender tests
and 18 Python tests; it does not substitute for art acceptance.
Image-comparer rates pass 9 at 4/10 and pass 10 at 5/10 within its matching
comparison. It finds clearer tan residue and more throw wear, but still
rejects the coherent cushion forms, abrupt tears and sparse angular debris.
Fine powder is not visually established.

### Pass 8: rejected candidate, shipped sofa unchanged

Pass 8 replaces seat partitions and back subdivision carriers with clean
level-1 cloth. Seats solve jointly with 55–75% welt release. Backs solve
jointly with rear ties at 0.60–0.62 m and residue inside the lower return.
A controlled comparison found that the animated back envelope stretched
the pinned covers, so the final back solve uses static residue instead.
The actual fitted throw is a back collider; the throw then solves with one
67.500 mm rear-corner bridge and 351 cap pins. Every working triangle has
at least 5 mm altitude, and no self-collision exclusions are used.

The early controls completed within 21 minutes of the first inspection:
centre-back frame-20 sharpness 3.440%, Frame-only 0.932%, free-fall speed
0.300000 m/s, cantilever co-scaling error 0 mm, area within 0.174% of fitted,
maximum sampled substep motion 0.909 mm, and zero initial SAT crossings.
The measured drag relation is `2.4*m*g/air` for the RNA setting at 24 fps
and half-speed integration. Production targets 0.3 m/s, with 3 mm contact
distances and quality 20 for covers, 30 for the throw.

The final preview passes 11 of 22 gates. G30 passes with zero changed
contacts and an exact rigid baseline. Fixed geometry bytes, pivots,
byte-identical re-export and all seven fringe-node checks pass. All solves
reach 900 frames without satisfying the three-check stillness rule. The
left seat retains 32.708% centre height and 31.697% of fitted boxing pixels
in the hero view. Back height retention is 90.464/86.450/87.603%, above
40–65%. The throw remains one piece at the arm, but stops 118.619 mm above
the floor with only one qualifying fold. Contours, left-back/throw
faceting, visible centre residue planarity and seat boundary error also
fail. No shipped GLB, texture or baked source was replaced.

The [aging README](../../../tools/blender/quarters_aging/README.md) records
all gate values against their thresholds, the G3/G7/G12/G19/G30 scope
decisions, failed controls and measured stage runtimes. The final exported
candidate and reports remain in `tmp/age/pass8/`. Captures use the pass-7
cameras: `sofa-before-after.png`, `sofa-turntable.png` and
`sofa-closeup.png` in that directory. The closeup is at 0.6 m. Software
checks pass 35 Blender tests and five Python camera-gate tests. The captures
have no visual sign-off. Review skipped per Andrew 2026-10-09.

### Pass 7: partitioned aging controls

Pass 7 uses invisible seam and arm partitions, fitted back-contact helpers for seat solves, then each predecessor's final reduced surface. None of the helpers exports. The centre-settled/right-fitted control reports zero initial SAT crossings. The final six-cover solve starts from the fitted source; controls and checkpoints stay under `tmp/age/pass7/`.

The fitted centre back is clear, but its former empty-rest target crosses triangles 4480 and 13329. The depth mapping jumped at 560 mm. It now transitions continuously from that lower edge to the top. The regression first reproduced the crossing, then verified both fitted and rest poses on all three backs. The Blender suite passes 26 tests with that correction; back height and fold acceptance still require the final simulation.

The throw's floor-contact controls isolate the response before tuning it. Both a plane and a solid floor settle the same 200 mm swatch: final clearances are 2.320 and 2.336 mm, with maximum speeds 5.960 and 6.490 mm/s. Disabling throw self-collision removes its ejection, but permits crossings. Resolving narrow elements against Blender's actual 1 mm minimum self-distance does not fully cure the falling throw: its reduced mesh still crosses itself, and halving the time step leaves 153 self-crossings. These are failed controls, not accepted substitutes. The production contact pool now includes only the final mechanical surfaces, excluding duplicate dense covers and alpha cards. Replacing only the floor plane with a closed 100 mm slab eliminates the baseline's upward ejection: contact begins at frame 224 in both runs, but the plane later lifts the lowest vertex to 396.954 mm, while the slab keeps it below 3.160 mm. The final throw solve uses that unexported slab with its top still at zero. This control establishes the floor representation's contribution; it does not establish a continuous, contact-free arm-to-floor drape.

The old floor patches came from placing most foam on the floor. Deposition now places six floor crumbs per leaking seat, up to twenty inside or under its openings and twelve along its front lip. The powder cards follow the deck instead of forming three floor discs. The template library's `fragment-05` contains a self-crossing triangle pair, so it is rejected before instancing; eight qualifying templates remain.

Seat tears now bound the actual snapped cut length, rather than only the authored walk, and conserve a long tapered fallen island as the third opening. An under-resolved tip detached a three-vertex sliver and shortened the centre island to 111.9 mm. Resolving that tip and allowing for mesh snapping makes all three seats pass the 120–250 mm opening regression. Alpha-aware contour acceptance remains separate. The G7 failure included the residue's planar underside and side caps. The balanced low mesh now samples the stable roof and an irregular underside separately, retaining relief on the lower rim.

A same-mesh shrink control found that a 3% minimum shrink also contracts vertices outside the lip group. At frame 20 it produced 30.726% sharp dihedrals; changing only that minimum to zero reduced the share to 2.044%. Production keeps zero minimum shrink and 5% maximum shrink in the authored lip group. This preserves local lip curl without contracting the whole panel.

All six final covers completed: seats centre/left/right took 456.500/196.325/285.175 seconds; backs took 724.758/543.668/366.601 seconds. The backs no longer retain their fitted boxes, but they over-collapse: height retention is 28.053/39.047/33.517%, below G15's 40–65%. G17 finds 2/2/1 front folds, against at least two each. Seat centre retention is 58.463/63.084/58.513%, above G14's 10–25%. The stable residue mesh reduces G7 to 4.486/6.846/5.678% on seats and 1.620/2.919/2.750% on backs; the remaining above-limit patches are on the roof, not the corrected underside or rim. These failed source measurements block publication. The Blender regression suite passes 27 tests. No pass-7 candidate has replaced the shipped sofa or its textures.

#### Pass-7 final acceptance: rejected, shipped asset unchanged

All G1–G19 and G30–G32 are measured on the final preview, dense sources and alpha-aware captures. Eight of the 22 gates pass. `tmp/age/pass7/final/gates.json` contains the per-opening values; `collisions.json` contains the SAT contacts. Geometry bytes for Frame, Feet and Rivets, object pivots, all-six-simulated status and byte-identical re-export all pass. The candidate stays at `tmp/age/pass7/final/sofa-preview.glb`. Neither `assets/props/quarters/sofa_aged.glb` nor its textures was replaced.

The final throw is one connected sheet, but no part remains at the arm. Its fallen centroid is 430.163 mm from the arm footprint, and it has 394 self-crossings. Four folds meet the 10 mm requirement. Contact starts at frame 226; afterwards its lowest vertex stays below 9.310 mm, rather than the old run's 396.954 mm upward ejection. Correcting the floor representation did not solve arm retention, faceting or self-contact. The high-friction arm control retained the throw above 351.774 mm without reaching the floor, so it is also rejected. The remaining drape cannot be accepted by choosing either failed control.

Deposition places 20 crumbs inside or under openings and 12 along the front lip of each seat, with six per seat on the floor: 114 fragments total, of which 18 are on the floor. Three supported powder drifts lie on the deck. The exported crumb node has zero self-crossings, fixing the former 13 instance crossings. G9–G11 pass, but no visual rating has been obtained for these captures.

In the table, seat and back triplets are centre/left/right. Missing visible openings are measured failures, not omitted tests. G6 lists only contours large enough for its 64 px extent requirement; smaller contours remain in the full report.

| Gate | Final value | Threshold | Result |
| --- | --- | --- | --- |
| G1 | Visible sharp adjacencies: seats 10.467/11.585/8.666%; backs 52.174/25.000/56.757%; throw 39.412% | Covers ≤8%; throw ≤9% | Fail |
| G2 | Normal jumps: seats 0.156/0.169/0.181%; backs 23.317/32.740/49.814%; throw 3.543% | ≤2% each | Fail |
| G3 | Longest alpha-aware straight runs: seats 32.249/28.000/52.038 px; backs absent/64.382/absent; throw 21.506 px | ≤12 px, about 4.5 mm | Fail |
| G4 | Minimum opening-width CV: seats 0.5323/0.3457/0.3355; backs absent/0.6158/absent; throw 0.4191 | ≥0.35 each | Fail |
| G5 | Lip length lifted over 3 mm: seats 23.716/20.492/15.836%; backs 30.675/53.539/43.849% | ≥30% each | Fail |
| G6 | Resolved contour dimensions: centre 1.1493–1.2608; left 1.1278; right 1.1597–1.2989; backs absent/1.2631/absent; throw unresolved | 1.15–1.40 each resolved contour, with a measured contour per part | Fail |
| G7 | Planar residue area: seats 4.486/6.846/5.678%; backs 1.620/2.919/2.750% | ≤5% each | Fail |
| G8 | Dense plane-fit RMS: seats 1.712 mm each; backs 2.494/2.478/2.478 mm; all normal maps present | ≥1.5 mm and map | Pass |
| G9 | 8 templates, 24 triangles each, thickness/width 0.2663–0.4592 | ≥8 templates; 14–40 triangles; ratio 0.25–0.70 | Pass |
| G10 | Clark-Evans R 1.118321; largest cluster 0%; 18 floor crumbs | R 0.8–1.4; cluster ≤20% | Pass |
| G11 | Spill radial-density rho -1.000/-0.800/-1.000; powder present for each | ≤-0.6 per source, with powder | Pass |
| G12 | Seat vertical-wall area 50.677/52.284/63.033% of fitted | ≤25% each | Fail |
| G13 | Exported rounded-box RMS 15.863/13.725/11.613 mm | ≥12 mm each seat | Fail |
| G14 | Seat centre-height retention 58.463/63.084/58.513% | 10–25% each | Fail |
| G15 | Back height retention 28.053/39.047/33.517% | 40–65% each | Fail |
| G16 | Back residue volume in lower third 100% each | ≥60% each | Pass |
| G17 | Front folds at ≥8 mm prominence: 2/2/1 | ≥2 each back | Fail |
| G18 | Arm-crest split 79.947% | 60–90% | Pass |
| G19 | Distance 430.163 mm; 4 folds ≥10 mm; 1 component, 0 arm-to-floor components | ≤250 mm; ≥3 folds; 1 continuous arm-to-floor component, ≤1 detached remnant | Fail |
| G30 | 10,917 changed contacts; rigid baseline exact | Zero changed contacts; exact rigid baseline | Fail |
| G31 | 29,253 triangles, 1.496317 times fitted | ≤29,325 and ≤1.5 times fitted | Pass |
| G32 | Dense/game boundary bound 0.125 mm for all covers and throw | ≤1.5 mm | Pass |

G30 comprises 9,198 back self-crossings, six seat self-crossings, 394 throw self-crossings and 1,319 changed-part pair crossings. The rigid counts remain 522 Frame self-crossings and 272 Frame/Rivets crossings, with the other four rigid self/pair counts zero. The partition control proves initialization clearance, not final contact acceptance. The backs' remaining instability is unresolved: a fresh-modifier fitted-rest control still has 39.079% sharp adjacencies at frame 40, so the corrected rest-depth discontinuity is not its sole cause. No solver thresholds or SAT checks were relaxed.

The six cover solves took 2,573.027 seconds in total; the throw's 480-frame solve took 165.258 seconds. Measured finishing stages took 76.285 seconds for cushion detail, 13.925 for throw detail, 26.910 for deposition, 13.002 for atlas/export, 19.473 for rendering, 0.826 for composition, 2.355 for SAT and 8.589 for acceptance. Acceptance exited 1 because the candidate fails. The software verification passes 46 Python tests and 27 Blender tests. Review skipped per Andrew 2026-10-09.

The provisional-material captures are `tmp/age/pass7/sofa-before-after.png`, `tmp/age/pass7/sofa-turntable.png` and `tmp/age/pass7/sofa-closeup.png`. The closeup is at 0.6 m. These are rejected-candidate diagnostics, without visual sign-off.

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

### Tunic15: remove baked torso crests; full-frame shading remains disputed

The torso's baked curvature contribution is removed. The unchanged geometric folds still produce broad shading. The isolated neutral-crop review describes elongated vertical bands without isolated rounded spots; the full shoulder-frame review still calls the result cloudy. These observations do not establish a complete visual fix for the garment. The numerical result below concerns the identified baked contribution, not acceptance of every remaining tonal feature.

**Layer controls.** `tmp/age/tunic15/` contains matched 160 mm-square, 400 by 400 neutral chest/torso captures. Luminance is the sRGB-byte weighted sum 0.2126 R + 0.7152 G + 0.0722 B. Spectra use a fitted-plane subtraction, Hann window and radial power histogram. Frequency is in camera-plane cycles per 100 mm; the 160 mm frame has 0.625-cycle frequency resolution. Listed frequencies are histogram-bin centres, not exact wavelengths. The table reports raw luminance standard deviation and median spectral power frequency. All six controls retain the same geometry, camera and light.

| Control | Blender luminance std | Godot luminance std | Median frequency, both engines |
|---|---:|---:|---:|
| Shipped baseline | 14.262 | 6.385 | 1.56 |
| AO set to one | 14.141 | 6.278 | 1.56 |
| Fade fixed to its atlas mean | 13.068 | 5.990 | 1.56 |
| Dust disabled | 14.121 | 6.362 | 1.56 |
| Curvature crest contribution disabled | 12.361 | 4.746 | 1.56 |
| Broad pigment fixed to 0.5; grain fixed to one | 14.590 | 6.599 | 1.56 |
| Roughness one; specular zero | 14.263 | 6.367 | 1.56 |

There is no spatial roughness/ORM texture on the body: its roughness is the constant 0.97. Controls can change the displayed mean, so a lower raw standard deviation alone is not visual acceptance. The reconstructed Blender baseline differs by only 0.000081 RGB levels on average. Removing crests changes Blender RGB by 7.861 levels on average; AO, dust and base pigment controls change it by 0.197, 0.219 and 0.650 respectively. After removing a fitted plane, the crest-control difference has luminance std 3.826, against 0.356 for AO and 0.677 for pigment. The normal-map control does not remove the dominant broad pattern.

The Blender ON-minus-OFF difference spectra isolate each contribution more directly than the full rendered frame. Their fitted-plane-removed luminance std and median frequency are:

| Removed contribution | Difference std | Difference median cycles/100 mm |
|---|---:|---:|
| AO | 0.356 | 17.81 |
| Fade variation | 1.750 | 1.56 |
| Dust | 0.473 | 2.81 |
| Curvature crest | 3.826 | 1.56 |
| Base pigment variation | 0.677 | 0.94 |
| Roughness/specular response | 0.498 | 14.06 |

**Source defect and density.** The old normal-displacement Laplacian divided by 1.5 mm grows with squared edge length. The same 100 mm-radius cylinder sampled at 2.5, 5, 10 and 20 mm gave crest values 0.0104, 0.0417, 0.1665 and 0.6644. The normalised estimator stays near 0.5 across those spacings. On the torso the old crest/edge-spacing correlation was 0.359. Its median longest triangle edge is 18.1 mm and maximum 103.2 mm, so interpolating that vertex signal paints broad brightness patches.

The colour atlas is 4096 square, with median torso density 2.60 px/mm, range 2.28 to 2.63. The current-cloth 60 mm AO bake is 2048 square and is resampled twofold by nearest neighbour. The crest mask is calculated on the reduced garment and rasterised by barycentric interpolation; it is not transferred from the dense simulation. No mask blur was found in this path. Increasing atlas resolution would not correct the mesh-spacing bias. Density normalisation and a directional-curvature experiment did not visibly resolve the broad pattern, so the latter is retained only in scratch, not in shipping source.

The persistent 1.56-cycle band corresponds approximately to 64 mm. Real wool does not supply a universal permissible fade frequency. A [Smithsonian wool tunic photograph](https://ids.si.edu/ids/manifest/NMAH-AHB2010ps03351), object AF.59195-N(2-B), provides a measured 762 mm padded height. Its clean red-wool crop has an approximate 125 mm width, low-frequency peak 0.94 cycles/100 mm and median power frequency 58.44 cycles/100 mm, including nap and photographic noise. Its review sees directional folds, not round clouds, but cannot separate illumination from dye fading. The scale excludes dark collar/hem and is approximate. This comparison supports examining spatial structure rather than treating the tunic's 1.56-cycle band as proof of an artefact. [CCI textile guidance](https://www.canada.ca/en/conservation-institute/services/preventive-conservation/guidelines-collections/textiles-costumes.html) describes exposure-dependent light damage; this photograph does not establish a quantitative faded-wool standard.

**Source correction.** `aged_linear(..., crest_fade=False)` keeps the main drape's fade on exposure, height, orientation and AO instead of adding a second curvature-painted fold highlight. `bake_colour()` uses this policy for `TunicBody`, including its dust-off control. `rebake_pilot_crest.py` applies the linear-light difference to the existing body pixels, preserving the other baked contributions and alpha. Lighting and AO still darken real recesses. Normal maps, roughness, dust boundaries, debris, facings, fittings and their textures are unchanged. The separate density regression retains the corrected physical estimator for callers that still use a crest term.

The final Blender torso std is 12.354, against 14.262 before; Godot is approximately 4.74, against 6.385. Median frequency remains 1.56 in both engines because broad geometric shading remains. A brightness-comparable constant-albedo Godot control has std 3.861, or 3.248 with tangent normals disabled. The accepted mesh also retains `polish_pass9.py:broad_folds()`, an authored product-of-sinusoids normal displacement of at most 1.8 mm below the attachments; this pass does not alter that geometry. The final colour bake matches the independent no-crest control within 0.23 RGB levels on average. The isolated review also reports weak visible wool microtexture; that is not corrected by this pass.

**Colour and retained contracts.** The six calibrated displayed role means remain within 0.969 sRGB levels of `target-colours.json`; the palette and Godot pigment gains are unchanged. The actual garment crop remains darker than the generated target, as documented in Tunic14. The neutral chest mean is RGB 70.279/75.651/86.148 in Blender and 71.557/76.710/87.449 in the actual Godot-imported asset, maximum error 1.301 levels. The wider torso crop's maximum error is 2.937 levels. Both remain below the six-level limit. `final-measurements.json` records these actual means, separately from the flat-role calibration.

All 19 numbered thresholds are unchanged: 17 pass, with only the accepted G3/G6 failures. G1 is 0.040589; G2 is 0.000776; G5 is 0.322459; G30 has zero changed crossings; G31 is 20,305 triangles, ratio 1.47480; G32 is 0.62324 mm. Armhole median clearance remains 33.155 mm and all attachment bases remain within 2 mm. Over 105,985 visible upper-cloth pixels, dust raises mean RGB by 23.232 levels, and 98.066% brighten by at least eight levels. The eight-level and majority-coverage requirements are unchanged.

`test_crest_export.py` verifies exact geometry, bounds, hierarchy, names, pivots, all alpha, normals, material roles and every non-body image. Only one embedded image payload changes. The saved candidate and pruned standalone source re-export byte-identically. The focused run passes 24 Godot tests; the full guarded headless run passes 812, with zero failures. Twenty focused tunic scripts pass, including the density, exposure-policy and exported-asset regressions; the existing suites pass 19 sofa and 51 locker tests. All 91 locker PNG controls remain byte-identical to `tmp/mat/tunic/locker-before/`. No sofa/locker assets, shared aging code, application shaders or `app/quarters_props.gd` change. OCR review is skipped per Andrew 2026-10-09.

Matched images under `tmp/age/tunic15/` are `torso-before-after.png`, `blender-closeup-pair.png` and `godot-shoulder-pair.png`. `blender-control-sheet.png` and `godot-control-sheet.png` contain the individual layer controls. `blender-before/` and `blender-after/` retain full-resolution source frames. `godot-before/` and `godot-after/` use `tools/quarters_pilot_preview.gd` cameras, including `neutral-pair.png`, `closeup.png` and `in-locker-neutral.png`; the after capture loads the published GLB without the diagnostic texture substitution. Complete numerical results are in `layer-measurements.json`, `final-measurements.json`, `palette-colour-check.json`, `candidate/gates.json` and `dust-lit-difference.json`.

Rebuild with Blender `rebake_pilot_crest.py -- --out tmp/age/tunic15/candidate`, starting from `tmp/age/tunic14/short-fibres`. `test_crest_export.py --out tmp/age/tunic15/candidate --baseline tmp/age/tunic15/before.glb` checks the exported contract. The existing `publish_pilot.py` performs candidate/pruned-source repeat checks and retains the G3/G6 pilot exceptions. The checked drivers are `final-source-check.sh`, `tests.sh`, `verify-gates.sh`, `dust-check.sh` and `publish-and-capture.sh` under the scratch directory. The full suite runs with `nohup godot --headless --path . -s tests/run_tests.gd`, with its output retained under the same scratch directory.

### Godot tunic integration (2026-11-09)

`QuartersProps.material(&"dress_uniform", state, part, surface)` and `apply(root, &"dress_uniform", state)` now support both tunic assets. The default material is the state's `TunicBody` surface zero. Instantiate `dress_uniform.glb` for `as_built` and `dress_uniform_aged.glb` for `aged`; each retains its own geometry. Applying a finish preserves all imported nodes, names, transforms, meshes and bounds. Materials are constructed once per state and shared by imported material identity, including across instances. There is no per-frame material work.

Separate surface overrides preserve the medal's ribbon and brass, masked cloth cut edges and the shoulder's fractional-alpha rim. The three new tunic shaders retain glTF `OPAQUE`, `MASK` and `BLEND` roles, two-sided rendering, normal strengths, vertex colours, roughness and metallic values. Godot imports glTF `BLEND` as alpha with a depth prepass; the blend shader keeps that behavior. The aged Blender specular level of 0.12 is restored because Godot omits `KHR_materials_specular`. Clean wool remains navy and clean brass retains metallic 0.8; aged brass retains metallic 0.15 and roughness 0.94.

Both GLB import files embed their textures, avoiding dependencies on editor-extracted PNGs. Embedded colour and normal textures have mipmaps. Albedo uses an sRGB `source_color` sampler; normals use the linear `hint_normal` path. These exports have no ORM textures: metallic and roughness are constants, and the supplied colour already contains the baked occlusion. No GLB geometry or texture bytes change.

#### Godot colour check

The comparison reuses the actual 49 by 49 pixel neutral chest render at `tmp/age/tunic14/swatch/aged-chest-neutral.png` and its recorded locker-context camera. Godot uses the same 49 mm crop, position, surface-normal approach and white light position. A separate co-located 18% linear-grey plane matches illumination before wool fitting. Blender's mean grey is **119.137, 119.449, 119.754**; Godot's current capture is **118.969, 119.125, 119.471**, a maximum difference of **0.324 sRGB levels**. Godot's point-light energy is 4.17, ambient energy 0.0072 and fill energy zero for this calibration only. This measured grey reference compensates for the different area/point-light models rather than equating Blender watts with Godot light energy. The Godot preview retains its linear tone mapper; Blender retains AgX Medium High Contrast.

| Neutral chest | Mean displayed RGB, sRGB levels |
| --- | --- |
| Blender locker-context reference | 75.347, 80.793, 91.388 |
| Godot before material calibration | 83.382, 86.914, 96.167 |
| Godot after material calibration | 75.455, 80.841, 91.417 |
| Absolute calibrated difference | 0.108, 0.048, 0.029 |

The initial red-channel difference of **8.035 levels** exceeds the six-level tolerance. Multiplying aged wool, dust and fibre albedo in linear light by **0.813331, 0.860586, 0.899057** brings the maximum displayed difference to **0.108 levels**. This is a Godot material parameter, not a texture edit. Clean wool, brass, ribbon and hanger are excluded. The current measurements are in `tmp/mat/tunic2/colour-check.json`; the original attempts remain under `tmp/mat/tunic/raw/`, `light-matched/` and `uncalibrated/`. The fit establishes this chest patch under the calibration light, without claiming a whole-image match to the generated target or resolving the accepted G3/G6 geometry failures.

#### Captures and regression checks

Run the windowed Forward+ preview with:

```sh
nohup godot --windowed --path . -s tools/quarters_pilot_preview.gd -- \
  --prop dress_uniform --out res://tmp/mat/tunic2 \
  > tmp/mat/tunic2/preview.log 2>&1 < /dev/null &
nohup godot --headless --path . -s tests/run_tests.gd \
  > tmp/mat/tunic2/unit-suite.log 2>&1 < /dev/null &
```

The requested sheets are `before-after.png`, `neutral-pair.png`, `closeup.png` and `in-locker.png` under `tmp/mat/tunic2/`, each 2048 by 1024. `in-locker.png` now frames the hanging tunic at a 1.5 m orthographic span rather than 2.7 m, making it 1.8 times larger. `in-locker-neutral.png` uses the identical camera under white light. Complete lockers remain in `locker-context.png`; the heap and separate fallen strips remain in the standalone `in-locker-floor.png`, outside the main sheet. Remembered light is warm; present light retains the game's dim secondary-power settings with RGB **1.0, 0.97, 0.90**. Both neutral state views use identical light. The shoulder camera is perspective and exactly **0.5 m** from its target; both shoulder states now include their matching locker backing. `closeup-game-light.png` adds remembered/present light beside the neutral `closeup.png`.

Each locker retains its matching finish, with the door open **112 degrees**. Garments turn **55 degrees** to fit diagonally. Preview-only placement raises the hook to 1.65 m and seats the separately placed heap on the 0.105 m locker floor. The untextured preview ground now sits at y=0, beneath the locker base. Runtime application never makes these placement changes. An offscreen viewport retains the requested pixel dimensions while the renderer runs windowed. `preview.json` records camera positions, targets and projections.

Ten tunic tests cover both states, shared materials, source surface roles, texture mipmaps and colour-space roles, specular/normal settings, brass/ribbon separation, retained names/transforms/meshes, isolation from sofa/locker materials, renderer-owned backface correction, remapped normal UVs and generated orthonormal tangent frames. The focused run passes **24 tests, 0 failures**, including all four existing sofa tests and ten existing locker tests. The full guarded headless suite ran under `nohup` and passes **812 tests, 0 failures**. Existing Python regressions pass **19 sofa tests** and **51 locker tests**. Logs are `focused.log`, `unit-suite.log`, `sofa-python.log` and `locker-python.log` in `tmp/mat/tunic2/`. Godot retains its existing ObjectDB, resources-in-use and allocator teardown diagnostics. All **91 locker control PNGs are byte-identical** to `tmp/mat/tunic/locker-before/`. Reproduce those controls with `tools/quarters_aging/locker_preview.gd`, which prepares the existing hinge geometry before checking state swaps. The complete `app/quarters_props.gd`, sofa/locker shaders and assets remain byte-identical to `87fb9b7`. No geometry, texture or import setting changed. No OCR review was run, per Andrew's standing instruction.

#### Rendering diagnosis

The old shoulder preview hid its locker, unlike the approved Blender closeup. The real openings consequently exposed the near-black environment background. In the central **(312,312) to (712,712)** shoulder crop, **54,889 of 54,893** pixels whose mean RGB is below 45 brighten by more than 100 levels when only the background turns white. Showing the actual locker brightens all 54,893 by more than ten levels, without altering alpha or geometry. `shoulder-before-after.png`, `shoulder-context-sheet.png` and `background-check.json` record this control. The comparison uses identical camera and neutral light.

The tunic shaders also manually inverted backface normals after Godot had already done so for `cull_disabled`. Removing that second inversion restores the renderer's two-sided correction. The regression fails on the old shaders, with **22 passed, 1 failed**, then passes after the fix. This is a separate, smaller shading correction; it does not explain the background-sized dark gaps.

The alpha controls retain the exported **0.5** cutoff, which matches Blender's ROUND node for masked wool. The soft shoulder rim/cards retain fractional BLEND alpha. Disabling their depth prepass changes no shoulder pixel by more than six levels. Forcing opacity to mip zero changes only **254 of 1,048,576** pixels by more than six levels. Ordinary alpha-to-coverage applied to every alpha surface hardens the soft rim; alpha hash adds noise. Converting the masked body to blending makes broad cloth translucent and is rejected. Mask-only coverage at the same 0.5 contour also fails to produce a visible improvement in the image comparison. Separate soft-card controls find no material effect from disabling their normal map or reversing backface tangent axes. Doubling internal resolution, TAA and an 8x MSAA request do not resolve the remaining fringe appearance in the image comparison. Lambert diffuse changes cloth shading without repairing the edge, so the original Burley model is retained. These controls do not justify lowering the cutoff or changing source transparency roles. `control-sheet.png`, `mask-control-sheet.png`, `coverage-control-sheet.png`, `soft-control-sheet.png`, `shoulder-sampling-sheet.png` and their JSON measurements retain the alternatives.

Normal maps use the glTF/OpenGL convention without a green-channel inversion. Imported body normal R/G differs from embedded data by only **0.072/0.094 levels** on average; the removed blue channel is reconstructed by Godot. The body retains normal strength 1 and fibre maps retain 0.25. Godot remaps the glTF primary texture coordinates to UV, so substituting UV2 breaks the bake. The imported tangent frames pass unit-length, orthogonality and handedness checks. In the fixed torso patch **(460,340) to (550,520)**, disabling normal maps changes RGB by **0.942 levels** on average and leaves low-pass luminance variation at **3.985**, versus **4.123** with normals. It does not remove the broad variation. A flat-albedo control changes the patch by 20.802 levels, but also removes its supplied fade, dust and baked occlusion. Those pigments and the normal strength are retained rather than flattened to conceal the difference. `body-control-crops.png`, `body-controls.json` and `texture-check.json` separate these effects.

The horizontal floor stripes belong to the unchanged locker. They persist when the untextured preview ground or debris is hidden and disappear when the locker is hidden. `floor-control-sheet.png` records all four views. The main locker sheet now excludes this grazing-angle floor inset; the separate floor capture still exposes the locker issue for inspection. No locker material or UV was changed.

Image-comparer confirms that the conspicuous black background gaps are gone in `shoulder-before-after.png`, while still flagging thin wispy/speckled fringe compared with Blender. Its separate inspection of `aged-lighting-pair.png` finds the complete tunic large enough to judge, opaque outside its tears, smoothly shaded without conspicuous cloudy or normal-map artifacts, and readable under the retained game light. It still calls the damaged outlines coarse and the small fittings blocky. These observations do not establish full Blender render parity. The source geometry's accepted G3/G6 limitations and the flat-looking ribbon remain outside this material/capture correction.

### Tunic14: shoulder drape and fibre-card polish

This pass retains the calibrated pigments, chest repair, extended hem strips and fibre heap from Tunic13. It changes only the torn shoulder and its attached fringe. The tall triangular flap came from the pass-12 free-edge lift, rather than a loose fringe card. The replacement lowers the tongue by 14 mm, lays it forward by 16 mm and outward by 10 mm, and gives it a 4 mm local roll with a 3 mm downturned tip. The opposite lip drops 14 mm and moves back 12 mm. A smooth pinned transition preserves the retained armhole stitches, shoulder-board seating and hanger support.

Matched cards-off and cut-rim-off controls isolate the conspicuous dark dashes to the curved fibre cards. Reversing their shading-normal orientation did not fix the appearance and was rejected. Rounding atlas alpha changes edge softness but does not remove the dashes. The shoulder cards projected up to **8.408 mm** from their root lines; seam-allowance cards reached **6.009 mm**. Their projected height is now limited to **1.2 mm**, retaining root width and arclength coverage. Cards are reseated against the changed cloth. The thin shoulder cut rim follows the new sheet with 0.10 to 0.35 mm thickness; its intersections are checked rather than hidden. Fractional atlas alpha and parent-cloth fibre normals soften the remaining short fringe without changing any colour or alpha PNG bytes.

The numerical comparison isolates 1,491 previously dark card pixels in the upper tear crop: cards-off must brighten them by more than ten sRGB levels and the original mean RGB must be below 70. Shorter cards brighten **1,254 of those pixels (84.105%)** by more than ten levels; nine darken by that amount. Their mean RGB changes from **55.698, 59.532, 61.710** to **76.161, 81.064, 82.109**. This measures the removed dark-card footprint, not the brightness of the garment as a whole. The broad dark opening beneath the torn cloth remains intentional. The image-comparer confirms that the tall shard is gone and the free cloth droops. Its tighter fibre comparison finds the conspicuous dark dashes removed, with short lighter fuzz remaining. It still notes a somewhat decal-like fringe transition; this is a visual qualification, not a claim of matching every detail in the target.

All thresholds remain unchanged. G3 and G6 retain Andrew's accepted pilot exceptions; they are still reported as failed. The exported candidate has the following measurements:

| Gate | Measured | Result |
| --- | --- | --- |
| G1 visible sharp adjacency | 4.058853% | Pass, at most 6% |
| G2 normal-jump pixels | 0.077591% | Pass, at most 2% |
| G3 longest straight lip run | 35.014283 px | Accepted exception, at most 12 px required |
| G4 visible tear-gap width CV | 0.726940 / 0.757397 / 0.985331 / 0.713087 / 0.447153 | Pass, each at least 0.35 |
| G5 lip length lifted over 3 mm | 32.245909% | Pass, at least 30% |
| G6 contour dimension | 0.993555 to 1.171888 | Accepted exception, each must be 1.15 to 1.40 |
| G20 hanger-region sharp adjacency | 5.242668% | Pass, at most 10% |
| G21 hanger leak pixels | 0 | Pass |
| G22 sleeve depth / width | 0.425571 | Pass, at most 0.45 |
| G23 retained armhole arc / released-edge fringe coverage | 36.004298% / 70.398494% | Pass, at least 35% / 70% |
| G24 chest width / unaged | 1.014139 | Pass, 0.92 to 1.08 |
| G25 open-hem fringe coverage | 82.121978% | Pass, at least 70% |
| G26 hem-height autocorrelation peak | 0 | Pass, below 0.30 |
| G27 heap height | 33.057582 mm | Pass, 15 to 35 mm |
| G28 fallen pieces | 6 | Pass, at least 2 |
| G29 inferred heap packing | 0.142769 | Pass, 0.05 to 0.15 |
| G30 changed/new-part SAT crossings | 0 | Pass; unchanged hanger baseline remains 28 |
| G31 triangles | 20,305 / 13,768 unaged, ratio 1.474797 | Pass, at most 1.5 |
| G32 boundary Hausdorff | 0.623240 mm | Pass, at most 1.5 mm |
| Armhole maximum clear opening | 41.958148 mm | Pass, at least 25 mm |
| Independent attachment seating | Maximum base distance 1.800060 mm | Pass, at most 2 mm |

The lit dust ON/OFF control passes without changing its threshold: **97.978016%** of 105,985 visible upper-cloth pixels brighten by at least eight sRGB levels; the mean increase is **20.829265** and median **21.333333**. The published `dress_uniform_aged.glb` reproduces byte-identically from the pruned standalone `tunic-pilot.blend`, including a fresh reopen and export. Node names, pivots, external Y-up bounds, every pigment/alpha PNG and the as-built asset remain unchanged.

#### Neutral-light wool comparison

`tmp/age/tunic14/wool-neutral-swatch-sheet.png` places an actual rendered aged-chest crop beside the fixed target's wool crop at **(596, 496) to (645, 545)**. Both are 49 by 49 pixels, enlarged identically eightfold, with no exposure, colour or histogram correction. The candidate uses white light, exposure zero and the retained AgX view. The arithmetic mean RGB is **75.347, 80.793, 91.388** for the rendered chest and **101.081, 104.166, 111.483** for the target, in sRGB byte units. Their medians are **74, 80, 90** and **102, 106, 114** respectively. In this comparison the candidate is darker, with a larger blue-minus-red difference. No pigment changes follow from the pale-grey assessment.

The target is a generated PNG with baked lighting and no recorded exposure or physical ruler. Its original lighting cannot be reproduced from those pixels. The rendered crop uses an approximate 1 mm per target pixel, recorded in `swatch/neutral-light.json`; both crops receive the same display sampling and no post-adjustment. This sheet does not establish a physically matched target relight. It also does not replace Tunic13's within-one-level calibration of flat displayed swatches.

The requested locker-context composites are under `tmp/age/tunic14/`: `tunic-in-locker-before-after.png`, `tunic-in-locker-closeup.png`, `tunic-in-locker-heap.png` and `tunic-target-match.png`. `context/` retains the same cameras and lighting as Tunic13, including the 0.5 m shoulder camera. `controls/` contains matched full, cards-off, cut-rim-off and hard-alpha frames; `smooth-controls/` retains the longer-card controls used for diagnosis. `fibre-projection-comparison.png` and `fibre-projection-difference.json` record the card-length comparison. The swatch pixels and measured means are retained under `swatch/`.

Rebuild with Blender `polish_pilot.py -- --out tmp/age/tunic14/short-fibres --edge-normals --soft-shoulder`, starting from `tmp/age/tunic13/blue` and the retained rest-pattern source. `test_shoulder_drape.py` tests the supported root, roll and tip; Blender `test_shoulder_fibres.py` tests exact fibre roots, width, topology and unaffected vertices. `test_shoulder_export.py --out tmp/age/tunic14/short-fibres --baseline <Tunic13 GLB>` checks names, pivots, unchanged pigment/alpha bytes, shoulder-only geometry, unchanged gate thresholds, seating, external Y-up bounds and byte-identical re-export. OCR review is skipped per Andrew 2026-10-09. This pass changes no application code, game tests or shared aging helpers and makes no new Godot integration claim.

### Tunic13: exported pilot, with two accepted geometry limitations

The delivered aged asset is `assets/props/quarters/dress_uniform_aged.glb`, with packed editable source `tools/blender/quarters/dress_uniform/tunic-pilot.blend` and its PNG textures under `assets/props/quarters/dress_uniform/`. The as-built navy/bright-brass GLB is byte-for-byte unchanged. This finish retains pass-12 geometry except two free hem tongues and their attached fringe. The ship has been adrift about **1000 years**.

Andrew accepted pass-12 geometry as showable for the pilot after an anchored fixed-target review rated it 70%, compared with pass 11's 60%. **G3 still fails at 37.047267 px, and G6 still fails with a 0.979305 minimum.** Andrew's exception permits pilot export while both gates remain failed and their thresholds stay unchanged. All other gates and the independent attachment audit pass on this export. Godot material integration is deferred; this pass changes no application code, game tests or shared aging helpers.

#### Display-to-albedo calibration

The target's regional RGB samples already include illumination and tone mapping. `calibrate_pilot.py` renders flat swatches in the fixed locker scene, measures the central displayed pixels and iterates the linear albedo using the linearised display-colour ratio. The lighting remains the 75 W ceiling strip, dim world and AgX Medium High Contrast view. The final fit uses a common upper-chest plane at world (-0.08, -0.31, 1.30) m with normal proportional to (0.47, -0.88, 0), measured from the exported garment. The fibre-dust swatch uses the floor location. Keeping garment pigments on the same plane avoids comparing a shaded substrate with a directly lit dust swatch.

The chest-reference fit uses 17 initial swatch renders across six roles, followed by eight renders after broadening the primary wool sample. Every final role is within one sRGB byte level of its sampled target. The old 5 by 5 wool patch at target (620, 520) had median RGB (104, 106, 109); a 49 by 49 patch at the same point gives (102, 106, 114). The smaller mottled patch underrepresented the blue cast. All other target patches stay unchanged. Every attempted albedo and displayed result is recorded in `tools/blender/quarters/dress_uniform/target-colours.json`, also copied to `tmp/age/tunic13/target-colours.json`. It retains the original samples, mixed-orientation trial, upward-only trial and narrow-patch chest fit with their dispositions. The upward-only fit made the front cloth too dark in the locker view. The fitted swatches do not establish a pixel match for the entire target photograph.

| Role | Final linear-RGB albedo | Target display RGB | Final swatch RGB | Chest-fit renders, including broad-patch check |
| --- | --- | --- | --- | --- |
| Dark wool fold | 0.031189, 0.034975, 0.047071 | 46, 50, 57 | 47, 50, 57 | 3 |
| Dusty grey-blue wool | 0.103681, 0.111554, 0.139753 | 102, 106, 114 | 102, 106, 114 | 6 |
| Faded wool ridge | 0.125226, 0.133025, 0.156793 | 114, 117, 122 | 114, 117, 122 | 4 |
| Shoulder dust | 0.149091, 0.165695, 0.205108 | 126, 131, 139 | 126, 131, 139 | 5 |
| Floor fibre dust | 0.205806, 0.215150, 0.234512 | 126, 127, 128 | 126, 127, 128 | 3 |
| Dull brown brass | 0.178494, 0.162993, 0.130634 | 131, 122, 105 | 132, 122, 105 | 4 |

Wool retains blue greater than green greater than red, with darker self-occluded folds and lighter convex ridges. Broad dust coverage follows upward exposure and upper-garment height; fine grain amplitude is reduced so it does not replace the directional deposit with uniform speckle. Brass uses metallic 0.15, roughness 0.94 and specular 0.12 to represent an oxide-dulled surface. The higher-metallic trial retained pale reflections on the fittings.

#### Chest repair, hem and lit dust control

The isolated chest disk at hero pixel approximately (465, 495) was a stale selected-to-active AO transfer. The cloth there was opaque, with alpha 1, AO 0 and a neutral tangent normal. A 60 mm current-cloth-only self-occlusion bake excludes hidden dense copies and fittings. AO at the old spot is now **0.956863**. Its rendered 10 px-radius mean RGB changes from (23.68, 24.85, 25.62) to (78.61, 81.75, 88.03), removing the isolated near-black disk.

Two retained front hem tongues extend downward by approximately **78 mm and 99 mm**, with forward drape at 0.7 times the extension to avoid the separate floor debris. No side-to-side displacement is added. Faces crossing the extension root are split at z = -0.840 m so straight interpolation cannot drive an adjacent rim through the sheet. Only affected faces are triangulated; unaffected fringe keeps its original tessellation. Export inspection confirms exact node names and transforms, unchanged fittings and hanger, and exact body/fringe triangles outside the two selected hem regions. G25 coverage is 82.121978% and G26 remains zero.

The matched locker closeup disables dust on all five garment-cloth parts while retaining fade, alpha, camera, exposure and lighting. A separate alpha-aware raw diagnostic selects visible body/collar/board pixels above 1.31 m whose geometric normal has world Z greater than 0.35. Over **107,153 fully covered shoulder-top pixels**, dust raises mean RGB by **20.803966 sRGB levels**, with a median of **21.333333**. **98.107379%** rise by at least **8 levels**, exceeding the requirement over most shoulder tops. The measurement uses lit ON-minus-OFF captures to test the displayed change. `pilot-dust.json` stores the result; captures and the raw mask are in `tmp/age/tunic13/`.

#### Export gates and source

`pilot-gates.json` and `pilot-seating.json` beside the packed source contain the measured values and explicit pilot exceptions. The full gate measurement still exits 1 because G3 and G6 fail. Publication separately permits only those two failures and requires passing seating, dust and byte-identity checks.

| Gate | Measured | Requirement | Result |
| --- | --- | --- | --- |
| G1 | 4.026253% visible sharp adjacency | At most 6% | Pass |
| G2 | 0.115220% normal-jump pixels | At most 2% | Pass |
| G3 | 37.047267 px longest straight lip run | At most 12 px on every visible lip | Accepted pilot failure |
| G4 | 0.454798 to 0.850919 width CV | At least 0.35 on every visible gap | Pass |
| G5 | 30.552230% lifted lip length | At least 30% over 3 mm | Pass |
| G6 | 0.979305 to 1.379382 contour dimension | Every resolved lip 1.15 to 1.40 | Accepted pilot failure |
| G20 | 4.541915% near-hanger sharp adjacency | At most 10% | Pass |
| G21 | 0 hanger pixels outside split hull | Zero | Pass |
| G22 | 0.425571 maximum sleeve depth/width | At most 0.45 | Pass |
| G23 | 36.004298% retained arc; 78.673496% released-edge fringe | At least 35%; at least 70% | Pass |
| G24 | 101.413899% chest width | 92% to 108% | Pass |
| G25 | 82.121978% open-hem fringe | At least 70% | Pass |
| G26 | 0.0 hem autocorrelation peak | Below 0.30 | Pass |
| G27 | 33.057582 mm mound height | 15 to 35 mm | Pass |
| G28 | 6 fallen cloth pieces | At least 2 | Pass |
| G29 | 351.508860 cm³ mound; 50.184712 cm³ lost wool; 14.276941% inferred packing | Volume within factor 2 at 5% to 15% packing | Pass |
| G30 | 0 changed crossings; hanger 28/28, geometry exact | Zero; exact unchanged hanger | Pass |
| G31 | 20,305 / 13,768 triangles, ratio 1.474797 | At most 20,652, ratio 1.5 | Pass |
| G32 | 0.623240 mm retained boundary-error bound; extended-hem bound 0.050156 mm | At most 1.5 mm | Pass |

The extended hem is checked against the dense reference after applying the same root-split affine extension. The baseline dense and reduced hem boundaries match exactly. Bidirectional samples at no more than 0.1 mm give a 0.000156 mm sampled difference after extension; adding half the sample spacing bounds the new hem error at 0.050156 mm. The unchanged remainder retains its 0.623240 mm bound. All attachment bases remain within 2 mm; the maximum is 1.800060 mm. External trimesh inspection confirms exported +Y-up bounds, 29 named parts and 20,305 triangles.

The measured candidate, checkpoint reload, pruned standalone source export and fresh standalone-source reload all produce **byte-identical GLBs**. The packed source includes only the exported parts and active material graphs; committed PNGs are also packed into it. Re-export with Blender:

```sh
blender --background --threads 3 --python-exit-code 1 \
  --python tools/blender/quarters/dress_uniform/publish_pilot.py -- \
  --export-only tmp/age/tunic13/reexport.glb
```

The complete finishing run starts with `pilot_finish.py -- --base tmp/age/tunic12/curled --out tmp/age/tunic13/blue`. `test_pilot_export.py` checks the actual GLB against pass 12, including frozen triangles, pivots, repaired AO, retained gates, seating and repeat bytes. Focused hem, lip-station, lip-metric, wear, fringe, heap-alpha, shoulder, support and colour scripts pass. OCR review is skipped per Andrew 2026-10-09. No Godot integration is claimed in this pass.

The four requested composites are under `tmp/age/tunic13/`: `tunic-in-locker-before-after.png`, `tunic-in-locker-closeup.png`, `tunic-in-locker-heap.png` and `tunic-target-match.png`, all 2400 by 1440. `context/` holds the source frames and cameras, `dust-off/` holds the matched control, and `dust-top-detail.png` shows the upper-cloth crop. The final image-comparer result is recorded separately in `final-art-review.json`. It judges all requested material and aging goals achieved, including a visible cool/blue cast, directional dust, dull readable brass, no circular chest artefact, distinct longer strips, soft fray and a volumetric heap. It reports no rendering defects in that scope. The blue cast still reads slightly weaker than the fixed target, and the exact number of long strips is uncertain in the low-contrast full-body capture. Those visual qualifications remain separate from the two documented geometry-gate exceptions.

### Tunic12: historical checkpoint before pilot approval

The final scratch candidate at this checkpoint was `tmp/age/tunic12/curled/candidate.glb`. G3 and G6 failed, so the delivered `assets/props/quarters/dress_uniform_aged.glb`, its textures and the as-built navy/brass asset remained unchanged then. This pass starts from tunic11's `visible/baked.blend` and retains its settled garment, connected allowance, hanger and fittings. The age is 1000 years. The fixed `aged-target.png` supplies the overall look; `aged-target.json` explicitly leaves shoulder, armhole and hem damage placement to the plan.

**Physical lips and visibility.** The old world-coordinate projection traversed only 43.9% to 70.7% of armhole arclength. Each connected boundary now gets cumulative physical stations sampled every 0.20 mm. Its opacity noise uses 2.2, 1.1, 0.55 and 0.275 mm wavelengths, with monotone inward losses of 0.15 to 6 mm. Every allowance triangle gets nonzero bake area and the sheet's wool/opacity material, including its cut edge. These repairs do not eliminate the remaining straight or under-detailed contours. A wider noise-spectrum experiment was measured and rejected.

The hero shoulder previously exposed only its back lip. Moving the front lip forward or down left G4 unmeasurable. Raised-edge controls resolve the second contour between 24 and 27 mm of additional lift. The adopted free-edge curl has at most 31.385 mm total motion, while front cloth within 8 mm of the board and the inner front region x <= 180 mm remain fixed. Its narrower pattern-length falloff leaves the adjacent panel in place: G5 rises from the broad-deformation trial's 29.4289% to 30.5522%. Hero shoulder width CV is 0.746692. All five measured gaps now pass G4.

Panel dissolution had changed the sleeve sections despite preserving vertex positions. Sleeve faces and fitting-support faces now survive reduction exactly. Only free torso panels dissolve, up to 12 degrees, reaching the unchanged triangle budget. The final sleeve ratio is 0.425571. An earlier raised-lip trial had one sheet/rim crossing near x=171 mm. Keeping the inner region fixed removes it. The existing 0.1 mm minimum rim depth and its tests remain unchanged; allowing thinner rims was rejected after it failed that existing assertion. The final rim compressor records three initial contacts and zero remaining contacts. Exported G30 also reports zero changed-part crossings.

**Hem, fray and debris.** Six unequally spaced slots remove 48.7309 cm² of actual hem sheet, leaving five tongues with different widths and up to 41.000 mm of downward relaxation. The centre-front fitting support stays fixed. Curved, tapered cards extend fraying to cuffs, hem and openings. The mound is broadened, and three additional crumpled strips bring the fallen-piece count to six. Their actual areas are deducted from the new hem loss before assigning the remainder to fibre dust; alpha losses are measured separately. The final inferred packing is 14.2769%.

The mound carries 150 curved bundles, 600 triangles, placed by upward ray hits on its actual surface and checked against surrounding geometry. Eighteen strands across the previous sub-1.2-mm cards were below close-view resolution. The mound now uses four wider curled bundles on 3-4 mm cards, separately from fine edge fray. A later helper renamed the heap material, defeating name-based atlas selection. Selection now uses the material owned by `HeapFibres`; the real-GLB test verifies that its exported alpha contains four bundles. Numeric volume and coverage do not establish a loose-fibre appearance.

**Baked aged colour.** Wool fade and dust are baked into the candidate's own base textures, using Cycles AO, world up-facing normals, positive normal-Laplacian curvature and independent exposure variation. Exposed upper cloth and crests fade toward grey-blue; occluded folds retain darker colour. Heap fibres use the sampled neutral fibre-dust colour. Brass receives its own brown/patina texture and higher roughness. None of these tunic colours is a context-render override. The locker retains the pass-eleven review setup.

The colour reference is a 5-by-5 regional median at image-comparer-labelled positions in the fixed target. Lighting and tone mapping are present in these samples. sRGB bytes are converted to linear values for baking. Complete patches and ranges are in `tmp/age/tunic12/target-colours.json`.

| Reference | Target x,y | sRGB bytes | Linear RGB |
| --- | --- | --- | --- |
| Dark fold | 430,720 | 46,50,57 | 0.027321,0.031896,0.040915 |
| Dusty grey-blue | 620,520 | 104,106,109 | 0.138432,0.144128,0.152926 |
| Faded crest | 380,245 | 114,117,122 | 0.168269,0.177888,0.194618 |
| Shoulder dust | 640,230 | 126,131,139 | 0.208637,0.226966,0.258183 |
| Fibre dust | 520,940 | 126,127,128 | 0.208637,0.212231,0.215861 |
| Dull brown brass | 492,355 | 131,122,105 | 0.226966,0.194618,0.141263 |

All nineteen gates below use the actual final export and fresh diagnostics. Thresholds and collision exclusions are unchanged. Full per-lip results remain in `curled/gates.json`.

| Gate | Measured | Requirement | Result |
| --- | --- | --- | --- |
| G1 | 4.032360% visible sharp adjacency | At most 6% | Pass |
| G2 | 0.115220% normal-jump pixels | At most 2% | Pass |
| G3 | 37.047267 px longest straight lip run | At most 12 px on every visible lip | Fail |
| G4 | 0.454798 to 0.850919 width CV; hero shoulder 0.746692 | At least 0.35 on every visible gap | Pass |
| G5 | 30.552230% lifted lip length | At least 30% over 3 mm | Pass |
| G6 | 0.979305 to 1.379382 contour dimension | Every resolved lip 1.15 to 1.40 | Fail |
| G20 | 4.541915% near-hanger sharp adjacency | At most 10% | Pass |
| G21 | 0 hanger pixels outside split hull | Zero | Pass |
| G22 | 0.425571 maximum sleeve depth/width | At most 0.45 | Pass |
| G23 | 36.004298% retained arc; 78.673496% released-edge fringe | At least 35%; at least 70% | Pass |
| G24 | 101.413899% chest width | 92% to 108% | Pass |
| G25 | 82.661868% open-hem fringe | At least 70% | Pass |
| G26 | 0.0 hem autocorrelation peak | Below 0.30 | Pass |
| G27 | 33.057582 mm mound height | 15 to 35 mm | Pass |
| G28 | 6 fallen cloth pieces | At least 2 | Pass |
| G29 | 351.508860 cm³ mound; 50.184712 cm³ lost wool; 14.276941% inferred packing | Volume within factor 2 at 5% to 15% packing | Pass |
| G30 | 0 changed crossings; hanger 28/28, geometry exact | Zero; exact unchanged hanger | Pass |
| G31 | 20,255 / 13,768 triangles, ratio 1.471165 | At most 20,652, ratio 1.5 | Pass |
| G32 | 0.623240 mm boundary error | At most 1.5 mm | Pass |

Every attachment passes the independent 2 mm base-distance audit. The two board maxima remain 1.299531 and 1.421234 mm; the medal ribbon reaches 1.800060 mm. Saved-scene re-export is byte-identical. All sixteen focused scripts pass, including actual exported alpha/colour/normal UV contracts, allowance UV area, physical stations, immutable sleeve/support faces, hem supports, curved fringe, four-bundle heap alpha and 3,072 retained-binding opacity samples. The existing reduced-clearance control also passes unchanged. The full nineteen-gate measurement command exits 1 because G3 and G6 fail.

**Locker captures.** Pass-eleven cameras and lighting remain the main review. The final images are `tmp/age/tunic12/tunic-in-locker-before-after.png`, `tunic-in-locker-closeup.png`, `tunic-in-locker-heap.png` and `tunic-target-match.png`. Their source frames and camera records are under `context-curled/`; studio diagnostics are under `curled-images/`. The matching dust-off closeup is `context-curled-no-dust/after-closeup.png`, using the final GLB with only body dust disabled. Fade, camera and lighting stay unchanged. Baked mask coverage does not establish visible dust.

**Visual assessment: the fixed look is not achieved.** The configured image-comparer, Qwen3.8-27B, reviewed all four locker composites plus raw dust-on/off closeups. It accepts the soft curled fray, volumetric fibre heap with separate crumpled strips, and dull brown brass with readable insignia. It sees no green or biological material. The hanging hem has an irregular edge, but its constructed tongues still do not read as the target's long distinct hanging strips. The partly attached sleeve opening also reads harshly dark.

The candidate is judged too pale and neutral against the target, with a uniform-looking fine speckle. Directional shoulder dust is not visually established by the matched control. The complete-frame mean absolute dust-on/off difference is 0.574988 sRGB byte values; 1.5675% of pixels differ by at least eight in any channel. These measurements have no body mask and do not constitute visual acceptance. The directional mask exists in the bake; the review does not establish why its contribution reads weakly. Source display-colour samples have not been calibrated through the fixed lighting and AgX pipeline. That colour fit, visible directional dust, longer readable tongues, G3 and G6 remain unfinished. The review is `tmp/age/tunic12/curled-review.json`, and the lit difference measurements are `dust-lit-difference.json`.

Rebuild with `polish_pass12.py -- --shape --out tmp/age/tunic12/retained-curled`, then `finish_aging.py` with that output and `colour_pass12.py -- --base tmp/age/tunic12/retained-curled --out tmp/age/tunic12/curled`. Render, collision, seating and measurement commands are in `tmp/age/tunic12/curled.sh`; final tests and the lit dust-off comparison are in `review-curled.sh`. Shared aging modules and the locker asset were not edited. At that checkpoint production export was blocked by G3 and G6; the Tunic13 section above records Andrew's later pilot exception.

### Tunic11: not shipped, 16 of 19 gates pass

The final scratch candidate is `tmp/age/tunic11/visible/candidate.glb`; `retained/` records the preceding surface-wear control. G3, G4 and G6 still fail, so neither `assets/props/quarters/dress_uniform_aged.glb` nor its textures was replaced. Pass eleven starts from pass ten's `curled/baked.blend`, preserving its settled sleeve, connected allowance, surviving yarns, hanger and seated fittings. The intended age remains 1000 years. Physical-lip experiments introduced new crossings and were rejected rather than replacing the pass-ten shape.

**Locker context.** The full-size tunic hangs diagonally at 55 degrees in the unmodified `storage_locker_module.glb`, whose door is opened 112 degrees for the scene. Its hanger crown is 1.65 m above the locker base, on a rail spanning the side panels. One sleeve extends through the open doorway; transformed wool vertices do not cross the side or back panels. The inner floor is at 0.105 m. The garment was raised to this plausible hanging height and the heap, fallen strips and loose fibres were placed separately on that floor. This gives a scene floor drop of 1.545 m; the asset's authored 0.95 m parameter is unchanged.

The provisional locker paint has linear albedo 0.065/0.080/0.070, roughness 0.76 and metallic 0.15. A 75 W rectangular area light at Blender (0.1, -1.0, 2.65) supplies dim overhead/front light with colour (1.0, 0.97, 0.90). There is no rim light. The back panel is 225.7 to 252.2 mm behind the pass-ten armhole yarn roots, instead of the distant lit studio floor. The 0.5 m close camera approaches through the doorway: approaching along the rotated garment normal crossed the right locker wall and produced an unusable dark control. The corrected camera sees the shoulder and upper torso. Both states use identical cameras and lighting. Context captures are the main review images; studio captures remain for comparison. The initial pass-ten-in-locker comparison is under `tmp/age/tunic11/context-base/`. Its review preceded the geometry and finishing trials.

**Contour diagnosis.** G3/G4/G6 use unlit emission labels, decoded as wool-plus-fringe alpha coverage. They do not trace the lit wool's shading boundary. On the pass-ten control, ordinary rendering gives a 27.459060 px longest run. Making the wool opaque leaves that maximum unchanged and changes little on the armhole; hiding fringe increases it to 39.849718 px. The connected allowance is an opaque, separately shaded material, so the sheet opacity texture cannot roughen its outer contour. Removing that texture is therefore not a repair for those lips.

Rendering at twice the resolution reveals more small fibre detail, but still gives a 26.967573 px longest run after conversion back to the original pixel scale. Several qualifying contours remain below dimension 1.15, while others exceed 1.40. Antialiasing and subpixel coverage affect fine fringe, but do not explain away the straight physical outlines. The original geometry noise also uses a fixed world-space projection: its station variation on the three armhole chains is only 43.9% to 70.7% of physical arclength, stretching the intended noise wavelengths. No measurement algorithm or numbered threshold was relaxed. Controls and individual contour results are in `tmp/age/tunic11/diagnosis/` and `noise-projection.json`.

Two physical-boundary trials refine the existing lips and add inward losses. The first leaves 50 new body/rim crossings, lifts only 27.3100% of lip length and exceeds the triangle budget. Arclength-based losses bounded by supporting face depth reduce the crossings to 22, but lift remains 26.7864%, below 30%. Its midsurface has zero self crossings before thickness; the new rim geometry introduces the 22 crossings. These are rejected trials under `candidate/` and `arclength/`, not accepted geometry. `polish_pass11.py --refine-lips` retains the bounded experiment; the default keeps the pass-ten lips.

**Wool finishing.** The long-fringe category now has 47 cards instead of 69. Shoulder and seam tufts use four transverse sections with curl and taper, mostly 2.5 to 4.5 mm long. A separate atlas supplies rounded, curved wool bundles with fractional edge coverage; shortening a card while retaining straight atlas strands still produced bristles. Hem and fallen-strip fringe retain their previous atlas. Coverage measures each tuft's attached root once, rather than counting its internal section edges as additional roots. Released-seam root coverage is 79.6704%, above 70%.

The first retained-lip control scores 5/10 against the fixed aged target's 8/10 on that reviewer's scale. Its 5.6 mm-wide patch control still reads as punctures, its broad wool remains too uniform, and the heap reads as a flat backing with angular scraps. This is a separate comparison from the earlier pass-ten rating, which used a different reference and scale.

Seven fold-aligned losses are now short, irregular patches with surrounding thinning rather than long narrow slit masks. The final visibility trial enlarges them by 1.5 times in each direction, removing 203.2697 square millimetres of wool. It also bakes distributed blue-grey fading separately from the thinning mask. Additional broad wrinkles and sag move the wool at most 2.4772 mm, below the fittings and away from the placket. The original 2.5 mm local motion limit is unchanged. G1 and G24 remain within their limits.

The original mound and fallen-strip geometry are retained; loose mound fibres use the curled atlas. Each fallen piece now has perimeter-only alpha erosion within 3 mm of its physical edge, while its interior stays opaque. The additional 837.8124 square millimetres of lost strip-edge wool are included in the heap mass estimate. This avoids leaving a completely straight, opaque strip boundary beneath the frayed cards. These construction changes do not establish visual acceptance. The final image-comparer review remains 5/10 against the fixed target's 8/10. It still finds hard shoulder strands, isolated torso marks, insufficient visible wool variation and a flat-looking heap. The task's remaining visual defects are not resolved. That review also asks for a lip touching the steel; contact with the backing is not a requirement and was not introduced. The scene retains the measured air gap between wool and steel.

All 19 numeric gates below are measured on the final visibility candidate. G3 has 13 over-limit runs among 30, and eight of eleven qualifying G6 contours are outside their limits. Those image-space results are worse than pass ten's despite the unchanged 16/19 pass count. G4's first value is the hero shoulder, where only one lip is measurable; the other values are hero armhole, close shoulder and close armhole. Missing width evidence remains a failure.

| Gate | Measured value | Threshold | Result |
| --- | --- | --- | --- |
| G1 | Visible sharp adjacency 1.967946% | ≤6% | Pass |
| G2 | Normal-jump pixels 0.143307% | ≤2% | Pass |
| G3 | Longest visible lip run 37.583241 px | ≤12 px | Fail |
| G4 | Width CV unavailable / 0.822366 / 0.775748 / 0.873879 | Each measurable and ≥0.35 | Fail |
| G5 | Lifted lip length 32.031467% | ≥30% lifted over 3 mm | Pass |
| G6 | Dimensions 0.936005 to 1.183320; 8 of 11 fail | Each qualifying contour 1.15 to 1.40 | Fail |
| G20 | Near-hanger sharp adjacency 3.348641% | ≤10% | Pass |
| G21 | Hanger pixels outside the split hull 0 | 0 | Pass |
| G22 | Maximum hero sleeve depth/width 0.425572 | ≤0.45 | Pass |
| G23 | Retained arc 36.004298%; released fringe 79.670392% | ≥35%; ≥70% | Pass |
| G24 | Chest width/unaged 1.014395 | 0.92 to 1.08 | Pass |
| G25 | Open-hem fringe coverage 86.020641% | ≥70% | Pass |
| G26 | Hem-height autocorrelation peak 0.0 | <0.30 | Pass |
| G27 | Mound height 26.876078 mm | 15 to 35 mm | Pass |
| G28 | Fallen cloth pieces 3 | ≥2 | Pass |
| G29 | Mound 95.259745 cm³; lost wool 9.510194 cm³; inferred packing 9.983435% | Factor 2 of lost-wool volume at 5% to 15% packing | Pass |
| G30 | Changed SAT crossings 0; original hanger 28/28; hanger geometry exact | 0 changed crossings; exact hanger baseline | Pass |
| G31 | 20,580 triangles / 13,768 unaged = 1.494770 times unaged | ≤20,652 and ≤1.5 times unaged | Pass |
| G32 | Worst boundary bound 0.623240 mm | ≤1.5 mm | Pass |

The separate armhole gap audit passes at 32.940270 mm median, against 25 mm minimum. Every attachment base passes the independent 2 mm seating audit. Shoulder-board maxima remain 1.299524 and 1.421234 mm; the largest other gap is 1.800060 mm at the medal ribbon. The saved blend re-exports byte-identically. All nine studio camera records match pass ten exactly, including position, aim, projection, lens, distance and resolution.

The requested images are `tmp/age/tunic11/tunic-in-locker-before-after.png`, `tunic-in-locker-closeup.png` and the supplemental `tunic-in-locker-heap.png`. Studio comparisons are `tunic-before-after.png`, `tunic-turntable.png` and `tunic-closeup.png` in the same directory. Individual context states and camera/setup records are under `context-visible/`; studio diagnostics are under `visible-images/`. The unchanged legacy studio renderer still substitutes grey for unrecognised untextured materials, including the exposed allowance and surviving yarns, so its bright opening is not a faithful colour comparison with the locker render.

Focused Blender controls pass, including the saved-candidate contracts, independent fading/thinning channels, fallen-edge opacity and area accounting, and 3,072 retained-binding opacity samples. Six Python wear/atlas checks and five open-lip metric checks pass. The full acceptance command exits 1 because G3, G4 and G6 fail. Per-opening values, all SAT contacts and seating are in `visible/gates.json`, `collisions.json` and `attachment-audit.json`. No shared aging module or locker asset was edited. Rebuild with `polish_pass11.py -- --out tmp/age/tunic11/visible`, then `finish_aging.py`, `render_aging.py`, `render_context.py`, `compose_context.py`, the shared studio composer/collision audit, `audit_attachments.py` and `measure_aging.py`. The scratch driver is `tmp/age/tunic11/run.sh`.

### Tunic10: rejected, 16 of 19 gates pass

The measured candidate is `tmp/age/tunic10/curled/candidate.glb`. G3, G4 and G6 fail, and the visual review rejects it for close-up use. The production `assets/props/quarters/dress_uniform_aged.glb` and its tunic textures remain unchanged. Pass ten starts from `tmp/age/tunic9/binding/baked.blend`, preserving the settled sleeve, retained underarm, original hanger and seated fittings. It adds finishing geometry and texture fields without rerunning the cloth solve. The intended age remains 1000 years.

**Armhole and shoulder.** Pass nine's short edge fringe did not supply an actual fabric connection across the opening. Pass ten extrudes connected allowance from the existing armhole boundaries, with 125 added edge vertices and measured widths of 1.252 to 9.812 mm. Three curved surviving yarns are placed on the visible wool before fringe placement. Building them afterwards let the fringe card planes occupy their attachment space. Their exported endpoint vertices are at most 1.238 mm from the final wool surface. The armhole median clearance is 32.940 mm, against the 25 mm minimum and intended 25 to 35 mm range; its 90th percentile is 39.270 mm and maximum 41.836 mm.

The shoulder boundary is refined at 1.8 mm spacing, with irregular losses up to 8 mm and an outward roll up to 4.5 mm. The stronger experimental opacity erosion produced fragmented dark contours, so the final candidate keeps pass nine's monotone 0.15 to 2.85 mm lip erosion. Initial gap probes hit the lit studio floor 3.10 to 3.97 m behind the garment. The final rear-light-disabled control still shows the bright aperture. No light or floor change conceals it. Despite the connected geometry, the image-comparer still sees an oversized bright tangle, sharp shoulder fibres and an insufficiently convincing sleeve connection.

**Hem, body and dust.** The existing curved hem has deeper irregular scallops. A world-height taper and protected centre keep the new hem and bagging fields away from the placket support; earlier pass-ten attempts introduced crossings there. Sparse fold-aligned wear adds seven isolated losses, faded thinning fields and bagging up to 3.5 mm, without biological clusters. The through-wear raster accounts for 135.877 square millimetres of additional lost wool in G29. The saved 4096-square thinning image retains a Blender user so it survives checkpoint reload.

The original mound topology is retained because reducing it introduced a self-crossing. Its albedo is now linear 0.34/0.31/0.26, and loose fibres have an independent pale 0.39/0.35/0.29 material instead of reusing navy wool. Fallen strips are slightly lighter. The dust-disabled control confirms a visible pale contribution, but the reviewer still sees a low, nearly flat patch with dark angular scraps rather than the requested soft heap. Body wear also remains too smooth overall, with conspicuous dark slits. Passing geometry measurements do not establish those visual requirements.

All 19 numeric gates are measured. G3 includes 12 over-limit runs among 38 traced runs. G4 is ordered hero shoulder, hero armhole, close shoulder, close armhole; the hero shoulder still lacks two measurable lips. Six of ten qualifying G6 contours fall below 1.15.

| Gate | Measured value | Threshold | Result |
| --- | --- | --- | --- |
| G1 | Visible sharp adjacency 1.927693% | ≤6% | Pass |
| G2 | Normal-jump pixels 0.072177% | ≤2% | Pass |
| G3 | Longest visible lip run 27.459060 px | ≤12 px | Fail |
| G4 | Width CV absent / 0.784572 / 0.690266 / 0.779957 | ≥0.35, measurable in every required view | Fail |
| G5 | Lip length lifted over 3 mm: 32.031271% | ≥30% | Pass |
| G6 | Contour dimensions 1.003139 to 1.333767; six failures | 1.15 to 1.40 on each qualifying contour | Fail |
| G20 | Sharp adjacency near hanger 3.315022% | ≤10% | Pass |
| G21 | Hanger exposure outside split hull 0 pixels | 0 | Pass |
| G22 | Maximum sleeve depth/width 0.429021 | ≤0.45 | Pass |
| G23 | Retained arc 36.004298%; released fringe 78.622307% | ≥35%; ≥70% | Pass |
| G24 | Chest width/unaged 1.014395 | 0.92 to 1.08 | Pass |
| G25 | Open-hem fringe coverage 86.018800% | ≥70% | Pass |
| G26 | Hem-height autocorrelation peak 0 | <0.30 at 20 to 120 mm lags | Pass |
| G27 | Heap height 26.876078 mm | 15 to 35 mm | Pass |
| G28 | Fallen cloth pieces 3 | ≥2 | Pass |
| G29 | Mound 95.259745 cm³; lost wool 6.341975 cm³; inferred packing 6.657560% | Volume ratio 0.5 to 2 at packing 5% to 15% | Pass |
| G30 | Changed SAT crossings 0; original hanger's 28 unchanged; hanger geometry exact | 0 changed crossings; exact hanger baseline | Pass |
| G31 | 20,594 triangles / 13,768 unaged = 1.495787 times unaged | ≤20,652 and ≤1.5 times unaged | Pass |
| G32 | Worst boundary bound 0.623240 mm | ≤1.5 mm | Pass |

The independent attachment audit passes every base within 2 mm. Maximum shoulder-board base distances remain 1.299524 and 1.421234 mm; the largest other attachment distance is 1.800060 mm at the medal. G32 compares the final game sheet with the authored pass-nine sheet after pass-ten finishing and before its further reduction, not with an independently deformed obsolete dense checkpoint. That reference has 11,279 triangles, reduced to 10,199 before thickness. The body's boundary bound is 0.125 mm; an unchanged fallen strip sets the overall 0.623240 mm maximum.

A fresh image-comparer review scores this candidate 6/10 against 5/10 for the reference in that comparison. It prefers the more readable shoulder and hem damage, but identifies the bright tangled armhole, spiky fibres, graphic torso slits and under-described dust as remaining defects. Its report is `tmp/age/tunic10/curled-image-review.md`. These scores are that review's judgments, not a recalibration of earlier ratings.

The requested sheets are `tmp/age/tunic10/tunic-before-after.png`, `tunic-turntable.png` and `tunic-closeup.png`. Detailed captures and calibration are under `curled-images/`; controls are under `controls/`. All nine camera records retain tunic nine's camera parameters, including the 0.5 m close view. External GLB bounds confirm Y-up height 950.012 mm and depth 180.090 mm. Gates, SAT contacts, seating and repeat-export results are in `curled/gates.json`, `collisions.json`, `attachment-audit.json` and `repeat.json`. Repeat export is byte-identical.

Thirteen focused script checks pass, covering wear fields, metrics, fringe, sampling, rims, connected allowance/shoulder geometry, surviving yarns, the saved candidate and 3,072 retained-binding opacity samples. The complete numeric acceptance command exits 1 because the three lip gates fail. No numbered threshold or collision check was relaxed. Rebuild with `polish_pass10.py -- --base tmp/age/tunic9/binding --out tmp/age/tunic10/curled`, then `finish_aging.py` with that output, `render_aging.py`, the shared composer and exported collision audit, `audit_attachments.py` and `measure_aging.py`. The recorded scratch driver is `tmp/age/tunic10/final-run.sh`.

### Tunic9: 16 of 19 gates pass, not shipped

The latest scratch candidate is `tmp/age/tunic9/binding/candidate.glb`. G3, G4 and G6 still fail. The attachment seating audit now passes, but the candidate has not replaced `assets/props/quarters/dress_uniform_aged.glb` or its textures. This pass starts from the settled tunic8 checkpoint, without rerunning or replacing its solve. The armhole opening intentionally connects to the exterior. By the gate author's decision, G3, G4 and G6 now trace each visible tear lip as an open polyline in both the hero and close cameras, regardless of whether the gap is enclosed. G3 still limits straight runs to 12 px; G4 still requires width CV of at least 0.35 along each gap; G6 still requires dimension 1.15 to 1.40 on lip contours at least 64 px long. Endpoints are not joined by an artificial closing edge. Cloth silhouettes are selected near projected physical tear lips after alpha testing, so an unrelated garment outline is not a tear.

The tunic8 cards-only controls are under `tmp/age/tunic9/diagnosis/`. The original exported fringe has linked alpha, two-sided rendering and a non-colour normal map. Disconnecting that normal map leaves the dark strands. Its median RGB bytes represent sRGB 0.067/0.075/0.094, far darker in linear light than the wool's 0.025/0.043/0.080 albedo. A fixed-linear-colour control lightens those same cards without changing their geometry or alpha. The image-comparer confirms the spikes in the isolated original cards and their persistence with the rim hidden. It also identifies a residual narrow seam at the collar/shoulder junction; the material control alone does not resolve the full shoulder defect.

**Fringe and dark shoulder marks.** The replacement atlas converts its slightly lighter linear colour, 0.033/0.054/0.095, to sRGB before writing. A separate ROUND node discarded fractional strand coverage. Fringe now links fractional texture alpha directly and exports as two-sided glTF BLEND. Normal strength and specular response are reduced. Final isolated cards and full controls are in `tmp/age/tunic9/binding-card-controls/`.

The remaining dark triangle had a different source. Camera-ray probes hit the rear wool ply and cut-edge material, rather than fringe cards. The opacity pass eroded intact collar-side binding and could leave isolated opaque specks over the dark inner ply. Retained binding is now opaque, fringe classification uses the actual release group, and lip erosion is monotone inward from each boundary station. The focused regression checks 3,072 collar-side shoulder samples in the final opacity texture while retaining losses on released lips. These checks establish the material and mask repairs, not visual acceptance of every dark mark. Final controls isolate the residual assembled-edge problem: in the fixed shoulder patch, 740 pixels have luminance below 0.24; hiding fringe increases that to 1,235, removing sheet AO leaves 725, and making the sheet opaque reduces it to 166. Ray samples identify wool, cut-edge and fitting surfaces rather than cards. Opacity revealing the dark inner surface remains the main source of the assembled dark edge; the successful isolated-card material repair does not solve it. The controls are in `tmp/age/tunic9/binding-sheet-controls/`.

**Shoulder boards.** Coarse facing triangles bridged wool creases, and subsequent whole-fitting clearance lifted the board away. Each facing now has a finer paired grid. Base/top columns descend together toward the wool only when strict self/body SAT remains clear. Finishing no longer lifts these already-seated boards again. Maximum exported base distances fall from tunic8's 2.417948/3.124559 mm to 1.299524/1.421234 mm, below 2 mm. Column thickness changes by less than 0.000002 mm. Board self/body crossings and the complete G30 changed-part count remain zero. Every other attachment base also passes its independent 2 mm audit.

**Sleeve and broad cloth.** The pressed sleeve presented its thin edge to rear/side cameras. An 8-degree row-centred twist turns its face without changing the upper 8% of its pattern length or the settled cap opening. The armhole retains its 33.3266 mm median clearance. The hero-camera depth/width maximum is 0.419127, below 0.45; its three section ratios are 0.302977, 0.406206 and 0.419127. Broad fabric lacked small drape variation. Normal displacement below the fittings adds at most 1.7991 mm of fold variation, retaining G1 and G24. Both are finishing deformations of tunic8, not a newly settled simulation.

**Hem.** Broad cornered cutouts came from the retained cut geometry. Six boundary-curvature steps, diffused through the backing, round those corners with at most 7.9347 mm motion. The alpha bake had a separate sampling defect: a 2048 opacity image was packed at the smaller AO texture's resolution. Wool packing now preserves the opacity image's own dimensions, and this candidate uses 4096 square opacity. At the hem, physical texel size is 0.3800 mm median, 0.5026 mm at the 95th percentile and 0.5509 mm maximum. Boundary-station erosion removes inward pinholes; grain-channel widths vary instead of repeating one straight width. The G3/G6 failures below show that the resulting visible lips still have overly straight or insufficiently complex sections.

**Debris.** The strips were too coarsely reduced for their folded forms; they now have curved arclength spines, transverse crumples and individual 400-triangle reduction targets. The mound's Gaussian height never reached zero at its rectangular grid border. The shared mesher's positive isovalue also thickened zero-height columns into a floor film. A tunic-local compact, irregular support now clips the entire SDF volume as well as its height. No shared module was changed. The dense deposit is faired before reduction and normal baking; surface fibres lie mostly along the mound rather than standing as spikes. The final mound is 26.8761 mm high, has 6.1583% inferred packing and retains three fallen cloth pieces. Those geometry checks do not establish a soft visual read.

All 19 gate measurements below come from `tmp/age/tunic9/binding/gates.json`. That file retains every individual lip run and per-camera result. Percentages are fractions converted to percent; millimetres and cubic centimetres are identified explicitly. Attachment pixels are masked separately, so a board silhouette cannot supply a missing lip. An unmeasurable gap remains a failure.

| Gate | Measured | Requirement | Result |
| --- | --- | --- | --- |
| G1 | 1.759645% visible sharp adjacency | At most 6% | Pass |
| G2 | 0.070750% normal-jump pixels | At most 2% | Pass |
| G3 | 29 open runs; 8 exceed the limit; maximum 66.037868 px | At most 12 px per visible lip run | Fail |
| G4 | Hero shoulder unmeasurable; hero armhole 0.586345; close shoulder/armhole 0.767818/0.625096 | At least 0.35 along every measurable visible gap; no missing result accepted | Fail |
| G5 | 55.642448% lifted lip length | At least 30% lifted over 3 mm | Pass |
| G6 | 0.924943, 1.041407, 1.129874, 1.310074, 1.043452, 1.347519, 1.124900, 1.229351 | Dimension 1.15 to 1.40 on every visible lip contour at least 64 px long | Fail |
| G20 | 2.869267% near-hanger sharp adjacency | At most 10% | Pass |
| G21 | 0 outside-split hanger pixels | Zero | Pass |
| G22 | 0.419127 maximum hero-camera depth/width | At most 0.45 | Pass |
| G23 | 36.004298% retained arc; 89.662777% released-edge fringe | At least 35%; at least 70% | Pass |
| G24 | 99.852254% chest width | 92% to 108% | Pass |
| G25 | 85.633583% open-hem fringe | At least 70% | Pass |
| G26 | 0.0 hem autocorrelation peak | Below 0.30 at 20 to 120 mm lags | Pass |
| G27 | 26.876078 mm mound height | 15 to 35 mm | Pass |
| G28 | 3 fallen cloth pieces | At least 2 | Pass |
| G29 | 95.259745 cm³ mound; 5.866407 cm³ lost wool; 6.158327% inferred packing | Factor 0.5 to 2 of volume at 5% to 15% packing | Pass |
| G30 | 0 changed crossings; exact hanger geometry and 28/28 baseline contacts | Zero changed/new-part SAT crossings | Pass |
| G31 | 20,616 / 13,768 triangles, ratio 1.497385 | At most 20,652 triangles, ratio 1.5 | Pass |
| G32 | 0.623240 mm boundary Hausdorff | At most 1.5 mm | Pass |

The hero shoulder exposes only one measurable lip, so G4 is not silently passed. G3 maxima for hero shoulder/armhole are 19.209373/13.656500 px; close shoulder/armhole maxima are 38.052595/66.037868 px. Five of the eight G6 contours are below 1.15. This gate change removes the enclosed-contour requirement but does not make the candidate pass.

The final required sheets are `tmp/age/tunic9/tunic-before-after.png`, `tunic-turntable.png` and `tunic-closeup.png`, copied from the binding candidate's fresh renders. All nine recorded cameras match tunic8 in distance, lens, position, aim, projection and resolution. The close camera remains 0.5 m away. Rear/side full-resolution captures are in `tmp/age/tunic9/binding-images/`. Saved-blend re-export is byte-identical. Independent trimesh bounds confirm the exported GLB is upright with its 0.9500 m height along glTF +Y.

The image-comparer inspected the final sheets, full-resolution rear/side views, debris view and isolated cards. It accepts the curved hem losses and subtle broad-cloth folds, and sees softer, slightly lighter isolated fringe. It still rejects assembled shoulder spikes and the small dark triangle. There is no obvious broad bright board gap, but a hard dark contact seam remains. The sleeve presents a face yet reads as a rigid strip, and the debris still looks angular rather than soft. These visual failures prevent delivery independently of the three gate failures. The complete assessment is `tmp/age/tunic9/binding-image-review.md`; visual success is not claimed for the material, seating or mound checks alone.

All 44 local tunic regression scripts pass in the final run. This includes five open-lip metric unit cases, three diagnostic-label cases, independent-opacity and linear-fringe controls, monotone erosion and retained-binding checks, the compact mound footprint, paired board seating and the 3,072-sample shoulder regression. The complete run is `tmp/age/tunic9/tests-final.log`, with per-script logs in `final-tests/`. These passing tests do not override the failed asset gates or visual assessment.

### Tunic8: 16 of 19 gates pass, not shipped

The candidate and checkpoints stay under `tmp/age/tunic8/final/`. G3, G4 and G6 fail, so the shipped tunic and textures are unchanged. This pass retains the source-grid rest carrier, attachment frames and curled fallen strips. No shared aging module was edited.

The source retained an upper-back arc that held the sleeve at the shoulder. Its permanent holds are on the opposite shoulder. The armhole split now releases the upper cap and retains the low underarm bridge. The pressed rest lets free cap material fall 60 mm and move outward 25 mm, fading over 100 mm of geodesic distance from the retained stitches. An intermediate vertical-only drop produced a median opening of 16.430 mm, below the required 25 mm; lowering the cap alone left its edge beside the body outline. The physical opening audit uses the median continuous lip clearance, so a single wide sample cannot pass it. The isolated capsule control implicates coupled cap/body loading in G22; it does not isolate the contribution of each new setting.

The dark shoulder triangles had several causes. Independent per-triangle attachment frames folded the board facings into themselves and through the wool. Coherent board poses followed by paired normal-ray columns remove tangential point snapping while allowing the sewn boards to bend. The released board slips 20 mm down the front ply. The retained board keeps its source frame, seats 10 mm inward and bends across a 9.5 mm transverse radius. A separate rim defect assumed Solidify appended one copy per original vertex. Rim-only Solidify copies boundary vertices only; a preserved source-ID attribute now identifies the correct base for compression. A finite 0.1 mm minimum keeps unresolved overpacking detectable by SAT. The rim also inherited a tangent-space normal map despite its collapsed UVs. Its material now uses geometric normals while retaining alpha; the broad wool sheet keeps its normal map. The normal-input regression fails before this change and passes afterward.

The regular hem came from three horizontal cuts at the same 38 mm pattern height, with vertical ends. Unequal scalloped runs now use varying 12 to 49 mm pattern heights and sloped end cuts. The mound had enough mass but spread it over too broad a footprint. A narrower smooth deposition envelope concentrates the same lost wool into a taller central mound. The three fallen strips retain their cloth solve and curl. The separate eight-triangle dust backing card was a flat decal and is removed. These changes pass the geometric hem and mound gates but do not establish their visual success.

Mass, springs, pin stiffness and material damping are co-scaled by 0.05; air damping stays at 10. The settled 200 mm swatch control differs by 0.0371 mm against a 3 mm limit. The coupled garment uses 2 mm self/object contacts, quality 30, and a 150-frame temporary shoulder-pin release. Persistent motion is checked before freezing. This addresses the underdamped motion behind the lumpy torso folds. The image-comparer describes shallow longitudinal folds and still rejects the broad fabric as too smooth and clean to convey aged wool.

Post-reduction push-out measures actual triangle crossings against the hanger, collar and sewn fittings. Medal metal is seated rigidly; its ribbon follows paired flexible columns over both wool and ribbon bar. The final seating runs after the wool rim is built. The retained neckline hold now reaches x = -0.085 m rather than stopping at -0.100 m. A ray probe located two intermediate G21 pixels at x about -0.097 m, beside the unheld neckline. Extending the hold shifted the two pixels but did not eliminate them. At their final positions, geometry intercepted both rays ahead of the wire, but the exported wool alpha was zero. The lip-opacity pass had also perforated the reinforced neckline. Keeping that sewn binding opaque restores G21 to zero; a regression fails on both texels before the fix and passes afterward. The camera and zero-pixel threshold are unchanged.

The final dense solve settles at frame 600 with zero strict self contacts, zero exclusions and 0.160899 mm motion over its last five frames. The exported armhole has 33.3266 mm median clearance and 46.0313 mm maximum clearance, against a 25 mm median minimum. This opening does not supply an enclosed contour: all 108 projected mid-gap samples land in exterior-connected background in the close-camera label mask. The only enclosed alpha openings have extents of 26, 26 and 17 px. None reaches G6's existing 64 px minimum. G3 and G4 also reject two of those small openings. Their thresholds remain unchanged.

| Gate | Measured | Requirement | Result |
| --- | --- | --- | --- |
| G1 | 1.752678% visible sharp adjacency | At most 6% | Pass |
| G2 | 0.154702% normal-jump pixels | At most 2% | Pass |
| G3 | 14.0000, 15.1327, 10.5119 px straight runs | At most 12 px each | Fail |
| G4 | 0.335645, 0.255459, 0.435631 width CV | At least 0.35 each | Fail |
| G5 | 55.642448% lifted lip length | At least 30% lifted over 3 mm | Pass |
| G6 | No closed contour at least 64 px across | Dimension 1.15 to 1.40 on a resolved contour | Fail |
| G20 | 2.741058% near-hanger sharp adjacency | At most 10% | Pass |
| G21 | 0 outside-split hanger pixels | Zero | Pass |
| G22 | 0.169362 maximum depth/width; sections 0.169362, 0.142632, 0.121686 | At most 0.45 | Pass |
| G23 | 36.004298% retained arc; 89.662785% released-edge fringe | At least 35%; at least 70% | Pass |
| G24 | 99.852815% chest width | 92% to 108% | Pass |
| G25 | 84.951440% open-hem fringe | At least 70% | Pass |
| G26 | 0.0 hem autocorrelation peak | Below 0.30 at 20 to 120 mm lags | Pass |
| G27 | 32.961250 mm mound height | 15 to 35 mm | Pass |
| G28 | 3 fallen cloth pieces | At least 2 | Pass |
| G29 | 115.465441 cm³ mound; 5.866407 cm³ lost wool; 5.080660% inferred packing | Factor 0.5 to 2 of volume at 5% to 15% packing | Pass |
| G30 | 0 changed crossings; exact hanger geometry and 28/28 baseline contacts | Zero changed/new-part SAT crossings | Pass |
| G31 | 16,889 / 13,768 triangles, ratio 1.226685 | At most 20,652 triangles, ratio 1.5 | Pass |
| G32 | 0.623974 mm boundary Hausdorff | At most 1.5 mm | Pass |

The medal metal and ribbon bases seat within 1.184369 and 1.802257 mm, respectively, against 2 mm. The independent attachment audit still rejects board base gaps of 2.417948 and 3.124559 mm. Board self/body and collar/body SAT crossings are zero; proximity and crossing tests measure different defects. Placket, buttons, ribbon bar and collar stars pass their 2 mm base-distance checks. Saved-blend re-export is byte-identical. All 35 original local test scripts pass, as do the added retained-neckline, opacity and rim-normal regressions, for 38 passing scripts. The rim-thickness, opposing-rim and rim-normal tests also pass after the final material change. Scratch logs remain in `tmp/age/tunic8/`.

The image-comparer inspected all six tunic7/tunic8 full-resolution captures. It confirms a more legible shoulder opening and a sleeve hanging away, but judges that sleeve too detached and straight. It rejects the noisy shoulder edge, block-like hem losses, smooth broad fabric and angular debris that still fails to read as a soft mound. It also reports a flat ground patch despite removal of the separate dust card; the remaining ground appearance is unresolved. Those observations prevent visual acceptance independently of G3, G4 and G6. The assessment is in `tmp/age/tunic8/image-review-final.log`.

The final images are `tmp/age/tunic8/tunic-before-after.png`, `tunic-turntable.png` and `tunic-closeup.png`. Their camera distance, lens, position, aim, projection and resolution match tunic7. The close camera remains 0.5 m away. Complete measurements are in `tmp/age/tunic8/final/gates.json`, `dense-control.json` and `attachment-audit.json`. The scratch GLB is `tmp/age/tunic8/final/candidate.glb`; it is rejected for delivery.

### Tunic7 continuation: not shipped

The capsule candidate passes 14 of 19 gates and has not replaced the shipped tunic. Its repaired source-grid carrier uses no contact exclusions. The dense control settles at frame 875 with one strict self contact and 0.6629 mm final-five-frame motion, meeting the fewer-than-50 / under-1-mm control. G1 is 2.8565% against 6%; G20 is 8.4250% against 10%; G24 preserves 97.6960% of chest width against 92% to 108%. The scratch GLB is `tmp/age/tunic7/capsule/candidate.glb`.

G22 now measures actual camera-ray depth divided by camera-visible width at quarter, half and three-quarter sleeve length, with the same 0.45 ceiling. The old 0.2708 principal-axis score accepted a sleeve whose camera ratio was 2.300. The 12 mm capsule rest passes its preparation controls but reopens in the coupled solve: corrected G22 is 0.629927 and fails. G3, G4 and G6 also fail because the alpha-aware diagnostic has no eligible enclosed opening contour. Empty contour lists are not accepted.

The standing collar follows its complete sewn curve and gets 2 mm layering along the actual support normal. Collar stars now bind to the collar rather than the torso; their base gaps are below 0.541 mm. The ribbon bar follows its sewn cloth, and the medal metal and cloth ribbon fit separately. The medal still exceeds the 2 mm base-gap limit at 2.901 mm. Vertex-only seating misses shoulder-board face crossings.

G21 now reports zero outside-split hanger pixels after fixing the stale projection matrix, without moving the wire or changing the camera. This does not approve the wire's appearance inside the split. G30 still fails with 832 changed contacts: 46 board self contacts, 5 body/rim self contacts, 65 collar/body contacts and 716 board/body contacts. Collar/hanger contacts are zero. The unchanged hanger exactly matches its geometry and 28-contact baseline.

The mound is 18.471 mm high with 5.213% inferred packing and three fallen strips; G27 to G29 pass. The export has 17,004 triangles against 20,652 allowed, boundary error is 0.63145 mm against 1.5 mm, and saved-blend re-export is byte-identical. Fresh comparison images are `tmp/age/tunic7/tunic-before-after.png`, `tunic-turntable.png` and `tunic-closeup.png`, using the tunic6 cameras and a 0.5 m close view. They have no new visual review. Full gate values and remaining causes are in `tools/blender/quarters/dress_uniform/README.md`. The shipped tunic and textures remain unchanged; age remains 1000 years.

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

## Batch 1

Rigid furniture follows the pilot's approved image, full Hunyuan3D-2mv guide and clean fitted-part route. `prompts/batch1.json` uses the pilot style and tail, with four seeds per prop. The selected hero and its generation provenance live in `sheets/<prop>/`. `tools/blender/quarters/<prop>/` contains the editable source, build and verification scripts, measurements and visual verdict. No texture maps or aging have been applied. A passing export is listed separately from visual acceptance.

Authoring uses Blender Z-up with front -Y; exports have +Y up and front +Z, with floor-centred asset roots. Dimensions are asset-local width, height and depth. Wall and desktop mounting heights belong to room placement. Wardrobe bounds refer to its closed carcass, excluding the parked leaf and mating hinge hardware; its open envelope is measured separately. The bed includes the separate layout headboard height and leaves its mattress platform exposed.

Verification reads the exported GLB through trimesh. It checks the layout envelope within 10 mm, floor origin, named parts and material classes, positive closed shells, winding, inward rays across all six faces of each shell, capture-matched orthographic hero-camera first hits, UV triangle overlap and consistent physical texel density, triangle budget and byte-identical export from the saved source. Visibility is weighted by projected surface area. Eight positive and negative controls cover closure, winding, UV overlap and occlusion, including an off-axis case that distinguishes orthographic from perspective visibility. The wardrobe adds five-face carcass rays, a 0.5-degree door sweep and unobstructed hanging-space rays. Each `verify.json` records measured values and limits.

| Prop | Picked seed | Hunyuan wall seconds | Triangles | Export checks | Fit rating | Status | Remaining visual defects |
| --- | --- | --- | --- | --- | --- | --- | --- |
| wardrobe | 203 | 187.81 | 11,016 | Pass | 4/10 | Not accepted | Top surface geometry mismatch: B has a protruding, light-colored roof panel that overhangs the carcass, whereas A has a flat, flush top in the same grey-green color.; Missing interior hardware: The bare-steel horizontal hanging rail visible in A is completely absent in B.; Color mismatch on top: The top panel in B is a distinct light color (white/pale grey) compared to the uniform grey-green of the rest of the object and the top of A.; Proportion/Silhouette deviation: The overhanging top in B alters the vertical proportions and silhouette compared to the clean, boxy profile of A. |
| bed | 216 | 177.60 | 3,512 | Pass | 9/10 | Accepted fit | In image B, the rivets on the headboard appear slightly irregular in spacing and size, potentially looking like noise rather than precise manufacturing details.; The 'folded panel edges' mentioned in the brief are not clearly distinct in B; the edges look flat rather than folded over. |
| desk_chair | 244 | 175.21 | 2,032 | Pass | 8/10 | Accepted fit | The small bare steel rivets on the corner plates in B are less distinct than in A, potentially due to lighting or resolution.; The fabric texture on the seat pad in B appears slightly smoother and less detailed than in A. |
| dining_table | 251 | 2004.80 | 3,728 | Pass | 8/10 | Accepted fit | None observed. |

### Rebuilding and checking

For example, run Blender with `--background --factory-startup --python-exit-code 1 --python tools/blender/quarters/wardrobe/build.py -- --assemble` to fit from `tmp/props/wardrobe/guide.glb`. Each prop's default guide has the same scratch path pattern. Omit `--assemble` to export directly from the committed `.blend` without scratch inputs. Supply `--output tmp/props/wardrobe/reexport.glb` for an independent second export, then run the local Hunyuan Python on `tools/blender/quarters/wardrobe/verify.py --reexport tmp/props/wardrobe/reexport.glb`. Run `tools/blender/quarters/wardrobe/test_verify.py` for the eight gate controls. Other props use the wardrobe's shared construction and verification helpers. `construction.json` records cameras, guide landmarks and part hierarchies.

### Bed platform

The selected seed 216 shows thin rails, an exposed continuous plate and open legs. The fit keeps the layout frame top at .55 m and the separate headboard at 1.10 m, with the platform at .50 to .52 m to preserve that selected silhouette. This differs from the generation prompt's .40 m platform request, which the selected image did not reproduce. The platform range is a recorded fitting choice, separate from the layout height check; build and verification read the same value from `construction.json`.

### Wardrobe placement

The single right-hinged door is parked at 100 degrees in the asset used for both room states. At room origin (7.675, 0, 3.6), with Y rotation -90 degrees, its barrel axis lies at room X/Z (7.335, 4.1). The barrel axis is 15 mm forward of the plan's closed-carcass hinge line. The parked leaf and hardware extend outside the closed footprint. The generated hero is left-hinged; the fitted assembly and hidden guide are reflected in X with face winding corrected and positive node scales retained. `hero.png` remains the original generated image and `fit-reference.png` is the reflected fitting target.

Not yet accepted: wardrobe, desk, console, dining_chair, bedside, view_screen, media_cabinet, lockers_over_bed.

Batch sheets: [`sheets/batch1-heroes.png`](sheets/batch1-heroes.png) and [`sheets/batch1-fitted-turntables.png`](sheets/batch1-fitted-turntables.png). Unaccepted fits are labelled as unfinished work. Per-prop `fit-review.json` retains the reviewer observations.
