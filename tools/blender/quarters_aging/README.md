# Quarters geometry aging

## Sofa pass 6: fitted six-cover collapse

`sofa_decay_joint.py` starts all six covers from `sofa/sofa-working.blend` in one dense cloth system. Each cover has its own seed. Inter-cover contact uses self-collision across all resolvable panels; the exclusion group contains split lips and triangles below Blender's 2 mm contact diameter, rather than whole top panels. The working system has 131,148 triangles. It contains no sofa-k geometry.

The filling contacts animate from the fitted volumes into the residue envelopes. A static, already-settled back residue intersects an inflated seat at frame one, so that final residue is not also added as a premature collider. Back-envelope roof heights are sampled from the actual residue, not a box. Exported covers and residues still require the complete G30 SAT test.

The fitted back's front bulge has downward normals as high as 650 mm. Removing every downward face deleted that front panel and stopped a grain walk after 109 mm. The back opening is now confined to faces below the 432 mm hem. The fitted-asset regressions in `test_sofa_decay_geometry.py` verify both the preserved front panel and a 160 mm grain walk across it.

`sofa_full_decay.py` retains the ordered fallback and the isolated seat controls. Keyed cloth is frozen from evaluated data because Blender cannot apply a cloth modifier to a mesh with shape keys. A folded-rest control found that Blender 4.5.11 transfers the rest coordinates only when a real level-1 Subdivision modifier precedes Cloth; an absent or level-0 modifier leaves the same control flat. The joint path reduces the carrier first, then subdivides it back to the working density. This second subdivision uses SIMPLE because the cover was already smoothed before cutting: another Catmull-Clark pass bends opposite split lips through each other at frame one. The initial surface and collider SAT checks pass with SIMPLE. Vertex mass uses the evaluated count. Per-cover vertex groups survive subdivision and restore the original pivots when the solved mesh is separated. A solved checkpoint is saved before reduction or baking, and `--finish <joint-solved.blend>` resumes that work without another simulation.

The pass-6 controls, checkpoints and captures stay under `tmp/age/pass6/`. Missing or failed gates block publication. The game asset is not replaced by a preview.

## Pass 5 calibration and contact policy

The 200 mm cantilever now compares 21 width-averaged material stations in 3D, rather than only the free-tip height. At 150 frames and 24 fps, the maximum dense/reference profile difference is 1.926 mm for upholstery and 4.409 mm for wool, against a 10 mm limit. Both fits retain total swatch mass. The requested 6 mm grid is actually 5.882 mm (34 cells); the reference is 22.222 mm (9 cells).

The upholstery reference is the selected fitted `seat-u` record: structural 500, shear 350, bending 10, vertex mass 0.015 kg. The wool reference uses structural 150, shear 80, vertex mass 0.15 kg and bending 0.25, as specified for the fitted throw in the #95 task. The older `throw-l` trial records a different bending experiment (0.7); it must not replace the task's 0.25 reference.

Spring-only sweeps failed to reproduce the upholstery drape. Damping had also been left constant while vertex mass fell with resolution, so the dense swatch was still moving toward its drape at frame 150. Joint spring/damping sweeps and independent mass, structural and bending perturbations found a mass-conserving fit. At the measured edge ratio 9/34, upholstery uses structural 160, shear 56 and bending 1.6; wool retains 150/80/0.25. Both use structural damping 1.44, bending damping 0.36 and air damping 0.6.

`cloth_stage.calibrated_config` records the empirical formula `q(h) = q_ref * (h / h_ref)^p`. Upholstery exponents are 0.857274446 for structural springs and 1.378776541 for shear and bending. Wool spring exponents are zero. Both fabrics use 1.595219466 for damping and air damping. Mass remains `mass_ref * N_ref / N_dense`. These coefficients describe this Blender version and fixture; they are not a general resolution law. The full sweeps, selected settings, profiles and exponents are under `pass5_calibration` in `sofa/cloth-trials.json`. Reproduce with `swatch_calibration.py`; raw exploratory runs stay under `tmp/age/pass5/`.

