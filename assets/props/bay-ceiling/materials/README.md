# Bay ceiling surface bake

The five material sets use the generated charcoal-paint and aged-steel swatches in `art-source/bay-ceiling`. The steel swatch supplies oxide colour and the luminance/chroma/edge structure that selects localized corrosion. Geometry, layout, fixtures, UVs, runtime materials, global shaders and lighting are unchanged by this calibration.

`tools/prepare_bay_ceiling_material.py` reproduces the textures with NumPy, Pillow and SciPy. It asserts fitted contours against the geometry manifest before baking. `material-provenance.json` records source hashes, dimensions, masks, texture hashes and control differences.

## Material calibration

Same-camera, single-input studio ablations identify albedo/mask contrast as the main contributor to the coarse surface. On intact and torncorner panels, removing albedo wear changes the central ROI by 1.68 and 3.31 RGB levels on average. Disabling normals changes it by 0.16 and 0.24; flattening roughness changes it by 0.17 and 0.25. Normal relief is a secondary effect in this rig. These measurements isolate inputs; they do not establish visual acceptance.

The balanced bake reduces diffuse cluster density and modulates it with a 25 mm low-pass of source structure. Damage fields still select higher-density locations rather than solid oxide fills. A 35 mm low-pass of source steel luminance supplies broad paint-value variation at strength 0.70. Oxide uses 0.55 linear-light saturation and one scalar gain targeting median luminance at 0.95 times the charcoal source. No synthetic colour noise, pale peel outline or directional grime is added.

Maps remain 2048×1024 over 1.14×0.56 m. Fine source filters remain 0.45–0.65 mm. Median connected-cluster equivalent diameter is 1.65 mm on all variants; some connected groups are larger. Colour and mask mirrors remain registered. Repeated intact instances still share one texture.

Oxide mask coverage is 24.17% intact, 24.32% subtlewarp, 30.83% sag, 31.26% torncorner and 30.89% brokenedge. These are mask measurements, not visible orange coverage. The unchanged damaged-mask test requires more than 29% at its test resolution, so the bake does not reach the suggested 20–28% damaged-panel range. Away from geometry edges, oxide coverage is 10.19% intact and 18.00% torncorner. Mean edge oxide is 3.42 and 2.25 times mean broad-face oxide respectively.

Lower intact density lost installed-view visibility: the first balanced result changed only 3.83% of the fixed central ROI by more than three levels, below the unchanged 5% gate. Increasing broad value strength alone produced 3.88%, despite a larger studio response. Restoring selected fine clusters increased installed visibility without restoring the old orange saturation or relief. The final intact density is 0.075 versus the original 0.115. Isolated parameter captures and measurements are retained under `broad-value-ab/`, `intact-density-ab/` and `calibration-edit-measurements.json`.

Production paint-height scale is 0.24, giving a maximum film of 88.02 micrometres rather than about 367. The relief function retains its unit-scale default for the existing signed-ramp tests; the production bake explicitly passes the artist thickness scale. Separate verification recomputes scaled derivatives and matches every normal PNG pixel. Runtime normal scale stays 0.35. Roughness calibration is unchanged. The small existing edge-dust term remains; its visibility is unconfirmed.

## Controls and review evidence

`control_albedo.png`, `control_normal.png` and `control_roughness.png` are byte-identical to the prior bake. Controls disable body wear without replacing hardware materials. Captures and numerical diagnostics live in `tmp/verify-stasis-ceiling/material-balanced/`:

- Root captures: final room white/red, installed closeups, single intact/torncorner studio and matching wear-off controls.
- `baseline-ab/`: original material with albedo, normals or roughness disabled separately.
- `final-ab/`: final ablations, reconstructed old material, albedo-map-only and normal-map-only edits.
- `accepted-hatch-same-studio-closeup.png`: existing production hatch, front rotated to the panel's visible-face orientation, using the exact intact camera and studio lights. This is a metric closeup, not a whole-hatch view.
- `review/`: 1280×720 review copies, including the approved source image. The source image has its original baked lighting and is not relit to the studio.

Visual acceptance belongs to the driver image review. Numeric texture statistics cannot establish a match to either the source image or the accepted hatch.

## UV, normal and runtime contract

Broad-face UV0 uses normalized Blender XY: `u = x / 1.14 + 0.5`, `v = y / 0.56 + 0.5`. Image rows descend as UV +V rises. Tangent normals use normalized `(-dheight/dcolumn, +dheight/drow, 1)`, matching `tools/prepare_hatch_paint.py`. The existing positive-U and positive-V ramp tests retain their assertions.

Both broad faces overlap in UV space. Return edges project their bottom UV 2 mm toward adjacent metal. The sloping pressed rim retains planar projection. No geometry or UV exports were regenerated.

`BayCeilingMaterial.material_for_variant(...)` binds matching albedo, roughness and normal maps through exactly five cached `StandardMaterial3D` resources. Metallic remains 0.22, roughness scalar 0.86, normal scale 0.35 and emission disabled. `roughness.png` and `normal.png` remain byte-identical aliases of the intact maps. Runtime capture checks compare imported pixels against the current source PNGs.

Mount heads, rails, hangers and service trim retain their existing shared weathered-steel material and geometry.
