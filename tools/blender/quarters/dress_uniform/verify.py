"""Measure the exported garment with trimesh, retaining failed measurements in JSON."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess

import numpy as np
import trimesh
from scipy.spatial import cKDTree
from scipy.spatial.distance import pdist

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
GLB = ROOT / 'assets/props/quarters/dress_uniform.glb'
SCRATCH = ROOT / 'tmp/fit/tunic/sim'
BLENDER = '/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender'
EXPECTED = ['TunicBody', 'Collar', 'ShoulderBoard_L', 'ShoulderBoard_R', 'Placket', 'Buttons', 'CollarInsignia_L', 'CollarInsignia_R', 'RibbonBar', 'Medal', 'Hanger']


def game_points(points):
    p = np.asarray(points)
    return p[:, [0, 2, 1]] * [1, 1, -1]


def clean(mesh):
    mesh = mesh.copy()
    mesh.merge_vertices(merge_tex=True, merge_norm=True)
    return mesh


def crossings(mesh, other=None):
    """Finite mesh-edge/triangle crossings, excluding shared self-mesh endpoints."""
    target = mesh if other is None else other
    edges = mesh.edges_unique
    starts = mesh.vertices[edges[:, 0]]
    ends = mesh.vertices[edges[:, 1]]
    delta = ends - starts
    lengths = np.linalg.norm(delta, axis=1)
    directions = delta / lengths[:, None]
    origins = starts + directions * 1e-7
    tri_ids, ray_ids, locations = trimesh.ray.ray_triangle.ray_triangle_id(target.triangles, origins, directions, tree=target.triangles_tree, multiple_hits=True)
    if not len(tri_ids):
        return 0
    distance = np.einsum('ij,ij->i', locations - starts[ray_ids], directions[ray_ids])
    valid = (distance > 1e-6) & (distance < lengths[ray_ids] - 1e-6)
    if other is None:
        incident = np.any(target.faces[tri_ids, :, None] == edges[ray_ids, None, :], axis=(1, 2))
        valid &= ~incident
    return int(valid.sum())


def gap(a, b):
    samples = np.vstack([a.vertices, a.triangles_center])
    return float(trimesh.proximity.closest_point(b, samples)[1].min())


def main():
    scene = trimesh.load(GLB, force='scene', process=False)
    parts = {}
    materials = set()
    for node in scene.graph.nodes_geometry:
        transform, geometry = scene.graph[node]
        m = scene.geometry[geometry].copy()
        material = getattr(m.visual, 'material', None)
        if material:
            materials.add(material.name)
        m.apply_transform(transform)
        part = next((name for name in EXPECTED if node == name or node.startswith(name + '_')), node)
        parts[part] = trimesh.util.concatenate([parts[part], m]) if part in parts else m
    body_raw = parts['TunicBody']
    uv = body_raw.visual.uv
    regions = {}
    for name, lo, hi in [('body', -.01, 1.01), ('Sleeve_L', 1.09, 1.56), ('Sleeve_R', 1.69, 2.16)]:
        mask = np.all((uv[body_raw.faces, 0] >= lo) & (uv[body_raw.faces, 0] <= hi), axis=1)
        regions[name] = clean(body_raw.submesh([mask], append=True))
    garment = clean(body_raw)
    body = regions['body']
    chest = body.vertices[(body.vertices[:, 1] > -.45) & (body.vertices[:, 1] < -.37)]
    waist = body.vertices[(body.vertices[:, 1] > -.70) & (body.vertices[:, 1] < -.60)]
    hem_mask = (uv[:, 0] < 1.01) & (uv[:, 1] < .001)
    hem = body_raw.vertices[hem_mask, 1]
    dims = body.extents
    width_ratio = float(np.ptp(waist[:, 0]) / np.ptp(chest[:, 0]))
    # Shared UV seams are welded only for topology checks, not for surface distances.
    incidence = np.bincount(garment.edges_unique_inverse)
    seam_gap = 0.0 if np.all(incidence == 2) else None
    step1 = {'body_width_m': float(dims[0]), 'body_depth_m': float(dims[2]), 'hem_level_range_m': float(np.ptp(hem)), 'waist_chest_width_ratio': width_ratio, 'stitched_seam_gap_m': seam_gap}
    step1['pass'] = .50 <= dims[0] <= .58 and dims[2] <= .22 and np.ptp(hem) <= .03 and width_ratio >= .85 and seam_gap is not None and seam_gap <= .002
    sleeves = {}
    for name in ['Sleeve_L', 'Sleeve_R']:
        m = regions[name]
        mask = np.all((m.vertices[m.faces, 1] < -.48) & (m.vertices[m.faces, 1] > -.80), axis=1)
        hanging = m.submesh([mask], append=True)
        minimum = gap(hanging, body)
        sleeves[name] = {'underarm_gap_below_y_minus_0_48_m': minimum, 'armhole_seam_gap_m': seam_gap, 'body_triangle_crossings_below_armpit': crossings(hanging, body), 'pass': minimum >= .010 and seam_gap is not None and seam_gap <= .003}
    construction = json.loads((HERE / 'construction.json').read_text())
    collider_report = {}
    for name, data in construction['colliders_blender'].items():
        m = trimesh.Trimesh(game_points(data['vertices']), data['faces'], process=True)
        samples = np.vstack([garment.vertices, garment.triangles_center])
        inside = m.contains(samples)
        collider_report[name] = {'inside_cloth_samples': int(inside.sum()), 'edge_crossings': crossings(garment, m)}
    self_crossings = crossings(garment)
    details = {}
    for name in EXPECTED:
        if name in ['TunicBody', 'Hanger']:
            continue
        mesh = clean(parts[name])
        entry = construction['attachments'].get(name)
        if entry:
            anchors = game_points(entry['base_blender_m'])
            nearest = cKDTree(mesh.vertices).query(anchors)[1]
            anchors = mesh.vertices[nearest]
            support = clean(parts[entry['support']])
            distance = trimesh.proximity.closest_point(support, anchors)[1]
            anchor_gap = float(distance.max())
        else:
            anchor_gap = None
            support = garment
        # Check all faces, not only the stored attachment footprint, for inward crossings.
        samples = np.vstack([mesh.vertices, mesh.triangles_center])
        inside = support.contains(samples)
        penetration = float(trimesh.proximity.closest_point(support, samples[inside])[1].max()) if inside.any() else 0.0
        limit = .0015 if name.startswith('ShoulderBoard') else .002
        details[name] = {'attachment_gap_max_m': anchor_gap, 'inward_penetration_max_m': penetration, 'pass': (anchor_gap is None or anchor_gap <= limit) and penetration <= .001}
    # Coincident front/back UVs on the thickness returns identify corresponding plies.
    thicknesses = []
    keys = np.round(uv, 6)
    _, inv = np.unique(keys, axis=0, return_inverse=True)
    for group in np.unique(inv):
        points = np.unique(np.round(body_raw.vertices[inv == group], 7), axis=0)
        if len(points) == 2:
            d = np.linalg.norm(points[0] - points[1])
            if .002 < d < .006:
                thicknesses.append(d)
    thickness = {'median_m': float(np.median(thicknesses)), 'min_m': float(min(thicknesses)), 'max_m': float(max(thicknesses)), 'sample_pairs': len(thicknesses), 'nonadjacent_edge_crossings': self_crossings}
    collar_mesh = clean(parts['Collar'])
    collar_spec = construction['attachments']['Collar']
    base_targets = game_points(collar_spec['base_blender_m'])
    top_targets = game_points(collar_spec['top_blender_m'])
    collar_tree = cKDTree(collar_mesh.vertices)
    measured_base = collar_mesh.vertices[collar_tree.query(base_targets)[1]]
    measured_top = collar_mesh.vertices[collar_tree.query(top_targets)[1]]
    band_heights = measured_top[:, 1] - measured_base[:, 1]
    button_components = clean(parts['Buttons']).split(only_watertight=False)
    button_diameters = [float(pdist(m.vertices).max()) for m in button_components]
    medal_components = clean(parts['Medal']).split(only_watertight=False)
    medal_disc = max(medal_components, key=lambda m: m.extents[0])
    frame = construction['issue130_medal_frame']
    blender_medal = medal_disc.vertices[:, [0, 2, 1]] * [1, -1, 1]
    local_medal = (blender_medal - frame['origin']) @ np.array(frame['frame']).T
    lower = local_medal[local_medal[:, 2] < -.005]
    medal_diameter = float(2 * np.linalg.norm(lower[:, [0, 2]], axis=1).max())
    medal_depth = float(np.ptp(local_medal[local_medal[:, 2] <= .01601, 1]))
    emblem_diameters = {}
    for name in ['CollarInsignia_L', 'CollarInsignia_R']:
        center = game_points([construction['attachments'][name]['base_blender_m'][0]])[0]
        emblem_diameters[name] = float(2 * np.linalg.norm(parts[name].vertices[:, :2] - center[:2], axis=1).max())
    radial = np.linalg.norm(collar_mesh.vertices[:, [0, 2]], axis=1)
    slot_radii = radial[radial < .006]
    dimensions = {
        'collar_band_height_min_max_m': [float(band_heights.min()), float(band_heights.max())],
        'button_count': len(button_components), 'button_diameters_m': button_diameters,
        'emblem_circumscribed_diameters_m': emblem_diameters, 'medal_diameter_m': medal_diameter, 'medal_body_depth_m': medal_depth,
        'collar_facing_slot_radii_min_max_m': [float(slot_radii.min()), float(slot_radii.max())],
        'facing_to_hook_radial_clearance_max_m': float(slot_radii.max() - .0035),
    }
    dimensions['pass'] = bool(band_heights.min() >= .040 and band_heights.max() <= .045 and len(button_components) == 8 and all(abs(d - .014) < .0001 for d in button_diameters) and all(abs(d - .020) < .001 for d in emblem_diameters.values()) and abs(medal_diameter - .032) < .0001 and .002 <= medal_depth <= .004 and slot_radii.max() - .0035 < .001)
    settling = {name: float(trial['metrics']['last_five_frames_displacement_m']) for name, trial in construction['simulation'].items()}
    settling['last_five_frames_limit_m'] = .001
    settling['pass'] = settling['body'] <= .001 and settling['sleeves'] <= .001
    # glTF document names are checked separately from trimesh's graph/resource renaming.
    data = GLB.read_bytes()
    length = struct.unpack_from('<I', data, 12)[0]
    document = json.loads(data[20:20 + length])
    nodes = {n['name'] for n in document['nodes'] if 'mesh' in n}
    meshes = {m['name'] for m in document['meshes']}
    triangles = sum(len(m.faces) for m in parts.values())
    reexport = SCRATCH / 'verify-reexport.glb'
    with (SCRATCH / 'verify-reexport.log').open('w') as log:
        subprocess.run([BLENDER, '--background', '--factory-startup', '--python-exit-code', '1', '--python', str(HERE / 'build.py'), '--', '--output', str(reexport)], cwd=ROOT, check=True, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    identical = hashlib.sha256(data).digest() == hashlib.sha256(reexport.read_bytes()).digest()
    all_vertices = np.vstack([m.vertices for m in parts.values()])
    front = {n: float(parts[n].vertices[:, 2].mean()) for n in ['Buttons', 'RibbonBar', 'Medal']}
    orientation = {'up': '+Y', 'front': '+Z', 'origin_at_hook_top_error_m': float(abs(parts['Hanger'].bounds[1, 1])), 'front_detail_centroids_z_m': front, 'pass': all(v > 0 for v in front.values()) and abs(parts['Hanger'].bounds[1, 1]) < .001 and np.ptp(all_vertices[:, 1]) > np.ptp(all_vertices[:, 2])}
    names_ok = set(EXPECTED) == nodes == meshes
    report = {'step1': step1, 'step2': sleeves, 'step3': {'thickness': thickness, 'details': details, 'dimensions': dimensions}, 'settling_simulation_record_m': settling, 'colliders': collider_report, 'orientation': orientation, 'bounds_game_xyz_m': [all_vertices.min(0).tolist(), all_vertices.max(0).tolist()], 'node_names': sorted(nodes), 'mesh_names': sorted(meshes), 'names_pass': names_ok, 'materials': sorted(materials), 'triangles': triangles, 'triangle_limit_exclusive': 15000, 'byte_identical_reexport': identical, 'garment_watertight': garment.is_watertight, 'garment_winding_consistent': garment.is_winding_consistent}
    report['pass'] = bool(step1['pass'] and all(s['pass'] and s['body_triangle_crossings_below_armpit'] == 0 for s in sleeves.values()) and all(d['pass'] for d in details.values()) and all(c['inside_cloth_samples'] == 0 and c['edge_crossings'] == 0 for c in collider_report.values()) and self_crossings == 0 and .003 <= thickness['min_m'] <= thickness['max_m'] <= .004 and dimensions['pass'] and settling['pass'] and names_ok and triangles < 15000 and identical and orientation['pass'] and materials == {'NaturalFabric', 'Brass', 'MedalEnamel', 'RibbonFabric', 'BareSteel'})
    # NumPy scalar booleans need conversion before JSON serialization.
    (HERE / 'verify.json').write_text(json.dumps(report, indent=2, default=lambda x: x.item()) + '\n')
    print(json.dumps(report, indent=2, default=lambda x: x.item()))
    if not report['pass']:
        raise SystemExit('tunic verification failed; see verify.json')


if __name__ == '__main__':
    main()
