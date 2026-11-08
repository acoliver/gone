"""Settle one gathered wool sheet over a rounded arm-cap roll."""
import argparse
import json
import math
import sys
from pathlib import Path
import bpy
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cloth import SCRATCH, activate, collider
from assemble import uv


def create_sheet(amplitude, front_shift=0, pin_roll=False):
    profile = []
    control = np.array([[.87,.59],[.96,.59],[.95,.813],[1.025,.813]])
    for t in np.linspace(0,1,9):
        p = (1-t)**3*control[0]+3*(1-t)**2*t*control[1]+3*(1-t)*t*t*control[2]+t**3*control[3]
        profile.append((*p,0.))
    for x in np.linspace(1.025,1.075,4)[1:]:
        profile.append((x,.813,0.))
    for a in np.linspace(math.pi/2,0,8)[1:]:
        profile.append((1.075+.035*math.cos(a),.778+.035*math.sin(a),0.))
    for t in np.linspace(0,1,12)[1:]:
        profile.append((1.11+.014*min(1,t*4),.778-.400*t,min(1,t*4)))
    verts, faces = [], []
    nv, nu = 28, len(profile)-1
    pins = []
    for j in range(nv+1):
        t = j/nv
        y = -.405-front_shift+.63*t
        # Four gathered ripples seed vertical gravity folds. Their amplitude
        # fades at the cap so its contact strip remains a smooth rolled turn.
        wave = amplitude*(math.sin(math.tau*4*t)+.07*math.sin(math.tau*7*t))
        for i,(x,z,weight) in enumerate(profile):
            verts.append((x+wave*weight,y,z-.001+.003*weight*math.sin(math.tau*3*t)))
            if 9 <= i <= (18 if pin_roll else 12):
                pins.append(j*(nu+1)+i)
    for j in range(nv):
        for i in range(nu):
            a = j*(nu+1)+i
            faces.append((a,a+1,a+nu+2,a+nu+1))
    mesh = bpy.data.meshes.new('Throw')
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(bpy.data.materials['OatmealWool'])
    mesh.update()
    obj = bpy.data.objects.new('Throw',mesh)
    bpy.context.collection.objects.link(obj)
    for face in mesh.polygons:
        face.use_smooth = True
    return obj, pins


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--name',required=True)
    ap.add_argument('--source',type=Path,default=SCRATCH/'assembly.blend')
    ap.add_argument('--frames',type=int,default=120)
    ap.add_argument('--amplitude',type=float,default=.022)
    ap.add_argument('--bending',type=float,default=.7)
    ap.add_argument('--friction',type=float,default=30)
    ap.add_argument('--thickness',type=float,default=.004)
    ap.add_argument('--self-distance',type=float,default=.005)
    ap.add_argument('--front-shift',type=float,default=0)
    ap.add_argument('--pin-roll',action='store_true')
    args = ap.parse_args(sys.argv[sys.argv.index('--')+1:])
    bpy.ops.wm.open_mainfile(filepath=str(args.source))
    old = bpy.data.objects.get('Throw')
    if old:
        bpy.data.objects.remove(old,do_unlink=True)
    for name in ['Frame','SeatCushion_R','SeatCushion_C','BackCushion_R']:
        obj = bpy.data.objects[name]
        collider(obj,.002)
        obj.collision.cloth_friction = args.friction
    obj,pins = create_sheet(args.amplitude,args.front_shift,args.pin_roll)
    activate(obj)
    mod = obj.modifiers.new('Gathered wool gravity settle','CLOTH')
    s = mod.settings
    s.quality = 30
    s.time_scale = .5
    s.mass = .15
    s.tension_stiffness = 150
    s.compression_stiffness = 150
    s.shear_stiffness = 80
    s.bending_stiffness = args.bending
    s.tension_damping = s.compression_damping = s.shear_damping = 12
    s.bending_damping = 3
    s.air_damping = 5
    c = mod.collision_settings
    c.use_self_collision = True
    c.self_distance_min = args.self_distance
    c.distance_min = .003
    c.collision_quality = 12
    group = obj.vertex_groups.new(name='Arm cap friction contact')
    group.add(pins,1,'REPLACE')
    s.vertex_group_mass = group.name
    mod.point_cache.frame_end = args.frames
    previous = None
    for f in range(1,args.frames+1):
        bpy.context.scene.frame_set(f)
        ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        points = np.array([v.co[:] for v in ev.data.vertices])
        if f == args.frames-5:
            previous = points.copy()
        print('FRAME',f,flush=True)
    displacement = float(np.linalg.norm(points-previous,axis=1).max())
    activate(obj)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    uv(obj)
    mod = obj.modifiers.new('Bound folded wool thickness','SOLIDIFY')
    mod.thickness = args.thickness
    mod.offset = 0
    mod.use_even_offset = False
    bpy.ops.object.modifier_apply(modifier=mod.name)
    for face in obj.data.polygons:
        face.use_smooth = True
    for other in bpy.data.objects:
        for modifier in list(other.modifiers):
            other.modifiers.remove(modifier)
        if other.type == 'MESH':
            other.data.name = other.name
    bpy.context.scene.frame_set(1)
    out = SCRATCH/args.name
    out.mkdir(parents=True,exist_ok=True)
    settings = {**vars(args),'source':str(args.source),'quality':30,'time_scale':.5,
                'stiffness':[150,150,80],'mass':.15,'thickness_m':args.thickness,
                'self_distance_m':args.self_distance,'collision_distance_m':.003,'collision_quality':12,
                'arm_roll_radius_m':.035,'cap_clearance_adjustment_m':-.001,'folds':4,'sheet_width_m':.63,
                'fold_method':'one continuous thick sheet with a rounded cap roll'}
    record = {'settings':settings,'last_five_frames_max_displacement_m':displacement,
              'triangles':sum(len(p.vertices)-2 for p in obj.data.polygons)}
    (out/'numbers.json').write_text(json.dumps(record,indent=2)+'\n')
    from build import name_meshes
    name_meshes()
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'sofa.blend'))
    from build import export
    export(out/'sofa.glb')
    print(json.dumps(record),flush=True)


if __name__ == '__main__':
    main()
