from pathlib import Path
import json
O=Path(__file__).resolve().parent;P=O.parent
r=json.loads((O/'report.json').read_text());s=r['standing'];k=r['keyboard'];t=r['textures'];placement=json.loads((O/'keyboard-placement.json').read_text());gaps=[x['gap_mm'] for x in k['support_samples']]
a=json.loads((P/'assembly3/report.json').read_text());g=json.loads((P/'finish3/geometry-report.json').read_text());f=json.loads((P/'finish4/report.json').read_text());kb=json.loads((P/'kb3/report.json').read_text())
console_prompt=(P/'prompts/console-front.txt').read_text().strip();keyboard_prompt=(P/'kb3/prompt.txt').read_text().strip()
readme=f'''# Standing-height console

The deck centre is now 1.000000 m above the floor. Only the housing below the lip stretches; the deck, lip, head, display, sockets and keyboard move upward without scaling. All files in this delivery are under `{O}`. No tracked repository files were changed.

## Delivered files

`console.glb` contains exactly ConsoleBody, DisplayPlane, ScreenSocket and KeyboardSocket. `keyboard.glb` is byte-identical to `../assembly3/keyboard.glb`, in its unchanged local frame. `keyboard-placement.json` gives its transform relative to the console origin, in Blender and glTF coordinates. `console-with-keyboard.glb` contains both assets already assembled. `console-with-keyboard.blend` retains the render scene, embedded asset images and raised assembly.

The 2048 x 2048 maps are `console-albedo.png`, `console-normal.png`, `console-orm.png` and `console-ao.png`. ORM channels are occlusion, roughness, metallic. `front.png`, `three-quarter.png`, `side.png` and `operator.png` are 1600 x 900 Cycles renders, 64 samples, denoised. `albedo-z-cut.png` uses emission alone to inspect the boundary without lighting, AO or normal-map shading. `contact.png` includes these views and both requested references. `report.json` records measurements and checks.

## Measured standing adjustment

| Quantity | Metres unless noted |
| --- | ---: |
| Original deck centre | {s['deck_source_z_m']:.12f} |
| Lowest rigid front-lip underside | {s['lip_underside_lowest_m'][2]:.12f} |
| Source cut, 10 mm below underside | {s['z_cut_m']:.12f} |
| Rigid lift, delta | {s['delta_m']:.12f} |
| Lower vertical scale, s | {s['lower_body_vertical_scale']:.12f} |
| New cut height | {s['cut_new_z_m']:.12f} |
| New deck centre | {s['deck_new_z_m']:.12f} |
| New total height | {s['height_m']:.12f} |
| New screen centre z | {s['screen_centre_m'][2]:.12f} |
| Width | {s['dimensions_m'][0]:.12f} |
| Actual source and final depth | {s['dimensions_m'][1]:.12f} |

The measured lowest underside point is `{s['lip_underside_lowest_m']}`. The lip selection is recovered from assembly3's recorded rigid lip vertices, then restricted to downward-facing triangles at the front. This avoids mistaking the tapered lower housing for the lip underside. The exact test is in `geometry.py` and `geometry-report.json`. The source depth is 0.731263 m because assembly3 had already extended the deck. Its pre-extension body depth was approximately 0.70 m. X and Y are unchanged in this delivery.

With `delta = 1 - deck_z` and `s = (z_cut + delta) / z_cut`, the map is:

```text
z < z_cut:  z_new = z * s
z >= z_cut: z_new = z + delta
```

A shared mesh ring is inserted at the cut, interpolating existing UVs, so crossing triangles obey the continuous piecewise map. No volume is added separately. The floor remains at zero within mesh floating-point precision, the back remains at y=0, and the lower taper is retained. There are {s['final_vertices']} vertices and {s['final_triangles']} triangles, with no nonmanifold edges. All upper vertices and object matrices are checked against a rigid translation. Local keyboard and display vertices are unchanged.

Only {s['lower_reunwrapped_faces']} lower triangles receive Smart UV projection, 66 degrees, island margin 0.012, area weight 0.25. Their islands are packed into the available rectangle `{s['lower_uv_slot_pixels_2048']}` in the 2048 atlas. Untouched upper loop UVs remain exactly equal; split upper triangles retain their interpolated original mapping. The whole finish is rebaked in continuous object-space coordinates, including the fixed upper UVs, so the atlas boundary has no separate color rule. Grain and chip frequency are specified in metres rather than stretching the old bitmap by s.

## Concept, image editing and shape generation

The console concept is `../../room9/ref-console-design.png`; room context is `../../for-andrew-v8/03-west.png`. The extracted concept crop is `../inputs/ref-console-crop.png`. `../make_assets.py` removes the generated images' grey backgrounds using corner-colour distance >34, the largest connected component, hole filling, 2-pixel dilation and a 1-pixel Gaussian alpha edge; it also makes the initial sheets. All paths below are relative to this README unless absolute.

`../run-generations.sh` ran `/Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-flux2-edit` using FLUX.2-klein-4B, 4-bit, 8 steps, guidance 1.0. Console candidates used seeds 510, 511, 512 and 513 at 768 x 1024; the selected image is `../outputs/console-s510.png`. The console prompt in `../prompts/console-front.txt` is:

> {console_prompt}

Initial keyboard candidates used seeds 520 through 523 at 1024 x 768 and the prompt in `../prompts/keyboard-front.txt`, using `../../kbmodel/render-top.png` and `render-front.png`. They were superseded by the layout-preserving kb3 route below and are not the delivered keyboard.

`../run_meshes.py` ran `/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/generate.py`, model `weights/Hunyuan3D-2mv`, subfolder `hunyuan3d-dit-v2-mv`, float16, 30 steps, guidance 5.0, octree resolution 384, front RGBA image only. The chosen console is `../meshes/console-s510-rgba-410.glb`, shape seed 410. Other recorded console trials are shape seeds 411 and 412 on image seed 510, plus image seed 513 with shape seed 410. `../mesh-runs.json` contains all completed jobs. `../make_previews.py` and `../mesh-metrics.json` supplied selection comparisons.

## Console fit and earlier geometric adjustments

`../fit/build.py` removes loose components smaller than 1% of the largest component's area, applies the generated rotation and scale, fits width to 1.10 m, centres X, floors Z and aligns the rear to y=0. The scale reused by the final shell reconstruction is {g['uniform_scale']:.12f}; Y compression is {g['depth_y_factor']:.12f}. The initial 39000-triangle paint-fit branch is documented in `../fit/console-fit.json`, with paint normalisation in `../paint/prepare.py`, `fit-transform.json` and `assemble.py`. That earlier branch was superseded by the following shell reconstruction, rather than compounded onto it.

`../finish2/segment.py` measured the console silhouette and screen rectangle from image seed 510. It keeps the screen plane 8 mm inside the detected border. `../finish2/profile.py` established the cross-section remap used by `../finish3/geometry.py`. The latter starts again from the raw chosen Hunyuan mesh and the fitting prefix of `../fit/build.py`, not from the earlier decimated mesh. It removes the backdrop behind y=-0.030 m, extends the cut rear rim to y=0, and remaps each horizontal X cross-section to the reference silhouette. Maximum X displacement is {g['photo_fit_maximum_x_displacement_m']:.12f} m.

The clean shell uses 320 height rows and 65 front columns plus rear corners. Side outlines are line-fitted over source z intervals 0.025..0.465, 0.555..0.625 and 0.700..1.245 m, with 12 mm feathering. Row filtering weights are 0.2, 0.6, 0.2. Front ray depth stays between the measured front envelope and front+35 mm; outer 6% columns use the envelope. The rebuild uses 5 mm voxels, smoothing factor 0.5 for 5 iterations, then floors Z, restores 1.10 m width, flattens rear vertices with y>-12 mm to y=0 and decimates to 47998 triangles. Front/side silhouette IoU against the raw fitted reference is {g['silhouette_iou']['front']:.9f}/{g['silhouette_iou']['side']:.9f}. The script is `../finish3/geometry.py`; `refine_shell.py` authored its shell-reconstruction block.

`../finish3/transfer.py` restores Hunyuan paint from its normalised frame, transfers it to Smart UVs with a 4 mm cage and 8 mm ray range, and measures the actual sloped deck with 25 rays. It also establishes the sockets and uses the screen segmentation. `../finish3/make_bake.py`, `bake.py`, `edge_bake.py` and `edge_field.py` produced earlier wear variants. These were replaced by the assembly3 finish described below.

`../finish4/build.py` fills the recessed head-to-deck junction over source z=0.600..0.710 m and y<-0.43 m, using a reference front ray at z=0.680 m, slope 0.13, 6 mm smooth-min radius, 15 mm upper fade, 60 mm lateral fade and 45 mm depth fade. It moved {f['geometry_fill']['moved_vertices']} vertices, maximum outward fill {f['geometry_fill']['maximum_outward_fill_mm']:.9f} mm. It also removed a raised right-side scan strip for x>0.405 m, y=-0.682..-0.519 m, z=0.545..0.642 m toward plane `z=0.00025930161*x+0.4948926607*y+0.8868393254`, with 35 mm X fade and 12/8 mm Y fades. It adjusted {f['right_deck_smoothing']['vertices']} vertices, maximum {f['right_deck_smoothing']['max_removed_height_mm']:.9f} mm. `../assembly/build.py` then assembled this body with kb3 without changing its geometry.

`../assembly3/geometry.py` extends the front lip and front 25 mm deck band by exactly 35 mm along the sloped deck: displacement `{a['deformation']['full_displacement_m']}` m. The lip stays rigid. The lower front displacement decreases linearly from source z=0.478 to 0.278 m, with a local side transition. `../assembly3/tessellate.py` subdivides the affected large side triangles before deformation. `../assembly3/lip_profile.py` measures lip thickness and angle; `profile_comparison.py` renders the comparison. The result has 34120 vertices and 68236 triangles before this standing adjustment. Affected faces alone were re-unwrapped and repainted by `../assembly3/bake.py` and `textures.py`. Assembly2 was an alternate extension and is not in this source chain.

The assembly3 deck is plane `z={a['deck']['plane_z_equals_ax_plus_by_plus_c']}`, slope {a['deck']['slope_degrees']:.9f} degrees, useful depth {a['deck']['along_slope_depth_m']:.12f} m and useful width {a['deck']['usable_width_m']:.6f} m. Its 25-ray flatness residual is {a['deck']['flatness_peak_to_peak_mm']:.9f} mm. Standing height adds delta only to the plane intercept. `geometry.py` in this directory applies the final piecewise stretch stated above.

## Keyboard pipeline and placement

`../kb3/design.py` and `reference_geometry.py` obtain the 29-key layout from `../../kbmodel/render-top.png`. `../kb3/run_flux.py` crops it with 4% margin and generates FLUX candidates 530..533, with the same 4-bit, 8-step, guidance-1.0 configuration. The selected image is seed 531 at 1024 x 288, recorded in `../kb3/reference.json`. `../kb3/score_flux.py` matches all 29 components. Its prompt, `../kb3/prompt.txt`, is:

> {keyboard_prompt}

`../kb3/run_shapes.py` uses the same Hunyuan shape settings as the console, with seeds 410 and 411. `../kb3/run_staging.py`, `stage_shape.py` and `score_shapes.py` select seed 410. The raw mesh has {kb['shape_stage']['raw_triangles']} triangles. Front-surface PCA, rather than whole-body PCA, levels the key-facing surface; its exact raw-to-levelled matrix is recorded in `../kb3/mesh-410/stage.json`. X/Y use one uniform width scale to 0.8 m; Z is fitted to 0.055 m thickness; X/Y are centred and Z floored. Decimation produces 28998 triangles, silhouette IoU {kb['shape_stage']['silhouette_iou']:.12f}. Final unchanged local dimensions are `{kb['dimensions_m']}` m.

`../kb3/run_finishing.py` runs Hunyuan `paint.py` on the chosen raw paint mesh and `reference-rgba.png`, texture size 2048, resolution 512, paint seed 531. The paint log records 50 delight steps and 10 reference-pass steps. `../kb3/prepare.py` applies the stored leveling matrix, merges vertices within 1 micrometre, repairs winding, transfers generated paint to Smart UVs and reserves a projected key-top atlas. `../kb3/atlas.py` and `finish.py` darken the key tops, boots and frame to median sRGB `{kb['final_medians_srgb']}`. Legends use colour (150,146,128), maximum opacity 0.45 and 15% key margins. No keyboard geometry, UVs, textures or local GLB bytes are changed for standing height.

`../assembly3/placement.py` fits the actual underside plane `z={a['keyboard']['source_underside_plane_z_equals_ax_plus_by_plus_c']}`, correcting its {a['keyboard']['source_underside_axis_tilt_degrees']:.9f}-degree axis tilt. Uniform placement scale is {k['uniform_scale']:.12f}. The keyboard is 0.528022 m wide, placed 0.5 mm normally above the fitted deck, then slid {a['keyboard']['rearward_slide_mm']:.9f} mm rearward to prevent raised-key silhouette overhang. Standing height keeps its rotation and scale and adds delta to KeyboardBase Z.

Exact final placement:

```json
{json.dumps(placement,indent=2)}
```

Blender is right-handed Z-up, front -Y. glTF is right-handed Y-up: `(x,y,z)_Blender -> (x,z,-y)_glTF`. Blender quaternion order is w,x,y,z; glTF order is x,y,z,w. Apply the recorded transform to the standalone KeyboardBase relative to console origin.

## Finish recipe and rebake

The final finish is the assembly3 paint recipe, rebaked by `bake.py` and `textures.py` in this directory. Earlier console Hunyuan paint was used during look development and transfer, but its invocation did not retain a seed in the available records. Its log is `../finish3/paint.log`, with 50 delight steps, 10 reference-pass steps and 512 px conditioning; `paint.py` currently defaults its seed to 0, which is not proof of the historical invocation. Final console albedo uses the deterministic recipe below and does not read that historical paint atlas.

The concept's connected lit olive patches yield target median sRGB (117,125,80). Selection excludes the dark screen, brown surroundings, deep shadows and neutral highlights: G 102..174, G-R>=2, R/G>0.80, B/G 0.50..0.80, patches at least 12 pixels. Linear-space mottle is 11/m seed 713 with 20% range, plus 75/m seed 912 with 6% range. AO darkening is 18%, reduced to 12% at the protected contact junction. Paint is median-calibrated after grime, rust streaks and dust.

Convex edges with dihedral at least 8 degrees are sampled at 1 mm intervals. A 4 mm band is eligible for chips. Its noise field mixes 145/m seed 819 at weight 0.55, 53/m seed 931 at 0.30 and 9/m seed 491 at 0.15, with a 0.35 broad-peak boost. Thresholding targets 9% edge-band coverage. A protected junction uses y<-0.46 and source z=0.615..0.705 m, shifted by delta. Chip selector is 87/m seed 624, with 70% dark undercoat (48,49,37), 25% rust (96,62,44), 5% muted steel (104,103,87), modulated 20% by 190/m seed 94. Only steel chips are metallic. Paint roughness is approximately 0.68, undercoat 0.77, rust 0.84, steel 0.58. Principled specular IOR level is 0.10.

Five rust streaks begin at source (x,z) (-0.36,0.684), (-0.19,0.553), (0.025,0.683), (0.225,0.553), (0.375,0.688) m, with source lengths 0.23,0.17,0.31,0.21,0.26 m, Gaussian widths 4,2.5,3.2,4.5,2.8 mm and maximum blends 0.13,0.15,0.10,0.11,0.14. Their starts move up by delta and lengths multiply by s to reach down the extended body; transverse widths do not stretch. Small sinusoidal drift and broken falloff keep them irregular. Dust uses 17/m noise seed 2031, upward normal and sheltered AO, with maximum allowed blend 0.15 and desaturated, slightly lifted paint colour. Object-space grain is 1500/m, bump distance 0.14 mm, strength 0.10; chip recess bump distance is 0.18 mm, strength 0.20. Tangent normals are rebaked after UV changes.

Measured final paint median is `{t.get('baked_paint_median_srgb_255',t['resolved_paint_median_srgb_255'])}`; edge chip coverage is {t['edge_chip_coverage']*100:.6f}%. Undercoat/rust/steel fractions are {t['undercoat_fraction_of_chips']*100:.4f}/{t['rust_fraction_of_chips']*100:.4f}/{t['steel_fraction_of_chips']*100:.4f}%. Maximum dust blend is {t['dust']['maximum_blend']:.9f}. Rust-streak affected texels: {t['streak_affected_texels']}.

## Fit checks and seam inspection

`fit.py` reruns all nine underside rays using the unchanged local support points. Gaps are {min(gaps):.9f}..{max(gaps):.9f} mm. Body/keyboard BVH intersections: {k['intersections']}. Front vertical clearance is {k['front_vertical_clearance_mm']:.9f} mm; deck-frame front/rear clearances are {k['front_deck_clearance_mm']:.9f}/{k['rear_deck_clearance_mm']:.9f} mm; side clearance is {k['side_clearance_mm']:.9f} mm. Minimum key-top distance from the housing is {k['minimum_keytop_body_clearance_mm']:.9f} mm.

The operator eye is `{k['operator_eye_m']}` m, 1.65 m above floor and 0.55 m in front of the deck front edge. {k['visible_keytops']}/29 actual key-top centres are visible, meeting the 27/29 requirement. The screen-centre ray hits DisplayPlane first. Export node sets, local keyboard byte equality, placement transforms, manifoldness, winding, image embedding, map size and render size are checked in `verify_scene.py` and `validate.py`. `report.json` contains the seam's paired UV samples and colour-difference summary; `albedo-z-cut.png` is the rendered close-up. Inspection found no visible colour discontinuity at the cut. Across {r['seam']['sample_count']} paired samples, median per-channel differences are `{r['seam']['median_channel_difference_srgb_255']}` on the 0..255 scale, with 95th-percentile maximum-channel difference {r['seam']['p95_max_channel_difference_srgb_255']:.6f}. The near-side camera is at (3.5,-1.3,1.50) m and aims at housing mid-height so the rusty wall and steel floor are visible. `render_side.py` produced this staging correction; `build.py` includes the same camera for future builds.

## Reproduction and script paths

Run with Blender 4.5.11 at `/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender`, always `--background --factory-startup`. The external scientific Python is `/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python`. `setup.py` copies the assembly3 bake/finish logic and rusty-wall/steel-floor staging to local scripts. `run.py` executes `geometry.py`, `fit.py`, `bake.py`, `build.py`, `verify_scene.py`, `validate.py`, checking completion markers as well as return codes. `bake.py` calls `textures.py`. `build.py` calls `stage.py`, exports assets, saves the Blender file, renders four views, then renders the emission-only boundary close-up. `document.py` writes this README from the resulting measurements.

```sh
cd {O}
/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python setup.py
nohup /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python -u run.py > run.log 2>&1 < /dev/null &
# Poll with sleeps no longer than 90 seconds.
# After FINAL_COMPLETE:
/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python document.py
```

`probe.py` inspected initial bounds and underside rays. `lip_measure.py` explored underside connectivity; the final lip measurement is the rigid-lip test in `geometry.py`, rather than the exploratory component bounds. Neither probe changes the source file. Stage logs live beside their scripts.

## Limitations

The historical console Hunyuan paint invocation's seed cannot be recovered from its available log. Its generated paint was superseded by the deterministic final finish; the final asset build starts from the supplied assembly3 Blender file and is fully scripted here. No game integration or tracked-file replacement was requested or performed.
'''
(O/'README.md').write_text(readme)
r['seam']['visual_inspection']='No visible colour discontinuity at z_cut in the emission-only close-up.'
r['incomplete']=['Historical console Hunyuan paint seed was not recorded and could not be recovered; this atlas was superseded by the final deterministic finish.']
r['files']=['console.glb','keyboard.glb','keyboard-placement.json','console-with-keyboard.glb','console-with-keyboard.blend','console-albedo.png','console-ao.png','console-orm.png','console-normal.png','front.png','three-quarter.png','side.png','operator.png','albedo-z-cut.png','contact.png','README.md','report.json']
(O/'report.json').write_text(json.dumps(r,indent=2)+chr(10))
print('README_DONE')
