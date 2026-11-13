# Stage-two PBR candidate produced; cage and scratch gates still fail

The #130 medal has UV-bound normal, AO, curvature, albedo and ORM masters, Remembered and Present materials, matched high/low studio renders and the requested controls. Stop B images are available for review. This is not a claim of visual acceptance or a fully passing stage: the strict zero-cage-miss contract is unmet, and five of six equal-precision temporal scratch lanes fail the numeric threshold. No images were judged and no reviewer was delegated.

All paths in this report are relative to `/Volumes/XS1000/acoliver/projects/gone/branch-2/tmp/wt-130` unless written in full. Logs, raw arrays, linear captures and JPEGs are under `tmp/issue130-photoreal/stage2/`.

## Scope and preservation

The accepted `medal-high.blend` and `medal-low.blend` were read, never overwritten. The candidate retains 171,930 high and 8,270 low triangles. Independent comparison of both PBR candidate blends against the accepted sources found exact equality of vertex positions, faces, smooth flags, corner normals, material membership and feature labels. Low `MedalUV` values are also exact. No geometry fault was established, and no geometry was changed to repair a bake.

The existing atlas was retained: 90 charts, zero collapsed triangles or overlap pairs, 18.88 texels minimum chart separation and approximately 1,284 texels across the visible body at 2048 resolution. UV rasterization found zero overlapping interior texels. Individual feature regions sometimes share a chart, so their boundaries are not necessarily UV gutters.

No production GLBs, tunic sources, runtime shaders or tests were changed. The pre-existing edits to `verify_details.py` and `verify_details_export.py` were left untouched. No installs, downloads, Git configuration changes, resets, stashes, commits or OCR occurred. All bakes and renders used CPU Cycles. Other sessions' Godot processes were not killed.

## Bakes and the remaining projection failure

The medal-specific baker uses selected-to-active projection, seed 130303, 64 path samples for normal/transfer maps and 128 for final AO. The atlas is 2048 square. Normal convention is OpenGL tangent +Y. Explicit feature-patch cages have 0.15 mm extrusion and 0.30 mm maximum reach. High-source patches retain their original positions and corner shading normals. All high patches remain assembled for the two AO radii.

The first shared cage crossed feature boundaries at 14,615 texels, mostly enamel/star-wall transitions. Isolated feature sources removed those crossings. A subsequent per-pass dilation also contaminated neighboring features inside shared UV charts. The final method bakes independent undilated region images, merges only owned texels and dilates after the merge. The corrections affected only the baker.

Signed curvature is computed from the high-poly surface's normal variation, then spatially Gaussian-filtered at 0.10 and 0.40 mm. Convex and concave fields are transferred with EMIT. AO uses 0.3 and 2 mm radii; ORM.R is `1 - 0.30*(1-AO_near) - 0.20*(1-AO_local)`. Direct lighting is not multiplied into albedo. CPU AO uses one shader sample per path sample, rather than multiplying two independent 128-sample loops.

| Bake measurement | Result |
| --- | --- |
| Occupied atlas texels audited | 2,322,083 |
| Final uncovered texels / triangle centroids | 0 / 0 |
| Final wrong-feature encoded texels | 0 |
| Undilated invalid shader samples | 813: 796 misses and 17 partial edge samples |
| Completion distance | 1 texel in most regions; maximum 1.414 texels on the small central land |
| Independent actual cage rays | 2,322,083 |
| Actual missed rays | **737, strict gate fails** |
| Wrong-region source hits | 0, sources are isolated by feature |
| Actual misses by region | Sidewall 254; rim 394; star roof 17; central land 27; suspension 45; other regions 0 |
| Invalid shader samples with an actual ray hit | 79 |
| Invalid shader samples with an actual ray miss | 734 |
| Tangent decode versus high object-space normal, median / p95 | 0.0102° / 0.3292° |
| Delivered low tangent unit / orthogonality maximum error | 1.49e-7 / 1.70e-7 |
| Wrong-material UV face centres in final high / low previews | 0 / 0 |

