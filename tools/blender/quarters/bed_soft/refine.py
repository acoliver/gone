"""Finish the retained aged simulation without changing the remembered source."""
import json
from pathlib import Path
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build import ASSETS, bake_origin, unwrap
from age import clear_left_rail
from common import activate, export, midsurface, recalc, save, solidify, surface_tree
from fabric_mesh import new_object
from finish_aged import retain_material
from fringe_cards import cards, fringe_material, image_from_array
from powder_cards import powder_card
from refinement_fields import convex_outline, powder_field, powder_normals, without_foot_corner, fringe_groups
from stress_cut import cut_faces

TEXTURES = ASSETS / 'bed_soft_aged_textures'


def components(bm):
    remaining = set(bm.verts)
    result = []
    while remaining:
        first = min(remaining, key=lambda v: v.index)
        remaining.remove(first)
        frontier, group = {first}, {first}
        while frontier:
            following = {e.other_vert(v) for v in frontier for e in v.link_edges} & remaining
            remaining -= following
            group |= following
            frontier = following
        result.append(group)
    return result


def isolate(mattress, name, predicate):
    obj = mattress.copy()
    obj.data = mattress.data.copy()
    bpy.context.collection.objects.link(obj)
    obj.name = name
    retain_material(obj, predicate)
    return obj


def crust_plates(foam):
    bm = bmesh.new()
    bm.from_mesh(foam.data)
    bm.verts.index_update()
    groups = components(bm)
    vertices, faces, plates = [], [], []
    for index, group in enumerate(groups):
        outline = without_foot_corner(convex_outline(np.array([v.co[:2] for v in group])))
        if len(outline) < 3:
            continue
        center = outline.mean(axis=0)
        scale = .975 if .15 < center[0] < .55 and -.4 < center[1] < .15 else .994
        outline = center + (outline - center) * scale
        basin = np.exp(-((center[0] - .20) / .40) ** 2 - ((center[1] + .10) / .45) ** 2)
        following = np.roll(outline, -1, axis=0)
        area = abs((outline[:, 0] * following[:, 1] - outline[:, 1] * following[:, 0]).sum()) / 2
        plates.append((index, outline, center, basin, area))
    offsets = np.array([.005 * basin * np.sin(index * 3.1) for index, _, _, basin, _ in plates])
    # Different plate levels reveal fracture edges without adding filling volume.
    offsets -= np.average(offsets, weights=[p[4] for p in plates])
    for offset, (index, outline, center, basin, _) in zip(offsets, plates):
        top = .5455 - .012 * basin + .0008 * np.sin(index * 2.39) + offset
        n, start = len(outline), len(vertices)
        for point in outline:
            vertices.append((*point, .5001))
        for point in outline:
            vertices.append((*point, top - .0035))
        inset = center + (outline - center) * .975
        for k, point in enumerate(inset):
            vertices.append((*point, top + .0016 * np.sin(k * 2.1 + index)))
        vertices.append((*center, top + .0013 * np.sin(index * 8.3) - .0003))
        faces.append(tuple(start + k for k in reversed(range(n))))
        for k in range(n):
            j = (k + 1) % n
            faces.extend([(start + k, start + j, start + n + j, start + n + k),
                          (start + n + k, start + n + j, start + 2*n + j, start + 2*n + k),
                          (start + 2*n + k, start + 2*n + j, start + 3*n)])
    bm.free()
    data = bpy.data.meshes.new('CompactedExistingCrustPlates')
    data.from_pydata(vertices, [], faces)
    data.materials.append(bpy.data.materials['Foam'])
    foam.data = data
    recalc(foam)
    return {'plates': len(plates), 'upper_surface_max_m': max(v[2] for v in vertices),
            'rail_top_m': .55, 'support_z_m': .5001, 'footprints_from_existing_plates': True,
            'missing_foot_corner_x_minus_y_m': 1.35,
            'plate_offset_range_m': [float(offsets.min()), float(offsets.max())],
            'plate_offset_area_weighted_mean_m': float(np.average(offsets, weights=[p[4] for p in plates]))}


