# Wall-mounted emergency lamps (#111)

The nineteen neutral emergency lamps that were pendants at `219a257` use weathered hatch cages on wall brackets. None uses a ceiling exception. Their `EmergencyFill` names preserve the circuit bindings. Every source remains inside visible glass, with no added light or ambient fill. The sixteen white beam fixtures, their assets, materials, textures, seating and source profiles are unchanged. Pod belts and their sources are unchanged.

## Why the bay needed another lighting pass

The first wall layout, `5a24c61`, passed the fixed incident-illumination grid while its bay overview fell from 52.9640 to 19.2251 mean display luma. The power overview lost 15.95%. The grid samples ninety architectural points equally, including walls outside the camera view. It does not model the surfaces visible between pods, material response or reflected light.

Before changing production code, the follow-up compared rendered-triangle camera rays and six individual source-off captures against `219a257`. The visible floor's mean direct incident proxy fell from 0.4147 to 0.0499, an 88% loss. The middle pair supplied 0.3491 units before the move and only 0.02636 afterwards. Moving the lamps from Z=±1.6 to Z=±3.8, reducing range to 4 m and reducing the central energy share to 0.10 left the centre floor outside useful throw. Stronger end lamps spent energy on nearby wall samples instead.

Both versions had shadows disabled, the same receiver masks, attenuation 1, exposure multiplier 2 and auto exposure disabled. Occlusion and exposure changes do not explain the discrepancy. The red strips are the installed pod status belts. The combined pod-only direct contribution remains 0.1596 in both versions; the belts stood out after neutral room light disappeared. Increasing their output would worsen the imbalance.

Local `tmp/emerg5/diagnosis.md` records the measurements, controls and limitations. `diagnose-baseline/` and `diagnose-wall/` retain the renders and 3,600 camera-ray records per scene. Those diagnostic tables use Rec.709-weighted RGB; the image regression below uses Pillow RGB-to-L, matching the review's display-luma convention.

## Positions and mounting

Coordinates are source centres in metres. Bay positions use its local frame; hall and power positions use ship-world coordinates. No positions change in this follow-up. All nineteen cages still face inward, with no drop into the walking lane.

| Space | Lamp indices | Positions |
|---|---|---|
| Bay | 0, 1 | (-4, 2.50, -3.8), (-4, 2.50, 3.8) |
| Bay | 2, 3 | (0, 2.50, -3.8), (0, 2.50, 3.8) |
| Bay | 4, 5 | (4, 2.50, -3.8), (4, 2.50, 3.8) |
| Hall | 0, 1 | (7.5, 2.36, 1.3), (10.5, 2.36, -1.3) |
| Hall | 2, 3 | (13.5, 2.36, 1.3), (16.5, 2.36, -1.3) |
| Hall | 4, 5, 6 | (19.5, 2.36, 1.3), (22.5, 2.36, -1.3), (25.5, 2.36, 1.3) |
| Power | 0, 1 | (24, 2.50, -1.9), (24, 2.50, -9.5) |
| Power | 2, 3 | (26, 2.50, -1.9), (27, 2.50, -9.5) |
| Power | 4, 5 | (30, 2.50, -1.9), (30, 2.50, -9.5) |

Hall cages sit below the side conduits with lower edges above 2.2 m. Bay and power cages sit below the pipe and sprinkler band. The power near-wall middle lamp stays at X=26 to clear the doorway, frame, labels and hatch services. Tests check complete fitting bounds against service, detector, hatch and door exclusions and require bracket contact with a structural wall. The unchanged ship-wide gate rejects any fixture extending more than 150 mm below a ceiling without wall contact. It still rejects a supported pendant and a 160 mm ceiling fitting and accepts 150 mm.

## Source profiles

The six backed bay cages now emit inward hemispheres: 90-degree SpotLight3D apertures without angular fade. They no longer illuminate the wall immediately behind their housings. The central pair throws across the visible room. The end pairs retain shorter reach. All six retain their source centres, glass, metalwork, neutral colour, attenuation 1, room-only mask, disabled shadows and existing fade clock. A shared level application keeps the omni and wall-aperture circuit behaviour together.

Energy shares multiply the unchanged 45/(4π) fixture energy.

