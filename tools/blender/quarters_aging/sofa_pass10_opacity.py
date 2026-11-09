"""Surface-space torn edges without the old straight 3 mm erosion cutoff."""
from pathlib import Path

import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree

from bake_down import boundary_samples, boundary_segments
from common import surface_tree
from fringe_cards import image_from_array
from opacity_bake import value_noise


def torn_coverage(points, distances, roots, seed, opening=None):
    noise = .25*value_noise(roots, .004, seed)+.75*value_noise(roots, .0016, seed+1)
    opaque = distances >= .0045+.0054*noise
    if opening is not None:
        delta = points-opening['centre']
        u = np.einsum('ij,j->i', delta, opening['tangent'])
        v = np.einsum('ij,j->i', delta, opening['across'])
        along = u/.045
        taper = np.sqrt(np.maximum(0., 1-along*along))
        width = (.010+.004*np.sin(along*8+seed)+.003*np.sin(along*19))*taper
        rag = .0025*value_noise(points, .0022, seed+13)
        hole = (np.abs(along) < 1.) & (np.abs(v) < width+rag)
        opaque &= ~hole
    return opaque


def opening_for(obj):
    if not (obj.name.startswith('Back') or obj.name.startswith('Throw')):
        return None
    centre = Vector((obj.matrix_world.translation.x-.05, .18, .57))
    if obj.name.startswith('Throw'):
        centre = sum((obj.matrix_world@v.co for v in obj.data.vertices), Vector())/len(obj.data.vertices)
    direction = Vector((-.18, -.50, .28)).normalized()
    hit, normal, _, _ = surface_tree(obj).ray_cast(centre+direction*.6, -direction)
    if hit is None:
        raise ValueError(f'{obj.name}: close-camera ray misses cloth for the stress opening')
    # Project both plies through the same opening rather than exposing another
    # intact cover directly behind a nominal tear in the front ply.
    tangent = Vector((0, 0, 1)) if obj.name.startswith('Throw') else Vector((1, 0, 0))
    tangent = (tangent-direction*tangent.dot(direction)).normalized()
    across = direction.cross(tangent).normalized()
    return {'centre': np.array(hit), 'tangent': np.array(tangent), 'across': np.array(across)}


def opacity(obj, out, seed, size=2048):
    samples = boundary_samples(boundary_segments(obj), .00025)
    tree = KDTree(len(samples))
    for index, p in enumerate(samples):
        tree.insert(p, index)
    tree.balance()
    positions = np.array([obj.matrix_world@v.co for v in obj.data.vertices])
    opening = opening_for(obj)
    obj.data.calc_loop_triangles()
    uv = obj.data.uv_layers['BakeUV'].data
    mask = np.ones((size, size), dtype=np.float32)
    for triangle in obj.data.loop_triangles:
        tex = np.array([uv[i].uv[:] for i in triangle.loops])*size
        low = np.maximum(0, np.floor(tex.min(0)).astype(int))
        high = np.minimum(size-1, np.ceil(tex.max(0)).astype(int))
        if np.any(high < low):
            continue
        x, y = np.meshgrid(np.arange(low[0], high[0]+1)+.5, np.arange(low[1], high[1]+1)+.5)
        a, b, c = tex
        det = (b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(det) < 1e-12:
            continue
        u = ((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/det
        v = ((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/det
        w = 1-u-v
        inside = (u >= 0) & (v >= 0) & (w >= 0)
        if not inside.any():
            continue
        p = np.einsum('ij,jk->ik', np.stack([u[inside], v[inside], w[inside]], axis=1),
                      positions[list(triangle.vertices)])
        nearest = [tree.find(point) for point in p]
        roots = np.array([q[0] for q in nearest])
        distances = np.array([q[2] for q in nearest])
        tile = mask[low[1]:high[1]+1, low[0]:high[0]+1]
        tile[inside] = torn_coverage(p, distances, roots, seed, opening)
    rgba = np.ones((size, size, 4), dtype=np.float32)
    rgba[:, :, :3] = mask[:, :, None]
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    image = image_from_array(obj.name+'_Pass10Opacity', rgba, out, noncolor=True)
    report = {'path': str(out), 'size': size, 'transparent_texels': int((mask < .5).sum()),
              'method': 'nearest-lip noise field; no straight erosion cap or isolated pinholes',
              'opening': {key: value.tolist() for key, value in opening.items()} if opening else None}
    return image, report