def crust_crumbs(foam):
    tree = surface_tree(foam)
    rng = np.random.default_rng(95263)
    vertices, faces = [], []
    for _ in range(30):
        center = rng.uniform([.03, -.60], [.60, .32])
        angle = rng.uniform(0, 2 * np.pi) + np.arange(3) * 2 * np.pi / 3
        size = rng.uniform(.005, .011)
        xy = center + np.c_[np.cos(angle), np.sin(angle)] * size
        hits = [tree.ray_cast(Vector((*p, .7)), Vector((0, 0, -1)))[0] for p in xy]
        if any(hit is None for hit in hits):
            continue
        base = [Vector((p[0], p[1], hit.z + .0008)) for p, hit in zip(xy, hits)]
        start = len(vertices)
        height = min(rng.uniform(.0015, .0030), .549 - max(p.z for p in base))
        vertices.extend(base)
        vertices.extend([p + Vector((0, 0, height)) for p in base])
        faces.extend([tuple(start + i for i in f) for f in
                      ((2, 1, 0), (3, 4, 5), (0, 1, 4, 3), (1, 2, 5, 4), (2, 0, 3, 5))])
    chips = new_object('CrustChipsWork', vertices, faces, bpy.data.materials['Foam'])
    activate(foam)
    chips.select_set(True)
    bpy.ops.object.join()
    return {'chips': len(faces) // 5, 'support_gap_m': .0008, 'seed': 95263}


def smooth_rims(obj, quilt=False):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.index_update()
    removed = 0
    if quilt:
        groups = components(bm)
        main = max(groups, key=lambda g: sum(f.calc_area() for f in {f for v in g for f in v.link_faces}))
        detached = [v for group in groups if group is not main for v in group]
        removed = len(groups) - 1
        bmesh.ops.delete(bm, geom=detached, context='VERTS')
    edges = [e for e in bm.edges if quilt and e.is_boundary and e.calc_length() > .045]
    bmesh.ops.subdivide_edges(bm, edges=edges, cuts=1, use_grid_fill=False)
    bm.normal_update()
    boundary = {v for e in bm.edges if e.is_boundary for v in e.verts}
    origins = {v: v.co.copy() for v in boundary}
    for _ in range(24 if quilt else 12):
        following = {}
        for v in boundary:
            neighbors = [e.other_vert(v) for e in v.link_edges if e.is_boundary]
            if len(neighbors) != 2:
                continue
            p = origins[v]
            # The finished wrap ridge is a measured rail contact, not a tear.
            if quilt and -.825 < p.x < -.70 and .48 < p.z < .57:
                continue
            average = (neighbors[0].co + neighbors[1].co) / 2
            candidate = v.co.lerp(average, .34)
            limit = .085 if quilt and p.x < -.9 and p.z < .25 else .028
            delta = candidate - p
            if delta.length > limit:
                candidate = p + delta.normalized() * limit
            following[v] = candidate
        for v, point in following.items():
            v.co = point
    # Fibre splits run along the long warp direction; submillimetre lateral
    # wander avoids replacing the softened contour with another sawtooth.
    for v in boundary:
        p = v.co
        if -.69 < p.x < .69 and p.z > .52:
            p.x += .0007 * np.sin(p.y * 39)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    recalc(obj)
    return {'smoothed_boundary_vertices': len(boundary), 'detached_unsupported_scraps_removed': removed,
            'max_contour_displacement_m': .085 if quilt else .028, 'long_grain_axis_blender': '+Y'}


def refit_cover(cover, foam):
    midsurface(cover)
    bm = bmesh.new()
    bm.from_mesh(cover.data)
    bm.normal_update()
    # The old cover has rolled side returns. Projecting those onto the crust
    # inverts their triangles, so retain only the upward rags before refitting.
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.z < .30 or f.calc_center_median().z < .54], context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.to_mesh(cover.data)
    bm.free()
    cut = cut_faces(cover, lambda p: (-.02 < p.x < .60 and -.67 < p.y < .37)
                    or p.x - p.y > 1.35, 95260, refine=False)
    record = smooth_rims(cover)
    tree = surface_tree(foam)
    for v in cover.data.vertices:
        p = v.co
        if p.z > .525:
            hit, _, _, _ = tree.ray_cast(Vector((p.x, p.y, .8)), Vector((0, 0, -1)))
            # Torn spans above plate gaps remain slack, not attached to the floor.
            p.z = (hit.z if hit is not None else .544) + .0023 + .0006 * np.sin(p.y * 24 + p.x * 13)
    solidify(cover, .0012)
    record['opened_central_cover'] = cut
    return record


