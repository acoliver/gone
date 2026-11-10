# Ceiling seat rail: historical readability capture

This document records the earlier standalone capture at the obsolete Z=-1.2 failure station. Its profile, PBR and floor-pose evidence is retained, but its installed-context coordinates, PNGs, manifests and test counts are historical. Active proofs now fail at production Z=-0.6 and place the healthy central neighbor at Z=-1.2. See [corrected installation notes](stasis-wiring-production-installation.md) for current proof sources, fingerprints and verification.

The detachable component is the lower formed seat. Its source remains unchanged: 36 mm flat bearing, 42 mm overall width, 18 mm depth and 2.5 mm metal gauge. The separate 55 mm upper carrier stays intact. This supersedes the upper-carrier fracture proposal in `stasis-wiring-layout.md`.

The floor piece now rolls 115 degrees about the old rod's actual long axis. Its bay-local XZ center remains `(-0.6,-1.4)`. Translation Y is computed from transformed source vertices, not an approximate section box. Contact is Y=0; maximum height is 43.692789 mm. The unchanged 220 x 100 x 1150 mm world-space pickup proxy contains it, with 16.447 mm minimum X clearance, floor contact at the lower Y face, 56.307 mm overhead clearance, and 75.365 mm minimum Z clearance. Inverse-pose error is below `4e-16 m`.

## Prototype identities and materials

In the `StasisWiringProof/fault-frame-pair` subtree:

- `SeatRail_left/seat_rail_left` and `SeatRail_right/seat_rail_right` are individual imports from the unchanged left/right source GLBs, positioned at `(-0.6,2.988,-1.2)`. They replace the old grouped retained mesh, which is removed rather than drawn twice.
- `seat_healthy` contains the unchanged full-source neighbors. The labeled neighbor is centered at `(-0.6,2.988,-0.6)`.
- `fallen_fragment` is the same middle source under the measured floor pose. Only this mesh's baked position/normal buffer ranges changed.
- `steel_frame` is separate carrier/web/long-ledger context. It now uses the actual `BayCeiling._hardware_material()` resource: intact panel albedo/roughness textures, metallic 0.62, roughness 0.78. Other wiring materials are unchanged.

The actual baked frame has 28 components, zero duplicate bounds, no replaced flat cross-ledgers and one continuous upper carrier across the failure. Existing longitudinal ledgers remain. Accepted panel contact still has zero below-bearing intersections and nine flange contact samples.

## Captures and reproduction

Four deliverables are under `tmp/verify-stasis-wiring/seat-rail/readability/`: `shared-component-sheet.png`, `installed-seat-detail.png`, `fallen-stick-standing.png`, and `fracture-match-close.png`. The sheet uses one orthographic camera, scale and fixed light set for all three rows. The standing camera is `(-0.8,1.6,-2.65)`, 1.265899 m in plan from the original pickup center. Fracture inspection mates are separated 12 mm along their original axis.

`capture-manifest.json` records source mesh paths, surface triangle indices, camera projections, ray-verified visible object identities, final annotation pixels, camera poses and material references. Labels come from actual rendered-source surface points; the missing-piece outline projects the real middle source. Native mesh normals and material normal maps remain enabled as authored. Neutral inspection lighting exists only in this capture script.

Use `tools/build_seat_rail.py --floor-only` to update the baked floor pose without rebuilding the source component, `tools/capture_seat_rail_readability.gd` for native Godot readbacks, then `tools/compose_seat_rail_readability.py` for layout. Python checks need the existing 3D virtual environment. Five focused seat tests, two existing fault/contact regressions and five Godot wiring tests pass. Native Metal capture exits 0 without script errors.

The source meshes/PBR, original six proof PNGs and final housing SHA `4386c118...` are preserved. No production installation, global material/light edits, concept generation or model-body changes were made. Image-comparer review belongs to the parent agent; these checks do not claim a visual verdict.
