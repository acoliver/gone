"""Extend the existing released armhole edges into small curled seam allowances."""
import bmesh
import numpy as np
from mathutils import Vector

from common import recalc
from fabric_mesh import material
from wear_pass10 import ragged_erosion, smoothstep


def released_side(edge, layer):
    if not edge.is_boundary:
        return None
    pattern = np.array([loop[layer].uv[:] for vertex in edge.verts for loop in vertex.link_loops])
    if pattern[:, 0].min() > 1.09 and pattern[:, 0].max() < 1.56 and pattern[:, 1].max() < .001:
        return 'sleeve'
    if (pattern[:, 0].max() < 1. and pattern[:, 1].min() > .66 and pattern[:, 1].max() < .96 and
            min(np.max(np.abs(pattern[:, 0]-.46)), np.max(np.abs(pattern[:, 0]-.97))) < .003):
        return 'body'
    return None


def ragged_shoulders(body):
    bm = bmesh.new()
    bm.from_mesh(body.data)
    layer = bm.loops.layers.uv[0]
    deform = bm.verts.layers.deform.active
    release = body.vertex_groups['Lip shrink'].index
    def shoulder(edge):
        if not edge.is_boundary or not all(v[deform].get(release, 0.) >= .5 for v in edge.verts):
            return False
        uv = np.array([loop[layer].uv[:] for v in edge.verts for loop in v.link_loops])
        return uv[:, 0].max() < 1. and np.max(np.abs(uv[:, 1]-.94)) < .001 and min(v.co.x for v in edge.verts) > .075
    edges = [edge for edge in bm.edges if shoulder(edge)]
    for edge in edges:
        cuts = max(0, int(np.ceil(edge.calc_length()/.0018))-1)
        if cuts:
            bmesh.ops.subdivide_edges(bm, edges=[edge], cuts=cuts, use_grid_fill=False)
    edges = [edge for edge in bm.edges if shoulder(edge)]
    chains = {side: [] for side in ['front', 'back']}
    for edge in edges:
        uv = np.array([loop[layer].uv[:] for v in edge.verts for loop in v.link_loops])
        side = 'front' if uv[:, 0].mean() < .48 else 'back'
        points = np.array([v.co[:] for v in edge.verts])
        erosion = .001+.007*ragged_erosion(points, 9527 if side == 'front' else 9534)/.0065
        erosion *= smoothstep((points[:, 0]-.15)/.020)
        chains[side].append((points, erosion))
    moved = 0
    maximum = 0.
    bm.normal_update()
    normals = {vertex: vertex.normal.copy() for vertex in bm.verts}
    for vertex in bm.verts:
        uv = next(iter(vertex.link_loops))[layer].uv
        if uv.x >= 1. or uv.y < .84 or vertex.co.x < .145:
            continue
        side = 'front' if uv.x < .48 else 'back'
        candidates = []
        point = np.array(vertex.co)
        for (a, b), erosion in chains[side]:
            t = np.clip((point-a)@(b-a)/((b-a)@(b-a)), 0, 1)
            distance = np.linalg.norm(point-a-(b-a)*t)
            candidates.append((distance, erosion[0]*(1-t)+erosion[1]*t))
        if not candidates:
            continue
        distance, erosion = min(candidates, key=lambda item: item[0])
        motion = float(erosion*smoothstep(1-distance/.018))
        curl = .0045*float(smoothstep(1-distance/.008)*smoothstep((point[0]-.15)/.020))
        vertex.co.z -= motion
        vertex.co += normals[vertex]*curl
        maximum = max(maximum, motion)
        moved += motion > 0
    bm.to_mesh(body.data)
    bm.free()
    recalc(body)
    return dict(moved_vertices=moved, maximum_lip_loss_m=maximum, maximum_authored_curl_m=.0045,
                method='refined shoulder lips with irregular 1 to 8 mm losses and a soft 4.5 mm outward roll')


def add_allowances(body):
    bm = bmesh.new()
    bm.from_mesh(body.data)
    pattern = bm.loops.layers.uv[0]
    edges = [edge for edge in bm.edges if released_side(edge, pattern)]
    original_count = len(bm.faces)
    for edge in edges:
        cuts = max(0, int(np.ceil(edge.calc_length()/.0018))-1)
        if cuts:
            bmesh.ops.subdivide_edges(bm, edges=[edge], cuts=cuts, use_grid_fill=False)
    bm.normal_update()
    edges = [edge for edge in bm.edges if released_side(edge, pattern)]
    vertices = {v for edge in edges for v in edge.verts}
    roots, sides, outward, normals, uvs = {}, {}, {}, {}, {}
    for v in vertices:
        key = tuple(v.co)
        roots[key] = v
        adjacent = [edge for edge in v.link_edges if edge in edges]
        sides[key] = released_side(adjacent[0], pattern)
        directions = []
        for edge in adjacent:
            a, b = [p.co for p in edge.verts]
            tangent = (b-a).normalized()
            inward = edge.link_faces[0].calc_center_median()-(a+b)/2
            inward = (inward-tangent*inward.dot(tangent)).normalized()
            directions.append(-inward)
        outward[key] = sum(directions, Vector()).normalized()
        normals[key] = v.normal.copy()
        uvs[key] = {layer.name: next(iter(v.link_loops))[layer].uv.copy() for layer in bm.loops.layers.uv}
    root_positions = {side: np.array([key for key in roots if sides[key] == side]) for side in ['body', 'sleeve']}
    allowance = material('Exposed wool seam allowance', (.034, .051, .084))
    allowance.use_backface_culling = False
    shader = allowance.node_tree.nodes['Principled BSDF']
    shader.inputs['Roughness'].default_value = .97
    shader.inputs['Specular IOR Level'].default_value = .12
    body.data.materials.append(allowance)
    index = len(body.data.materials)-1
    result = bmesh.ops.extrude_edge_only(bm, edges=edges)
    new_vertices = [element for element in result['geom'] if isinstance(element, bmesh.types.BMVert)]
    root_keys = {v: tuple(v.co) for v in new_vertices}
    for face in result['geom']:
        if not isinstance(face, bmesh.types.BMFace):
            continue
        face.material_index = index
        face.smooth = True
        for loop in face.loops:
            key = tuple(loop.vert.co)
            for name, uv in uvs[key].items():
                loop[bm.loops.layers.uv[name]].uv = uv
    widths = []
    for vertex, key in root_keys.items():
        point = np.asarray(key)
        opposite = root_positions['sleeve' if sides[key] == 'body' else 'body']
        clearance = float(np.linalg.norm(opposite-point, axis=1).min())
        erosion = ragged_erosion(point[None], 9562)[0]
        width = (.002+.009*erosion/.0065)*(1. if sides[key] == 'body' else .55)
        width *= float(smoothstep((clearance-.006)/.014))
        width = max(width, .00025)
        curl = .0018*np.sin(width/.011*np.pi)*float(smoothstep((clearance-.006)/.014))
        vertex.co += outward[key]*width+normals[key]*curl
        widths.append(width)
    bm.to_mesh(body.data)
    bm.free()
    recalc(body)
    return dict(root_spacing_m=.0018, extended_vertices=len(new_vertices),
                minimum_maximum_width_m=[min(widths), max(widths)],
                added_polygons=len(body.data.polygons)-original_count,
                construction='connected extrusion of the existing armhole lips, with curled ragged allowance')
