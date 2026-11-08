"""Tunic-only source preparation and sewn/rigid attachment bindings."""
import json
from pathlib import Path
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / 'tools/blender/quarters_aging'))
from common import collision, midsurface, recalc, surface_tree

DETAILS = ('ShoulderBoard_L', 'ShoulderBoard_R', 'Placket', 'Buttons',
           'RibbonBar', 'Medal', 'CollarInsignia_L', 'CollarInsignia_R')


def load_source():
    bpy.ops.wm.open_mainfile(filepath=str(HERE / 'tunic-working.blend'))
    settings = json.loads((HERE / 'aging.json').read_text())
    retained = set(settings['parts']) | set(settings['colliders'])
    for obj in list(bpy.data.objects):
        if obj.type == 'MESH' and obj.name not in retained:
            bpy.data.objects.remove(obj, do_unlink=True)
    for obj in bpy.context.scene.objects:
        obj.modifiers.clear()
        obj.hide_viewport = False
        obj.hide_set(False)
        obj['aged_export'] = obj.name in settings['parts']
        obj.hide_render = not obj['aged_export']
    form = bpy.data.objects['ShoulderChestForm']
    collision(form, .0015)
    form['aged_export'] = False
    form.hide_render = True
    wire = bpy.data.objects['Hanger']
    collision(wire, .0015)
    collar = bpy.data.objects['Collar']
    sections = components(collar)
    band = max(sections, key=lambda ids: max(collar.data.vertices[i].co.z for i in ids))
    bm = bmesh.new()
    bm.from_mesh(collar.data)
    bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index not in set(band)], context='VERTS')
    bm.to_mesh(collar.data)
    bm.free()
    body = bpy.data.objects['TunicBody']
    midsurface(body)
    recalc(body)
    return body


