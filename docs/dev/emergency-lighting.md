# Emergency lighting

The live game uses Godot. Emergency fixtures light the opening in red; the hall switch and secondary-power console control the later circuit changes. Secondary activation hands the bay, hall and power room from emergency red to regular white. The quarters have their own two-state treatment.

## Sources

`sim/power.gd` owns the power state. `app/lighting.gd`, `app/hallway.gd` and `app/power_room.gd` present it through fixture profiles and fades. Mounted source locations, housing assets and capture commands are described in [Wall and ceiling fixtures](light-fixture-mounting.md).

The [quarters art guide](../art/quarters/README.md#playable-demo) describes Remembered and Present lighting. The pod indicators, machinery emission and spark flashes are separate from the room's sustained emergency fixtures.

## Verification

Run from the repository root:

```sh
godot --headless --path . -s tests/run_tests.gd
godot --headless --path . -s harness/run.gd -- scenarios/hallway.json
godot --headless --path . -s harness/run.gd -- scenarios/power-room.json
```

The harness launches a windowed renderer for captures. `tests/lighting_test.gd`, `tests/section_power_lighting_test.gd` and `tests/d16_fixture_bindings_test.gd` cover output and handoff. Use the fixture guide's fixed-view capture command when changing placement or energy.

## Known limitations

The sources are shadowless. Numerical red/white classification and luminance checks do not establish scene readability or appearance at every camera position. The archived Bevy implementation is under `archive/rust/`; its light units and render-bridge details do not describe the active Godot scene.
