"""Pass-4 sofa acceptance checks. Unmeasured visual checks never pass."""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[3]
SPECS = {
    'G1': ('visible cloth dihedral >30 degrees', 'covers <=0.08; throw <=0.09'),
    'G2': ('normal-pass interior pixels with >10 degree neighbour change', '<=0.02'),
    'G3': ('alpha-aware opening longest straight run at 0.6 m', '<=12 px / 4.5 mm'),
    'G4': ('opening medial-axis width coefficient of variation', '>=0.35 each opening'),
    'G5': ('lip length lifted >3 mm', '>=0.30'),
    'G6': ('opening contour box-counting dimension at 1..32 px', '1.15..1.40'),
    'G7': ('crust area in coplanar facets >10 cm2', '<=0.05 each residue'),
    'G8': ('20 mm dense crust plane-fit RMS and normal map', '>=0.0015 m and map present'),
    'G9': ('cut-residue fragment templates', '>=8; thickness/width 0.25..0.7; 14..40 triangles; not 20-face icosahedra'),
    'G10': ('floor Clark-Evans R and largest DBSCAN cluster', 'R 0.8..1.4; cluster <=0.20'),
    'G11': ('five-bin spill radial density Spearman rho', '<=-0.6 each source; powder card per spill'),
    'G12': ('seat vertical-wall area relative to unaged', '<=0.25 each seat'),
    'G13': ('seat rounded-box fit RMS', '>=0.012 m each seat'),
    'G14': ('seat centre height above deck relative to unaged', '0.10..0.25 each seat'),
    'G15': ('back top height retained', '0.40..0.65 each back'),
    'G16': ('back residue volume in lowest third', '>=0.60 each back'),
    'G17': ('back horizontal front folds with >=8 mm prominence', '>=2 each back'),
    'G18': ('arm-cap crest split share', '0.60..0.90'),
    'G19': ('fallen throw distance, folds and continuity', '<=0.250 m from arm footprint; >=3 folds >=0.010 m; one arm-to-floor component and <=1 detached remnant'),
    'G30': ('changed-part triangle SAT and unchanged rigid baseline', '0 changed intersections; rigid counts exactly equal unaged'),
    'G31': ('export triangle count', '<=29325 and <=1.5x unaged'),
    'G32': ('decimated/dense open-boundary Hausdorff distance', '<=0.0015 m'),
}


def missing_gates():
    return {key: {'measure': name, 'threshold': threshold, 'value': None,
                  'status': 'not_measured', 'pass': False}
            for key, (name, threshold) in SPECS.items()}


def dihedral_share(mesh):
    return float(np.mean(mesh.face_adjacency_angles > np.radians(30))) if len(mesh.face_adjacency) else 0.


def vertical_area(mesh):
    return float(mesh.area_faces[np.abs(mesh.face_normals[:, 1]) < .35].sum())


def rounded_box_rms(points):
    from scipy.optimize import least_squares
    points = np.asarray(points)
    centre = (points.min(0)+points.max(0))/2
    half = np.maximum(np.ptp(points, axis=0)/2, .002)
    def residual(parameters):
        c, s = np.cos(parameters[6]), np.sin(parameters[6])
        rotation = np.array([[c, 0, -s], [0, 1, 0], [s, 0, c]])
        radius = parameters[7]*parameters[3:6].min()
        q = np.abs((points-parameters[:3])@rotation)-parameters[3:6]+radius
        return np.linalg.norm(np.maximum(q, 0), axis=1)+np.minimum(q.max(1), 0)-radius
    fit = least_squares(residual, [*centre, *half, 0, .1],
                        bounds=([*(centre-half), .0001, .0001, .0001, -np.pi/2, 0],
                                [*(centre+half), *(half*2), np.pi/2, 1]))
    return float(np.sqrt(np.mean(residual(fit.x)**2)))


def volume_below(mesh, height):
    volume = 0.
    for triangle in mesh.triangles:
        polygon = []
        for a, b in zip(triangle, np.roll(triangle, -1, axis=0)):
            inside_a, inside_b = a[1] <= height, b[1] <= height
            if inside_a:
                polygon.append(a)
            if inside_a != inside_b:
                polygon.append(a+(b-a)*(height-a[1])/(b[1]-a[1]))
        for i in range(1, len(polygon)-1):
            a, b, c = polygon[0], polygon[i], polygon[i+1]
            volume += ((a[1]+b[1]+c[1])/3-height)*np.cross(b-a, c-a)[1]/2
    return abs(float(volume))


def cluster_fraction(points, eps=.030, minimum=4):
    """DBSCAN core connectivity with border points, without a sklearn dependency."""
    if not len(points):
        raise ValueError('No floor fragments')
    neighbours = cKDTree(points).query_ball_point(points, eps)
    core = np.array([len(n) >= minimum for n in neighbours])
    labels = np.full(len(points), -1)
    cluster = 0
    for start in np.flatnonzero(core):
        if labels[start] >= 0:
            continue
        labels[start] = cluster
        pending = [int(start)]
        while pending:
            index = pending.pop()
            for other in neighbours[index]:
                if labels[other] < 0:
                    labels[other] = cluster
                    if core[other]:
                        pending.append(other)
        cluster += 1
    return float(max((np.sum(labels == i) for i in range(cluster)), default=0) / len(points))


