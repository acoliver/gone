"""Export the baked sewn tunic; --assemble fits its surface-mounted dress details."""
import argparse
import json
import math
from pathlib import Path
import sys

import bpy
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SOURCE = HERE / 'tunic-working.blend'
OUT = ROOT / 'assets/props/quarters/dress_uniform.glb'
SCRATCH = ROOT / 'tmp/fit/tunic/sim'
MATERIALS = {}
ATTACHMENTS = {}


def material(name, color, metallic=0, roughness=.7):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Roughness'].default_value = roughness
    return mat


def activate(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def recalc(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def mesh(name, vertices, faces, mat, smooth=True):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    obj['export'] = True
    recalc(obj)
    for p in data.polygons:
        p.use_smooth = smooth
    if mat.name == 'RibbonFabric':
        colors = data.color_attributes.new(name='RibbonColours', type='FLOAT_COLOR', domain='CORNER')
        for color in colors.data:
            color.color = (.40, .025, .045, 1)
    if not data.uv_layers:
        uv = data.uv_layers.new(name='DetailUV')
        for loop in data.loops:
            v = data.vertices[loop.vertex_index].co
            uv.data[loop.index].uv = (v.x + .5, -v.z)
    return obj


def tree(obj):
    obj.data.calc_loop_triangles()
    return BVHTree.FromPolygons([obj.matrix_world @ v.co for v in obj.data.vertices], [tuple(t.vertices) for t in obj.data.loop_triangles], all_triangles=True)


def fair_armholes(body):
    body_vertices, sleeve_vertices = set(), set()
    for polygon in body.data.polygons:
        target = body_vertices if polygon.index < body['body_faces'] else sleeve_vertices
        target.update(polygon.vertices)
    seeds = body_vertices & sleeve_vertices
    weights = {i: 1.0 for i in seeds}
    frontier = seeds
    for weight in [.5, .25]:
        following = set()
        for edge in body.data.edges:
            a, b = edge.vertices
            if a in frontier:
                following.add(b)
            if b in frontier:
                following.add(a)
        following -= weights.keys()
        weights.update({i: weight for i in following})
        frontier = following
    group = body.vertex_groups.new(name='ArmholeStitchFairing')
    for index, weight in weights.items():
        if body.data.vertices[index].co.z < -.20:
            group.add([index], weight, 'REPLACE')
    activate(body)
    modifier = body.modifiers.new('RoundStitchedArmholeReturns', 'SMOOTH')
    modifier.factor = .35
    modifier.iterations = 12
    modifier.vertex_group = group.name
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    recalc(body)


def solidify(obj, thickness, offset=0):
    activate(obj)
    mod = obj.modifiers.new('WoolThickness', 'SOLIDIFY')
    mod.thickness = thickness
    mod.offset = offset
    mod.use_even_offset = False
    bpy.ops.object.modifier_apply(modifier=mod.name)
    recalc(obj)


def hit_front(surface, x, z):
    loc, normal, _, _ = surface.ray_cast(Vector((x, -1, z)), Vector((0, 1, 0)))
    if loc is None:
        raise ValueError(f'No cloth at x={x}, z={z}')
    if normal.y > 0:
        normal.negate()
    return loc, normal


def patch(name, coordinates, faces, surface, mat, offset=.0007, thickness=.0007, dome=None):
    vertices, anchors = [], []
    for i, (x, z) in enumerate(coordinates):
        loc, normal = hit_front(surface, x, z)
        extra = dome(i) if dome else 0
        vertices.append(tuple(loc + normal * (offset + thickness + extra)))
        anchors.append(tuple(loc + normal * offset))
    n = len(vertices)
    vertices += anchors
    closed = list(faces) + [tuple(n + i for i in reversed(f)) for f in faces]
    edge_counts = {}
    for f in faces:
        for a, b in zip(f, f[1:] + f[:1]):
            e = tuple(sorted((a, b)))
            edge_counts[e] = edge_counts.get(e, 0) + 1
    for (a, b), count in edge_counts.items():
        if count == 1:
            closed.append((a, b, n + b, n + a))
    obj = mesh(name, vertices, closed, mat)
    ATTACHMENTS[name] = {'base_vertex_indices': list(range(n, 2 * n)), 'support': 'Collar' if name.startswith('CollarInsignia') else 'TunicBody', 'nominal_offset_m': offset, 'base_blender_m': anchors}
    obj['attachment'] = json.dumps(ATTACHMENTS[name])
    return obj


def rectangle(name, x0, x1, z0, z1, surface, mat, offset=.0007, thickness=.0007, nx=3, nz=8):
    vertices = [(x0 + (x1 - x0) * i / nx, z0 + (z1 - z0) * j / nz) for j in range(nz + 1) for i in range(nx + 1)]
    faces = []
    for j in range(nz):
        for i in range(nx):
            a = j * (nx + 1) + i
            faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    return patch(name, vertices, faces, surface, mat, offset, thickness)


def join_named(objects, name):
    activate(objects[0])
    for obj in objects[1:]:
        obj.select_set(True)
    bpy.ops.object.join()
    obj = bpy.context.object
    obj.name = name
    obj.data.name = name
    return obj


def disc(name, x, z, radius, surface, mat, dome=.0005, sides=32, offset=.0007):
    samples = [tuple(hit_front(surface, x, z)[0])]
    for fraction in [.5, 1.0]:
        for i in range(16):
            angle = 2 * math.pi * i / 16
            samples.append(tuple(hit_front(surface, x + fraction * radius * math.cos(angle), z + fraction * radius * math.sin(angle))[0]))
    points = np.asarray(samples)
    centroid = points.mean(axis=0)
    _, _, vectors = np.linalg.svd(points - centroid)
    normal = Vector(vectors[-1])
    if normal.y > 0:
        normal.negate()
    center = Vector((x, centroid[1] - (normal.x * (x - centroid[0]) + normal.z * (z - centroid[2])) / normal.y, z))
    tangent_x = (Vector((1, 0, 0)) - normal * normal.x).normalized()
    tangent_z = normal.cross(tangent_x).normalized()
    anchors = [center + normal * offset]
    for i in range(sides):
        angle = 2 * math.pi * i / sides
        anchors.append(center + normal * offset + radius * (math.cos(angle) * tangent_x + math.sin(angle) * tangent_z))
    n = len(anchors)
    vertices = [tuple(v + normal * (.0005 + (dome if i == 0 else 0))) for i, v in enumerate(anchors)]
    vertices += [tuple(v) for v in anchors]
    faces = [(0, 1 + i, 1 + (i + 1) % sides) for i in range(sides)]
    faces += [tuple(n + j for j in reversed(f)) for f in list(faces)]
    faces += [(1 + i, 1 + (i + 1) % sides, n + 1 + (i + 1) % sides, n + 1 + i) for i in range(sides)]
    obj = mesh(name, vertices, faces, mat)
    ATTACHMENTS[name] = {'base_blender_m': [tuple(v) for v in anchors], 'support': 'TunicBody', 'nominal_offset_m': offset}
    obj['attachment'] = json.dumps(ATTACHMENTS[name])
    return obj


def neckline(body):
    # The neck is the only upper boundary remaining after side/shoulder stitching.
    counts = {}
    for p in body.data.polygons:
        ids = list(p.vertices)
        for a, b in zip(ids, ids[1:] + ids[:1]):
            e = tuple(sorted((a, b)))
            counts[e] = counts.get(e, 0) + 1
    edges = [e for e, count in counts.items() if count == 1 and all(abs(body.data.vertices[i].co.x) < .105 and body.data.vertices[i].co.z > -.30 for i in e)]
    neighbors = {}
    for a, b in edges:
        neighbors.setdefault(a, []).append(b)
        neighbors.setdefault(b, []).append(a)
    start = min(neighbors)
    loop, prev, current = [], None, start
    while True:
        loop.append(current)
        candidates = [i for i in neighbors[current] if i != prev]
        nxt = candidates[0]
        if nxt == start:
            break
        prev, current = current, nxt
        if len(loop) > len(neighbors):
            raise ValueError('Neck boundary is not a loop')
    return [body.data.vertices[i].co.copy() for i in loop]


def collar(neck_points, surface):
    base = []
    for v in neck_points:
        loc, normal, _, _ = surface.find_nearest(v + Vector((0, 0, .003)))
        base.append(loc + normal * .0005)
    n = len(base)
    vertices = [tuple(v) for v in base]
    vertices += [tuple(v + Vector((0, 0, .043))) for v in base]
    ATTACHMENTS['Collar'] = {'base_blender_m': vertices[:n], 'top_blender_m': vertices[n:], 'support': 'TunicBody', 'nominal_offset_m': .0005}
    faces = [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
    obj = mesh('Collar', vertices, faces, MATERIALS['NaturalFabric'])
    solidify(obj, .003, 0)
    # A recessed fabric facing closes the view into the hanger, with a wire-sized slot.
    top = [Vector(vertices[n + i]) for i in range(n)]
    facing_height = min(v.z for v in top) - .003
    inner = []
    for v in top:
        radial = Vector((v.x, v.y, 0)).normalized() * .0039
        inner.append(Vector((radial.x, radial.y, facing_height)))
    facing_vertices = [tuple(v - Vector((0, 0, .003))) for v in top] + [tuple(v) for v in inner]
    facing_faces = [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
    facing = mesh('CollarFacing', facing_vertices, facing_faces, MATERIALS['NaturalFabric'])
    solidify(facing, .001)
    obj = join_named([obj, facing], 'Collar')
    obj['height_m'] = .043
    return obj


def shoulder_board(name, sign, surface):
    vertices, anchors, faces = [], [], []
    for j in range(9):
        y = -.014 + .028 * j / 8
        for i in range(13):
            x = sign * (.111 + .133 * i / 12)
            loc, normal, _, _ = surface.ray_cast(Vector((x, y, .1)), Vector((0, 0, -1)))
            if loc is None:
                raise ValueError('Shoulder board misses cloth')
            if normal.z < 0:
                normal.negate()
            vertices.append(tuple(loc + normal * .0009))
            anchors.append(tuple(loc + normal * .0009))
    for j in range(8):
        for i in range(12):
            a = j * 13 + i
            faces.append((a, a + 1, a + 14, a + 13))
    obj = mesh(name, vertices, faces, MATERIALS['NaturalFabric'])
    solidify(obj, .0006, 1)
    ATTACHMENTS[name] = {'base_blender_m': anchors, 'support': 'TunicBody', 'nominal_offset_m': .0009}
    obj['attachment'] = json.dumps(ATTACHMENTS[name])
    return obj


def assemble(args):
    bpy.ops.wm.open_mainfile(filepath=str(SCRATCH / f'{args.sleeves}-sleeves.blend'))
    hanger = bpy.data.objects['Hanger']
    hook_top = max((hanger.matrix_world @ v.co).z for v in hanger.data.vertices)
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH':
            for vertex in obj.data.vertices:
                vertex.co.z -= hook_top
    MATERIALS.update({
        'NaturalFabric': material('NaturalFabric', (.018, .031, .064), 0, .85),
        'Brass': material('Brass', (.66, .43, .14), .8, .3),
        'RibbonFabric': material('RibbonFabric', (.36, .035, .055), 0, .8),
        'BareSteel': material('BareSteel', (.43, .47, .52), .85, .27),
    })
    ribbon_material = MATERIALS['RibbonFabric']
    vertex_color = ribbon_material.node_tree.nodes.new('ShaderNodeVertexColor')
    vertex_color.layer_name = 'RibbonColours'
    ribbon_material.node_tree.links.new(vertex_color.outputs['Color'], ribbon_material.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
    body = bpy.data.objects['TunicBody']
    recalc(body)
    fair_armholes(body)
    neck_points = neckline(body)
    # Per-face pattern UVs survive baking, seam joining and the thickness modifier.
    solidify(body, .0035, 0)
    body.data.materials.clear()
    body.data.materials.append(MATERIALS['NaturalFabric'])
    for p in body.data.polygons:
        p.use_smooth = True
    body.data.name = 'TunicBody'
    surface = tree(body)
    collar_obj = collar(neck_points, surface)
    collar_obj['attachment'] = json.dumps(ATTACHMENTS['Collar'])
    collar_surface = tree(collar_obj)
    shoulder_board('ShoulderBoard_L', 1, surface)
    shoulder_board('ShoulderBoard_R', -1, surface)
    rectangle('Placket', -.014, .014, -.83, -.224, surface, MATERIALS['NaturalFabric'], .0009, .0004, 4, 64)
    buttons = [disc('Button', 0, z, .007, surface, MATERIALS['Brass'], .0007) for z in (-.265, -.365, -.465, -.565, -.665, -.765)]
    all_anchors = []
    for obj in buttons:
        all_anchors.extend(json.loads(obj['attachment'])['base_blender_m'])
    button_obj = join_named(buttons, 'Buttons')
    ATTACHMENTS['Buttons'] = {'base_blender_m': all_anchors, 'support': 'TunicBody', 'nominal_offset_m': .0011}
    # The shallow button seats overlap the placket by less than a millimetre.
    for v in button_obj.data.vertices:
        v.co.y -= .0004
    ATTACHMENTS['Buttons']['base_blender_m'] = [[x, y - .0004, z] for x, y, z in all_anchors]
    button_obj['attachment'] = json.dumps(ATTACHMENTS['Buttons'])
    for sign, suffix in [(1, 'L'), (-1, 'R')]:
        x = sign * .048
        # A winged star reads at the 20 mm collar-emblem scale.
        base_points = np.asarray(ATTACHMENTS['Collar']['base_blender_m'])
        front_points = base_points[base_points[:, 1] < 0]
        front_points = front_points[np.argsort(front_points[:, 0])]
        z = float(np.interp(x, front_points[:, 0], front_points[:, 2]) + .0215)
        coords = [(x, z)]
        for i in range(10):
            a = math.pi / 2 + 2 * math.pi * i / 10
            radius = .010 if i % 2 == 0 else .0045
            coords.append((x + radius * math.cos(a), z + radius * math.sin(a)))
        patch('CollarInsignia_' + suffix, coords, [(0, 1 + i, 1 + (i + 1) % 10) for i in range(10)], collar_surface, MATERIALS['Brass'], .0007, .0007)
    ribbon = rectangle('RibbonBar', .073, .143, -.329, -.311, surface, MATERIALS['RibbonFabric'], .0007, .0008, 14, 2)
    # Use vertex colour stripes within the one ribbon material class.
    colors = ribbon.data.color_attributes['RibbonColours']
    for loop in ribbon.data.loops:
        x = ribbon.data.vertices[loop.vertex_index].co.x
        stripe = int((x - .073) / .010) % 3
        colors.data[loop.index].color = [(1, .77, .25, 1), (.20, .35, .8, 1), (.65, .055, .09, 1)][stripe]
    ribbon_parts = [rectangle('MedalRibbon', .098, .118, -.366, -.328, surface, MATERIALS['RibbonFabric'], .0007, .0008, 4, 6)]
    medal = disc('Medal', .108, -.383, .016, surface, MATERIALS['Brass'], .0003, 40, offset=.0005)
    # Raised star on the medal uses the same brass material and remains below 1 mm relief.
    coords = [(.108, -.383)]
    for i in range(10):
        a = math.pi / 2 + 2 * math.pi * i / 10
        r = .010 if i % 2 == 0 else .0045
        coords.append((.108 + r * math.cos(a), -.383 + r * math.sin(a)))
    star = patch('MedalStar', coords, [(0, 1 + i, 1 + (i + 1) % 10) for i in range(10)], tree(medal), MATERIALS['Brass'], .0002, .0003)
    anchors = json.loads(medal['attachment'])['base_blender_m']
    anchors += json.loads(ribbon_parts[0]['attachment'])['base_blender_m']
    medal = join_named([medal, star] + ribbon_parts, 'Medal')
    ATTACHMENTS['Medal'] = {'base_blender_m': anchors, 'support': 'TunicBody', 'nominal_offset_range_m': [.0005, .0007]}
    medal['attachment'] = json.dumps(ATTACHMENTS['Medal'])
    hanger = bpy.data.objects['Hanger']
    hanger.data.materials.clear()
    hanger.data.materials.append(MATERIALS['BareSteel'])
    hanger.data.name = 'Hanger'
    hanger.hide_render = False
    for p in hanger.data.polygons:
        p.use_smooth = True
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH' and not obj.get('export', False):
            obj.hide_render = True
    # Record non-exported collision geometry for exported-surface verification.
    colliders = {}
    for name in ['ShoulderChestForm', 'Hanger']:
        obj = bpy.data.objects[name]
        obj.data.calc_loop_triangles()
        colliders[name] = {'vertices': [list(obj.matrix_world @ v.co) for v in obj.data.vertices], 'faces': [list(t.vertices) for t in obj.data.loop_triangles]}
    trials = json.loads((HERE / 'cloth-trials.json').read_text())
    sleeve_trial = next(t for t in reversed(trials['sleeves']) if t['trial'] == args.sleeves)
    body_trial = next(t for t in reversed(trials['body']) if t['trial'] == sleeve_trial['settings']['body'])
    construction = {
        'colliders_blender': colliders, 'attachments': ATTACHMENTS, 'thickness_m': .0035,
        'simulation': {'body': body_trial, 'sleeves': sleeve_trial},
        'armhole_fairing': {'factor': .35, 'iterations': 12},
    }
    (HERE / 'construction.json').write_text(json.dumps(construction, separators=(',', ':')) + '\n')
    bpy.context.scene.frame_set(1)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE))


def export(path):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH' and obj.get('export', False):
            obj.hide_set(False)
            obj.select_set(True)
            obj.data.name = obj.name
    bpy.context.view_layer.objects.active = bpy.data.objects['TunicBody']
    bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True, export_yup=True, export_apply=False, export_materials='EXPORT', export_cameras=False, export_lights=False, export_extras=True, export_all_vertex_colors=True)


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def render(args):
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
    scene.render.image_settings.file_format = 'PNG'
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.world.use_nodes = True
    scene.world.node_tree.nodes.get('Background').inputs[0].default_value = (.72, .72, .72, 1)
    scene.world.node_tree.nodes.get('Background').inputs[1].default_value = .6
    scene.view_settings.view_transform = 'AgX'
    for name, loc, energy, size in [('Front', (-2, -3, 2), 450, 3), ('Right', (3, -1, .3), 300, 3), ('Back', (0, 3, 2), 450, 3), ('Left', (-3, 1, 0), 250, 3)]:
        data = bpy.data.lights.new(name, 'AREA')
        obj = bpy.data.objects.new(name, data)
        scene.collection.objects.link(obj)
        obj.location = loc
        data.energy = energy
        data.shape = 'DISK'
        data.size = size
        aim(obj, (0, 0, -.4))
    def shot(name, loc, target, scale, size):
        data = bpy.data.cameras.new(name)
        camera = bpy.data.objects.new(name, data)
        scene.collection.objects.link(camera)
        camera.location = loc
        aim(camera, target)
        data.type = 'ORTHO'
        data.ortho_scale = scale
        scene.camera = camera
        scene.render.resolution_x = size
        scene.render.resolution_y = size
        scene.render.filepath = str(SCRATCH / (name + '.png'))
        bpy.ops.render.render(write_still=True)
    shot('hero-render', (1.75, -3.031, .15), (0, 0, -.45), 1.06, 1000)
    for angle in [30, 120, 210, 300]:
        a = math.radians(angle)
        shot(f'turn-{angle}', (3 * math.sin(a), -3 * math.cos(a), .1), (0, 0, -.45), 1.06, 700)
    shot('detail-render', (.2, -3, -.12), (0, -.03, -.25), .43, 1000)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--assemble', action='store_true')
    parser.add_argument('--sleeves', default='sleeve-h')
    parser.add_argument('--render', action='store_true')
    parser.add_argument('--output', type=Path, default=OUT)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    SCRATCH.mkdir(parents=True, exist_ok=True)
    if args.assemble:
        assemble(args)
    else:
        bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    export(args.output)
    if args.render:
        render(args)


if __name__ == '__main__':
    main()
