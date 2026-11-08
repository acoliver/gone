"""Export-space checks for the sofa's support, rounded upholstery and wool folds."""
import json
import struct
import numpy as np
import trimesh
from scipy.signal import find_peaks
from scipy.optimize import least_squares


def mesh_names(path):
    data = path.read_bytes()
    length = struct.unpack_from('<I', data, 12)[0]
    document = json.loads(data[20:20 + length])
    pairs = {node['name']: document['meshes'][node['mesh']]['name']
             for node in document['nodes'] if 'mesh' in node}
    return {'node_mesh_names': pairs, 'pass': all(a == b for a, b in pairs.items())}


def foot_contacts(feet, frame):
    records = []
    for part in sorted(feet.split(), key=lambda p: tuple(p.centroid)):
        top = part.bounds[1, 1]
        samples = part.vertices[part.vertices[:, 1] > top - .00001]
        samples = np.vstack((samples, samples.mean(axis=0)))
        nearest, distance, _ = trimesh.proximity.closest_point(frame, samples)
        # A side wall is not a mounting surface above a foot.
        above = np.all(nearest[:, 1] >= samples[:, 1] - .00001)
        records.append({'top_y_m': float(top), 'nearest_frame_gaps_m': distance.tolist(),
                        'surface_above_foot': bool(above),
                        'pass': bool(above and distance.max() <= .001)})
    return {'feet': records, 'pass': len(records) == 4 and all(r['pass'] for r in records)}


def edge_rounding(body):
    lo, hi = body.bounds
    center = (lo + hi) / 2
    radii = []
    convex = []
    for axis in (0, 2):
        for sign in (-1, 1):
            points = []
            for inset in (.012, .025, .040, .055, .075):
                p = center.copy()
                p[axis] = lo[axis] + inset if sign < 0 else hi[axis] - inset
                p[1] = hi[1] + 1
                hits, _, _ = body.ray.intersects_location([p], [[0, -1, 0]], multiple_hits=True)
                if not len(hits):
                    return {'pass': False, 'reason': 'Rounded edge section missed the shell'}
                points.append([inset, float(hits[:, 1].max())])
            q = np.array(points)
            # Fit a circle to the top-to-side transition in each central section.
            a = np.column_stack((2*q, np.ones(len(q))))
            cx, cy, constant = np.linalg.lstsq(a, (q*q).sum(axis=1), rcond=None)[0]
            radii.append(float(np.sqrt(constant + cx*cx + cy*cy)))
            slopes = np.diff(q[:, 1]) / np.diff(q[:, 0])
            convex.append(bool(np.all(np.diff(slopes) <= .20)))
    # Sample diagonally into every top corner. A pinched corner produces a
    # depression or a reversed slope on the way from the seam to the crown.
    corners = []
    for sx in (-1, 1):
        for sz in (-1, 1):
            heights = []
            for inset in (.035, .055, .080, .110):
                x = lo[0]+inset if sx < 0 else hi[0]-inset
                z = lo[2]+inset if sz < 0 else hi[2]-inset
                hits, _, _ = body.ray.intersects_location([[x, hi[1]+1, z]], [[0,-1,0]], multiple_hits=True)
                heights.append(float(hits[:,1].max()) if len(hits) else float('nan'))
            corners.append({'heights_y_m': heights, 'pass': bool(np.all(np.isfinite(heights)) and np.all(np.diff(heights) >= -.001))})
    return {'top_edge_radii_m': radii, 'convex_sections': convex, 'corners': corners,
            'pass': min(radii) >= .035 and all(convex) and all(c['pass'] for c in corners)}


def back_shape(body):
    lo, hi = body.bounds
    x = (lo[0]+hi[0])/2
    y = lo[1] + (hi[1]-lo[1])*.64
    def front(px):
        hits, _, _ = body.ray.intersects_location([[px,y,hi[2]+1]], [[0,0,-1]], multiple_hits=True)
        return float(hits[:,2].max())
    edges = [front(lo[0]+.020), front(hi[0]-.020)]
    crown = front(x) - float(np.mean(edges))
    # Treat the front as an up-facing shell to measure the soft top transition.
    rotated = body.copy()
    rotated.vertices = body.vertices[:, [0,2,1]]
    rounding = edge_rounding(rotated)
    return {'extents_xyz_m': body.extents.tolist(), 'front_crown_m': crown,
            'top_edge_radii_m': rounding.get('top_edge_radii_m', []),
            'pass': bool(abs(body.extents[0]-.66)<.01 and abs(body.extents[1]-.42)<.01
                         and .040 <= crown <= .060
                         and len(rounding.get('top_edge_radii_m', [])) == 4
                         and min(rounding['top_edge_radii_m'][i] for i in (0,1,3)) >= .035)}


