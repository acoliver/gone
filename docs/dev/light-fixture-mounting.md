# Consolidated wall fixtures (#111)

## Merged with main 1aeb2a4

Main adds the standing consoles and live status board, protected stasis wiring, a formed ceiling seat and lower generator-band emission. Those assets, screen transforms, wiring routes, spark-tip positions and the 0.24 generator material emission remain as main authored them. Main adds no Light3D sources. Its displays remain visible surfaces in their housings; they add no ambient or fill lighting.

The textual conflict in `emergency_fill_test.gd` keeps main's two-argument `ShipScene.build_into` API and this branch's nine bay emergency keys: eight mirrored wall cages plus the hatch key. The beam mounting test also drops the retired wiring argument. Main's bay beam stations remain at local X=-4.2, -0.6 and 4.2 m, Z=±1.5 m. Imported housings still meet the slab at Y=3.2 m, with each source seated at its glass.

The ceiling integration previously reserved the removed pendant lenses and stems. Removing those obsolete reservations restores two ordinary panels, leaving 113 panels and six beam cassettes across the same 119 non-failed cells. The formed seat source, missing seat, failure location and protected wiring remain unchanged. Exact geometry tests now measure the stem-free layout: 129 cross-seat spans, three cached source meshes, 1,161 gauge rays, 7,667 panel-bearing samples and 24 cassette-edge contacts. All clearance, contact and dimensional tolerances remain unchanged. The wiring test now checks the existing three spark groups for one light, one spray and the visible arc required by #111, instead of rejecting that arc as a third child.

### Main's baseline drift

Plain main was measured with the same inventory code before any retuning. Of 370 space/circuit rows, only these two changed; all 185 emergency rows and the other 183 white rows are unchanged. Values are renderer-proxy units. The complete per-space table is in `tmp/sync/main-drift.md` and its numeric form is in `tmp/sync/main-drift.json`.

| Space and circuit | Total before → main | Floor before → main | Ceiling before → main | Walls before → main |
|---|---:|---:|---:|---:|
| White bay | 60.241950 → 60.163235 (-0.131%) | 13.660420 → 13.278352 (-2.797%) | 2.700538 → 2.688465 (-0.447%) | 43.880993 → 44.196417 (+0.719%) |
| White D14-S-041 | 46.228707 → 46.590436 (+0.782%) | 9.887813 → 10.040320 (+1.542%) | 3.388807 → 3.411179 (+0.660%) | 32.952087 → 33.138937 (+0.567%) |

The illuminance fixture is regenerated from plain `1aeb2a4` as `illuminance-1aeb2a4.json`. The 10% limit and the same three white-ceiling exceptions are unchanged.

Only bay and power overview references are refreshed, using scratch `219a257` with main merged in. The reference retains the original emergency fixture layout; the removed `Lighting.LENS_SIZE` constant is represented by its original 0.42 × 0.16 × 0.12 m value in that scratch merge. The six hall/connector reference values, all ten cameras, resolution, FOV and the 15% limit remain unchanged. The mixed reference is `overviews-219a257-main-1aeb2a4.json`.

| Changed overview | Original 219a257 luma | Main-merged reference luma | Drift |
|---|---:|---:|---:|
| Emergency bay | 52.964048 | 63.109877 | +19.156% |
| White bay | 80.590340 | 52.335891 | -35.059% |
| Emergency power | 35.783815 | 37.556665 | +4.954% |
| White power | 42.720111 | 42.661029 | -0.138% |

These overview differences include capture-input normalization as well as main's content. Unlike the deterministic incident proxy, the old bay capture left the smoke seed and animation time uncontrolled. The first merged bay image measured 48.7377 against an uncontrolled 59.3791 reference. A constrained tuning trial then measured 52.2000 in one capture and 44.3463 in another with the same lamp settings, so those images could not establish a lighting change.

The capture tool now retains all 144 smoke particles and the production seven-second preprocessing, sets particle seed 91, warms for 30 frames and freezes the particle transforms and shader time using the project's existing `pod_captures.gd` pattern. Captures use `--fixed-fps 60`. The four main-changed references use these same inputs; the other six numeric references remain untouched. Repeated controlled captures reproduce the bay images byte for byte. The original, untuned profile passes all ten views: emergency bay 66.9335 versus 63.1099 (+6.06%), white bay 52.1733 versus 52.3359 (-0.31%). The tuning trial is discarded. The integration retains #111's fixture profiles and energy budget, with no additional material-output change.