| Space | Shares in lamp-index order | Ranges in metres |
|---|---|---|
| Bay | 2.35, 2.35, 0.56, 0.56, 0.01, 0.01 | 3, 3, 12, 12, 3, 3 |
| Hall | 0.71, 0.30, 0.42, 0.315, 0.315, 0.42, 0.30 | 4 for all seven |
| Power | 0.60 for all six | 4 for all six |

The power share rises from 0.58 to 0.60 to recover its overview while retaining the existing floor bound. Hall profiles and the existing emergency and white end practicals are unchanged. No fixture was added: the inventory remains 309 sources and 255 standalone housings. There is no GI, exposure adjustment, free fill source or beam/belt compensation.

## Regression checks

`tests/fixtures/overviews-219a257.json` fixes all ten standard overview reference lumas and camera poses. `tools/capture_fixture_views.gd` captures the same hall overview, hall eye-height, bay, power and connector views on both circuits at 1600×900, FOV 55 and 2× MSAA. It also captures every relocated cage close-up. `tools/check_fixture_overviews.py` checks every overview's full-image mean display luma within ±15%, rejects changed camera poses and dimensions, and fails on missing or duplicate views. Display luma is Pillow's 8-bit RGB-to-L conversion averaged over every pixel.

The new image test failed against `5a24c61` before the lighting implementation: bay -63.70%, power -15.95%. A separate GDScript regression failed on the missing inward aperture. Boundary tests reject values outside either side of the image limit. No threshold was loosened.

Run native captures and their image check from the project root:

```sh
godot --path . -s tools/capture_fixture_views.gd -- /absolute/path/to/captures
python tools/check_fixture_overviews.py /absolute/path/to/captures
FIXTURE_OVERVIEW_CAPTURES=/absolute/path/to/captures python -m unittest discover -s tests -p 'test_*.py'
```

The existing illuminance regression independently retains all 370 space/circuit rows against `217355c`, with ±10% limits for totals, floors, walls and ceilings. Only the three previously approved secondary-white ceiling exceptions remain. All 618 source/circuit observations must still pass emitter co-location. A new directional test requires inward emission, no throw behind a bay housing and direct contribution at the visible centre floor.


## Measured result

All ten overview images pass the fixed ±15% display-luma limit against `219a257`:

| Circuit / view | Reference luma | Final luma | Change |
|---|---:|---:|---:|
| Emergency / bay | 52.9640 | 58.7373 | +10.90% |
| Emergency / power | 35.7838 | 30.5659 | -14.58% |
| Emergency / hall eye-height | 44.7644 | 39.5286 | -11.70% |
| Emergency / hall overview | 44.3910 | 40.6447 | -8.44% |
| Emergency / connector | 33.0537 | 33.0596 | +0.02% |
| White / bay | 80.5903 | 74.0314 | -8.14% |
| White / power | 42.7201 | 42.3211 | -0.93% |
| White / hall eye-height | 39.5115 | 39.2813 | -0.58% |
| White / hall overview | 37.4494 | 37.1352 | -0.84% |
| White / connector | 33.0650 | 33.0650 | 0.00% |

The incident proxy independently passes all 370 space/circuit rows. All 618 source observations pass co-location, with maximum emitter separation 0.000003815 m. The affected room subtotals change as follows against `217355c`:

| Circuit / space | Total | Floor | Walls | Ceiling |
|---|---:|---:|---:|---:|
| Emergency / bay | -7.033% | -8.050% | -6.863% | -7.386% |
| Emergency / power | +0.818% | +9.400% | +0.833% | -4.813% |
| Emergency / hall | -7.515% | -3.046% | -9.368% | +1.574% |
| White / bay | -7.722% | -3.315% | -3.415% | -100.000% |
| White / power | -9.452% | -2.679% | -3.190% | -73.216% |
| White / hall | -8.696% | -2.691% | -1.888% | -92.422% |

Only the three existing white ceiling exceptions apply. Local `tmp/emerg5/illuminance.md`, `illuminance-summary.json` and `after.json` retain the full measurements. `tmp/emerg5/luma.json` records the image gate. `compare.jpg` contains 48 matched pairs: ten overviews and nineteen lamp close-ups on each circuit. PNGs and camera manifests are in `before/` and `after/`; `CAPTURES_READY` is present. These captures are not a visual-review verdict.

