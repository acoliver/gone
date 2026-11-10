"""Polish the accepted pilot shoulder without recalibrating garment pigments."""
import argparse
import json
from pathlib import Path
import shutil
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT
from age_tunic import save_checkpoint
from common import export
from pilot_finish import card_groups
from shoulder_drape import drape, rest_field


def move_fringe(sheet, delta):
    points, faces = sheet['vertices'], sheet['faces']
    tree = BVHTree.FromPolygons(points.tolist(), faces.tolist(), all_triangles=True)
    moved = {}
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH' or not any('Fringe' in mat.name for mat in obj.data.materials):
            continue
        groups = card_groups(obj)
        changes = 0
        for ids in groups:
            # Cards move with their attached roots, not the free end nearest a
            # neighbouring panel. Their short curved shapes stay intact.
            uv = {}
            for face in obj.data.polygons:
                for i in face.loop_indices:
                    index = obj.data.loops[i].vertex_index
                    if index in ids:
                        uv[index] = obj.data.uv_layers[0].data[i].uv.y
            minimum = min(uv.values())
            roots = [i for i in ids if abs(uv[i]-minimum) < 1e-7]
            centre = sum((obj.matrix_world @ obj.data.vertices[i].co for i in roots), Vector())/len(roots)
            point, _, index, _ = tree.find_nearest(centre)
            triangle = faces[index]
            old = points[triangle]
            new = old+delta[triangle]
            if np.max(np.abs(new-old)) > 1e-8:
                inverse = obj.matrix_world.inverted()
                old_normal = np.cross(old[1]-old[0], old[2]-old[0])
                old_normal /= np.linalg.norm(old_normal)
                normal = np.cross(new[1]-new[0], new[2]-new[0])
                normal /= np.linalg.norm(normal)
                for i in ids:
                    p = obj.matrix_world @ obj.data.vertices[i].co
                    mapped = barycentric_transform(p, *[Vector(v) for v in old], *[Vector(v) for v in new])
                    height = float((np.array(p)-old[0]) @ old_normal)
                    obj.data.vertices[i].co = inverse @ (mapped+Vector(normal)*height)
                if obj.name == 'Seamallowance':
                    root_points = [obj.data.vertices[i].co for i in roots]
                    centre = sum(root_points, Vector())/len(root_points)
                    tangent = max((b-a for a in root_points for b in root_points), key=lambda v: v.length).normalized()
                    for i in ids:
                        vertex = obj.data.vertices[i]
                        vertex.co += tangent*((vertex.co-centre).dot(tangent)*.25)
                changes += 1
        obj.data.update()
        if changes:
            moved[obj.name] = changes
    return moved


