# Wall and ceiling fixtures

The stasis bay, hall, power room, connectors and quarters use mounted emitters with circuit-specific output. A standalone cage or beam contains one light source seated at its visible emitter. Source placement, housing contact and service clearances are part of the fixture contract.

## Runtime sources and layout

`app/emergency_fixture_profile.gd` defines emergency shares, range and falloff. `app/fixture_emitter.gd` and `app/ceiling_fixture.gd` bind sources to their housings. `app/lighting.gd`, `app/hallway.gd` and `app/power_room.gd` own their opening-room instances. Layout records supply section and connector stations.

The bay has four wall cages on each long wall, at world Z=3.2, 6.2, 9.2 and 12.2 m, Y=2.5 m. West source centers are X=11.1 m and east centers X=18.9 m. The hatch fixture is separate. Ceiling beams mount at the slab; their source sits at the glass. Fixture housings must clear pods, wiring, hatches and the standing envelope.

The bay wall rows use one profile, with a 7 m range and uniform spacing. Shares multiply the common energy unit. The hall and power room retain their own profiles. Emergency/white handoff follows the simulation fade clock. Independent section and connector circuits remain separate from the switched opening rooms. Display emission and status belts have their own roles; they do not add ambient fill.

The ceiling beam's editable source is `art-source/ceiling-props/fixture/aging/fixture.blend`; its output is `assets/props/ceiling/fixture.glb`. `app/ceiling_fixture.gd` binds the imported beam. Wall cages are built at runtime by `app/hatch_services.gd` and reused through `app/fixture_emitter.gd`. Changing only a station or energy profile needs no mesh rebuild.

With `BLENDER` set to the Blender 4.5.11 LTS executable, re-export the beam from the repository root:

```sh
"$BLENDER" --background --factory-startup --python-exit-code 1 --python tools/blender/export_ceiling_fixture.py
```

Wall-cage changes take effect on the next scene build and need no separate export.

## Capture and verification

Run from the repository root with Godot's native renderer and the art Python environment:

```sh
OUT="$PWD/art-output/fixtures"
mkdir -p "$OUT"
godot --headless --editor --path . --import
godot --path . --fixed-fps 60 -s tools/capture_fixture_views.gd -- "$OUT" --overviews-only
python tools/check_fixture_overviews.py "$OUT"
python -m unittest discover -s tests -p 'test_fixture_*.py'
godot --headless --path . -s tests/run_tests.gd
```

Omit `--overviews-only` for wall-row inspection views as well. Captures freeze the seeded smoke field and animation time after warm-up. `views.json` records the fixed cameras, allowing the checker to compare matching views. `tools/light_inventory.gd` supplies the native inventory used by the fixture tests.

Coverage includes `tests/light_mounting_test.gd`, `tests/fixture_spacing_test.gd`, `tests/emergency_fixture_profile_test.gd`, `tests/bay_fixtures_test.gd` and `tests/ceiling_fixture_test.gd`. The tests check housed emitters, mirrored bay rows, source count, spacing, live-lamp glow, circuit handoff and the incident-light reference. Python tests cover image-checker boundaries and fixture weathering.

## Known limitations

These point sources do not cast shadows, so room masks and receiver layers matter. Fixed-view luminance and incident-light checks constrain output but do not establish the quality of every view. Shared-host performance measurements do not establish an isolated speed improvement. Godot can emit cleanup diagnostics after native capture or test shutdown.
