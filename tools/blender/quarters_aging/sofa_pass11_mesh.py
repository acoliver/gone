"""Broad physical openings and local sofa shape changes in Blender's Z-up frame."""
import bmesh
import numpy as np
from mathutils import Vector

from common import recalc
from sofa_pass9_finish import points

def simplify_boundary(obj, tolerance=.0004):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    remaining = {e for e in bm.edges if e.is_boundary}
    remove = set()
    def retained(chain):
        if len(chain) <= 2:
            return set(chain)
        p = np.array([v.co[:] for v in chain])
        delta = p[-1]-p[0]
        length = np.sum(delta*delta)
        t = np.clip(np.sum((p-p[0])*delta, axis=1)/length, 0, 1) if length else np.zeros(len(p))
        distances = np.linalg.norm(p-p[0]-t[:, None]*delta, axis=1)
        index = int(distances.argmax())
        if distances[index] <= tolerance:
            return {chain[0], chain[-1]}
        return retained(chain[:index+1]) | retained(chain[index:])
    while remaining:
        first = min(remaining, key=lambda e: tuple(e.verts[0].co))
        start, current = first.verts[0], first.verts[0]
        chain = [start]
        while True:
            edge = next((e for e in current.link_edges if e in remaining), None)
            if edge is None:
                break
            remaining.remove(edge)
            current = edge.other_vert(current)
            chain.append(current)
            if current == start:
                break
        remove.update(set(chain)-retained(chain))
    bmesh.ops.dissolve_verts(bm, verts=list(remove), use_face_split=False, use_boundary_tear=False)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bmesh.ops.dissolve_degenerate(bm, dist=.000002, edges=list(bm.edges))
    bm.to_mesh(obj.data)
    bm.free()
    recalc(obj)
    return dict(removed_vertices=len(remove), chord_tolerance_m=tolerance)



def surface_area(obj):
    obj.data.calc_loop_triangles()
    triangles = points(obj)[np.array([t.vertices[:] for t in obj.data.loop_triangles])]
    return float(np.linalg.norm(np.cross(triangles[:, 1]-triangles[:, 0], triangles[:, 2]-triangles[:, 0]), axis=1).sum()/2)


def set_points(obj, positions):
    inverse = obj.matrix_world.inverted()
    for vertex, position in zip(obj.data.vertices, positions, strict=True):
        vertex.co = inverse@Vector(position)
    recalc(obj)


def seat_bowl(positions, centre, amount):
    result = np.array(positions, copy=True)
    x = np.clip((result[:, 0]-centre)/.29, -1., 1.)
    y = np.clip((result[:, 1]+.08)/.36, -1., 1.)
    # Leave the already collapsed middle above its support. Lift the loose
    # perimeter into a separate shallow bowl for each seat instead of flattening it.
    result[:, 2] += amount*(.8*x*x+.2*y*y)
    return result


def lean_back(obj, degrees, floor=.415):
    before = surface_area(obj)
    original = points(obj)
    centre = np.array([original[:, 0].mean(), .35, .44])
    angle = np.radians(degrees)
    rotation = np.array([[1, 0, 0], [0, np.cos(angle), -np.sin(angle)], [0, np.sin(angle), np.cos(angle)]])
    result = np.einsum('ij,kj->ik', original-centre, rotation)+centre
    result[:, 2] += floor-result[:, 2].min()
    set_points(obj, result)
    return dict(method='rigid forward pitch and lowered ties, no envelope scaling', degrees=degrees,
                area_ratio=surface_area(obj)/before, matrix=rotation.tolist(),
                translation=(result[0]-original[0]@rotation.T).tolist())