def lower_cloth(obj):
    for vertex in obj.data.vertices:
        p = vertex.co
        weight = (np.clip((p.x + .815) / .13, 0, 1)
                  * np.clip((p.z - .51) / .06, 0, 1)
                  * np.clip((p.y + .95) / .18, 0, 1))
        p.z -= .034 * weight


def visible_fringe(mat):
    shader = mat.node_tree.nodes.get('Principled BSDF')
    texture = shader.inputs['Base Color'].links[0].from_node
    image = texture.image
    rgba = np.array(image.pixels[:], dtype=np.float32).reshape(2048, 1024, 4)
    groups = fringe_groups(95264)
    rgba[:, :, 3] = np.maximum(rgba[:, :, 3], groups.reshape(2048, 1024))
    image.pixels.foreach_set(rgba.ravel())
    image.save()
    image.pack()
    # Sparse hair coverage vanished below MASK's 0.5 cutoff at capture scale.
    mat.node_tree.links.new(texture.outputs['Alpha'], shader.inputs['Alpha'])
    mat.surface_render_method = 'DITHERED'
    mip = rgba[:, :, 3].reshape(8, 4, 64, 4, 256).mean(axis=(2, 4))
    return {'alpha_mode': 'BLEND', 'minimum_4px_root_alpha': float(mip[:, 0, :].min()),
            'mean_4px_tip_alpha': float(mip[:, -1, :].mean()), 'root_groups_per_card': 8}


def finish_fringe(fringe, quilt):
    layer = fringe.data.uv_layers.active.data
    tree = surface_tree(quilt)
    gaps = []
    for face in fringe.data.polygons:
        row = min(layer[i].uv.y for i in face.loop_indices)
        roots = []
        for i in face.loop_indices:
            vertex = fringe.data.loops[i].vertex_index
            corner = vertex % 4
            # Normal recalculation can rotate quad loops. Use the authored
            # corner identity so the strand roots stay on the cloth edge.
            layer[i].uv = (int(corner in (1, 2)), row + .125 * int(corner in (2, 3)))
            if corner in (0, 1):
                roots.append(fringe.matrix_world @ fringe.data.vertices[vertex].co)
        gaps.append(tree.find_nearest((roots[0] + roots[1]) / 2)[3])
    maximum = max(gaps)
    if maximum > .003:
        raise ValueError(f'Fringe attachment gap {maximum} exceeds 3 mm')
    return {'maximum_root_gap_m': maximum, 'uvs_follow_authored_roots': True}


def powder_relief(obj, center, extent, density):
    nx, ny = 10, 16
    vertices, faces = [], []
    for j, v in enumerate(np.linspace(0, 1, ny + 1)):
        for i, u in enumerate(np.linspace(0, 1, nx + 1)):
            alpha = density[round(v * 1023), round(u * 1023)]
            height = .003 * alpha
            vertices.append((center[0] + (2*u - 1) * extent[0],
                             center[1] + (2*v - 1) * extent[1], center[2] + height))
            if i < nx and j < ny:
                a = j * (nx + 1) + i
                faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    data = bpy.data.meshes.new(obj.name + '_PowderRelief')
    data.from_pydata(vertices, [], faces)
    data.materials.append(obj.data.materials[0])
    uv = data.uv_layers.new(name='PowderUV')
    for loop in data.loops:
        j, i = divmod(loop.vertex_index, nx + 1)
        uv.data[loop.index].uv = (i / nx, j / ny)
    obj.data = data
    return {'grid_cells': [nx, ny], 'max_relief_m': max(p[2] for p in vertices) - center[2]}


