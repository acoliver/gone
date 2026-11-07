"""Settle a once-folded 1.3 by 1.5 metre wool sheet on the fitted sofa."""
import argparse
import json
import math
import sys
from pathlib import Path
import bpy
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cloth import SCRATCH, activate, collider, bake
from assemble import SOURCE, uv


def create_sheet():
    path=np.array([[.209,.565],[.80,.565],[1.005,.832],[1.104,.832],[1.107,.365]])
    lengths=np.linalg.norm(np.diff(path,axis=0),axis=1)
    path[0,0]=path[1,0]-(1.5-lengths[1:].sum())
    lengths=np.linalg.norm(np.diff(path,axis=0),axis=1);arc=np.r_[0,np.cumsum(lengths)]
    # Two plies are simulated separately within one cloth object. Their folded
    # edge remains a parting line, avoiding a sub-resolution bend in a coarse grid.
    cross=[]
    for layer in range(2):
        for u in np.linspace(0,.65,13):
            cross.append((-.477+u,layer*.016))
    verts=[];faces=[];nu=24;nv=len(cross)-1
    for j,(y,dz) in enumerate(cross):
        for i in range(nu+1):
            s=i/nu*1.5; k=min(np.searchsorted(arc,s,side='right')-1,len(lengths)-1)
            t=(s-arc[k])/lengths[k]; x,z=path[k]*(1-t)+path[k+1]*t
            # Millimetric initial perturbations break a perfectly straight grid's symmetry.
            x+=.0015*math.sin(j*.8+i*.7);z+=.0015*math.sin(j*.9+i*.4)
            tangent=(path[k+1]-path[k])/lengths[k]
            normal=np.array([-tangent[1],tangent[0]])
            verts.append((x+normal[0]*dz,y,z+normal[1]*dz))
    for j in range(nv):
        if j==12:continue
        for i in range(nu):
            a=j*(nu+1)+i;faces.append((a,a+1,a+nu+2,a+nu+1))
    mesh=bpy.data.meshes.new('Folded 1.3 x 1.5 m wool');mesh.from_pydata(verts,[],faces);mesh.materials.append(bpy.data.materials['OatmealWool']);mesh.update()
    obj=bpy.data.objects.new('Throw',mesh);bpy.context.collection.objects.link(obj)
    for p in mesh.polygons:p.use_smooth=True
    return obj


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--name',default='throw-a');ap.add_argument('--frames',type=int,default=50);ap.add_argument('--bending',type=float,default=.3);ap.add_argument('--friction',type=float,default=20);ap.add_argument('--pin-cap',action='store_true')
    ap.add_argument('--source',default=str(SOURCE))
    ap.add_argument('--clearance-lift',type=float,default=.002)
    args=ap.parse_args(sys.argv[sys.argv.index('--')+1:])
    bpy.ops.wm.open_mainfile(filepath=str(Path(args.source).resolve()))
    old=bpy.data.objects.get('Throw')
    if old:bpy.data.objects.remove(old,do_unlink=True)
    for name in ['Frame','SeatCushion_R','SeatCushion_C','BackCushion_R']:
        ob=bpy.data.objects[name];collider(ob);ob.collision.cloth_friction=args.friction
    obj=create_sheet();activate(obj);mod=obj.modifiers.new('Wool drape settle','CLOTH');s=mod.settings
    s.quality=30;s.time_scale=.5;s.mass=.15;s.tension_stiffness=100;s.compression_stiffness=100;s.shear_stiffness=50;s.bending_stiffness=args.bending
    s.tension_damping=12;s.compression_damping=12;s.shear_damping=12;s.bending_damping=3;s.air_damping=5
    c=mod.collision_settings;c.use_self_collision=True;c.self_distance_min=.004;c.distance_min=.004;c.collision_quality=12;c.self_friction=.5
    if args.pin_cap:
        # This contact strip represents static grip at the cap, not a rigid throw.
        ids=[j*25+16 for j in range(len(obj.data.vertices)//25)]
        for i in ids:obj.data.vertices[i].co.z-=.020
        group=obj.vertex_groups.new(name='Arm cap static contact');group.add(ids,1,'REPLACE');s.vertex_group_mass=group.name
    mod.point_cache.frame_end=args.frames
    previous=None;displacement=None
    for f in range(1,args.frames+1):
        bpy.context.scene.frame_set(f)
        ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());p=np.array([v.co[:] for v in ev.data.vertices])
        if f==args.frames-5:previous=p.copy()
        if f==args.frames:displacement=float(np.linalg.norm(p-previous,axis=1).max())
        print('FRAME',f,flush=True)
    activate(obj);bpy.ops.object.modifier_apply(modifier=mod.name)
    uv(obj)
    thick=obj.modifiers.new('Six millimetre wool thickness','SOLIDIFY');thick.thickness=.006;thick.offset=0;thick.use_even_offset=False
    bpy.ops.object.modifier_apply(modifier=thick.name)
    for p in obj.data.polygons:p.use_smooth=True
    # Leave clearance for triangle chords after adding the wool thickness.
    obj.location.z+=args.clearance_lift
    obj['cloth_clearance_lift_m']=args.clearance_lift
    v=np.array([v.co[:] for v in obj.data.vertices])+np.array(obj.location);lo=v.min(axis=0);hi=v.max(axis=0)
    record={'settings':vars(args),'sheet_m':[1.3,1.5],'fold_method':'two 0.65 x 1.5 m plies','quality':30,'time_scale':.5,'stiffness':[100,100,50],'mass':.15,'thickness_m':.006,'self_distance_m':.004,'collision_distance_m':.004,'bounds_blender_m':[lo.tolist(),hi.tolist()],'triangles':sum(len(p.vertices)-2 for p in obj.data.polygons),'last_five_frames_max_displacement_m':displacement}
    out=SCRATCH/args.name;out.mkdir(parents=True,exist_ok=True);(out/'numbers.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record),flush=True)
    for ob in bpy.data.objects:
        for m in list(ob.modifiers):ob.modifiers.remove(m)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'sofa.blend'))

if __name__=='__main__':main()
