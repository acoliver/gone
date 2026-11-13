# Mounted photoreal medal, issue #130

The medal is mounted in both production tunics, with reproducible exports and measured in-game normal, enamel and cloth-contact responses. The probe-contribution target remains unmet. The other dresses occlude the medal at the unchanged buttons and wardrobe cameras. Visual approval belongs to the driver; this leaf did not judge images or run a vision agent.

## Mount and ribbon

The frozen input was PR head `ef57c29314e01a6c1b9a818d3aba4a8d66183bbd`. The accepted stage-one body, integral eyelet, jump ring and suspender bar remain the three manufactured solids. No front, suspension, atlas or material retexture was made. Independent comparison with the accepted stage-two blends finds identical topology, material regions, smooth flags and corner UVs; visible-position differences are at most 0.0000201 mm from storing world coordinates as float32. Only the hidden reverse was fitted to the existing wool.

| Measurement | Remembered | Present |
| --- | ---: | ---: |
| Reverse anchors | 96 | 96 |
| Anchor support distances | 0.610686–1.969605 mm | 0.328561–0.920816 mm |
| Continuous metal/wool clearance | 0.250999 mm | 0.251001 mm |
| Disk-body depth, excluding claw | 3.973170 mm | 2.180004 mm |
| Maximum hidden-reverse adjustment | 1.793169 mm | 0 mm |
| Exported minimum metal/ribbon clearance | 0.098295 mm | 0.098294 mm |
| Ribbon lower width | 21.807853 mm | 21.575336 mm |
| Central lower relief | 6.542356 mm | 6.472601 mm |

The original 0.8 mm ribbon cannot pass through the 0.130 mm space between the accepted claw top and bar bottom while retaining the 0.080 mm metal clearance on each side. The lower attachment therefore has two continuous 180-degree U-fold tongues and a central relief for the linked ring and claw. This is a lower central cutout, not an unbroken full-width lower loop. The tongues retain the saved outer width, have a nominal 0.100 mm bar clearance, return upward behind the bar and reach local Z=17.250 mm at their bottom. Upper sewn positions and per-corner DetailUV, BakeUV and RibbonColours samples are preserved exactly, including the pilot's UV seams. The separate RibbonBar is unchanged.

Strict checks find four closed, consistently wound, positive-volume components and no self, cloth or metal crossings. The original 0.25 mm continuous clearance and 2 mm support limits remain. Updated attachment, fitted-medal, eyelet, frame and rigid/flexible binding records are stored in the editable tunics.

The metal has 8,270 triangles. The lower fold adds 520 ribbon triangles, changing 136 to 656. Complete garment totals are 21,838 Remembered and 28,375 Present, below the issue-specific 22,943/28,728 ceilings; the aged/clean ratio remains below 1.5. `medal-budget.json` records the allocation reason. No cloth reduction, performance-policy change or code-quality exemption was used.

## Runtime material routing

Only Medal surfaces 0/1 use `quarters_medal.gdshader`. Their state/role finishes are cached. Albedo uses `source_color`; normals use linear `hint_normal` sampling and positive-Z reconstruction from RG for BC5; ORM uses linear mipmapped sampling, R=AO, G=roughness, B=metallic. Imported channel selectors and identical packed pixel contents are asserted. Godot can supply distinct texture resource objects for the same packed pixels, so resource identity is not used as the packing test. Roughness/metallic multipliers remain one. Enamel has specular 0.5, coat 0.65 and coat roughness 0.13 Remembered/0.23 Present. Brass has no coat. Generic aged pigment/specular rules do not reach the medal.

RibbonFabric and every other part retain their former shader/bindings. TunicBody receives a separate opt-in contact finish rather than sharing it with facings. Its 512-square linear patch is AO(cloth+mounted metal)/AO(cloth), over 48 by 56 mm, with front-facing/depth coverage and a 3 mm bounded footprint. Albedo is not darkened. A PNG-origin correction maps the bottom-origin Blender patch to top-origin Godot sampling. The saved flipped-projection control fails visibility/locality; the corrected projection has zero measured LDR change outside the 3 mm bound. The baked ratio is exactly one outside its bound in both states.

Local direct-light AO influence is 0.75 Remembered and 0.35 Present. Starting at 0.35 produced only 2.4933% median crescent reduction on Remembered's larger clearance, so only that state's bounded contact influence was calibrated. This is an approximation for the existing shadowless rig. Medal seam AO influence remains 0.2. Room lights, exposure, cameras, ambient, probes and shadows were not changed. An ineffective medal specular-occlusion experiment was removed.

## Fixed-camera game measurements

Values are from tone-mapped PNGs decoded to linear Rec.709, not HDR radiance. Normalized differences use a 0.02 luminance floor. First-hit masks use prepared runtime wardrobe geometry, near clipping, instance-transform parity, culling and accepted feature labels. Contact distances are measured in the recorded cloth frame, not screen-space silhouette distance. Camera JSON matches the frozen baseline exactly.

