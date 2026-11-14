# Installed stasis wiring

`ShipScene.build_into()` installs one source-to-seven-pod wiring network beneath `BayRoot`. It contains the source enclosure, supported overhead power/data runs, wall drops, buried distribution and the localized fault. The [layout guide](stasis-wiring-layout.md) gives coordinates and explains the connection to the fallen ceiling seat.

## Sources and outputs

The authored route and hardware modules are `tools/stasis_wiring_production.py`, `stasis_wiring_assemblies.py`, `stasis_wiring_ports.py`, `stasis_wiring_fault.py` and `stasis_wiring_installation_graph.py`. They live under `tools/`. `tools/stasis_wiring_export_checks.py` verifies the resulting geometry outside Blender.

Production files are under `assets/props/stasis-wiring/`:

- `production-installation.glb` and `production-installation.blend`: installed mesh and editable export.
- `production-installation.json`: generated assembly description and measurements.
- `production-routes.json`: semantic connectivity and fault-tip records.
- `stasis-wiring-enclosure.glb`, its editable `.blend` and `sockets.json`: source housing and physical interfaces.
- `seat-rail/`: the separate formed-seat family, described in the [seat guide](seat-production-integration.md).

The installation uses two 24 mm power jackets and six 6 mm data strands. Pipes stop at enclosure ports; insulated jackets terminate there and copper links join shared terminal positions inside. The overhead split has separate trunk and takeoff ports. Different conductors retain physical separation. Runtime does not add a second carrier grid or cable collision inventory.

## Rebuild and verify

Run from the repository root with Godot, Blender 4.5.11 LTS and a Python environment containing NumPy, Pillow, SciPy, trimesh and the geometry dependencies imported by the builders. `tools/build_stasis_wiring.py` defines the local Blender executable used by the production builder. Check that path before running on another machine.

Choose a new repository-relative results directory. The same environment variable must reach the builder, capture and checker:

```sh
export STASIS_WIRING_RESULTS=art-output/stasis-wiring
mkdir -p "$STASIS_WIRING_RESULTS"
godot --headless --editor --path . --import
python tools/stasis_wiring_provenance.py
godot --path . -s tools/dump_stasis_wiring_context.gd -- "$STASIS_WIRING_RESULTS/context.json"
python tools/build_stasis_wiring_production.py
godot --headless --editor --path . --import
python -m unittest discover -s tools -p 'test_stasis_wiring_*.py'
godot --headless --path . -s tools/run_stasis_wiring_tests.gd
godot --path . -s tools/check_stasis_wiring_scene.gd
```

The context dump needs the native renderer because it measures actual prepared meshes. The builder writes the production GLB, editable Blender file, manifest and route JSON. It checks contacts, complete lid motion, pod-base containment, fixture/service reservations and exported jacket/enclosure intersections. Graph generation requires physical strand-level interfaces, rather than accepting axis connectivity alone.

The provenance tool records build inputs and preserved assets. If an input changes during a build or between build and capture, rebuild from stable inputs before using the capture checker. A new results directory avoids reusing a baseline from a different source tree.

## Capture

With native rendering available:

```sh
godot --path . -s tools/capture_stasis_wiring_production.gd
python tools/check_stasis_wiring_capture.py
```

The capture starts in `main.tscn`, records the normal wake and get-up through physical input, then switches to separately labeled diagnostic cameras. White diagnostics use the existing secondary circuit, without added lamps or material overrides. The capture validates the current import and build inputs before rendering. The checker reads the output from `STASIS_WIRING_RESULTS`.

## Tests

`tools/test_stasis_wiring_*.py` covers route geometry, junctions, fault conductors, transitions, output independence and provenance failures. The focused Godot runner covers installed placement and semantic endpoints. `tests/run_tests.gd` runs the full game suite, including the shared ceiling and pickup contracts.

## Known limitations

Wiring is static and has no runtime cable simulation. The standalone fault and transition assets are diagnostic construction references, separate from the installed network. Native scene and capture shutdowns can emit resource and renderer cleanup diagnostics; their cause is not fully attributed. Capture timings include scheduling and readback and do not establish isolated rendering cost.
