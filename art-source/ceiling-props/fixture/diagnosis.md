# Why the beam became a box

The earlier multi-view conditioning supplied essentially the same long face as both the front and the left view. The front and left silhouettes have identical bounding boxes, [100, 358, 928, 613] on 1024-square canvases, and identical aspect ratio 3.247. Their RGB correlation is 0.99823; mean absolute pixel difference is only 1.544/255. The left-edit prompt requested a 90-degree turn, but the images did not implement that turn. Assigning these near-duplicate images to perpendicular view labels tells reconstruction that the fixture has approximately equal X and Z lengths.

The three earlier meshes confirm this interpretation: seed 410 has extents [1.99542, 0.61906, 1.99483], seed 411 [1.99506, 0.62464, 1.99331], and seed 412 [1.99502, 0.62995, 1.99418]. Their two largest dimensions differ by less than 0.09%. The long 3.25:1 face has effectively been applied to two perpendicular sides of a square slab.

The square canvas is not itself the cause. The port's preprocess.recenter crops to alpha bounds and uniformly scales the longest side before square padding. This preserves aspect ratio. The box-v parameter controls the isotropic marching-cubes domain, not independent axis resizing. The original beam alpha masks remove zero enclosed interior pixels, so there is no evidence that white matting ate the grille in those inputs.

The replacement cassette inputs have a different, additional problem: front silhouette aspect is only 1.611 and left 1.232, despite a prompt requesting length-to-width 3.3. Its generation script also explicitly cropped the beam and requested removal of the structural beam. That was a change of object, not repair of the selected beam.

## Corrective direction

Generate an approximately 1.10 m long complete beam fixture with 0.22 m width and 0.10 m depth, capped ends, a narrow underside grille, and recessed pale glass. Generate multiple front/left/back/right candidates, reject duplicate perpendicular silhouettes numerically, and retain each input and mask. Preserve opaque internal glass in the alpha matte by removing only the exterior background. Use the full non-turbo Hunyuan model at the requested settings and compare raw-mesh axis ratios before any Blender scaling.

## Placement proposal

The current module is 0.575 x 0.060 x 0.180 m, used as a pair along X in CeilingServices.module_poses(). A single 1.10 x 0.10 x 0.22 m beam replaces the visual span of that pair (1.15 m overall) rather than doubling the pair's length. The proposed export has its top at Y=0, bottom at Y=-0.10 m, and length along X. Its origin belongs directly on the ceiling plane. Current regular fixtures sit 0.08 m below the ceiling and retain old separate lenses and material overrides, so later integration must remove the duplicate pair/lens and place the new top at the actual ceiling. Phase 1 makes no placement or game changes.

Diagnosis is based on image/mask measurements, generator source inspection, and mesh bounds, not a visual quality judgment.

## Oriented-bounds cross-check

The original beam meshes also have square oriented bounds, not merely equal world-axis spans: seed 410 [0.61888, 1.99482, 1.99529], seed 411 [0.62769, 1.99328, 1.99507], seed 412 [0.63029, 1.99419, 1.99499]. Their oriented length/width ratios are 1.0002 to 1.0009, confirming the original square-slab diagnosis.

The new four-view trial 710 is different: although its world-axis L/W is 1.269, oriented bounds are [0.58429, 0.58892, 2.26160], giving oriented length/width 3.840. It is a diagonal beam with an approximately square cross-section, not another square slab. The initial raw-axis screening rejected it too quickly. It remains available for comparison; final ranking must distinguish object orientation from shape before fitting. Front-only candidates test whether omitting the still-unreliable end edits improves the cross-section and grille.
