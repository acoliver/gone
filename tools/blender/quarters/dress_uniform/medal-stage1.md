# Medal second geometry fix: numerical checks pass; image review pending

The standalone #130 candidate passes 17 geometry checks, six manufacturing checks and the unchanged close-camera projection check. The low solid assembly has 8,270 triangles, down from 10,142. Maximum sampled surface residual is 0.02856 mm low-to-high and 0.02792 mm high-to-low, with no excluded region. Frozen close-camera silhouette departure is 0.354 px. These measurements do not establish visual acceptance. No image judgment was performed.

The editable sources are:

- `/Volumes/XS1000/acoliver/projects/gone/branch-2/tmp/wt-130/tools/blender/quarters/dress_uniform/medal-high.blend`
- `/Volumes/XS1000/acoliver/projects/gone/branch-2/tmp/wt-130/tools/blender/quarters/dress_uniform/medal-low.blend`

Standalone exports, measurements, logs and JPEGs are under:

`/Volumes/XS1000/acoliver/projects/gone/branch-2/tmp/wt-130/tmp/issue130-photoreal/stage1c/`

No mounting, production GLB change, shader change, test-file change, commit, install, download, Git configuration change, reset, stash or OCR was performed. The pre-existing edits to `verify_details.py` and `verify_details_export.py` were not changed in this pass. Their shared `medal-budget.json` allocation was updated because the candidate triangle count changed, using the recorded #130 replacement rule.

## Suspension construction and seating limit

The rejected suspension used a broad closed wire path with two long feet and a rear return. It has been removed. The replacement has a compact solid tapered claw integral with the medal's front rim, a separate round-wire jump ring through its drilled eye, and a separate straight solid bar through the jump ring. The bar spans the unchanged sewn ribbon's measured width. It has a rounded square section, rather than an open frame. There are no long vertical side supports.

The raw guide was inspected numerically in registered space. Around z=16 mm its suspension spans approximately 6.17 mm across X; the candidate claw is 6.0 mm wide at its embedded base and tapers to 2.7 mm at the top. This follows the review's description of the concept's compact tapered medal-end fitting. The generated guide's deep upper loop does not determine a new ribbon shape.

The frozen ribbon is a closed cloth strip with a capped lower edge. It has no folded tunnel through which a solid bar can be threaded. Its lower-edge depths also vary across its width. A literal cloth loop around this bar cannot be produced while preserving every ribbon vertex and face.

The selected seating places the bar in front of the lower hem, with its lower surface 1.216 mm above the ribbon's lowest vertex. The exact closest bar-to-ribbon surface gap is 1.153 mm. The front offset allows the jump ring's rear arc to clear the unchanged cloth by at least 0.175 mm. The bar sits above the claw with 0.130 mm clearance. Moving it straight down toward the ribbon's lowest vertex would run into the claw. These gaps are recorded rather than claiming the ribbon is physically folded over the bar. Image review should assess this constrained seating; a literal folded cloth loop would require a later ribbon edit outside this assignment.

The new assembly contains exactly three closed, consistently wound solids: body with integral claw, jump ring, and bar. The topology check now requires those three parts, including exported watertightness. Separate interlocked manufactured pieces cannot be represented by the former single fused-component expectation. Contact, residual, UV and clearance thresholds remain unchanged.

## Star construction and proportions

The former roof sampled an asymmetric guide height field on many shrinking contour rings, blended those heights toward a plateau, then connected them to separate circular centre rings. Those constructions did not share ten facet planes. Their convergence retained uneven ridge heights near the centre. Corresponding probes on the previous low mesh differed by as much as 0.06773 mm under fivefold rotation.

The replacement takes the median of the five guide tip radii and the five notch radii, retaining the measured phase. Straight contour edges and homothetic support loops define ten planar facets. One virtual apex at 2.20 mm is truncated at 2.18 mm to form a small fivefold-symmetric central land. The construction has no independently sampled centre height patch. Ridge finishing is 0.035 mm; the outer tip-edge setback is 0.08 mm. Main facet faces use flat normals, so their surface normals do not inflate a planar roof into a rounded highlight profile.

