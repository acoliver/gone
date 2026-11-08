"""Viewer-facing aging measurements on exported, world-transformed GLB geometry."""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree
from scipy.signal import find_peaks, peak_prominences
import trimesh

from verify import clean, geometry_buffers, load as load_combined, pivots, silhouette

ROOT = Path(__file__).resolve().parents[3]


def load(path):
    parts, doc = load_combined(path)
    scene = trimesh.load(path, force='scene', process=False)
    for node in scene.graph.nodes_geometry:
        transform, geometry = scene.graph[node]
        mesh = scene.geometry[geometry].copy()
        mesh.apply_transform(transform)
        name = next(n for n in sorted(parts, key=len, reverse=True) if node == n or node.startswith(n + '_'))
        parts[name].metadata.setdefault('raw_primitives', {})[mesh.visual.material.name] = mesh
    return parts, doc


def primitive(mesh, material):
    if material in mesh.metadata.get('raw_primitives', {}):
        return mesh.metadata['raw_primitives'][material]
    mask = np.zeros(len(mesh.faces), dtype=bool)
    for start, end, name in mesh.metadata['material_source_ranges']:
        if name == material:
            mask[start:end] = True
    if not mask.any():
        raise ValueError(f'Missing material surface {material}')
    return mesh.submesh([mask], append=True)


def boundaries(mesh):
    """Weld position seams without confusing UV seams with physical tear boundaries."""
    keys, ids = {}, []
    positions = []
    for p in mesh.vertices:
        key = tuple(np.round(p, 7))
        if key not in keys:
            keys[key] = len(keys)
            positions.append(p)
        ids.append(keys[key])
    ids = np.asarray(ids)
    uses = {}
    for face in mesh.faces:
        for a, b in zip(face, np.roll(face, -1)):
            key = tuple(sorted((ids[a], ids[b])))
            uses.setdefault(key, []).append((a, b))
    edges = [e for e, occurrences in uses.items() if len(occurrences) == 1]
    graph = {}
    for a, b in edges:
        graph.setdefault(a, []).append(b)
        graph.setdefault(b, []).append(a)
    if any(len(v) != 2 for v in graph.values()):
        raise ValueError('Unbounded or branched external fabric boundary')
    remaining, loops = set(graph), []
    while remaining:
        start = min(remaining)
        order, previous, current = [], None, start
        while True:
            order.append(current)
            remaining.remove(current)
            nxt = next(i for i in graph[current] if i != previous)
            if nxt == start:
                break
            previous, current = current, nxt
        loops.append(np.asarray(positions)[order])
    uv_edges = [mesh.visual.uv[list(uses[e][0])] for e in edges] if getattr(mesh.visual, 'uv', None) is not None else []
    return loops, uv_edges


def hole(loop):
    centred = loop - loop.mean(0)
    _, _, axes = np.linalg.svd(centred, full_matrices=False)
    planar = centred @ axes[:2].T
    following = np.roll(planar, -1, axis=0)
    area = abs(float(np.sum(planar[:, 0] * following[:, 1] - planar[:, 1] * following[:, 0]))) / 2
    perimeter = float(np.linalg.norm(np.roll(loop, -1, axis=0) - loop, axis=1).sum())
    size = float(np.linalg.norm(loop[:, None] - loop[None, :], axis=2).max())
    return {'size_m': size, 'perimeter_m': perimeter, 'projected_area_m2': area,
            'irregularity': perimeter / np.sqrt(area), 'irregularity_min': 5.5}


def straight_run(loop):
    longest = 0.
    n = len(loop)
    for i in range(n):
        pts = np.vstack([loop[i:], loop[:i]])
        for j in range(1, n):
            delta = pts[j] - pts[0]
            length = np.linalg.norm(delta)
            if length < 1e-9:
                continue
            t = (pts[:j + 1] - pts[0]) @ delta / length ** 2
            distance = np.linalg.norm(pts[:j + 1] - pts[0] - t[:, None] * delta, axis=1)
            if distance.max() > .001:
                continue
            longest = max(longest, float(length))
    return longest


