"""Tunic fringe categories, released-stitch opacity and floor fibres."""
import math

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree

from bake_down import material_maps
from common import apply, surface_tree
from fabric_mesh import material, new_object
from fringe_cards import fringe_material, image_from_array, strand_atlas
from fringe_boundary import spaced_cards
from tear_opacity import wool_opacity


def edge_groups(body):
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bm.verts.ensure_lookup_table()
    uv = bm.loops.layers.uv[0]
    deform = bm.verts.layers.deform.active
    released = body.vertex_groups['Lip shrink'].index
    categories = {'Hem fringe': set(), 'Seam allowance': set(), 'Long wool fringe': set()}
    for edge in bm.edges:
        if not edge.is_boundary:
            continue
        if (min(v.co.z for v in edge.verts) > -.24 and
                not all(v[deform].get(released, 0.) >= .5 for v in edge.verts)):
            continue
        pattern = np.array([loop[uv].uv[:] for v in edge.verts for loop in v.link_loops])
        seam = (pattern[:, 0].min() > 1.09 and pattern[:, 0].max() < 1.56 and pattern[:, 1].max() < .08)
        seam |= (pattern[:, 0].max() < 1. and pattern[:, 0].min() > .44 and
                 pattern[:, 1].min() > .66 and pattern[:, 1].max() < .96 and
                 sum(v.co.x for v in edge.verts) > .30)
        hem = pattern[:, 0].max() < 1. and pattern[:, 1].max() < .06
        name = 'Seam allowance' if seam else 'Hem fringe' if hem else 'Long wool fringe'
        categories[name].update(v.index for v in edge.verts)
    bm.free()
    for name, ids in categories.items():
        group = body.vertex_groups.get(name) or body.vertex_groups.new(name=name)
        group.remove(list(range(len(body.data.vertices))))
        if ids:
            group.add(sorted(ids), 1., 'REPLACE')
    return categories


def needle_centers(body):
    bm = bmesh.new()
    bm.from_mesh(body.data)
    deform = bm.verts.layers.deform.active
    group = body.vertex_groups['Seam allowance'].index
    edges = {e for e in bm.edges if e.is_boundary and all(v[deform].get(group, 0.) > .5 for v in e.verts)}
    centers = []
    while edges:
        degree = {}
        for edge in edges:
            for v in edge.verts:
                degree[v] = degree.get(v, 0)+1
        current = next((v for v, count in degree.items() if count == 1), next(iter(degree)))
        phase = .001
        while True:
            edge = next((e for e in current.link_edges if e in edges), None)
            if edge is None:
                break
            edges.remove(edge)
            following = edge.other_vert(current)
            a, b = body.matrix_world @ current.co, body.matrix_world @ following.co
            tangent = (b-a).normalized()
            middle = (a+b)/2
            inward = body.matrix_world @ edge.link_faces[0].calc_center_median()-middle
            inward = (inward-tangent*inward.dot(tangent)).normalized()
            length = (b-a).length
            while phase < length:
                centers.append(a+tangent*phase+inward*.0015)
                phase += .002
            phase -= length
            current = following
    bm.free()
    if not centers:
        raise ValueError('Released seam has no stitch-hole centers')
    return centers