Within-feature nearest valid samples complete the subtexel seams before atlas dilation. This produces zero final holes, but it does not turn the 737 actual misses into ray hits. The raw maps, completion report and independent miss mask are retained. Do not promote this candidate as passing the zero-ray-miss contract.

The high-poly preview receives transferred color/roughness UVs without changing its geometry. Forty-eight tiny faces initially sampled the wrong material interior; their UVs were constrained to the matched low chart and the high views were rendered again. The high preview does not consume a tangent normal map, and its transferred UVs are not a delivery unwrap. Some of its tangent vectors are zero. The low mesh is the normal-mapped delivery candidate and passes the tangent contract.

Files: `bake-settings.json`, `bake-quality.json`, `seam-completion.json`, `cage-ray-audit.json`, `actual-cage-ray-misses.npy`, `normal-error-heatmap.png` and `source-verification.json` in the stage-two directory. The independent cage script and log are `audit_cage_rays.py` and `cage-ray-audit.log` there.

## Materials and masters

Masters are in `assets/props/quarters/dress_uniform/medal/`. The six delivery PNGs are `as_built_albedo.png`, `as_built_normal.png`, `as_built_orm.png`, `aged_albedo.png`, `aged_normal.png` and `aged_orm.png`. All are 2048 RGB8. Albedo alone is sRGB. ORM uses linear R occlusion, G final roughness and B metallic. Normal is linear OpenGL +Y. Offline `geometry_normal.png`, `ao_near.png`, `ao_local.png`, `curvature_convex.png` and `curvature_concave.png` are linear RGBA16.

The concept crop is x=266–779, y=348–871 from `docs/art/quarters/sheets/medal/c-machined-rim-seed130303.png`. Its brass chromaticity is sampled after removing luminance, mixed conservatively with the accepted clean brass reference and clamped to modest color variation. The source patch is sampled once over the face, without tiling. Brown oxide takes its chromaticity from the darker brass pixels. No rusty-steel recoloring or Hunyuan Paint pass was used.

| Parameter | Remembered | Present |
| --- | --- | --- |
| Principal brass linear albedo | (0.6600, 0.4381, 0.1487) | Same exposed-metal reference |
| Exposed brass metallic | 0.985 | 0.960 |
| Brass roughness, minimum / median / maximum | 0.200 / 0.300 / 0.363 | 0.330 / 0.385 / 0.650 |
| Limited cavity stain / oxide metallic minimum | 0.889 | 0.025 |
| Oxide linear color | (0.0850, 0.0516, 0.0153), restrained mixture | Same color, stronger cavity coverage |
| Enamel linear albedo / metallic | (0.008, 0.025, 0.095) / 0 | Same / 0 |
| Enamel roughness | 0.215 | 0.310, sparse scuffs up to 0.365 |
| Enamel specular / coat weight | 0.5 / 0.65 | 0.5 / 0.65 |
| Enamel coat roughness | 0.13 | 0.23 |
| Brass coat | 0 | 0 |

Rim brushing follows circumference; the star finish follows the ten facet directions. Sparse scratch widths are 0.01–0.04 mm and lengths 0.2–1.5 mm. Normal depth is 0.6 micrometres for scratches and 0.18 micrometres for brushing, filtered before encoding. Present represents **1000 years** of dry, sealed, sterile storage: oxide follows sheltered cavities, exposed high points retain metallic response, and enamel has limited dulling/scuffs. There is no green growth, wet streak pattern or uniform grunge layer.

Candidate blends are `tmp/issue130-photoreal/stage2/medal-pbr-remembered.blend` and `medal-pbr-present.blend`. `materials.json` contains the recipe measurements. Studio Cycles supplies physical occlusion; ORM.R is wired as the intended export occlusion input, not baked again into base color. Runtime coat/ORM integration is outside this stage.

## Studio visibility and negative controls

The neutral studio has a large white area light, a dark camera-invisible reflection card and a grey environment. Front and concept three-quarter camera positions, targets and scales match stage1c exactly. The ±35° views are explicit pure-yaw diagnostics; stage1c's render manifest did not contain pure-yaw ±35° frames. High and low use identical cameras and lighting within every pair. Exposure remains zero. Metrics use linear Rec.709 luminance from float32 EXRs, with a 0.02 normalization floor. Feature masks come from first-hit triangle rays, including 606 front-facing star-bevel pixels at the 500-pixel body scale.

