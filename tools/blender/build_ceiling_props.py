"""Fit frozen Hunyuan props to unit bounds for metric MultiMesh placements."""
import json
import struct
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'art-source/ceiling-props'
OUTPUT = ROOT / 'assets/props/ceiling'
BUDGETS = {'detector': 3000, 'sprinkler': 3000, 'duct': 2000, 'module': 1500}



def exported_triangles(path):
    raw = path.read_bytes()
    length = struct.unpack_from('<I', raw, 12)[0]
    document = json.loads(raw[20:20 + length])
    return sum(document['accessors'][part['indices']]['count'] // 3
               for mesh in document['meshes'] for part in mesh['primitives'])


def build_duct():
    """Flat sheet body, raised flange rings and a ceiling-reaching strap."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    pieces = []

    def box(center, size):
        bpy.ops.mesh.primitive_cube_add(size=1, location=center)
        obj = bpy.context.object
        obj.scale = size
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        pieces.append(obj)

    # Runtime envelope is 0.8 x 0.35 x 0.44 m, including flanges and hanger.
    width = .40 / .44
    height = .30 / .35
    top = height - .5
    box((0, (top - .5) / 2, 0), (1, height, width))
    for x in [-.48875, .48875, 0]:
        strap = .0225 if x else .0375
        box((x, -.5 + .01 / .35, 0), (strap, .02 / .35, 1))
        box((x, top, 0), (strap, .02 / .35, 1))
        for side in [-1, 1]:
            box((x, (top - .5) / 2, side * (width / 2 + .01 / .44)),
                (strap, height, .02 / .44))
        if x == 0:
            for side in [-1, 1]:
                box((0, (top + .5) / 2, side * (width / 2 + .01 / .44)),
                    (strap, .5 - top, .02 / .44))
            box((0, .5 - .006 / .35, 0), (.10, .012 / .35, 1))
        else:
            for y in [-.5 + .04 / .35, top - .04 / .35]:
                for side in [-1, 1]:
                    bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=4,
                        radius=1, location=(x, y, side * .494))
                    rivet = bpy.context.object
                    rivet.scale = (.010, .008 / .35, .006)
                    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
                    pieces.append(rivet)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in pieces:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = pieces[0]
    bpy.ops.object.join()
    obj = pieces[0]
    obj.name = 'duct'
    for vertex in obj.data.vertices:
        x, y, z = vertex.co
        vertex.co = (x, -z, y)
    material = bpy.data.materials.new('SurfaceRole')
    obj.data.materials.clear()
    obj.data.materials.append(material)
    triangulate = obj.modifiers.new('Triangles', 'TRIANGULATE')
    bpy.ops.object.modifier_apply(modifier=triangulate.name)
    triangles = len(obj.data.polygons)
    assert 0 < triangles <= BUDGETS['duct']
    OUTPUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(OUTPUT / 'duct.glb'), export_format='GLB',
        use_selection=True, export_animations=False, export_extras=True)
    triangles = exported_triangles(OUTPUT / 'duct.glb')
    assert 0 < triangles <= BUDGETS['duct']
    return {'triangles': triangles, 'surfaces': 1, 'bounds': [[-.5]*3, [.5]*3],
            'body_cross_section_m': [.40, .30], 'source': 'tools/blender/build_ceiling_props.py'}

def build(name, budget):
    if name == 'duct':
        return build_duct()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE / name / 'mesh.glb'))
    objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    obj = objects[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    # glTF Y-up -> Blender Z-up is undone before metric fitting.
    points = [Vector((v.co.x, v.co.z, -v.co.y)) for v in obj.data.vertices]
    if name == 'duct':
        points = [Vector((p.z, p.y, -p.x)) for p in points]
    elif name == 'module':
        points = [Vector((p.x, -p.z, p.y)) for p in points]
    low = Vector(tuple(min(p[a] for p in points) for a in range(3)))
    high = Vector(tuple(max(p[a] for p in points) for a in range(3)))
    extent = high - low
    for vertex, point in zip(obj.data.vertices, points):
        p = Vector(tuple((point[a] - low[a]) / extent[a] - .5 for a in range(3)))
        if name in ('detector', 'sprinkler') and p.z < -.40:
            p.z = -.5
        vertex.co = p
    if name == 'module':
        # Cut the generated glass backing out of the armour. Runtime glass
        # retains the existing circuit and lens dimensions behind these slots.
        import bmesh
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        remove = []
        for face in bm.faces:
            center = face.calc_center_median()
            frame = abs(center.x) >= .43 or abs(center.z) >= .36
            louvre = any(abs(center.x - x) < .018 for x in [-.30, -.10, .10, .30])
            if not frame and not louvre:
                remove.append(face)
        bmesh.ops.delete(bm, geom=remove, context='FACES')
        bm.to_mesh(obj.data)
        bm.free()
    modifier = obj.modifiers.new('Budget', 'DECIMATE')
    modifier.ratio = min(1.0, (budget - 16) / max(1, len(obj.data.polygons)))
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    triangulate = obj.modifiers.new('Triangles', 'TRIANGULATE')
    bpy.ops.object.modifier_apply(modifier=triangulate.name)
    # Re-seat the final reduced bounds exactly, including the mounting face.
    for axis in range(3):
        lo = min(v.co[axis] for v in obj.data.vertices)
        hi = max(v.co[axis] for v in obj.data.vertices)
        for vertex in obj.data.vertices:
            vertex.co[axis] = (vertex.co[axis] - lo) / (hi - lo) - .5
    triangles = len(obj.data.polygons)
    if not 0 < triangles <= budget:
        raise ValueError(f'{name}: {triangles} triangles exceeds {budget}')
    obj.name = name
    obj.data.materials.clear()
    material = bpy.data.materials.new('SurfaceRole')
    obj.data.materials.append(material)
    # Convert the fitted runtime Y-up unit mesh to Blender Z-up for export.
    for vertex in obj.data.vertices:
        x, y, z = vertex.co
        vertex.co = (x, -z, y)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    OUTPUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(OUTPUT / f'{name}.glb'), export_format='GLB',
        use_selection=True, export_animations=False, export_extras=True)
    # The exporter omits zero-area faces created by seating a flat back.
    triangles = exported_triangles(OUTPUT / f'{name}.glb')
    if not 0 < triangles <= budget:
        raise ValueError(f'{name}: exported {triangles} triangles exceeds {budget}')
    return {'triangles': triangles, 'surfaces': 1, 'bounds': [[-.5]*3, [.5]*3],
            'source': str((SOURCE / name / 'mesh.glb').relative_to(ROOT))}


def main():
    rows = {name: build(name, budget) for name, budget in BUDGETS.items()}
    (OUTPUT / 'manifest.json').write_text(json.dumps(rows, indent=2) + '\n')
    print(json.dumps(rows, indent=2), flush=True)


if __name__ == '__main__':
    main()
