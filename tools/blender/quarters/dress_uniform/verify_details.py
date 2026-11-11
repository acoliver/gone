"""Issue #130 fitting measurements on the real saved cloth and metal surfaces."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from tunic_details import geometry_hash, points
from aging_support import components
from common import surface_tree
from detail_clearance import continuous_gap, triangles
from reduced_clearance import crossing_pairs
from medal_mount_checks import upper_ribbon_samples, assert_upper_preserved


def ribbon_signature(obj, uv_names):
    rows = []
    colours = obj.data.color_attributes['RibbonColours'].data
    for face in obj.data.polygons:
        if not obj.data.materials[face.material_index].name.startswith('RibbonFabric'):
            continue
        corners = []
        for i in face.loop_indices:
            vertex = obj.data.loops[i].vertex_index
            values = list(obj.matrix_world @ obj.data.vertices[vertex].co)
            for name in uv_names:
                values.extend(obj.data.uv_layers[name].data[i].uv)
            values.extend(colours[i].color)
            corners.append(tuple(values))
        rows.append(tuple(sorted(corners)))
    return hashlib.sha256(np.array(sorted(rows), dtype='<f8').tobytes()).hexdigest(), len(rows)


def row_limits(body, fit):
    body.data.calc_loop_triangles()
    uv = body.data.uv_layers[0].data
    positions = points(body)
    selected, levels = [], []
    for t in body.data.loop_triangles:
        if body.data.polygons[t.polygon_index].material_index != 0 or max(uv[i].uv.x for i in t.loops) >= .48:
            continue
        face = positions[list(t.vertices)]
        selected.append(face)
        for a, b in zip(face, np.roll(face, -1, axis=0)):
            da, db = a[0] - np.polyval(fit, a[2]), b[0] - np.polyval(fit, b[2])
            if da * db < 0:
                levels.append(float((a + (b - a) * (-da / (db - da)))[2]))
    if not levels:
        raise ValueError('Missing front cloth section along the fitted button row')
    selected = np.array(selected)
    tree = BVHTree.FromPolygons(selected.reshape(-1, 3).tolist(),
                               np.arange(selected.size // 3).reshape(-1, 3).tolist(), all_triangles=True)
    count = 0
    for z in np.linspace(-.168, -.862, 695):
        for dx in np.linspace(-.014, .014, 29):
            hit = tree.ray_cast(Vector((np.polyval(fit, z) + dx, -1, z)), Vector((0, 1, 0)))[0]
            count += hit is not None
    assert count == 20155, ('Unsupported extended placket samples', count)
    return min(levels), max(levels), count


def measure(directory, baseline):
    report = {}
    frozen_by_state, ribbons = {}, {}
    for name in ['working', 'pilot']:
        bpy.ops.wm.open_mainfile(filepath=str(baseline / f'tunic-{name}.blend'))
        frozen_by_state[name] = {o.name: geometry_hash(o) for o in bpy.context.scene.objects
                                 if o.type == 'MESH' and o.name != 'Medal'}
        medal = bpy.data.objects['Medal']
        uv_names = [layer.name for layer in medal.data.uv_layers]
        frame = json.loads(medal['medal_frame'])
        ribbons[name] = (frame, upper_ribbon_samples(medal, frame))
    for name in ['working', 'pilot']:
        bpy.ops.wm.open_mainfile(filepath=str(directory / f'tunic-{name}.blend'))
        for part, expected in frozen_by_state[name].items():
            assert geometry_hash(bpy.data.objects[part]) == expected, ('Frozen geometry changed', name, part)
        medal, body = bpy.data.objects['Medal'], bpy.data.objects['TunicBody']
        frame_before, expected = ribbons[name]
        upper_count = assert_upper_preserved(expected, medal, frame_before)
        assert json.loads(medal['ribbon_loop'])['loop_wrap_degrees'] >= 180
        buttons = bpy.data.objects['Buttons']
        positions = points(buttons)
        groups = sorted(components(buttons), key=lambda ids: -positions[ids, 2].mean())
        assert len(groups) == 8
        centers = np.array([positions[ids].mean(0) for ids in groups])
        np.testing.assert_allclose(centers[:, 2], np.linspace(-.180, -.850, 8), atol=.0001)
        fit = np.polyfit(centers[:, 2], centers[:, 0], 1)
        hem, neck, samples = row_limits(body, fit)
        edges = [positions[groups[0], 2].max(), positions[groups[-1], 2].min()]
        gaps = [float(neck - edges[0]), float(edges[1] - hem)]
        assert all(.010 <= gap <= .020 for gap in gaps), (name, 'Button row end gaps', gaps)
        item = dict(button_count=8, button_centers_m=centers.tolist(),
                    button_pitch_m=(-np.diff(centers[:, 2])).tolist(),
                    button_neck_hem_gaps_m=gaps,
                    front_row_neck_hem_z_m=[neck, hem], placket_supported_samples=samples,
                    frozen_non_detail_geometry=True, upper_ribbon_geometry_uv_vertex_colours_exact=True,
                    preserved_upper_ribbon_samples=upper_count, details={})
        for part in ['Placket', 'Buttons', 'Medal']:
            obj = bpy.data.objects[part]
            obj.data.calc_loop_triangles()
            pos = points(obj)
            attachment = json.loads(obj['attachment'])
            anchors = np.asarray(attachment['base_blender_m'])
            ids = np.linalg.norm(anchors[:, None] - pos[None, :], axis=2).argmin(1)
            support = bpy.data.objects['Placket'] if part == 'Buttons' else body
            tree = surface_tree(support)
            distances = np.array([tree.find_nearest(Vector(pos[i]))[3] for i in ids])
            self_contacts, body_contacts = len(crossing_pairs(obj)), len(crossing_pairs(obj, body))
            assert self_contacts == body_contacts == 0, (name, part, self_contacts, body_contacts)
            assert distances.max() <= .002, (name, part, distances.max())
            entry = dict(triangles=len(obj.data.loop_triangles), self_contacts=self_contacts,
                         body_contacts=body_contacts, base_gap_min_max_m=[float(distances.min()), float(distances.max())])
            if part == 'Medal':
                metal = set(attachment['metal_base_vertex_indices'])
                metal_distances = [tree.find_nearest(Vector(pos[i]))[3] for i in metal]
                ribbon_distances = [tree.find_nearest(Vector(pos[i]))[3] for i in ids if i not in metal]
                frame = json.loads(obj['medal_frame'])
                local = np.einsum('ij,kj->ik', pos-np.array(frame['origin']), np.array(frame['frame']))
                ribbon_vertices = {i for f in obj.data.polygons if obj.data.materials[f.material_index].name.startswith('RibbonFabric') for i in f.vertices}
                # #130: exclude the accepted integral claw from the body envelope.
                plate_ids = list(medal['body_vertex_indices'])
                reverse = local[list(metal)]
                thickness = float(local[plate_ids, 1].max() - local[plate_ids, 1].min())
                assert .002 <= thickness <= .004, (name, 'Actual formed body depth', thickness)
                metal_ids = sorted(set(range(len(pos))) - ribbon_vertices)
                assert len(components(obj)) == 4, '#130: closed body/claw, jump ring, bar and looped ribbon'
                assert len(metal) >= 25, 'Measured reverse anchors'
                normal = -np.array(frame['frame'])[1]
                obj.data.calc_loop_triangles()
                faces = [t.vertices[:] for t in obj.data.loop_triangles if set(t.vertices) <= set(metal_ids)]
                gap = continuous_gap(pos[faces], triangles(body), normal)
                assert gap >= .00025 - 1e-8, (name, 'Continuous metal clearance', gap)
                lower_body = local[metal_ids]
                lower_body = lower_body[lower_body[:, 2] < -.005]
                diameter = float(2 * np.linalg.norm(lower_body[:, [0, 2]], axis=1).max())
                entry.update(body_depth_m=thickness, body_diameter_m=diameter,
                             star_relief_m=json.loads(obj['fitted_medal'])['relief_m'],
                             metal_back_gap_min_max_m=[min(metal_distances), max(metal_distances)],
                             ribbon_back_gap_min_max_m=[min(ribbon_distances), max(ribbon_distances)],
                             continuous_metal_clearance_m=gap, eyelet=json.loads(obj['eyelet']))
            item['details'][part] = entry
        count = 0
        for obj in bpy.context.scene.objects:
            if obj.type == 'MESH' and obj.get('aged_export' if name == 'pilot' else 'export'):
                obj.data.calc_loop_triangles()
                count += len(obj.data.loop_triangles)
        # #130 asset-art allocation and its close-camera reason live beside this gate.
        budget = json.loads((HERE / 'medal-budget.json').read_text())
        assert count <= budget['garment_ceiling'][name], (name, 'Triangle budget', count)
        item['total_triangles'] = count
        report[name] = item
    assert report['pilot']['total_triangles'] / report['working']['total_triangles'] <= 1.5
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sources', type=Path, default=HERE)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    result = measure(args.sources.resolve(), args.baseline.resolve())
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print('PASS: both states retain cloth/ribbon and meet strict contact, support, depth and budget gates')
