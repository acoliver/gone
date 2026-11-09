# Wall-mounted emergency lamps (#111)

The nineteen neutral emergency lamps that were pendants at `219a257` now use the weathered hatch cage and its wall bracket. None uses a ceiling exception. Their node names retain `EmergencyFill` for the existing circuit bindings; every source is inside its visible glass, with no added source or ambient fill.

## Positions

Coordinates below are source centres in metres. The bay table uses the bay's local frame. Hall and power coordinates are ship-world coordinates. Each cage faces inward from the mounting wall.

| Space | Lamp indices | Positions |
| --- | --- | --- |
| Bay | 0, 1 | (-4, 2.50, -3.8), (-4, 2.50, 3.8) |
| Bay | 2, 3 | (0, 2.50, -3.8), (0, 2.50, 3.8) |
| Bay | 4, 5 | (4, 2.50, -3.8), (4, 2.50, 3.8) |
| Hall | 0, 1 | (7.5, 2.36, 1.3), (10.5, 2.36, -1.3) |
| Hall | 2, 3 | (13.5, 2.36, 1.3), (16.5, 2.36, -1.3) |
| Hall | 4, 5, 6 | (19.5, 2.36, 1.3), (22.5, 2.36, -1.3), (25.5, 2.36, 1.3) |
| Power | 0, 1 | (24, 2.50, -1.9), (24, 2.50, -9.5) |
| Power | 2, 3 | (26, 2.50, -1.9), (27, 2.50, -9.5) |
| Power | 4, 5 | (30, 2.50, -1.9), (30, 2.50, -9.5) |

Hall cages sit below the continuous side conduit, away from the overhead pipe and duct band. Their lower edge is above 2.2 m. The power-room near-wall middle lamp moves to X=26 to clear the door, frame, labels and hatch-service envelope. Bay and power cages sit below the fire pipe and sprinkler band. Tests check each complete relocated housing against the authored service, detector, door and hatch exclusions, and require physical bracket contact with a structural wall.

The existing side cages also lose their redundant ceiling stems. Remote connector cages use horizontal wall brackets, including side-wall brackets for the low landing keys. Those sources retain their positions, energies, ranges and falloff. No beam geometry, seating, material or texture changes are part of this follow-up.

The earlier power-room ceiling measurement at Y=3.188 m hit `EmergencyFill0/Steel`, specifically its ceiling plate. Triangle probes against `219a257` identify that mesh; filtering for the architectural ceiling instead hits `PowerCeiling` at Y=3.200 m before and after this change. The beam test now excludes fixture hardware from its ceiling rays and retains exact contact checks. The reported 12 mm ceiling-skin overlap was a measurement error.

## Source profiles

All nineteen relocated lamps use the original 4.0 m range, removing the 4.2 m pendant compensation. Energy shares below multiply the unchanged emergency fixture energy, 45 / (4π). Colours, attenuation, masks, shadow policy and circuit fades remain unchanged.

| Space | Shares in lamp-index order |
| --- | --- |
| Bay | 1.435, 1.435, 0.10, 0.10, 1.435, 1.435 |
| Hall | 0.71, 0.30, 0.42, 0.315, 0.315, 0.42, 0.30 |
| Power | 0.58 for all six |

A uniform bay share at the wall loses floor and ceiling incidence before it restores the wall subtotal. Stronger end stations and weaker middle stations meet all three unchanged panel bounds without increasing range. The hall likewise needs station-specific shares to restore its wall subtotal without exceeding its floor or ceiling bound. The power-room share restores floor and ceiling reach at the wall. Only these nineteen moved sources change energy.

The regular white end practical retains its 0.24 share. Restoring 0.12 would leave the hall total 11.66% below `217355c`. Relocating emergency sources cannot compensate for that loss because those sources are off in the white circuit.

## Measurement and regression coverage

The fixed inventory still covers 185 spaces in each circuit. Every total, floor and wall subtotal remains within ±10% of `217355c`; the unchanged secondary-white bay, power and hall ceiling exceptions still apply. Local measurements and the complete inventory are under `tmp/emerg4/`.

| Circuit / space | Total change | Floor change | Wall change | Ceiling change |
| --- | ---: | ---: | ---: | ---: |
| emergency / bay | +5.46% | -8.52% | +9.53% | -9.45% |
| emergency / hall | -7.52% | -3.05% | -9.37% | +1.57% |
| emergency / power | +0.70% | +5.75% | +0.75% | -7.65% |
| white / bay | -7.72% | -3.31% | -3.42% | -100.00% |
| white / hall | -8.70% | -2.69% | -1.89% | -92.42% |
| white / power | -9.45% | -2.68% | -3.19% | -73.22% |

`light_mounting_test.gd` checks 255 standalone housings across the ship, including all remote connectors, using individual fitting bounds and structural wall boxes rather than a mounting label. A fixture without wall contact must remain within 150 mm of its ceiling. Negative controls reject the old suspended layout and a 160 mm ceiling fixture, while accepting a 150 mm fixture and real wall contact. The new tests failed against the pendants before relocation. Existing co-location tests still check all 309 sources in both circuit states.

Captures compare `219a257` with the wall mounts. Hall, bay, power and connector overviews and the eye-height hall view retain fixed cameras in both circuits. Each of the nineteen lamp close-ups follows its source so its mounting is visible. `tmp/emerg4/compare.jpg` contains all 48 before/after pairs; the matching PNGs and camera manifests are in `before/` and `after/`. Captures do not constitute a visual-review verdict.

The guarded Godot suite passes 858 tests; Python passes 29; the twelve Blender suites pass 78. D14 collider counts remain 1024 with both doors closed, 1023 with the bay open and 1022 with both open. Every other deck retains 542 colliders. All nine native functional lanes pass, and all three negative controls fail as intended. Native hatch colour and seal-render checks also pass. Native runs use `tmp/hatch-model/round8/run/run_visible.py` pointed at this worktree, after waiting for the ageing lane marker.

Performance uses the fixed AB/BA/AB schedule against `217355c`, with three repetitions per phase, 60 warm-up frames and 300 measured frames per repetition at 1152 × 648. All 5400 measured frames are retained. The median paired mean-cost change is **+3.40%**, within the unchanged +10% limit.

| Pair / order | Baseline mean ms | Candidate mean ms | Cost change |
| --- | ---: | ---: | ---: |
| 1 / AB | 2.964771 | 2.430434 | -18.02% |
| 2 / BA | 2.351890 | 2.694896 | +14.58% |
| 3 / AB | 2.442006 | 2.524914 | +3.40% |

The first batch measured +12.25% but failed the quiet-host gate when an external guarded suite and import overlapped sampling. That batch remains in `perf-contaminated-summary.json` with its original logs and host trace. No source changes or sample exclusions separate the batches. The accepted batch under `perf-isolated/` waits for external Godot work and local inference to become idle, monitors both throughout sampling, and passes the quiet-host gate. `perf-summary.json` records the accepted result.
