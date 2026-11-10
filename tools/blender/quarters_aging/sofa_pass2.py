"""Gravity-shaped, split cushion sacks and a continuous throw over the arm."""
import math

import bpy
import numpy as np
from mathutils import Vector

from common import recalc
from fabric_mesh import fray, grid, join, material, new_object, replace, shell, thicken, volume


def seat_point(cx, u, v, seed):
    x = .318 * u * (1 - .045 * abs(v) ** 8)
    y = -.105 + .265 * v * (1 - .045 * abs(u) ** 8)
    z = .462 + .050 * (u ** 4 + v ** 4) / 2
    z += .011 * math.sin(12 * u + 4 * v + seed) * math.sin(8 * v - 2 * u) * (1 - .45 * abs(u * v))
    z -= .008 * math.exp(-((u - .30) / .22) ** 2) * (1 - v * v)
    return (cx + x, y, z)


def seat(obj, seed):
    original_volume = volume(obj)
    cx = obj.matrix_world.translation.x
    rng = np.random.default_rng(seed)
    jitter = rng.uniform(-.0055, .0055, (21, 21, 2))
    def point(s, t, i, j):
        u, v = 2 * s - 1, 2 * t - 1
        if 11 <= i <= 17 and j in (12, 13):
            v += .010 if j == 12 else -.010
        if 0 < i < 20 and 0 < j < 20:
            u += jitter[j, i, 0] / .318
            v += jitter[j, i, 1] / .265
        return seat_point(cx, u, v, seed)
    def bottom(p, t):
        return (p[0], p[1], p[2] * (1 - t) + .3912 * t)
    cuts = lambda i, j: (5 <= i <= 8 and j == 3) or (12 <= i <= 15 and j == 12)
    vertices, faces = shell(20, 20, point, bottom, cuts)
    replace(obj, vertices, faces, material('CharcoalUpholstery', (.055, .060, .066)))
    fibre_count = fray(obj, seed, probability=.55, length=(.0015, .004), region=lambda p: p.y < -.15)
    thicken(obj, .00012, 'CoverInside', 'CoverSplitSection')
    cover_volume = volume(obj)
    # Match the remaining filling volume by reducing footprint, not by moving the visible top.
    scale = .90
    def core_point(s, t, i, j):
        p = seat_point(cx, (2 * s - 1) * scale, (2 * t - 1) * scale, seed)
        return (p[0], p[1], p[2] - .008)
    def core_bottom(p, t):
        return (p[0], p[1], p[2] * (1 - t) + .3922 * t)
    cv, cf = shell(14, 14, core_point, core_bottom)
    core = new_object(obj.name + '_Crust', cv, cf, material('Foam', (.16, .065, .022)))
    desired = original_volume * .255 - cover_volume
    ratio = desired / volume(core)
    for vtx in core.data.vertices:
        vtx.co.x = cx + (vtx.co.x - cx) * ratio
    recalc(core)
    join(obj, [core])
    return {'method': 'Zero-pressure height-field drape with retained seam edges, settled inner crust and bounded tears; no cloth simulation claimed.',
            'original_volume_m3': original_volume, 'target_volume_ratio': .255, 'cover_volume_m3': cover_volume,
            'frays': fibre_count, 'split_cells': [[5, 8, 3], [12, 15, 12]], 'crust_width_fit': ratio}


def back_front(cx, u, v, seed):
    x = .316 * u * (1 - .045 * abs(2 * v - 1) ** 6)
    z = .418 + .355 * v - .020 * (1 - u * u) * v ** 5
    # Keep the empty upper sack above the arm; only the filling settles into the bottom.
    z += .060 * max(0, (v - .5) / .5) ** 2
    z += .004 * math.sin(13 * u + seed) * math.sin(math.pi * v)
    depth = .160 * (1 - v) ** 3 + .018
    centre = .300 - .040 * v ** 3
    wave = .007 * math.sin(18 * u + 9 * v + seed) * math.sin(math.pi * v)
    return np.array((cx + x, centre - depth / 2 + wave, z)), depth


def back(obj, seed):
    original_volume = volume(obj)
    cx = obj.matrix_world.translation.x
    rng = np.random.default_rng(seed)
    jitter = rng.uniform(-.003, .003, (25, 21))
    def point(s, t, i, j):
        p, _ = back_front(cx, 2 * s - 1, t, seed)
        if 0 < i < 20 and 0 < j < 24:
            p[2] += jitter[j, i]
        return p
    def rear(p, t):
        v = np.clip((p[2] - .418) / .355, 0, 1)
        return (p[0], (1 - t) * p[1] + t * (.300 - .040 * v ** 3 + (.160 * (1 - v) ** 3 + .018) / 2), p[2])
    cuts = lambda i, j: (4 <= i <= 7 and j == 7) or (12 <= i <= 15 and j == 16)
    vertices, faces = shell(20, 24, point, rear, cuts)
    replace(obj, vertices, faces, material('CharcoalUpholstery', (.055, .060, .066)))
    frays = fray(obj, seed, probability=.5, length=(.001, .003))
    thicken(obj, .00010, 'CoverInside', 'CoverSplitSection')
    cover_volume = volume(obj)
    def core_point(s, t, i, j):
        p, _ = back_front(cx, (2 * s - 1) * .90, .015 + .51 * t, seed)
        p[1] += .010
        return p
    def core_rear(p, t):
        v = np.clip((p[2] - .418) / .355, 0, 1)
        rear_y = .300 - .040 * v ** 3 + (.160 * (1 - v) ** 3 + .018) / 2 - .010
        return (p[0], (1 - t) * p[1] + t * rear_y, p[2])
    cv, cf = shell(14, 12, core_point, core_rear)
    core = new_object(obj.name + '_Crust', cv, cf, material('Foam', (.16, .065, .022)))
    ratio = (original_volume * .255 - cover_volume) / volume(core)
    for vertex in core.data.vertices:
        vertex.co.x = cx + (vertex.co.x - cx) * ratio
    recalc(core)
    join(obj, [core])
    return {'method': 'Settled lower filling; upper empty sack folds forward without lowering its bottom.',
            'original_volume_m3': original_volume, 'target_volume_ratio': .255, 'cover_volume_m3': cover_volume,
            'frays': frays, 'crust_width_fit': ratio, 'crust_top_m': .604}


