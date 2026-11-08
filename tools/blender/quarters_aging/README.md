# Quarters geometry aging

The aged sofa and tunic represent 1000 years in dry, sealed, sterile, oxygenated air. Foam oxidises into crust and crumbs; wool splits at seams and hanging stress points. There is no biological or water damage. Locker materials and `bake_masks.py` belong to a separate pipeline.

Author in Blender's native Z-up frame, with front toward -Y, then export with `export_yup=True`. The GLBs have +Y up and front +Z. Original object names, transforms and pivots are retained. Crust and cover share their cushion node; debris has separate named nodes.

## Second-pass construction

The selected bakes are sofa `pass2-o` and tunic `pass2-n`, recorded in each prop's `cloth-trials.json`. The editable aged sources and `verify-aged.json` live beside the unchanged fitted sources under `tools/blender/quarters/sofa/` and `tools/blender/quarters/dress_uniform/`.

`pass2.py` loads the fitted source and calls the prop-specific construction. `sofa_pass2.py` builds slack seat shells, bottom-heavy back sacks, actual cover openings, a continuous cap-to-floor throw and solid crumbs. The cover is measured independently of the reduced crust. `tunic_pass2.py` releases a contiguous armhole seam arc and deforms the existing sewn pattern, with asymmetric shoulder and waist slump. It refines and displaces tear edges, checks triangle orientation before accepting displacement, and keeps brass details attached. These are directly constructed gravity-shaped surfaces and constrained pattern deformations. They are not new cloth or rigid-body simulations.

`fabric_mesh.py` owns tear boundaries, attached frays and thin closed sections. Narrow fibres use the original surface normal and locally limited thickness. `section_contacts.py` removes impossible thread-tip extensions that cross the cloth before rebuilding the section. The tunic uses a double-sided, zero-thickness cloth midsurface with nine explicit boundary loops: neck, hem, two cuffs and five tears. No cloth or cushion parts are exempt from collision verification.

To construct a fresh trial, run the installed Blender with `--background --factory-startup --python-exit-code 1 --python tools/blender/quarters_aging/pass2.py -- --prop sofa --trial <name>`. Substitute `dress_uniform` for the tunic. Outputs go under `tmp/age/pass2/<name>/`. The `--publish` option also writes the aged source, construction JSON and game GLB. Seed and named source parts come from the existing `aging.json`; construction parameters are kept beside the prop-specific surface code.

To reproduce the delivered export without changing the geometry, use the normal prop exporter: `tools/blender/quarters/sofa/build.py -- --aged --output <file.glb>` or `tools/blender/quarters/dress_uniform/build.py -- --aged --output <file.glb>`. Both load the saved baked source. Byte-identical re-export is checked through these entry points.

Use the installed Blender and Hunyuan virtual environment's Python. No additional packages are needed. Run long jobs under `nohup`, with logs and scratch files below `tmp/age/pass2/`.

## Exported-geometry verification

Run Blender with `--python tools/blender/quarters_aging/collision_export.py -- --input <aged.glb> --report <collisions.json>`. This imports the actual export, builds a triangle BVH and checks candidate pairs with a continuous triangle-triangle separating-axis test, including coplanar overlap. Shared-vertex adjacency alone is omitted from self checks. Cloth versus furniture and cloth versus attachments remain included. Fixed frame and hanger joints are reported separately, and their geometry bytes must match the unaged asset.

Then run the installed Hunyuan Python with `tools/blender/quarters_aging/visible_gates.py --prop <sofa|dress_uniform> --input <aged.glb> --reexport <repeat.glb> --collisions <collisions.json> --report <gates.json>`. A failed gate saves its values and exits nonzero.

Sofa measurements include centre cover height above the deck, edge sag, top-height residual after plane removal, back-cushion first-hit coverage from the hero direction, actual opening boundaries, crust-plus-cover volume, solid crumb size and support gaps, and throw area below the cap. Crumb qualification requires at least 150 pieces from 2 to 15 mm within 250 mm of a split; at least 60% of those must rest within 2 mm of a surface. Additional spill pieces outside this qualifying set are reported rather than counted toward it.

Tunic measurements include tear-boundary irregularity, longest straight run within 1 mm, hem-notch variation, open armhole reference length, UV-matched shoulder drop, silhouette IoU and heap dimensions and placement. Both reports include topology, triangle budget, original pivots, fixed geometry bytes and byte-identical re-export. `test_pass2.py` provides positive and negative triangle-intersection and hem-variation controls; `test_verify.py` retains the export, silhouette and reference-surface controls.

Back coverage uses an orthographic first-hit depth raster from the same hero direction as the captures, with all other exported prop geometry included as occluders. Its control verifies that a nearer surface hides the target while a farther surface does not. This caught a right back sack that passed projected overlap but sat below the arm; retaining its empty upper fabric above the arm corrected the failure. Geometry gates do not establish whether the damage reads as old fabric. The designated image-comparer endpoint refused connections during this pass, so there is no visual sign-off.

## Captures

Use Blender with `--python tools/blender/quarters_aging/render.py -- --prop sofa --out tmp/age/pass2`, then repeat for `dress_uniform`. `--aged-input <file.glb>` renders an unpublished trial. Captures import the exported GLBs with identical before/after cameras, neutral world fill and four area lights. Placeholder colours are charcoal covers, dark brown crust, oatmeal throw and navy wool.

Run `compose.py --out tmp/age/pass2` with the Hunyuan Python to make `sofa-before-after.png`, `tunic-before-after.png` and their four-view turntables. Unaged is left and aged right. `sofa-closeup.png` uses a perspective camera 0.6 m from the split-seat target.

## Earlier simulation tools

`build.py`, `foam_collapse.py`, `cloth_decay.py` and `debris.py` retain the earlier simulation workflow and its parameter files for the recorded first-pass trials. They do not construct the selected second-pass geometry. Their `verify.py` uses sampled distances and finite edge crossings; use `collision_export.py` and `visible_gates.py` for the current intersection and viewer-facing requirements.