| Gate | Remembered | Present | Controls / result |
| --- | --- | --- | --- |
| High versus finished RGB8 normal render, median / p95 | 0.138° / 1.041° | Same geometry/normal atlas | Pass ≤3° / ≤8° |
| Flat / ignored normal error, median / p95 | 5.435° / 13.638° | Same geometry | Both fail |
| Inverted-green normal error, median / p95 | 5.886° / 22.156° | Same geometry | Fails |
| Rim linear Y p10 / p95 | 0.05872 / 1.53903 | 0.08538 / 1.22026 | Ratios 26.21 / 14.29; differences 1.480 / 1.135; pass |
| Rim highlight bands | Up to 4; ≥2 in 22/24 sectors | Up to 4; ≥2 in 24/24 sectors | Detected bands are at least 2 px wide |
| Near-clipped rim JPEG pixels, channel ≥254 | 0.248% | 0.244% | Reported separately from HDR values above 1 |
| Full versus flat normal, rim / star bevel normalized MAE | 51.75% / 59.70% | 36.26% / 34.44% | Coherent ≥2 px changes over all inspected angular samples; pass |
| Ignored binding versus flat normal | 0 difference | 0 difference | Both fail the effectiveness test as intended |
| Smooth-normal rim control | 0 bands; luminance ratio 1.42 | Up to 2 bands; luminance ratio 1.75 | Both fail the combined band/contrast gate |
| Wrong UV / inverted green, rim/bevel image difference | 73.57% / 61.90% | 59.49% / 45.24% | Both produce measurable errors |
| Moving enamel reflection | 5 consecutive qualifying frames; median area 5.16%; neighbor contrast 346.7%; roughness-one change 88.5%; travel 258.6 px | 22 consecutive frames; area 4.99%; contrast 21.0%; change 28.9%; travel 314.6 px | Pass; roughness-one paired excess is zero; frozen painted response has zero travel |
| Present age follows form | Not an age acceptance lane | Atlas cavity/edge occupancy ratio 10.66; visible cavities 157/481 affected, exposed edges 0/11,651; affected-region change 62.25% | Visible ratio lower bound 3,803 using a one-edge-pixel denominator; uniform-tint control ratio 1 fails |
| Repeated color blocks | 0 duplicates among 799 nonconstant 32px brass blocks | Same source/atlas policy | Repeated-tile control has 15 duplicate blocks and fails |

The enamel negative control sets surface and coat roughness to one and disables coat weight. It is a combined fully rough/coat-off reflection control. The first enamel proxy selected the top luminance decile and also passed this control's diffuse gradients. It is retained in `visibility-gates.json` and marked invalid. Acceptance instead uses positive full-minus-roughness-one excess to locate coherent specular-dependent regions, checks their contrast against a six-pixel neighboring enamel ring and requires movement over at least three consecutive qualifying frames. A source behind the medal is not required to produce a front reflection. The plan's 1% area, 15% contrast and 2% effect-off thresholds are retained.

Visible Present oxide affects only 157 pixels in this front mask, about 0.107% of its 146,429 inspected brass pixels. Its effect is measurable but spatially limited. Image review must assess whether this is the intended amount of dry age; the occupancy ratio alone does not settle that question. The block test rejects exact repetition, not every possible visual pattern.

## Scratch stability does not pass

There are 24 slow light-rotation samples per state, captured natively at body widths 500.09, 34.23 and 7.44 px, using 672, 46 and 10 px square renders. Full, fine-finish-off, roughness-one and nearest-sampled 18× scratch-normal controls are retained. These are native small renders, not only resized close-ups.

The initial effect-off normal was RGBA16 while the finished normal was RGB8. An additional equal-precision RGB8 control separates this quantization difference from fine finish. Normalization was also corrected to use the actual brass region rather than the whole frame. The earlier measurements remain in `visibility-precision16-control.json`; the final ones are in `visibility-gates.json`.