def throw(obj, seed):
    # Arclength follows the cap, rounds its outer edge, then falls outside the arm.
    knots = np.array([[.970, .817], [1.035, .820], [1.096, .819], [1.126, .800],
                      [1.142, .756], [1.150, .600], [1.160, .400], [1.174, .200],
                      [1.194, .050], [1.225, .010], [1.290, .003]])
    lengths = np.r_[0, np.cumsum(np.linalg.norm(np.diff(knots, axis=0), axis=1))]
    lengths /= lengths[-1]
    def point(s, t, i, j):
        x = np.interp(t, lengths, knots[:, 0])
        z = np.interp(t, lengths, knots[:, 1])
        y = -.240 + .490 * s
        envelope = math.sin(math.pi * s) * math.sin(math.pi * t)
        x += .008 * math.sin(19 * s + 3 * t) * envelope
        y += .006 * math.sin(8 * t + 4 * s) * envelope
        z += .003 * math.sin(23 * s + t) * envelope
        return (x, y, z)
    cuts = lambda i, j: (4 <= i <= 6 and 10 <= j <= 12 and (i, j) != (4, 10)) or (10 <= i <= 11 and 20 <= j <= 24 and (i, j) != (11, 20))
    vertices, faces = grid(16, 32, point, cuts)
    replace(obj, vertices, faces, material('OatmealWool', (.56, .48, .35)))
    frays = fray(obj, seed, probability=.65, length=(.003, .012))
    thicken(obj, .00018, 'ThrowInside', 'ThrowFraySection')
    def scrap_point(s, t, i, j):
        return (1.27 + .16 * s, -.43 + .16 * t, .0013 + .005 * math.sin(math.pi * s) ** 2 * math.sin(math.pi * t) ** 2)
    sv, sf = grid(7, 7, scrap_point, lambda i, j: (i == 0 and j < 2) or (i == 6 and j > 3) or (i == 4 and j == 4))
    scrap = new_object('ThrowDetachedPiece', sv, sf, obj.data.materials[0])
    fray(scrap, seed + 1, length=(.003, .008))
    thicken(scrap, .00018, 'ThrowInside', 'ThrowFraySection')
    return {'method': 'Continuous cap-to-floor gravity drape, outside the arm collision envelope, with a separate torn floor remnant.',
            'frays': frays, 'arm_cap_z_m': .8075}


def crumbs(seed):
    rng = np.random.default_rng(seed)
    vertices, faces = [], []
    # Drop each piece vertically onto the deck or the cushion. Cells keep pieces apart.
    for cx in [-.67, 0, .67]:
        for k in range(64):
            i, j = k % 16, k // 16
            x = cx - .24 + i * .030 + rng.uniform(-.003, .003)
            y = -.427 + j * .0115 + rng.uniform(-.001, .001)
            size = rng.uniform(.0025, .008)
            z = .3869
            n = len(vertices)
            # A rough, low-poly solid, never a zero-thickness scrap.
            vertices += [(x - size / 2, y - size / 3, z), (x + size / 2, y - size / 3, z),
                         (x + size * .35, y + size / 3, z), (x - size * .40, y + size / 3, z),
                         (x - size * .1, y, z + size * .65)]
            faces += [(n, n + 3, n + 2, n + 1), (n, n + 1, n + 4), (n + 1, n + 2, n + 4),
                      (n + 2, n + 3, n + 4), (n + 3, n, n + 4)]
    return new_object('FoamDebris', vertices, faces, material('Foam', (.16, .065, .022)))


def floor_spill(seed):
    rng = np.random.default_rng(seed)
    vertices, faces = [], []
    for cx in [-.67, 0, .67]:
        for k in range(12):
            x = cx + (k % 4 - 1.5) * .018
            y = -.46 + (k // 4 - 1) * .018
            r = rng.uniform(.0012, .0025)
            n = len(vertices)
            vertices += [(x - r, y - r, .0002), (x + r, y - r, .0002), (x, y + r, .0002), (x + .2 * r, y, .0002 + 1.3 * r)]
            faces += [(n, n + 2, n + 1), (n, n + 1, n + 3), (n + 1, n + 2, n + 3), (n + 2, n, n + 3)]
    new_object('FoamFloorDebris', vertices, faces, material('Foam', (.16, .065, .022)))
    return {'pieces': 36, 'floor_gap_m': .0002}


def build(seed):
    record = {}
    for i, side in enumerate(['L', 'C', 'R']):
        record['SeatCushion_' + side] = seat(bpy.data.objects['SeatCushion_' + side], seed + 11 * i)
        record['BackCushion_' + side] = back(bpy.data.objects['BackCushion_' + side], seed + 17 * i)
    record['Throw'] = throw(bpy.data.objects['Throw'], seed + 300)
    crumbs(seed + 400)
    record['floor_spill'] = floor_spill(seed + 401)
    return record
