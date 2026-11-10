# Issue 110: corrected production wiring

`ShipScene.build_into()` still installs one `StasisWiring.installation()` beneath `BayRoot`. The installation contains the production network and the separate source enclosure. It does not install a standalone proof, add a carrier grid, create cable physics, or change the collision inventory. The network retains eight material groups, including the released-core insulation.

The corrected evidence directory is `tmp/verify-stasis-wiring/production-corrected/`. Earlier `production-final/` captures and results describe the installation before the junction corrections. They are historical and must not be used to validate the current geometry. Appearance assessment belongs to the separate visual worker. No lighting, pod/lid pose, smoke, eye/wake timing or normal gameplay changes were made for screenshot appearance.

## Buried junctions now have open physical interfaces

The original continuous row buses crossed the branch jackets with their steel walls. All 72 entry, cross-bus and pod routes examined by the review reproduced that defect. The original probe results remain in `review/`; the finite-segment reproduction is `production-corrected/original-centerline-regression.json`.

The builders now declare the folded junctions before routing the pipes. Each pipe stops at the actual enclosure face, through a bounded opening. Its annular end remains hollow. Insulated jackets also end at these ports, and exported copper links connect their ends to shared terminal positions inside the enclosure. No continuous through-pipe wall remains across a branch. The compact data ring fans into ordered terminal levels; the route records retain the port-strand to terminal-strand mapping. Different terminal conductors have a positive clearance check.

There are 18 buried enclosures, 88 buried jacket routes, 224 internal conductor links and 72 connected strand-level junctions. The distribution boxes are 180×80×180 mm; pod takeoff boxes are 130×80×160 mm. Their reduced heights keep the power and lower data enclosures separate. Riser supports mount outboard of the pipe bore. Lower data-row hanger stations avoid the upper power crossing, with additional support stations maintaining the existing spacing limit.

`tools/stasis_wiring_ports.py` owns the manufactured pipe/jacket sections and terminal links. `stasis_wiring_installation_graph.py` requires every hidden junction endpoint to have all two power or six data terminal interfaces. Removing a physical strand interface now prevents graph generation. A connected axis graph alone is insufficient.

`tools/stasis_wiring_export_checks.py` reloads the transformed GLB outside Blender. It tests every buried exported jacket edge against actual pipe, box and support triangles, and performs the reciprocal wall-edge versus jacket-triangle tests. It also repeats the original centerline/steel probe, tests both reported common-interior points, checks exported connector occupancy and terminal contact against actual jacket/copper surfaces, and verifies shared terminal continuity. These checks do not exempt junction bounding boxes from foreign-wall collision testing.

## Overhead takeoff uses separate output ports

The source splice remains centered at `(-4.849006472,2.817588099,-3.1)`. Its enclosure is 150×100×260 mm. The +X wall has a 64 mm continuing-trunk aperture and a separate 72 mm takeoff aperture, with a real 10 mm steel partition between them. The takeoff begins 75 mm toward +Z from the trunk center. Two rigid internal copper links use separate height levels, so the split does not short the two poles or require an insulated jacket to make a zero-radius turn.

Both 24 mm power jackets and all six 6 mm data strands remain. The branch bend construction, clamps, source glands, wall entries and service reservations remain enforced. All four branch jackets are compared continuously against every continuing power/data jacket and the left-side feeds supplying the retained-end junction. Any permitted split overlap must fit inside the real enclosure interior, contracted by 3 mm sheet thickness plus the 12 mm jacket radius. The exported jacket/box-wall check and the two original closed-solid occupancy probes run as well.

The retained-end splice supplies the same four endpoints: left `(-1.15,2.82,-0.587)` and `(-1.15,2.82,-0.613)`, right `(-0.05,2.82,-0.613)` and `(-0.05,2.82,-0.587)`. The released leads, their 160 mm bends, three 4 mm copper exposures, sealed fourth end and existing tip-bound spark emitters are unchanged.

## Production coordinates and accepted seat remain unchanged

The source enclosure stays at `(-5.935,2.75,-3.1)`, yaw +90 degrees, with its rear mounting plane at X=-6. The 60 mm power floor crossing stays at `(-4.02,0,-3.93)` and the 25 mm data crossing at `(-4.18,0,-3.955)`. Buried power remains at Y=-0.55, with south/north bus Z=-3.35/1.85. Data remains at Y=-0.65, with bus Z=-3.47/1.73.

All seven native pod bases retain their terminals at `(pod_x-0.06,0.08,pod_z)` for power and `(pod_x+0.06,0.08,pod_z)` for data. The actual stationary-base containment tests, complete lid sweep, native fixture/service reservations, source socket fit, wall-drop gap and measured support contacts remain enforced.

