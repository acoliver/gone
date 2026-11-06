# Pod v4 source (#88)

`pod-v4-working.blend` is the editable Y-up source. It retains the fitted
shell, closed glazing solid, couch, pillow, original base gasket and smooth
normals. The glass has explicit `pane_region` face tags: outer 0, inner 1,
cut edge 2 and polished bevel 3. `build.py` derives the single-sheet game
pane from those tags. It never repeats the perimeter trim.

Export with the retained Blender version:

```sh
/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender \
  --background --factory-startup --python-exit-code 1 \
  --python tools/blender/pod_v4/build.py -- \
  --output assets/props/pod/pod-v4.glb
godot --headless --path . --import
```

Re-export is byte-identical with Blender 4.5.11 LTS. The export contains
27,158 triangles in five mesh nodes: PodBase with Couch and Pillow, and
PodLid with WindowPane. Godot retains 19,702 triangles after shell LOD;
the pane keeps its unsimplified 5,280 triangles so the bevel and region
mask survive. The existing 20,000-triangle limit is unchanged.

Coordinates are metres, +Y up, +Z foot and -Z head. Closed bounds remain
2.392917 m long, 0.899940 m wide and 0.895995 m high. The couch plateau is
Y=0.240. PodLid's origin is the head seam at
`(0, 0.437, -1.17250931263)`. Negative local X rotation opens it. The
production open angle is 67.7295 degrees for both empty and player pods;
the rows move 206.999 mm inward to leave 20 mm behind the swept dome while
retaining a 2.5 m aisle and 150 mm exit reserve. `measure_hinge.py` checks
the sweep, contact and camera clearances against the source geometry.

The pane preserves its fitted thickness outside a 2 mm perimeter band.
Its edge has a 1 mm reveal and a three-segment 0.5 mm bevel. A closed
window seat shares PodLid and the existing Gasket material, recessed
1.5 mm below the glass exterior. The seat follows the retained tapered
cut edge. Its nominal lateral separation is 0.25 mm rather than the
advice plan's 0.05 mm: the smaller offset allowed finite-triangle chord
intersections on the taper. The source verifier requires zero pane/seat
intersections. This is an explicit departure from that proposed dimension.

`author_glass.py` records the one-time conversion from the original
paired solid. Ordinary editing and export use the saved tagged source.
`verify_glass.py -- --output <directory>` checks source topology, actual
bevel radii and reveal, preserved positions/thickness and aperture rays.
Run it with `--python-exit-code 1`; Blender otherwise reports Python
assertions without a failing process exit code.

Materials remain ShellPlastic, WindowTint, CouchFabric, PillowFabric and
Gasket. Blender's closed-solid preview uses Principled transmission 1,
IOR 1.5 and roughness 0.07. The GLB has a neutral transport fallback;
Godot replaces WindowTint with `app/pod_glass.gdshader`. COLOR_0 selects
the seated cut edge without tinting the broad viewing surface. PodMesh
also restores the shell clearcoat that Godot drops during glTF import.

Full glass acceptance is still open. The reflection fixture measures zero
card-on/card-off signal from both the glass and its metallic mirror control.
Direct-light specular and a sky-lit metallic control work; the cause of the
room-probe failure is unresolved. Smoke/depth ordering, edge-card response,
full production transition and post-LOD aperture gates are not established.

The source originated in the local reconstruction and clean-cage fitting
pipeline. Scratch fitting scripts and external weights are not export
dependencies. `build_pod_probe.py` belongs to the earlier #45 probe.
