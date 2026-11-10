"""Sewn-pattern, finish and export operations shared by the two clothing props."""
import json
import math
from pathlib import Path
import sys

import bpy
import bmesh
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
ASSETS = ROOT / 'assets/props/quarters'
SCRATCH = ROOT / 'tmp/clothes'
sys.path.insert(0, str(ROOT / 'tools/blender/quarters_aging'))
from common import activate, collision, export, recalc, save
from fringe_cards import image_from_array


def mesh(name, vertices, faces, edges=(), uv=None):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, edges, faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj['aged_export'] = True
    layer = data.uv_layers.new(name='SewnPattern')
    for loop in data.loops:
        p = data.vertices[loop.vertex_index].co
        layer.data[loop.index].uv = uv[loop.vertex_index] if uv is not None else (p.x * 8, p.z * 8)
    for face in data.polygons:
        face.use_smooth = True
    return obj


def tube(name, points, radius=.0025, sides=8):
    vertices, faces = [], []
    for i, p in enumerate(points):
        tangent = (Vector(points[min(i + 1, len(points)-1)]) - Vector(points[max(0, i-1)])).normalized()
        axis = Vector(tuple(1 if k == min(range(3), key=lambda j: abs(tangent[j])) else 0 for k in range(3)))
        u = tangent.cross(axis).normalized()
        v = tangent.cross(u).normalized()
        for j in range(sides):
            a = 2 * math.pi * j / sides
            vertices.append(tuple(Vector(p) + radius * (math.cos(a)*u + math.sin(a)*v)))
        if i:
            for j in range(sides):
                a=(i-1)*sides+j;b=(i-1)*sides+(j+1)%sides
                faces.append((a,b,b+sides,a+sides))
    faces.extend([tuple(reversed(range(sides))),tuple((len(points)-1)*sides+j for j in range(sides))])
    return mesh(name, vertices, faces)


def fabric(name, color, prop, aged=False):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = (*color, 1)
    mat.use_backface_culling = False
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Roughness'].default_value = .98 if aged else .85
    shader.inputs['Sheen Weight'].default_value = .12 if aged else .25
    # Reuse the approved generated yarn, removing its pigment before tinting.
    source = bpy.data.images.load(str(ASSETS / 'sofa/weave.png'), check_existing=True)
    pixels = np.array(source.pixels[:], dtype=np.float32).reshape(source.size[1], source.size[0], 4)
    grain = pixels[:, :, :3].mean(2)
    grain = np.clip(grain / np.median(grain), .65, 1.35)
    rgba = np.ones_like(pixels)
    rgba[:, :, :3] = np.asarray(color) * (.88 + .12 * grain[:, :, None])
    out = ASSETS / f'{prop}_textures'
    out.mkdir(parents=True, exist_ok=True)
    image = image_from_array(name + '_weave', rgba, out / (name.lower() + '.png'))
    texture = mat.node_tree.nodes.new('ShaderNodeTexImage')
    texture.image = image
    mat.node_tree.links.new(texture.outputs['Color'], shader.inputs['Base Color'])
    normal = bpy.data.images.load(str(ASSETS / 'bed_soft_textures/wool_weave_normal.png'), check_existing=True)
    normal.pack()
    n = mat.node_tree.nodes.new('ShaderNodeTexImage')
    n.image = normal
    n.image.colorspace_settings.name = 'Non-Color'
    bump = mat.node_tree.nodes.new('ShaderNodeNormalMap')
    bump.inputs['Strength'].default_value = .22
    mat.node_tree.links.new(n.outputs['Color'], bump.inputs['Color'])
    mat.node_tree.links.new(bump.outputs['Normal'], shader.inputs['Normal'])
    return mat


def plain(name, color, metal=0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = (*color, 1)
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Metallic'].default_value = metal
    shader.inputs['Roughness'].default_value = .65
    mat.use_backface_culling = False
    return mat


def load_support(prop):
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(ASSETS / f'{prop}.glb'))
    objects = [o for o in bpy.context.scene.objects if o not in before and o.type == 'MESH']
    for obj in objects:
        collision(obj, .0005)
        obj['aged_export'] = False
        obj['support'] = True
    return objects


