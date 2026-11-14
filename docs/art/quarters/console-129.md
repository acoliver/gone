# Quarters console and native keyboard

The desk console plays the message that changes the quarters from Remembered to Present. Its active display is 0.874 by 0.54625 m, a 16:10 rectangle. The housing is about 0.939 m high above its base and retains its sloped screen. Runtime placement seats it on the desk's actual 0.70 m worktop, below the rear upstand.

The separate keyboard reuses the power-room keyboard's complete geometry and UV triangles. Its 29 printed legends are native Naleya signs. They are asset markings; the keys do not implement a typing interface. The console's idle underscore and 60/180/60-tick corruption, message and fault sequence are controlled by the game.

## Sources and outputs

All paths are relative to the repository root.

| Source | Output or responsibility |
| --- | --- |
| `tools/blender/quarters/console/console-working.blend` | `assets/props/quarters/console.glb` |
| `tools/blender/quarters/console/keyboard-working.blend` | `assets/props/quarters/console_keyboard.glb` |
| `tools/blender/quarters/console/keyboard-placement.json` | Keyboard pose and support relative to the deck |
| `tools/blender/quarters/console/legends.json` | Production Naleya quads and cap assignments |
| `assets/props/quarters/steel/console_keyboard/` | Both states' albedo, normal and ORM maps, plus `mapping.json` |
| `assets/props/terminal/keyboard.glb` | Shared power-room source geometry |
| `app/quarters_console_keyboard.gd` | Runtime keyboard material and placement |
| `app/quarters_furnishings.gd` | Console installation and display fitting |

The keyboard's source pipeline is in `art-source/terminal/PIPELINE.md`. The quarters exporter preserves the main block, long operator-side cap and four-key right cluster. Its installed uniform scale matches the power-room unit. Both room states share the same mesh and seated transform.

Remembered cap pigment follows the source keyboard. Present adds neutral grey dust, bounded fading and higher polymer roughness under the [quarters aging rule](README.md#two-finish-states). Housing finish maps remain separate from polymer treatment. Runtime duplicates the imported `StandardMaterial3D` and substitutes the state textures, retaining source specular, normal and AO behavior.

Legend inputs begin with octal digits `0` through `7`, followed by the assigned vowels and syllables in `legends.json`. The raster uses production Naleya strokes, a 70% height envelope, a 90% width ceiling and the source keyboard's 5.5% stroke rule. Ink is muted, non-emissive and printed without raised geometry.

## Export and rebuild

Run from the repository root. Set `BLENDER` to Blender 4.5.11 LTS and use the art Python environment described in the [quarters guide](README.md#tools-and-export-conventions).

```sh
OUT="$PWD/art-output/console"
mkdir -p "$OUT"
"$BLENDER" --background --factory-startup --python-exit-code 1 --python tools/blender/quarters/console/build.py -- --output "$OUT/console.glb"
"$BLENDER" --background --factory-startup --python-exit-code 1 --python tools/blender/quarters/console/keyboard.py -- --output "$OUT/console_keyboard.glb"
cmp assets/props/quarters/console.glb "$OUT/console.glb"
cmp assets/props/quarters/console_keyboard.glb "$OUT/console_keyboard.glb"
```

Omitting `--assemble` and `--refit` exports the saved sources. `refit.py` owns the taller display cage. `keyboard.py --refit` rebuilds the accessory fit and removes obsolete separate controls from the console source; it writes the editable sources and placement record. Run that option only when intentionally changing the fit.

To rebuild printed legends and both keyboard finish sets:

```sh
godot --headless --path . -s tools/blender/quarters/console/export_legends.gd
python tools/blender/quarters/console/bake_legends.py
godot --headless --editor --path . --import
```

`export_legends.gd` calls the same Naleya layout and stroke expansion used by the game. The baker uses the source keyboard report's measured cap-interior UV rectangles. Console housing finishes use the shared steel library described in [Batch 1 materials](README.md#batch-1-materials).

## Verification

```sh
python tools/blender/quarters/console/test_console.py
python tools/blender/quarters/console/verify.py --reexport "$OUT/console.glb"
godot --headless --path . -s tests/run_tests.gd
```

The Python tests check active glass dimensions, retained support, keyboard triangle/UV identity, seated placement, cap pigment, print bounds and finish maps. The console verifier covers exported geometry and display emission. `verify_keyboard.py` adds triangle contact and underside support checks, but requires a separate baseline tree through its `--baseline` argument.

Game coverage includes `tests/quarters_console_geometry_test.gd`, `tests/quarters_console_presentation_test.gd`, `tests/console_screen_fit_test.gd` and `tests/quarters_display_test.gd`. Run the [quarters demo lane](README.md#captures-and-tests) to capture idle, playback and both room states with the actual cameras.

## Known limitations

The message and fault wording remain placeholders. The reused keyboard has a nonuniform UV-density report inherited from its source. Final keyboard finish changes have numeric comparisons but no completed visual acceptance recorded. Saved-source export and tests should be accompanied by a windowed inspection when changing the display or legends.
