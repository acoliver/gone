# Physical brass and resolved ribbon ribs, issue #130

This pass restores conductor reflectance and supplies additional attachment evidence. It does not establish an appearance pass: physical brass still exceeds the unchanged clipping gate under the fixed room rig. No image judgment was performed. The comparison baseline is `6987fce`; separate sheets retain `ef57c29` as the original rejected baseline.

## Measured causes

The previous finish multiplied Remembered brass by `0.76 × 0.13` and Present brass by `0.15` after its oxide recipe. Quantized exposed Remembered linear RGB was `(0.066119, 0.043088, 0.014498)`, only `(7.35%, 6.73%, 6.04%)` of the supplied polished-brass F0 reference `(0.90, 0.64, 0.24)`. Median roughness was `0.235294`, below the requested brushed range. Present exposed RGB was `(0.044934, 0.031923, 0.013699)`, roughness `0.533333`, metallic `0.890196`. Reducing reflected energy while narrowing the clean specular lobe removed broad-face response and left concentrated highlights.

Present's former film multiplied the concept-derived base by `(0.45, 0.49, 0.62)`. It reduced red relative to green and blue: exposed R/G was `1.4075`, compared with `1.7344` in the replacement brown-gold film. Shader albedo is sampled as sRGB, ORM is linear, and factors remain unit-valued. The local probe's baseline added linear mean RGB `(0.000887, 0.000521, 0.000202)` over brass, a warm contribution rather than a green one. The evidence identifies the film recipe and overall reflectance attenuation, not a colour-space conversion fault or a predominantly green probe signal.

The local probe has intensity `1`, box projection enabled, wardrobe-sized bounds `(0.650002, 2.200001, 1.0)` m, centre `(41.325, -9.9, 5.3)` and capture origin `(41.6, -9.9, 5.3)`. Its capture mask includes existing light instances. Six independently oriented, windowed views were rendered from that origin with the existing room lighting. The final square 90-degree views use the native probe capture mask and far range. Remembered direction medians span linear luminance `0.04537–0.10682`, with p95 `0.13331–0.33149`; Present medians span `0.04355–0.11374`, with p95 `0.19110–0.38676`. They establish nonzero room information at the capture origin; they are viewpoint renders, not a readback of the engine's filtered cubemap. No probe intensity, position, extent, mask or environment setting was changed.

The pale centre speck was the game's aiming overlay. `ClickIndicators._draw()` draws a radius-two dot in colour `(0.9, 0.9, 0.85, 0.85)` at the viewport centre. A matched Remembered overlay-on/off control changes exactly 12 pixels within cropped PNG coordinates `(766..769, 390..393)`. The centre changes from sRGB `(205, 200, 185)` to `(63, 35, 8)`. This explains its fixed screen position in both states. The capture tool now hides only `ClickIndicators`; gameplay UI, geometry, UVs and baked normals are unchanged.

The ribbon's old mapping repeated a 16-rib tile 680 times across a UV length representing 1.066 m. Its rib pitch was about `0.0980` mm, roughly 1.5 pixels at the production close-up scale. Filtering suppressed the weak normal and roughness modulation. The new mapping uses 260 repeats, a `0.25625` mm rib pitch, with stronger cross-ribbon relief, roughness modulation and directional fibre sheen. Authored stripe colours remain exact.

## Changes and constraints

`medal_dry_finish.py` now uses physical yellow-brass F0 with the retained concept chromatic variation. Clean roughness follows brushing and curvature: broad faces are rougher than high edges. Present has a darker brown-gold film, exposed metallic near `0.94`, moderately higher roughness, brighter edges and darker, rougher recessed oxide. The old reflectance attenuation and the clean `0.6` roughness multiplier are removed. Enamel and the filtered geometric/fine normal maps remain unchanged.

`medal_refresh_finish.py` refreshes only the Medal's packed source images and ribbon sampling in the saved mounted blends. It verifies every mesh's geometry hash. It does not regenerate the suspender or rerun a cloth solve. The existing full-width ribbon roll and all support/contact/clearance geometry remain exact.

The additional oblique camera is separate from the player camera so the player's pitch driver cannot overwrite its diagnostic pose. It shows the surrounding garment and full suspension region, with contact-off and weave-off controls. These files are labelled additional evidence. The three production camera definitions and their manifests remain unchanged. A regression pins the new ribbon sampling to exactly 260; the former 680 assertion described the previous art recipe, not a quality threshold. No engineering threshold was relaxed.

## Fixed-rig clipping limitation

