# Pod v4 source (#88)

`pod-v4-working.blend` is the editable, Y-up clean-cage pass-13 source.
It retains the fitted shell, matching dome/window boundary, couch, pillow,
gasket, material assignments and smooth normals. `build.py` exports it
without depending on gitignored scratch files or external weights. Re-export
matches the delivered GLB byte-for-byte with the retained Blender version.
Keep pivot subtraction in Python double precision before assigning the
converted vertex coordinates; early Vector rounding changes exporter
vertex welding and smooth normals.

Run from the repository root:

```sh
/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender \
  --background --factory-startup --python tools/blender/pod_v4/build.py -- \
  --output assets/props/pod/pod-v4.glb
godot --headless --path . --import
godot --headless --path . --import
```

The source came from the local Hunyuan reconstruction, followed by the
clean-cage fitting pipeline in `tmp/pods/cage*/`. Pass 13 repaired triangle
winding and fitted a 2.032 m occupant with 100 mm crown room and 80 mm foot
room. Earlier inference and fitting experiments are not required to edit
or export this retained source. Historical scratch scripts are not a
supported rebuild entry point.

The export has 28,566 triangles and five mesh nodes: PodBase with Couch
and Pillow children, and PodLid with WindowPane. Coordinates are metres,
+Y up, +Z foot, -Z head; the floor is Y=0. Closed bounds are
2.392917 m long, 0.899940 m wide and 0.895995 m high. The couch plateau is
Y=0.240. The hidden lid pivot is (0, 0.976, -1.15330785124). Negative local
X rotation opens it, without passing behind the head wall through 90°.

Materials are ShellPlastic, WindowTint, CouchFabric, PillowFabric and
Gasket. Godot does not import the clearcoat extension, so PodMesh restores
shell clearcoat explicitly. The game shares meshes/materials across pods
and preserves the separate lid pivot. `build_pod_probe.py` remains only
for the original #45 pipeline probe, not for this production asset.