def projected_masks(before, after, eye, target, size=1400, occluders=((), ())):
    forward = np.asarray(target, dtype=float) - eye
    forward /= np.linalg.norm(forward)
    right = np.cross(forward, [0, 1, 0])
    right /= np.linalg.norm(right)
    up = np.cross(right, forward)
    basis = np.array([right, up])
    points = np.vstack([m.vertices @ basis.T for m in before + after])
    lo, hi = points.min(0), points.max(0)
    scale = (size - 5) / max(hi - lo)
    masks = []
    for group, obstruction in zip([before, after], occluders):
        depth = np.full((size, size), np.inf)
        mask = np.zeros((size, size), dtype=bool)
        for mesh, selected in [(m, True) for m in group] + [(m, False) for m in obstruction]:
            pixel = (mesh.vertices @ basis.T - lo) * scale + 2
            distance = (mesh.vertices - eye) @ forward
            for face in mesh.faces:
                triangle = pixel[face]
                left, bottom = np.maximum(0, np.floor(triangle.min(0)).astype(int))
                right_edge, top = np.minimum(size - 1, np.ceil(triangle.max(0)).astype(int))
                if right_edge < left or top < bottom:
                    continue
                a, b, c = triangle
                determinant = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
                if abs(determinant) < 1e-12:
                    continue
                x, y = np.meshgrid(np.arange(left, right_edge + 1) + .5, np.arange(bottom, top + 1) + .5)
                u = ((b[1] - c[1]) * (x - c[0]) + (c[0] - b[0]) * (y - c[1])) / determinant
                v = ((c[1] - a[1]) * (x - c[0]) + (a[0] - c[0]) * (y - c[1])) / determinant
                w = 1 - u - v
                z = u * distance[face[0]] + v * distance[face[1]] + w * distance[face[2]]
                tile = depth[bottom:top + 1, left:right_edge + 1]
                nearer = (u >= -1e-9) & (v >= -1e-9) & (w >= -1e-9) & (z < tile)
                tile[nearer] = z[nearer]
                mask[bottom:top + 1, left:right_edge + 1][nearer] = selected
        masks.append(mask)
    return masks


def heights(mesh, xy):
    origins = np.c_[xy[:, 0], np.full(len(xy), 2.), xy[:, 1]]
    directions = np.tile([0, -1, 0], (len(xy), 1))
    locations, rays, _ = mesh.ray.intersects_location(origins, directions, multiple_hits=True)
    result = np.full(len(xy), np.nan)
    for p, ray in zip(locations, rays):
        if np.isnan(result[ray]) or p[1] > result[ray]:
            result[ray] = p[1]
    return result