The failed lower seat is `BayCeiling.FAILED_SEAT_CENTER=(-0.6,2.988,-0.6)`, beside the single empty panel cell `(4,4)`, centered at `(-0.6,2.99,-0.9)`. Active standalone retained seats, Python proof geometry, healthy neighbors, context checks, seat comparison captures, readability anchors and proof-camera targets now use that station. The healthy central neighbor is at Z=-1.2. The shared formed profile, PBR textures, source seat GLBs and accepted 115-degree floor pose were not rebuilt or changed.

The fault-frame and supported-transition GLB/BLEND proofs were rebuilt. Their current manifests contain matching source hashes. `refresh_stasis_wiring_proof_context.py` refreshes only the seat manifest's standalone-frame measurements and changed proof-source fingerprint after verifying the other 32 fingerprints. It records the earlier proof-source hash and the rebuilt context GLB hash. The previous manifests are preserved under `production-corrected/historical-manifests/`. Earlier proof/readability PNGs and their tmp manifests are historical; they do not depict the corrected proof station.

## Rebuilt export measurements

The current GLB has 802,716 triangles, 100 jacket routes and 330 measured contacts. Its bay-local bounds are `(-5.870,-0.690,-4.000)` to `(0.385,3.092500,2.626501)` metres. `build-results.json` and `exported-junction-collision-results.json` contain the full values.

| Measurement | Current result |
| --- | --- |
| Maximum measured support/contact gap | 0.0000287 mm |
| Minimum power/data centerline radius | 245.868 / 252.472 mm |
| Maximum support pitch | 683.935 mm |
| Wall-drop pod-side / complete lid-sweep clearance | 123.030 / 61.175 mm |
| Minimum hidden base-terminal margin | 22.000 mm |
| Buried jacket edges checked against exported walls | 494,880 |
| Pipe / enclosure / support intersections, including reciprocal wall edges | 0 / 0 / 0 |
| Maximum exported jacket-to-port / conductor-to-terminal gap | 0.000153 / 0.0000385 mm |
| Minimum clearance between different internal terminal conductors | 2.646 mm |
| Minimum exterior overhead branch-to-continuing-jacket clearance | 23.000 mm |

## Build, capture and readback binding

`build-snapshot.json` binds the implementation inputs, native context, source enclosure/sockets, seat/pod and other production prop assets, generated GLB/BLEND, finalized production manifest and semantic route JSON. The asset manifest records input hashes directly. The separate snapshot hashes the completed manifest and routes; neither output hashes the snapshot, avoiding a self-reference cycle.

`protected-before.json` and `protected-after-build.json` record unchanged inputs, including accepted seat/profile/PBR assets, source enclosure, pod/ceiling assets, runtime scene/gameplay/renderer sources and original test enforcement. Intended edits such as the wiring builders, proof placement and refreshed manifests are excluded from the unchanged baseline. The initial baseline and the additional unchanged app-source baseline are retained separately. These are preservation checks against the existing worktree, not claims about a clean-HEAD baseline.

The native capture verifies the build snapshot before loading `main.tscn`, checks that the imported scene's source/destination checksums match the current GLB and import resource, and fingerprints that actual imported resource. It records input/protected fingerprints before and after rendering and computes the preservation flags from those comparisons. A mismatch exits nonzero. Every PNG has a SHA-256 hash. The normal-opening result and actual frame readbacks are hashed in the capture manifest. The Python checker verifies these bindings before decoding the PNGs, and its report binds back to the capture manifest and verified snapshot.

The provenance regressions reject changed implementation/context/route/GLB inputs, changed PNG bytes, changed readback bytes and an input changed during capture. The native fingerprint probe accepts its unchanged fixture with exit 0 and rejects the deliberately mismatched fixture with exit 1. A build run also refused to certify its outputs after proof-camera and verifier sources changed while it was running; that exit-1 record is `build-stale-input-refused.log/.exit`. Final verification uses a source-stable rebuild.

## Reproduction

From the repository root, use the existing local Python environment and native Godot. Blender is invoked by the builders, authors the editable file in native Z-up and exports with `export_yup=True`; Trimesh verifies the exported +Y-up meshes.