def stitch_holes(body, image):
    centers = needle_centers(body)
    tree = KDTree(len(centers))
    for i, point in enumerate(centers):
        tree.insert(point, i)
    tree.balance()
    size = image.size[0]
    rgba = np.empty(size*size*4, dtype=np.float32)
    image.pixels.foreach_get(rgba)
    rgba = rgba.reshape(size, size, 4)
    positions = np.array([body.matrix_world @ v.co for v in body.data.vertices])
    seam = body.vertex_groups['Seam allowance'].index
    weights = np.array([max((g.weight for g in v.groups if g.group == seam), default=0.)
                        for v in body.data.vertices])
    body.data.calc_loop_triangles()
    uv = body.data.uv_layers['BakeUV'].data
    count = 0
    for triangle in body.data.loop_triangles:
        ids = np.array(triangle.vertices)
        if weights[ids].max() < .5:
            continue
        tex = np.array([uv[i].uv[:] for i in triangle.loops])*size
        lo = np.maximum(0, np.floor(tex.min(0)).astype(int))
        hi = np.minimum(size-1, np.ceil(tex.max(0)).astype(int))
        x, y = np.meshgrid(np.arange(lo[0], hi[0]+1)+.5, np.arange(lo[1], hi[1]+1)+.5)
        a, b, c = tex
        det = np.linalg.det(np.array([b-a, c-a]))
        if abs(det) < 1e-12:
            continue
        v = ((x-a[0])*(c[1]-a[1])-(y-a[1])*(c[0]-a[0]))/det
        w = ((b[0]-a[0])*(y-a[1])-(b[1]-a[1])*(x-a[0]))/det
        u = 1-v-w
        inside = (u >= 0) & (v >= 0) & (w >= 0)
        if not inside.any():
            continue
        p = np.c_[u[inside], v[inside], w[inside]] @ positions[ids]
        dot = np.array([tree.find(point)[2] < .00035 for point in p])
        tile = rgba[lo[1]:hi[1]+1, lo[0]:hi[0]+1, :3]
        values = tile[inside]
        values[dot] = 0.
        tile[inside] = values
        count += int(dot.sum())
    # Replace the existing packed bytes as well as the live pixel buffer.
    # Otherwise saved blends retain the pre-stitch mask.
    image.unpack(method='REMOVE')
    image.pixels.foreach_set(rgba.ravel())
    image.save()
    image.reload()
    image.pack()
    return dict(pitch_m=.002, radius_m=.00035, centers=len(centers),
                placement='physical arclength on each released seam lip', transparent_stitch_texels=count)


def wool_fringe(out):
    mat = fringe_material(out, 9521, wool=True)
    rgba, normal = strand_atlas(9521, wool=True, strip_height=128)
    alpha = rgba[:, :, 3]
    padded = np.pad(alpha, ((0, 0), (7, 7)))
    root = np.maximum.reduce([padded[:, i:i+1024] for i in range(15)])
    tips = np.maximum.reduce([padded[:, i:i+1024] for i in range(5, 10)])
    # Bundled roots stay legible; fractional alpha preserves the thinner
    # tips instead of discarding their subpixel coverage.
    blend = np.clip(1-(np.arange(len(alpha)) % 128)/40., 0, 1)[:, None]
    rgba[:, :, 3] = tips+(root-tips)*blend
    gy, gx = np.gradient(rgba[:, :, 3])
    normals = np.stack([-gx*.7, -gy*.7, np.ones_like(gx)], axis=2)
    normals /= np.linalg.norm(normals, axis=2, keepdims=True)
    normal[:, :, :3] = normals*.5+.5
    # Atlas RGB is sRGB, while the wool recipe is linear reflectance.
    linear = np.array([.033, .054, .095])
    srgb = np.where(linear <= .0031308, linear*12.92, 1.055*linear**(1/2.4)-.055)
    rgba[:, :, :3] *= srgb/np.array([.42, .36, .26])
    shader = mat.node_tree.nodes['Principled BSDF']
    shader.inputs['Sheen Weight'].default_value = 0.
    shader.inputs['Specular IOR Level'].default_value = .15
    mat.surface_render_method = 'BLENDED'
    for node in mat.node_tree.nodes:
        if node.type == 'NORMAL_MAP':
            node.inputs['Strength'].default_value = .25
    images = [image_from_array('Tunic wool fibres', rgba, out / 'woolfringe_rgba.png'),
              image_from_array('Tunic wool fibre normals', normal, out / 'woolfringe_normal.png', True)]
    for node in mat.node_tree.nodes:
        if node.type == 'TEX_IMAGE':
            node.image = images[1 if 'Normal' in node.image.name else 0]
            if node.image == images[0]:
                mat.node_tree.links.new(node.outputs['Alpha'], shader.inputs['Alpha'])
    return mat