def retain_pattern(obj):
    source = obj.copy()
    source.data = obj.data.copy()
    source.modifiers.clear()
    source.name = obj.name + '_CutPattern'
    bpy.context.collection.objects.link(source)
    source['aged_export'] = False
    source.hide_render = True
    source.hide_set(True)
    return source


def solve(obj, pins, frames=180, sewing=True, aged=False, quality=14, time_scale=.35, collide=True, self_collide=True):
    scene = bpy.context.scene
    scene.frame_set(1)
    group = obj.vertex_groups.get('SupportStitches') or obj.vertex_groups.new(name='SupportStitches')
    for index, weight in pins.items():
        group.add([index], weight, 'REPLACE')
    mod = obj.modifiers.new('SewnClothGravity', 'CLOTH')
    s = mod.settings
    s.quality = quality
    s.time_scale = time_scale
    s.mass = .18
    s.tension_stiffness = 350
    s.compression_stiffness = 350
    s.shear_stiffness = 240
    s.bending_stiffness = .55 if aged else .25
    s.tension_damping = 12
    s.compression_damping = 12
    s.shear_damping = 12
    s.bending_damping = 2
    s.air_damping = 8
    s.vertex_group_mass = group.name
    s.use_sewing_springs = sewing
    s.sewing_force_max = 6
    c = mod.collision_settings
    c.use_collision = collide
    c.use_self_collision = self_collide
    c.distance_min = .001
    # Two 2 mm exclusions would force the retained 3 mm two-ply fold apart.
    c.self_distance_min = .001 if aged else .002
    c.collision_quality = 8
    excluded = set()
    for edge in obj.data.edges:
        if edge.is_loose:
            excluded.update(edge.vertices)
    seam_vertices = excluded.copy()
    for face in obj.data.polygons:
        if seam_vertices.intersection(face.vertices):
            excluded.update(face.vertices)
    if excluded:
        g = obj.vertex_groups.new(name='SewingPlyExclusions')
        g.add(sorted(excluded), 1, 'REPLACE')
        c.vertex_group_self_collisions = g.name
    mod.point_cache.frame_end = frames
    previous = None
    for frame in range(1, frames + 1):
        scene.frame_set(frame)
        evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        if frame == frames - 5:
            previous = np.array([v.co[:] for v in evaluated.data.vertices])
        if frame % 30 == 0:
            print(obj.name, 'cloth frame', frame, flush=True)
    positions = np.array([v.co[:] for v in evaluated.data.vertices])
    record = {'frames': frames, 'quality': s.quality, 'time_scale': s.time_scale,
              'sewing': sewing, 'sewing_force_max': s.sewing_force_max,
              'bending_stiffness': s.bending_stiffness, 'pin_count': len(pins),
              'self_collision_distance_m':c.self_distance_min,
              'colliders_active':c.use_collision,'self_collision_active':c.use_self_collision,
              'last_five_frames_motion_m': float(np.linalg.norm(positions - previous, axis=1).max())}
    baked = bpy.data.meshes.new_from_object(evaluated, depsgraph=bpy.context.evaluated_depsgraph_get())
    obj.modifiers.clear()
    obj.data = baked
    scene.frame_set(1)
    return record


def weld_seams(obj, pairs):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    gap = max(((bm.verts[a].co - bm.verts[b].co).length for a, b in pairs), default=0)
    mapping = {}
    for a, b in pairs:
        va, vb = bm.verts[a], bm.verts[b]
        va.co = (va.co + vb.co) / 2
        mapping[vb] = va
    bmesh.ops.weld_verts(bm, targetmap=mapping)
    loose = [e for e in bm.edges if not e.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='EDGES')
    bm.to_mesh(obj.data)
    bm.free()
    recalc(obj)
    return gap


def cut(obj, predicate):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    doomed = [f for f in bm.faces if predicate(f.calc_center_median())]
    area = sum(f.calc_area() for f in doomed)
    count = len(doomed)
    bmesh.ops.delete(bm, geom=doomed, context='FACES')
    bm.to_mesh(obj.data)
    bm.free()
    return {'removed_faces': count, 'lost_area_m2': area}


