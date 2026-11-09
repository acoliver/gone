"""Batch 3 closed-part fitting, paired finishes and saved-source export."""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'tools/blender/quarters/wardrobe'))
import batch_tools as bt

COLORS = {
    'PaintedSteel': (.12, .18, .16, 1), 'BareSteel': (.42, .47, .46, 1),
    'Brass': (.57, .34, .09, 1), 'Ceramic': (.77, .74, .64, 1),
    'Glaze': (.065, .11, .08, 1), 'HardPlastic': (.12, .18, .14, 1),
    'IvoryPlastic': (.72, .70, .58, 1), 'BluePlastic': (.08, .18, .23, 1),
    'Display': (.007, .012, .014, 1), 'Rubber': (.018, .024, .021, 1),
    'Leather': (.055, .033, .023, 1), 'Lining': (.15, .025, .035, 1),
    'Bristle': (.39, .26, .12, 1), 'Ribbon': (.40, .045, .035, 1),
    'RibbonIvory': (.65, .61, .45, 1), 'Stain': (.77, .74, .64, 1),
}


def mats():
    result = {}
    for name, color in COLORS.items():
        metal = .7 if name in {'BareSteel', 'Brass'} else .15 if name == 'PaintedSteel' else 0
        rough = .25 if name in {'Ceramic', 'Glaze', 'Display'} else .42
        result[name] = bt.material(name, color, metal, rough)
        if name == 'Display':
            result[name].node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 0
    return result


def box(name, dims, center, mat, bevel=.001):
    assert bevel < min(dims)/2, f'{name}: bevel must leave a nonzero straight edge'
    obj = bt.panel(name, dims, center, mat, 0)
    bt.bevel(obj, bevel, 1)
    return obj


def lathe(name, profile, mat, sides=24, band_mats=None):
    # Endpoints on the axis are single poles, rather than degenerate rings.
    vertices = []
    rings = []
    for radius, z in profile:
        if radius == 0:
            rings.append([len(vertices)])
            vertices.append((0, 0, z))
        else:
            rings.append(list(range(len(vertices), len(vertices) + sides)))
            vertices.extend((radius * math.cos(i * math.tau / sides),
                             radius * math.sin(i * math.tau / sides), z) for i in range(sides))
    faces = []
    bands = []
    for band, (a, b) in enumerate(zip(rings, rings[1:])):
        for i in range(sides):
            j = (i + 1) % sides
            if len(a) == 1:
                faces.append((a[0], b[j], b[i]))
            elif len(b) == 1:
                faces.append((a[i], a[j], b[0]))
            else:
                faces.append((a[i], a[j], b[j], b[i]))
            bands.append(band)
    obj = bt.cage(name, vertices, faces, mat, 0)
    for band, material in (band_mats or {}).items():
        obj.data.materials.append(material)
        slot = len(obj.data.materials) - 1
        for poly, section in zip(obj.data.polygons, bands):
            if section == band:
                poly.material_index = slot
    for face in obj.data.polygons:
        face.use_smooth = abs(face.normal.z) < .995
    return obj


def tube(name, centers, radius, mat, sides=6):
    vertices = []
    for i, point in enumerate(centers):
        tangent = Vector(centers[min(i+1, len(centers)-1)]) - Vector(centers[max(0, i-1)])
        tangent.normalize()
        across = tangent.cross(Vector((0, 1, 0))).normalized()
        second = tangent.cross(across).normalized()
        vertices.extend(tuple(Vector(point) + radius * (math.cos(k*math.tau/sides)*across +
                            math.sin(k*math.tau/sides)*second)) for k in range(sides))
    faces = [tuple(reversed(range(sides)))]
    for i in range(len(centers)-1):
        faces.extend((i*sides+k, i*sides+(k+1)%sides,
                      (i+1)*sides+(k+1)%sides, (i+1)*sides+k) for k in range(sides))
    faces.append(tuple(range((len(centers)-1)*sides, len(centers)*sides)))
    obj = bt.cage(name, vertices, faces, mat, 0)
    for face in obj.data.polygons:
        face.use_smooth = len(face.vertices) == 4
    return obj


def image_material(name, image_path, roughness=.65):
    mat = bt.material(name, (1, 1, 1, 1), 0, roughness)
    nodes = mat.node_tree.nodes
    image = nodes.new('ShaderNodeTexImage')
    image.image = bpy.data.images.load(str(image_path), check_existing=True)
    image.image.pack()
    mat.node_tree.links.new(image.outputs['Color'], nodes.get('Principled BSDF').inputs['Base Color'])
    return mat


def photo_uv(obj):
    uv = obj.data.uv_layers.active or obj.data.uv_layers.new(name='UVMap')
    for poly in obj.data.polygons:
        if poly.normal.y < -.99:
            for loop in poly.loop_indices:
                v = obj.data.vertices[obj.data.loops[loop].vertex_index].co
                uv.data[loop].uv = (v.x/.162 + .5, v.z/.112 + .5)


def aged_material(clean, item):
    name = clean.name.split('.')[0]
    if name == 'PhotoPrint':
        return image_material('PhotoPrint_Aged', ROOT/'assets/props/quarters/textures/photo_frame/print_aged.png', .9)
    if name == 'Glass':
        mat = bt.material('Glass_Aged', (.61, .55, .42, .21), 0, .78)
        mat.surface_render_method = 'DITHERED'
        mat.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value = .21
        return mat
    texture = ROOT / 'assets/props/quarters/textures' / item / (name + '_aged.png')
    mat = image_material(name + '_Aged', texture, .88)
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Metallic'].default_value = .12 if name in {'Brass', 'BareSteel', 'PaintedSteel'} else 0
    nodes = mat.node_tree.nodes
    normal_path = texture.with_name(name + '_normal.png')
    if normal_path.exists():
        tex = nodes.new('ShaderNodeTexImage')
        tex.image = bpy.data.images.load(str(normal_path), check_existing=True)
        tex.image.colorspace_settings.name = 'Non-Color'
        tex.image.pack()
        normal = nodes.new('ShaderNodeNormalMap')
        mat.node_tree.links.new(tex.outputs['Color'], normal.inputs['Color'])
        mat.node_tree.links.new(normal.outputs['Normal'], shader.inputs['Normal'])
    return mat


