"""Lay the pilot's lifted shoulder tongue forward, with a small downward roll."""
import numpy as np


def smoothstep(value):
    t = np.clip(value, 0, 1)
    return t*t*(3-2*t)


def replacement_motion(t, free):
    t = np.clip(np.asarray(t), 0, 1)
    weight = smoothstep(t)*free
    delta = np.zeros((len(t), 3))
    delta[:, 0] = .010*weight
    delta[:, 1] = -.016*weight
    delta[:, 2] = -.014*weight+free*(.004*np.sin(np.pi*t)-.003*smoothstep((t-.7)/.3))
    return delta


def counterlip_motion(t, free):
    weight = smoothstep(t)*free
    delta = np.zeros((len(t), 3))
    delta[:, 1] = .012*weight
    delta[:, 2] = -.014*weight
    return delta


def rest_field(source):
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    from polish_pass9 import vertex_pattern
    bpy.ops.wm.open_mainfile(filepath=str(source))
    body, board = bpy.data.objects['TunicBody'], bpy.data.objects['ShoulderBoard_L']
    pattern = vertex_pattern(body)
    points = np.array([v.co[:] for v in body.data.vertices])
    tree = BVHTree.FromObject(board, bpy.context.evaluated_depsgraph_get())
    inverse = board.matrix_world.inverted()
    clearance = np.array([tree.find_nearest(inverse @ (body.matrix_world @ v.co))[3]
                          for v in body.data.vertices])
    x = points[:, 0]
    free = smoothstep((x-.180)/.020)*smoothstep((.255-x)/.025)
    free *= (pattern[:, 0] < .48)*smoothstep((clearance-.008)/.006)
    t = np.clip((pattern[:, 1]-.90)/.04, 0, 1)
    delta = replacement_motion(t, free)
    rear = smoothstep((x-.165)/.025)*smoothstep((.255-x)/.025)
    rear *= (pattern[:, 0] > .48)*(pattern[:, 0] < 1.)
    delta += counterlip_motion(t, rear)
    body.data.calc_loop_triangles()
    faces = np.array([t.vertices[:] for t in body.data.loop_triangles])
    tex = pattern[faces]
    a, b = tex[:, 1]-tex[:, 0], tex[:, 2]-tex[:, 0]
    area = a[:, 0]*b[:, 1]-a[:, 1]*b[:, 0]
    faces = faces[np.abs(area) > 1e-12]
    uvpoints = np.column_stack([pattern, np.zeros(len(pattern))])
    tree = BVHTree.FromPolygons(uvpoints.tolist(), faces.tolist(), all_triangles=True)
    from mathutils.geometry import barycentric_transform
    def sample(uv):
        if uv[0] >= 1. or uv[1] <= .75:
            return np.zeros(3)
        point, _, index, distance = tree.find_nearest(Vector((*uv, 0.)))
        ids = faces[index]
        value = barycentric_transform(point, *[Vector(uvpoints[i]) for i in ids],
                                      *[Vector(delta[i]) for i in ids])
        if distance > .0001:
            raise ValueError(f'Shoulder pattern sample lies outside the rest field: {uv}, {distance}')
        return np.array(value)
    return sample


