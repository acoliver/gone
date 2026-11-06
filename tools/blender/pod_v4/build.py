"""Export the retained clean-cage pod source in the game's Y-up frame.

Run Blender --background --factory-startup --python this_file -- --output path.glb.
The editable source uses Y-up coordinates; Blender's exporter expects Z-up.
"""
import argparse
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
NAMES = ("PodBase", "PodLid", "WindowPane", "Couch", "Pillow")
PIVOT = Vector((0.0, 0.976, -1.1533078512396695))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    bpy.ops.wm.open_mainfile(filepath=str(ROOT / "pod-v4-working.blend"))
    for obj in list(bpy.data.objects):
        if obj.name not in NAMES:
            bpy.data.objects.remove(obj, do_unlink=True)
    for name in NAMES:
        obj = bpy.data.objects[name]
        normals = [tuple(n.vector) for n in obj.data.corner_normals]
        origin = PIVOT if name in ("PodLid", "WindowPane") else Vector()
        for vertex in obj.data.vertices:
            x, y, z = vertex.co - origin
            vertex.co = (x, -z, y)
        obj.data.normals_split_custom_set([(x, -z, y) for x, y, z in normals])
        obj.location = (origin.x, -origin.z, origin.y)
    for child, parent in (("Couch", "PodBase"), ("Pillow", "PodBase"), ("WindowPane", "PodLid")):
        obj = bpy.data.objects[child]
        frame = obj.matrix_world.copy()
        obj.parent = bpy.data.objects[parent]
        obj.matrix_world = frame
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(
        filepath=str(args.output.resolve()), export_format="GLB", use_selection=True,
        export_yup=True, export_materials="EXPORT", export_cameras=False, export_lights=False,
    )


if __name__ == "__main__":
    main()