The registered guide's central height is about 3.28 mm, falling toward approximately 0.95-1.37 mm at the ten contour anchors. The new construction retains that raised centre and descending arms while correcting angular noise and rounded contour variation. Tip radius is 10.6413 mm and notch radius 5.3058 mm. Maximum fivefold depth spread over matching radial probes is 0.000000656 mm on the low mesh. Main-facet interior plane error is below 0.000000281 mm on both meshes.

The concept comparison available to this pass is the supplied image review, which called for straighter planes, crisper ridges and a regular centre. The annular profile was reconsidered and retained at the measured guide radii, including the 11.4868 mm inner crest. No unmeasured claim of a closer annular-width match is made. The broad annulus observation remains an image-review decision.

## Sidewall cause and roundness

The old suspension's Boolean return and feet intersected the turned shell, inserting nonstation vertices and interrupting the sidewall patch. The old low sidewall had 403 vertices over 18 distinct depth values despite a four-station intended profile. Five of six sampled depth sections had missing sidewall-only ray hits where the Boolean joined another feature. This was present in positions before UV projection, so a UV seam was not the source of those cuts.

The replacement claw joins the front rim only. It leaves the sidewall at its four intended depth stations and 384 vertices, with maximum station-vertex radius error of 0.00000450 mm. Every perimeter ray now hits the sidewall at all six measured depths. Each section is sampled at 1,440 angles around the full perimeter, including triangle interiors. Maximum departure from the circular section at that depth is 0.00855 mm low and 0.000771 mm high, consistent with their polygon chords. The numeric result establishes circular sections within those bounds; the implementer has not judged the edge-on renders.

## Measurements

`stage1c/measurements.json` contains the full geometry results. `manufacture-measurements.json` contains the additional suspension, facet and sidewall results, also embedded in the main file. High / low values are listed where different.

| Measurement | Result |
| --- | --- |
| Solid assembly triangles, ribbon excluded | 171,930 / 8,270 |
| Body diameter | 32.0000 mm |
| Body depth, excluding suspension | 2.1800 mm |
| Complete assembly front-to-rear extent | 4.8000 mm |
| Enamel above reverse datum | 1.0000 mm |
| Star central land above reverse datum | 2.1800 mm |
| Star rise above enamel | 1.1800 mm |
| Star tip / notch radius | 10.6413 / 5.3058 mm |
| Claw base width / top width / height | 6.0 / 2.7 / 3.47 mm |
| Claw section depth / eye bore diameter | 0.90 / 1.52 mm |
| Nominal metal above eye bore | 0.26 mm |
| Jump ring round-wire section | 1.00 mm, measured across final X section |
| Jump ring centreline radius / outside diameter | 1.90 / 4.80 mm |
| Solid straight bar width | 22.0517 mm |
| Bar section / edge radius | 1.40 by 1.40 / 0.28 mm |
| Bar-to-ribbon exact surface gap | 1.15303 mm |
| Bar bottom above lowest ribbon edge | 1.21607 mm |
| Complete metal-to-ribbon exact clearance | 0.17503 / 0.17937 mm |
| Body/claw-to-ring clearance | 0.20244 / 0.20057 mm |
| Body/claw-to-bar clearance | 0.12999 mm |
| Ring-to-bar clearance | 0.52587 / 0.53141 mm |
| Strict self-crossings / ribbon crossings | 0 / 0, both meshes |
| Closed, consistently wound manufactured parts | Exactly 3, both meshes; exports watertight |
| Fivefold apex maximum depth spread | 0.000000314 / 0.000000656 mm |
| Main facet plane maximum error | 0.000000281 mm, both meshes |
| Sidewall full-perimeter maximum radial error | 0.000770 / 0.008547 mm |
| Low-to-high residual p50 / p95 / maximum | 0.00431 / 0.01174 / 0.02856 mm |
| High-to-low residual p50 / p95 / maximum | 0.00529 / 0.01348 / 0.02792 mm |
| Convex silhouette departure, front / -35 / +35 degrees | 0.00960 / 0.01257 / 0.01261 mm |
| Complete silhouette error at 490 px body width, front / -35 / +35 | 0.375 / 0.375 / 0.375 px |
| Additional 90-degree complete-silhouette diagnostic | 0.250 px |
| Frozen close-camera filled and boundary silhouette departure | 0.354 px, both metrics |
| Raster spacing for silhouette checks | 0.125 px |
| Frozen close-camera body dimensions, high / low | 483.911 by 499.103 / 483.878 by 499.027 px |
| Low UV collapsed triangles / overlapping pairs | 0 / 0 |
| Low atlas charts / minimum gutter at 2048 | 90 / 18.88 texels |
| Area-equivalent visible-face diameter at 2048 | 1,283.67 texels |
| Noise-only guide displacement p95 / pinned displacement | 0.04078 / 0 mm |