def throw_folds(throw, seat):
    # The outermost hit at each station selects one face of the thick sheet.
    stations = np.linspace(throw.bounds[0,2]+.030, throw.bounds[1,2]-.030, 181)
    y = .56
    origins = np.column_stack((np.full(len(stations), 2.), np.full(len(stations), y), stations))
    hits, rays, _ = throw.ray.intersects_location(origins, np.tile([-1,0,0], (len(stations),1)), multiple_hits=True)
    samples = []
    for i, z in enumerate(stations):
        x = hits[rays == i, 0]
        x = x[x > 1.10]
        if len(x):
            samples.append([z, x.max()])
    q = np.array(samples)
    coefficients = np.polyfit(q[:,0], q[:,1], 1)
    residual = q[:,1] - np.polyval(coefficients, q[:,0])
    peaks, _ = find_peaks(residual, prominence=.006, distance=12)
    deviation = float(np.abs(residual).max())
    # Orthographic top-area coverage, sampled only where a ray hits the right
    # cushion first, measures the actual cushion footprint rather than its box.
    lo, hi = seat.bounds
    xs = np.linspace(lo[0]+.001, hi[0]-.001, 100)
    zs = np.linspace(lo[2]+.001, hi[2]-.001, 104)
    xx, zz = np.meshgrid(xs, zs)
    origins = np.column_stack((xx.ravel(), np.full(xx.size, 2.), zz.ravel()))
    directions = np.tile([0,-1,0], (len(origins),1))
    cushion_hits, cushion_rays, _ = seat.ray.intersects_location(origins, directions, multiple_hits=True)
    throw_hits, throw_rays, _ = throw.ray.intersects_location(origins, directions, multiple_hits=True)
    cushion_top = np.full(len(origins), -np.inf)
    throw_top = np.full(len(origins), -np.inf)
    np.maximum.at(cushion_top, cushion_rays, cushion_hits[:,1])
    np.maximum.at(throw_top, throw_rays, throw_hits[:,1])
    valid = np.isfinite(cushion_top)
    coverage = float(np.count_nonzero(valid & (throw_top > cushion_top)) / valid.sum())
    # A continuous single sheet cannot expose a second free ply at the arm.
    components = len(throw.split())
    return {'section_y_m': y, 'section_z_range_m': [float(stations[0]),float(stations[-1])], 'section_samples': len(q), 'best_fit_plane_deviation_m': deviation,
            'fold_peak_count': len(peaks), 'fold_peak_z_m': q[peaks,0].tolist(),
            'right_seat_top_coverage_fraction': coverage, 'sheet_components': components,
            'pass': bool(deviation >= .015 and len(peaks) >= 3 and coverage <= .30 and components == 1)}


def rivet_shape(rivets):
    records = []
    plates = {}
    for part in rivets.split():
        lo, hi = part.bounds
        diameter = float(max((hi-lo)[1:]))
        dome = float((hi-lo)[0])
        key = ('R' if part.centroid[0] > 0 else 'L') + ('F' if part.centroid[2] > 0 else 'B')
        plates[key] = plates.get(key, 0) + 1
        records.append({'plate': key, 'diameter_m': diameter, 'dome_height_m': dome,
                        'pass': bool(.010 <= diameter <= .0121 and .002 <= dome <= .004)})
    return {'rivets': records, 'counts_per_plate': plates,
            'pass': len(plates) == 4 and all(4 <= c <= 6 for c in plates.values()) and all(r['pass'] for r in records)}


def arm_roll(throw):
    sections = []
    for depth in (0.,.1,.2):
        section = throw.section(plane_origin=[0,0,depth],plane_normal=[0,0,1])
        q = section.vertices
        q = q[(q[:,0]>=1.074)&(q[:,0]<=1.12)&(q[:,1]>=.775)][:,:2]
        a = np.column_stack((2*q,np.ones(len(q))))
        cx,cy,k = np.linalg.lstsq(a,(q*q).sum(axis=1),rcond=None)[0]
        radius = float(np.sqrt(k+cx*cx+cy*cy))
        # Geometric residuals avoid the radius bias of an algebraic circle fit
        # to a short arc containing both skins of a thick sheet.
        fit = least_squares(lambda p: np.linalg.norm(q-p[:2],axis=1)-p[2], [cx,cy,radius])
        radius = float(fit.x[2])
        error = float(np.abs(fit.fun).max())
        sections.append({'z_m':depth,'samples':len(q),'radius_m':radius,'max_radial_error_m':error,
                         'pass':bool(len(q)>=12 and radius>=.025 and error<=.003)})
    return {'sections':sections,'pass':all(s['pass'] for s in sections)}