def sofa_gates(before, after):
    result, split_points = {}, []
    for name in sorted(n for n in before if 'Cushion' in n):
        outer = primitive(after[name], 'CharcoalUpholstery')
        loops, _ = boundaries(outer)
        holes = [hole(loop) for loop in loops]
        split_points.extend(np.vstack(loops))
        crust = primitive(after[name], 'Foam')
        ratio = float(after[name].volume / before[name].volume)
        entry = {'volume_ratio': ratio, 'volume_band': [.25, .35], 'volume_pass': .25 <= ratio <= .35,
                 'openings': holes, 'opening_count': len(holes), 'opening_count_band': [1, 4],
                 'splits_pass': 1 <= len(holes) <= 4 and all(.020 <= h['size_m'] <= .150 and h['irregularity'] >= 5.5 for h in holes),
                 'crust_watertight': clean(crust).is_watertight}
        if name.startswith('Seat'):
            cx = float((outer.bounds[0, 0] + outer.bounds[1, 0]) / 2)
            cy = float((outer.bounds[0, 2] + outer.bounds[1, 2]) / 2)
            centre = float(heights(outer, np.array([[cx, cy]]))[0])
            x, z = np.meshgrid(np.linspace(cx - .28, cx + .28, 35), np.linspace(cy - .23, cy + .23, 33))
            xy = np.c_[x.ravel(), z.ravel()]
            y = heights(outer, xy)
            valid = np.isfinite(y) & (y > .43)
            xy, y = xy[valid], y[valid]
            design = np.c_[xy, np.ones(len(xy))]
            residual = y - design @ np.linalg.lstsq(design, y, rcond=None)[0]
            edge = np.maximum(abs((xy[:, 0] - cx) / .28), abs((xy[:, 1] - cy) / .23)) > .95
            sag = float(np.mean(y[edge]) - centre)
            height_ratio = (centre - .3898) / (before[name].bounds[1, 1] - .3898)
            entry['visible_seat'] = {'centre_y_m': centre, 'height_above_deck_ratio': height_ratio,
                                     'band': [.35, .45], 'edge_to_centre_sag_m': sag, 'sag_min_m': .015,
                                     'detrended_top_std_m': float(residual.std()), 'std_min_m': .006,
                                     'pass': .35 <= height_ratio <= .45 and sag >= .015 and residual.std() >= .006}
        else:
            angle = np.radians(35)
            eye = np.array([3 * np.sin(angle), 1.8, 3 * np.cos(angle)])
            old, new = projected_masks([before[name]], [after[name]], eye, [0, .4, 0],
                                       occluders=([mesh for key, mesh in before.items() if key != name],
                                                  [mesh for key, mesh in after.items() if key != name]))
            coverage = float((old & new).sum() / old.sum())
            entry['hero_coverage'] = {'value': coverage, 'min': .55, 'method': 'Orthographic hero-camera first-hit depth raster, including all other prop parts as occluders.', 'pass': coverage >= .55}
            entry['retained_top_fraction'] = float((outer.bounds[1, 1] - before[name].bounds[0, 1]) / np.ptp(before[name].vertices[:, 1]))
        result[name] = entry
    pieces = clean(after['FoamDebris']).split(only_watertight=False)
    support = trimesh.util.concatenate([after['Frame'], *[after[n] for n in before if 'Cushion' in n]])
    tree = cKDTree(np.asarray(split_points))
    debris = []
    for piece in pieces:
        size = float(piece.extents.max())
        distance = float(tree.query(piece.vertices)[0].min())
        bottom = piece.vertices[piece.vertices[:, 1] <= piece.bounds[0, 1] + 1e-6]
        gap = float(trimesh.proximity.closest_point(support, bottom)[1].min())
        debris.append({'size_m': size, 'split_distance_m': distance, 'support_gap_m': gap})
    qualified = [p for p in debris if .002 <= p['size_m'] <= .015 and p['split_distance_m'] <= .25]
    resting = sum(p['support_gap_m'] <= .002 for p in qualified) / max(1, len(qualified))
    result['crumbs'] = {'pieces': len(pieces), 'qualifying_pieces': len(qualified), 'min_pieces': 150,
                        'size_band_m': [.002, .015], 'max_split_distance_m': max(p['split_distance_m'] for p in debris),
                        'resting_fraction': resting, 'resting_min': .60, 'max_support_gap_m': max(p['support_gap_m'] for p in debris),
                        'pass': len(qualified) >= 150 and resting >= .60}
    throw = primitive(after['Throw'], 'OatmealWool')
    loops, _ = boundaries(throw)
    holes = sorted(loops, key=lambda p: -np.linalg.norm(np.roll(p, -1, axis=0) - p, axis=1).sum())[1:]
    proportion = float(throw.area_faces[throw.triangles_center[:, 1] < .8075].sum() / throw.area)
    metrics = [hole(loop) for loop in holes]
    result['throw'] = {'area_below_cap_fraction': proportion, 'min_fraction': .40,
                        'detached_piece_on_floor': 'ThrowDetachedPiece' in after and after['ThrowDetachedPiece'].bounds[0, 1] < .002,
                        'holes': metrics, 'pass': proportion >= .4 and 'ThrowDetachedPiece' in after and all(h['irregularity'] >= 5.5 for h in metrics)}
    return result


def notch_depths(heights):
    n = len(heights)
    periodic = np.tile(heights, 3)
    peaks, _ = find_peaks(periodic, prominence=.001)
    central = peaks[(peaks >= n) & (peaks < 2 * n)]
    return peak_prominences(periodic, central, wlen=n)[0]


