# Tunic medal and button row

The medal hangs from the dress uniform inside the protagonist's wardrobe. It has a nominal 32 mm brass body, a raised five-point star, blue enamel, a soldered ring and an interlinked ribbon attachment. Both room states use the same design. The [quarters guide](../../README.md#two-finish-states) defines Remembered and Present aging.

The owner has chosen to leave the current appearance as it is for now. At the close camera it does not yet pass as a photograph. Regular star facets, broad smooth highlights from the shadowless point lights and the even rim remain visible tells. The ribbon and attachment also lose photographic detail in wider views.

## Sources and outputs

Paths below are relative to the repository root.

- `tools/blender/quarters/dress_uniform/tunic-working.blend`: mounted Remembered garment, buttons, ribbon and medal.
- `tools/blender/quarters/dress_uniform/tunic-pilot.blend`: mounted Present garment and details.
- `tools/blender/quarters/dress_uniform/medal_v3/frozen-c01-hyseed0.glb`: retained Hunyuan shape guide. The corresponding `frozen-c01-seed1306201.png`, height samples and star measurements are beside it.
- `tools/blender/quarters/dress_uniform/medal_v3/medal-fitted.blend`: editable generated-surface fitting source. `medal-enamel14.blend` retains the enamel/shape finishing source.
- `assets/props/quarters/dress_uniform.glb` and `dress_uniform_aged.glb`: production exports, including the complete garment.

The fitted cage follows the generated surface, with independently sampled side bands and feature curves. It retains generated asymmetry. High and low body depth are scaled together, and the mounted reverse follows the wool. The finish uses photo-derived brass, enamel and grosgrain maps. Brass and enamel have separately padded albedo, ORM and normal maps; an antialiased surface mask blends their boundary. Enamel has its own coat map and is excluded from wool colour calibration.

`medal_v3/texture/` contains the texture preparation and bake tools. The mounted material helpers include `medal_photo_finish.py`, `medal_twelfth_finish.py`, `medal_thirteenth_finish.py` and `medal_fourteenth_finish.py` in the uniform directory. These filenames identify source modules, rather than steps needed for an ordinary export. The saved mounted sources contain the current finish.

The uniform has eight 14 mm buttons and an extended placket. `tunic_details.py` owns the row fitting and rebake; `issue130-details.json` records it. Present row textures use their final surface UVs. `medal-budget.json` records the mounted medal's allocation separately from cloth. Use the current budget records when changing the generated medal.

## Rebuild and export

Run from the repository root with Blender 4.5.11 LTS. Set `BLENDER` to its executable and use a writable output directory:

```sh
OUT="$PWD/art-output/medal"
mkdir -p "$OUT"
"$BLENDER" --background --factory-startup --python-exit-code 1 --python tools/blender/quarters/dress_uniform/build.py -- --output "$OUT/dress_uniform.glb"
"$BLENDER" --background --factory-startup --python-exit-code 1 --python tools/blender/quarters/dress_uniform/build.py -- --aged --output "$OUT/dress_uniform_aged.glb"
cmp assets/props/quarters/dress_uniform.glb "$OUT/dress_uniform.glb"
cmp assets/props/quarters/dress_uniform_aged.glb "$OUT/dress_uniform_aged.glb"
```

These commands export the retained mounted sources without solving cloth or refitting the medal. Authoring is Blender +Z up, front -Y; export converts to glTF +Y up, front +Z. Copy an intentional replacement to its production path, then refresh Godot imports before capture.

## Verification

Use the existing art Python environment described in the [quarters guide](../../README.md#tools-and-export-conventions). A portable regression covers final enamel transport; the row texture-binding check runs inside Blender:

```sh
python tools/blender/quarters/dress_uniform/test_medal_fourteenth_finish.py
"$BLENDER" --background --factory-startup --python-exit-code 1 --python tools/blender/quarters/dress_uniform/test_detail_bakes.py
godot --headless --editor --path . --import
python tools/blender/quarters/dress_uniform/verify_native_import.py --output "$OUT/native-import.json"
godot --headless --path . -s tests/run_tests.gd
```

`tests/quarters_clothes_test.gd` and `tests/quarters_reflected_clothes_test.gd` cover garment installation and material routing. Other `test_medal_*.py` modules cover normal maps, finish masks, soldered attachment, interlinking and support. Some source tests require Blender; inspect their imports before selecting the interpreter.

With native rendering available, capture the actual room's wardrobe, button and medal views:

```sh
godot --path . -s tools/capture_tunic_details.gd -- "$OUT/captures"
```

The capture script checks fresh native garment imports and uses the game wardrobe camera and room lighting. Its optional `--diagnostics` mode is an inspection view, separate from the ordinary capture.

## Known limitations

- The close view remains visibly rendered for the reasons described above. Export, contact and texture tests do not establish photographic appearance.
- Reconstructing the full tunic through `--assemble` needs its original saved sleeve intermediate, which is absent from the tracked tree. The mounted-source export route does not need it.
- The standalone fitting scripts retain local intermediate dependencies. They are useful for editing the method, but are not a self-contained clean-checkout reconstruction command for the final mounted medal.
- Older comparison JPGs in this directory show the earlier concentric medal. They do not depict the current generated-surface replacement and are intentionally not used as current appearance references here.
