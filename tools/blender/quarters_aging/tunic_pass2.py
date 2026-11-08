"""Release an armhole seam, deform the sewn pattern, and build ragged tear edges."""
import json
import math

import bmesh
import bpy
import numpy as np
from mathutils import Vector

from common import midsurface, recalc, surface_tree
from fabric_mesh import boundary_loops, fray, material, new_object, replace, thicken


def deformation(point):
    x, y, z = point
    original_x = x
    lower = float(np.clip((-z - .27) / .53, 0, 1))
    lateral = float(np.clip((abs(x) - .025) / .13, 0, 1))
    shoulder = .040 * min(1, max(0, (abs(x) - .105) / .06))
    x = x * (1 - .24 * lower) + .018 * lower ** 2
    y += lateral * lower * (.011 * math.sin(36 * x + 7 * z) + .008 * math.sin(70 * x - 9 * z))
    if abs(original_x) < .32:
        shoulder *= max(1 - math.exp(-(abs(y) / .020) ** 4), float(np.clip((abs(original_x) - .28) / .04, 0, 1)))
    z -= shoulder + .018 * lower * lateral * (.6 + .4 * math.sin(14 * x + 3))
    return np.array((x, y, z))


def detach(vertices, faces, sleeve_start, sleeve_end):
    body_indices = {i for f in faces[:1680] for i in f}
    sleeve_indices = {i for f in faces[sleeve_start:sleeve_end] for i in f}
    cap = body_indices & sleeve_indices
    # Order the shared seam by connectivity, then release a contiguous front arc.
    neighbors = {i: set() for i in cap}
    for f in faces[sleeve_start:sleeve_end]:
        for a, b in zip(f, f[1:] + f[:1]):
            if a in cap and b in cap:
                neighbors[a].add(b)
                neighbors[b].add(a)
    start = min(cap)
    loop, previous, current = [], None, start
    while True:
        loop.append(current)
        nxt = next(i for i in sorted(neighbors[current]) if i != previous)
        if nxt == start:
            break
        previous, current = current, nxt
    n = len(loop)
    count = round(.60 * n)
    # Put the middle of the released run at the most forward point.
    front = min(range(n), key=lambda k: vertices[loop[k]][1])
    released = {loop[(front - count // 2 + k) % n] for k in range(count)}
    duplicates = {}
    for i in released:
        duplicates[i] = len(vertices)
        vertices.append(vertices[i].copy())
    for j in range(sleeve_start, sleeve_end):
        faces[j] = tuple(duplicates.get(i, i) for i in faces[j])
    retained = cap - released
    sleeve_indices = {i for f in faces[sleeve_start:sleeve_end] for i in f}
    anchors = np.asarray([vertices[i] for i in retained])
    centre = np.mean([vertices[i] for i in cap], axis=0)
    for i in sleeve_indices - retained:
        p = np.asarray(vertices[i])
        distance = np.linalg.norm(anchors - p, axis=1).min()
        w = min(1, distance / .090)
        angle = .30 * w
        delta = p - centre
        c, s = math.cos(angle), math.sin(angle)
        p[0] = centre[0] + c * delta[0] - s * delta[1] - .035 * w
        p[1] = centre[1] + s * delta[0] + c * delta[1] - .020 * w
        p[2] -= .026 * w
        vertices[i] = p
    lengths = [float(np.linalg.norm(np.asarray(vertices[a]) - vertices[b])) for a, b in zip(loop, loop[1:] + loop[:1])]
    opened = sum(length for a, b, length in zip(loop, loop[1:] + loop[:1], lengths) if a in released or b in released)
    return {'cap_vertices': n, 'released_vertices': len(released), 'released_reference_length_fraction': opened / sum(lengths),
            'retained_reference_length_m': sum(lengths) - opened, 'reference_seam_length_m': sum(lengths)}


def ragged_edges(obj, seed):
    rng = np.random.default_rng(seed)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.normal_update()
    pattern = bm.loops.layers.uv.active
    boundary = [e for e in bm.edges if e.is_boundary and not any(loop[pattern].uv.x > 1 and loop[pattern].uv.y > .70 for v in e.verts for loop in v.link_loops)]
    # Refine only boundaries; a whole-garment subdivision would waste the triangle budget.
    bmesh.ops.subdivide_edges(bm, edges=boundary, cuts=3, use_grid_fill=False)
    bmesh.ops.triangulate(bm, faces=list(bm.faces), quad_method='BEAUTY', ngon_method='EAR_CLIP')
    bm.normal_update()
    boundary_vertices = {v for e in bm.edges if e.is_boundary for v in e.verts}
    pattern = bm.loops.layers.uv.active
    for v in boundary_vertices:
        sleeve_cuff = any(loop[pattern].uv.x > 1 and loop[pattern].uv.y > .70 for loop in v.link_loops)
        if sleeve_cuff:
            continue
        if v.co.z > -.19 or abs(v.co.x) < .023 or (abs(v.co.x) > .25 and v.co.z < -.70):
            continue
        edges = [e for e in v.link_edges if e.is_boundary]
        neighbors = [e.other_vert(v).co for e in edges]
        tangent = neighbors[1] - neighbors[0]
        outward = v.normal.cross(tangent).normalized()
        limit = min(.0060, .65 * min(e.calc_length() for e in edges))
        displacement = outward * rng.uniform(-limit, limit)
        if v.co.z < -.84:
            # Independent thread failures avoid a regular sawtooth hem.
            displacement.z -= rng.beta(.65, 2.8) * .018
        original = v.co.copy()
        reference = []
        for face in v.link_faces:
            a, b, c = [corner.co for corner in face.verts]
            reference.append((face, (b - a).cross(c - a)))
        # A tear-edge displacement must not fold an incident triangle back over the cloth.
        for fraction in [1, .5, .25, .125, .0625, 0]:
            v.co = original + fraction * displacement
            valid = True
            for face, normal in reference:
                a, b, c = [corner.co for corner in face.verts]
                valid &= (b - a).cross(c - a).dot(normal) >= .20 * normal.length_squared
            if valid:
                break
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bmesh.ops.triangulate(bm, faces=list(bm.faces), quad_method='BEAUTY', ngon_method='EAR_CLIP')
    bm.to_mesh(obj.data)
    bm.free()
    recalc(obj)


def heap(body, seed):
    rng = np.random.default_rng(seed)
    points = np.asarray([v.co[:] for v in body.data.vertices])
    hem_indices = {loop.vertex_index for loop in body.data.loops if body.data.uv_layers.active.data[loop.index].uv.x < 1 and body.data.uv_layers.active.data[loop.index].uv.y < .08}
    hem = points[sorted(hem_indices)]
    centre = (hem[:, :2].min(0) + hem[:, :2].max(0)) / 2
    vertices = [(centre[0], centre[1], -.939)]
    n = 48
    for j in [1, 2, 3, 4]:
        r = j / 4
        for i in range(n):
            a = 2 * math.pi * i / n
            z = -.9498 + .0108 * (1 - r * r) ** 1.5 + (.0003 * math.sin(13 * a) if j < 4 else 0)
            vertices.append((centre[0] + .072 * r * math.cos(a), centre[1] + .047 * r * math.sin(a), z))
    faces = [(0, 1 + i, 1 + (i + 1) % n) for i in range(n)]
    for j in range(3):
        for i in range(n):
            a = 1 + j * n + i
            b = 1 + j * n + (i + 1) % n
            faces.append((a, b, b + n, a + n))
    bottom = len(vertices)
    vertices.append((centre[0], centre[1], -.9498))
    faces += [(bottom, 1 + 3 * n + (i + 1) % n, 1 + 3 * n + i) for i in range(n)]
    dust = new_object('FibreDust', vertices, faces, material('FibreDust', (.27, .24, .19)))
    return {'centre_blender_m': centre.tolist(), 'height_m': .0108, 'diameter_m': .144, 'seed': seed}


def build(seed):
    # The unaged collar facing intersects the collar band. Keep the band and its insignia.
    collar = bpy.data.objects['Collar']
    bm = bmesh.new()
    bm.from_mesh(collar.data)
    remaining, groups = set(bm.verts), []
    while remaining:
        frontier = {remaining.pop()}
        group = set(frontier)
        while frontier:
            following = {e.other_vert(v) for v in frontier for e in v.link_edges} & remaining
            remaining -= following
            group |= following
            frontier = following
        groups.append(group)
    band = max(groups, key=lambda g: max(v.co.z for v in g))
    bmesh.ops.delete(bm, geom=[v for g in groups if g is not band for v in g], context='VERTS')
    bm.to_mesh(collar.data)
    bm.free()
    recalc(collar)
    obj = bpy.data.objects['TunicBody']
    midsurface(obj)
    vertices = [np.asarray(v.co[:]) for v in obj.data.vertices]
    faces = [tuple(p.vertices) for p in obj.data.polygons]
    uv = [[tuple(obj.data.uv_layers.active.data[i].uv) for i in p.loop_indices] for p in obj.data.polygons]
    seam = detach(vertices, faces, 1974, 2268)
    vertices = [deformation(p) for p in vertices]
    # Keep shoulder tears away from the placket, medals and retained back seam.
    kept, kept_uv = [], []
    removed = 0
    for f, pattern in zip(faces, uv):
        p = np.mean([vertices[i] for i in f], axis=0)
        x, y, z = p
        cut = False
        if y < -.010 and abs(x) > .045:
            for cx, cz, width, height in [(-.14, -.285, .026, .077), (.172, -.278, .022, .058), (-.105, -.63, .019, .078), (.14, -.70, .025, .060)]:
                across = x - cx + .10 * (z - cz)
                irregular = 1 + .23 * math.sin(z * 180 + seed) + .16 * math.sin(z * 391)
                if (across / (width * irregular)) ** 2 + ((z - cz) / height) ** 2 < 1:
                    cut = True
        if z < -.85 and abs(x) < .25:
            hem_loss = .008 + .026 * (.5 + .5 * math.sin(x * 77 + seed)) ** 3
            cut |= z < -.900 + hem_loss
        if cut:
            removed += 1
        else:
            kept.append(f)
            kept_uv.extend(pattern)
    replace(obj, vertices, kept, material('NaturalFabric', (.025, .043, .080)))
    for corner, pattern in zip(obj.data.uv_layers.active.data, kept_uv):
        corner.uv = pattern
    ragged_edges(obj, seed)
    loops = boundary_loops(obj.data)
    fibres = fray(obj, seed + 1, probability=.14, length=(.001, .004), max_edge=.015, region=lambda p: abs(p.x) < .20 or p.z > -.82)
    from section_contacts import prune_surface_fibres
    prune_surface_fibres(obj)
    recalc(obj)
    obj['bounded_cloth'] = True
    obj.data.materials[0].use_backface_culling = False
    # All sewn details follow the same deformation, while brass keeps its shape.
    surface = surface_tree(obj)
    for detail in list(bpy.context.scene.objects):
        if detail.type != 'MESH' or detail.name in ['TunicBody', 'Hanger', 'Collar', 'CollarInsignia_L', 'CollarInsignia_R']:
            continue
        positions = np.asarray([detail.matrix_world @ v.co for v in detail.data.vertices])
        if any(mat.name == 'Brass' for mat in detail.data.materials):
            centre = positions.mean(0)
            delta = deformation(centre) - centre
            transformed = positions + delta
        else:
            transformed = np.asarray([deformation(p) for p in positions])
        inverse = detail.matrix_world.inverted()
        for vertex, p in zip(detail.data.vertices, transformed):
            vertex.co = inverse @ Vector(p)
        if detail.name.startswith('ShoulderBoard'):
            sign = 1 if detail.name.endswith('_L') else -1
            verts, board_faces = [], []
            for j in range(9):
                for i in range(13):
                    x, y = sign * (.111 + .133 * i / 12), -.014 + .028 * j / 8
                    hit, _, _, _ = surface.ray_cast(Vector((x, y, .1)), Vector((0, 0, -1)))
                    if hit is None:
                        raise ValueError(f'{detail.name}: unsupported shoulder board at {x}, {y}')
                    verts.append((x, y, hit.z + .003))
            for j in range(8):
                for i in range(12):
                    a = j * 13 + i
                    board_faces.extend([(a, a + 1, a + 14), (a, a + 14, a + 13)])
            n = len(verts)
            verts += [(x, y, z + .0006) for x, y, z in verts]
            uses = {}
            for face in board_faces:
                for a, b in zip(face, face[1:] + face[:1]):
                    key = tuple(sorted((a, b)))
                    uses.setdefault(key, []).append((a, b))
            closed = [tuple(reversed(face)) for face in board_faces] + [tuple(n + i for i in face) for face in board_faces]
            closed += [(a, b, n + b, n + a) for edges in uses.values() if len(edges) == 1 for a, b in edges]
            replace(detail, verts, closed, obj.data.materials[0])
        if detail.name == 'Medal':
            for vertex in detail.data.vertices:
                vertex.co.y -= .0040
        if detail.name == 'Buttons':
            # Original button bases overlap the placket, so lift them to its outer face.
            for vertex in detail.data.vertices:
                vertex.co.y -= .0014
        recalc(detail)
    return {'method': 'Released contiguous armhole stitches, gravity-aligned sleeve displacement and asymmetric sewn-pattern slump, followed by refined ragged boundaries. No cloth simulation claimed.',
            'seam': seam, 'removed_faces': removed, 'boundary_loops_before_fray': len(loops),
            'frays': fibres, 'section': 'Double-sided bounded cloth midsurface; neck, hem, cuffs and actual tears remain explicit boundary loops.', 'heap': heap(obj, seed + 200)}
