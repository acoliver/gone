# Quarters geometry aging

These tools derive aged meshes from the baked unaged sources. Coordinates inside Blender are metres, Z up and front -Y. Export uses `export_yup=True`. The exported GLBs are Y up and front +Z. The original objects keep their transforms and names. Crust joins the corresponding cushion node. FoamDebris and FibreDust are separate nodes.

The age is 1000 years in dry, sealed, sterile, oxygenated air. Foam becomes oxidised crust and crumbs. Wool splits along folds and hanging stress lines. There is no biological damage or water damage. Material aging is a separate pipeline.

## Run

Use the installed Blender with `--background --factory-startup --python-exit-code 1 --python`. From the repository root, pass `tools/blender/quarters_aging/build.py -- --source tools/blender/quarters/sofa/sofa-working.blend --params tools/blender/quarters/sofa/aging.json --output tools/blender/quarters/sofa/sofa-aged`. For the tunic, use `dress_uniform/tunic-working.blend`, `dress_uniform/aging.json` and `dress_uniform/tunic-aged` instead.

The output argument names the baked source prefix. The parameter file's `asset` names the exported GLB. The build saves the applied mesh to `<prefix>.blend` and the simulation settings and measurements to `<prefix>.json`. It never reruns physics when re-exporting. Each prop's existing `build.py -- --aged --output <file.glb>` exports the baked aged source.

`foam_collapse.py`, `cloth_decay.py` and `debris.py` accept the same three arguments to run only their respective stages. Cloth decay also scatters debris. The source must contain the named parts in the parameter file. Cloth inputs use the paired-vertex layout of an applied Blender Solidify modifier, with the original pattern UVs retained. Other construction meshes are removed from the derived source, without changing the unaged file.

Long jobs run under `nohup`. Set `TMPDIR` to the repository's `tmp/age` directory. Logs and renders also go there. Do not run a long foreground simulation.

## Methods and parameters

`foam_collapse.py` extracts the cushion's main connected shell, compresses it and clips it into seeded Voronoi cells. Each cut is capped, so the crust plates are closed volumes. `height_ratio`, `back_depth_ratio` and `back_support_y_shift_m` control collapse and placement. Back pads use inverse height compensation for their depth reduction, keeping the same volume fraction. `core_reduction`, `voronoi_cells` and `crack_width_m` control the plate geometry. Simplification can remove the lowest vertices, so the reduced core is translated back onto its specified support before the cover settles.

The retained upper cover has pressure zero. Its rim stitches remain pinned, while the interior settles under gravity against the shrunken core's continuous contact envelope. The envelope bridges narrow cracks so the cover cannot tunnel through them. After mesh reduction, a measured clearance fit corrects the small chord errors introduced by simplification. The envelope is removed before saving. The trial record includes the largest correction. The exported crust still has actual gaps between plates. A final support fit raycasts the frame below each load-carrying crust and translates the baked cushion to the requested contact gap. This accounts for curved supports instead of using the frame's global maximum height.

`cloth_decay.py` opens the original baked fabric at its middle surface. Seeded, corrugated, elongated masks remove faces along the supplied stress and fold lines. `stress_slits_xz_m` gives each slit as centre X, centre Z, half width, half length and rotation in radians. `retained_seam_boxes_xz_m` and `retained_seam_boxes_xyz_m` preserve specified seam bridges. The latter distinguishes the retained back of a sleeve cap from its torn front. Protected detail patches retain their pins and original wool thickness. The remaining wool has lower stiffness and fewer pins. Its lower side panels contract by `lateral_shrink` before the gravity settle. Hanging wool is 45 percent of the nominal thickness. Fibres have a much thinner section than the wool and extend from narrow splits in the boundary before thickness is applied. Frays whose tips would enter a named collider are omitted.

`debris.py` takes three triangle shapes from the existing source mesh as fragment templates. It scatters closed flakes in separated cells and joins them into one node. `count`, `piece_size_m`, `radius_xy_m` and `heap_height_m` control the heap. For hanging garments, `drop_height_m` places both the heap and the simulation floor relative to the hook origin. The pilot uses 0.95 m.

## Verification and images

Run `verify.py` with the installed Hunyuan Python, which supplies trimesh, NumPy, SciPy and Pillow. Arguments are `--prop sofa` or `--prop dress_uniform`, `--reexport <file.glb>` and `--report <report.json>`. An optional `--input` measures an archived aged export. Failures are saved before the command exits with status 1. `test_verify.py` exercises positive and negative controls for area loss, silhouette, penetration and raw geometry bytes.

Tear area is measured as missing UV coverage, weighted by the unaged exported surface area. This avoids mistaking gravity stretching for lost fabric. Cushion volume includes the closed crust and the thin cover. Support distances are measured from the load-carrying crust to the frame below it. The report records crust closure separately from cover closure.

The intersection report distinguishes unchanged assembly contacts from changed geometry. Its absolute depth gate still includes both. Distances are sampled at vertices, edge midpoints and triangle centres, in both directions. Nonadjacent finite edge crossings are checked separately for each connected changed component. These checks do not certify a continuous maximum self-penetration depth when crossings remain. Open surfaces do not enclose a volume and are listed in the report. A passing sample distance alone is not a clean collision result.

Use Blender to run `render.py -- --prop sofa --out tmp/age`, and repeat with `dress_uniform`. These captures import the exported GLBs, use identical cameras before and after, and apply placeholder colours with neutral world fill and four area lights. Run `compose.py --out tmp/age` with the Hunyuan Python to make the before/after pairs and four-view turntables. The comparison convention is unaged on the left, aged on the right. Numeric image checks do not replace a visual review.