def deposits():
    records = []
    for obj in list(bpy.context.scene.objects):
        if obj.name.startswith('FibreFoamPowder_'):
            bpy.data.objects.remove(obj, do_unlink=True)
    for name, center, extent, seed in (
        ('FibreFoamPowder_Floor', (-1.18, -.30, .0008), (.33, .70), 95246),
        ('FibreFoamPowder_Platform', (.62, -.85, .5008), (.06, .04), 95247),
        ('FibreFoamPowder_Foot', (0, -1.024, .5008), (.64, .0045), 95261),
    ):
        obj = powder_card(name, center, extent, TEXTURES, seed, sectors=24)
        alpha = powder_field(seed)
        rng = np.random.default_rng(seed + 2)
        samples = rng.random((256, 256))
        coordinates = np.linspace(0, 255, 1024)
        across = np.array([np.interp(coordinates, np.arange(256), row) for row in samples])
        grain = np.array([np.interp(coordinates, np.arange(256), column) for column in across.T]).T
        pigment = .55 + .70 * grain
        rgba = np.ones((1024, 1024, 4), dtype=np.float32)
        rgba[:, :, :3] = np.array([.43, .34, .19]) * pigment[:, :, None]
        rgba[:, :, 3] = alpha
        mat = obj.data.materials[0]
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        shader = nodes.get('Principled BSDF')
        texture = shader.inputs['Base Color'].links[0].from_node
        texture.image = image_from_array(name + '_Deposit', rgba, TEXTURES / f'{name.lower()}.png')
        links.new(texture.outputs['Alpha'], shader.inputs['Alpha'])
        # The shared card's millimetre height noise at micron-sized texels
        # produced near-horizontal normals. Preserve grain at its physical pitch.
        height = min(.0003, min(extent) * .01) * grain
        normals = powder_normals(height, extent)
        normal_rgba = np.ones_like(rgba)
        normal_rgba[:, :, :3] = normals * .5 + .5
        normal_map = shader.inputs['Normal'].links[0].from_node
        normal_texture = normal_map.inputs['Color'].links[0].from_node
        normal_texture.image = image_from_array(name + '_GrainNormal', normal_rgba,
                                                TEXTURES / f'{name.lower()}_normal.png', True)
        relief = powder_relief(obj, center, extent, alpha)
        mat.surface_render_method = 'DITHERED'
        mat.use_backface_culling = False
        obj['aged_export'] = True
        bake_origin(obj)
        records.append({'name': name, 'mean_alpha': float(alpha.mean()), 'max_alpha': float(alpha.max()),
                        'extent_xy_m': extent, 'soft_edge_width_fraction': .31, 'relief': relief})
    return records


def main():
    TEXTURES.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(HERE / 'bed-soft-aged.blend'))
    mattress = bpy.data.objects['Mattress']
    foam = isolate(mattress, 'CrustFinishWork', lambda n: n == 'Foam')
    cover = isolate(mattress, 'CoverFinishWork', lambda n: n.startswith('CottonTicking'))
    record = {'crust': crust_plates(foam), 'cover': refit_cover(cover, foam)}
    record['crust_crumbs'] = crust_crumbs(foam)
    bpy.data.objects.remove(mattress, do_unlink=True)
    activate(foam)
    cover.select_set(True)
    bpy.ops.object.join()
    foam.name = 'Mattress'
    foam['aged_export'] = True
    quilt = bpy.data.objects['Quilt']
    midsurface(quilt)
    record['tears'] = smooth_rims(quilt, quilt=True)
    lower_cloth(quilt)
    record['rail_wrap_finish'] = clear_left_rail(quilt)
    fringe_mat = fringe_material(TEXTURES, 95262, wool=True)
    fringe_visibility = visible_fringe(fringe_mat)
    # Keep rail contacts bare. Fringe belongs on internal splits and the
    # low hanging tip, where alpha strands soften its silhouette.
    group = quilt.vertex_groups.new(name='Internal splits')
    for v in quilt.data.vertices:
        if ((-.60 < v.co.x < .22 and -.90 < v.co.y < -.20)
                or (v.co.x < -.9 and v.co.z < .35)):
            group.add([v.index], 1, 'REPLACE')
    blockers = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    fringe, record['fringe'] = cards(quilt, fringe_mat, 95262, wool=True, spacing=.022,
                                     boundary_group=group.name, blockers=blockers)
    fringe['aged_export'] = True
    solidify(quilt, .0012)
    record['fringe'].update(finish_fringe(fringe, quilt))
    record['fringe'].update(fringe_visibility)
    for name in ('Pillow_L', 'Pillow_R'):
        lower_cloth(bpy.data.objects[name])
    record['powder'] = deposits()
    for obj in (foam, quilt, bpy.data.objects['Pillow_L'], bpy.data.objects['Pillow_R']):
        bake_origin(obj)
        if obj == quilt:
            obj.data.uv_layers.active.name = 'WeaveUV'
            atlas = obj.data.uv_layers.new(name='AgedAtlas')
            obj.data.uv_layers.active_index = len(obj.data.uv_layers) - 1
            atlas.active_render = True
        unwrap(obj)
    save(HERE / 'bed-soft-aged-finished.blend', record)
    export(ASSETS / 'bed_soft_aged.glb')
    (HERE / 'refinement.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2), flush=True)


if __name__ == '__main__':
    main()