A constant physical-F0 diagnostic isolates finish from albedo. Under the unchanged room rig, Remembered rim clipping is `36.97%` at roughness `0.35`, `51.91%` at `0.45`, and `96.38%` at `1.0`, measured as any LDR channel at least `0.99`. Twelve additional anisotropic combinations per state varied roughness `0.35/0.43`, strength `0.7/0.95` and three tangent directions. Their lowest Remembered clipping was `24.70%`; Present's was `29.50%` with the same untarnished physical-F0 control. This tested set does not demonstrate that every possible physical finish is infeasible, but it provides no basis for claiming the 2% gate is satisfied. No arbitrary BRDF attenuation, painted highlight, emission, light adjustment or tonemap change was introduced to conceal the failure.

## Final game measurements

The candidate fails two appearance criteria in Remembered and one in Present. The existing tests, engineering invariants and appearance thresholds remain unchanged. Values below come from actual windowed Metal Forward+ captures, decoded from LDR to linear Rec.709, with runtime first-hit masks. NMAE uses the existing 0.02 reference floor.

| Measurement | Remembered | Present | Existing gate |
| --- | ---: | ---: | --- |
| Rim any-channel clipping | 51.062188% | 21.446533% | At most 2%, both fail |
| Rim p95/p10 luminance | 9.281577 | 8.278371 | At least 2, pass |
| Rim p95 minus p10 luminance | 0.846356 | 0.674169 | At least 0.08, pass |
| Flat-normal rim NMAE | 0.157270 | 0.180733 | At least 0.03, pass |
| Flat-normal bevel NMAE | 0.054272 | 0.084924 | At least 0.03, pass |
| Two-pixel coherent normal-effect bevel fraction | 48.526077% | 85.448578% | At least 50%, Remembered fails |
| Normal-buffer NMAE | 0.029051 | 0.028994 | Greater than zero, pass |
| Rough-enamel NMAE | 0.468763 | 0.227315 | At least 0.02, pass |
| All quarters probes off, brass NMAE | 0.016727 | 0.010376 | Brass or enamel at least 0.01, pass |
| All quarters probes off, enamel NMAE | 0.023180 | 0.021187 | Same gate |
| Local probe off, brass NMAE | 0.016727 | 0.010375 | Diagnostic |
| Whole contact-crescent median reduction | 5.511866% | 6.205836% | 5–20%, pass |
| Outside 3 mm, maximum LDR channel delta | 0 | 0 | At most 1/255, pass |
| Exposed brass age-off NMAE | 0.008058 | 0.552436 | Present at least 0.03, pass |
| Exposed brass visibly changed by age | 1.716273% | 95.608711% | Present at least 50%, pass |
| Tarnish cavity/edge occupancy ratio | 13.947388 | 15.467073 | Present at least 2, pass |
| Ribbon weave-off NMAE | 0.103108 | 0.187221 | At least 0.01, pass |

The normals themselves are unchanged. Their coherent-bevel visibility metric is now below its 50% threshold in Remembered; the physical-finish candidate must not be reported as a normal-visibility pass. All other existing visibility gates pass. In particular, the probe's measured relative contribution remains only about 1–2%; the stronger broad-face response is not evidence of a large environmental reflection contribution.

The quantized exposed atlas now measures Remembered F0 `(0.910654, 0.647823, 0.252453)`, median roughness `0.431373`, metallic `0.984314`; Present F0 `(0.465598, 0.268262, 0.086478)`, roughness `0.549020`, metallic `0.941176`.

### Broad faces versus the concept reference

The supplemental broad-face mask selects visible rim samples outside the tarnish and convex-edge masks. The concept uses the retained stage-two brass-colour selection, which excludes very dark and bright pixels. Its illumination differs from the game, so these are image comparisons rather than optical reflectance measurements.

| Measurement | Concept brass | Remembered broad faces | Present broad faces |
| --- | ---: | ---: | ---: |
| Mean linear luminance | 0.360171 | 0.499561 | 0.392623 |
| Baseline `6987fce` broad-face mean luminance | n/a | 0.037315 | 0.049681 |
| Mean RGB divided by mean luminance | (1.325745, 0.964124, 0.396188) | (1.519795, 0.929108, 0.171652) | (1.562419, 0.908695, 0.248351) |
| Broad-face luminance / concept | 1 | 1.387012 | 1.090102 |
| Broad-face local-probe NMAE | n/a | 0.017455 | 0.010732 |
| Broad-face mean luminance, local probe off | n/a | 0.490841 | 0.388409 |
| Broad faces with any clipped channel | n/a | 52.022194% | 23.526527% |
| Broad faces with all three channels clipped | n/a | 0% | 0% |

Clipping is principally red, with green clipped on 18.067464% / 1.572716% of broad-face pixels; blue does not clip. This distinction does not turn the any-channel clipping failure into a pass. Present's matched untarnished control has exposed mean luminance `0.617327`, versus `0.397738` with the oxide film.