| Gate | Remembered | Present | Target |
| --- | ---: | ---: | --- |
| Rim Y p95/p10 | 36.5533 | 14.4429 | ≥2 |
| Rim Y p95−p10 | 0.913581 | 0.897355 | ≥0.08 |
| Sectors with ≥2 px highlight and shadow bands | 35 | 35 | Distinct bands |
| Normal effect, rim | 35.2805% | 19.1683% | ≥3% |
| Normal effect, star wall/bevel | 8.3071% | 11.7823% | ≥3% |
| Bevel samples beside ≥2 px coherent normal-effect bands | 78.5068% | 76.8053% | ≥50% |
| Enamel full versus rough control | 62.1496% | 37.1364% | ≥2% |
| Contact crescent median reduction | 7.1756% | 6.4212% | 5–20% |
| Outside 3 mm, max LDR channel delta | 0 | 0 | ≤1/255 |
| Visible tarnish cavity/edge occupancy ratio | 15.4450 | 12.5418 | ≥2 for aged |
| Tarnish-off affected-region difference | 8.4669% | 97.3314% | ≥3% for aged |

Normal buffers differ. Flat/ignored/missing/swapped-normal binding controls and white-contact controls fail the corresponding effect test. Uniform tarnish has occupancy ratio one and fails spatial correlation. The deliberately misregistered contact control has zero median crescent response and an outside-bound LDR change of 0.035294/0.074510; it is retained under `tmp/issue130-photoreal/stage3/contact-flipped/`.

Probe-on/off response remains below 0.001% on the exposed medal, below the 1% target. Probe inventories record active quarters probes with mask 16, box projection and bounds covering the room. Mirror/refresh diagnostics establish population, but do not establish the ordinary material's required contribution. No global remedy or painted reflection was introduced.

The close-up projects the body to 484.58/498.11 pixels, with 195,344/204,854 visible metal pixels. Buttons/wardrobe project to 33.28/6.93 pixels Remembered and 33.77/6.98 Present, but first-hit metal coverage is zero behind the dresses. The buttons images are pixel-identical to the shipped baseline; Present wardrobe is also identical. Remembered wardrobe differs by more than one code value at one pixel. Do not infer scratch or bevel visibility at those occluded distances.

The 24-frame additional view arc uses common uncompressed, mipmapped ImageTexture normals for full, geometry-only and overstrong lanes. Above a 10% temporal-second-difference threshold, the full finish has 14/0 isolated spike samples, versus 874/44 for the overstrong control. This distinguishes the control but does not prove literal absence of every glitter pixel or reproduce production texture compression. Production embedded normals/ORM have mipmaps. CPU masks use the prepared mesh arrays; the renderer's selected LOD index is not exposed by this capture tool.

At least one RGB channel is ≥0.99 on 24.6483%/32.0561% of rim samples and 0.3811%/0.4709% of enamel samples. These clipped LDR samples limit highlight analysis. No tone-map or accepted texture was changed to suppress them. Existing power fade/off states are captured by switching game power state and advancing the room's existing fade, then restoring it. No new red fixture definition was introduced; a separate monochrome-red quarters lane is not supplied.

## Verification and delivery

The source and independent exported-triangle verifiers pass. They now freeze every non-Medal part, including Buttons and Placket, without the historical row-rebuild exemptions. All unrelated vertices, channels, UVs, textures, material signatures, pivots and geometry are exact. Saved-source exports reproduce both GLBs byte for byte. Exported axes are +Y up/+Z front.

Both GLBs and every medal-directory PNG were freshly imported. Their native `.md5` source hashes match the actual source before captures. Runtime provenance records effective shaders/maps, pixel hashes, UV channels, tangents, render layers, shadow flags and probe inventories. Its pixel hashes are hashes of the hex-encoded image buffer, not PNG file hashes.

Regression results: focused guarded Godot cohort 33 passed/0 failed; full guarded suite 1,013 passed/0 failed; tunic/detail/support/mount/attachment/aging/baked-color, contact negative cases and fixture-weather tests pass. Stage-two geometry/UV/texture-role verification passes; its recorded raw cage misses remain documented and were not relabeled as successful rays. No OCR was run, per Andrew 2026-10-09. Godot emits existing shutdown resource/RID leak diagnostics; there are no capture shader compilation errors. No uncontended frame-time result is claimed.

Raw PNGs, masks, controls and logs are under `tmp/issue130-photoreal/stage3/`. JPEGs are under `docs/art/quarters/sheets/medal/photoreal-stage3/`, at most 1400 pixels on either side. Tunic frames use the standard top-40-pixel protocol crop. Before/after sheets place shipped `ef57c29` left and mounted production right. Concept/studio/game sheets label their different lighting. `jpeg-paths.json` lists the exact 22 JPEG paths. Image stop C remains for the driver/image reviewer.

Saved-source export remains `build.py --output …` and `build.py --aged --output …`; do not use `--assemble`. `medal_mount.py --sources <frozen-baseline> --materials <stage2> --output <candidate>` rebuilds the mount. `medal_contact.py --sources <candidate> --output <medal-map-directory>` rebuilds contact. `verify_medal_mount.py` independently compares accepted source geometry and the contact ratio. `tools/run_tunic_tests.gd` inherits the ordinary child-process guard; it does not replace `tests/run_tests.gd`.
