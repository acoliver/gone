import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parent
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
paths = [Path(arg) for arg in args] if args else sorted((ROOT / "meshes").glob("*.glb"))
if not paths:
    raise SystemExit(
        "No mesh files supplied or found in art-source/status_panel/meshes. "
        "Pass one or more candidate GLB paths after Blender's -- argument."
    )
for path in paths:
    if not path.is_file():
        raise SystemExit(f"Mesh input not found: {path}")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    vertices = [
        vertex.co[:]
        for obj in bpy.context.scene.objects if obj.type == "MESH"
        for vertex in obj.data.vertices
    ]
    if not vertices:
        raise SystemExit(f"No mesh vertices found in {path}")
    low = [min(vertex[axis] for vertex in vertices) for axis in range(3)]
    high = [max(vertex[axis] for vertex in vertices) for axis in range(3)]
    dimensions = [high[axis] - low[axis] for axis in range(3)]
    print(path.name, "bounds", low, high, "dims", dimensions, flush=True)
