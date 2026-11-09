"""Keep sofa thresholds while tracing the exported visible gash outlines."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sofa_decay_policy import ORDER
from sofa_pass8_accept import project
from sofa_pass9_accept import measure as previous_measure
from sofa_pass11_metrics import cloth_coverage, visible_gashes, fringe_visibility


def connected_segments(segments):
    endpoints = {}
    for index, segment in enumerate(segments):
        for point in segment:
            endpoints.setdefault(tuple(np.round(point, 6)), set()).add(index)
    remaining = set(range(len(segments)))
    while remaining:
        start = remaining.pop()
        component, pending = {start}, [start]
        while pending:
            for point in segments[pending.pop()]:
                for index in endpoints[tuple(np.round(point, 6))] & remaining:
                    remaining.remove(index)
                    component.add(index)
                    pending.append(index)
        yield segments[sorted(component)]


def fragment_gate(path, record):
    from scipy.spatial import cKDTree
    from visible_gates import load
    from verify import clean
    parts, _ = load(path)
    pieces = clean(parts['FoamDebris']).split(only_watertight=False)
    placements = record['debris']['placements']
    centres = np.array([p['centre_blender_m'] for p in placements])
    centres = centres[:, [0, 2, 1]]*np.array([1, 1, -1])
    tree = cKDTree(centres)
    measured, matched = {}, set()
    passed = len(pieces) == len(placements)
    for piece in pieces:
        distance, index = tree.query(piece.centroid)
        template = placements[index]['template']
        points = piece.vertices-piece.vertices.mean(0)
        axes = np.linalg.svd(points, full_matrices=False)[2]
        extents = np.sort(np.ptp(points@axes.T, axis=0))
        ratio = float(extents[0]/extents[-1])
        valid = 14 <= len(piece.faces) <= 40 and len(piece.faces) != 20 and .25 <= ratio <= .7 and distance < .00001
        passed &= valid and int(index) not in matched
        matched.add(int(index))
        measured.setdefault(template, []).append(dict(triangles=len(piece.faces), thickness_width=ratio, **{'pass': bool(valid)}))
    passed &= len(measured) >= 8 and len(matched) == len(placements)
    return dict(templates=measured, used=len(measured), instances=len(pieces),
                method='actual exported connected crumbs, PCA dimensions and area-centroid identity against placements', **{'pass': bool(passed)})


def tear_result(outlines, seam_report):
    result = dict(value=[o['longest_straight_run_px'] for o in outlines], outlines=outlines)
    if seam_report is not None:
        result.update({key: value for key, value in seam_report.items() if key.startswith('seam_')})
    result['pass'] = (bool(outlines) and all(o['longest_straight_run_px'] <= 12 for o in outlines)
                      and (seam_report is None or seam_report['seam_fringe_and_gape_pass']))
    return result


def measure(args):
    result = previous_measure(args)
    images = [np.array(Image.open(args.renders/name).convert('RGB')) for name in
              ['hero-visibility.png', 'sofa-after.png', 'hero-without-fringe.png']]
    fringe = fringe_visibility(*images)
    result['visibility']['fringe'].update(fringe)
    result['invariants']['fringe_visible_in_lit_hero'] = fringe['pass']
    cameras = json.loads((args.renders/'diagnostics/cameras.json').read_text())['parts']
    values = {key: {} for key in ['G3', 'G4', 'G6']}
    for name in [*ORDER, 'Throw']:
        stem = 'throw' if name == 'Throw' else name
        segments = np.load(args.out/(stem+'-gash-seeds.npz'))['segments']
        outlines = []
        components = list(connected_segments(segments))
        for view in ['labels', 'crease-labels'] if name == 'Throw' else ['labels']:
            rgb = np.array(Image.open(args.renders/'diagnostics'/name/(view+'.png')).convert('RGB'))
            cloth = cloth_coverage(rgb)
            occluded = (rgb[:, :, 0] > 180) & (rgb[:, :, 2] > 180)
            for index, component in enumerate(components):
                projected = project(component.reshape(-1, 3), cameras[name][view]).reshape(-1, 2, 2)[:, :, ::-1]
                for outline in visible_gashes(cloth, projected, radius=32., occluded=occluded):
                    outline.update(physical_lip_component=index, camera=view)
                    outlines.append(outline)
        resolved = [o for o in outlines if o['maximum_extent_px'] >= 64]
        seam_report = None if name == 'Throw' else result['gates']['G3']['value'][name]
        values['G3'][name] = tear_result(outlines, seam_report)
        widths = [o['width_cv'] for o in outlines]
        values['G4'][name] = dict(value=widths, **{'pass': bool(widths) and all(w is not None and w >= .35 for w in widths)})
        dimensions = [o['contour_dimension'] for o in resolved]
        values['G6'][name] = dict(value=dimensions, minimum_extent_px=64,
                                  **{'pass': bool(dimensions) and all(1.15 <= d <= 1.40 for d in dimensions)})
    for key, parts in values.items():
        result['gates'][key].update(value=parts, status='measured', **{'pass': all(p['pass'] for p in parts.values())})
        result['gates'][key]['method'] = 'combined antialiased cloth/fringe coverage; actual alpha/lip contours near each physical tear component, no synthetic endpoint closure'
    result['gates']['G1']['method'] = 'first-hit face IDs in the unchanged close and hero cameras'
    record = json.loads((args.out/'simulation.json').read_text())
    fragments = fragment_gate(args.input, record)
    result['gates']['G9'].update(value=fragments, status='measured', **{'pass': fragments['pass']})
    ratios = {name: item['area_ratio_after_cut_and_finish'] for name, item in record['pass11']['parts'].items() if name.startswith('Back')}
    result['back_area_control'] = dict(reference='retained pass-10 cover, before local cutting and finishing', values=ratios, limits=[.97, 1.03])
    result['invariants']['back_area_97_to_103_percent'] = all(.97 <= value <= 1.03 for value in ratios.values())
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
