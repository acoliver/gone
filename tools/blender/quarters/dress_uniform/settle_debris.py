"""Settle released allowances on the deposit from a curled, area-preserving rest."""
import math

import bmesh
import bpy
import numpy as np

from cloth_stage import configure
from common import collision, recalc


def curl_strip(obj, number):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.subdivide_edges(bm, edges=list(bm.edges), cuts=3, use_grid_fill=True)
    bmesh.ops.triangulate(bm, faces=list(bm.faces), quad_method='BEAUTY')
    bm.to_mesh(obj.data)
    bm.free()
    points = np.array([v.co[:] for v in obj.data.vertices])
    center = points.mean(0)
    axes = np.linalg.svd(points-center)[2]
    coordinates = (points-center) @ axes.T
    s = coordinates[:, 0]
    stations = np.linspace(s.min(), s.max(), 2048)
    phase = number*.9
    angle = .85*np.sin(2*math.pi*(stations-stations[0])/np.ptp(stations)+phase)
    step = np.diff(stations)
    x = np.r_[0, np.cumsum((np.cos(angle[:-1])+np.cos(angle[1:]))*.5*step)]
    z = np.r_[0, np.cumsum((np.sin(angle[:-1])+np.sin(angle[1:]))*.5*step)]
    x -= (x.min()+x.max())/2
    z -= z.min()
    yaw = [-.35, .20, .70][number]
    along = np.array([math.cos(yaw), math.sin(yaw)])
    across = np.array([-along[1], along[0]])
    xy = np.interp(s, stations, x)[:, None]*along+coordinates[:, 1, None]*across
    xy += np.array([[-.045, -.008], [.020, .018], [.055, -.020]])[number]
    height = -.890+np.interp(s, stations, z)+coordinates[:, 2]
    for vertex, point, h in zip(obj.data.vertices, xy, height):
        vertex.co = (*point, h)
    recalc(obj)
    obj.data.calc_loop_triangles()
    vertices = np.array([v.co[:] for v in obj.data.vertices])
    faces = np.array([t.vertices[:] for t in obj.data.loop_triangles])
    triangles = vertices[faces]
    lengths = np.linalg.norm(triangles-np.roll(triangles, 1, axis=1), axis=2)
    altitude = np.linalg.norm(np.cross(triangles[:, 1]-triangles[:, 0], triangles[:, 2]-triangles[:, 0]), axis=1)/lengths.max(1)
    if altitude.min() < .002:
        raise ValueError(f'{obj.name}: curled rest has sub-contact triangles: {altitude.min()}')
    return dict(minimum_rest_altitude_m=float(altitude.min()),
                method='arclength-preserving curled strip, deposited over mound before gravity')


def settle_fallen(out, record, config, bake_simulation):
    for piece in record['fallen']:
        bpy.data.objects.remove(bpy.data.objects[piece['name']], do_unlink=True)
    names = tuple(piece['name'] for piece in record['fallen'])
    with bpy.data.libraries.load(str(out/'prepared.blend'), link=False) as (source, target):
        target.objects = list(names)
    for obj in target.objects:
        bpy.context.collection.objects.link(obj)
        obj['aged_export'] = True
    body = bpy.data.objects['TunicBody']
    mound = bpy.data.objects['FibreDust']
    collision(body, .0015)
    source_area = sum(p.area for p in body.data.polygons)
    record['fallen_simulations'] = {}
    for number, piece in enumerate(record['fallen']):
        obj = bpy.data.objects[piece['name']]
        rest = curl_strip(obj, number)
        bpy.context.scene.frame_set(1)
        settings = dict(config, frames=800)
        reference = record['density']['unaged_vertices']*piece['area_m2']/source_area
        mod = configure(obj, settings, reference)
        mod.settings.tension_damping = mod.settings.compression_damping = mod.settings.shear_damping = 5.
        mod.settings.bending_damping = .5
        mod.settings.air_damping = 10.
        mod.collision_settings.vertex_group_self_collisions = ''
        rest['exclusion_vertices'] = 0
        result = bake_simulation(obj, mod, 800, settle=True)
        result['rest'] = rest
        record['fallen_simulations'][obj.name] = result
        collision(obj, .001)
    for obj in [body, mound]+[bpy.data.objects[name] for name in names]:
        for modifier in list(obj.modifiers):
            if modifier.type == 'COLLISION':
                obj.modifiers.remove(modifier)
    return record