def fill_small_wear(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    remaining = {e for e in bm.edges if e.is_boundary}
    filled = []
    while remaining:
        edge = min(remaining, key=lambda e: tuple(e.verts[0].co))
        remaining.remove(edge)
        pending, loop = [edge], {edge}
        while pending:
            for vertex in pending.pop().verts:
                for other in vertex.link_edges:
                    if other in remaining:
                        remaining.remove(other)
                        loop.add(other)
                        pending.append(other)
        p = np.array([v.co[:] for e in loop for v in e.verts])
        length = sum(e.calc_length() for e in loop)
        component = set(e.link_faces[0] for e in loop)
        pending_faces = list(component)
        while pending_faces:
            for e in pending_faces.pop().edges:
                for face in e.link_faces:
                    if face not in component:
                        component.add(face)
                        pending_faces.append(face)
        component_boundary = {e for face in component for e in face.edges if e.is_boundary}
        if loop == component_boundary:
            continue
        if length < .50 and np.ptp(p, axis=0).max() < .19:
            result = bmesh.ops.holes_fill(bm, edges=list(loop), sides=0)
            filled.append(dict(perimeter_m=length, faces=len(result['faces'])))
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    recalc(obj)
    return filled


def gash_field(positions, spec):
    delta = np.asarray(positions)-np.asarray(spec['centre'])
    u, v = delta@spec['tangent'], delta@spec['across']
    along = u/spec['half_length']
    phase = spec['seed']*.137
    taper = np.sqrt(np.maximum(0., 1.-along*along))
    broad = .72+.24*np.sin(along*7+phase)+.13*np.sin(along*17+phase*.7)
    rag = .0035*np.sin(u*1450+phase)+.0018*np.sin(u*3300+phase*.31)
    width = np.maximum(.001, spec['half_width']*broad+rag*spec.get('rag_scale', 1.))*taper
    field = np.maximum(np.abs(u)-spec['half_length'], np.abs(v)-width)
    if 'depth_max' in spec:
        field = np.maximum(field, np.asarray(positions)[:, 1]-spec['depth_max'])
    return field


def cut_gash(obj, spec, spacing=.004):
    before = surface_area(obj)
    groups = {name: (obj.vertex_groups.get(name) or obj.vertex_groups.new(name=name)).index
              for name in ['Lip shrink', 'Panel tear', 'Broad gash']}
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    deform = bm.verts.layers.deform.verify()
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    def position(vertex):
        return np.array(tuple(obj.matrix_world@vertex.co))
    def near(edge):
        p = np.array([position(v) for v in edge.verts])
        delta = p-np.asarray(spec['centre'])
        u, v = delta@spec['tangent'], delta@spec['across']
        return (u.min() < spec['half_length']+.012 and u.max() > -spec['half_length']-.012 and
                v.min() < spec['half_width']+.015 and v.max() > -spec['half_width']-.015)
    for _ in range(6):
        edges = [e for e in bm.edges if e.calc_length() > spacing and near(e)]
        if not edges:
            break
        bmesh.ops.subdivide_edges(bm, edges=edges, cuts=1, use_grid_fill=True)
        bmesh.ops.triangulate(bm, faces=list(bm.faces))
    values = {v: float(gash_field([position(v)], spec)[0]) for v in bm.verts}
    roots = {v for v, value in values.items() if abs(value) < 1e-8}
    for vertex in roots:
        values[vertex] = 0.
    for edge in list(bm.edges):
        a, b = edge.verts
        if values[a]*values[b] >= 0:
            continue
        pa, pb = position(a), position(b)
        low, high = 0., 1.
        for _ in range(22):
            middle = (low+high)/2
            value = gash_field([pa+(pb-pa)*middle], spec)[0]
            if (value > 0) == (values[a] > 0):
                low = middle
            else:
                high = middle
        factor = (low+high)/2
        length = (b.co-a.co).length
        if factor*length < .000002:
            vertex = a
        elif (1-factor)*length < .000002:
            vertex = b
        else:
            _, vertex = bmesh.utils.edge_split(edge, a, factor)
        values[vertex] = 0.
        roots.add(vertex)
    for face in list(bm.faces):
        crossing = [v for v in face.verts if v in roots]
        if len(crossing) == 2:
            bmesh.utils.face_split(face, *crossing)
    remove = [f for f in bm.faces if any(values[v] < -1e-9 for v in f.verts)]
    bmesh.ops.delete(bm, geom=remove, context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bmesh.ops.dissolve_degenerate(bm, dist=.000002, edges=list(bm.edges))
    lips = {v for v in roots if v.is_valid and v.is_boundary}
    for v in lips:
        for group in groups.values():
            v[deform][group] = 1.
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bm.normal_update()
    lip_points = np.array([position(v) for v in lips])
    lip_edges = sum(e.is_boundary and all(v in lips for v in e.verts) for e in bm.edges)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    recalc(obj)
    delta = lip_points-spec['centre']
    return dict(removed_area_m2=before-surface_area(obj), lip_edges=lip_edges,
                opening_span_m=float(np.ptp(np.einsum('ij,j->i', delta, spec['tangent']))),
                opening_width_m=float(np.ptp(np.einsum('ij,j->i', delta, spec['across']))), spec=spec)


def curl_gashes(obj, amplitude=.005):
    from mathutils.kdtree import KDTree
    original = points(obj)
    group = obj.vertex_groups['Broad gash'].index
    ids = [v.index for v in obj.data.vertices if any(g.group == group and g.weight > .5 for g in v.groups)]
    tree = KDTree(len(ids))
    for index in ids:
        tree.insert(original[index], index)
    tree.balance()
    distance = np.array([tree.find(p)[2] for p in original])
    weights = np.maximum(0., 1-distance/.015)
    phase = original[:, 0]*85+original[:, 1]*63+original[:, 2]*91
    normal = np.array([obj.matrix_world.to_3x3()@v.normal for v in obj.data.vertices])
    result = original+normal*(weights*(amplitude+.002*np.sin(phase)))[:, None]
    set_points(obj, result)
    return dict(lift_range_m=[amplitude-.002, amplitude+.002], band_m=.015,
                moved_vertices=int((weights > 0).sum()))