G30 now uses the owner's rigid-assembly decision below. `collision_policy.py` compares all six rigid self/pair counts against the unaged SAT report and separately totals every changed-part contact. The controls reject an added changed contact and either an increase or decrease in rigid baseline counts. Supply the unaged report explicitly with `sofa_gates.py --baseline-collisions`; `collision_export.py --baseline` can perform both inspections in one Blender run.

## Reusable soft-prop stages

## Pass 5 centre-seat initialization diagnosis

The old centre seat is already crumpled before decimation: the proxy-residue run has 52.727% dense sharp adjacencies and 60.985% after reduction. Decimation adds faceting but does not create the outlier at 1.138 m. The x=1.455 m and below-floor outliers belong to the unchanged sofa-k throw, not the centre seat.

The fitted cover begins with 1,765 SAT crossings against the already-aged centre back and 18 against the right back. The collapse envelope, residue, frame, feet and rivets have zero initial crossings. These mixed-time initial poses cause collision impulses before the foam has collapsed. Disabling self-collision or slowing the collider without clearing the initial contacts still leaves more than 40% dense sharp adjacencies.

`neighbour_colliders.py` starts seat simulation against the fitted back contacts. The maintained `--uncut-control --settings <self-collision-off.json>` regression at 360 frames, with collapse over 240 frames, measures 1.174% dense and 6.920% game sharp adjacencies, below the 8% limit. All vertices are within the frame bounds expanded by 0.15 m; G32 is 0.125 mm. The grain-tear production seat is a separate run. Fitted contacts do not certify final clearance against the comparison backs: G30 must still inspect those actual exported meshes.

The stage now also uses Blender's self-collision group as an exclusion, as its API specifies. The old group excluded boxing walls instead of enabling their contacts. Lip shrink now interpolates from zero outside the authored band to the configured lip shrink, rather than applying the same 4% shrink everywhere. These API fixes have direct Blender controls in `test_cloth_stage.py`.

The centre-seat bake is still experimental. `seat_render.py` imports the actual trial GLB and records alpha-tested close and hero face IDs, material IDs and normals. `seat_gates.py` measures visible G1 adjacencies, G2 normal discontinuities, G3's 1 px Douglas-Peucker contours, G4 medial-axis widths, G6 box counts, dense lip lift and crust roughness, exported shape, and final SAT contacts. G6 reports all opening dimensions; its acceptance fit uses contours at least 64 px across so the largest 32 px box has two samples. Smaller opacity openings remain reported. Missing measurements fail. `card_contacts.py` tests complete card triangles against the cloth, residue, comparison parts and earlier cards before accepting placement. The baked lip-control seat has zero cover/residue self-crossings and zero fringe contacts, but 616 contacts with neighbouring comparison cushions; it is rejected and has not replaced the game asset.

A translated aged-back contact is also rejected: its long hanging skirt reaches the seat before the back body, then the later body compresses the cloth against the deck. The staged control rises from 3.47% dense sharp adjacencies at frame 620 to 42.46% at frame 700. The `morph` experiment instead moves an unexported contact surface from the fitted back envelope to the exact comparison-back vertices during the foam collapse. This is an experiment, not an accepted replacement. Reducing boxing bending below the calibrated baseline produced further unstable runs, so it is not the default.

`densify.py` subdivides working surfaces and optionally refines projected bands. `tear_paths.py` snaps paths with Dijkstra and splits edges without removing area. `grain_paths.py` derives physical warp/weft directions from the pattern UV gradient. `cloth_stage.py` preserves explicit lip, welt and collision groups, scales per-vertex mass and records every frame's elapsed compute time.

