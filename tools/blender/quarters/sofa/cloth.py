"""Small, independently measured cloth experiments. Coordinates are Blender Z-up."""
import argparse
import json
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[4]
SCRATCH = ROOT / 'tmp/fit/sofa/cloth2'


def activate(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def box_shell(name, dims, divisions=(14, 14, 4), radius=.022):
    half = np.array(dims) / 2
    core = half - radius
    verts, faces, indices = [], [], {}
    def vertex(grid):
        grid = tuple(grid)
        if grid not in indices:
            p = np.array(grid) / np.array(divisions) * 2 - 1
            q = p * half
            c = np.clip(q, -core, core)
            delta = q - c
            q = c + delta / np.linalg.norm(delta) * radius
            indices[grid] = len(verts)
            verts.append(q.tolist())
        return indices[grid]
    for axis in range(3):
        u, v = (axis + 1) % 3, (axis + 2) % 3
        for side in (0, divisions[axis]):
            for j in range(divisions[u]):
                for k in range(divisions[v]):
                    quad = []
                    for a, b in ((j,k),(j+1,k),(j+1,k+1),(j,k+1)):
                        g = [0,0,0]; g[axis] = side; g[u] = a; g[v] = b
                        quad.append(vertex(g))
                    faces.append(quad if side else quad[::-1])
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces); mesh.update()
    obj = bpy.data.objects.new(name, mesh); bpy.context.collection.objects.link(obj)
    return obj


def collider(obj, distance=.001):
    obj.modifiers.new('Cloth collision', 'COLLISION')
    obj.collision.thickness_outer = distance
    obj.collision.thickness_inner = .001
    obj.collision.cloth_friction = 8


def cloth(obj, pressure, scale=1, bending=.2, stiffness=100, mass=.015, pin=False):
    activate(obj)
    mod = obj.modifiers.new('Upholstery pressure settle', 'CLOTH')
    s = mod.settings
    s.quality = 20
    s.mass = mass
    s.tension_stiffness = stiffness
    s.compression_stiffness = stiffness
    s.shear_stiffness = stiffness * .7
    s.bending_stiffness = bending
    s.tension_damping = 15
    s.compression_damping = 15
    s.shear_damping = 15
    s.bending_damping = 2
    s.air_damping = 5
    s.use_pressure = True
    s.uniform_pressure_force = pressure
    s.pressure_factor = scale
    c = mod.collision_settings
    c.use_self_collision = True
    c.self_distance_min = .002
    c.distance_min = .001
    c.collision_quality = 6
    if pin:
        vg = obj.vertex_groups.new(name='Lower seam anchors')
        bottom = min(v.co.z for v in obj.data.vertices)
        ids = [v.index for v in obj.data.vertices if v.co.z < bottom + .005]
        vg.add(ids, 1, 'REPLACE'); s.vertex_group_mass = vg.name
    return mod


def bake(obj, mod, frame):
    scene = bpy.context.scene
    mod.point_cache.frame_start = 1; mod.point_cache.frame_end = frame
    for f in range(1, frame+1):
        scene.frame_set(f)
        obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh_clear()
        print('FRAME', f, flush=True)
    activate(obj)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    for face in obj.data.polygons:
        face.use_smooth = True


def ray(obj, origin, direction):
    hit, loc, normal, idx = obj.ray_cast(Vector(origin), Vector(direction))
    if not hit:
        raise ValueError(f'Ray missed {obj.name}: {origin}')
    return np.array(loc)


def measurements(obj):
    v = np.array([p.co[:] for p in obj.data.vertices])
    lo, hi = v.min(axis=0), v.max(axis=0)
    center = (lo + hi)/2
    top = ray(obj, (center[0],center[1],hi[2]+1), (0,0,-1))[2]
    edges = []
    for axis in (0,1):
        for sign in (-1,1):
            p = center.copy(); p[axis] = lo[axis]+.020 if sign<0 else hi[axis]-.020; p[2] = hi[2]+1
            edges.append(float(ray(obj,p,(0,0,-1))[2]))
    bulges = []
    for axis in (0,1):
        for sign in (-1,1):
            p = center.copy(); p[axis] = center[axis]+sign*2
            d = [0,0,0]; d[axis] = -sign
            mid = ray(obj,p,d)[axis]
            p[2] = hi[2]-.025
            hit, loc, normal, idx = obj.ray_cast(Vector(p),Vector(d))
            bulges.append(float(sign*(mid-loc[axis])) if hit else None)
    return {'bounds_blender_m':[lo.tolist(),hi.tolist()], 'extents_m':(hi-lo).tolist(),
            'top_center_m':float(top), 'top_edge_20mm_m':edges,
            'crown_m':float(top-np.mean(edges)), 'side_bulges_m':bulges,
            'quads':len(obj.data.polygons), 'triangles':sum(len(p.vertices)-2 for p in obj.data.polygons)}


def experiment(args):
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    scene=bpy.context.scene; scene.render.fps=24
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0,0,-.025))
    deck=bpy.context.object; deck.name='Deck'; deck.dimensions=(1,1,.05)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); collider(deck)
    obj=box_shell('SeatCushion_C',(.66,.70,args.height),tuple(args.divisions),args.radius)
    # A sewn upper shoulder sits inside the side-wall belly. This gives the
    # pressure shell a rounded edge without pulling its whole side into a dome.
    for v in obj.data.vertices:
        t=np.clip(v.co.z/(args.height/2-args.radius),0,1)
        t=t*t*(3-2*t)
        for axis,half in ((0,.33),(1,.35)):
            weight=max(0,(abs(v.co[axis])-(half-.13))/.13)
            v.co[axis]-=np.sign(v.co[axis])*args.shoulder_inset*weight*t
    obj.location.z=args.height/2+.002
    mod=cloth(obj,args.pressure,args.scale,args.bending,args.stiffness,args.mass,args.pin)
    bake(obj,mod,args.frames)
    out=SCRATCH/args.name; out.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'cushion.blend'))
    raw=np.array([v.co[:] for v in obj.data.vertices])
    print('RAW_BOUNDS',raw.min(axis=0),raw.max(axis=0),flush=True)
    record={'settings':{**vars(args),'quality':20,'shear_stiffness':args.stiffness*.7,
                        'collision_quality':6,'collision_distance_m':.001,
                        'self_distance_m':.002,'bevel_radius_m':args.radius},
            'measurements':measurements(obj)}
    (out/'numbers.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record),flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--name',required=True)
    ap.add_argument('--pressure',type=float,default=.001)
    ap.add_argument('--scale',type=float,default=.001)
    ap.add_argument('--bending',type=float,default=.2)
    ap.add_argument('--stiffness',type=float,default=100)
    ap.add_argument('--mass',type=float,default=.015)
    ap.add_argument('--frames',type=int,default=20)
    ap.add_argument('--pin',action='store_true')
    ap.add_argument('--shoulder-inset',type=float,default=0)
    ap.add_argument('--radius',type=float,default=.055)
    ap.add_argument('--height',type=float,default=.16)
    ap.add_argument('--divisions',type=int,nargs=3,default=[14,16,6])
    experiment(ap.parse_args(sys.argv[sys.argv.index('--')+1:]))
