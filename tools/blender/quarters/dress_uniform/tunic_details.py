"""Issue #130: fit details to frozen saved cloth, without running a cloth solve."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build import activate, disc, join_named, patch, tree, export as clean_export
from aging_support import ROOT, bind_points, components
from common import export as aged_export
from medal_fit import FITTED, build_source


def points(obj):
    return np.array([obj.matrix_world @ v.co for v in obj.data.vertices])


def geometry_hash(obj):
    obj.data.calc_loop_triangles()
    digest = hashlib.sha256(points(obj).astype('<f8').tobytes())
    digest.update(np.array([t.vertices[:] for t in obj.data.loop_triangles], dtype='<i4').tobytes())
    return digest.hexdigest()


def binding(obj, groups, support, rigid):
    original = points(obj)
    return dict(original=original.tolist(), entries=bind_points(support, original), groups=groups,
                support=support.name, rigid=rigid, patch_vertices=[], fitted_saved_pose=True)


def rebake_row(out):
    """Bake the replacement geometry, never reuse the six-button surface atlas."""
    from bake_down import bake_uv
    from baked_age_colour import aged_brass, bake_colour
    palette = json.loads((HERE / 'target-colours.json').read_text())['colours']
    placket, buttons = (bpy.data.objects[name] for name in ['Placket', 'Buttons'])
    for obj in [placket, buttons]:
        bake_uv(obj)
    placket.data.materials[0] = placket.data.materials[0].copy()
    report = {'Placket': bake_colour(placket, out, palette)}
    buttons.data.materials[0] = aged_brass(buttons, buttons.data.materials[0], out, palette)
    report['Buttons'] = dict(base_texture=str(out / 'buttons_brass_aged.png'),
                             masks='final-surface broad exposure in new BakeUV atlas', aged_only=True)
    # Remove only superseded row bake nodes; other materials remain untouched.
    for obj in [placket, buttons]:
        nodes = obj.data.materials[0].node_tree.nodes
        keep = {nodes['Material Output']}
        pending = list(keep)
        while pending:
            node = pending.pop()
            for socket in node.inputs:
                for link in socket.links:
                    if link.from_node not in keep:
                        keep.add(link.from_node)
                        pending.append(link.from_node)
        for node in list(nodes):
            if node not in keep:
                nodes.remove(node)
    return report


def row_details(body, aged=False):
    old_buttons = bpy.data.objects['Buttons']
    centers = np.array([points(old_buttons)[ids].mean(0) for ids in components(old_buttons)])
    fit = np.polyfit(centers[:, 2], centers[:, 0], 1)
    fabric = bpy.data.objects['Placket'].data.materials[0]
    brass = old_buttons.data.materials[0]
    old_placket = bpy.data.objects['Placket']
    # Keep the existing longitudinal tessellation, removing redundant width columns.
    nx, nz = 2, 64
    coordinates = [(float(np.polyval(fit, z) + dx), float(z))
                   for z in np.linspace(-.862, -.168, nz + 1)
                   for dx in np.linspace(-.014, .014, nx + 1)]
    faces = [(j * (nx + 1) + i, j * (nx + 1) + i + 1,
              (j + 1) * (nx + 1) + i + 1, (j + 1) * (nx + 1) + i)
             for j in range(nz) for i in range(nx)]
    for obj in (old_buttons, old_placket):
        bpy.data.objects.remove(obj, do_unlink=True)
    placket = patch('Placket', coordinates, faces, tree(body), fabric, .0005, .0004)
    uv = placket.data.uv_layers[0]
    for loop in placket.data.loops:
        p = placket.data.vertices[loop.vertex_index].co
        uv.data[loop.index].uv = (.5 + p.x, -p.z)
    surface = tree(placket)
    buttons = [disc('Button', float(np.polyval(fit, z)), float(z), .007, surface, brass, .0007, 24, .0005)
               for z in np.linspace(-.180, -.850, 8)]
    anchors = [p for obj in buttons for p in json.loads(obj['attachment'])['base_blender_m']]
    obj = join_named(buttons, 'Buttons')
    obj['attachment'] = json.dumps(dict(base_blender_m=anchors, support='Placket', nominal_offset_m=.0005))
    # Rigid tangent discs need continuous face seating, not just centre ray hits.
    from detail_clearance import continuous_gap, triangles
    support = np.concatenate([triangles(body), triangles(placket)])
    groups = sorted(components(obj), key=lambda ids: -points(obj)[ids, 2].mean())
    for ids, z in zip(groups, np.linspace(-.180, -.850, 8)):
        vertices = points(obj)
        centre = vertices[ids].mean(0)
        vertices[ids, 0] += np.polyval(fit, z) - centre[0]
        vertices[ids, 2] += z - centre[2]
        normal = np.array([0., -1., 0.])
        group = set(ids)
        obj.data.calc_loop_triangles()
        fs = np.array([t.vertices[:] for t in obj.data.loop_triangles if set(t.vertices) <= group])
        gap = continuous_gap(vertices[fs], support, normal)
        for index in ids:
            obj.data.vertices[index].co = Vector(vertices[index] + normal * (.0005 - gap))
    obj.data.update()
    anchors = [obj.data.vertices[i].co[:] for ids in components(obj) for i in ids[len(ids) // 2:]]
    obj['attachment'] = json.dumps(dict(base_blender_m=anchors, support='Placket', nominal_offset_m=.0005))
    if aged:
        rebake_row(ROOT / 'assets/props/quarters/dress_uniform')
    return dict(Placket=binding(placket, [list(range(len(placket.data.vertices)))], body, False),
                Buttons=binding(obj, components(obj), placket, True)), fit.tolist()


def extract_ribbon(old):
    ribbon = old.copy()
    ribbon.data = old.data.copy()
    bpy.context.collection.objects.link(ribbon)
    bm = bmesh.new()
    bm.from_mesh(ribbon.data)
    remove = [f for f in bm.faces if old.data.materials[f.material_index].name != 'RibbonFabric']
    bmesh.ops.delete(bm, geom=remove, context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.to_mesh(ribbon.data)
    bm.free()
    ribbon.data.update()
    activate(ribbon)
    bpy.ops.object.material_slot_remove_unused()
    return ribbon



def replace_medal(body, fit_report, aged):
    old = bpy.data.objects['Medal']
    old_points = points(old)
    old_attachment = json.loads(old['attachment'])
    # Existing 41 back anchors encode the accepted pressed support plane.
    from attachment_metrics import base_indices
    if 'metal_base_vertex_indices' in old_attachment:
        raise ValueError('Detail fitting requires the preserved six-button baseline source')
    record = json.loads(bpy.context.scene['tunic5_record']) if aged else None
    original = np.asarray(record['bindings']['Medal']['original']) if aged else old_points
    anchors = base_indices(original, old_attachment['base_blender_m'])[:41]
    base = old_points[anchors]
    normal = np.linalg.svd(base - base.mean(0))[2][-1]
    normal *= -np.sign(normal[1])
    tx = np.array([1., 0., 0.]) - normal * normal[0]
    tx /= np.linalg.norm(tx)
    frame = np.array([tx, -normal, np.cross(normal, tx)])
    origin = base[0]
    ribbon = extract_ribbon(old)
    with bpy.data.libraries.load(str(FITTED), link=False) as (source, destination):
        destination.objects = ['FittedMedalBody']
    for obj in destination.objects:
        bpy.context.collection.objects.link(obj)
    plate = destination.objects[0]
    brass = plate.data.materials[0] if aged else old.data.materials[0]
    plate.data.materials[0] = brass
    body_vertex_count = len(plate.data.vertices)
    # Fit the back plane against the actual visible support, not the relief volume.
    support = tree(body)
    targets = []
    for p in base:
        hit, _, _, _ = support.ray_cast(Vector(p + normal * .02), Vector(-normal), .04)
        if hit is None:
            raise ValueError('Medal reverse has no cloth support')
        targets.append(hit[:])
    targets = np.array(targets)
    normal = np.linalg.svd(targets - targets.mean(0))[2][-1]
    normal *= -np.sign(normal[1])
    tx = np.array([1., 0., 0.]) - normal * normal[0]
    tx /= np.linalg.norm(tx)
    frame = np.array([tx, -normal, np.cross(normal, tx)])
    origin = base[0].copy()
    origin += normal * np.dot(targets.mean(0) - origin, normal)
    from detail_clearance import continuous_gap, triangles
    local_plate = points(plate)
    plate.data.calc_loop_triangles()
    fs = np.array([t.vertices[:] for t in plate.data.loop_triangles])
    gap = continuous_gap((origin + local_plate @ frame)[fs], triangles(body), normal)
    origin += normal * (.00025 - gap)
    # Fair the hidden reverse only where the frozen clean cloth curves away.
    # This preserves the front relief instead of fitting the whole metal volume.
    reverse = np.flatnonzero(abs(local_plate[:, 1]) < 1e-8)
    for index in reverse:
        world = origin + local_plate[index] @ frame
        hit, _, _, _ = support.ray_cast(Vector(world + normal * .02), Vector(-normal), .04)
        distance = float(np.dot(world - np.array(hit), normal))
        local_plate[index, 1] += max(0., distance - .00175)
        plate.data.vertices[index].co = Vector(local_plate[index])
    reverse_points = local_plate[reverse].copy()
    from medal_eyelet import fit_eyelet
    loop_report = fit_eyelet(ribbon, origin, frame, brass, plate, support)
    metal = plate
    local = points(metal)
    distances = np.linalg.norm(reverse_points[:, None] - local[None, :], axis=2)
    metal_back = distances.argmin(1)
    metal_back = metal_back[distances.min(1) < 1e-7]
    for name in ['DetailUV', 'BakeUV']:
        layer = metal.data.uv_layers.get(name) or metal.data.uv_layers.new(name=name)
        for loop in metal.data.loops:
            p = local[loop.vertex_index]
            layer.data[loop.index].uv = (.5 + p[0] / .045, .4 + p[2] / .045)
    for vertex, p in zip(metal.data.vertices, origin + local @ frame):
        vertex.co = Vector(p)
    bpy.data.objects.remove(old, do_unlink=True)
    obj = join_named([metal, ribbon], 'Medal')
    metal_ids = list(range(len(local)))
    ribbon_ids = list(range(len(local), len(obj.data.vertices)))
    ribbon_bases = [ribbon_ids[i] for i in range(len(ribbon_ids) // 2, len(ribbon_ids))]
    bases = metal_back.tolist() + ribbon_bases
    current = points(obj)
    obj['attachment'] = json.dumps(dict(base_blender_m=current[bases].tolist(), support='TunicBody',
                                       metal_base_vertex_indices=metal_back.tolist(),
                                       base_vertex_indices=bases, nominal_offset_range_m=[.00025, .0018]))
    small = {k: v for k, v in fit_report.items() if not k.startswith('raw_samples') and k != 'raw_star_outline_m'}
    obj['fitted_medal'] = json.dumps(small)
    obj['eyelet'] = json.dumps(loop_report)
    obj['medal_frame'] = json.dumps(dict(origin=origin.tolist(), frame=frame.tolist(), body_vertices=body_vertex_count))
    new_binding = binding(obj, [metal_ids, ribbon_ids], body, True)
    if aged:
        from baked_age_colour import aged_brass, aged_enamel
        palette = json.loads((HERE / 'target-colours.json').read_text())['colours']
        texture_out = ROOT / 'assets/props/quarters/dress_uniform'
        for i, mat in enumerate(list(obj.data.materials)):
            if mat.name.startswith('Brass'):
                obj.data.materials[i] = aged_brass(obj, mat, texture_out, palette)
            elif mat.name.startswith('MedalEnamel'):
                obj.data.materials[i] = aged_enamel(mat)
    return new_binding, loop_report


def update(source_directory, output_directory):
    output_directory.mkdir(parents=True, exist_ok=True)
    fit_report = build_source()
    report = {}
    for aged, filename in [(False, 'tunic-working.blend'), (True, 'tunic-pilot.blend')]:
        bpy.ops.wm.open_mainfile(filepath=str(source_directory / filename))
        frozen = {o.name: geometry_hash(o) for o in bpy.context.scene.objects
                  if o.type == 'MESH' and o.name not in ['Buttons', 'Placket', 'Medal']}
        body = bpy.data.objects['TunicBody']
        bindings, row = row_details(body, aged=aged)
        bindings['Medal'], loop = replace_medal(body, fit_report, aged)
        for name in bindings:
            bpy.data.objects[name]['aged_export' if aged else 'export'] = True
        if aged:
            record = json.loads(bpy.context.scene['tunic5_record'])
            record['bindings'].update(bindings)
            record['issue130'] = dict(frozen_geometry=frozen, row_fit=row, medal_source='medal-fitted.blend', loop=loop)
            bpy.context.scene['tunic5_record'] = json.dumps(record)
        for name, expected in frozen.items():
            assert geometry_hash(bpy.data.objects[name]) == expected, name
        for data in list(bpy.data.meshes):
            if data.users == 0:
                bpy.data.meshes.remove(data)
        for obj in bpy.context.scene.objects:
            if obj.type == 'MESH' and obj.get('aged_export' if aged else 'export'):
                obj.data.name = obj.name
        # Packed resources remain unchanged when saving to a different path.
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=str(output_directory / filename))
        path = output_directory / ('dress_uniform_aged.glb' if aged else 'dress_uniform.glb')
        (aged_export if aged else clean_export)(path)
        report[filename] = dict(frozen_geometry=frozen, row_fit=row, loop=loop)
    (output_directory / 'fitting.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-directory', type=Path, required=True)
    p.add_argument('--output-directory', type=Path, required=True)
    args = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
    update(args.source_directory.resolve(), args.output_directory.resolve())