def components(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    remaining = set(bm.verts)
    result = []
    while remaining:
        frontier = {remaining.pop()}
        group = set(frontier)
        while frontier:
            following = {e.other_vert(v) for v in frontier for e in v.link_edges} & remaining
            remaining -= following
            group |= following
            frontier = following
        result.append(sorted(v.index for v in group))
    bm.free()
    return result


def bind_points(body, points):
    body.data.calc_loop_triangles()
    vertices = np.array([body.matrix_world @ v.co for v in body.data.vertices])
    faces = [tuple(t.vertices) for t in body.data.loop_triangles]
    tree = BVHTree.FromPolygons(vertices.tolist(), faces, all_triangles=True)
    result = []
    for p in points:
        q, _, index, _ = tree.find_nearest(Vector(p))
        tri = faces[index]
        a, b, c = vertices[list(tri)]
        uv = np.linalg.lstsq(np.c_[b-a, c-a], np.asarray(q)-a, rcond=None)[0]
        weights = np.array([1-uv.sum(), *uv])
        result.append({'triangle': tri, 'weights': weights.tolist(),
                       'offset': (np.asarray(p)-weights@vertices[list(tri)]).tolist()})
    return result


def bind_neckline(body, points):
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bm.verts.index_update()
    remaining = {edge for edge in bm.edges if edge.is_boundary}
    necklines = []
    while remaining:
        first = remaining.pop()
        component = {first}
        pending = list(first.verts)
        visited = set(pending)
        while pending:
            vertex = pending.pop()
            for edge in vertex.link_edges:
                if edge in remaining:
                    remaining.remove(edge)
                    component.add(edge)
                    other = edge.other_vert(vertex)
                    if other not in visited:
                        visited.add(other)
                        pending.append(other)
        boundary_points = np.array([vertex.co[:] for vertex in visited])
        if (boundary_points[:, 0].min() < -.03 and boundary_points[:, 0].max() > .03 and
                boundary_points[:, 2].min() > -.25):
            necklines.append(component)
    if len(necklines) != 1:
        raise ValueError(f'Expected one neckline crossing garment centre, found {len(necklines)}')
    edges = sorted(necklines[0], key=lambda edge: edge.index)
    body.data.calc_loop_triangles()
    triangles = [tuple(t.vertices) for t in body.data.loop_triangles]
    result = []
    for p in points:
        candidates = []
        for edge in edges:
            a, b = [np.array(body.matrix_world @ v.co) for v in edge.verts]
            t = float(np.clip((p-a)@(b-a)/((b-a)@(b-a)), 0, 1))
            q = a+t*(b-a)
            candidates.append((float(np.linalg.norm(p-q)), edge, t, q))
        _, edge, t, q = min(candidates, key=lambda item: item[0])
        ids = [v.index for v in edge.verts]
        triangle = next(f for f in triangles if all(i in f for i in ids))
        weights = [1-t if i == ids[0] else t if i == ids[1] else 0. for i in triangle]
        result.append({'triangle': triangle, 'weights': weights, 'offset': (p-q).tolist()})
    bm.free()
    return result


def follow_points(body, entries):
    vertices = np.array([body.matrix_world @ v.co for v in body.data.vertices])
    return np.array([np.array(e['weights'])@vertices[list(e['triangle'])]+e['offset'] for e in entries])


def reinforce_and_bind(body):
    """The collar follows sewn displacements; closed details retain their topology."""
    points = np.array([body.matrix_world @ v.co for v in body.data.vertices])
    patch = body.vertex_groups.get('DetailPatch') or body.vertex_groups.new(name='DetailPatch')
    bindings = {}
    collar = bpy.data.objects['Collar']
    collar_points = np.array([collar.matrix_world @ v.co for v in collar.data.vertices])
    # Bind the whole collar to its sewn lower ring, not the nearby shoulder tops.
    attachment = json.loads(collar['attachment'])
    bases = np.asarray(attachment['base_blender_m'])
    columns = np.asarray(attachment['top_blender_m'])-bases
    fraction = np.clip(np.einsum('ijk,jk->ij', collar_points[:, None]-bases, columns)/
                       np.sum(columns**2, axis=1), 0, 1)
    nearest = np.linalg.norm(collar_points[:, None]-bases-columns*fraction[:, :, None], axis=2).argmin(1)
    sewn = bases[nearest]
    entries = bind_neckline(body, sewn)
    for e, base, offset in zip(entries, sewn, collar_points-sewn):
        # Seat the 3 mm collar just inside the actual neckline. Keeping the
        # old coarse-mesh base offset puts its lower edge through the new ply.
        radial = np.array([base[0], base[1], 0.])
        radial /= np.linalg.norm(radial)
        e['offset'] = (offset-radial*.002).tolist()
    bindings['Collar'] = {'entries': entries, 'original': collar_points.tolist(), 'rigid': False}
    coverage = {}
    for name in DETAILS:
        obj = bpy.data.objects[name]
        original = np.array([obj.matrix_world @ v.co for v in obj.data.vertices])
        groups = components(obj) if name == 'Buttons' else [list(range(len(original)))]
        indices = set()
        for group in groups:
            region = original[group]
            lo, hi = region.min(0)-.005, region.max(0)+.005
            # Reach the support ply, without reinforcing the far side or hem.
            axis = 2 if name.startswith('ShoulderBoard') else 1
            lo[axis], hi[axis] = region[:, axis].min()-.020, region[:, axis].max()+.020
            selected = np.flatnonzero(np.all((points >= lo) & (points <= hi), axis=1))
            if not len(selected):
                center = region.mean(0)
                selected = np.argsort(np.linalg.norm(points-center, axis=1))[:3]
            indices.update(selected.tolist())
        patch.add(sorted(indices), 1., 'REPLACE')
        bindings[name] = {'entries': bind_points(body, original), 'original': original.tolist(),
                          'rigid': True, 'groups': groups, 'patch_vertices': sorted(indices)}
        coverage[name] = len(indices)
    return bindings, coverage


def configure_detail_stiffness(mod):
    s = mod.settings
    s.vertex_group_structural_stiffness = 'DetailPatch'
    s.vertex_group_shear_stiffness = 'DetailPatch'
    s.tension_stiffness_max = max(750., s.tension_stiffness)
    s.compression_stiffness_max = max(750., s.compression_stiffness)
    s.shear_stiffness_max = max(525., s.shear_stiffness)
    s.vertex_group_bending = 'DetailPatch'
    s.bending_stiffness_max = 15.


def fit_details(body, bindings):
    reports = {}
    for name, binding in bindings.items():
        obj = bpy.data.objects[name]
        original = np.asarray(binding['original'])
        destination = follow_points(body, binding['entries'])
        if binding['rigid']:
            for ids in binding['groups']:
                src, dst = original[ids], destination[ids]
                a, b = src.mean(0), dst.mean(0)
                u, _, vt = np.linalg.svd((src-a).T@(dst-b))
                rotation = u@vt
                if np.linalg.det(rotation) < 0:
                    u[:, -1] *= -1
                    rotation = u@vt
                destination[ids] = (src-a)@rotation+b
                # Seat the uncut solid above its support without clipping its faces.
                axis = np.array([0., 0., 1.]) if name.startswith('ShoulderBoard') else np.array([0., -1., 0.])
                normal = axis@rotation
                support_names = (['Collar'] if name.startswith('CollarInsignia') else
                                 ['Placket'] if name == 'Buttons' else
                                 ['RibbonBar'] if name == 'Medal' else [])
                supports = [body]+[bpy.data.objects[n] for n in support_names]
                obj.data.calc_loop_triangles()
                group_ids = set(ids)
                triangles = [t.vertices[:] for t in obj.data.loop_triangles
                             if all(i in group_ids for i in t.vertices)]
                samples = np.vstack([destination[ids], destination[triangles].mean(1)])
                direction = Vector(normal)
                gaps = []
                for support in supports:
                    tree = surface_tree(support)
                    for point in samples:
                        hit, _, _, _ = tree.ray_cast(Vector(point)+direction*.25, -direction, .5)
                        if hit is not None:
                            gaps.append(float((Vector(point)-hit).dot(direction)))
                if not gaps:
                    raise ValueError(f'{name}: rigid detail has no support beneath its footprint')
                destination[ids] += normal*max(0., .0005-min(gaps))
        inverse = obj.matrix_world.inverted()
        for vertex, point in zip(obj.data.vertices, destination):
            vertex.co = inverse @ Vector(point)
        recalc(obj)
        reports[name] = {'vertices': len(destination), 'rigid': binding['rigid'],
                         'extra_collar_lift_m': 0. if name == 'Collar' else None}
    return reports


def boundary_count(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    count = sum(e.is_boundary for e in bm.edges)
    bm.free()
    return count
