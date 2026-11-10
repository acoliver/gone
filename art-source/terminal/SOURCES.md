# Generated console sources

## Territory restriction

**The Hunyuan license excludes the European Union, United Kingdom and South Korea.** Keep `LICENSE` and `Notice` with these assets and check their terms before redistribution. Both files are retained unchanged. FLUX.2-klein-4B uses Apache-2.0; that does not replace the Hunyuan terms.

## Selected assets and modifications

The standing console replaces the previous terminal and procedural keyboard tray. `assets/props/terminal/console.glb` contains the generated `ConsoleBody`, the screen rectangle `DisplayPlane`, and the `ScreenSocket` and `KeyboardSocket` placement nodes. Its body has 48,000 triangles and the display adds two. The selected standing-height delivery had 68,810 body triangles. `export_game_console.py` reduces it for the game, weighting the keyboard deck against collapse and retaining the embedded 2048-pixel albedo, ORM and tangent-normal maps.

`assets/props/terminal/keyboard.glb` is the supplied 28,998-triangle keyboard without geometry or texture changes. Its `KeyboardBase` receives the glTF transform from `keyboard-placement.json` at runtime. There is no separate tray, hinge droop or keycap-removal treatment. One busted station loses its whole keyboard; both busted screens use the existing crack texture.

The console measures approximately 1.10 m wide, 0.7313 m deep and 1.6984 m high. Its floor and wall-back planes are zero, with roomward +Z after Godot import. The keyboard deck centre is 1.00 m above the floor and the screen centre is 1.40 m. Godot tests measure underside support gaps, triangle intersections, screen visibility and text orientation on the shipped export.

## Generation record

`PIPELINE.md` preserves the delivery's pipeline notes. Relative paths in those notes resolve from the duplicate `generated/console2/final/README.md`, where the original directory relationships are retained. `generated/` contains the selected console image seed 510, keyboard image seed 531, input RGBA images, reference images, prompts, metadata, source scripts and measurement records. The original image metadata files contain `null`; the generation commands and recorded seeds supply the settings. `provenance.json` records model revisions and SHA-256 hashes of the shipped GLBs, placement and retained inputs.

Both selected raw Hunyuan meshes are below 20 MB and are included: `generated/console2/meshes/console-s510-rgba-410.glb` and `generated/console2/kb3/shape-410.glb`. The standing-height stage's assembly3 Blender input, unchanged local keyboard, and source vertices are also retained. Intermediate stages can be regenerated with the archived scripts and the external model/tool installations listed in the pipeline. The final pre-budget GLB is retained so the game export can be reproduced without rerunning inference or baking.

The selected shape model is Hunyuan3D-2mv, `hunyuan3d-dit-v2-mv`, with seed 410 for both props. FLUX uses 4-bit FLUX.2-klein-4B, eight steps and guidance 1.0. Shape generation uses float16, 30 steps, guidance 5.0 and octree resolution 384. The keyboard paint seed is 531. The historical console paint seed was not recorded; that atlas was superseded by the deterministic finish documented in `PIPELINE.md`.
