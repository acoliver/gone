"""Pressure-filled bedding and a gravity-draped wool quilt on the fitted bed."""
import argparse
import json
import math
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE.parent / 'sofa'))
from cloth import box_shell, cloth
sys.path.insert(0, str(HERE.parents[1] / 'quarters_aging'))
from common import activate, apply, collision, export, recalc, save, settle, solidify, surface_tree
from fabric_mesh import material, new_object

SCRATCH = ROOT / 'tmp/bed_soft'
ASSETS = ROOT / 'assets/props/quarters'
PARTS = ('Mattress', 'Quilt', 'Pillow_L', 'Pillow_R')


def mesh_points(obj):
    return np.array([obj.matrix_world @ v.co for v in obj.data.vertices])


def bake_origin(obj):
    activate(obj)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    obj['aged_export'] = True
    for face in obj.data.polygons:
        face.use_smooth = True
    recalc(obj)


def unwrap(obj):
    activate(obj)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(island_margin=.012)
    bpy.ops.object.mode_set(mode='OBJECT')


def load_bed():
    bpy.ops.import_scene.gltf(filepath=str(ASSETS / 'bed.glb'))
    for obj in list(bpy.context.scene.objects):
        if obj.type == 'MESH':
            collision(obj, .0005)
            obj['bed_frame'] = True
    # This floor participates in cloth contact but never enters the game export.
    bpy.ops.mesh.primitive_plane_add(size=12)
    floor = bpy.context.object
    floor.name = 'SupportFloor'
    collision(floor, .0005)
    floor['support_only'] = True


def drop_to(obj, support, gap=.001):
    tree = surface_tree(support)
    points = mesh_points(obj)
    obj.data.calc_loop_triangles()
    triangles = points[np.array([t.vertices[:] for t in obj.data.loop_triangles])]
    # Coarse pillow faces can cross a mattress crest between their vertices.
    samples = [points, triangles.mean(axis=1)]
    samples.extend((triangles[:, i] + triangles[:, (i + 1) % 3]) / 2 for i in range(3))
    samples = np.concatenate(samples)
    start_z = max(points[:, 2].max(), mesh_points(support)[:, 2].max()) + .1
    gaps = []
    for point in samples:
        hit, _, _, _ = tree.ray_cast(Vector((point[0], point[1], start_z)), Vector((0, 0, -1)))
        if hit is not None:
            gaps.append(float(point[2] - hit.z))
    if not gaps:
        raise ValueError(f'{obj.name}: no support beneath its lower surface')
    shift = gap - min(gaps)
    inverse = obj.matrix_world.inverted()
    for vertex in obj.data.vertices:
        p = obj.matrix_world @ vertex.co
        p.z += shift
        vertex.co = inverse @ p
    return shift


def pressure_shell(name, dims, center, divisions, support):
    obj = box_shell(name, dims, divisions, radius=min(dims[2] * .36, .055))
    # The sewn top shoulder is inset while the broad faces retain their crown.
    for vertex in obj.data.vertices:
        t = max(0, vertex.co.z / (dims[2] / 2))
        for axis in (0, 1):
            edge = max(0, (abs(vertex.co[axis]) / (dims[axis] / 2) - .65) / .35)
            vertex.co[axis] *= 1 - .035 * t * edge
    obj.location = center
    bpy.context.scene.frame_set(1)
    # Retain platform-contact stitches so the large mattress cannot drift into
    # a rail and buckle into a taco while its pressure shell settles.
    mod = cloth(obj, pressure=.01, scale=1, bending=.3, stiffness=150, mass=.015, pin=name == 'Mattress')
    mod.settings.time_scale = .4
    frames = 80
    mod.point_cache.frame_end = frames
    previous = None
    motion = None
    for frame in range(1, frames + 1):
        bpy.context.scene.frame_set(frame)
        evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        if frame in (frames - 5, frames):
            points = np.array([v.co[:] for v in evaluated.data.vertices])
            if previous is not None:
                motion = float(np.linalg.norm(points - previous, axis=1).max())
            previous = points
        if frame % 20 == 0:
            print(name, 'pressure frame', frame, flush=True)
    apply(obj, mod)
    if name != 'Mattress':
        points = np.array([v.co[:] for v in obj.data.vertices])
        lo, hi = points[:, 2].min(), points[:, 2].max()
        for vertex in obj.data.vertices:
            vertex.co.z = lo + (vertex.co.z - lo) * .12 / (hi - lo)
    bake_origin(obj)
    print(name, 'solved bounds', mesh_points(obj).min(0), mesh_points(obj).max(0),
          'support bounds', mesh_points(support).min(0), mesh_points(support).max(0), flush=True)
    shift = drop_to(obj, support)
    obj.data.materials.append(material('CottonTicking' if name == 'Mattress' else 'CottonPillow',
                                       (.50, .46, .37) if name == 'Mattress' else (.78, .76, .70)))
    unwrap(obj)
    collision(obj, .0005)
    return obj, {'frames': frames, 'uniform_pressure': .01, 'pressure_factor': 1,
                 'quality': 20, 'time_scale': .4, 'mass': .015, 'stiffness': 150,
                 'bending': .3, 'last_five_frames_motion_m': motion,
                 'support_translation_m': shift, 'bounds_native_m': [mesh_points(obj).min(0).tolist(), mesh_points(obj).max(0).tolist()]}


