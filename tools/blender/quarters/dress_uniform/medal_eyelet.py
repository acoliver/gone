"""Fit a compact formed bail to the unchanged sewn ribbon's actual cross-section."""
import bpy
import numpy as np
from mathutils import Vector

from build import activate, mesh, recalc


def union(target, operand):
    activate(target)
    modifier = target.modifiers.new('Joined formed metal', 'BOOLEAN')
    modifier.operation = 'UNION'
    modifier.solver = 'EXACT'
    modifier.object = operand
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(operand, do_unlink=True)
    recalc(target)


def ribbon_envelope(local, faces, z):
    segments = []
    for height in [z - .0002, z, z + .0002]:
        for face in faces:
            cut = []
            for a, b in zip(local[list(face)], np.roll(local[list(face)], -1, axis=0)):
                if (a[2] - height) * (b[2] - height) < 0:
                    cut.append(a + (b - a) * ((height - a[2]) / (b[2] - a[2])))
            if len(cut) == 2:
                segments.append(np.array(cut)[:, :2])
    segments = np.array(segments)
    lo, hi = segments[:, :, 0].min(), segments[:, :, 0].max()
    xs = np.unique(np.round(segments[:, :, 0].ravel(), 8))
    sample_x = np.r_[lo - .0004, xs, hi + .0004]
    backs, fronts = [], []
    for x in sample_x:
        ys = []
        for a, b in segments:
            # Horizontal dilation encloses the complete 0.4 mm threading slab.
            x0, x1 = sorted([a[0], b[0]])
            if x1 - x0 < 1e-9:
                if abs(x - x0) < .00015:
                    ys.extend([a[1], b[1]])
            elif x0 - .0004 <= x <= x1 + .0004:
                for xx in [max(x0, min(x1, x - .00015)), max(x0, min(x1, x + .00015))]:
                    ys.append(a[1] + (b[1] - a[1]) * ((xx - a[0]) / (b[0] - a[0])))
        if not ys:
            raise ValueError('Ribbon cross-section envelope has an unsupported station')
        backs.append(max(ys) + .00008)
        fronts.append(min(ys) - .00008)
    backs, fronts = np.array(backs), np.array(fronts)
    indices = simplified_stations(sample_x, backs, fronts)
    return sample_x[indices], backs[indices] + .000008, fronts[indices] - .000008


def simplified_stations(sample_x, backs, fronts):
    retained = {0, len(sample_x) - 1}
    pending = [(0, len(sample_x) - 1)]
    tolerance = .000008
    while pending:
        a, b = pending.pop()
        if b - a <= 1:
            continue
        fraction = (sample_x[a:b + 1] - sample_x[a]) / (sample_x[b] - sample_x[a])
        error = np.maximum(abs(backs[a:b + 1] - (backs[a] + (backs[b] - backs[a]) * fraction)),
                           abs(fronts[a:b + 1] - (fronts[a] + (fronts[b] - fronts[a]) * fraction)))
        i = a + int(error.argmax())
        if error.max() > tolerance:
            retained.add(i)
            pending.extend([(a, i), (i, b)])
    return sorted(retained)


def fit_eyelet(ribbon, origin, frame, brass, plate, support):
    local = np.array([(ribbon.matrix_world @ v.co) for v in ribbon.data.vertices])
    local = (local - origin) @ frame.T
    bottom = float(local[:, 2].min())
    ribbon.data.calc_loop_triangles()
    faces = [tuple(t.vertices) for t in ribbon.data.loop_triangles]
    normal = -frame[1]
    z = bottom + .003
    rear_z = bottom - .0007
    sample_x, backs, fronts = ribbon_envelope(local, faces, z)
    lo, hi = sample_x[0] + .0004, sample_x[-1] - .0004
    # A tilted return closes below the ribbon, rather than forcing metal into
    # the narrow accepted cloth/ribbon clearance along its entire width.
    original_x, original_front = sample_x, fronts
    sample_x = np.unique(np.r_[sample_x, np.linspace(sample_x[0], sample_x[-1], 129)])
    backs = []
    for x in sample_x:
        levels = []
        for height in [rear_z - .0002, rear_z, rear_z + .0002]:
            point = origin + np.array([x, -.03, height]) @ frame
            hit, _, _, _ = support.ray_cast(Vector(point), Vector(-normal), .06)
            if hit is None:
                raise ValueError('The formed rear return has no wool backing')
            levels.append(((np.array(hit) - origin) @ frame.T)[1])
        backs.append(min(levels) - .0005)
    backs = np.array(backs)
    fronts = np.minimum(np.interp(sample_x, original_x, original_front), backs - .0006)
    indices = simplified_stations(sample_x, backs, fronts)
    sample_x, backs, fronts = sample_x[indices], backs[indices] - .000008, fronts[indices] - .000008
    inner = np.vstack([np.c_[sample_x, backs], np.c_[sample_x[::-1], fronts[::-1]]])
    outer = inner.copy()
    n = len(sample_x)
    outer[:n, 1] += .00012
    outer[n:, 1] -= .00055
    outer[[0, -1], 0] -= .00055
    outer[[n - 1, n], 0] += .00055
    count = len(inner)
    vertices = [(x, y, (rear_z if i < n else z) + offset) for offset in [-.0002, .0002]
                for loop in [outer, inner] for i, (x, y) in enumerate(loop)]
    polygons = []
    for i in range(count):
        j = (i + 1) % count
        polygons += [(i, j, count + j, count + i),
                     (2 * count + i, 3 * count + i, 3 * count + j, 2 * count + j),
                     (i, 2 * count + i, 2 * count + j, j),
                     (count + i, count + j, 3 * count + j, 3 * count + i)]
    loop = mesh('FittedMedalEyelet', vertices, polygons, brass, smooth=False)
    for sign, endpoint in [(-1, 0), (1, -1)]:
        x = float(sample_x[endpoint] + sign * .0005)
        tip_depth = float(fronts[endpoint] - .00025)
        vertices = []
        sections = [(sign * .0095, -.0016, .0115),
                    (x, tip_depth, bottom - .0008), (x, tip_depth, z)]
        for xx, depth, height in sections:
            vertices += [(xx - .00025, depth + .0004, height), (xx + .00025, depth + .0004, height),
                         (xx + .00025, depth - .0004, height), (xx - .00025, depth - .0004, height)]
        faces = [(0, 3, 2, 1), (8, 9, 10, 11)]
        for a in [0, 4]:
            faces += [(a + i, a + (i + 1) % 4, a + 4 + (i + 1) % 4, a + 4 + i) for i in range(4)]
        strap = mesh('FormedBailStrap', vertices, faces, brass, smooth=False)
        union(loop, strap)
    union(plate, loop)
    return dict(aperture_width_m=float(hi - lo + .0008),
                aperture_depth_min_max_m=[float(np.min(backs - fronts)), float(np.max(backs - fronts))],
                rear_section_m=.00012, front_section_m=.00055, vertical_section_m=.0004,
                ribbon_min_clearance_m=.00008, rear_return_z_m=rear_z, ribbon_bottom_local_z_m=bottom,
                threaded_cross_section_z_m=z, cross_section_stations=len(sample_x),
                decision='Tilted formed bail has its rear return below the sewn ribbon and its front crossbar above the ribbon tip; rear return follows wool with 0.38 mm authored clearance; joined straps close the real opening without moving ribbon or wool')