The first guarded run recorded 895 passes and two failures. One was the stale two-child spark assertion described above. The unchanged lift-writing native check reported a Metal fence timeout rather than a gameplay assertion; the same check subsequently passed on both plain main and the merged tree. The original failure log is retained at `tmp/sync/111/guarded-first.log`.

### Verification after integration

The final guarded suite ran alone among this worker's verification jobs and passed 897 tests with zero failures. Python passed 32 tests, including all ten saved overview views. The eight offline tool modules passed 44 tests with a freshly dumped native wiring context. They run in separate interpreters because the ceiling-bake importer prepends the Blender directory and otherwise shadows the Python seat module. Thirteen Blender suites passed 87 tests; the separate enclosure hardware geometry contract also passed. Protected wiring provenance was not rewritten.

All 572 light observations have valid housed emitters, with maximum gap 0.000003815 m. The two circuit inventories contain the same 240 standalone fixtures, with zero close wall pairs and zero live-lamp glow failures. All 370 incident-light rows pass. Collider counts match plain main exactly: D14 has 1,024 closed, 1,023 with the bay open and 1,022 with both doors open; every other deck has 542.

All nine native functional machine lanes pass: calibration-move, calibration-step, click-route, connector-route, gameplay-full, gameplay-keyboard-turn, hallway, power-room and rod-pickup. The three negative controls fail for their intended assertions: exposure does not converge with adaptation disabled, the requested beat exceeds the deadline, and emergency lenses remain lit without a handoff. Native colour checks pass. Seal rendering passes 1,230 checks over 28,369,212 samples with zero green leaks. The current verification logs contain zero light/geometry pairing errors.

The complete AB/BA/AB comparison against plain main retains all eighteen runs and 5,400 measured frames. Every phase has three repetitions with 60 warm-up and 300 measured frames at 1152×648. There is no idle wait, load gate or discarded phase.

| Pair / order | Main phase mean ms | Merged phase mean ms | Change |
|---|---:|---:|---:|
| 1 / AB | 12.495999 | 3.249608 | -73.995% |
| 2 / BA | 2.985187 | 2.872340 | -3.780% |
| 3 / AB | 2.940069 | 2.747401 | -6.553% |

Median paired cost is -6.553%, passing the unchanged +10% limit. One-minute host load spans 5.61–9.33. The first baseline phase is much slower than the later phases; these shared-load measurements do not establish a stable speed improvement. Raw results and host snapshots are in `tmp/sync/111/perf/`.

Sixteen final captures and their manifest are in `tmp/sync/111/`: the ten fixed views and west, east and north power-room wall rows in both circuits, including main's consoles. `CAPTURES_READY` marks the completed set. They are quantitative capture evidence, not an independent visual-review verdict. Both the requested working-tree `git diff --check` and the complete PR diff against `origin/main` pass. The broader first-parent diff includes whitespace already present in main's unchanged vendor text; those files are preserved. Review skipped per Andrew 2026-10-09.

The sections below record the earlier branch states and their original baselines.

## Mirrored bay rows after 4797e81

The bay wall cages now belong to the room layout rather than the seven-pod registry. Each long wall has four cages at world Z=3.2, 6.2, 9.2 and 12.2 m, on a 3 m pitch at Y=2.5 m. West source centres are at X=11.1 m and east centres at X=18.9 m. The rows mirror across X=15 m. Their housings clear the services and hatch exclusions, and remain above the standing envelope.

All eight row cages use one profile: 2.48 shares, 7 m range and 2.479420 attenuation. They share the same lens emission and colour mixture. There is no second row group. The existing bay-side hatch lamp stays at (15, 2.56, 2.01) m with two shares; its range becomes 10.449859 m and attenuation 1.134204. Retuning that doorway source preserves spill into the hall without changing a hall or power-room fixture. The total bay budget remains 21.84 shares. The long rows no longer inherit different throws and shares from former per-pod channels.

