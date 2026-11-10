"""Manufactured conduit ends and conductor terminals at folded-box ports."""
import numpy as np

from stasis_wiring_assemblies import annulus, sweep
from stasis_wiring_transition import stations


def box_interval(a, b, bounds):
    delta = b-a
    lo, hi = 0., 1.
    for axis in range(3):
        if abs(delta[axis]) < 1e-12:
            if not bounds[0, axis] <= a[axis] <= bounds[1, axis]:
                return None
        else:
            ends = sorted((bounds[:, axis]-a[axis])/delta[axis])
            lo, hi = max(lo, ends[0]), min(hi, ends[1])
    return (lo, hi) if hi > lo else None


def port_sections(path, junctions):
    """Return exterior station intervals and the actual box crossing intervals."""
    d = stations(path)
    crossings = []
    for junction in junctions:
        bounds = np.array(junction['bounds_m'])
        hits = []
        for i, (a, b) in enumerate(zip(path, path[1:])):
            hit = box_interval(a, b, bounds)
            if hit is not None:
                hits.append(d[i]+np.array(hit)*(d[i+1]-d[i]))
        if hits:
            crossings.append((float(min(h[0] for h in hits)), float(max(h[1] for h in hits)), junction))
    crossings.sort(key=lambda row: row[0])
    sections, cursor = [], 0.
    for lo, hi, _ in crossings:
        if lo < cursor-1e-8:
            raise ValueError('overlapping manufactured junctions')
        if lo > cursor+1e-8:
            sections.append((cursor, lo))
        cursor = hi
    if cursor < d[-1]-1e-8:
        sections.append((cursor, float(d[-1])))
    return sections, crossings


def slice_path(path, lo, hi, vectors=None):
    d = stations(path)
    samples = np.r_[lo, d[(d > lo+1e-9) & (d < hi-1e-9)], hi]
    values = path if vectors is None else vectors
    return np.column_stack([np.interp(samples, d, values[:, axis]) for axis in range(3)])


def section_meshes(path, sections, inner, outer, n, b):
    return [annulus(slice_path(path, lo, hi), inner, outer,
                    slice_path(path, lo, hi, n), slice_path(path, lo, hi, b))[0]
            for lo, hi in sections]


def terminated_jackets(assembly, name, path, offsets, sections, crossings, n, b, power):
    import trimesh
    for number, offset in enumerate(offsets):
        strand = path+offset
        radius = .012 if power else .003
        assembly.route(f'{name}-{number+1}', strand, radius, .144 if power else .048,
                       n if not power else None, b if not power else None)
        pieces = [sweep(slice_path(path, lo, hi)+slice_path(path, lo, hi, offset), radius,
                        slice_path(path, lo, hi, n), slice_path(path, lo, hi, b))[0]
                  for lo, hi in sections]
        assembly.parts['jacket'][-1] = trimesh.util.concatenate(pieces)
        route = assembly.routes[-1]
        route['actual_mesh_bounds_m'] = assembly.parts['jacket'][-1].bounds.tolist()
        route['physical_sections_m'] = [slice_path(path, lo, hi, strand).tolist() for lo, hi in sections]
        for lo, hi, junction in crossings:
            center = np.array(junction['center_m'])
            for station in (lo, hi):
                port = slice_path(path, station, station, strand)[0]
                # Fan the compact six-wire ring into ordered terminal levels.
                # Sorting by incoming height prevents crossed bare conductors;
                # the route record retains the explicit port-to-terminal map.
                terminal = number
                if not power:
                    ports = [slice_path(path,station,station,path+v)[0] for v in offsets]
                    order = sorted(range(len(ports)),key=lambda i:(round(ports[i][1],8),round(ports[i][0],8),round(ports[i][2],8)))
                    terminal = order.index(number)
                hub = center+np.array([0., (terminal-(len(offsets)-1)/2)*.006, 0.])
                # Only boundary ports exist when an axis terminates inside a box.
                if np.max(abs(port-center)/(np.array(junction['size_m'])/2)) < .99:
                    continue
                wire_radius = .0016 if power else .0007
                link = np.array([port, hub])
                assembly.add('copper', sweep(link, wire_radius)[0])
                assembly.metrics.setdefault('junction_links', []).append({
                    'junction':junction['id'], 'route':route['id'], 'strand':terminal+1, 'port_strand':number+1,
                    'port_m':port.tolist(), 'hub_m':hub.tolist(), 'radius_m':wire_radius})
    return crossings