`bake_down.py` protects a 6 mm **surface-distance** band around open boundaries, then reduces the interior. Euclidean distance incorrectly protected nearby folds in the centre-seat test, freezing reduction at 4,886 triangles. Blender decimates weighted vertices, so the `Keep` group must be inverted. A conservative sampled Hausdorff upper bound includes half the sampling interval; the control and centre-seat result are both 0.125 mm against a 1.5 mm limit. The stage creates `BakeUV` and selected-to-active Cycles tangent normal and AO maps, with 4 mm cage extrusion, 12 mm ray range and an 8 px margin.

`residue_sdf.py` builds a continuous powder base, noisy lumps, Voronoi cracks and tilted skin slabs, then extracts the dense surface with marching cubes. Overlapping lumps initially exceeded 80 mm; bounded lump heights and an unbroken powder base bring the current source below 35 mm. A 13 micrometre isovalue offset avoids grid-aligned zero-thickness contacts. The pore-rich source contains hundreds of small handles, which cannot survive a 700-triangle budget. A vertically filled height-field proxy carries the outer envelope into the collider/game mesh; the detailed pore surface remains the normal/AO bake source. The game mesh uses this filled proxy because collapse alone preserves the pore topology.

Full-size proxy testing also exposed a numeric topology defect that the small fixture missed. Marching cubes returned a closed indexed surface, but ordinary vertex merging identified distinct float32 grid-corner tips. The proxy now reconstructs a single-valued top, fills footprint holes, keeps at least two voxel cells of thickness, quantizes the field to 1 micrometre and places the isovalue halfway between quantized values. Field clipping bounds interpolation near grid corners; world-origin addition uses float64. The full-size regression remains closed with Euler characteristic 2 after vertex merging. Blender reduces the current proxy to 700 triangles with the same closed topology. This fixes topology, not appearance: its G7 planar fraction is still 33.233%, above 5%, dominated by underside facets. The revised dense source measures 1.655 mm plane-fit RMS against G8's 1.5 mm geometry requirement, but it has not yet been baked into an accepted seat.

The rear-approach contact experiment also fails. At frame 1200 its dense sharp-adjacency share is 39.594%, so it is retained as a failed simulation checkpoint under `tmp/age/pass5/seat-rear-contact/`. No experimental seat has replaced `assets/props/quarters/sofa_aged.glb`. The centre seat, remaining cushions, throw, crumb deposition and final shared atlas remain unfinished.

`fragment_library.py` takes connected skin pieces cut from 12 Voronoi cells in that same SDF. An 8 mm skin depth produced nine accepted templates at 24 triangles each; three thinner pieces remain rejected in the measurement record and are not exported. Deposition onto final sofa surfaces has not been implemented.

`fringe_cards.py` generates eight 1024 by 256 strand variants in numpy, their normal map and boundary cards. `opacity_bake.py` rasterizes 0.5 to 2 mm lip breakup into the game's `BakeUV`. `powder_cards.py` provides an irregular 48-triangle floor deposit with alpha coverage and a normal map from a 0.5 to 2 mm height field. The Blender control exports cloth opacity, fringe and powder as glTF `alphaMode: MASK`, and checks byte-identical re-export from a saved blend. This control does not certify card collision clearance or appearance.

The single-seat pilot currently uses a 4096-square normal/AO/opacity set for that seat and 2048-square residue maps. Packing all six covers into the shared 4096-square atlas remains unfinished. Coverage-preserving alpha mip generation and a Godot back-face-normal check also remain unfinished.

Run the Python tests with the Hunyuan environment. `test_bake_masks.py` requires Blender's `bpy`, so it cannot run under ordinary Python. Run `blender_soft_controls.py` in background Blender for integration coverage. Logs, fixtures, maps and experimental blends stay under `tmp/age/pass4/`.

## Sofa pass 4: dense simulation and bake-down

The pass-3 sofa trials `sofa-a` through `sofa-k`, including the failed `sofa-e`, are retained in `sofa/cloth-trials.json`. They are comparison inputs, not accepted pass-4 results. The fitted source and shipped GLB remain untouched until a new bake passes.