def fringe(obj, mat, seed, minimum_z=0, maximum_z=100, axis_limit=None, blockers=()):
    from card_contacts import CardContacts
    contacts=CardContacts(blockers) if blockers else None
    shortened,omitted=0,0
    rng = np.random.default_rng(seed)
    counts = {}
    for f in obj.data.polygons:
        ids = list(f.vertices)
        for a, b in zip(ids, ids[1:] + ids[:1]):
            edge = tuple(sorted((a, b)))
            counts[edge] = counts.get(edge, 0) + 1
    vertices, faces = [], []
    for (a, b), count in counts.items():
        if count != 1:
            continue
        p, q = obj.data.vertices[a].co, obj.data.vertices[b].co
        middle = (p + q) / 2
        if not minimum_z < middle.z < maximum_z:
            continue
        tangent = (q - p).normalized()
        for t in (.18, .47, .79):
            root = p.lerp(q, t)
            tip = root + Vector((rng.normal(0, .002), rng.normal(0, .002), -rng.uniform(.006, .024)))
            width = rng.uniform(.0004, .0010)
            placement=None
            for factor in (1.,.6,.3,.1,.05):
                end=root+(tip-root)*factor
                quad=[root-tangent*width,root+tangent*width,end+tangent*width*.12,end-tangent*width*.12]
                if axis_limit is not None and any(not axis_limit[0]<v.x<axis_limit[1] for v in quad):continue
                if contacts is None or contacts.clear(quad):
                    placement=quad
                    shortened+=factor<1
                    break
            if placement is None:
                omitted+=1
                continue
            quad=placement
            start = len(vertices)
            vertices.extend(tuple(v) for v in quad)
            faces.append(tuple(start + i for i in range(4)))
    result = mesh(obj.name + '_FrayedYarns', vertices, faces)
    result.data.materials.append(mat)
    result['collision_shortened_yarns']=int(shortened)
    result['collision_omitted_yarns']=omitted
    return result


def deposit(name, center, extent, mat, seed, count=120,height=.006):
    rng = np.random.default_rng(seed)
    vertices, faces = [], []
    for i in range(count):
        angle = rng.uniform(0, 2 * math.pi)
        radius = math.sqrt(rng.random())
        x = center[0] + extent[0] * radius * math.cos(angle)
        y = center[1] + extent[1] * radius * math.sin(angle)
        z = center[2]
        width = rng.uniform(.001, .004)
        length = rng.uniform(.004, .019)
        a = rng.uniform(0, 2 * math.pi)
        u = Vector((math.cos(a), math.sin(a), 0)) * length / 2
        v = Vector((-math.sin(a), math.cos(a), 0)) * width / 2
        h = .001 + height * (1 - radius) ** 2
        p = Vector((x, y, z))
        start = len(vertices)
        vertices.extend(tuple(q) for q in (p-u-v, p+u-v, p+u+v, p-u+v, p+Vector((0,0,h))))
        faces.extend((start+j,start+(j+1)%4,start+4) for j in range(4))
    obj = mesh(name, vertices, faces)
    obj.data.materials.append(mat)
    obj['deposit'] = True
    return obj


def bake_transforms(obj):
    activate(obj)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    obj['aged_export'] = True


def native_bounds():
    points = np.array([tuple(obj.matrix_world @ v.co) for obj in bpy.context.scene.objects
                       if obj.type == 'MESH' and obj.get('aged_export') for v in obj.data.vertices])
    return [points.min(0).tolist(), points.max(0).tolist()]


def save_state(here, prop, state, record):
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH' and obj.get('aged_export'):
            recalc(obj)
    record['bounds_blender_native_m'] = native_bounds()
    (here / f'{state}.json').write_text(json.dumps(record, indent=2) + '\n')
    save(here / f'{prop}-{state}.blend', record)
    export(ASSETS / f'{prop}{"_aged" if state == "aged" else ""}.glb')
