"""Measure tunic G-gates. Missing measurements fail and block publication."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np
import trimesh
from PIL import Image
from scipy.ndimage import gaussian_filter1d
from scipy.spatial import ConvexHull
from skimage.draw import polygon

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / 'tools/blender/quarters_aging'))
from seat_image_gates import evaluate, visible_dihedrals

THRESHOLDS = {'G1': '<= 0.06 visible sharp adjacency', 'G2': '<= 0.02 normal-jump pixels',
              'G3': '<= 12 px longest straight opening contour', 'G4': '>= 0.35 opening width CV',
              'G5': '>= 0.30 lip length lifted >3 mm', 'G6': '1.15..1.40 contour dimension',
              'G20': '<= 0.10 sharp adjacency within 120 mm of hanger',
              'G21': '0 hanger pixels outside split hull inside unaged cloth mask',
              'G22': '<= 0.45 maximum camera-depth / camera-width at 25%, 50%, 75% sleeve length',
              'G23': '>= 0.35 retained arc and >= 0.70 released-edge fringe coverage',
              'G24': '0.92..1.08 chest width / unaged', 'G25': '>= 0.70 open-hem fringe coverage',
              'G26': '< 0.30 hem-height autocorrelation peak, 20..120 mm lags',
              'G27': '0.015..0.035 m heap height', 'G28': '>= 2 fallen cloth pieces',
              'G29': '0.5..2 mound volume / lost wool at packing 0.05..0.15',
              'G30': '0 changed/new-part SAT crossings; exact unchanged hanger baseline',
              'G31': '<= 1.5 x unaged triangles', 'G32': '<= 0.0015 m boundary Hausdorff'}


def meshes(path):
    scene = trimesh.load(path, force='scene', process=False)
    result = {}
    for node in scene.graph.nodes_geometry:
        transform, name = scene.graph[node]
        mesh = scene.geometry[name].copy()
        mesh.apply_transform(transform)
        part = next((n for n in ('TunicBody', 'Hanger', 'FibreDust') if node == n or node.startswith(n+'_')), node)
        result[part] = trimesh.util.concatenate([result[part], mesh]) if part in result else mesh
    return result


def sheet_regions(data):
    v, f, uv = data['vertices'], data['faces'], data['uv']
    face_uv = uv.mean(1)
    return v, f, face_uv


def hem_autocorrelation(v, f, uv):
    edges = np.sort(np.vstack([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]), axis=1)
    unique, counts = np.unique(edges, axis=0, return_counts=True)
    boundary = unique[counts == 1]
    vertex_uv = np.zeros((len(v), 2))
    for ids, values in zip(f, uv):
        vertex_uv[ids] = values
    selected = [edge for edge in boundary if (vertex_uv[edge, 0] < .48).all() and
                (vertex_uv[edge, 1] < .06).all()]
    if not selected:
        raise ValueError('No front hem boundary samples')
    graph = {}
    remaining = {tuple(edge) for edge in selected}
    for a, b in remaining:
        graph.setdefault(a, set()).add(b)
        graph.setdefault(b, set()).add(a)
    if any(len(neighbors) > 2 for neighbors in graph.values()):
        raise ValueError('Front hem boundary branches')
    from hem_metrics import periodic_peak
    peaks, correlations = [], []
    while remaining:
        ids = {i for edge in remaining for i in edge}
        ends = [i for i in ids if len(graph[i]) == 1]
        current = min(ends or ids)
        chain = [current]
        while True:
            edge = next((tuple(sorted((current, j))) for j in sorted(graph[current])
                         if tuple(sorted((current, j))) in remaining), None)
            if edge is None:
                break
            remaining.remove(edge)
            current = edge[1] if edge[0] == current else edge[0]
            chain.append(current)
        points = v[chain]
        distance = np.r_[0., np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
        station = np.arange(0, distance[-1], .001)
        if len(station) < 42:
            continue
        peak, values = periodic_peak(station, np.interp(station, distance, points[:, 2]))
        peaks.append(peak)
        correlations.append(values)
    if not peaks:
        raise ValueError('No front hem segment long enough to measure 20 mm periods')
    return max(peaks), correlations


def measure(out, images):
    gates = {key: dict(value=None, threshold=value, status='not_measured', pass_gate=False)
             for key, value in THRESHOLDS.items()}
    def put(key, value, passed, **extra):
        gates[key].update(value=value, status='pass' if passed else 'fail', pass_gate=bool(passed), **extra)
    record = json.loads((out / 'finished.json').read_text()) if (out / 'finished.json').exists() else json.loads((out / 'simulated.json').read_text())
    data_path = out / 'game-sheet.npz'
    if data_path.exists():
        data = np.load(data_path)
        v, f, face_uv = sheet_regions(data)
        body = trimesh.Trimesh(v, f, process=False)
        body.merge_vertices(digits_vertex=7)
        distances = trimesh.proximity.closest_point(meshes(ROOT / 'assets/props/quarters/dress_uniform.glb')['Hanger'],
                                                   v[:, [0, 2, 1]]*[1, 1, -1])[1]
        near = (distances[f].min(1) <= .12)
        # Preserve the sheet's indexed topology after position-only welding.
        pairs = body.face_adjacency
        selected = near[pairs].all(1)
        sharp = float(np.mean(body.face_adjacency_angles[selected] > np.pi/6))
        put('G20', sharp, sharp <= .10)
        from sleeve_metrics import pressed_sections
        sleeve = pressed_sections(v, f, data['uv'])
        ratio = sleeve.pop('ratio')
        put('G22', ratio, ratio <= .45, **sleeve)
        front = np.unique(f[face_uv[:, 0] < 1.])
        chest = v[front][np.abs(v[front, 2]+.285) < .025]
        baseline = meshes(ROOT / 'assets/props/quarters/dress_uniform.glb')['TunicBody']
        old_uv = baseline.visual.uv
        old = baseline.vertices[(old_uv[:, 0] < 1.) & (np.abs(baseline.vertices[:, 1]+.285) < .025)]
        width = float(np.ptp(chest[:, 0])/np.ptp(old[:, 0]))
        put('G24', width, .92 <= width <= 1.08)
        correlation, values = hem_autocorrelation(v, f, data['uv'])
        put('G26', correlation, correlation < .30, correlations=values)
    if 'lip_lift' in record:
        put('G5', record['lip_lift']['fraction'], record['lip_lift']['fraction'] >= .30)
    if 'fringe' in record:
        retained = record['splits']['armhole']['retained_fraction']
        allowance = record['fringe']['Seam allowance']['authored_coverage']
        hem = record['fringe']['Hem fringe']['authored_coverage']
        put('G23', dict(retained_arc=retained, fringe_coverage=allowance), retained >= .35 and allowance >= .70)
        put('G25', hem, hem >= .70)
    candidate = out / 'candidate.glb'
    if candidate.exists():
        parts = meshes(candidate)
        mound = parts['FibreDust']
        height = float(mound.bounds[1, 1]+.95)
        put('G27', height, .015 <= height <= .035)
        import re
        fallen = {re.match(r'FallenHem_\d+', name).group(0) for name in parts
                  if re.fullmatch(r'FallenHem_\d+(?:_[a-f0-9]+)?', name)}
        put('G28', len(fallen), len(fallen) >= 2)
        lost = record['heap']['lost_area_m2']*.0035
        volume = abs(float(mound.volume))
        packing = lost/volume
        put('G29', dict(volume_m3=volume, lost_wool_m3=lost, inferred_packing=packing),
            volume >= lost/.15/2 and volume <= lost/.05*2)
        triangles = sum(len(m.faces) for m in parts.values())
        original = sum(len(m.faces) for m in meshes(ROOT / 'assets/props/quarters/dress_uniform.glb').values())
        put('G31', dict(triangles=triangles, unaged_triangles=original, ratio=triangles/original), triangles <= 1.5*original)
    if 'reduction' in record:
        worst = max(v['boundary_hausdorff_upper_m'] for v in record['reduction'].values())
        put('G32', worst, worst <= .0015)
    sat_path = out / 'collisions.json'
    if sat_path.exists():
        sat = json.loads(sat_path.read_text())
        baseline = json.loads((out.parent / 'unaged-sat.json').read_text())
        from tunic_contacts import contact_gate
        unaged = meshes(ROOT / 'assets/props/quarters/dress_uniform.glb')['Hanger']
        aged = meshes(candidate)['Hanger']
        contacts = contact_gate(sat, baseline, unaged.triangles, aged.triangles)
        put('G30', contacts, contacts['pass'])
    if (images / 'tunic-labels.png').exists() and (images / 'tunic-normals.png').exists():
        rgb = np.array(Image.open(images / 'tunic-labels.png').convert('RGB'))
        from diagnostic_labels import decode_labels
        labels = decode_labels(rgb)
        measures = evaluate(labels, np.array(Image.open(images / 'tunic-normals.png').convert('RGB')))
        for key in ['G2', 'G3', 'G4', 'G6']:
            item = measures[key]
            put(key, item.get('value', item.get('fraction')), item['pass'])
        gates['opening_measurements'] = measures['openings']
    if (images / 'visible-faces.npz').exists() and (images / 'tunic-faces.png').exists():
        source = np.load(images / 'visible-faces.npz')
        views = [images / 'tunic-faces.png']+sorted(images.glob('tunic-faces-*.png'))
        item = visible_dihedrals(source['vertices'], source['faces'], source['ids'],
                                 [np.array(Image.open(path).convert('RGB')) for path in views])
        put('G1', item['fraction'], item['fraction'] <= .06, visible_pairs=item['visible_pairs'],
            views=[path.name for path in views])
    if (images / 'tunic-hero-labels.png').exists():
        after = np.array(Image.open(images / 'tunic-hero-labels.png').convert('RGB'))
        before = np.array(Image.open(images / 'tunic-hero-before.png').convert('RGB'))
        cameras = json.loads((images / 'tunic-cameras.json').read_text())
        points = np.array(cameras['split_hull_pixels'])
        hull_mask = np.zeros(after.shape[:2], bool)
        if len(points) >= 3:
            hull = points[ConvexHull(points).vertices]
            yy, xx = polygon(hull[:, 1], hull[:, 0], shape=hull_mask.shape)
            hull_mask[yy, xx] = True
        cloth_before = (before[:, :, 0] > 230) & (before[:, :, 1] < 20) & (before[:, :, 2] < 20)
        wire_after = (after[:, :, 2] > 230) & (after[:, :, 0] < 20) & (after[:, :, 1] < 20)
        poke = int((cloth_before & wire_after & ~hull_mask).sum())
        put('G21', poke, poke == 0)
    gates['pass'] = all(gates[key]['pass_gate'] for key in THRESHOLDS)
    (out / 'gates.json').write_text(json.dumps(gates, indent=2)+'\n')
    print(json.dumps(gates, indent=2))
    return gates


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, default=ROOT / 'tmp/age/tunic7/source-damped')
    p.add_argument('--images', type=Path, default=ROOT / 'tmp/age/tunic7')
    a = p.parse_args()
    r = measure(a.out.resolve(), a.images.resolve())
    raise SystemExit(0 if r['pass'] else 1)
