# GONE ceiling light, round 3

This pass starts from `../round2/fixture.blend`. It retains the seed-720 generated body and the perforated generated lower skin, the fourteen-slot layout, and the recessed glass slab. All authored files are under `tmp/lights-redo/round3/`. The round-2 files and concept images are read-only inputs. No tracked files, branches, index or Git configuration were changed.

## Reproduce

The installed Blender performs the geometry edits, field baking, GLB export and CPU Cycles renders. The existing Python environment supplies NumPy, Pillow, SciPy and trimesh for texture processing, independent exported-mesh checks and the labelled comparison sheet. No image generation, Hunyuan inference, download or package installation is used.

```sh
R=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/lights-redo/round3
B=/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender
P=/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python
"$B" --background --factory-startup --threads 4 --python-exit-code 1 --python "$R/build.py"
PYTHONDONTWRITEBYTECODE=1 "$P" "$R/weather.py"
"$B" --background --factory-startup --threads 4 --python-exit-code 1 --python "$R/finish.py" -- --export-only
PYTHONDONTWRITEBYTECODE=1 "$P" "$R/verify.py"
"$B" --background --factory-startup --threads 4 --python-exit-code 1 --python "$R/finish.py"
PYTHONDONTWRITEBYTECODE=1 "$P" "$R/report.py"
touch "$R/READY"
```

The build/export/verify/render chain was run with `nohup bash -c` as a managed background job, with output in `pipeline.log`. That avoids the workstation's foreground-command watchdog. All rendering uses four CPU threads. No foreign process was signalled; one render job started by this task was cancelled after geometry verification found a defect.

## Geometry and shading

`build.py` opens the round-2 Blender file. The existing olive body receives a 1.014 × 0.116 m pocket with its roof at Blender Z=-0.076 m, rather than leaving the grille against the underside. The retained perforated strip is 94 mm wide. Raised 8 mm-wide rails leave approximately 10 mm of shadow channel between their shoulders and the body cutout. Closed inner side and end baffles prevent the shadow channel from exposing the diffuser at oblique angles.

The generated grille skin is thickened continuously from 4 mm to 9.5 mm. Its long slot edges receive 0.65 mm bevels. The original 2 mm slot corner radius remains. Two selected louvres have centre-span upward dents of 1.4 and 1.9 mm, at X=-0.14 and +0.28 m. The transverse deformation leaves their X/Y slot layout unchanged. Their upper surfaces remain below the glass. The rails have 7.8 mm total depth and 0.85 mm chamfers, with the existing rivets retained. Four additional side fasteners are placed at intersections with the actual generated body, providing origins for gravity streaks.

The body receives a two-segment 0.85 mm bevel and weighted face normals. Coplanar bevel diagonals are dissolved without removing the chamfer surfaces. The original generated-normal texture is not used in this pass, so the source scan's normal noise cannot restore the lower-edge shading defects. After the small body bevel, its metric envelope is restored to 1.10 × 0.10 × 0.22 m with its uppermost surface at zero.

The retained glass slab has its downward surface at Blender Z=-0.087 m, 13 mm above the body underside and 12.5 mm above the undented louvre low face. Its thickness remains 3 mm. The lens uses an opaque rough emissive material, with no transparency dependency. Dark cavity walls keep its side faces hidden. Full-depth end shoes cover a tapered sliver inherited from the generated left terminal, with a 0.2 mm offset from the old underside to avoid coincident visible surfaces.

Blender authoring is Z-up, with front along -Y. Export explicitly sets `export_yup=True`. The resulting GLB has +Y up, front +Z, and top mounting plane Y=0. The preview ceiling, camera and room lights are created after export and are not part of the GLB.

## Weathering and diffuser texture

Each of the body, grille and hardware receives a fresh 1024-square UV atlas. `build.py` bakes world positions and surface normals into float arrays. `weather.py` derives physical masks from those arrays and writes albedo and ORM maps. All runtime textures are embedded in the GLB.