### Additional context and temporal controls

The additional oblique view has 56,777 / 49,610 visible brass pixels, 16,797 / 13,435 ribbon pixels and 86,100 / 75,970 surrounding-cloth pixels. Its measured contact crescent has 10,707 / 11,454 pixels with median reduction `5.580462% / 6.216491%`. Ribbon weave-off NMAE is `0.086566 / 0.096311`. The retained full-width roll, suspender, ribbon return and surrounding wool are supplied for image review; these measurements establish sampled context and effect visibility, not photographic realism.

The 24-frame additional sweep measures zero isolated fine-normal spike pixels in both states. The overstrong controls yield 10,785 / 1,401. Production normalized temporal second-difference p99.9 is `0 / 0.014515`. The zero Remembered value must be interpreted alongside its clipping and failed coherent-bevel gate, not as proof of ideal finish detail.

At the unchanged 1152×648 smoke-policy resolution, 300 samples give production mean/p95 frame times of `2.950507 / 3.113` ms Remembered and `3.195663 / 3.480` ms Present. Both pass the existing policy. GPU timing is unavailable; negative texture-memory counters are invalid and do not establish VRAM usage.

## Verification

Nine Blender regressions passed: `test_issue130_details.py`, `test_detail_bakes.py`, `test_detail_clearance.py`, `test_medal_support.py`, `test_medal_mount.py`, `test_attachment_rotation.py`, `test_attachment_supports.py`, `test_aging_support.py` and `test_baked_age_colour.py`. Python tests passed: three new physical-finish tests, two fine-normal tests, three attachment-metrics tests, six contact tests and eleven fixture-weather tests. The new physical-finish tests first failed because their implementation functions were absent. The first focused Godot run correctly rejected the old exact weave-frequency expectation; it now pins the new art recipe to 260 without relaxing a tolerance.

The focused guarded Godot runner passed `36` tests with `0` failures. The full guarded runner passed `1016` tests with `0` failures. Shutdown resource/leak diagnostics remain in the full-suite log, as in the baseline log; no script-error or remapped-parameter guard violations occurred. Windowed capture logs have no script, shader-compilation or assertion errors.

Saved-source GLB repeat exports are byte-identical to both production GLBs; checked-in blends equal the tested mounted sources. Source and independent export verifiers preserve all non-Medal geometry, transforms, UVs, normals, colours, materials and embedded textures. The independent accepted-metal verifier also confirms retained metal topology, UVs, material regions and smooth flags. Geometry totals remain 21,962 / 28,499 triangles, with unchanged garment ceilings. Strict self/body crossing counts are zero. Continuous metal/wool clearance is `0.250999 / 0.251001` mm, body depths are `3.973170 / 2.180004` mm, and all support and metal/ribbon separation checks pass. The unchanged contact ratio remains exactly one outside its 3 mm bound.

A fresh editor import preceded captures. All 18 native import records, covering both GLBs and every medal PNG, have source MD5 equal to the current files before and after capture. Both production camera manifests equal the `6987fce` baseline exactly. Windowed capture, performance and probe-view runs were serialized using process checks; no other session was killed.

All 40 JPEGs have maximum dimension at most 1400 pixels. `*-before-after.jpg` places `6987fce` on the left and this candidate on the right; `*-original-before-after.jpg` places `ef57c29` left and this candidate right. `*-oblique-context.jpg` and `*-oblique-context-controls.jpg` are additional evidence, not replacement production views. The concept/studio sheets retain labelled stage-two studio references rather than implying that those references render the new finish. `git diff --check` passed.

Raw logs and PNGs are under `tmp/issue130-photoreal/stage3c/`. JPEG sheets are under `docs/art/quarters/sheets/medal/photoreal-stage3c/`.

## Reproduction

Use the existing Blender 4.5.11 and Hunyuan Python environment. Run `medal_dry_finish.py --bakes tmp/issue130-photoreal/stage2 --normal-source tmp/issue130-photoreal/stage3b/baseline/maps --output tmp/issue130-photoreal/stage3c`, then `medal_refresh_finish.py --baseline tmp/issue130-photoreal/stage3c/baseline --output tmp/issue130-photoreal/stage3c/mounted`. The baseline contains the saved `6987fce` sources. Promote the refreshed blends and use `build.py --output …` / `build.py --aged --output …` without `--assemble`. Repeated saved-source exports must match byte-for-byte.

No installs, downloads, Git configuration changes, resets, stashes, force pushes, OCR, global environment edits, room-light edits, production-camera edits or merge were made. OCR review skipped per Andrew 2026-10-09.