def rim_modifier(obj, blockers):
    # The edge must disappear with the same lip breakup as its parent sheet.
    rim_mat = obj.data.materials[0].copy()
    rim_mat.name = 'WoolCutEdge'
    rim_mat.use_backface_culling = False
    # Rim UVs collapse onto the lip line and have no tangent-space basis.
    for link in list(rim_mat.node_tree.nodes['Principled BSDF'].inputs['Normal'].links):
        rim_mat.node_tree.links.remove(link)
    obj.data.materials.append(rim_mat)
    source = obj.data.attributes.new(name='Wool rim source', type='INT', domain='POINT')
    source.data.foreach_set('value', np.arange(len(obj.data.vertices), dtype=np.int32))
    rim = obj.modifiers.new('Rim-only 3 mm wool', 'SOLIDIFY')
    rim.use_rim_only = True
    rim.thickness = .003
    # Offset zero also moves the retained sheet by half the thickness. Keep
    # the baked/collision-tested surface fixed and put the cut edge inward.
    rim.offset = -1.
    rim.use_even_offset = False
    rim.use_quality_normals = True
    rim.thickness_clamp = 1.
    rim.use_thickness_angle_clamp = True
    rim.vertex_group = thickness_weights(obj, blockers)
    rim.thickness_vertex_group = 0.
    rim.material_offset_rim = len(obj.data.materials)-1
    return rim


def thickness_weights(obj, blockers):
    from mathutils.bvhtree import BVHTree
    obj.data.calc_loop_triangles()
    positions = [obj.matrix_world @ v.co for v in obj.data.vertices]
    faces = [tuple(t.vertices) for t in obj.data.loop_triangles]
    tree = BVHTree.FromPolygons(positions, faces, all_triangles=True)
    supports = [surface_tree(blocker) for blocker in blockers]
    neighbors = {i: {i} for i in range(len(positions))}
    for edge in obj.data.edges:
        a, b = edge.vertices
        neighbors[a].add(b)
        neighbors[b].add(a)
    group = obj.vertex_groups.get('Wool edge compression') or obj.vertex_groups.new(name='Wool edge compression')
    for index, point in enumerate(positions):
        gaps = [distance for _, _, face, distance in tree.find_nearest_range(point, .0036)
                if not neighbors[index].intersection(faces[face])]
        # Both opposing cut edges extrude into this gap; reserve half for each.
        weight = min(1., .45*min(gaps)/.003) if gaps else 1.
        inward = -(obj.matrix_world.to_3x3() @ obj.data.vertices[index].normal).normalized()
        for support in supports:
            hit, _, _, distance = support.ray_cast(point, inward, .0036)
            if hit is not None:
                weight = min(weight, .9*distance/.003)
        group.add([index], weight, 'REPLACE')
    return group.name


