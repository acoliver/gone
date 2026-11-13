# Status panel sources

The panel shell is a Hunyuan3D-2mv reconstruction from FLUX.2-klein-4B product images. `assets/props/status_panel/panel.glb` retains its textured olive shell and exported `ScreenSocket`; it contains 44,972 triangles and three embedded images. The native and perceived board images are rendered from the board drawing and data in the local issue-91 scratch work, then used as the two presentation layers by `app/status_board.gd`.

The selected inputs are the three front product images named `front-s410`, `front-s411`, and `front-s412`. `build_panel.py` and the supporting inspection and image-preparation scripts are retained here. The panel is mounted at X=27 m on the north wall, with the display center at Y=2.10 m.

`LICENSE` and `Notice` are copied unchanged from `art-source/hatch/hunyuan/`. Its territory and redistribution restrictions apply to Hunyuan outputs. FLUX.2-klein-4B is under Apache-2.0. These records do not grant rights beyond the original terms.
