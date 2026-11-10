# Production ceiling seat and pickup, issue 110

The production bay now uses the passed formed-seat source for its lower cross supports and the detached pickup. The source GLBs, image-derived PBR, shared component API and 115-degree floor pose are unchanged. Upper 55 mm carriers, webs, primary longitudinal ledgers, fixtures and service positions remain in place.

## Installed geometry

`app/seat_rail_mesh.gd` provides `span(length)`, `clipped(part, low, high)` and `cache_size()`. It clips imported source triangles in source-local X, interpolates UVs and normals, and closes the physical sheet cuts with concave caps. It does not scale the profile, holes or UV atlas. Intersection ordering is deterministic across incident faces. Cap triangulation uses millimetres so Godot's polygon tolerance does not erase the small bend radii.

The production ceiling has 130 healthy spans sharing three meshes: 1.164 m, 0.9635 m and 0.143499 m. Two additional cached meshes retain the left and right source ends, clipped at X = -0.582 and +0.582 m. These butt against the primary long ledgers. No old flat cross strip remains beneath the new seats or the missing middle.

The bearing top stays at Y = 2.988 m. The overall profile is 42 mm wide and 18 mm deep, with the original 36 mm bearing and 2.5 mm gauge. During the existing panel merge, horizontal flange planes are restored to their exported -2 mm underside. Godot's compressed imports otherwise move those planes by approximately 0.15 to 0.4 micrometres. The panel rim, texture coordinates and asset files are retained.

## Coordinate correction

The empty cell is (4,4), centered at bay (-0.6,2.99,-0.9). Sag is (3,4); broken edge is (4,5). The previous damaged cells and bowed strip at Z = 1.8 are repaired.

**The installed failed-seat center is (-0.6,2.988,-0.6), rather than the requested Z = -1.2.** Z = -1.2 borders beam-aperture cassette (4,3), removing a healthy cassette bearing. Keeping the broken-edge panel at (4,5) also caused up to 10 mm of real penetration into the intact seat at Z = -0.6. Using the north boundary aligns the one matched source gap with that panel's missing flange, preserves every healthy bearing, and requires no asset redesign or fixture movement.

## Verification

The focused runner inherits the production child-process script-error guard. It covers ceiling layout, bounds, bearings, ledger junctions, fixture visibility, source identity, pickup, click-proxy boundaries and hatch prying. Native checks retain all 7,531 panel-bearing samples and all 32 cassette-edge contacts. Nine top-skin rays on each installed span add 1,170 physical gauge samples. All six beam footprints remain unobstructed; ledger junctions have zero positive-area horizontal overlaps.

`tools/check_seat_production.py` audits native instance readback. All five cached meshes have closed, consistently wound metal volumes and an open channel. Source UV error is at most 6.26e-8; source-normal interpolation error is below 7.78e-5 after normal packing. It checks 223 installed rail/panel candidate pairs, representing seven relative source arrangements, with zero below-bearing edge intersections or contained vertices. The original penetration tolerance is retained.

`Rod/RodBar` now contains the passed `middle.glb` with its floor transform applied once. Its actual floor contact is Y = 0 and maximum height is 43.692789 mm. The logical anchor, walking-only 1.3 m reach, 0.22 x 0.10 x 1.15 m world click proxy, carried flag, hide-on-pickup path and hatch-pry behavior are unchanged.

## Captures and scope

`tools/capture_seat_production.gd` instantiates `main.tscn` and takes four diagnostic native-GPU views under production lighting, at 1280 x 900. It freezes that instance, hides its eyelid overlay for the inspection camera, and advances the console only for white-light captures. It adds no lights or material overrides. PNGs, hashes, native readback and logs are under `tmp/verify-stasis-wiring/seat-production/`.

Normal startup, smoke, eyes, emergency power, simulation, colliders and pod placements are unchanged. The supported-wiring prototype remains separate and is not installed. No full test suite or code review was run as part of this unit. Image-comparer assessment and final normal game launch remain with the parent after wiring integration.

The final capture exits with code 0 and writes all four PNGs and their hash manifest. Shutdown then prints geometry/light unpair and particle/texture cleanup messages. Their cause remains unverified; no production renderer or startup changes were made to suppress them. The focused test runner exits 0 with 42 passed and no failed tests; its native ceiling subprocess passes all five contracts. The separate mesh audit also exits 0.