def normalize(objects):
    bpy.context.view_layer.update()
    coords = [o.matrix_world @ v.co for o in objects for v in o.data.vertices]
    lo = Vector([min(p[i] for p in coords) for i in range(3)])
    hi = Vector([max(p[i] for p in coords) for i in range(3)])
    offset = Vector(((lo.x+hi.x)/2, (lo.y+hi.y)/2, lo.z))
    for obj in objects:
        obj.location -= offset
    bpy.context.view_layer.update()
    return [[lo.x-offset.x, lo.z-offset.z, -hi.y+offset.y],
            [hi.x-offset.x, hi.z-offset.z, -lo.y+offset.y]]


def main(script, item, assemble, deform=None):
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--assemble', action='store_true')
    parser.add_argument('--state', choices=['remembered', 'aged'], default='remembered')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--render', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    folder = Path(script).resolve().parent
    output = args.output or ROOT / f'assets/props/quarters/{item}{"_aged" if args.state == "aged" else ""}.glb'
    if args.assemble:
        bt.reset()
        assemble(mats())
        objects = [o for o in bpy.context.scene.objects if o.type == 'MESH' and not o.name.startswith('Guide_')]
        for obj in objects:
            obj['quarters_prop'] = item
        bounds = normalize(objects)
        bt.unwrap(objects)
        if item == 'photo_frame':
            photo_uv(bpy.data.objects['PhotoPlate'])
        root = bt.empty(item)
        root['age_years'] = 0
        root['front'] = 'Blender -Y; exported glTF +Z'
        for obj in objects:
            bt.attach(obj, root)
        bpy.context.preferences.filepaths.save_version = 0
        clean_source = folder / f'{item}-working.blend'
        bpy.ops.wm.save_as_mainfile(filepath=str(clean_source))
        bt.export(ROOT/f'assets/props/quarters/{item}.glb', objects+[root])
        if args.render:
            capture(item, 'remembered', bounds)
        # Captures add lights and cameras, never asset geometry.
        cache = {}
        for obj in objects:
            for slot in obj.material_slots:
                clean = slot.material
                if clean.name not in cache:
                    cache[clean.name] = aged_material(clean, item)
                slot.material = cache[clean.name]
        if deform:
            deform(objects)
        root['age_years'] = 1000
        bpy.ops.wm.save_as_mainfile(filepath=str(folder/f'{item}-aged.blend'))
        bt.export(ROOT/f'assets/props/quarters/{item}_aged.glb', objects+[root])
        if args.render:
            capture(item, 'aged', bounds)
            dust_control(item, objects, bounds)
        construction = {'id': item, 'bounds_gltf': bounds, 'triangle_limit': 4000 if item=='boots' else 1500,
                        'required_nodes': [o.name for o in objects],
                        'axis_contract': 'Blender +Z up/-Y front, export_yup=True -> glTF +Y up/+Z front',
                        'age_years': 1000, 'base_origin': [0,0,0]}
        (folder/'construction.json').write_text(json.dumps(construction, indent=2)+'\n')
    else:
        source = folder / f'{item}-{"aged" if args.state == "aged" else "working"}.blend'
        bpy.ops.wm.open_mainfile(filepath=str(source))
        objects = [o for o in bpy.context.scene.objects if o.get('quarters_prop') == item]
        objects.append(bpy.data.objects[item])
        bt.export(output, objects)


def capture(item, state, bounds):
    # CPU rendering does not contend with the shared MLX GPU queue.
    for obj in list(bpy.data.objects):
        if obj.type in {'LIGHT', 'CAMERA'}:
            bpy.data.objects.remove(obj, do_unlink=True)
    size = [bounds[1][i]-bounds[0][i] for i in range(3)]
    d = max(size)
    folder = ROOT/f'docs/art/quarters/sheets/{item}/{state}'
    bt.render(folder, (size[0],size[1],size[2]), hero=(-d*1.5,-d*2.8,d*2.5),
              target=(0,0,size[1]*.48), angles=(), scale=1.45)


def dust_control(item, objects, bounds):
    swapped = []
    glass = []
    materials = {slot.material for obj in objects for slot in obj.material_slots}
    for mat in materials:
        if mat.name == 'Glass_Aged':
            shader = mat.node_tree.nodes['Principled BSDF']
            glass.append((shader, shader.inputs['Base Color'].default_value[:],
                          shader.inputs['Roughness'].default_value))
            shader.inputs['Base Color'].default_value = (.72,.83,.85,.045)
            shader.inputs['Roughness'].default_value = .075
            shader.inputs['Alpha'].default_value = .045
        for node in mat.node_tree.nodes:
            if node.type != 'TEX_IMAGE' or not node.image:
                continue
            control = ROOT/'tmp/small'/item/'no_dust'/Path(node.image.filepath).name
            if control.is_file():
                swapped.append((node,node.image))
                node.image = bpy.data.images.load(str(control),check_existing=True)
    capture(item, 'dust-disabled-control', bounds)
    for node,image in swapped:
        node.image = image
    for shader,color,roughness in glass:
        shader.inputs['Base Color'].default_value = color
        shader.inputs['Roughness'].default_value = roughness
        shader.inputs['Alpha'].default_value = .21