def measured_lift(body):
    from cloth_metrics import lip_lift
    body.data.calc_loop_triangles()
    triangles = [t for t in body.data.loop_triangles if body.data.polygons[t.polygon_index].material_index == 0]
    faces = np.array([t.vertices[:] for t in triangles])
    used, inverse = np.unique(faces, return_inverse=True)
    mesh = bpy.data.meshes.new('Shoulder gate midsurface')
    mesh.from_pydata([body.matrix_world @ body.data.vertices[i].co for i in used], [], inverse.reshape(-1, 3))
    obj = bpy.data.objects.new(mesh.name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    group = obj.vertex_groups.new(name='Lip shrink')
    source_group = body.vertex_groups['Lip shrink'].index
    for index, old in enumerate(used):
        weight = next((g.weight for g in body.data.vertices[old].groups if g.group == source_group), 0.)
        if weight:
            group.add([index], weight, 'REPLACE')
    result = lip_lift(obj)
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.meshes.remove(mesh)
    return result


def soften_shoulder_fringe():
    source = bpy.data.objects['Longwoolfringe'].data.materials[0]
    mat = source.copy()
    mat.name = 'WoolFringeShoulderSoft'
    shader = mat.node_tree.nodes['Principled BSDF']
    texture = shader.inputs['Base Color'].links[0].from_node
    mat.node_tree.links.new(texture.outputs['Alpha'], shader.inputs['Alpha'])
    mat.surface_render_method = 'BLENDED'
    for name in ['Longwoolfringe', 'Seamallowance']:
        for index in range(len(bpy.data.objects[name].data.materials)):
            bpy.data.objects[name].data.materials[index] = mat
    body = bpy.data.objects['TunicBody']
    original = next(i for i, material in enumerate(body.data.materials)
                    if material.name.startswith('WoolCutEdge'))
    rim = body.data.materials[original].copy()
    rim.name = 'WoolCutEdgeShoulderSoft'
    shader = rim.node_tree.nodes['Principled BSDF']
    texture = shader.inputs['Base Color'].links[0].from_node
    rim.node_tree.links.new(texture.outputs['Alpha'], shader.inputs['Alpha'])
    rim.surface_render_method = 'BLENDED'
    slot = len(body.data.materials)
    body.data.materials.append(rim)
    changed = 0
    for face in body.data.polygons:
        if face.material_index == original and face.center.x > .14 and face.center.z > -.35:
            face.material_index = slot
            changed += 1
    return dict(material=mat.name, rim_material=rim.name, rim_faces=changed,
                alpha='fractional atlas coverage, glTF BLEND',
                original_alpha='ROUND atlas alpha at 0.5, glTF MASK', colour_bytes_changed=False)


def finish(base, out, rest, edge_normals=False, soft_shoulder=False):
    sample = rest_field(rest)
    bpy.ops.wm.open_mainfile(filepath=str(base/'finished.blend'))
    record = json.loads(bpy.context.scene['tunic5_record'])
    out.mkdir(parents=True, exist_ok=True)
    shutil.copytree(base/'textures', out/'textures', dirs_exist_ok=True)
    shutil.copyfile(Path(__file__).with_name('target-colours.json'), out/'target-colours.json')
    sheet = dict(np.load(base/'game-sheet.npz'))
    original = {key: value.copy() for key, value in sheet.items()}
    report = drape(bpy.data.objects['TunicBody'], sheet, sample)
    delta = sheet['vertices']-original['vertices']
    report['fringe_root_motion'] = move_fringe(original, delta)
    from fringe_drape import measure_root_coverage, seat_cards, shorten_shoulder_cards
    report['shoulder_fibre_projection'] = shorten_shoulder_cards(report['fringe_root_motion'])
    report['fringe_seating'] = seat_cards(sheet, report['fringe_root_motion'])
    report['fringe_coverage'] = measure_root_coverage(bpy.data.objects['TunicBody'], report['fringe_root_motion'])
    for role, coverage in report['fringe_coverage'].items():
        record['fringe'][role].update(coverage)
    record['lip_lift'] = measured_lift(bpy.data.objects['TunicBody'])
    if edge_normals:
        from edge_fibre_normals import repair
        report['edge_normals'] = repair(bpy.data.objects['TunicBody'], sheet)
    if soft_shoulder:
        report['shoulder_alpha'] = soften_shoulder_fringe()
    report['measured_lift_fraction'] = record['lip_lift']['fraction']
    record['pass14'] = report
    np.savez_compressed(out/'game-sheet.npz', **sheet)
    save_checkpoint(out, 'finished', record)
    export(out/'candidate.glb')
    bpy.ops.wm.open_mainfile(filepath=str(out/'finished.blend'))
    export(out/'repeat.glb')
    identical = (out/'candidate.glb').read_bytes() == (out/'repeat.glb').read_bytes()
    (out/'repeat.json').write_text(json.dumps(dict(byte_identical=identical))+'\n')
    if not identical:
        raise ValueError('Shoulder polish does not re-export byte-identically')
    print('SHOULDER', json.dumps(report), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base', type=Path, default=ROOT/'tmp/age/tunic13/blue')
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--rest', type=Path, default=ROOT/'tmp/age/tunic11/visible/baked.blend')
    p.add_argument('--edge-normals', action='store_true')
    p.add_argument('--soft-shoulder', action='store_true')
    a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
    finish(a.base.resolve(), a.out.resolve(), a.rest.resolve(), a.edge_normals, a.soft_shoulder)