```sh
PY=/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python
OUT=tmp/verify-stasis-wiring/production-corrected
mkdir -p "$OUT"
# Establish the unchanged-input baseline before rebuilding outputs.
"$PY" tools/stasis_wiring_provenance.py
# Dump production transforms with the native backend, not dummy MultiMeshes.
godot --path . -s tools/dump_stasis_wiring_context.gd -- tmp/verify-stasis-wiring/production-install/context.json
"$PY" tools/build_stasis_wiring.py
"$PY" tools/build_supported_transition.py
"$PY" tools/refresh_stasis_wiring_proof_context.py
"$PY" tools/build_stasis_wiring_production.py
godot --headless --editor --path . --import
"$PY" -m unittest discover -s tools -p 'test_stasis_wiring_*.py' -v
"$PY" -m unittest discover -s tools -p 'test_seat_rail.py' -v
godot --headless --path . -s tools/run_stasis_wiring_tests.gd
godot --headless --path . -s tools/run_seat_production_tests.gd
godot --path . -s tools/check_stasis_wiring_scene.gd
# Run long verification as a managed/nohup background job on this workstation.
godot --headless --path . -s tests/run_tests.gd
godot --path . -s tools/capture_stasis_wiring_production.gd
"$PY" tools/check_stasis_wiring_capture.py
git diff --check
```

`run-final-verification.sh` in the corrected output directory captures each command's complete stdout/stderr and actual exit status. It does not filter teardown errors or modify the original guarded runner. The full suite, focused tests, native checks and capture retain any ObjectDB/resource/RID or renderer-unpairing diagnostics.

## Completed verification

These results are from the source-stable corrected build. Each named log has a matching `.exit` file in `production-corrected/`.

| Check | Result | Log |
| --- | --- | --- |
| Native context dump | Exit 0 | `context.log` |
| Standalone fault / supported-transition rebuilds | Both exit 0 | `proof-build-final.log`, `transition-build-final.log` |
| Seat proof-context refresh | Exit 0; all 33 current source fingerprints match | `proof-context-refresh-final.log`, `proof-provenance-audit.json` |
| Production GLB/BLEND build and exported junction checks | Exit 0 | `build.log`, `exported-junction-collision-results.json` |
| Godot asset import | Exit 0 | `import.log` |
| Python wiring tests | 32 passed, exit 0, including the original 22 and 10 additions | `python-tests.log` |
| Python shared-seat tests | 6 passed, exit 0 | `seat-python.log` |
| Focused guarded Godot wiring tests | 19 passed, 0 failed, exit 0 | `godot-tests.log` |
| Guarded seat contracts | 42 passed, 0 failed, exit 0 | `seat-regression.log` |
| Native scene construction | 8 mesh groups, 7 pods, 1,024 colliders, 0 graph errors; exit 0 | `native-scene.log` |
| Original guarded full suite | 847 passed, 0 failed, exit 0 | `full-suite.log` |
| Native production capture and content-bound PNG readback | 6 ordinary + 10 diagnostic PNGs; both exit 0 | `capture.log`, `capture-readback.log` |
| Focused provenance mutations | 5 tests passed, exit 0 | `tamper-tests-final.log` |
| Native fingerprint fixture / deliberately wrong fingerprint | Valid exit 0; tampered exit 1 as required | `native-fingerprint-valid.log`, `native-fingerprint-tampered.log` |
| Whitespace check | Exit 0 | `diff-check.log` |

The completed build snapshot binds 352 input fingerprints and four output fingerprints. All 147 protected inputs matched before/after build and capture. The actual saved files were verified again after capture. `capture-manifest.json` includes every PNG hash and hashes for the normal-opening result and frame readbacks. `performance-readback.json` binds its measurements to that capture manifest and snapshot.

The normal opening reaches Standing through physical Space input, with zero direct power calls or teleports and all 1,024 colliders retained. Its six saved wake ticks are 112, 196, 280, 288, 305 and 348. Diagnostics start only after the ordinary Standing capture. The normal-opening result records 276 sampled frames.

Exit 0 does not mean teardown was clean. The focused run retains 93 leaked ObjectDB instances and four resources. The full suite retains 94,326 instances, 59 resources, RID/dependency and allocator diagnostics. Native scene/capture logs retain geometry/light unpairing, an unfreed particle shader and texture/material RID diagnostics. These reproduce the kinds recorded in the review; complete attribution remains unverified. No runner enforcement was changed to obtain these statuses.

## Capture interpretation

The first six PNGs follow the actual `main.tscn` camera through natural blink/open-eye/awake/get-up/standing states. Physical Space press/release passes through `Input.parse_input_event` and the existing player adapter. No direct power, phase or teleport calls occur in this ordinary leg.

Only afterward does the harness freeze main processing, hide the eye overlay for an inspection camera and advance the existing console circuit for white diagnostics. The remaining ten PNGs are explicitly labeled diagnostic. No lights or material overrides are added. The hallway view is a limited non-bay snapshot, not a paired appearance baseline.

Frame measurements include forced draws, scheduling and readback. Concurrent sibling jobs are recorded. No isolated performance or visual-appearance approval is claimed.
