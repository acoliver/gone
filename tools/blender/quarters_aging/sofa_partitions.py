"""Temporary fitted seam barriers for ordered cushion solves, never export geometry."""
import bpy
import numpy as np

from common import collision

PREFIX = 'CushionPartition_'


def clear_partitions():
    for obj in list(bpy.context.scene.objects):
        if obj.name.startswith(PREFIX):
            bpy.data.objects.remove(obj, do_unlink=True)


def slab(name, centre, dimensions):
    bpy.ops.mesh.primitive_cube_add(size=1, location=centre)
    obj = bpy.context.object
    obj.name = PREFIX+name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj['aged_export'] = False
    obj.hide_render = True
    obj.display_type = 'WIRE'
    collision(obj, .0008)
    obj.collision.cloth_friction = 5
    return obj


def fitted_bounds():
    return {name: np.array([obj.matrix_world@v.co for v in obj.data.vertices])
            for name in ('SeatCushion_L', 'SeatCushion_C', 'SeatCushion_R')
            for obj in [bpy.data.objects[name]]}


def partition_plan(points, back=False):
    bounds = {name: (p.min(0), p.max(0)) for name, p in points.items()}
    seats = ['SeatCushion_L', 'SeatCushion_C', 'SeatCushion_R']
    seams = [(bounds[a][1][0]+bounds[b][0][0])/2 for a, b in zip(seats, seats[1:])]
    result = [(f'seam_{i}', (x, 0, .75), (.002, 1.2, 1.0)) for i, x in enumerate(seams)]
    result.extend([(f'arm_{side}', (x, 0, .75), (.002, 1.2, 1.0))
                   for side, x in [('left', bounds[seats[0]][0][0]-.010),
                                   ('right', bounds[seats[-1]][1][0]+.010)]])
    if back:
        # The fitted back overlaps the seat's AABB. A full-height vertical
        # plane would cut that starting pose. Above the seat welt there is a
        # vertical seam; the lower sack remains free to fold onto the seat.
        roof = max(b[1][2] for b in bounds.values())+.006
        result.append(('seat_back_upper', (0, .167, (roof+1.2)/2), (2.03, .002, 1.2-roof)))
        result.append(('back_rail', (0, .386, .75), (2.03, .002, 1.0)))
    else:
        rear = max(b[1][1] for b in bounds.values())+.007
        result.append(('seat_back_lower', (0, rear, .75), (2.03, .002, 1.0)))
    return result


def install_partitions(points, back=False):
    clear_partitions()
    objects = [slab(name, centre, dimensions) for name, centre, dimensions in partition_plan(points, back)]
    bpy.context.view_layer.update()
    return [{'name': o.name, 'centre_m': list(o.location), 'dimensions_m': list(o.dimensions),
             'exported': False} for o in objects]