| Wall | X | Y | Z stations | Share per cage | Range | Attenuation |
|---|---:|---:|---|---:|---:|---:|
| West | 11.1 | 2.5 | 3.2, 6.2, 9.2, 12.2 | 2.48 | 7.0 | 2.479420 |
| East | 18.9 | 2.5 | 3.2, 6.2, 9.2, 12.2 | 2.48 | 7.0 | 2.479420 |

The bay now has nine emergency wall fixtures, including its existing hatch lamp, and six unchanged ceiling beams. The whole ship has 240 standalone fixtures: 224 wall cages and 16 ceiling beams. There are 286 sources, including machinery, status belts and sparks, or 572 observations over both circuit states. Each standalone fixture still contains exactly one source. All observations have a housed, co-located emitter. The existing spacing and glow gates report no failures.

| Bay circuit | Total versus 217355c | Floor | Walls | Ceiling |
|---|---:|---:|---:|---:|
| Emergency | +3.419% | +1.182% | +5.808% | -9.000% |
| Secondary white | -7.722% | -3.315% | -3.415% | -100.000% (existing exception) |

All 370 space/circuit rows pass the unchanged incident-light checks. The original three secondary-white ceiling exceptions remain the only exceptions. No reference, tolerance, glow ratio or mounting threshold changes.

All ten fixed overview captures also pass the unchanged 219a257 display-luma checker. Bay emergency luma is 48.1064 versus 52.9640 (-9.17%); bay white luma is 73.5184 versus 80.5903 (-8.78%). The hall overview remains within its limit at 37.8545 versus 44.3910 (-14.72%).

The first 9.973076 m row profile failed two AB/BA/AB batches, with median paired costs of +66.63% and +10.88%. A range-only native control repeatedly measured lower wall-frame time at 6 m than at 9.973076 m, while script CPU time stayed below 0.1 ms and GPU timestamps were unavailable. The final 7 m profile limits the affected volume while retaining all illumination and image limits. Its full AB/BA/AB batch against 217355c measures -7.66%, +6.59% and -6.67%, for a median paired cost of -6.67%, passing the unchanged +10% limit. Each phase has three repetitions, 60 warm-up frames and 300 measured frames at 1152×648. All eighteen runs and 5,400 measured frames are retained. One-minute host load spans 6.87–8.69; there was no idle wait or idle gate. Both failed designs and the final results remain in `tmp/emerg7/perf-final-summary.json`. Shared-load measurements do not establish a stable speed improvement.

The new bay-row regression failed on 4797e81 before production changes: four west cages versus three east cages. It now checks both circuit inventories for mirrored positions, a single mounting height, uniform spacing within 3 cm, and no more than two symmetric share/range/falloff groups. Exact layout pins also cover all eight wall stations. The existing one-third-median glow rule remains unchanged.

The final guarded suite ran without concurrent tests owned by this worker and passed 867 tests, with zero failures. Python passed 32. All twelve Blender suites passed 78 tests; their asset and exported-hatch inputs are unchanged by the final range-only tuning. All 672 pod-head/lid clearance checks pass. Collider counts remain 1,024 on D14 with doors closed, 1,023 with the bay open and 1,022 with both doors open, and 542 on every other deck. `git diff --check` passes.

All nine native functional lanes pass through `tools/run_visible.py` pointed at this worktree. The three negative controls fail as intended. Native hatch colour and Python-native checks pass. Seal rendering passes 1,230 checks over 28,369,212 samples with zero green leaks. Native checks report zero light/geometry pairing errors and no signal-11 crashes. Renderer cleanup warnings remain in the logs. Review skipped per Andrew 2026-10-09.

Local `tmp/emerg7/compare.jpg` contains eight matched before/after bay pairs against 4797e81: overview, west row, east row and doorway, each in emergency and white circuits. Camera manifests and full-resolution PNGs are in `before/` and `after/`; `CAPTURES_READY` marks the completed set. Only bay emergency wall lighting and its tests change. Beam assets, seating, pod placement, hall and power-room fixtures remain unchanged.

## Earlier consolidation at 4797e81

The following records the preceding consolidation and its measurements before the mirrored bay follow-up.

The wall relocation at `49f9127` put neutral cages beside the original emergency keys. Bay keys were also only 1.4 m apart, and two added bay sources had shares of 0.01. Removing the added cages alone would have left the original bay row below the requested spacing.

