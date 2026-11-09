"""Physical boundary stations shared by the tunic's sheet and connected allowance."""
import numpy as np


def chain_stations(points):
    points = np.asarray(points)
    return np.r_[0., np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]


def erosion_depth(stations, seed):
    from opacity_bake import value_noise
    stations = np.asarray(stations)
    coordinates = np.column_stack([stations, np.zeros((len(stations), 2))])
    noise = sum(weight*value_noise(coordinates, wavelength, seed+octave)
                for octave, (weight, wavelength) in enumerate(zip(
                    [.48, .27, .16, .09], [.0038, .0019, .00095, .00048])))
    return np.clip(.0027+.0068*noise, .00015, .006)


def labelled_station_samples(obj, spacing=.0002):
    import bmesh
    from tear_boundaries import release_weights
    weights = release_weights(obj)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.index_update()
    remaining = {edge for edge in bm.edges if edge.is_boundary}
    points, erodible, stations = [], [], []
    component = 0
    lengths = []
    while remaining:
        degree = {}
        for edge in remaining:
            for vertex in edge.verts:
                degree[vertex] = degree.get(vertex, 0)+1
        current = min([v for v in degree if degree[v] == 1] or list(degree), key=lambda v: v.index)
        station = 0.
        while True:
            edge = next((e for e in sorted(current.link_edges, key=lambda e: e.index) if e in remaining), None)
            if edge is None:
                break
            remaining.remove(edge)
            following = edge.other_vert(current)
            a, b = [obj.matrix_world @ v.co for v in [current, following]]
            length = (b-a).length
            allowed = min(a.z, b.z) < -.24 or all(weights[v.index] >= .5 for v in edge.verts)
            count = max(1, int(np.ceil(length/spacing)))
            for t in np.linspace(0., 1., count+1):
                points.append(a.lerp(b, float(t)))
                erodible.append(allowed)
                stations.append(station+t*length+component*1.731)
            station += length
            current = following
        lengths.append(station)
        component += 1
    bm.free()
    return points, np.array(erodible, bool), np.array(stations), lengths
