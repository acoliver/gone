"""Independent material preservation and finite-surface attachment measurements."""
import copy
import hashlib

import numpy as np
import trimesh


def material_signature(document, raw, binary, material):
    result = copy.deepcopy(material)

    def resolve(value):
        for name, item in value.items():
            if isinstance(item, dict):
                if name.endswith('Texture') and 'index' in item:
                    texture = document['textures'][item['index']]
                    image = document['images'][texture['source']]
                    view = document['bufferViews'][image['bufferView']]
                    start = binary + view.get('byteOffset', 0)
                    item['index'] = dict(image_sha256=hashlib.sha256(raw[start:start + view['byteLength']]).hexdigest(),
                                         sampler=document['samplers'][texture['sampler']] if 'sampler' in texture else None)
                resolve(item)
    resolve(result)
    return result


def separation(a, b):
    """Exact disjoint triangle distance: vertex/face and interior edge/edge minima."""
    distances = [trimesh.proximity.closest_point_naive(b, a.vertices)[1].min(),
                 trimesh.proximity.closest_point_naive(a, b.vertices)[1].min()]
    segments = b.vertices[b.edges_unique]
    direction = segments[:, 1] - segments[:, 0]
    cc = np.einsum('ij,ij->i', direction, direction)
    for start, end in a.vertices[a.edges_unique]:
        delta, offset = end - start, start - segments[:, 0]
        aa = delta @ delta
        bb = direction @ delta
        dd = offset @ delta
        ee = np.einsum('ij,ij->i', direction, offset)
        determinant = aa * cc - bb ** 2
        s = np.divide(bb * ee - cc * dd, determinant, out=np.zeros_like(bb), where=determinant > 1e-24)
        t = np.divide(aa * ee - bb * dd, determinant, out=np.zeros_like(bb), where=determinant > 1e-24)
        inside = (determinant > 1e-24) & (s > 0) & (s < 1) & (t > 0) & (t < 1)
        if inside.any():
            vector = offset[inside] + s[inside, None] * delta - t[inside, None] * direction[inside]
            distances.append(np.linalg.norm(vector, axis=1).min())
    return float(min(distances))


def medal_metrics(mesh):
    welded = mesh.copy()
    welded.merge_vertices(merge_tex=True, merge_norm=True)
    pieces = welded.split(only_watertight=False)
    assert len(pieces) == 2, 'Export must retain connected metal and the unchanged ribbon'
    metal, ribbon = sorted(pieces, key=lambda part: -part.extents[0])
    assert metal.is_watertight and metal.is_winding_consistent and metal.volume > 0
    clearance = separation(metal, ribbon)
    assert clearance >= .00008 - 1e-8, 'Exported metal/ribbon clearance must retain the authored 80 micrometres'
    return dict(metal_triangles=len(metal.faces), ribbon_triangles=len(ribbon.faces),
                metal_watertight=True, metal_winding_consistent=True,
                actual_metal_ribbon_clearance_m=clearance)