Six bay cages, seven hall cages and three far-wall power cages are removed. Their output is folded into the existing keys. The eight pod-only bay channels also share those keys instead of adding a second source in each cage. Every standalone cage and beam now has exactly one source. The ship changes from 255 to 239 standalone fixtures and from 309 to 285 sources. The other 196 fixtures are unchanged.

## Energy and visible glow

Shares multiply the unchanged 45/(4π) energy unit. Merging sums energy and blends source colours in linear RGB. The bay retains eight red shares, eight pod shares and all 5.84 neutral shares, totalling 21.84. Hall output remains 11.62 shares, including its retained 0.84 end practical. Power output remains 9.6 shares. `app/emergency_fixture_profile.gd` records the consolidated shares, throw and falloff at each station.

A live lamp must have at least one third of the median live share in its room and circuit. Circuit state determines whether a lamp is live. Independent section and connector lamps are always live; the three switched spaces follow the emergency/white handoff. Zero-output lamps on either kind of live circuit fail too. The white hall end practical rises from 0.24 to 0.36 of regular-fixture energy, putting its absolute share at 0.198 beside the unchanged 0.55 beams. This changes no beam source, asset, texture, material or seating.

Bay cages move down to Y=2.5 m to clear the service band. Their four-lamp row uses a 3.2 m pitch; the opposite three-lamp row uses 4 m. Hall keeps its original stations and integrated hatch cages. Power keeps its original side and far-wall keys; its three distinct near-wall cages use X=24, 26 and 28 m at a 2 m pitch. Full housing bounds clear services and hatch exclusions. The existing ship-wide mounting gate still rejects ceiling drops over 150 mm without wall contact. Walking lanes, pods and generator geometry are unchanged.

No source is detached from its emitter, and no ambient or GI fill is added. Status belts and their local samples are unchanged. Emergency handoff and blackout still use the existing fade clock. Consolidated bay keys now serve the architecture and pod receiver channels from one source. Source colour and range therefore cannot retain two different receiver-specific profiles; the fixed room and image checks constrain the combined result.

## Layout


Counts include wall cages and white ceiling beams, excluding status belts, machinery rings and spark arcs. Positions below are world source centres. The full before/after inventories contain circuit, shares and ranges for every deck.

| Space | Before | After |
|---|---:|---:|
| D14-BAY | 20 | 14 |
| D14-S-041 | 21 | 14 |
| D14-POWER | 18 | 15 |

## D14-BAY: Before
- WEST: (11.1, 2.65, 12.5), (11.1, 2.65, 11.1), (11.1, 2.65, 9.7), (11.1, 2.65, 8.3), (11.2, 2.5, 11.7), (11.2, 2.5, 7.7), (11.2, 2.5, 3.7)
- EAST: (18.9, 2.65, 9.7), (18.9, 2.65, 11.1), (18.9, 2.65, 12.5), (18.8, 2.5, 11.7), (18.8, 2.5, 7.7), (18.8, 2.5, 3.7)
- PORT: (15.0, 2.56, 2.01)
- CEILING: (13.607, 3.115, 11.7), (16.393, 3.115, 11.7), (13.607, 3.115, 7.7), (16.393, 3.115, 7.7), (13.607, 3.115, 3.7), (16.393, 3.115, 3.7)

## D14-BAY: After
- WEST: (11.1, 2.5, 12.5), (11.1, 2.5, 9.3), (11.1, 2.5, 6.1), (11.1, 2.5, 2.9)
- EAST: (18.9, 2.5, 11.7), (18.9, 2.5, 7.7), (18.9, 2.5, 3.7)
- PORT: (15.0, 2.56, 2.01)
- CEILING: (13.607, 3.115, 11.7), (16.393, 3.115, 11.7), (13.607, 3.115, 7.7), (16.393, 3.115, 7.7), (13.607, 3.115, 3.7), (16.393, 3.115, 3.7)