def finish_cards(out, record):
    body = bpy.data.objects['TunicBody']
    categories = edge_groups(body)
    opacity, report = wool_opacity(body, out / 'textures/tunic_opacity.png',
                                   size=record.get('finish_opacity_size', 2048), seed=9521)
    report['stitch_holes'] = stitch_holes(body, opacity)
    material_maps(body.data.materials[0], (.025, .043, .08), opacity_image=opacity)
    fringe = wool_fringe(out / 'textures')
    record['fringe'] = {}
    sheets = [body]+[bpy.data.objects[p['name']] for p in record['fallen']]
    from wool_material import wool_material
    record['wool_materials'] = {
        sheet.name: wool_material(sheet, out / 'textures', opacity if sheet == body else None,
                                  color=(.045, .061, .085) if 'pass10' in record and sheet != body else (.025, .043, .08))
        for sheet in sheets}
    # Test placements against the actual rim geometry without losing the open
    # midsurface from which the cards and their UV categories are constructed.
    rim_proxies = []
    rim_blockers = [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.get('aged_export')]
    rim_blockers.append(bpy.data.objects['AgingFloorCollider'])
    for sheet in sheets:
        proxy = sheet.copy()
        proxy.data = sheet.data.copy()
        bpy.context.collection.objects.link(proxy)
        proxy['aged_export'] = False
        apply(proxy, rim_modifier(proxy, [o for o in rim_blockers if o != sheet]))
        rim_proxies.append(proxy)
    from detail_clearance import seat_details
    record['rim_detail_clearance'] = seat_details(rim_proxies[0], record['bindings'])
    objects = [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.get('aged_export') and o not in sheets]+rim_proxies
    objects.append(bpy.data.objects['AgingFloorCollider'])
    for number, name in enumerate(categories):
        if not categories[name]:
            record['fringe'][name] = {'cards': 0, 'authored_coverage': 0.}
            continue
        obj, measured = spaced_cards(body, fringe, 9521+number, wool=name != 'Seam allowance',
                                     group_name=name, blockers=objects)
        obj.name = name.replace(' ', '')
        obj['aged_export'] = True
        objects.append(obj)
        record['fringe'][name] = measured
    record['fallen_fringe'] = {}
    for i, sheet in enumerate(sheets[1:]):
        obj, measured = spaced_cards(sheet, fringe, 9540+i, wool=True, blockers=objects)
        obj['aged_export'] = True
        objects.append(obj)
        record['fallen_fringe'][sheet.name] = measured
    from reduced_clearance import compress_rim
    record['rim_contacts'] = {}
    for sheet in sheets:
        count = len(sheet.data.vertices)
        apply(sheet, rim_modifier(sheet, [o for o in rim_blockers if o != sheet]))
        record['rim_contacts'][sheet.name] = compress_rim(sheet, count)
    for proxy in rim_proxies:
        objects.remove(proxy)
        bpy.data.objects.remove(proxy, do_unlink=True)
    objects.extend(sheets)
    record['opacity'] = report
    from common import surface_tree
    from card_contacts import CardContacts
    mound = bpy.data.objects['FibreDust']
    tree = surface_tree(mound)
    print('FRINGE', record['fringe'], record['fallen_fringe'], flush=True)
    print('CARD BLOCKERS', [(o.name, len(o.data.polygons)) for o in objects], flush=True)
    contacts = CardContacts(objects)
    rng = np.random.default_rng(9521)
    vertices, faces, patterns = [], [], []
    for _ in range(300):
        x, y = rng.uniform([-.10, -.045], [.10, .045])
        hit, normal, _, _ = tree.ray_cast(Vector((x, y, -.8)), Vector((0, 0, -1)))
        if hit is None:
            continue
        center = hit+normal*.0005
        angle = rng.uniform(0, math.tau)
        side = Vector((-math.sin(angle), math.cos(angle), 0))*.0007
        length = rng.uniform(.003, .008)
        rise = Vector((math.cos(angle)*length, math.sin(angle)*length, rng.uniform(.0007, .002)))
        quad = [center-side, center+side, center+side+rise, center-side+rise]
        if not contacts.clear(quad):
            continue
        contacts.add(quad)
        i = len(vertices)
        vertices.extend(quad)
        faces.append((i, i+1, i+2, i+3))
        variant = int(rng.integers(8))
        patterns.append([(0, variant/8), (1, variant/8), (1, (variant+1)/8), (0, (variant+1)/8)])
        if len(faces) == (50 if 'pass10' in record else 65):
            break
    fibre = new_object('HeapFibres', vertices, faces, fringe)
    for polygon, pattern in zip(fibre.data.polygons, patterns):
        for i in polygon.loop_indices:
            fibre.data.uv_layers.active.data[i].uv = pattern[fibre.data.loops[i].vertex_index % 4]
    fibre['aged_export'] = True
    record['heap_fibre_cards'] = len(faces)
    return record
