# Bay ceiling panel candidate

This is a full Hunyuan3D-2mv generated panel-shape candidate from the approved isolated reference. It is a shape source for the fitting stage, not a game-integrated asset. Keep the generated broad manufactured form and fit exact slots, fasteners and interfaces in Blender rather than rebuilding the panel from primitives.

For fitting, author in Blender's native Z-up frame (height along Blender +Z, front facing Blender -Y). Export glTF with `export_yup=True` so the exported file has +Y up and front +Z; verify the exported GLB bounds externally with trimesh.

Inputs: `panel-reference-approved-source.png` (approved isolated panel); `approved-room-concept.png` (room context). Generation command, seed, log, and measured mesh facts are recorded alongside the candidate. Fitted outputs live under `assets/props/bay-ceiling/`, with editable source `fitted-source.blend`, deterministic build script `tools/blender/build_bay_ceiling.py`, and measurements/known limitations in `fitted-provenance.txt`.

The 2-row review sheet is `candidate-seed-4208-multiview.png`: top row is the above view; bottom row is the underside. Each row uses azimuths 30, 120, 210, 300 degrees from left to right at elevations +35 and -35 degrees respectively. It is a fixed-angle diagnostic render, not a final material preview. The candidate contains two connected components (270,192 and 92 triangles); inspect the small component during fitting.