The numeric temporal gate measures spikes in the full-minus-fine-finish-off signal relative to adjacent light samples. A spike is greater than 10% of the reference brass-region mean, with the 0.02 floor. Acceptance requires fewer than 0.1% spike samples. It is conservative and may include coherent reflection changes; it is not a visual finding of individual glittering pixels.

| State / body width | Final spike-sample fraction | Strong unfiltered control | Result |
| --- | ---: | ---: | --- |
| Remembered / 500 px | 0.2907% | 1.7656% | **Fail** |
| Remembered / 34 px | 0.7440% | 4.7262% | **Fail** |
| Remembered / 7 px | 0.2778% | 6.6667% | **Fail** |
| Present / 500 px | 0.1102% | 0.9276% | **Fail** |
| Present / 34 px | 0.1369% | 2.0536% | **Fail** |
| Present / 7 px | 0% | 1.9444% | Pass |

All six strong controls fail. No material was retuned after these results. The candidate stops here for image review, with the failures reported rather than a claim that the finish is stable.

## Exact review JPEG paths

All JPEGs are at most 1400 px on the longest side. Sheets are text-free. The full inventory and dimensions are in `tmp/issue130-photoreal/stage2/review-jpegs.json`.

- `/Volumes/XS1000/acoliver/projects/gone/branch-2/tmp/wt-130/tmp/issue130-photoreal/stage2/renders/concept-remembered-high-low-three-quarter-sheet.jpg`: concept, high Remembered, low Remembered from left to right.
- `/Volumes/XS1000/acoliver/projects/gone/branch-2/tmp/wt-130/tmp/issue130-photoreal/stage2/renders/present-high-low-sheet.jpg`: three-quarter high/low above front high/low.
- `/Volumes/XS1000/acoliver/projects/gone/branch-2/tmp/wt-130/tmp/issue130-photoreal/stage2/renders/rim-brushing-star-facets-sheet.jpg`: Remembered high/low above Present high/low.
- `/Volumes/XS1000/acoliver/projects/gone/branch-2/tmp/wt-130/tmp/issue130-photoreal/stage2/renders/remembered-front-obliques-sheet.jpg`: high above low; front, concept three-quarter, -35°, +35° from left to right.
- `/Volumes/XS1000/acoliver/projects/gone/branch-2/tmp/wt-130/tmp/issue130-photoreal/stage2/renders/present-front-obliques-sheet.jpg`: same layout for Present.
- `/Volumes/XS1000/acoliver/projects/gone/branch-2/tmp/wt-130/tmp/issue130-photoreal/stage2/renders/remembered-rotating-light-8frames-sheet.jpg`: low Remembered, frames 0/3/6/9 above 12/15/18/21.
- `/Volumes/XS1000/acoliver/projects/gone/branch-2/tmp/wt-130/tmp/issue130-photoreal/stage2/renders/present-rotating-light-8frames-sheet.jpg`: same layout for low Present.
- `/Volumes/XS1000/acoliver/projects/gone/branch-2/tmp/wt-130/tmp/issue130-photoreal/stage2/renders/remembered-normal-controls-sheet.jpg`: full, flat normal, wrong UV, inverted green from left to right.
- `/Volumes/XS1000/acoliver/projects/gone/branch-2/tmp/wt-130/tmp/issue130-photoreal/stage2/renders/present-normal-controls-sheet.jpg`: same control layout for Present.

Individual high/low, front, three-quarter and ±35° JPEGs use names such as `high-remembered-front-full.jpg` and `low-present-plus35-full.jpg` in that same render directory.

## Verification and limits

Python syntax checks, final map validation, exact geometry/low-UV preservation, low tangent checks, actual texture role/dimension/bit-depth checks, wrong-material UV checks, independent cage rays, studio normal controls, native-resolution sweeps and JPEG dimension/inventory checks ran. The two unmet technical gates are listed above. No existing test assertion, tolerance, line limit or CI rule was changed.

Godot import, BC5 reconstruction, engine mipmaps, runtime tangent generation, reflection-probe contribution, cloth contact/locality, non-medal game-image preservation and production export have not been exercised. They require later integration and are not claimed from these standalone studio renders. No production asset has been promoted. Image review is pending. Work stops at image stop B.
