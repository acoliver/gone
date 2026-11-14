# Ceiling seat and pickup

The lower formed ceiling seat supports bay panels. At the fault station, a missing interval matches the floor fragment that the player picks up and uses to pry the hatch. The upper 55 mm carriers remain continuous. [Wiring layout](stasis-wiring-layout.md) describes the panel opening and exposed power tips at that station.

## Sources and installation

`tools/seat_rail.py` defines the shared formed profile, cut contours, material and floor pose. `art-source/stasis-wiring/seat-rail/` retains its generated guide and image-derived PBR source. `tools/build_seat_rail.py` builds the source family under `assets/props/stasis-wiring/seat-rail/`: `full.glb`, `left.glb`, `middle.glb` and `right.glb`, with finish textures and manifests.

`app/seat_rail_mesh.gd` clips imported source triangles to the installed span lengths, interpolates UVs and normals, and caps the sheet cuts. It preserves the profile rather than scaling it. `app/bay_ceiling.gd` installs the spans and retained ends. The bearing top is Y=2.988 m in bay coordinates; the profile is 42 mm wide, 18 mm deep and 2.5 mm thick, with a 36 mm bearing face.

The failed seat is centered at bay `(-0.6, 2.988, -0.6)`, beside the empty panel cell `(4,4)`. `app/rod.gd` uses the same middle source for the pickup. Its floor pose rolls 115 degrees about the longitudinal axis; translation is derived from transformed vertices so its lowest point meets Y=0. The pickup anchor, reach and click proxy belong to gameplay and must remain aligned when changing the mesh.

## Rebuild and verify

Run from the repository root with the art Python environment and Blender 4.5.11 available at the path in `tools/build_seat_rail.py`:

```sh
python tools/build_seat_rail.py
godot --headless --editor --path . --import
python -m unittest discover -s tools -p 'test_seat_rail.py'
godot --headless --path . -s tools/run_seat_production_tests.gd
python tools/check_seat_production.py
```

The builder updates source assets and proof geometry. Its `--floor-only` option updates the baked proof fragment pose without rebuilding the source family. The guarded Godot runner writes the native instance readback consumed by the Python checker. Checks cover closed metal volumes, retained UVs/normals, panel bearings, ledger junctions, rail/panel penetration, pickup bounds and hatch-pry behavior.

Use `godot --path . -s tools/capture_seat_production.gd` for production-light inspection views. The script selects its own output directory. [Standalone rail inspection](seat-rail-readability.md) provides neutral profile and fracture views.

## Known limitations

The seat family is a static mesh system; it has no fracture physics. Native capture shutdown can print resource cleanup diagnostics. The source family and installed spans have different responsibilities, so inspect both when changing end cuts or source UVs. The floor piece must remain within the unchanged gameplay proxy.
