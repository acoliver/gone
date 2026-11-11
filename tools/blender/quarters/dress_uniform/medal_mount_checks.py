"""Independent preserved-upper-ribbon checks for the #130 lower-fold edit."""
import numpy as np


def upper_ribbon_samples(obj, frame):
    origin, basis = np.array(frame['origin']), np.array(frame['frame'])
    values = []
    for face in obj.data.polygons:
        if obj.data.materials[face.material_index].name != 'RibbonFabric': continue
        for index in face.loop_indices:
            i = obj.data.loops[index].vertex_index
            p = np.array(obj.matrix_world @ obj.data.vertices[i].co)
            # Original second row begins at 23.2 mm in both saved poses.
            if np.dot(p-origin, basis[2]) < .0232: continue
            values.append(np.r_[p, *[obj.data.uv_layers[name].data[index].uv[:] for name in ['DetailUV','BakeUV']],
                                obj.data.color_attributes['RibbonColours'].data[index].color[:]])
    return np.unique(np.array(values), axis=0)


def assert_upper_preserved(expected, obj, frame):
    current = upper_ribbon_samples(obj, frame)
    # New collinear row-edge vertices do not replace any saved upper sample.
    for sample in expected:
        assert np.any(np.all(current == sample, axis=1)), ('Upper sewn ribbon/UV/colour changed', sample)
    return len(expected)
