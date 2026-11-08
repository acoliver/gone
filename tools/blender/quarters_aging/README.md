# Quarters geometry aging

## Sofa pass 4: dense simulation and bake-down

The pass-3 sofa trials `sofa-a` through `sofa-k`, including the failed `sofa-e`, are retained in `sofa/cloth-trials.json`. They are comparison inputs, not accepted pass-4 results. The fitted source and shipped GLB remain untouched until a new bake passes.

`sofa_gates.py` replaces sofa acceptance in both old gate entry points. Every G1 to G19 and G30 to G32 has an explicit threshold. Missing measurements are `not_measured` and fail; declaring a threshold does not implement its measurement. The current geometry checks measure G1, G7, G10, G12, G14, G15, G30 and G31. Render, dense-source and story checks remain to be implemented.

Gate changes and reasons:

- Remove crumb clustering >=70% and spacing CV >=0.50. These rewarded three compact piles. G10 instead requires Clark-Evans R 0.8 to 1.4 and no DBSCAN cluster above 20%; G11 requires a decaying spill with powder.
- Remove perimeter/sqrt(area) as a tear acceptance test and the 30 mm straight-run allowance. Slots passed both. G3 requires <=12 px/4.5 mm straight runs; G4 width CV >=0.35, G5 >=30% lifted lips and G6 contour dimension 1.15 to 1.40 prevent acceptance based on perimeter alone.
- Remove the 35% to 45% seat-height target and the pass-3 >=50% drop proxy. G14 requires 10% to 25% centre height above the deck. G12 limits surviving vertical wall area to 25%; G13 requires >=12 mm rounded-box residual.
- Remove the >=65% retained back-height target and hero-area proxy. G15 requires 40% to 65% retained height, G16 >=60% residue in the lowest third and G17 at least two 8 mm folds.
- G1 and G2 limit exported cloth faceting and normal-pass discontinuities. G7 limits large planar crust facets to 5%; G8 requires dense crust roughness plus a normal map.
- G9 checks cut-residue fragment templates rather than jittered icosahedra. G18 and G19 require the crest failure and nearby folded fall that explain the throw's pose.
- G30 includes every part, including fixed assemblies, Feet, rivets and fringe cards. Nothing is removed from collision totals. G31 retains the 29,325 triangle cap; G32 limits dense-to-game open-boundary error to 1.5 mm.

`Frame`, `Feet` and `Rivets` are all cloth colliders without changing their mesh. Neighbouring settled covers and the floor remain colliders. Fixed meshes and pivots are checked independently of the all-part SAT test.

The sofa and tunic represent 1000 years in dry, sealed, sterile, oxygenated air. Foam oxidises into crust and crumbs; wool splits at seams and hanging stress points. There is no biological or water damage. Locker materials and `bake_masks.py` belong to a separate pipeline.

Author in Blender's native Z-up frame, with front toward -Y, then export with `export_yup=True`. The GLBs have +Y up and front +Z. Existing object names, transforms and pivots are retained. Crust and cover share their cushion node; debris has separate named nodes.

## Cut-first physics

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

`collision_export.py` imports the actual GLB, builds triangle BVHs, then tests candidates with triangle-triangle SAT, including coplanar overlap. Only shared-vertex adjacency is omitted from self checks. No cloth, cushion or attachment is exempt from intersection tests. Fixed frame and hanger joints are reported separately, with their original geometry bytes checked independently. Cloth boundaries must be unbranched, without nonmanifold or degenerate edges; crust must be closed.

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
