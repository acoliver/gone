"""Pass-8 camera-scoped visual gates; other sofa thresholds stay unchanged."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image
from scipy.spatial import cKDTree
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sofa_decay_accept import measure as base_measure
from sofa_decay_policy import ORDER, DECK
from sofa_decay_measure import surface, throw_fall
from seat_image_gates import opening_metrics


def project(points, camera):
    eye = np.array(camera['eye_blender_m'])
    forward = np.array(camera['target_blender_m'])-eye
    forward /= np.linalg.norm(forward)
    right = np.cross(forward, [0, 0, 1.])
    right /= np.linalg.norm(right)
    up = np.cross(right, forward)
    p = points-eye
    width, height = camera['resolution']
    if camera.get('projection') == 'PERSP':
        focal = width*camera['lens_mm']/36
        scale = focal/np.einsum('ij,j->i', p, forward)
    else:
        scale = width/camera['scale']
    return np.c_[width/2+np.einsum('ij,j->i', p, right)*scale,
                 height/2-np.einsum('ij,j->i', p, up)*scale]


def encoded(path):
    rgb = np.array(Image.open(path).convert('RGB'), dtype=np.uint32)
    return rgb[:, :, 0]+(rgb[:, :, 1] << 8)+(rgb[:, :, 2] << 16)


def box_walls(vertices, faces):
    mesh = trimesh.Trimesh(vertices, faces, process=False)
    mesh.merge_vertices(digits_vertex=7)
    steep = np.abs(mesh.face_normals[:, 2]) < .35
    pairs = mesh.face_adjacency
    pairs = pairs[steep[pairs].all(1) & (mesh.face_adjacency_angles < np.radians(20))]
    selected = np.zeros(len(faces), dtype=bool)
    for group in trimesh.graph.connected_components(pairs, nodes=np.flatnonzero(steep)):
        p = mesh.triangles[group].reshape(-1, 3)
        # A skirt that extends below the deck is deliberately free slack.
        # Upright boxing is a connected steep panel above the deck.
        if np.ptp(p[:, 2]) >= .07 and np.ptp(p[:, :2], axis=0).max() >= .08 and p[:, 2].min() >= DECK-.005:
            selected[group] = True
    return selected


def residue_opening_counts(before, after, cover_ids, residue_ids):
    through_cover = np.isin(before, cover_ids)
    visible = np.bincount(after[through_cover], minlength=int(residue_ids.max())+1)
    return visible[residue_ids]


def visibility_gates(directory):
    records = {label: json.loads((directory/(label+'.json')).read_text()) for label in ['before', 'after']}
    maps = {label: {view: encoded(directory/(label+'-'+view+'.png')) for view in ['hero', 'front']}
            for label in records}
    walls, residue = {}, {}
    for name in ORDER:
        data = {label: np.load(directory/records[label]['parts'][name]) for label in records}
        if name.startswith('Seat'):
            counts = {}
            for label, d in data.items():
                ids = d['ids'][box_walls(d['vertices'], d['faces'])]
                counts[label] = {view: int(np.isin(image, ids).sum()) for view, image in maps[label].items()}
            ratios = {v: counts['after'][v]/counts['before'][v] for v in ['hero', 'front'] if counts['before'][v]}
            walls[name] = {'box_wall_pixels': counts, 'ratios': ratios,
                           'ratio': max(ratios.values(), default=None),
                           'pass': bool(ratios) and all(v <= .25 for v in ratios.values())}
        d = data['after']
        mask = d['kinds'] == 'residue'
        f, ids = d['faces'][mask], d['ids'][mask]
        mesh = trimesh.Trimesh(d['vertices'], f, process=False)
        mesh.merge_vertices(digits_vertex=7)
        fractions = np.zeros(len(f))
        before = data['before']
        cover_ids = before['ids'][before['kinds'] == 'cover']
        for view, camera in records['after']['cameras'].items():
            counts = residue_opening_counts(maps['before'][view], maps['after'][view], cover_ids, ids)
            projected = project(d['vertices'], camera)[f]
            a, b = projected[:, 1]-projected[:, 0], projected[:, 2]-projected[:, 0]
            area_px = np.abs(a[:, 0]*b[:, 1]-a[:, 1]*b[:, 0])/2
            fraction = np.minimum(1., counts/np.maximum(area_px, 1e-12))
            fractions = np.maximum(fractions, fraction)
        area = mesh.area_faces*fractions
        planar = 0.
        for group in mesh.facets:
            exposed = area[group].sum()
            if exposed > .001:
                planar += exposed
        total = float(area.sum())
        value = float(planar/total) if total else 0.
        residue[name] = {'visible_area_m2': total, 'visible_large_planar_area_m2': float(planar),
                         'fraction': value, 'pass': value <= .05,
                         'visibility': 'first-hit hero/front union within the original cover silhouette; hidden and outside residue contributes zero'}
    return {'G12': {'value': walls, 'pass': all(v['pass'] for v in walls.values())},
            'G7': {'value': residue, 'pass': all(v['pass'] for v in residue.values())}}


def tear_gate(out, renders, gates):
    cameras = json.loads((renders/'diagnostics/cameras.json').read_text())['parts']
    results = {}
    simulation = json.loads((out/'simulation.json').read_text())
    for name in [*ORDER, 'Throw']:
        if name == 'Throw':
            results[name] = gates['G3']['value'][name]
            continue
        rgb = np.array(Image.open(renders/'diagnostics'/name/'labels.png').convert('RGB'))
        cloth = ((rgb[:, :, 0] > 250) & (rgb[:, :, 1] < 5) & (rgb[:, :, 2] < 5)) | ((rgb[:, :, 1] > 250) & (rgb[:, :, 0] < 5) & (rgb[:, :, 2] < 5))
        openings = opening_metrics(cloth)
        lip = np.load(out/(name+'-lip-classes.npz'))
        projected = project(lip['points'], cameras[name]['labels'])
        tree = cKDTree(projected)
        for opening in openings:
            yx = np.mean(opening['bounds_px'], axis=0)
            _, index = tree.query(yx[::-1])
            opening['class'] = str(lip['classes'][index])
            low, high = np.array(opening['bounds_px'])
            low = np.maximum(0, low-4)
            high = np.minimum(np.array(rgb.shape[:2])-1, high+4)
            tile = rgb[low[0]:high[0]+1, low[1]:high[1]+1]
            opening['fringe_pixels'] = int(((tile[:, :, 1] > 250) & (tile[:, :, 0] < 5) & (tile[:, :, 2] < 5)).sum())
        samples = simulation['cushions'][name]['G5']['samples']
        lip_tree = cKDTree(lip['points'])
        _, ids = lip_tree.query([s['midpoint_blender_m'] for s in samples])
        seam_samples = [s for s, i in zip(samples, ids) if lip['classes'][i] == 'seam']
        length = sum(s['length_m'] for s in seam_samples)
        lifted = sum(s['length_m'] for s in seam_samples if s['lift_m'] is not None and s['lift_m'] > .003)
        gape = lifted/length if length else 0.
        tears = [o for o in openings if o['class'] == 'tear']
        seams = [o for o in openings if o['class'] == 'seam']
        seam_pass = not seams or (gape >= .30 and all(o['fringe_pixels'] > 0 for o in seams))
        results[name] = {'value': [o['longest_straight_run_px'] for o in tears], 'openings': openings,
                         'seam_failures_exempt': len(seams), 'seam_gape_fraction': gape,
                         'seam_fringe_and_gape_pass': seam_pass,
                         'threshold': '<=12 px / 4.5 mm on panel tears only; seams need G5 gape and fringe',
                         'pass': bool(tears) and all(o['longest_straight_run_px'] <= 12 for o in tears) and seam_pass}
    return {'value': results, 'pass': all(v['pass'] for v in results.values())}


def measure(args):
    result = base_measure(args.input, args.out, args.renders, args.collisions, args.baseline)
    for key, value in visibility_gates(args.renders/'visibility').items():
        result['gates'][key].update(value, status='measured')
    result['gates']['G3'].update(tear_gate(args.out, args.renders, result['gates']), status='measured')
    fall = throw_fall(surface(args.out/'throw-game.npz'))
    mesh = surface(args.out/'throw-game.npz')
    components = mesh.split(only_watertight=False)
    held = []
    for part in components:
        p = part.vertices
        arm = (p[:, 0] >= .93) & (p[:, 0] <= 1.12) & (p[:, 1] >= -.46) & (p[:, 1] <= .22) & (p[:, 2] >= .76)
        if arm.any() and p[:, 2].min() <= .100:
            held.append(part)
    fall.update(arm_to_near_floor_components=len(held), floor_limit_m=.100, minimum_z_m=float(mesh.bounds[0, 2]))
    fall['pass'] = (len(held) == 1 and len(components) <= 2 and fall['distance_m'] is not None and
                    fall['distance_m'] <= .25 and fall['folds'] >= 3)
    result['gates']['G19'].update(value=fall, **{'pass': fall['pass']},
        threshold='<=0.250 m from arm; >=3 folds >=10 mm; one connected pinned-corner hang to <=100 mm from floor; <=1 detached remnant')
    result['gates']['G3']['measure'] = 'panel-tear straight runs only; seam failures still require gape and fringe'
    result['gates']['G7']['measure'] = 'visible residue in >10 cm2 coplanar facets, first-hit hero/front union'
    result['gates']['G12']['measure'] = 'visible upright box-wall pixels relative to unaged, hero and front'
    record = json.loads((args.out/'simulation.json').read_text())
    result['invariants']['all_cloth_settled'] = all(record[k+'_simulation']['settled'] for k in ['seats', 'backs']) and record['throw']['simulation']['settled']
    result['invariants']['no_self_collision_exclusions'] = all(not record[k+'_setup']['mesh_quality']['self_collision_exclusions'] for k in ['seats', 'backs'])
    from verify import geometry_buffers
    exported = geometry_buffers(args.input)
    result['invariants']['exported_fringe_nodes'] = all(name+'_Fringe' in exported for name in [*ORDER, 'Throw'])
    result['pass'] = all(g['pass'] for g in result['gates'].values()) and all(result['invariants'].values())
    result['publication_allowed'] = result['pass']
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ['input', 'out', 'renders', 'collisions', 'baseline']:
        parser.add_argument('--'+flag, type=Path, required=True)
    args = parser.parse_args()
    result = measure(args)
    (args.out/'gates.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['pass'] else 1)