def tunic_gates(before, after):
    outer = primitive(after['TunicBody'], 'NaturalFabric')
    loops, uv_edges = boundaries(outer)
    tears = [p for p in loops if -.83 < p[:, 1].mean() < -.19]
    metrics = [{**hole(p), 'max_straight_run_m': straight_run(p)} for p in tears]
    hem = np.vstack([p for p in loops if p[:, 1].mean() < -.83 and np.ptp(p[:, 0]) > .25])
    notches = notch_depths(hem[:, 1])
    coefficient = float(notches.std() / notches.mean())
    iou = silhouette([before['TunicBody']], [after['TunicBody']])
    # Match the retained cloth pattern, rather than nearest world points after slumping.
    source = before['TunicBody']
    select = (abs(source.vertices[:, 0]) > .12) & (abs(source.vertices[:, 0]) < .24) & (source.vertices[:, 1] > -.23)
    distance, index = cKDTree(outer.visual.uv).query(source.visual.uv[select])
    drop = float(np.mean(source.vertices[select, 1] - outer.vertices[index, 1]))
    # The sleeve cap is V=0 in its original flat-pattern island. Tear refinement retains it.
    intervals = []
    for edge in uv_edges:
        if np.all(abs(edge[:, 1]) < 1e-6) and np.all((edge[:, 0] >= 1.6999) & (edge[:, 0] <= 2.1501)):
            intervals.append(sorted(edge[:, 0]))
    intervals.sort()
    merged = []
    for lo, hi in intervals:
        if merged and lo <= merged[-1][1] + 1e-6:
            merged[-1][1] = max(merged[-1][1], hi)
        else:
            merged.append([float(lo), float(hi)])
    reference_edges = {}
    for face in source.faces:
        for a, b in zip(face, np.roll(face, -1)):
            uv = source.visual.uv[[a, b]]
            if np.all(abs(uv[:, 1]) < 1e-6) and np.all((uv[:, 0] >= 1.6999) & (uv[:, 0] <= 2.1501)):
                lo, hi = sorted(uv[:, 0])
                if hi - lo > 1e-6:
                    reference_edges.setdefault((round(float(lo), 6), round(float(hi), 6)), []).append(float(np.linalg.norm(source.vertices[a] - source.vertices[b])))
    total, opened = 0., 0.
    for (lo, hi), lengths in reference_edges.items():
        length = np.mean(lengths)
        total += length
        opened += length * sum(max(0, min(hi, b) - max(lo, a)) for a, b in merged) / (hi - lo)
    fraction = float(opened / total)
    dust = after['FibreDust']
    centre = (dust.bounds[0] + dust.bounds[1]) / 2
    under_hem = (hem[:, [0, 2]].min(0) + hem[:, [0, 2]].max(0)) / 2
    offset = float(np.linalg.norm(centre[[0, 2]] - under_hem))
    height, diameter = float(dust.extents[1]), float(max(dust.extents[[0, 2]]))
    return {'tears': {'holes': metrics, 'straight_run_max_m': .030, 'pass': bool(metrics) and all(h['irregularity'] >= 5.5 and h['max_straight_run_m'] <= .030 for h in metrics)},
            'hem': {'notch_mean_m': float(notches.mean()), 'notch_std_m': float(notches.std()), 'std_over_mean': coefficient, 'min': .40, 'pass': coefficient >= .40},
            'sleeve': {'open_reference_seam_length_fraction': fraction, 'band': [.50, .70], 'intervals': merged, 'pass': .50 <= fraction <= .70},
            'slump': {'shoulder_mean_drop_m': drop, 'drop_min_m': .015, 'silhouette_iou': iou, 'iou_band': [.55, .80], 'pass': drop >= .015 and .55 <= iou <= .80},
            'fibre_heap': {'height_m': height, 'height_min_m': .006, 'diameter_m': diameter, 'diameter_band_m': [.08, .20], 'under_hem_offset_m': offset, 'offset_max_m': .050, 'pass': height >= .006 and .08 <= diameter <= .20 and offset <= .050}}


def verify(prop, input_path, reexport, collisions):
    original = ROOT / f'assets/props/quarters/{prop}.glb'
    before, old_doc = load(original)
    after, new_doc = load(input_path)
    old_count = sum(len(m.faces) for m in before.values())
    count = sum(len(m.faces) for m in after.values())
    fixed = ['Frame', 'Feet', 'Rivets'] if prop == 'sofa' else ['Hanger']
    old_buffers, new_buffers = geometry_buffers(original), geometry_buffers(input_path)
    old_pivots, new_pivots = pivots(old_doc), pivots(new_doc)
    shared = {'triangles': {'unaged': old_count, 'aged': count, 'ratio': count / old_count, 'limit_ratio': 1.5, 'pass': count <= 1.5 * old_count},
              'unchanged_fixed_geometry_bytes': {n: old_buffers[n] == new_buffers[n] for n in fixed},
              'origins_and_pivots': {'unchanged': all(new_pivots[n] == p for n, p in old_pivots.items())},
              'byte_identical_reexport': reexport.exists() and input_path.read_bytes() == reexport.read_bytes(),
              'collision': json.loads(collisions.read_text())}
    gates = sofa_gates(before, after) if prop == 'sofa' else tunic_gates(before, after)
    result = {'prop': prop, 'shared': shared, 'visible': gates}
    result['pass'] = shared['triangles']['pass'] and all(shared['unchanged_fixed_geometry_bytes'].values()) and shared['origins_and_pivots']['unchanged'] and shared['byte_identical_reexport'] and shared['collision']['pass']
    for entry in gates.values():
        result['pass'] &= entry.get('pass', True) and entry.get('volume_pass', True) and entry.get('splits_pass', True) and entry.get('visible_seat', {}).get('pass', True) and entry.get('hero_coverage', {}).get('pass', True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prop', choices=['sofa', 'dress_uniform'], required=True)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--reexport', type=Path, required=True)
    parser.add_argument('--collisions', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    record = verify(args.prop, args.input, args.reexport, args.collisions)
    args.report.write_text(json.dumps(record, indent=2, default=lambda v: v.item()) + '\n')
    print(json.dumps({k: v for k, v in record.items() if k != 'shared'}, indent=2, default=lambda v: v.item()))
    if not record['pass']:
        raise SystemExit(1)
