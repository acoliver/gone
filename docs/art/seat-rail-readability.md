# Ceiling seat inspection views

The seat rail is the formed lower support beneath the stasis-bay ceiling panels. Its detached middle section is the player's pickup and pry tool. The [production seat guide](seat-production-integration.md) describes its source assets, dimensions, current fault station and gameplay constraints.

## Inspection tools

`tools/capture_seat_rail_readability.gd` renders the shared source profile, installed seat detail, floor fragment and separated fracture mates under inspection lighting. `tools/compose_seat_rail_readability.py` lays out those captures and their source-derived annotations. Both tools choose their output locations internally.

Run from the repository root after the source and proof assets have been rebuilt with `tools/build_seat_rail.py`:

```sh
godot --headless --editor --path . --import
godot --path . -s tools/capture_seat_rail_readability.gd
python tools/compose_seat_rail_readability.py
```

The composer requires the capture's native mesh readbacks and source manifests. It derives leaders from rendered source surfaces and projects the removed middle mesh to show the missing interval. Its same-scale source sheet supports comparison of the bearing profile and fracture match. These inspection lights are separate from game lighting.

## Verification

Use `python -m unittest discover -s tools -p 'test_seat_rail.py'` for source identity, cut and floor-pose checks. The production seat guide gives the native installed-mesh runner and audit commands. Rebuild captures after source or placement changes rather than reusing an earlier image set.

## Known limitations

Standalone inspection does not show the ordinary opening camera or establish game-scale readability. The composer depends on local generated readbacks and measurements and cannot compose a sheet from the tracked GLBs alone. The production capture is the appropriate check for installed lighting and pickup visibility.