The body uses a near-uniform olive paint base. Rust is restricted to lower edges, terminal edges, the channel rim and fastener tails. The oxide colour has only fine grain modulation, without the former broad scan-derived rust islands. Side-face streaks follow Blender -Z, equivalent to glTF -Y gravity. Their lengths are up to 42 mm and their half-widths grow from 1.5 to 1.95 mm. Channel grime follows the receiving pocket; it is not an arbitrary surface-noise mask. The measured body edge-to-broad-face rust ratio is recorded in `weather-stats.json`.

Grille soot follows the long slot lips and accumulates more heavily at the slot corners. Rail paint wear follows their chamfered edges, with grime and oxide around the rivet positions. Roughness rises in soot and rust, while worn edges expose a less rough metal tone. Rust has no bump or displaced geometry.

The 1024 × 128 frosted-glass emission image has a smooth longitudinal brightness envelope with 25.91% maximum-to-minimum variation. The mean end-to-centre brightness ratio is 0.798. It contains 190 dust specks, plus filtered fine-scale frosting. Those values describe the source emission image; they are not a claim about perceptual contrast in a tone-mapped render. The emission strength is 2.0, compared with 2.2 in round 2.

The weather-disabled controls replace both the albedo and ORM maps on all three metal materials. The glass texture, geometry, emission, cameras, room lighting, sample count and seed remain unchanged. Keeping the glass identical isolates the metal-weathering contribution. Both below-close and grazing views have paired controls.

## Exported-mesh checks

`verify.py` loads `fixture.glb` with trimesh and applies every glTF node transform before measuring anything. It checks the 3,000-triangle ceiling, full dimensions, mounting height, closed welded topology, winding and downward glass normals. A 5,201-ray centreline counts fourteen distinct visible slot runs. A 112,500-ray full-footprint grid and an 82,500-ray grille/channel grid check that vertical glass hits are confined to the slot envelopes.

Twelve oblique tests use 45,000 rays each, covering both the along-beam and across-beam directions at ±15, ±35 and ±55 degrees. Because the grille has finite thickness, chamfers and dents, the allowed aperture is evaluated through its physical depth, rather than assuming every lip lies on one plane. Each glass first hit must project through a slot envelope somewhere in that depth, and every visible glass triangle must have a downward normal. The total is 740,201 sampled rays, including the centreline.

The final export contains 2,934 triangles: 1,258 in the generated body, 992 in the retained grille, 672 in the rails/fasteners/baffles/end shoes, and 12 in the glass. That leaves 66 triangles below the budget. `verification.json` records the actual exported bounds, topology, aperture fractions and per-view ray results.

During construction, a binary assignment of upper/lower grille heights collapsed three intermediate vertices inherited from the source. The exported topology check caught the resulting coincident faces. Continuous depth scaling fixed that cause. An oblique ray then found the inherited terminal sliver; the end shoes close it. The failed checks were not relaxed. The final pipeline verifies the export before rendering.

## Renders and comparison sheet

`finish.py` uses 1200 × 900, 48-sample CPU Cycles renders, AgX, and seed zero. It retains the round-2 preview ceiling and two soft room fills. Cameras for below at 2.5 m, below close, ordinary three-quarter and both ends match round 2. A separate grazing three-quarter camera is about 15.4 degrees below the ceiling plane to expose louvre depth. There are nine renders: those six views, emissive off, below-close metal weather disabled, and grazing metal weather disabled.

`report.py` builds the labelled 2160-pixel-wide `sheet.jpg`, with concept 202 and 210 reference tiles and round-2/round-3 views side by side. It also measures weather-on/control image differences in the same below-close pixel region used in round 2, and records a separate grazing comparison. The lit-capture gate requires a mean RGB change above 0.002 and more than 2% of that region to change by over 2/255. These visibility measurements supplement the structural masks. They do not provide a visual quality verdict.

The measured below-close weather/control mean absolute RGB difference is 0.01347, with 26.19% of the fixed region exceeding 2/255 and a 95th-percentile difference of 0.07451. The mean difference is 9.31 times round 2's value in the same region. The grazing pair changes 3.02% of the entire image by more than 2/255. These statistics show a rendered effect contribution; they do not judge its appearance.

`results.json` contains the final measurements, image paths and limitations. No image reading or visual judgment was performed. Godot integration is outside this pass.
