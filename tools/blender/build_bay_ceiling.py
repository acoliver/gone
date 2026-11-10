"""Fit Hunyuan contours in Blender and export closed, perforated steel panels.

Run -- --intact-only first, verify_bay_ceiling.py --intact-only independently,
then run without --intact-only to build variants and neutral studio captures.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bay_ceiling_geometry import (
    FittedGuides, LENGTH, WIDTH, THICKNESS, RIM_DEPTH, RIM_FRACTIONS, RIM_HEIGHTS,
    contains, constraint_loop, distance_to_loop, radial, signed_area,
)
from bay_ceiling_details import mount_heads, panel_uv

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'art-source/bay-ceiling/hunyuan-panel-seed-4208.glb'
GUIDE = ROOT / 'art-source/bay-ceiling/source-guide.json'
OUT = ROOT / 'assets/props/bay-ceiling'
EVIDENCE = ROOT / 'tmp/verify-stasis-ceiling/geometry'
VARIANTS = ('intact', 'subtlewarp', 'sag', 'torncorner', 'brokenedge')


def source_profile(fit):
    bpy.ops.import_scene.gltf(filepath=str(SOURCE))
    imported = list(bpy.context.scene.objects)
    meshes = [obj for obj in imported if obj.type == 'MESH']
    source = max(meshes, key=lambda obj: len(obj.data.polygons))
    points = np.array([source.matrix_world @ v.co for v in source.data.vertices])
    c, s = math.cos(fit.angle), math.sin(fit.angle)
    # glTF import already produces Blender XY plan / Z height. Only align within XY.
    aligned = np.column_stack((c * points[:, 0] - s * points[:, 1],
                               s * points[:, 0] + c * points[:, 1]))
    assert np.isfinite(aligned).all(), 'nonfinite source coordinates'
    xy = fit.fit_plan(aligned)
    cells = np.floor(xy / .012).astype(int)
    _, inverse = np.unique(cells, axis=0, return_inverse=True)
    top = np.full(inverse.max() + 1, -np.inf)
    np.maximum.at(top, inverse, points[:, 2])
    top_indices = np.flatnonzero(points[:, 2] >= top[inverse] - 1e-9)
    _, unique = np.unique(inverse[top_indices], return_index=True)
    top_indices = top_indices[unique]
    top_xy, top_z = xy[top_indices], points[top_indices, 2]
    angles = np.arctan2(top_xy[:, 1], top_xy[:, 0])
    outer_radius = np.linalg.norm(radial(fit.outer, angles), axis=1)
    inner_radius = np.linalg.norm(radial(fit.inner, angles), axis=1)
    r = np.linalg.norm(top_xy, axis=1)
    across_rim = (r - inner_radius) / (outer_radius - inner_radius)
    masks = {'broad_face': r < .78 * inner_radius,
             'rim_crest': (across_rim > .25) & (across_rim < .80)}
    measured = {}
    for role, mask in masks.items():
        values = top_z[mask]
        assert len(values) > 20, (role, 'insufficient source profile samples')
        measured[role] = {'cells': len(values), 'raw_height_quantiles_10_50_90_m': np.quantile(values, [.1, .5, .9]).tolist()}
    crest = measured['rim_crest']['raw_height_quantiles_10_50_90_m'][1]
    face = measured['broad_face']['raw_height_quantiles_10_50_90_m'][1]
    face_height = (face - crest) * fit.scale
    assert -.025 < face_height < -.0005, ('source rim/face profile', measured)
    collection = bpy.data.collections.new('Frozen Hunyuan source, unmodified imported coordinates')
    bpy.context.scene.collection.children.link(collection)
    for obj in imported:
        for owner in list(obj.users_collection):
            owner.objects.unlink(obj)
        collection.objects.link(obj)
        obj.hide_render = True
        obj.hide_set(True)
    collection.hide_render = True
    collection.hide_viewport = True
    return face_height, {
        'method': 'Maximum imported Blender Z in 12 mm fitted-plan cells; robust median by inner-face and rim radial regions.',
        'source_imported_blender_bounds_m': [points.min(axis=0).tolist(), points.max(axis=0).tolist()],
        'source_mesh_faces': sorted((len(obj.data.polygons) for obj in meshes), reverse=True),
        'measurements': measured, 'datum_raw_y_m': crest,
        'three_ring_top_heights_blender_m': [0., 0., face_height],
        'simplification': 'Outer contact and middle crest at rim datum; measured median broad-face drop on inner ring. Raw underside and tunnel topology discarded.',
    }


def neutral_material():
    material = bpy.data.materials.new('Neutral opaque steel, paint deferred')
    material.diffuse_color = (.32, .32, .32, 1)
    material.use_nodes = True
    shader = material.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (.32, .32, .32, 1)
    shader.inputs['Metallic'].default_value = .4
    shader.inputs['Roughness'].default_value = .75
    shader.inputs['Alpha'].default_value = 1
    return material


def triangulate_panel(fit, kind, material):
    face_height = -RIM_DEPTH
    damaged_outer = fit.damaged_outer(kind)
    rings = [constraint_loop(ring, fit.attachment_indices(kind)) for ring in fit.profile_rings(kind)]
    outer = rings[0]
    vertices, heights, edges = [], [], []
    for loop, height in (*zip(rings, RIM_HEIGHTS), *((slot, face_height) for slot in fit.slots)):
        base = len(vertices)
        vertices.extend(loop.tolist())
        heights.extend([height] * len(loop))
        edges.extend((base+i, base+(i+1) % len(loop)) for i in range(len(loop)))
    grid = np.array([(x, y) for x in np.arange(-.5, .501, .025) for y in np.arange(-.225, .226, .025)])
    keep = contains(grid, fit.inner) & (distance_to_loop(grid, fit.inner) > .001)
    for slot in fit.slots:
        keep &= ~contains(grid, slot) & (distance_to_loop(grid, slot) > .001)
    grid = grid[keep]
    vertices.extend(grid.tolist())
    heights.extend([face_height] * len(grid))
    result = delaunay_2d_cdt([Vector(p) for p in vertices], edges, [], 0, 1e-8, True)
    coords, _, triangles, original_vertices, _, _ = result
    xy = np.array(coords)
    z = []
    for originals in original_vertices:
        assert originals, 'CDT introduced an intersection: inspect input constraints'
        source_heights = [heights[index] for index in originals]
        assert max(source_heights) - min(source_heights) < 1e-9, 'CDT merged separate profile rings'
        z.append(source_heights[0])
    triangles = np.array(triangles, dtype=int)
    assert triangles.shape[1] == 3
    centroids = xy[triangles].mean(axis=1)
    keep = contains(centroids, outer)
    for slot in fit.slots:
        keep &= ~contains(centroids, slot)
    triangles = triangles[keep]
    cross_z = ((xy[triangles[:, 1], 0] - xy[triangles[:, 0], 0]) * (xy[triangles[:, 2], 1] - xy[triangles[:, 0], 1])
               - (xy[triangles[:, 1], 1] - xy[triangles[:, 0], 1]) * (xy[triangles[:, 2], 0] - xy[triangles[:, 0], 0]))
    assert np.min(np.abs(cross_z)) > 2e-12, 'degenerate CDT triangle'
    triangles[cross_z < 0] = triangles[cross_z < 0, ::-1]
    used = np.unique(triangles)
    remap = np.full(len(xy), -1, dtype=int)
    remap[used] = np.arange(len(used))
    triangles = remap[triangles]
    xy = xy[used]
    z = np.array(z)[used] + fit.displacement(xy, kind)
    top = np.column_stack((xy, z))
    bottom = top.copy()
    bottom[:, 2] -= THICKNESS
    count = len(top)
    faces = triangles.tolist() + (triangles[:, ::-1] + count).tolist()
    directed = {}
    for tri in triangles:
        for a, b in zip(tri, np.roll(tri, -1)):
            key = tuple(sorted((int(a), int(b))))
            directed.setdefault(key, []).append((int(a), int(b)))
    boundary = []
    for incidence in directed.values():
        assert len(incidence) <= 2
        if len(incidence) == 1:
            a, b = incidence[0]
            boundary.append((a, b))
            faces.extend(((b, a, a+count), (b, a+count, b+count)))
    mesh = bpy.data.meshes.new(f'{kind}_closed_source_fitted_shell')
    mesh.from_pydata(np.vstack((top, bottom)).tolist(), [], faces)
    mesh.update()
    assert not mesh.validate(verbose=True), 'mesh validation had to repair geometry'
    assert len(mesh.vertices) - len(mesh.edges) + len(mesh.polygons) == 2 - 2*len(fit.slots)
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    mesh.set_sharp_from_angle(angle=.7)
    panel_uv(mesh, count, len(triangles), boundary)
    obj = bpy.data.objects.new(kind, mesh)
    bpy.context.collection.objects.link(obj)
    mesh.materials.append(material)
    obj['source'] = str(SOURCE.relative_to(ROOT))
    obj['through_slots'] = len(fit.slots)
    obj['sheet_thickness_m'] = THICKNESS
    obj['rim_datum_blender_z_m'] = 0.
    obj['role'] = 'closed_perforated_panel'
    obj['separate_hardware_bodies'] = 4
    changed = np.linalg.norm(damaged_outer - fit.outer, axis=1) > 1e-9
    arcs = np.linalg.norm(np.roll(fit.outer, -1, axis=0) - fit.outer, axis=1)
    anchors = fit.attachment_points(kind)
    return obj, {
        'triangles': len(faces), 'vertices_before_export_seams': len(mesh.vertices),
        'top_surface_triangles': len(triangles), 'closed_boundary_edges': len(boundary),
        'max_outline_notch_m': float(np.linalg.norm(damaged_outer - fit.outer, axis=1).max()),
        'removed_projected_area_m2': signed_area(fit.outer) - signed_area(damaged_outer),
        'changed_original_outline_arc_m': float(arcs[changed].sum()),
        'outer_blender_xy_m': damaged_outer.tolist(),
        'attachment_points_blender_m': [[*point, 0.] for point in anchors.tolist()],
        'attachment_points_gltf_m': [[point[0], 0., -point[1]] for point in anchors.tolist()],
        'attachment_normal_gltf': [0., 1., 0.],
        'attachment_policy': 'Four flanged heads seated at Z=0 on intact flange; torn upper-right mount relocated along surviving top edge. Underside support interface Z=-0.002.',
        'attachment_underside_points_gltf_m': [[point[0], -THICKNESS, -point[1]] for point in anchors.tolist()],
        'panel_bodies': 1, 'hardware_bodies': 4,
        'hardware_names': [f'{kind}_mount_head_{i+1}' for i in range(4)],
        'constraint_loop_vertices': [len(ring) for ring in rings],
        'collinear_constraint_removal_tolerance_m': 2e-7,
        'displacement_min_max_m': [float(fit.displacement(xy, kind).min()), float(fit.displacement(xy, kind).max())],
        'bounds_blender_m': [np.vstack((top, bottom)).min(axis=0).tolist(), np.vstack((top, bottom)).max(axis=0).tolist()],
        'damage': {'intact': 'none', 'subtlewarp': 'smooth signed twist; four flange mounts and outer edge fixed',
                   'sag': 'smooth 36 mm center sag; four flange mounts and outer edge fixed',
                   'torncorner': 'upper-right source corner region removed; compressed rim bands and depressed nonplanar lip; fourth mount relocated',
                   'brokenedge': 'long irregular left-edge segment removed; supported bent lip along continuous closed outline'}[kind],
    }


def export(obj, hardware):
    bpy.ops.object.select_all(action='DESELECT')
    for part in [obj, *hardware]:
        part.hide_set(False)
        part.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.gltf(filepath=str(OUT / f'{obj.name}.glb'), export_format='GLB',
                             use_selection=True, export_yup=True, export_apply=True, export_extras=True,
                             export_materials='EXPORT', export_texcoords=True, export_normals=True)


def camera_at(name, position, target, scale):
    data = bpy.data.cameras.new(name)
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = position
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()
    data.type = 'ORTHO'
    data.ortho_scale = scale
    bpy.context.scene.camera = obj
    return obj


def studio_renders(objects):
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 48
    scene.cycles.use_denoising = True
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 8
    scene.render.resolution_x = 2000
    scene.render.resolution_y = 1400
    scene.render.resolution_percentage = 100
    scene.world = bpy.data.worlds.new('Neutral studio')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.32, .32, .32, 1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value = .5
    scene.view_settings.view_transform = 'AgX'
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -.10))
    floor = bpy.context.object
    floor.name = 'Studio floor, not exported'
    material = bpy.data.materials.new('Studio gray')
    material.diffuse_color = (.16, .16, .16, 1)
    floor.data.materials.append(material)
    for name, position, energy, size in (
        ('Large key', (-.4, -.7, 1.8), 160, 1.5),
        ('Broad fill', (.8, .6, 1.3), 110, 1.),
        ('Rim light', (-1., .9, .7), 90, .8),
    ):
        data = bpy.data.lights.new(name, 'AREA')
        data.energy, data.shape, data.size = energy, 'DISK', size
        light = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(light)
        light.location = position
        light.rotation_euler = (Vector((0, 0, 0)) - light.location).to_track_quat('-Z', 'Y').to_euler()
    paths = []
    for kind in objects:
        for other_kind, parts in objects.items():
            for part in parts:
                part.hide_render = other_kind != kind
        for view, position, scale in (
            ('studio', (1.05, -1.30, 1.55), 1.42),
            ('plan', (0., 0., 2.), 1.32),
            ('edge', (-.9, 1.4, .28), 1.35),
        ):
            camera = camera_at(f'{kind}_{view}', position, (0, 0, -.005), scale)
            path = EVIDENCE / f'{kind}-{view}.png'
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            paths.append(str(path.relative_to(ROOT)))
            bpy.data.objects.remove(camera, do_unlink=True)
    for kind, target, position in (
        ('torncorner', (.46, .19, -.018), (.95, .85, .52)),
        ('brokenedge', (-.52, 0., -.018), (-1.05, -.65, .42)),
    ):
        for other_kind, parts in objects.items():
            for part in parts:
                part.hide_render = other_kind != kind
        camera = camera_at(f'{kind}_detail', position, target, .52)
        path = EVIDENCE / f'{kind}-detail.png'
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        paths.append(str(path.relative_to(ROOT)))
        bpy.data.objects.remove(camera, do_unlink=True)
    (EVIDENCE / 'renders.json').write_text(json.dumps(paths, indent=2) + '\n')
    (EVIDENCE / 'render-settings.json').write_text(json.dumps({
        'engine': 'CPU Cycles', 'samples': 48, 'resolution': [2000, 1400],
        'view_transform': 'AgX', 'material': 'neutral opaque steel, no baked paint bound',
        'geometry_manifest_sha256': hashlib.sha256((OUT / 'manifest.json').read_bytes()).hexdigest(),
        'visual_acceptance': 'Not evaluated; images for parent image-comparer.',
    }, indent=2) + '\n')
    return paths


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--intact-only', action='store_true')
    parser.add_argument('--skip-renders', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    OUT.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.context.scene.unit_settings.system = 'METRIC'
    bpy.context.scene.unit_settings.scale_length = 1.
    fit = FittedGuides(json.loads(GUIDE.read_text()))
    height, profile = source_profile(fit)
    material = neutral_material()
    manifest = {
        'source': str(SOURCE.relative_to(ROOT)), 'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'guide': str(GUIDE.relative_to(ROOT)), 'guide_sha256': hashlib.sha256(GUIDE.read_bytes()).hexdigest(),
        'units': 'meters', 'authoring_axes': 'Blender XY plan, +Z height; export_yup=True produces glTF XZ plan, +Y height',
        'footprint_m': [LENGTH, WIDTH], 'sheet_vertical_thickness_m': THICKNESS,
        'slot_count': len(fit.slots), 'slot_boundary_vertices': 16,
        'slot_nominal_length_width_m': [.108, .022],
        'minimum_slot_to_slot_ligament_m': fit.slot_gap,
        'minimum_slot_to_inner_rim_ligament_m': fit.slot_rim_gap,
        'original_source_corner_samples_blender_m': [[*fit.outer[i].tolist(), 0.] for i in fit.contact_indices],
        'fit': fit.record, 'measured_profile': profile,
        'shape_target_adjustment': {
            'measured_source_face_drop_m': -height, 'target_face_drop_m': RIM_DEPTH,
            'profile_fractions_outer_to_inner': RIM_FRACTIONS, 'profile_top_heights_blender_m': RIM_HEIGHTS,
            'reason': 'Retain the fitted source inner rim and perforated face, form the outer mounting flange to a shared cassette grid, and set the rim relief to 18 mm. These are authored manufacturing adjustments, not raw source dimensions.',
        },
        'hardware': {'bodies_per_variant': 4, 'type': 'closed flanged captive head, no shank or hidden bore',
                     'radius_m': .006, 'height_m': .0044, 'seat_blender_z_m': 0.},
        'uv0': 'Top/bottom normalized planar XY overlap. Each return edge projects its bottom UV 2 mm toward the metal-side bank of the same atlas; top UV follows the exact edge. No zero-area wall UV triangles. Sloped rim remains planar-projected. Hardware uses local dominant-plane face projection.',
        'variants': {},
    }
    objects = {}
    for kind in (('intact',) if args.intact_only else VARIANTS):
        obj, record = triangulate_panel(fit, kind, material)
        hardware = mount_heads(kind, fit.attachment_points(kind), material)
        export(obj, hardware)
        objects[kind] = [obj, *hardware]
        manifest['variants'][kind] = record
        for part in objects[kind]:
            part.hide_set(kind != 'intact')
            part.hide_render = kind != 'intact'
    bpy.context.view_layer.objects.active = objects['intact'][0]
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'fitted-source.blend'))
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (EVIDENCE / 'fit-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('BUILD_COMPLETE', json.dumps(manifest['variants']), flush=True)
    if not args.skip_renders:
        for parts in objects.values():
            for part in parts:
                part.hide_set(False)
        print('RENDERS_COMPLETE', studio_renders(objects), flush=True)


if __name__ == '__main__':
    main()