## D14-S-041: Before
- WEST: (6.51, 2.56, 0.99)
- EAST: (29.69, 2.56, -0.99)
- PORT: (9.0, 2.65, -1.3), (15.0, 2.65, -1.3), (21.0, 2.65, -1.3), (10.5, 2.36, -1.3), (16.5, 2.36, -1.3), (22.5, 2.36, -1.3), (29.1, 1.7, -1.3)
- STARBOARD: (15.99, 2.56, 1.19), (21.0, 2.65, 1.3), (27.0, 2.65, 1.3), (7.5, 2.36, 1.3), (13.5, 2.36, 1.3), (19.5, 2.36, 1.3), (25.5, 2.36, 1.3), (29.1, 1.7, 1.3)
- CEILING: (9.0, 3.115, 0.0), (15.0, 3.115, 0.0), (21.0, 3.115, 0.0), (27.0, 3.115, 0.0)

## D14-S-041: After
- WEST: (6.51, 2.56, 0.99)
- EAST: (29.69, 2.56, -0.99)
- PORT: (9.0, 2.65, -1.3), (15.0, 2.65, -1.3), (21.0, 2.65, -1.3), (29.1, 1.7, -1.3)
- STARBOARD: (15.99, 2.56, 1.19), (21.0, 2.65, 1.3), (27.0, 2.65, 1.3), (29.1, 1.7, 1.3)
- CEILING: (9.0, 3.115, 0.0), (15.0, 3.115, 0.0), (21.0, 3.115, 0.0), (27.0, 3.115, 0.0)

## D14-POWER: Before
- WEST: (21.1, 2.65, -3.7), (21.1, 2.65, -7.5)
- EAST: (32.9, 2.65, -3.7), (32.9, 2.65, -7.5)
- PORT: (24.5, 2.65, -9.6), (29.5, 2.65, -9.6), (24.0, 2.5, -9.5), (27.0, 2.5, -9.5), (30.0, 2.5, -9.5)
- STARBOARD: (24.0, 2.5, -1.9), (26.0, 2.5, -1.9), (30.0, 2.5, -1.9)
- CEILING: (24.0, 3.115, -3.7), (24.0, 3.115, -7.7), (27.0, 3.115, -3.7), (27.0, 3.115, -7.7), (30.0, 3.115, -3.7), (30.0, 3.115, -7.7)

## D14-POWER: After
- WEST: (21.1, 2.65, -3.7), (21.1, 2.65, -7.5)
- EAST: (32.9, 2.65, -3.7), (32.9, 2.65, -7.5)
- PORT: (24.5, 2.65, -9.6), (29.5, 2.65, -9.6)
- STARBOARD: (24.0, 2.5, -1.9), (26.0, 2.5, -1.9), (28.0, 2.5, -1.9)
- CEILING: (24.0, 3.115, -3.7), (24.0, 3.115, -7.7), (27.0, 3.115, -3.7), (27.0, 3.115, -7.7), (30.0, 3.115, -3.7), (30.0, 3.115, -7.7)

The other 196 fixtures are unchanged: three per connector on every deck, plus sixteen cages in the two independent D14 outer sections. The ship total changes from 255 to 239 standalone fixtures and from 309 to 285 sources. Bay row pitch is 3.2 m on the four-lamp wall and 4 m on the three-lamp wall. Hall original stations and integrated hatch lamps remain. Power near-wall pitch is 2 m; its far-wall duplicates are folded into the original X=24.5 and X=29.5 keys.

## Regression coverage

The spacing and glow tests failed on `49f9127` before production changes. They cover both circuit states and every deck represented by the ship inventory. Shared receiver channels are grouped by physical emitter for the baseline comparison; the new single-source assertion also rejects multiple sources in one standalone fixture. Exactly 1.5 m fails the spacing rule. A share exactly one third of the median passes; smaller shares and zero-output live lamps fail.

The original illuminance reference and its ±10% check remain unchanged, including only the three existing secondary-white ceiling exceptions. The original ten overview references, poses, dimensions and ±15% checker also remain unchanged. Range and attenuation fitting uses actual mounted positions and camera-visible triangles as well as the fixed incident grid. Power-room camera rays include the generator instead of treating the visible room as an empty box.


The fixed 217355c reference and ±10% checks are unchanged. Only the three existing secondary-white ceiling exceptions apply.

