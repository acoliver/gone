# Status panel sources

The panel shell is a Hunyuan3D-2mv reconstruction from FLUX.2-klein-4B product images. `assets/props/status_panel/panel.glb` retains its textured olive shell and exported `ScreenSocket`; it contains 44,972 triangles and three embedded images. The panel is mounted at X=27 m on the north wall, with the display center at Y=2.10 m. The native and perceived board images in the same directory are the two presentation layers used by `app/status_board.gd`; [the status board guide](../../docs/dev/status-board.md) describes how they are built.

## Generation inputs

- `inputs/ref-panel.png` is the approved panel concept used as the FLUX.2-klein-4B edit reference, with the prompt in `prompts/front.txt`.
- `inputs/front-s410.png`, `front-s411.png` and `front-s412.png` are the generated front views: 4-bit, 8 steps, guidance 1.0, 1024 x 512, seeds 410 to 412.
- `matte_inputs.py` writes the `-rgba` mattes beside them with rembg. `measure_opening.py` measures the dark screen opening in each view.
- `meshes/panel-s410.glb` and `panel-s411.glb` are the Hunyuan3D-2mv candidates: subfolder `hunyuan3d-dit-v2-mv`, float16, 30 steps, guidance 5.0, octree resolution 384, front view `inputs/front-s412-rgba.png`, seeds 410 and 411.
- `inputs/design-sheet-v3.png` is the approved power-room hardware design sheet. `make_contact.py` places it beside the builder's renders.

The front views, candidate meshes and design sheet were recovered from the original issue-91 scratch tree. Their generation logs were not kept.

## Build

`build_panel.py` runs in Blender 4.5 (`blender --background --python art-source/status_panel/build_panel.py`). It scores both candidates by front silhouette IoU against `inputs/front-s410-rgba.png`, fits the better one, applies the two tracked steel scans from `art-source/steel/`, renders the current runtime board into a preview, applies the runtime triangle budget, and writes `panel.glb`, `panel.blend`, `textures/`, `renders/`, `logs/` and `build-report.json` in this directory. With Blender 4.5.11 its `panel.glb` is byte-identical to `assets/props/status_panel/panel.glb`; copy it there only after a deliberate change.

`inspect_mesh.py` prints bounds for the candidate meshes, or for GLB paths passed after Blender's `--` argument.

`board_render_reference.gd` renders the original board layers from `board_data_reference.gd`, `app/naleya.gd` and the ship atlas into `tmp/status-panel-display/`. It uses the macOS SF Compact system font and needs a windowed renderer: `godot --path . -s art-source/status_panel/board_render_reference.gd`.

`LICENSE` and `Notice` are copied unchanged from `art-source/hatch/hunyuan/`. Its territory and redistribution restrictions apply to Hunyuan outputs. FLUX.2-klein-4B is under Apache-2.0. These records do not grant rights beyond the original terms.