The final guarded run, without this worker's other suites, reports **859 passed, 0 failed**. Lighting-focused tests pass all 50 cases, including the new aperture test. The previous guarded run reported 858 passed and one failed native click-device test: free-cursor motion changed the view. That failed run and passing diagnostic input traces remain recorded in [#115](https://github.com/acoliver/gone/issues/115); its varying input and root cause remain unconfirmed. Neither the input code nor its assertion was changed. The final pass does not resolve that intermittent failure. The earlier run's obsolete OmniLight3D count was corrected to account explicitly for six SpotLight3D bay apertures without reducing the total-source assertion.

Fresh-capture Python verification passes all 32 tests, including the new image gate. All twelve Blender suites pass 78 tests. Native hatch colour checks pass; seal rendering reports 1,230 checks, 28,369,212 samples and zero green leaks. Collider counts remain 1,024 with both D14 doors closed, 1,023 with the bay open and 1,022 with both open, and 542 on each other deck. `git diff --check` passes. Renderer resource-cleanup warnings remain in the logs; successful native checks report no light/geometry unpair errors or signal-11 crashes. Review skipped per Andrew 2026-10-09.

All nine functional native lanes pass: calibration-move, calibration-step, click-route, connector-route, gameplay-full, gameplay-keyboard-turn, hallway, power-room and rod-pickup. The three negative controls, calibration-no-autoexposure, never-beat and white-without-handoff, fail as intended. These completed runs use `tmp/hatch-model/round8/run/run_visible.py` pointed at this worktree and remain recorded in `tmp/emerg5/native-results.json`.

## Performance under shared host load

The final batch runs the required AB/BA/AB comparison against `217355c`, with three repetitions per phase, 60 warm-up frames and 300 measured frames per repetition at 1152×648. All eighteen runs pass their native policies and all 5,400 measured frames are retained. There is no host-idle requirement or sample exclusion. The median paired mean-cost change is **-37.22%**, passing the unchanged limit of at most +10%. The first complete batch passed, so no repeat was needed.

| Pair / order | Baseline mean ms | Candidate mean ms | Cost change |
|---|---:|---:|---:|
| 1 / AB | 7.981860 | 5.011056 | -37.22% |
| 2 / BA | 16.708598 | 7.103142 | -57.49% |
| 3 / AB | 7.564140 | 16.723258 | +121.09% |

These measurements pass the paired budget under the observed workload; they do not establish a stable speed improvement. One-minute host load ranged from 7.52 to 25.29. Foreign workloads continued throughout, including the processes below. CPU is the highest observed value for an individual process, not a sum across the listed PIDs.

| Foreign process / workload | Observed PIDs | Peak process CPU |
|---|---|---:|
| Blender console asset builds in branch-2/wt-95p | 56994, 57154 | 1062.0% |
| Metal compiler services | 58318, 58320, 58407, 58408 | 553.7% |
| Rust builds and Clippy for worldrunner and UQM | 57146, 57883, 58165, 58430, 59455 | 347.3% |
| UQM native campaign automation | 29557 | 158.6% |
| Qwen llama-server | 97788 | 145.7% |
| MLX Z-Image generation | 57710, 58912 | 106.3% |
| LM Studio worker | 1247 | 100.0% |
| Foreign Godot guarded/native checks and routes in branch-2/wt-95 | 57447, 57909, 57917, 58024, 58274, 58275, 58278, 58282, 58291, 58292, 58306, 58757, 58773, 59312, 59316 | 100.0% |
| Hunyuan-environment prop finalization and queues | 23458, 37202, 43214, 48820, 49442, 54721, 54748, 54962, 56966, 56992, 57196, 57709, 83310 | 75.9% |

Complete foreign process snapshots, load averages, all run reports and per-repetition means remain in `tmp/emerg5/perf-current-load/`; `perf-final-summary.json` records the result. Earlier workers' logs and interrupted performance outputs remain untouched. Native work uses `tmp/emerg5/LANES_RUNNING` and waits only for the age/gi lane markers, without signalling foreign processes.