| Circuit / space | Total | Floor | Walls | Ceiling |
|---|---:|---:|---:|---:|
| emergency/D14-BAY | -0.254% | +8.500% | -2.701% | +8.500% |
| emergency/D14-POWER | +8.392% | +6.040% | +8.500% | -1.624% |
| emergency/D14-S-041 | +6.288% | +7.198% | +7.316% | -0.477% |
| secondary-white/D14-BAY | -7.722% | -3.315% | -3.415% | -100.000% |
| secondary-white/D14-POWER | -9.452% | -2.679% | -3.190% | -73.216% |
| secondary-white/D14-S-041 | -5.734% | -1.596% | +1.593% | -89.054% |

All 370 rows pass. All 570 source observations are housed and co-located; maximum gap 0.000003815 m.

## Overview display luma

| View | Reference | Consolidated | Change |
|---|---:|---:|---:|
| emergency-hall-overview | 44.3910 | 38.5202 | -13.23% |
| emergency-hall-eye-height | 44.7644 | 39.4991 | -11.76% |
| emergency-bay-overview | 52.9640 | 51.9069 | -2.00% |
| emergency-power-overview | 35.7838 | 31.3530 | -12.38% |
| emergency-connector-overview | 33.0537 | 33.0667 | +0.04% |
| white-hall-overview | 37.4494 | 37.1532 | -0.79% |
| white-hall-eye-height | 39.5115 | 39.2824 | -0.58% |
| white-bay-overview | 80.5903 | 80.7322 | +0.18% |
| white-power-overview | 42.7201 | 42.2390 | -1.13% |
| white-connector-overview | 33.0650 | 33.0650 | +0.00% |

Local `tmp/emerg6/inventory.md` contains the complete before/after fixture inventory, close pairs and dim-lamp findings. `fixture-table.md`, `illuminance-summary.json` and `luma.json` retain the measurements. `compare.jpg` pairs 22 matched views against `49f9127`, with ten overviews and each long bay, hall and power wall on both circuits. The power wall cameras sit between the wall and generator so the column cannot hide the lamp row. Individual PNGs and camera manifests are under `before/` and `after/`, and `CAPTURES_READY` is present. These files record captures, not an independent visual-review verdict.

## Verification

The final guarded suite ran alone and passed 866 tests with zero failures. The focused run passed 47; Python passed 32 tests, and all twelve Blender suites passed 78. The new spacing and glow tests ran red on `49f9127`. A further zero-output always-on regression ran red before the circuit classification fix. The earlier full run's six failures were obsolete height, colour, energy, range and fixture-selector expectations; their replacements test the consolidated profiles without changing tolerances. The intermediate 865-test pass and the failed logs remain under `tmp/emerg6/`.

All nine functional native lanes pass through `tools/run_visible.py` pointed at this worktree: calibration-move, calibration-step, click-route, connector-route, gameplay-full, gameplay-keyboard-turn, hallway, power-room, rod-pickup. The three negative controls fail as intended: calibration-no-autoexposure, never-beat, white-without-handoff. Native hatch colour, Python-native checks and seal rendering pass. Successful native checks report zero light/geometry pairing errors and no signal-11 crashes. Renderer cleanup warnings remain in the logs. Review skipped per Andrew 2026-10-09.

Collider counts remain D14 1,024 closed, 1,023 with the bay open and 1,022 with both doors open, and 542 on every other deck. `git diff --check` passes. No beam asset, texture, material, source profile or seating changed, and only the assigned lighting worktree was edited.

## Performance under shared host load

AB/BA/AB against `217355c` uses three repetitions per phase, 60 warm-up frames and 300 measured frames per repetition at 1152×648. All eighteen runs pass and all 5,400 measured frames are retained. Median paired mean cost is -15.86%, passing the unchanged limit of at most +10%. No idle wait or idle gate was used. The shared-load variance does not establish a stable speed improvement.

| Pair / order | Baseline mean ms | Candidate mean ms | Change |
|---|---:|---:|---:|
| 1 / AB | 4.713997 | 2.213084 | -53.05% |
| 2 / BA | 2.506791 | 2.109319 | -15.86% |
| 3 / AB | 6.960919 | 8.343730 | +19.87% |

One-minute host load ranged from 9.27 to 13.65 across 51 recorded snapshots. Per-run reports and foreign-process snapshots remain under local `tmp/emerg6/perf-current-load/`; `perf-final-summary.json` records the complete first batch. No samples or phases were discarded.