def reorient_rim(body, before, used, faces, delta):
    import bpy
    from mathutils import Vector
    source = body.data.attributes['Wool rim source'].data
    roots = {}
    for index, vertex in enumerate(used):
        roots.setdefault(source[vertex].value, []).append((vertex, index))
    mesh = bpy.data.meshes.new('Draped rim supports')
    mesh.from_pydata([body.data.vertices[i].co[:] for i in used], [], faces)
    mesh.update()
    sheet_vertices = set(used)
    incident = [[] for _ in used]
    for face in mesh.polygons:
        for index in face.vertices:
            incident[index].append(np.array(face.normal))
    def inward(index):
        direction = -np.array(mesh.vertices[index].normal)
        for _ in range(32):
            for normal in incident[index]:
                penetration = float(direction @ normal)+.02
                if penetration > 0:
                    direction -= penetration*normal
            direction /= np.linalg.norm(direction)
            if max(direction @ normal for normal in incident[index]) < 0:
                return Vector(direction)
        raise ValueError(f'Shoulder rim has no inward normal cone at {index}')
    for vertex in body.data.vertices:
        if vertex.index in sheet_vertices:
            continue
        candidates = roots[source[vertex.index].value]
        root, normal_index = min(candidates, key=lambda pair: np.linalg.norm(before[vertex.index]-before[pair[0]]))
        worn = before[root, 0] > .14 and before[root, 2] > -.35
        if np.linalg.norm(delta[root]) <= 1e-8 and not worn:
            continue
        thickness = np.linalg.norm(before[vertex.index]-before[root])
        if worn:
            thickness = min(thickness, .00035)
        vertex.co = body.data.vertices[root].co+inward(normal_index)*thickness
    bpy.data.meshes.remove(mesh)
    body.data.update()
    from reduced_clearance import crossing_pairs, surface
    history = []
    for _ in range(16):
        pairs = crossing_pairs(body)
        history.append(len(pairs))
        if not pairs:
            return dict(crossings=history, minimum_rim_m=.0001, worn_shoulder_maximum_rim_m=.00035)
        _, triangles, _ = surface(body)
        tips = {int(v) for i, j in pairs for v in np.r_[triangles[i], triangles[j]]
                if v not in sheet_vertices}
        if not tips:
            raise ValueError('Draped midsurface intersects itself')
        for index in tips:
            root, _ = min(roots[source[index].value], key=lambda pair: np.linalg.norm(before[index]-before[pair[0]]))
            base = body.data.vertices[root].co
            offset = body.data.vertices[index].co-base
            body.data.vertices[index].co = base+offset.normalized()*max(.0001, offset.length*.5)
        body.data.update()
    raise ValueError(f'Draped rim compression did not clear crossings: {history}')


def drape(body, sheet, sample):
    import bpy
    from polish_pass9 import vertex_pattern
    from mathutils import Vector
    pattern = vertex_pattern(body)
    before = np.array([v.co[:] for v in body.data.vertices])
    delta = np.array([sample(uv) for uv in pattern])
    from mathutils.bvhtree import BVHTree
    clearance = np.full(len(before), np.inf)
    for name in ['ShoulderBoard_L', 'ShoulderBoard_R', 'Hanger']:
        support = bpy.data.objects[name]
        tree = BVHTree.FromObject(support, bpy.context.evaluated_depsgraph_get())
        inverse = support.matrix_world.inverted()
        distances = [tree.find_nearest(inverse @ (body.matrix_world @ vertex.co))[3]
                     for vertex in body.data.vertices]
        clearance = np.minimum(clearance, distances)
    region = smoothstep((before[:, 0]-.14)/.03)*smoothstep((before[:, 2]+.35)/.05)
    delta *= (region*smoothstep((clearance-.008)/.010))[:, None]
    seam = body.vertex_groups['Seam allowance'].index
    retained_armhole = np.array([any(g.group == seam and g.weight >= .5 for g in vertex.groups)
                                for vertex in body.data.vertices])
    delta[retained_armhole] = 0
    if not np.isfinite(delta).all():
        raise ValueError('Rest-pattern drape produced nonfinite motion')
    for vertex, change in zip(body.data.vertices, delta):
        vertex.co += Vector(change)
    body.data.update()
    # Rebuild the gate sheet from the changed surface, excluding solidified rims.
    from tear_boundaries import release_weights
    body.data.calc_loop_triangles()
    triangles = [t for t in body.data.loop_triangles if body.data.polygons[t.polygon_index].material_index == 0]
    faces = np.array([t.vertices[:] for t in triangles])
    used, inverse = np.unique(faces, return_inverse=True)
    rim = reorient_rim(body, before, used, inverse.reshape(-1, 3), delta)
    sheet.update(vertices=np.array([body.matrix_world @ body.data.vertices[i].co for i in used]),
                 faces=inverse.reshape(-1, 3), released=release_weights(body)[used],
                 uv=np.array([[body.data.uv_layers[0].data[i].uv[:] for i in t.loops] for t in triangles]))
    return dict(moved_vertices=int(np.sum(np.linalg.norm(delta, axis=1) > 1e-8)),
                maximum_motion_m=float(np.linalg.norm(delta, axis=1).max()),
                curl_height_m=.004, tip_droop_m=.003, rim=rim,
                construction='Lower the former upright tongue 14 mm, lay it forward 16 mm and outward 10 mm, with a 4 mm local roll and 3 mm downturned tip; droop the counterlip 14 mm and back 12 mm; pin delivered fitting and hanger supports')