`sofa_gates.py` replaces sofa acceptance in both old gate entry points. Every G1 to G19 and G30 to G32 has an explicit threshold. Missing measurements are `not_measured` and fail; declaring a threshold does not implement its measurement. The current geometry checks measure G1, G7, G10, G12, G13, G14, G15, G16, G30 and G31. G1 currently reports all-sheet adjacency and remains failed until visible-face filtering is implemented. Render, dense-source and story checks remain to be implemented.

Gate changes and reasons:

- Remove crumb clustering >=70% and spacing CV >=0.50. These rewarded three compact piles. G10 instead requires Clark-Evans R 0.8 to 1.4 and no DBSCAN cluster above 20%; G11 requires a decaying spill with powder.
- Remove perimeter/sqrt(area) as a tear acceptance test and the 30 mm straight-run allowance. Slots passed both. G3 requires <=12 px/4.5 mm straight runs; G4 width CV >=0.35, G5 >=30% lifted lips and G6 contour dimension 1.15 to 1.40 prevent acceptance based on perimeter alone.
- Remove the 35% to 45% seat-height target and the pass-3 >=50% drop proxy. G14 requires 10% to 25% centre height above the deck. G12 limits surviving vertical wall area to 25%; G13 requires >=12 mm rounded-box residual.
- Remove the >=65% retained back-height target and hero-area proxy. G15 requires 40% to 65% retained height, G16 >=60% residue in the lowest third and G17 at least two 8 mm folds.
- G1 and G2 limit exported cloth faceting and normal-pass discontinuities. G7 limits large planar crust facets to 5%; G8 requires dense crust roughness plus a normal map.
- G9 checks cut-residue fragment templates rather than jittered icosahedra. G18 and G19 require the crest failure and nearby folded fall that explain the throw's pose.
- G30 requires zero SAT intersections for every pair involving any changed or new part, including covers, residues, throw, fringe, crumbs and powder against Frame, Feet and Rivets. The unchanged rigid set is reported separately, with every self and cross-part count required to equal the unaged export exactly. Its fitted overlapping steel primitives have 522 Frame self-crossings and 272 Frame/Rivets crossings. These joints are acceptable because this rigid assembly is never deformed. Removing an existing rigid crossing also fails the exact-baseline check. G31 retains the 29,325 triangle cap; G32 limits dense-to-game open-boundary error to 1.5 mm.

`Frame`, `Feet` and `Rivets` are all cloth colliders without changing their mesh. Neighbouring settled covers and the floor remain colliders. Fixed meshes and pivots are checked independently of the changed-part SAT test and the exact rigid baseline comparison.

The sofa and tunic represent 1000 years in dry, sealed, sterile, oxygenated air. Foam oxidises into crust and crumbs; wool splits at seams and hanging stress points. There is no biological or water damage. Locker materials and `bake_masks.py` belong to a separate pipeline.

Author in Blender's native Z-up frame, with front toward -Y, then export with `export_yup=True`. The GLBs have +Y up and front +Z. Existing object names, transforms and pivots are retained. Crust and cover share their cushion node; debris has separate named nodes.

## Cut-first physics
### Swatch measurements

`swatch_tests.py` runs 200 by 200 mm cantilevers for 150 frames at 24 fps. The first fixture uses 24 mm requested edges; dense fixtures use 6 mm and 3 mm. Vertex mass scales by reference vertex count divided by dense count. Upholstery uses 180 structural stiffness and 0.2 bending; wool uses 150 and 0.5. These are candidate settings, not accepted calibration against the fitted wool's 0.25 bending.