Residuals sample final vertices, triangle centres and unique-edge midpoints in both directions. They are sampled bounds rather than a continuous Hausdorff certificate. No region is excluded from the 0.10 mm maximum gate. Distances are solved in millimetres to avoid the metre-space tolerance problem found in the earlier pass. Exact disjoint separations include vertex/face and interior edge/edge minima. The supplemental measurement uses a conservative AABB candidate filter bounded by an existing vertex/face upper bound; it does not exclude any potentially closer triangle pair.

The initial supplemental plane diagnostic accidentally included the intentional bevel strips with the flat facet interiors. Its area classification was corrected after inspecting the face areas: ten main triangles are approximately 15.9 square mm each, while ridge strips are below 0.21 square mm. The final diagnostic requires exactly ten main facet interiors. `manufacture.log` records the successful final supplemental run. No geometry, residual threshold or contact assertion was changed to resolve that measurement error.

The original numerical guide-fit arrays, raw guide samples and frozen ribbon arrays are identical to stage1b. Guide displacement, pinned curves and guide-triangle correspondence remain available. Both editable Blender files retain the immutable registered guide, faired original triangles, feature curves and embedded correction decisions.

## Triangle allocation

The solid count decreased by 1,872 triangles from stage1b, so the shared allocation decreased by the same amount. The rule is unchanged: add the candidate's increase over the removed solid to each original authored garment ceiling. The old medal is already absent from the non-medal baseline and is not credited twice. Hidden cloth was not reduced.

| Item | Clean | Aged |
| --- | ---: | ---: |
| Non-medal baseline, unchanged ribbon included | 13,048 | 19,585 |
| Removed old solid | 846 | 714 |
| New solid assembly | 8,270 | 8,270 |
| Increase over removed old solid | 7,424 | 7,556 |
| Original authored garment ceiling | 14,999 | 20,652 |
| Updated authored garment ceiling | 22,423 | 28,208 |
| Projected replacement total | 21,318 | 27,855 |

The projected aged/clean ratio is 1.30664, below the unchanged 1.5 limit. `stage1c/budget.json` and `tools/blender/quarters/dress_uniform/medal-budget.json` record the numbers and #130 reason. Frame-time policy, the ratio assertion, tests and unrelated quality checks were not changed. These are replacement projections, not mounted production exports.

## Renders and exact review paths

Cycles CPU rendered the same 31 individual JPEGs, followed by the two comparison sheets. Manifest comparison confirms unchanged frame names, camera positions, camera targets, scales, lights, samples and exposure relative to stage1b. All 33 JPEGs are at most 1400 px on the longest side. The JPEGs were opened only for sheet composition and dimension checks, without visual judgment.

Comparison sheets:

- `/Volumes/XS1000/acoliver/projects/gone/branch-2/tmp/wt-130/tmp/issue130-photoreal/stage1c/renders/concept-high-low-three-quarter-sheet.jpg`
- `/Volumes/XS1000/acoliver/projects/gone/branch-2/tmp/wt-130/tmp/issue130-photoreal/stage1c/renders/concept-raw-high-low-clay-sheet.jpg`

