"""Physical boundary stations shared by the tunic's sheet and connected allowance."""
import numpy as np

WAVELENGTHS_M = (.0022, .0011, .00055, .000275)


def chain_stations(points):
    points = np.asarray(points)
    return np.r_[0., np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]


def erosion_depth(stations, seed):
    from opacity_bake import value_noise
    stations = np.asarray(stations)
    coordinates = np.column_stack([stations, np.zeros((len(stations), 2))])
    noise = sum(weight*value_noise(coordinates, wavelength, seed+octave)
                for octave, (weight, wavelength) in enumerate(zip(
                    [.48, .27, .16, .09], WAVELENGTHS_M)))
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


def refine_physical_lips(obj):
    import bmesh
    from mathutils import Vector
    from mathutils.kdtree import KDTree
    from tear_boundaries import retained_binding
    samples, allowed, stations, _ = labelled_station_samples(obj)
    tree = KDTree(len(samples))
    for index, point in enumerate(samples):
        tree.insert(point, index)
    tree.balance()
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.normal_update()
    deform = bm.verts.layers.deform.active
    patch = obj.vertex_groups['DetailPatch'].index
    movements = {}
    for vertex in bm.verts:
        edges = [edge for edge in vertex.link_edges if edge.is_boundary]
        world = obj.matrix_world @ vertex.co
        if not edges or world.x < .16 or world.z < -.35 or vertex[deform].get(patch, 0.) > .1:
            continue
        hit = tree.find(world)
        if not allowed[hit[1]] or retained_binding(np.array([world]))[0]:
            continue
        directions, limits = [], []
        for edge in edges:
            tangent = (edge.verts[1].co-edge.verts[0].co).normalized()
            middle = (edge.verts[0].co+edge.verts[1].co)/2
            face = edge.link_faces[0]
            inward = face.calc_center_median()-middle
            inward = (inward-tangent*inward.dot(tangent)).normalized()
            directions.append(inward)
            limits.append(max((v.co-middle).dot(inward) for v in face.verts))
        loss = min(float(erosion_depth(np.array([stations[hit[1]]]), 9621)[0])*.11,
                   .10*min(limits), .00045)
        movements[vertex] = sum(directions, Vector()).normalized()*loss
    maximum = max((v.length for v in movements.values()), default=0.)
    for vertex, delta in movements.items():
        vertex.co += delta
    bm.to_mesh(obj.data)
    bm.free()
    from common import recalc
    recalc(obj)
    return dict(vertices=len(movements), maximum_loss_m=maximum,
                parameter='physical arclength; same stations as sheet and allowance opacity',
                protected='fitting supports and retained collar-side binding',
                supporting_face_fraction_limit=.10)