| Material | Edge | Uncut s/frame | Split s/frame | Uncut tip drop | Reference drop |
| --- | --- | --- | --- | --- | --- |
| Upholstery | 6 mm | 0.0605 | 0.0472 | 56 mm | 154 mm |
| Upholstery | 3 mm | 0.2504 | 0.2476 | 16 mm | 154 mm |
| Wool | 6 mm | 0.0528 | 0.0529 | 193 mm | 198 mm |
| Wool | 3 mm | 0.2260 | 0.2233 | 93 mm | 198 mm |

Raw frame costs, mass, slit gape and local lip-plane distances are recorded in `sofa/cloth-trials.json` under `pass4_swatches`. Drape differs by more than the 10 mm fixture tolerance in three cases. The settings are not production-ready; no calibration success is claimed. The first attempt stopped at an outdated bmesh lookup table after splitting. Refreshing that table fixed the tool error; its log remains under `tmp/age/pass4/swatches/run.log`.


`pass3.py` loads the unchanged fitted source. `stress_cut.py` releases shared armhole stitches and cuts stress-aligned rips before simulation. Its seeded boundary field has four octaves and a requested 6 mm amplitude, limited locally by edge length. It separates face fans that meet at a point, since a point contact is not a surviving stitch.

`tunic_pass3.py` removes about 60% of the near-side armhole stitches and weakens the wool. Pins are confined to a narrow top seam projected onto the hanger's actual upper wire surface, with 6 mm clearance. The shoulder mesh is refined to resolve the 7 mm wire. Blender cloth moves the body, sleeve and attached tear flaps under gravity. Neighbouring source cloth is lifted 12 mm before simulation to clear the wire. Both contact adjustments occur before gravity starts. There is no post-simulation garment pose deformation.

`sofa_pass3.py` derives shrunken closed crust from each unaged cushion. All six cut covers are simulated together with inter-cover self-collision, zero pressure and no pins. Their continuous collision envelopes start 8 mm inside the fitted filling surfaces and shrink linearly to the final crust over frames 1 to 480. Surface-normal offsets clear the concave back cushion returns, which a centre-based scale left crossing the cloth. The cover geometry is not narrowed or shifted to produce its aged pose. Underside loss clears starting cloth from the deck. The throw has no retained pins; reduced frame friction lets it slide. Its cut corner is simulated separately against the floor, furniture and settled main throw. The non-overlapping crumb clouds start at 0.50 to 0.62 m in the front spill zones and fall using Blender rigid bodies. Cushion surfaces are passive colliders; a solid floor volume prevents particles from tunnelling through a zero-thickness plane.

Some geometry is constructed rather than simulated. Crust shrinkage and Voronoi cracks are constructed. Fray fibres are added after cloth settling, with crossing thread tips removed. The fibre/dust heap is a seeded closed mound placed forward of the hem, toward the hero camera, above the unchanged 0.95 m floor drop. `detail_fit.py` clips visible simulated support triangles to the reinforced cloth details' footprints and lifts those patches 3 mm. It trims facets crossing underlying folds and opens point-only contacts by 0.2 mm. Brass follows rigid best fits, with the medal transformed as one rigid assembly. These details and the fibre heap have no separate physics simulation.

Fabric uses double-sided midsurfaces rather than sub-millimetre closed sections that can fold through themselves and spend the triangle budget on invisible back plies. Crust remains closed. Volume gates measure the closed crust against the unaged cushion envelope; an open cloth surface has no defined enclosed volume.

## Run and record a trial

Use the installed Blender with no additional packages:

```sh
nohup <blender> --background --factory-startup --python-exit-code 1 \
  --python tools/blender/quarters_aging/pass3.py -- \
  --prop sofa --trial <name> --frames 300 \
  > tmp/age/pass3/<name>.log 2>&1 &
```

Substitute `dress_uniform` for the tunic. All scratch outputs stay below `tmp/age/pass3/`. Every start, failure and completed bake is retained in the prop's `cloth-trials.json`, including actual simulator settings. Failed trials are not selected by their existence alone.