def measure(path, collisions=None, reexport=None, baseline_collisions=None):
    from visible_gates import load, heights
    from verify import clean, geometry_buffers, pivots
    from scipy.spatial import ConvexHull
    before, old_doc = load(ROOT / 'assets/props/quarters/sofa.glb')
    after, new_doc = load(path)
    gates = missing_gates()

    def measured(key, value, passed):
        gates[key].update(value=value, status='measured', **{'pass': bool(passed)})

    def surface(part, prefix):
        import trimesh
        matches = [m for name, m in part.metadata['raw_primitives'].items() if name.startswith(prefix)]
        if not matches:
            raise ValueError(f'No {prefix} surface in exported part')
        return trimesh.util.concatenate(matches)

    cloth, crust, walls, centres, backs = {}, {}, {}, {}, {}
    box_errors, bottom_volume = {}, {}
    for name in sorted(n for n in before if 'Cushion' in n):
        cover = surface(after[name], 'CharcoalUpholstery')
        residue = clean(surface(after[name], 'Foam'))
        cloth[name] = dihedral_share(clean(cover))
        crust[name] = float(residue.facets_area[residue.facets_area > .001].sum() / residue.area)
        if name.startswith('Seat'):
            walls[name] = vertical_area(cover) / vertical_area(before[name])
            box_errors[name] = rounded_box_rms(cover.vertices)
            cx = before[name].centroid[0]
            x, z = np.meshgrid(np.linspace(cx-.08, cx+.08, 7), np.linspace(.02, .17, 7))
            samples = np.c_[x.ravel(), z.ravel()]
            a, b = heights(before[name], samples), heights(cover, samples)
            valid = np.isfinite(a) & np.isfinite(b)
            centres[name] = float(np.median((b[valid]-.3898)/(a[valid]-.3898))) if valid.any() else None
        else:
            base = before[name].bounds[0, 1]
            backs[name] = float((cover.bounds[1, 1]-base)/(before[name].bounds[1, 1]-base))
            bottom_volume[name] = volume_below(residue, base+before[name].extents[1]/3)/abs(residue.volume)
    cloth['Throw'] = dihedral_share(clean(surface(after['Throw'], 'OatmealWool')))
    measured('G1', cloth, all(v <= (.09 if n == 'Throw' else .08) for n, v in cloth.items()))
    gates['G1']['method'] = 'All-sheet adjacency diagnostic; visible-face measurement remains pending'
    gates['G1']['status'] = 'partial'
    gates['G1']['pass'] = False
    measured('G7', crust, all(v <= .05 for v in crust.values()))
    measured('G12', walls, all(v <= .25 for v in walls.values()))
    measured('G13', box_errors, all(v >= .012 for v in box_errors.values()))
    measured('G14', centres, all(v is not None and .1 <= v <= .25 for v in centres.values()))
    measured('G15', backs, all(.4 <= v <= .65 for v in backs.values()))
    measured('G16', bottom_volume, all(v >= .6 for v in bottom_volume.values()))
    if 'FoamDebris' in after:
        pieces = clean(after['FoamDebris']).split(only_watertight=False)
        floor = np.array([p.centroid[[0, 2]] for p in pieces if p.bounds[0, 1] < .03])
        if len(floor) >= 4:
            area = ConvexHull(floor).volume
            mean = cKDTree(floor).query(floor, k=2)[0][:, 1].mean()
            r = float(mean / (.5 * np.sqrt(area / len(floor))))
            cluster = cluster_fraction(floor)
            measured('G10', {'R': r, 'largest_cluster': cluster, 'count': len(floor)}, .8 <= r <= 1.4 and cluster <= .2)
    count = sum(len(m.faces) for m in after.values())
    old_count = sum(len(m.faces) for m in before.values())
    measured('G31', {'aged': count, 'unaged': old_count, 'ratio': count/old_count}, count <= min(29325, 1.5*old_count))
    if collisions:
        from collision_policy import sofa_contacts
        sat = json.loads(collisions.read_text())
        if baseline_collisions is not None:
            contact = sofa_contacts(sat, json.loads(baseline_collisions.read_text()))
            measured('G30', contact, contact['pass'])
    original = ROOT / 'assets/props/quarters/sofa.glb'
    old, new = geometry_buffers(original), geometry_buffers(path)
    invariants = {'fixed_geometry_bytes': all(old[n] == new[n] for n in ['Frame', 'Feet', 'Rivets']),
                  'origins_and_pivots': all(pivots(new_doc).get(n) == v for n, v in pivots(old_doc).items()),
                  'byte_identical_reexport': reexport is not None and reexport.exists() and reexport.read_bytes() == path.read_bytes()}
    return {'input': str(path), 'gates': gates, 'invariants': invariants,
            'pass': all(g['pass'] for g in gates.values()) and all(invariants.values())}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--report', type=Path, required=True)
    p.add_argument('--collisions', type=Path)
    p.add_argument('--reexport', type=Path)
    p.add_argument('--baseline-collisions', type=Path)
    a = p.parse_args()
    result = measure(a.input, a.collisions, a.reexport, a.baseline_collisions)
    a.report.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['pass'] else 1)