Suspension close-ups:

- `/Volumes/XS1000/acoliver/projects/gone/branch-2/tmp/wt-130/tmp/issue130-photoreal/stage1c/renders/high-clay-bail-close.jpg`
- `/Volumes/XS1000/acoliver/projects/gone/branch-2/tmp/wt-130/tmp/issue130-photoreal/stage1c/renders/low-clay-bail-close.jpg`
- `/Volumes/XS1000/acoliver/projects/gone/branch-2/tmp/wt-130/tmp/issue130-photoreal/stage1c/renders/high-preview-bail-close.jpg`
- `/Volumes/XS1000/acoliver/projects/gone/branch-2/tmp/wt-130/tmp/issue130-photoreal/stage1c/renders/low-preview-bail-close.jpg`

Star-centre close-ups:

- `/Volumes/XS1000/acoliver/projects/gone/branch-2/tmp/wt-130/tmp/issue130-photoreal/stage1c/renders/high-clay-star-centre.jpg`
- `/Volumes/XS1000/acoliver/projects/gone/branch-2/tmp/wt-130/tmp/issue130-photoreal/stage1c/renders/low-clay-star-centre.jpg`
- `/Volumes/XS1000/acoliver/projects/gone/branch-2/tmp/wt-130/tmp/issue130-photoreal/stage1c/renders/high-preview-star-centre.jpg`
- `/Volumes/XS1000/acoliver/projects/gone/branch-2/tmp/wt-130/tmp/issue130-photoreal/stage1c/renders/low-preview-star-centre.jpg`

Edge-on views:

- `/Volumes/XS1000/acoliver/projects/gone/branch-2/tmp/wt-130/tmp/issue130-photoreal/stage1c/renders/high-clay-edge-left.jpg`
- `/Volumes/XS1000/acoliver/projects/gone/branch-2/tmp/wt-130/tmp/issue130-photoreal/stage1c/renders/high-clay-edge-right.jpg`
- `/Volumes/XS1000/acoliver/projects/gone/branch-2/tmp/wt-130/tmp/issue130-photoreal/stage1c/renders/low-clay-edge-left.jpg`
- `/Volumes/XS1000/acoliver/projects/gone/branch-2/tmp/wt-130/tmp/issue130-photoreal/stage1c/renders/low-clay-edge-right.jpg`
- `/Volumes/XS1000/acoliver/projects/gone/branch-2/tmp/wt-130/tmp/issue130-photoreal/stage1c/renders/high-preview-edge-left.jpg`
- `/Volumes/XS1000/acoliver/projects/gone/branch-2/tmp/wt-130/tmp/issue130-photoreal/stage1c/renders/low-preview-edge-left.jpg`

All front, three-quarter, reverse and attachment names are preserved. Every exact JPEG path and dimension is listed in:

`/Volumes/XS1000/acoliver/projects/gone/branch-2/tmp/wt-130/tmp/issue130-photoreal/stage1c/review-jpegs.json`

## Verification and limits

Geometry generation, standalone export, the full independent verifier, frozen-camera projection, final supplemental manufacturing checks, studio render, sheet composition, camera parity, input-array preservation, budget arithmetic and Python syntax checks passed. Logs are `stage1c/geometry.log`, `verify.log`, `projection.log`, `manufacture.log`, `studio.log`, `sheets.log`, `render-check.log` and `sidewall-diagnosis.log`. Blender/Godot process checks preceded Blender launches, and no other session's process was killed.

Visual acceptance remains pending, particularly the constrained ribbon/bar seating and the retained annular width. There is no finished PBR, normal/AO/ORM bake, mounting, cloth-support check, production export or runtime verification in this pass. The saved-camera result is a rigid standalone projection through the frozen registration frame, not a mounted runtime capture.