The tunic saves `simulated.blend` before fitting details. `--finish-tunic <checkpoint>` reuses that cloth bake to fit details without rerunning or changing the cloth. Its trial record identifies the reused simulation. The `--publish` option writes a completed bake to the prop source and game paths; use it only after inspecting the measured gates.

The normal prop exporters load baked sources: `sofa/build.py -- --aged --output <file.glb>` and `dress_uniform/build.py -- --aged --output <file.glb>`. Re-export is compared byte for byte with the delivered GLB.

## Export and camera gates

`collision_export.py` imports the actual GLB, builds triangle BVHs, then tests candidates with triangle-triangle SAT, including coplanar overlap. Only shared-vertex adjacency is omitted from self checks. No cloth, cushion or attachment is exempt from intersection tests. Sofa frame, feet and rivet joints remain reported as the unchanged rigid baseline; their counts must match the unaged export pair by pair, and their original geometry bytes are checked independently. The tunic's collision policy is unchanged. Cloth boundaries must be unbranched, without nonmanifold or degenerate edges; crust must be closed.

Run `pass3_gates.py` with the installed Hunyuan Python:

```sh
<python> tools/blender/quarters_aging/pass3_gates.py \
  --prop sofa --input <aged.glb> --reexport <repeat.glb> \
  --collisions <collisions.json> --out tmp/age/pass3/<name>/gates
```

Failures retain their values and exit nonzero. Displacement is measured on exported geometry: cuff and cap pattern islands, nearest unaged cloth surface distance, area-weighted throw centroid and central seat cover rays. Seat outlines are fitted against a rotated rectangle. Crumb checks use connected components, physical sizes, projected cluster distances and nearest-neighbour spacing variation.

The first-hit raster uses the same orthographic hero camera as the lit captures, at 1600 by 1422 pixels. It includes all prop parts and the studio floor. Lossless `before-hero-ids.png` and `after-hero-ids.png` encode integer labels in RGB; `hero-labels.json` maps those values to part/material names. The corresponding `*-hero-mask.png` files use a readable palette. Individual binary masks show the counted crust, crumbs, floor remnant, fibre heap, armhole gap and back silhouettes. Crust counts are restricted to projected internal tear boundaries, so exposed outside edges cannot satisfy the split-visibility gate.

The sofa framing remains 2.85 m wide. Both tunic states use 1.30 m rather than 1.15 m: the heap projects below the bottom of the 1.15 m frame. This widens the framing without changing the hero angle or target. Camera direction, placeholder colours and neutral lighting are unchanged. Armhole pixels are counted only within the unaged near-side cap's projected region, where cloth was the first hit before and background or a different part is the first hit afterward.

Pass 2's gates missed the visible defects because seam-cut length, heap dimensions, small shoulder displacement and projected shape measurements did not require a moved cuff, a rotated sleeve or visible first-hit debris. Its hand-shaped aged cloth also bypassed the simulator decision in `PLAN.md`.

## Captures and controls

`render.py -- --prop <sofa|dress_uniform> --out tmp/age/pass3` imports the exports for fixed-camera before/after pairs and four-view turntables. `--aged-input <trial.glb>` renders a trial without publishing it. `sofa-closeup.png` is 0.6 m from the split-seat target; `tunic-closeup.png` frames the shoulder and armhole from 0.5 m. Run `compose.py --out tmp/age/pass3` to make the comparison sheets, with unaged left and aged right.

`test_pass3.py` controls first-hit occlusion, area-weighted centroid, cuff/cap pattern selection and rectangle residuals. `test_pass2.py` retains continuous SAT and hem-variation controls; `test_verify.py` retains export and reference-surface controls. Geometry gates do not establish visual readiness. A separate image review is still needed.

`pass2.py`, the prop-specific `*_pass2.py` files, `build.py`, `cloth_decay.py` and `foam_collapse.py` retain earlier methods for their recorded trials. They do not substitute for the third-pass physics.
