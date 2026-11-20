# Selection notes

Three front views were generated with FLUX.2-klein-4B (seeds 410 to 412). Two Hunyuan3D-2mv candidates were reconstructed from the seed 412 matte. `build_panel.py` scored them against the seed 410 matte: front silhouette IoU 0.9108 for seed 410 and 0.9054 for seed 411, so `meshes/panel-s410.glb` was fitted (`build-report.json`). `assets/props/status_panel/panel.glb` is that fitted reconstruction with a distinct display plane and `ScreenSocket`.

The first board layers were drawn by `board_render_reference.gd` from `board_data_reference.gd`, with the ship profile from `docs/art/ship/3d/ship_atlas.json`. The current `board-native.png` and `board-perceived.png` runtime layers are produced by `tools/build_status_board.gd`.
