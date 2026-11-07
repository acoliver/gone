"""Export the retained Y-up pod, deriving one render sheet from tagged glass.

Run Blender --background --factory-startup --python this_file -- --output path.glb.
The editable pane stays a closed solid. Perimeter authoring is never repeated here.
"""
import argparse
from pathlib import Path
import sys

import bpy

ROOT = Path(__file__).resolve().parent
NAMES = ("PodBase", "PodLid", "WindowPane", "Couch", "Pillow")
PIVOT = (0.0, 0.437, -1.1725093126296997)


def render_pane(obj):
    source = obj.data
    assert 'pane_region' in source.attributes, 'author explicit glass regions before export'
    regions = [d.value for d in source.attributes['pane_region'].data]
    assert set(regions) == {0, 1, 2, 3}, 'glass solid lost an authored region'
    selected = [p for p, region in zip(source.polygons, regions) if region != 1]
    used = sorted({i for p in selected for i in p.vertices})
    mapping = {old: new for new, old in enumerate(used)}
    mesh = bpy.data.meshes.new('WindowRenderSheet')
    mesh.from_pydata([source.vertices[i].co[:] for i in used], [], [[mapping[i] for i in p.vertices] for p in selected])
    mesh.update()
    normals = [source.corner_normals[l].vector[:] for p in selected for l in p.loop_indices]
    # Custom normals are encoded in the smoothing basis; establish it first.
    for poly in mesh.polygons:
        poly.use_smooth = True
    mesh.normals_split_custom_set(normals)
    colors = mesh.color_attributes.new(name='PaneRegion', type='FLOAT_COLOR', domain='CORNER')
    for poly, original in zip(mesh.polygons, selected):
        color = (1.0 if regions[original.index] == 2 else 0.0, 0.0, 0.0, 1.0)
        for loop in poly.loop_indices:
            colors.data[loop].color = color
    mesh.color_attributes.active_color = colors
    fallback = bpy.data.materials.new('WindowFallback')
    fallback.name = 'WindowTintExport'
    fallback.use_nodes = True
    bsdf = next(n for n in fallback.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Base Color'].default_value = (1,1,1,1)
    bsdf.inputs['Metallic'].default_value = 0
    bsdf.inputs['Roughness'].default_value = .07
    # Transport only: Godot owns the actual lit thin-sheet material.
    preview = bpy.data.materials['WindowTint']
    preview.name = 'WindowSolidPreview'
    fallback.name = 'WindowTint'
    mesh.materials.append(fallback)
    obj.data = mesh


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    bpy.ops.wm.open_mainfile(filepath=str(ROOT / "pod-v4-working.blend"))
    for obj in list(bpy.data.objects):
        if obj.name not in NAMES:
            bpy.data.objects.remove(obj, do_unlink=True)
    render_pane(bpy.data.objects['WindowPane'])
    bpy.context.view_layer.update()
    positions = {name: [tuple(bpy.data.objects[name].matrix_world @ v.co) for v in bpy.data.objects[name].data.vertices] for name in NAMES}
    for name in NAMES:
        obj = bpy.data.objects[name]
        normals = [tuple(n.vector) for n in obj.data.corner_normals]
        obj.parent = None
        obj.matrix_world.identity()
        origin = PIVOT if name in ("PodLid", "WindowPane") else (0.0, 0.0, 0.0)
        for vertex, position in zip(obj.data.vertices, positions[name]):
            x, y, z = (float(position[i]) - origin[i] for i in range(3))
            vertex.co = (x, -z, y)
        obj.data.normals_split_custom_set([(x, -z, y) for x, y, z in normals])
        obj.location = (origin[0], -origin[2], origin[1])
    for child, parent in (("Couch", "PodBase"), ("Pillow", "PodBase"), ("WindowPane", "PodLid")):
        obj = bpy.data.objects[child]
        frame = obj.matrix_world.copy()
        obj.parent = bpy.data.objects[parent]
        obj.matrix_world = frame
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(
        filepath=str(args.output.resolve()), export_format="GLB", use_selection=True,
        export_yup=True, export_materials="EXPORT", export_cameras=False, export_lights=False,
        export_vertex_color="ACTIVE", export_all_vertex_colors=False,
    )


if __name__ == "__main__":
    main()