def quilt_sheet(top):
    nx = 32
    # A continuous doubled head cuff, not an intersecting second rectangular sheet.
    profile = [(y, top + .008) for y in np.linspace(-1.13, .37, 31)]
    profile += [(.37 + .024 * math.sin(a), top + .008 + .024 * (1 - math.cos(a)))
                for a in np.linspace(0, math.pi, 9)[1:]]
    profile += [(y, top + .056) for y in np.linspace(.37, .12, 6)[1:]]
    verts, faces = [], []
    for j, (y, z) in enumerate(profile):
        for i, x in enumerate(np.linspace(-.855, .855, nx + 1)):
            edge = max(0, (abs(x) - .60) / .255)
            foot = max(0, (-y - .87) / .26)
            ripple = .007 * math.sin(y * 15 + x * 4) * edge
            verts.append((x, y, z - .055 * edge - .045 * foot + ripple))
            if i < nx and j < len(profile) - 1:
                a = j * (nx + 1) + i
                faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    obj = new_object('Quilt', verts, faces, material('WovenWool', (.14, .105, .075)))
    obj.data.materials.append(material('WoolCuff', (.19, .15, .11)))
    obj.data.materials.append(material('WoolBinding', (.075, .053, .035)))
    for face in obj.data.polygons:
        row = face.index // nx
        face.material_index = 2 if row >= len(profile) - 2 else (1 if row >= len(profile) - 6 else 0)
    pins = {j * (nx + 1) + i: 1.0 for j in (15, 16) for i in (15, 16, 17)}
    return obj, pins


def settle_quilt(mattress):
    quilt, pins = quilt_sheet(float(mesh_points(mattress)[:, 2].max()))
    tree = surface_tree(mattress)
    for index in pins:
        p = quilt.data.vertices[index].co
        hit = tree.ray_cast(Vector((p.x, p.y, 2)), Vector((0, 0, -1)))[0]
        if hit is None:
            raise ValueError('Quilt contact stitch missed the mattress')
        p.z = hit.z + .003
    settings = dict(quality=24, time_scale=.35, mass=.18, stiffness=180, bending=.5,
                    frames=180, collision_quality=10, collision_distance_m=.001,
                    self_distance_m=.003, air_damping=8)
    record = settle(quilt, settings, pins)
    solidify(quilt, .003)
    bake_origin(quilt)
    unwrap(quilt)
    return record


def remembered():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    load_bed()
    platform = bpy.data.objects['MattressPlatform']
    mattress, record = pressure_shell('Mattress', (1.40, 1.96, .22), (0, -.025, .613), (20, 28, 4), platform)
    records = {'Mattress': record}
    top = float(mesh_points(mattress)[:, 2].max())
    for name, x in (('Pillow_L', -.355), ('Pillow_R', .355)):
        pillow, record = pressure_shell(name, (.65, .43, .155), (x, .70, top + .10), (12, 10, 4), mattress)
        records[name] = record
    records['Quilt'] = settle_quilt(mattress)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    (HERE / 'simulation.json').write_text(json.dumps(records, indent=2) + '\n')
    save(HERE / 'bed-soft-working.blend', records)
    export(ASSETS / 'bed_soft.glb')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assemble', action='store_true')
    parser.add_argument('--state', choices=('remembered', 'aged'), default='remembered')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--fit-contacts', type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    if args.assemble:
        remembered()
    else:
        source = 'bed-soft-working.blend' if args.state == 'remembered' else 'bed-soft-aged.blend'
        bpy.ops.wm.open_mainfile(filepath=str(HERE / source))
        if args.fit_contacts:
            shifts = json.loads(args.fit_contacts.read_text())
            record_path = HERE / ('simulation.json' if args.state == 'remembered' else 'aging.json')
            record = json.loads(record_path.read_text())
            for name, shift in shifts.items():
                for vertex in bpy.data.objects[name].data.vertices:
                    vertex.co.z += shift
                record[name]['exact_face_contact_translation_m'] = shift
            record_path.write_text(json.dumps(record, indent=2) + chr(10))
            save(HERE / source, record)
        export(args.output or ASSETS / ('bed_soft.glb' if args.state == 'remembered' else 'bed_soft_aged.glb'))


if __name__ == '__main__':
    main()
